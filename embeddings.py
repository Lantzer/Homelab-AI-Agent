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

import chromadb

def build_index(chunks: list[str], collection_name: str = "api_docs") -> chromadb.Collection:
    """
    Take text chunks and store them in ChromaDB.
    ChromaDB automatically handles the embedding (vectorizing) for us.
    """
    # Creates a local ChromaDB instance — stores data in memory for now
    client = chromadb.EphemeralClient()

    # A collection is like a table — holds all chunks for one docs site
    collection = client.create_collection(name=collection_name)

    # Add all chunks — ChromaDB embeds them automatically
    collection.add(
        documents=chunks,
        ids=[f"chunk_{i}" for i in range(len(chunks))]  # each chunk needs a unique ID
    )

    print(f"Indexed {len(chunks)} chunks into ChromaDB")
    return collection


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
    # Test it with fake chunks so we can see retrieval working
    fake_chunks = [
        "requests.get(url, params=None) sends a GET request and returns a Response object.",
        "requests.post(url, data=None, json=None) sends a POST request with a body.",
        "Response.status_code returns the HTTP status code as an integer, e.g. 200 or 404.",
        "Response.json() parses the response body as JSON and returns a Python dict.",
        "Session objects let you persist cookies and headers across multiple requests.",
        "Timeout parameter controls how long to wait for the server before giving up.",
    ]

    collection = build_index(fake_chunks)

    # Ask a question — watch which chunks come back
    question = "how do I send a POST request?"
    print(f"\nQuestion: {question}")
    print(f"\nTop relevant chunks:")
    
    relevant = query_index(collection, question)
    for i, chunk in enumerate(relevant):
        print(f"\n  [{i+1}] {chunk}")