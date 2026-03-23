"""
Layer 3: The LLM Call

Goal: Take the relevant chunks from Layer 2 and use them as context
for Ollama to answer the user's question, grounded in the actual docs.
"""

import os
import sys
import ollama
from embeddings import build_index, query_index
from scraper import fetch_docs, chunk_text, read_local_file

def build_prompt(question: str, chunks: list[str]) -> str:
    """
    Combine the retrieved chunks and the user's question into a prompt.
    The chunks act as Ollama's only source of truth.
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
    3. Send to Ollama and return the answer
    """
    # Layer 2 — retrieve relevant chunks
    chunks = query_index(collection, question)

    # Build the grounded prompt
    prompt = build_prompt(question, chunks)

    # Layer 3 — Using Ollama
    
    response = ollama.chat(
        model="llama3.2",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response["message"]["content"]


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: python agent.py <filepath or url>")
        sys.exit(1)

    source = sys.argv[1]

    # Load and chunk the source
    if source.startswith("http"):
        text = fetch_docs(source)
    else:
        text = read_local_file(source)

    chunks = chunk_text(text)

    # Build the index
    print("Indexing chunks...")
    collection = build_index(chunks)

    # Ask questions in a loop
    print("\nReady! Ask questions about your docs. Type 'exit' to quit.\n")
    while True:
        question = input("You: ")
        if question.lower() == "exit":
            break
        print(f"\nAnswer: {ask(question, collection)}\n")