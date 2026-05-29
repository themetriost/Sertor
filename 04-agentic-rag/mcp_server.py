"""Server **MCP** che espone i tool di retrieval (Tappe 01–03) a un agente Claude.

È la **superficie finale** dell'architettura target: invece di un orchestratore LLM nostro
(vanilla/AutoGen/SK/LangGraph), gli stessi tool di `shared/retrieval.py` sono offerti via
**Model Context Protocol**, così **Claude Code** (o qualunque client MCP) può usarli
nativamente come strumenti, orchestrando lui il loop.

Avvio (stdio): `PYTHONPATH=. python 04-agentic-rag/mcp_server.py`
Di norma non si lancia a mano: lo avvia il client MCP (vedi `.mcp.json` nella root del repo).

Il modello/embeddings seguono `RAG_BACKEND` del `.env` (entry point: Azure gpt-5.4-mini +
text-embedding-3-large). Le ricerche dense sono quindi a pagamento in modalità azure.
"""
from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:  # root -> shared
    sys.path.insert(0, str(HERE.parent))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from shared import retrieval  # noqa: E402

mcp = FastMCP(
    "sertor-rag",
    instructions=(
        "Tool di retrieval su una codebase (FastAPI) con codice e documentazione. "
        "Usa search_code per implementazioni/simboli, search_docs per spiegazioni concettuali, "
        "search_combined quando servono entrambi; find_symbol/who_calls/related_docs per "
        "navigare le relazioni del codice. Cita sempre i file (path#chunk o path:lineno)."
    ),
)


@mcp.tool()
def search_code(query: str, k: int = 5) -> list[dict]:
    """Cerca nel CODICE sorgente (hybrid BM25+dense): implementazioni, funzioni, classi, usi."""
    return retrieval.search_code(query, k)


@mcp.tool()
def search_docs(query: str, k: int = 5) -> list[dict]:
    """Cerca nella DOCUMENTAZIONE Markdown: spiegazioni concettuali, guide, tutorial."""
    return retrieval.search_docs(query, k)


@mcp.tool()
def search_combined(query: str, k: int = 6) -> list[dict]:
    """Cerca su CODICE + DOC insieme con reranking: quando servono implementazione e spiegazione."""
    return retrieval.search_combined(query, k)


@mcp.tool()
def find_symbol(name: str) -> list[str]:
    """Dove è DEFINITO un simbolo (classe/funzione/metodo), con path:lineno."""
    return retrieval.find_symbol(name)


@mcp.tool()
def who_calls(name: str) -> list[str]:
    """Chi CHIAMA un simbolo (chiamanti nel call graph)."""
    return retrieval.who_calls(name)


@mcp.tool()
def related_docs(name: str) -> list[str]:
    """Documenti Markdown che MENZIONANO un simbolo."""
    return retrieval.related_docs(name)


if __name__ == "__main__":
    mcp.run(transport="stdio")
