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

Collections:
  homelab   — the user's personal homelab documentation
  supporting — general product manuals, guides, and reference docs
"""

import sys
import json
import os
import shutil
import chromadb
from Core.scraper import fetch_docs, read_local_file, chunk_text

HOMELAB_COLLECTION = "homelab"
SUPPORTING_COLLECTION = "supporting"


def _sources_file(collection_name: str) -> str:
    return f"./data/sources_{collection_name}.json"


def save_source(source: str, collection_name: str = HOMELAB_COLLECTION):
    sources = get_sources(collection_name)
    if source not in sources:
        sources.append(source)
        with open(_sources_file(collection_name), "w") as f:
            json.dump(sources, f)


def get_sources(collection_name: str = HOMELAB_COLLECTION) -> list[str]:
    path = _sources_file(collection_name)
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def init_collections():
    """Ensure both homelab and supporting collections exist on startup."""
    client = chromadb.PersistentClient(path="./data/chroma_db")
    for name in (HOMELAB_COLLECTION, SUPPORTING_COLLECTION):
        client.get_or_create_collection(name=name)
        print(f"Collection '{name}' ready.")


def delete_index(collection_name: str = None):
    """
    Delete a specific collection or the entire index.
    If collection_name is None, deletes all of ./data/chroma_db and all sources files.
    """
    if collection_name is None:
        if os.path.exists("./data/chroma_db"):
            shutil.rmtree("./data/chroma_db")
        # Remove all per-collection sources files
        for name in (HOMELAB_COLLECTION, SUPPORTING_COLLECTION, "doc"):
            path = _sources_file(name)
            if os.path.exists(path):
                os.remove(path)
        # Remove legacy sources file
        if os.path.exists("./data/sources.json"):
            os.remove("./data/sources.json")
    else:
        try:
            client = chromadb.PersistentClient(path="./data/chroma_db")
            client.delete_collection(name=collection_name)
        except Exception:
            pass
        path = _sources_file(collection_name)
        if os.path.exists(path):
            os.remove(path)


def ingest(source: str, collection_name: str = HOMELAB_COLLECTION) -> int:
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
    save_source(source, collection_name)
    return len(chunks)


def build_index(chunks: list[str], collection_name: str = HOMELAB_COLLECTION) -> chromadb.Collection:
    client = chromadb.PersistentClient(path="./data/chroma_db")
    collection = client.get_or_create_collection(name=collection_name)

    offset = collection.count()
    collection.add(
        documents=chunks,
        ids=[f"chunk_{offset + i}" for i in range(len(chunks))]
    )
    print(f"Indexed {len(chunks)} chunks into '{collection_name}' (collection now has {collection.count()} total)")

    return collection

def load_index(collection_name: str = HOMELAB_COLLECTION) -> chromadb.Collection:
    client = chromadb.PersistentClient(path="./data/chroma_db")
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
        print("Usage: python embeddings.py <filepath or url> [collection_name]")
        print(f"  collection_name defaults to '{HOMELAB_COLLECTION}'")
        sys.exit(1)

    source = sys.argv[1]
    coll = sys.argv[2] if len(sys.argv) > 2 else HOMELAB_COLLECTION

    try:
        count = ingest(source, collection_name=coll)
        print(f"\nDone. {count} chunks ingested from: {source} into '{coll}'")
    except FileNotFoundError:
        print(f"Error: File not found — {source}")
        sys.exit(1)
    except Exception as e:
        print(f"Error during ingestion: {e}")
        sys.exit(1)
