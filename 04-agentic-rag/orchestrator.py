"""Orchestratore Agentic RAG — loop plan/route/retrieve/reflect/synthesize.

Versione **vanilla** (nessun framework): usa direttamente `shared.llm` con un loop di
tool-use manuale. È il riferimento/baseline contro cui confrontare gli adattatori
AutoGen / Semantic Kernel / LangGraph, che riusano gli stessi `tools` e system prompt.

Il loop: l'LLM decide quali tool chiamare → li eseguiamo → riaccodiamo i risultati →
l'LLM itera finché non risponde senza chiedere altri tool (o si esaurisce `max_steps`).
"""
from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
for _p in (HERE, HERE.parent):  # se stesso (tools) + root (shared)
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import tools  # noqa: E402  (modulo locale)
from shared.llm import get_chat_client  # noqa: E402


def run(task: str, max_steps: int = 6, backend: str | None = None,
        verbose: bool = False) -> dict:
    """Esegue il task agentico e ritorna {answer, steps, trace, client}."""
    client = get_chat_client(backend)
    messages = [{"role": "system", "content": tools.SYSTEM_PROMPT},
                {"role": "user", "content": task}]
    trace: list[dict] = []

    for step in range(1, max_steps + 1):
        resp = client.chat(messages, tools=tools.TOOLS)
        messages.append(resp.raw)
        if not resp.tool_calls:
            return {"answer": resp.content, "steps": step, "trace": trace, "client": client.name}
        for tc in resp.tool_calls:
            result = tools.call_tool(tc.name, tc.arguments)
            trace.append({"step": step, "tool": tc.name, "args": tc.arguments,
                          "result_preview": result[:200]})
            if verbose:
                print(f"  [{step}] {tc.name}({tc.arguments}) -> {result[:120].splitlines()[0] if result else ''}")
            messages.append(client.tool_result_message(tc, result))

    # Budget esaurito: forza una sintesi finale senza altri tool.
    messages.append({"role": "user",
                     "content": "Sintetizza ora la risposta finale con le citazioni, senza usare altri strumenti."})
    resp = client.chat(messages)
    return {"answer": resp.content, "steps": max_steps, "trace": trace, "client": client.name}
