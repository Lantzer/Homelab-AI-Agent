# Homelab AI Agent

A local AI powered assistant that answers questions about your homelab setup. Feed it your own markdown notes and config files, point it at external docs, and ask it questions — it answers based on what's actually in your docs, not guesswork.

Runs entirely on your machine using Ollama. No API costs, no internet required once set up.

## What it does

- Reads local markdown/text files or scrapes docs from a URL
- Chunks and indexes the content into a local vector database (ChromaDB)
- When you ask a question, retrieves the most relevant chunks
- Passes those chunks to a local LLM (llama3.2 via Ollama) to generate an answer with relevant context from the content it indexed
- Answers are grounded in your actual documents, rather than generic knowledge or guesswork

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com) installed and running with `llama3.2` pulled

## Installation

Clone the repo and install dependencies:

```bash
git clone https://github.com/yourusername/homelab-ai-agent.git
cd homelab-ai-agent
pip install requests beautifulsoup4 chromadb ollama python-dotenv
```

Pull the model if you haven't already:

```bash
ollama pull llama3.2
```

## Usage

Point it at a local markdown file:

```bash
python agent.py homelab.md
```

Or a live docs URL:

```bash
python agent.py https://docs.home-assistant.io/
```

Then just start asking questions:

```
Ready! Ask questions about your docs. Type 'exit' to quit.

You: How do I add a new Docker container?
Answer: ...

You: exit
```
