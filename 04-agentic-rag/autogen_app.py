"""Adattatore **AutoGen** dell'Agentic RAG (1° dei tre framework a confronto).

Stessa logica della baseline `orchestrator.py`, ma il loop di tool-use è gestito da
**AutoGen** (`AssistantAgent`). Riusa **gli stessi tool e lo stesso system prompt** di
`tools.py` → il confronto tra framework è a parità di strumenti e di prompt; cambia solo
chi orchestra.

Il modello è scelto da `RAG_BACKEND`:
- local → client OpenAI-compatible puntato all'endpoint `/v1` di Ollama (`OLLAMA_CHAT_MODEL`);
- azure → `AzureOpenAIChatCompletionClient` (deployment `AZURE_OPENAI_CHAT_DEPLOYMENT`).

Uso:
    PYTHONPATH=. python 04-agentic-rag/autogen_app.py "Cos'è OAuth2PasswordBearer e chi lo usa?" -v
"""
from __future__ import annotations

import argparse
import asyncio
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
for _p in (HERE, HERE.parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from autogen_agentchat.agents import AssistantAgent  # noqa: E402
from autogen_ext.models.openai import (  # noqa: E402
    AzureOpenAIChatCompletionClient,
    OpenAIChatCompletionClient,
)

import tools  # noqa: E402  (modulo locale: TOOLS schema-agnostici, dispatch, system prompt)
from shared import retrieval  # noqa: E402
from shared.config import settings  # noqa: E402

# AutoGen richiede il model_info per i modelli che non conosce (qwen3, gpt-5.4-mini, ...).
_MODEL_INFO = {"vision": False, "function_calling": True, "json_output": False,
               "family": "unknown", "structured_output": False, "multiple_system_messages": True}


def _model_client():
    if settings.backend == "azure":
        if not (settings.azure_endpoint and settings.azure_key and settings.azure_chat):
            raise RuntimeError("Backend azure: configurare AZURE_OPENAI_ENDPOINT / _API_KEY / _CHAT_DEPLOYMENT")
        base = settings.azure_endpoint.split("/openai")[0].rstrip("/")  # base resource URL
        return AzureOpenAIChatCompletionClient(
            azure_endpoint=base, azure_deployment=settings.azure_chat, model=settings.azure_chat,
            api_version=settings.azure_api_version, api_key=settings.azure_key, model_info=_MODEL_INFO)
    # locale: Ollama espone un'API OpenAI-compatible su /v1 (con tool-calling)
    return OpenAIChatCompletionClient(
        model=settings.ollama_chat_model, base_url=settings.ollama_host.rstrip("/") + "/v1",
        api_key="ollama", model_info=_MODEL_INFO)


# Tool come callable Python: AutoGen genera lo schema da firma + docstring.
# I wrapper riusano la facade condivisa e il formatter di tools.py.
def search_code(query: str, k: int = 5) -> str:
    """Cerca nel CODICE sorgente (hybrid BM25+dense): implementazioni, funzioni, classi, usi."""
    return tools._stringify(retrieval.search_code(query, k))


def search_docs(query: str, k: int = 5) -> str:
    """Cerca nella DOCUMENTAZIONE Markdown: spiegazioni concettuali, guide, tutorial."""
    return tools._stringify(retrieval.search_docs(query, k))


def search_combined(query: str, k: int = 6) -> str:
    """Cerca su CODICE + DOC insieme con reranking: quando servono implementazione e spiegazione."""
    return tools._stringify(retrieval.search_combined(query, k))


def find_symbol(name: str) -> str:
    """Dove è DEFINITO un simbolo (classe/funzione/metodo), con path:lineno."""
    return tools._stringify(retrieval.find_symbol(name))


def who_calls(name: str) -> str:
    """Chi CHIAMA un simbolo (chiamanti nel call graph)."""
    return tools._stringify(retrieval.who_calls(name))


def related_docs(name: str) -> str:
    """Documenti Markdown che MENZIONANO un simbolo."""
    return tools._stringify(retrieval.related_docs(name))


_TOOL_FNS = [search_code, search_docs, search_combined, find_symbol, who_calls, related_docs]


async def _arun(task: str, max_steps: int) -> dict:
    client = _model_client()
    agent = AssistantAgent(
        name="rag_agent", model_client=client, tools=_TOOL_FNS,
        system_message=tools.SYSTEM_PROMPT, reflect_on_tool_use=True,
        max_tool_iterations=max_steps)
    result = await agent.run(task=task)
    await client.close()

    trace, answer = [], ""
    for msg in result.messages:
        content = getattr(msg, "content", None)
        if isinstance(content, list):  # eventi di tool-call
            for item in content:
                # solo le RICHIESTE (FunctionCall ha `arguments`); gli esiti d'esecuzione no.
                if hasattr(item, "arguments"):
                    trace.append({"tool": getattr(item, "name", "?"), "args": item.arguments})
        elif isinstance(content, str) and getattr(msg, "source", "") == "rag_agent":
            answer = content  # l'ultima risposta testuale dell'agente
    return {"answer": answer, "trace": trace, "client": getattr(client, "_resolved_model", "autogen")}


def run(task: str, max_steps: int = 6) -> dict:
    return asyncio.run(_arun(task, max_steps))


def main() -> None:
    ap = argparse.ArgumentParser(description="Agentic RAG via AutoGen")
    ap.add_argument("task")
    ap.add_argument("--max-steps", type=int, default=6)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    out = run(args.task, args.max_steps)
    if args.verbose:
        print("== tool chiamati ==")
        for t in out["trace"]:
            print(f"  - {t['tool']}({t.get('args')})")
    print("\n=== RISPOSTA (AutoGen) ===\n")
    print(out["answer"])
    tool_names = ", ".join(t["tool"] for t in out["trace"]) or "nessuno"
    print(f"\n— tool chiamati: {tool_names}")


if __name__ == "__main__":
    main()
