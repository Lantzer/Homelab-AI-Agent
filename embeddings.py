"""
Layer 2: Embeddings and Vector Storage

Goal: Take our text chunks and store them in ChromaDB so we can
later retrieve only the chunks relevant to a user's question.

How it works:
  - ChromaDB converts each chunk to a vector (list of ~380 numbers)
  - Each number represents some dimension of meaning
  - Similar text = similar vectors = close together in vector space
  - When you ask a question, we convert it to a vector too,
    then find the chunks with the closest vectors
"""

import sys
import json
import os
import shutil
import chromadb
from scraper import fetch_docs, read_local_file, chunk_text

SOURCES_FILE = "./sources.json"


def save_source(source: str):
    sources = get_sources()
    if source not in sources:
        sources.append(source)
        with open(SOURCES_FILE, "w") as f:
            json.dump(sources, f)


def get_sources() -> list[str]:
    if not os.path.exists(SOURCES_FILE):
        return []
    with open(SOURCES_FILE) as f:
        return json.load(f)


def delete_index():
    if os.path.exists("./chroma_db"):
        shutil.rmtree("./chroma_db")
    if os.path.exists(SOURCES_FILE):
        os.remove(SOURCES_FILE)


def ingest(source: str, collection_name: str = "doc") -> int:
    """
    Ingest a document from a URL or local file path into ChromaDB.
    Returns the number of chunks added.
    """
    if source.startswith("http"):
        text = fetch_docs(source)
    else:
        text = read_local_file(source)

    chunks = chunk_text(text)
    build_index(chunks, collection_name=collection_name)
    save_source(source)
    return len(chunks)


def build_index(chunks: list[str], collection_name: str = "doc") -> chromadb.Collection:
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_or_create_collection(name=collection_name)

    offset = collection.count()
    collection.add(
        documents=chunks,
        ids=[f"chunk_{offset + i}" for i in range(len(chunks))]
    )
    print(f"Indexed {len(chunks)} chunks (collection now has {collection.count()} total)")

    return collection

def load_index(collection_name: str = "doc") -> chromadb.Collection:
    client = chromadb.PersistentClient(path="./chroma_db")
    return client.get_collection(name=collection_name)


def query_index(collection: chromadb.Collection, question: str, n_results: int = 3) -> list[str]:
    """
    Given a question, find the most relevant chunks.

    ChromaDB converts your question to a vector, then returns
    the n_results chunks whose vectors are closest to it.
    """
    results = collection.query(
        query_texts=[question],
        n_results=n_results
    )

    # results["documents"] is a list of lists — one per query
    # We only sent one query so we grab index 0
    return results["documents"][0]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python embeddings.py <filepath or url>")
        sys.exit(1)

    source = sys.argv[1]

    try:
        count = ingest(source)
        print(f"\nDone. {count} chunks ingested from: {source}")
    except FileNotFoundError:
        print(f"Error: File not found — {source}")
        sys.exit(1)
    except Exception as e:
        print(f"Error during ingestion: {e}")
        sys.exit(1)


# Previously used for testing
# if __name__ == "__main__":
#     # Test it with fake chunks so we can see retrieval working
#     fake_chunks = [
#         "requests.get(url, params=None) sends a GET request and returns a Response object.",
#         "requests.post(url, data=None, json=None) sends a POST request with a body.",
#         "Response.status_code returns the HTTP status code as an integer, e.g. 200 or 404.",
#         "Response.json() parses the response body as JSON and returns a Python dict.",
#         "Session objects let you persist cookies and headers across multiple requests.",
#         "Timeout parameter controls how long to wait for the server before giving up.",
#     ]

#     collection = build_index(fake_chunks)

#     # Ask a question — watch which chunks come back
#     question = "how do I send a POST request?"
#     print(f"\nQuestion: {question}")
#     print(f"\nTop relevant chunks:")
    
#     relevant = query_index(collection, question)
#     for i, chunk in enumerate(relevant):
#         print(f"\n  [{i+1}] {chunk}")