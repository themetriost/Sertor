"""Server MCP `sertor-rag` basato su `sertor-core`.

Espone la ricerca vettoriale del nucleo (codice / doc / combinata) come tool MCP. Sostituisce il
vecchio server del prototipo: usa il motore production-grade e la configurazione centralizzata
(`.env`: provider di embeddings, backend store, corpus). I tool di navigazione del grafo
(`find_symbol`/`who_calls`/`related_docs`/`get_context`) torneranno col motore GraphRAG (FEAT-005).

Avvio (stdio): di norma lo lancia il client MCP via `.mcp.json` (`python -m sertor_mcp.server`).
"""
from __future__ import annotations

from functools import lru_cache

from mcp.server.fastmcp import FastMCP

from sertor_core.composition import build_facade
from sertor_core.config.settings import Settings
from sertor_core.domain.entities import RetrievalResult

mcp = FastMCP(
    "sertor-rag",
    instructions=(
        "Retrieval su un corpus indicizzato (codice + documentazione) col motore Sertor. "
        "Usa search_code per implementazioni/simboli, search_docs per spiegazioni concettuali, "
        "search_combined quando servono entrambi. Cita sempre il file (path#chunk)."
    ),
)

_PREVIEW = 300


@lru_cache(maxsize=1)
def _facade():
    """Facade del core, costruita una volta dalla configurazione (`.env`)."""
    return build_facade(Settings.load())


def _fmt(r: RetrievalResult) -> dict:
    flat = " ".join(r.text.split())
    return {
        "path": r.path,
        "source": r.doc_type.value,
        "chunk": r.chunk_id,
        "score": round(r.score, 4),
        "preview": flat if len(flat) <= _PREVIEW else flat[:_PREVIEW] + "…",
    }


@mcp.tool()
def search_code(query: str, k: int = 5) -> list[dict]:
    """Cerca nel CODICE sorgente: implementazioni, funzioni, classi, usi."""
    return [_fmt(r) for r in _facade().search_code(query, k)]


@mcp.tool()
def search_docs(query: str, k: int = 5) -> list[dict]:
    """Cerca nella DOCUMENTAZIONE Markdown: spiegazioni, guide, decisioni, spec, wiki."""
    return [_fmt(r) for r in _facade().search_docs(query, k)]


@mcp.tool()
def search_combined(query: str, k: int = 6) -> list[dict]:
    """Cerca su CODICE + DOC insieme: quando servono implementazione e spiegazione."""
    return [_fmt(r) for r in _facade().search_combined(query, k)]


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
