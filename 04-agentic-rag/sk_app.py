"""Adattatore **Semantic Kernel** dell'Agentic RAG (2° dei tre framework a confronto).

Stessa logica di `orchestrator.py`/`autogen_app.py`, ma il loop di tool-use è gestito da
**Semantic Kernel** (`ChatCompletionAgent` + `FunctionChoiceBehavior.Auto`). Riusa **gli
stessi tool e lo stesso system prompt** di `tools.py` → confronto a parità: cambia solo
l'orchestratore.

Modello scelto da `RAG_BACKEND` (entry point operativo: Azure `gpt-5.4-mini`):
- azure → `AzureChatCompletion` (deployment `AZURE_OPENAI_CHAT_DEPLOYMENT`);
- local → `OpenAIChatCompletion` su client puntato all'endpoint `/v1` di Ollama.

La trace dei tool è catturata con un filtro `AUTO_FUNCTION_INVOCATION` sul kernel.

Uso:
    PYTHONPATH=. python 04-agentic-rag/sk_app.py "Cos'è OAuth2PasswordBearer e chi lo usa?" -v
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

from semantic_kernel import Kernel  # noqa: E402
from semantic_kernel.agents import ChatCompletionAgent  # noqa: E402
from semantic_kernel.connectors.ai import FunctionChoiceBehavior  # noqa: E402
from semantic_kernel.connectors.ai.open_ai import (  # noqa: E402
    AzureChatCompletion,
    OpenAIChatCompletion,
)
from semantic_kernel.filters import FilterTypes  # noqa: E402
from semantic_kernel.functions import kernel_function  # noqa: E402

import tools  # noqa: E402
from shared import retrieval  # noqa: E402
from shared.config import settings  # noqa: E402


class RagTools:
    """Plugin SK: gli stessi tool della facade, esposti come kernel function."""

    @kernel_function(description="Cerca nel CODICE sorgente (hybrid BM25+dense): implementazioni, funzioni, classi, usi.")
    def search_code(self, query: str, k: int = 5) -> str:
        return tools._stringify(retrieval.search_code(query, k))

    @kernel_function(description="Cerca nella DOCUMENTAZIONE Markdown: spiegazioni concettuali, guide, tutorial.")
    def search_docs(self, query: str, k: int = 5) -> str:
        return tools._stringify(retrieval.search_docs(query, k))

    @kernel_function(description="Cerca su CODICE + DOC insieme con reranking: quando servono implementazione e spiegazione.")
    def search_combined(self, query: str, k: int = 6) -> str:
        return tools._stringify(retrieval.search_combined(query, k))

    @kernel_function(description="Dove è DEFINITO un simbolo (classe/funzione/metodo), con path:lineno.")
    def find_symbol(self, name: str) -> str:
        return tools._stringify(retrieval.find_symbol(name))

    @kernel_function(description="Chi CHIAMA un simbolo (chiamanti nel call graph).")
    def who_calls(self, name: str) -> str:
        return tools._stringify(retrieval.who_calls(name))

    @kernel_function(description="Documenti Markdown che MENZIONANO un simbolo.")
    def related_docs(self, name: str) -> str:
        return tools._stringify(retrieval.related_docs(name))


def _service():
    if settings.backend == "azure":
        if not (settings.azure_endpoint and settings.azure_key and settings.azure_chat):
            raise RuntimeError("Backend azure: configurare AZURE_OPENAI_ENDPOINT / _API_KEY / _CHAT_DEPLOYMENT")
        base = settings.azure_endpoint.split("/openai")[0].rstrip("/")  # base resource URL
        return AzureChatCompletion(service_id="agent", deployment_name=settings.azure_chat,
                                   endpoint=base, api_key=settings.azure_key,
                                   api_version=settings.azure_api_version)
    from openai import AsyncOpenAI
    client = AsyncOpenAI(base_url=settings.ollama_host.rstrip("/") + "/v1", api_key="ollama")
    return OpenAIChatCompletion(service_id="agent", ai_model_id=settings.ollama_chat_model, async_client=client)


async def _arun(task: str, max_steps: int) -> dict:
    kernel = Kernel()
    kernel.add_plugin(RagTools(), plugin_name="rag")
    trace: list[dict] = []

    @kernel.filter(FilterTypes.AUTO_FUNCTION_INVOCATION)
    async def _record(context, next):  # noqa: A002  (firma richiesta da SK)
        try:
            args = {k: v for k, v in dict(context.arguments).items()}
        except Exception:  # noqa: BLE001
            args = {}
        trace.append({"tool": context.function.name, "args": args})
        await next(context)

    agent = ChatCompletionAgent(
        service=_service(), kernel=kernel, name="rag_agent",
        instructions=tools.SYSTEM_PROMPT,
        function_choice_behavior=FunctionChoiceBehavior.Auto())
    resp = await agent.get_response(messages=task)
    answer = str(resp.message.content) if resp and resp.message else ""

    # SK non espone i confini dei turni: approssima passi = round di tool + sintesi finale.
    steps = (len(trace) + 1) if trace else 1
    client = f"azure:{settings.azure_chat}" if settings.backend == "azure" else f"ollama:{settings.ollama_chat_model}"
    return {"answer": answer, "trace": trace, "steps": steps, "client": client}


def run(task: str, max_steps: int = 6) -> dict:
    return asyncio.run(_arun(task, max_steps))


def main() -> None:
    ap = argparse.ArgumentParser(description="Agentic RAG via Semantic Kernel")
    ap.add_argument("task")
    ap.add_argument("--max-steps", type=int, default=6)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    out = run(args.task, args.max_steps)
    if args.verbose:
        print("== tool chiamati ==")
        for t in out["trace"]:
            print(f"  - {t['tool']}({t.get('args')})")
    print("\n=== RISPOSTA (Semantic Kernel) ===\n")
    print(out["answer"])
    tool_names = ", ".join(t["tool"] for t in out["trace"]) or "nessuno"
    print(f"\n— tool chiamati: {tool_names}")


if __name__ == "__main__":
    main()
