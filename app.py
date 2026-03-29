from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from Core.agent import ask
from Core.embeddings import ingest, get_sources, delete_index, load_index, init_collections, HOMELAB_COLLECTION, SUPPORTING_COLLECTION

load_dotenv()
init_collections()

app = Flask(__name__, template_folder="web/templates", static_folder="web/assets")

conversation_history = []


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/ask", methods=["POST"])
def ask_question():
    global conversation_history
    data = request.get_json()
    question = data.get("question", "").strip()

    if not question:
        return jsonify({"error": "Question cannot be empty."}), 400

    try:
        result = ask(question, conversation_history)
        conversation_history = result["history"]
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Agent error: {e}"}), 500


@app.route("/reset-chat", methods=["POST"])
def reset_chat():
    global conversation_history
    conversation_history = []
    return jsonify({"message": "Conversation cleared."})


@app.route("/ingest", methods=["POST"])
def ingest_document():
    data = request.get_json()
    source = data.get("source", "").strip()
    collection_name = data.get("collection", SUPPORTING_COLLECTION)

    if not collection_name in (HOMELAB_COLLECTION, SUPPORTING_COLLECTION):
        collection_name = SUPPORTING_COLLECTION

    if not source:
        return jsonify({"error": "Source cannot be empty."}), 400

    if source.endswith(".txt"):
        return ingest_list(source, collection_name)

    try:
        count = ingest(source, collection_name)
        return jsonify({"message": f"Successfully ingested {count} chunks from: {source} into '{collection_name}'"})
    except FileNotFoundError:
        return jsonify({"error": f"File not found: {source}"}), 400
    except Exception as e:
        return jsonify({"error": f"Ingestion failed: {e}"}), 500


def ingest_list(filepath: str, collection_name: str = HOMELAB_COLLECTION):
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
            ingest(src, collection_name)
            succeeded.append(src)
        except Exception as e:
            failed.append({"source": src, "error": str(e)})

    return jsonify({
        "message": f"Ingested {len(succeeded)} of {len(sources)} sources into '{collection_name}'.",
        "succeeded": succeeded,
        "failed": failed
    })


@app.route("/sources", methods=["GET"])
def list_sources():
    collection_name = request.args.get("collection", SUPPORTING_COLLECTION)
    if collection_name not in (HOMELAB_COLLECTION, SUPPORTING_COLLECTION):
        collection_name = SUPPORTING_COLLECTION
    return jsonify({"sources": get_sources(collection_name), "collection": collection_name})


@app.route("/reset", methods=["POST"])
def reset_index():
    data = request.get_json() or {}
    collection_name = data.get("collection", None)
    try:
        delete_index(collection_name)
        label = f"'{collection_name}' collection" if collection_name else "entire index"
        return jsonify({"message": f"Deleted {label}. Ready for fresh ingestion."})
    except Exception as e:
        return jsonify({"error": f"Failed to delete index: {e}"}), 500


if __name__ == "__main__":
    app.run(debug=True)
