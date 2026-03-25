from flask import Flask, request, jsonify, render_template
from chromadb.errors import NotFoundError
from agent import ask, build_prompt
from embeddings import load_index, ingest, get_sources, delete_index

app = Flask(__name__)

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

    try:
        count = ingest(source)
        collection = load_index()  # Refresh collection after ingestion
        return jsonify({"message": f"Successfully ingested {count} chunks from: {source}"})
    except FileNotFoundError:
        return jsonify({"error": f"File not found: {source}"}), 400
    except Exception as e:
        return jsonify({"error": f"Ingestion failed: {e}"}), 500


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
