"""Adattatore **LangGraph** dell'Agentic RAG (3° dei tre framework a confronto).

Stessa logica di `orchestrator.py`/`autogen_app.py`/`sk_app.py`, ma il loop di tool-use è il
ReAct agent prebuilt di **LangGraph** (`create_react_agent`). Riusa **gli stessi tool e lo
stesso system prompt** di `tools.py` → confronto a parità.

Modello via `RAG_BACKEND` (entry point operativo: Azure `gpt-5.4-mini`):
- azure → `AzureChatOpenAI` (deployment `AZURE_OPENAI_CHAT_DEPLOYMENT`);
- local → `ChatOpenAI` puntato all'endpoint `/v1` di Ollama.

Uso:
    PYTHONPATH=. python 04-agentic-rag/langgraph_app.py "Cos'è OAuth2PasswordBearer e chi lo usa?" -v
"""
from __future__ import annotations

import argparse
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
for _p in (HERE, HERE.parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from langchain_core.tools import tool  # noqa: E402
from langchain_openai import AzureChatOpenAI, ChatOpenAI  # noqa: E402
from langgraph.prebuilt import create_react_agent  # noqa: E402

import tools  # noqa: E402
from shared import retrieval  # noqa: E402
from shared.config import settings  # noqa: E402


@tool
def search_code(query: str, k: int = 5) -> str:
    """Cerca nel CODICE sorgente (hybrid BM25+dense): implementazioni, funzioni, classi, usi."""
    return tools._stringify(retrieval.search_code(query, k))


@tool
def search_docs(query: str, k: int = 5) -> str:
    """Cerca nella DOCUMENTAZIONE Markdown: spiegazioni concettuali, guide, tutorial."""
    return tools._stringify(retrieval.search_docs(query, k))


@tool
def search_combined(query: str, k: int = 6) -> str:
    """Cerca su CODICE + DOC insieme con reranking: quando servono implementazione e spiegazione."""
    return tools._stringify(retrieval.search_combined(query, k))


@tool
def find_symbol(name: str) -> str:
    """Dove è DEFINITO un simbolo (classe/funzione/metodo), con path:lineno."""
    return tools._stringify(retrieval.find_symbol(name))


@tool
def who_calls(name: str) -> str:
    """Chi CHIAMA un simbolo (chiamanti nel call graph)."""
    return tools._stringify(retrieval.who_calls(name))


@tool
def related_docs(name: str) -> str:
    """Documenti Markdown che MENZIONANO un simbolo."""
    return tools._stringify(retrieval.related_docs(name))


_TOOLS = [search_code, search_docs, search_combined, find_symbol, who_calls, related_docs]


def _model():
    if settings.backend == "azure":
        if not (settings.azure_endpoint and settings.azure_key and settings.azure_chat):
            raise RuntimeError("Backend azure: configurare AZURE_OPENAI_ENDPOINT / _API_KEY / _CHAT_DEPLOYMENT")
        base = settings.azure_endpoint.split("/openai")[0].rstrip("/")  # base resource URL
        return AzureChatOpenAI(azure_endpoint=base, azure_deployment=settings.azure_chat,
                               api_version=settings.azure_api_version, api_key=settings.azure_key,
                               temperature=0)
    return ChatOpenAI(base_url=settings.ollama_host.rstrip("/") + "/v1", api_key="ollama",
                      model=settings.ollama_chat_model, temperature=0)


def run(task: str, max_steps: int = 6) -> dict:
    agent = create_react_agent(_model(), _TOOLS, prompt=tools.SYSTEM_PROMPT)
    result = agent.invoke({"messages": [{"role": "user", "content": task}]},
                          config={"recursion_limit": max_steps * 3 + 5})
    msgs = result["messages"]

    trace, rounds = [], 0
    for m in msgs:
        tc = getattr(m, "tool_calls", None)
        if tc:  # un AIMessage che richiede strumenti = un round
            rounds += 1
            for c in tc:
                trace.append({"tool": c.get("name", "?"), "args": c.get("args", {})})
    last = msgs[-1]
    answer = last.content if isinstance(getattr(last, "content", ""), str) else str(getattr(last, "content", ""))
    steps = rounds + 1  # round di tool + turno di sintesi finale (come vanilla/autogen)
    client = f"azure:{settings.azure_chat}" if settings.backend == "azure" else f"ollama:{settings.ollama_chat_model}"
    return {"answer": answer, "trace": trace, "steps": steps, "client": client}


def main() -> None:
    ap = argparse.ArgumentParser(description="Agentic RAG via LangGraph")
    ap.add_argument("task")
    ap.add_argument("--max-steps", type=int, default=6)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    out = run(args.task, args.max_steps)
    if args.verbose:
        print("== tool chiamati ==")
        for t in out["trace"]:
            print(f"  - {t['tool']}({t.get('args')})")
    print("\n=== RISPOSTA (LangGraph) ===\n")
    print(out["answer"])
    tool_names = ", ".join(t["tool"] for t in out["trace"]) or "nessuno"
    print(f"\n— passi: {out['steps']} · tool chiamati: {tool_names}")


if __name__ == "__main__":
    main()
