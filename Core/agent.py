"""
Agent: Prompt Builder and Query Layer

Handles querying the ChromaDB index and generating answers via Ollama.
Documents are added to the index separately via ingest.py.
"""

import ollama
from chromadb.errors import NotFoundError
from Core.embeddings import load_index, query_index


def build_prompt(question: str, chunks: list[str]) -> str:
    context = ""
    for i, chunk in enumerate(chunks):
        context += f"--- chunk {i+1} ---\n{chunk}\n\n"

    return f"""You are an expert homelab assistant. Your goal is to answer the user's question using the documentation provided, and where relevant, suggest ways to optimize, improve, or simplify their setup.

Guidelines:
- Base your answer on the documentation below
- If the answer isn't in the documentation, say so clearly
- If you can identify inefficiencies, better configurations, or useful alternatives based on the context, mention them
- Keep suggestions practical and specific to what's described in the docs

DOCUMENTATION:
{context}

QUESTION:
{question}"""


def ask(question: str, collection) -> str:
    chunks = query_index(collection, question)

    if not chunks:
        return "No relevant documents found. Try adding documents via the ingest process."

    prompt = build_prompt(question, chunks)

    # Handle errors per question
    try:
        response = ollama.chat(
            model="llama3.2",
            messages=[{"role": "user", "content": prompt}]
        )
        return response["message"]["content"]
    except ollama.ResponseError as e:
        return f"Ollama error: {e}"
    except Exception as e:
        return f"Unexpected error contacting Ollama: {e}"


if __name__ == "__main__":
    try:
        collection = load_index()
    except NotFoundError:
        print("Error: No documents indexed yet. Run ingest.py first.")
        raise SystemExit(1)
    except Exception as e:
        print(f"Error loading index: {e}")
        raise SystemExit(1)

    print("\nReady! Ask questions about your docs. Type 'exit' to quit.\n")
    while True:
        question = input("You: ")
        if question.lower() == "exit":
            break
        print(f"\nAnswer: {ask(question, collection)}\n")