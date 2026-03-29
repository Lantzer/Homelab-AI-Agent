"""
Agent: Orchestrates routing, tool execution, and response generation.

Flow:
  1. route(question)        — LLM decides which tools to use
  2. execute_tools(...)     — runs selected tools, gathers context
  3. build_system_prompt()  — assembles context into a system message
  4. call_llm()             — sends history + question to Ollama, gets answer
"""

import ollama
from Core.router import route, execute_tools
from Core.tools import ToolResult

# Number of conversation turns (user + assistant pairs) to retain.
# Older turns are dropped once this limit is exceeded.
MAX_HISTORY_TURNS = 10


def build_system_prompt(context_results: list[ToolResult]) -> str:
    context = ""
    for result in context_results:
        if result.content:
            label = result.tool.replace("_", " ").title()
            context += f"--- Source: {label} ---\n{result.content}\n\n"

    if not context:
        context = "No relevant context was retrieved from available sources.\n"

    return f"""You are an expert homelab assistant. Answer the user's question using ONLY the context provided below. Do not add information from your general knowledge that is not supported by the context.

Guidelines:
- Answer strictly from the context — if something isn't mentioned there, say so
- Do not invent services, hardware, or configs that are not in the context
- If you can identify inefficiencies or improvements based on what IS in the context, mention them
- Be concise and avoid repeating the same information

CONTEXT:
{context}"""


def call_llm(system_prompt: str, question: str, history: list[dict]) -> str:
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": question})
    try:
        response = ollama.chat(model="llama3.2", messages=messages)
        return response["message"]["content"]
    except ollama.ResponseError as e:
        return f"Ollama error: {e}"
    except Exception as e:
        return f"Unexpected error contacting Ollama: {e}"


def trim_history(history: list[dict]) -> list[dict]:
    """Keep only the last MAX_HISTORY_TURNS pairs (user + assistant = 2 messages per turn)."""
    max_messages = MAX_HISTORY_TURNS * 2
    return history[-max_messages:] if len(history) > max_messages else history


def ask(question: str, history: list[dict]) -> dict:
    """
    Main agent entry point. Returns a structured dict:
      answer     — the LLM's response text
      tools_used — list of tool names that succeeded
      commands   — list of command strings (if command tool was selected)
      reasoning  — router's one-sentence explanation
      history    — updated conversation history (trimmed to MAX_HISTORY_TURNS)
    """
    routing = route(question)
    results = execute_tools(question, routing)

    commands = [r.content for r in results if r.tool == "command" and bool(r.content)]
    context_results = [r for r in results if r.tool != "command"]

    system_prompt = build_system_prompt(context_results)
    answer = call_llm(system_prompt, question, history)

    updated_history = trim_history(history + [
        {"role": "user",      "content": question},
        {"role": "assistant", "content": answer},
    ])

    return {
        "answer": answer,
        "tools_used": [r.tool for r in results if not r.error],
        "commands": commands,
        "reasoning": routing.get("reasoning", ""),
        "history": updated_history,
    }


if __name__ == "__main__":
    history = []
    print("\nReady! Ask questions about your homelab. Type 'exit' to quit.\n")
    while True:
        question = input("You: ").strip()
        if not question:
            continue
        if question.lower() == "exit":
            break
        result = ask(question, history)
        history = result["history"]
        print(f"\nAnswer: {result['answer']}")
        if result["commands"]:
            print(f"Command: {result['commands'][0]}")
        print(f"(Tools used: {', '.join(result['tools_used'])})\n")
