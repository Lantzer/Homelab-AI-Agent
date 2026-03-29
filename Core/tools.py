"""
Tool implementations for the agentic pipeline.

Each tool retrieves context from a different source and returns a ToolResult.
"""

import os
import requests
from dataclasses import dataclass

from chromadb.errors import NotFoundError

from Core.embeddings import load_index, query_index


@dataclass
class ToolResult:
    tool: str        # "homelab_rag" | "supporting_rag" | "web_search" | "command"
    content: str     # prose context or command string
    error: str = ""
    reasoning: str = ""


def run_homelab_rag(question: str) -> ToolResult:
    """Query the user's personal homelab documentation."""
    try:
        collection = load_index("homelab")
        chunks = query_index(collection, question)
        if not chunks:
            return ToolResult(tool="homelab_rag", content="", error="No relevant chunks found in homelab docs.")
        content = "\n\n".join(chunks)
        return ToolResult(tool="homelab_rag", content=content)
    except NotFoundError:
        return ToolResult(tool="homelab_rag", content="", error="No homelab documents indexed yet.")
    except Exception as e:
        return ToolResult(tool="homelab_rag", content="", error=str(e))


def run_supporting_rag(question: str) -> ToolResult:
    """Query general supporting documentation (product manuals, guides)."""
    try:
        collection = load_index("supporting")
        chunks = query_index(collection, question)
        if not chunks:
            return ToolResult(tool="supporting_rag", content="", error="No relevant chunks found in supporting docs.")
        content = "\n\n".join(chunks)
        return ToolResult(tool="supporting_rag", content=content)
    except NotFoundError:
        return ToolResult(tool="supporting_rag", content="", error="No supporting documents indexed yet.")
    except Exception as e:
        return ToolResult(tool="supporting_rag", content="", error=str(e))


def run_web_search(question: str) -> ToolResult:
    """Search the web using Tavily API."""
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        return ToolResult(tool="web_search", content="", error="TAVILY_API_KEY not set in environment.")
    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={"api_key": api_key, "query": question, "max_results": 5},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        snippets = [r.get("content", "") for r in data.get("results", []) if r.get("content")]
        if not snippets:
            return ToolResult(tool="web_search", content="", error="No results returned from web search.")
        content = "\n\n".join(snippets)
        return ToolResult(tool="web_search", content=content)
    except requests.RequestException as e:
        return ToolResult(tool="web_search", content="", error=f"Web search request failed: {e}")
    except Exception as e:
        return ToolResult(tool="web_search", content="", error=str(e))
