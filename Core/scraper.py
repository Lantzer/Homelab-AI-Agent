"""
Layer 1: Fetching and parsing API documentation from a URL.

Goal: Given a URL, return clean, readable text we can later
split into chunks and feed to an AI model.
"""

import io
import requests
import sys
import pdfplumber
from bs4 import BeautifulSoup


def fetch_docs(url: str) -> str:
    """
    Fetch a documentation page or PDF from a URL and return clean text.
    """
    print(f"Fetching: {url}")

    headers = {"User-Agent": "Mozilla/5.0 (compatible; DocAgent/1.0)"}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "")
    is_pdf = "application/pdf" in content_type or url.split("?")[0].lower().endswith(".pdf")

    if is_pdf:
        text = _extract_pdf_text(io.BytesIO(response.content))
    else:
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        main = soup.find("main") or soup.find("article") or soup.find("body")
        raw = main.get_text(separator="\n")
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        text = "\n".join(lines)

    print(f"  Fetched {len(text)} characters")
    return text

def read_local_file(filepath: str) -> str:
    """
    Read a local file and return its contents as text.
    Supports .pdf, .md, and plain text files.
    """
    print(f"Reading: {filepath}")

    if filepath.lower().endswith(".pdf"):
        with open(filepath, "rb") as f:
            text = _extract_pdf_text(f)
    else:
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

    print(f"  Read {len(text)} characters")
    return text


def _extract_pdf_text(file_obj) -> str:
    pages = []
    with pdfplumber.open(file_obj) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                pages.append(page_text)
    return "\n\n".join(pages)

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Split text into overlapping chunks.
    
    Why chunks?
      - LLMs have context limits — we can't send an entire docs site at once
      - We want to retrieve only the *relevant* pieces for each question
      - Overlap ensures we don't cut a sentence in half and lose meaning
    
    Why overlap?
      - If a key sentence falls at the boundary of two chunks,
        overlap means it appears in both, so retrieval won't miss it
    """
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        # Move forward by (chunk_size - overlap) so chunks share `overlap` words
        start += chunk_size - overlap

    print(f"  Split into {len(chunks)} chunks ({chunk_size} words each, {overlap} word overlap)")
    return chunks


if __name__ == "__main__":
    # # Test it against a real, simple API docs page
    # url = "https://docs.python-requests.org/en/latest/api/"
    if len(sys.argv) < 2:
            print("Usage: python scraper.py <url>")
            sys.exit(1)
    
    source = sys.argv[1]

    # Detect if it's a local file or a URL
    if source.startswith("http"):
         text = fetch_docs(source)
    else:
        text = read_local_file(source)
    
    chunks = chunk_text(text)

    # print(f"\n--- First chunk preview ---\n")
    # print(chunks[0])
    # print(f"\n--- Second chunk preview ---\n")
    # print(chunks[1])
