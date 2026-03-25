# Homelab AI Agent

A local AI powered assistant that answers questions about your homelab setup. Feed it your own markdown notes, config files, PDFs, or URLs — it answers based on what's actually in your docs, not guesswork.

Runs entirely on your machine using Ollama. No API costs, no internet required once set up.

## What it does

- Ingests local markdown, text, and PDF files, or scrapes content from a URL
- Accepts a `.txt` file containing a list of sources (one per line) to batch ingest
- Chunks and indexes content into a persistent local vector database (ChromaDB)
- When you ask a question, retrieves the most relevant chunks
- Passes those chunks to a local LLM (llama3.2 via Ollama) to generate a grounded answer
- Serves a web UI for chatting with the agent and managing the index

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com) installed and running with `llama3.2` pulled

## Installation

Clone the repo and install dependencies:

```bash
git clone https://github.com/yourusername/homelab-ai-agent.git
cd homelab-ai-agent
pip install requests beautifulsoup4 chromadb ollama flask pdfplumber
```

Pull the model if you haven't already:

```bash
ollama pull llama3.2
```

## Web UI

Start the Flask server:

```bash
python app.py
```

Then open `http://localhost:5000` in your browser.

### Ask a Question

Type any question into the chat input. The agent retrieves the most relevant chunks from your indexed documents and answers based on them.

### Add Document

Enter a file path or URL to ingest a document into the index. Supported sources:

| Type | Example |
|---|---|
| Local markdown / text | `./homelab.md` |
| Local PDF | `./proxmox-guide.pdf` |
| Web page | `https://docs.docker.com/get-started/` |
| PDF URL | `https://example.com/manual.pdf` |
| Batch list (`.txt`) | `./sources.txt` |

**Batch ingestion:** Create a `.txt` file with one source per line (file paths or URLs). Entering this file in the Add Document field will ingest each item individually. Failures are reported per-item without stopping the rest.

```
./homelab.md
https://tailscale.com/kb/
./proxmox-guide.pdf
https://docs.docker.com/get-started/
```

### Delete Index

Click **Delete Index** to wipe the ChromaDB database and sources list, allowing you to start fresh.

## Command Line

Documents can also be ingested directly without the web UI:

```bash
python embeddings.py ./homelab.md
python embeddings.py https://docs.home-assistant.io/
```
