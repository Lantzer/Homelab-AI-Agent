"""
Layer 3: The LLM Call

Goal: Take the relevant chunks from Layer 2 and use them as context
for Claude to answer the user's question, grounded in the actual docs.
"""

import os
import anthropic
from dotenv import load_dotenv
from embeddings import build_index, query_index
from scraper import fetch_docs, chunk_text

load_dotenv()

def build_prompt(question: str, chunks: list[str]) -> str:
    """
    Combine the retrieved chunks and the user's question into a prompt.
    The chunks act as Claude's only source of truth.
    """
    context = ""
    for i, chunk in enumerate(chunks):
        context += f"--- chunk {i+1} ---\n{chunk}\n\n"

    return f"""You are a helpful homelab assistant. Answer the user's question 
based only on the documentation provided below. If the answer isn't in the 
documentation, say so — do not guess or make things up.

DOCUMENTATION:
{context}

QUESTION:
{question}"""


def ask(question: str, collection) -> str:
    """
    Full RAG pipeline:
    1. Retrieve relevant chunks from ChromaDB
    2. Build a prompt with those chunks as context
    3. Send to Claude and return the answer
    """
    # Layer 2 — retrieve relevant chunks
    chunks = query_index(collection, question)

    # Build the grounded prompt
    prompt = build_prompt(question, chunks)

    # Layer 3 — call Claude
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response.content[0].text


if __name__ == "__main__":
    # Test the full pipeline end to end with fake chunks
    fake_chunks = [
        "requests.get(url, params=None) sends a GET request and returns a Response object.",
        "requests.post(url, data=None, json=None) sends a POST request with a body.",
        "Response.status_code returns the HTTP status code as an integer, e.g. 200 or 404.",
        "Response.json() parses the response body as JSON and returns a Python dict.",
        "Session objects let you persist cookies and headers across multiple requests.",
        "Timeout parameter controls how long to wait for the server before giving up.",
    ]

    print("Indexing chunks...")
    collection = build_index(fake_chunks)

    question = "How do I send a POST request with JSON data?"
    print(f"\nQuestion: {question}")
    print(f"\nAnswer:")
    print(ask(question, collection))