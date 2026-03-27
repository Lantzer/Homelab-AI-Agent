import os
import tempfile
from functools import wraps
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from chromadb.errors import NotFoundError
from Core.agent import ask, build_prompt
from Core.embeddings import load_index, ingest, get_sources, delete_index

app = Flask(__name__, template_folder="web/templates", static_folder="web/assets")

# Hard cap on upload size — Flask returns 413 automatically if exceeded.
# Prevents memory exhaustion from oversized payloads before route code even runs.
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

# Allowlist of permitted file extensions — everything else is rejected immediately.
# Keeps the attack surface small; no processing occurs on unknown types.
ALLOWED_EXTENSIONS = {".md", ".txt", ".pdf"}

# Magic bytes for binary formats — the known byte signature at the start of a valid file.
# Used to detect extension spoofing (e.g. a renamed .exe submitted as .pdf).
MAGIC_BYTES = {
    ".pdf": b"%PDF",
}


def require_localhost(f):
    """Decorator that restricts an endpoint to localhost only.
    Rejects any request not from 127.0.0.1 or ::1 before route code runs.
    Protects the upload endpoint from network access even if the port is exposed."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.remote_addr not in ("127.0.0.1", "::1"):
            return jsonify({"error": "Access denied."}), 403
        return f(*args, **kwargs)
    return decorated


def validate_file_contents(file_bytes: bytes, ext: str) -> bool:
    """Verify file contents match the declared extension.
    For binary formats, checks magic bytes against known signatures.
    For text formats, verifies the data is valid UTF-8 — a renamed binary will fail this.
    Both checks must pass; extension alone is not trusted."""
    if ext in MAGIC_BYTES:
        magic = MAGIC_BYTES[ext]
        return file_bytes[:len(magic)] == magic
    try:
        file_bytes[:512].decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False

# Load or lazily initialize the collection
collection = None

def get_collection():
    global collection
    if collection is None:
        collection = load_index()
    return collection


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/ask", methods=["POST"])
def ask_question():
    data = request.get_json()
    question = data.get("question", "").strip()

    if not question:
        return jsonify({"error": "Question cannot be empty."}), 400

    try:
        col = get_collection()
    except NotFoundError:
        return jsonify({"error": "No documents indexed yet. Add a document first."}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to load index: {e}"}), 500

    answer = ask(question, col)
    return jsonify({"answer": answer})


@app.route("/ingest", methods=["POST"])
def ingest_document():
    global collection

    data = request.get_json()
    source = data.get("source", "").strip()

    if not source:
        return jsonify({"error": "Source cannot be empty."}), 400

    if source.endswith(".txt"):
        return ingest_list(source)

    try:
        count = ingest(source)
        collection = load_index()
        return jsonify({"message": f"Successfully ingested {count} chunks from: {source}"})
    except FileNotFoundError:
        return jsonify({"error": f"File not found: {source}"}), 400
    except Exception as e:
        return jsonify({"error": f"Ingestion failed: {e}"}), 500


def ingest_list(filepath: str):
    global collection

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            sources = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return jsonify({"error": f"File not found: {filepath}"}), 400
    except Exception as e:
        return jsonify({"error": f"Could not read file: {e}"}), 500

    if not sources:
        return jsonify({"error": "File is empty."}), 400

    succeeded, failed = [], []

    for src in sources:
        try:
            ingest(src)
            succeeded.append(src)
        except Exception as e:
            failed.append({"source": src, "error": str(e)})

    if succeeded:
        collection = load_index()

    return jsonify({
        "message": f"Ingested {len(succeeded)} of {len(sources)} sources.",
        "succeeded": succeeded,
        "failed": failed
    })


@app.route("/upload", methods=["POST"])
@require_localhost  # Network-level gate — only localhost can reach this endpoint
def upload_document():
    global collection

    if "file" not in request.files:
        return jsonify({"error": "No file provided."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    # secure_filename strips path components and dangerous characters from the filename.
    # Prevents path traversal attacks (e.g. "../../etc/passwd" in the filename field).
    safe_name = secure_filename(file.filename)
    ext = os.path.splitext(safe_name)[1].lower()

    # Extension allowlist check — reject unsupported types before reading any content.
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"Unsupported file type: {ext}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"}), 400

    file_bytes = file.read()

    # Content validation — verify the file is actually what its extension claims.
    # Catches renamed files and basic polyglots; extension alone cannot be trusted.
    if not validate_file_contents(file_bytes, ext):
        return jsonify({"error": "File contents do not match the declared file type."}), 400

    tmp_path = None
    try:
        # Write to a temp file so the existing ingest() pipeline works unchanged.
        # delete=False gives us explicit control — cleanup is guaranteed by the finally block.
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        count = ingest(tmp_path)
        collection = load_index()
        return jsonify({"message": f"Successfully ingested {count} chunks from: {safe_name}"})
    except Exception as e:
        return jsonify({"error": f"Ingestion failed: {e}"}), 500
    finally:
        # Always delete the temp file — even if ingestion raises an exception.
        # Ensures no uploaded content persists on disk after processing.
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.route("/sources", methods=["GET"])
def list_sources():
    return jsonify({"sources": get_sources()})


@app.route("/reset", methods=["POST"])
def reset_index():
    global collection
    try:
        delete_index()
        collection = None
        return jsonify({"message": "Index deleted. Ready for fresh ingestion."})
    except Exception as e:
        return jsonify({"error": f"Failed to delete index: {e}"}), 500


if __name__ == "__main__":
    app.run(debug=True)
