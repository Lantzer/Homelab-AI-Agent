"""
Router: decides which tools to use for a given question.

Calls the local LLM with a structured JSON prompt to select from:
  homelab_rag    — user's personal homelab docs
  supporting_rag — general product manuals and guides
  web_search     — live web search via Tavily
  command        — generate a runnable terminal command
"""

import json
import ollama

from Core.tools import ToolResult, run_homelab_rag, run_supporting_rag, run_web_search

ROUTING_PROMPT = """You are a routing agent for a homelab assistant. Given the user's question, decide which tools to use and respond with ONLY a valid JSON object.

Available tools:
- homelab_rag: Search the user's personal homelab documentation (their specific hardware, VMs, services, IPs, configs)
- supporting_rag: Search general product manuals and guides (router docs, NAS docs, software documentation)
- web_search: Search the internet for current information, software versions, or topics not in local docs
- command: Generate a terminal command the user can run to answer or act on their question

Rules:
- Always include at least one tool in the "tools" array
- Use homelab_rag when the question references "my", "I", "currently", or is about the user's specific setup
- NEVER combine homelab_rag with web_search — if the question is about the user's setup, homelab_rag alone is correct, if there is not
 enough content known about a user's setup to answer a question, state it.
- Use supporting_rag when the question is about how a specific product or software works generically
- Use web_search ONLY when the question cannot be answered from local docs (e.g. latest software versions, external troubleshooting)
- Include command when the user is asking how to do something actionable on a Linux/Unix system

Respond with ONLY this JSON structure (no markdown, no explanation):
{
  "tools": ["tool_name"],
  "command": "the shell command if command tool is selected, otherwise null",
  "reasoning": "one sentence explaining your choice"
}

Question: """


def route(question: str) -> dict:
    """
    Ask the LLM which tools to use for this question.
    Returns a dict with keys: tools (list), command (str|None), reasoning (str).
    """
    prompt = ROUTING_PROMPT + question

    try:
        response = ollama.chat(
            model="llama3.2",
            messages=[{"role": "user", "content": prompt}],
            format="json",
        )
        raw = response["message"]["content"] # json message response
        routing = json.loads(raw) # make it a json object to use json mapping

        # Validate structure
        if not isinstance(routing.get("tools"), list) or not routing["tools"]:
            raise ValueError("Invalid tools list in routing response")

        # Ensure only known tools are included
        valid_tools = {"homelab_rag", "supporting_rag", "web_search", "command"}
        routing["tools"] = [t for t in routing["tools"] if t in valid_tools] #if t is a valid tool, keep it in the tools table, else get rid of it
        if not routing["tools"]:
            raise ValueError("No valid tools in routing response")

        routing.setdefault("command", None)
        routing.setdefault("reasoning", "")
        return routing

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        # Try stripping markdown fences and retry
        try:
            raw = response["message"]["content"]
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            routing = json.loads(cleaned.strip())
            routing.setdefault("tools", ["homelab_rag", "supporting_rag"])
            routing.setdefault("command", None)
            routing.setdefault("reasoning", "")
            return routing
        except Exception as e2:
            print(f"Router fallback triggered: initial error: {e} | fence-strip retry error: {e2}. Defaulting to homelab_rag + supporting_rag.")
        return {"tools": ["homelab_rag", "supporting_rag"], "command": None, "reasoning": "fallback"}

    except Exception as e:
        print(f"Router error: {e}. Defaulting to homelab_rag + supporting_rag.")
        return {"tools": ["homelab_rag", "supporting_rag"], "command": None, "reasoning": "fallback"}


def execute_tools(question: str, routing: dict) -> list[ToolResult]:
    """
    Execute each tool selected by the router and return a list of ToolResults.
    """
    results = []
    tool_map = {
        "homelab_rag": lambda q: run_homelab_rag(q),
        "supporting_rag": lambda q: run_supporting_rag(q),
        "web_search": lambda q: run_web_search(q),
    }

    for tool_name in routing.get("tools", []):
        if tool_name == "command":
            # Command string comes from the router, not a separate execution
            cmd = routing.get("command") or ""
            reasoning = routing.get("reasoning", "")
            results.append(ToolResult(
                tool="command",
                content=cmd,
                error=f"No command provided. Reasoning: {reasoning}" if not cmd else "",
                reasoning=reasoning,
            ))
        elif tool_name in tool_map:
            results.append(tool_map[tool_name](question))

    return results
