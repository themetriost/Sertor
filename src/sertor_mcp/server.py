"""Server MCP `sertor-rag` basato su `sertor-core`.

Espone la ricerca vettoriale del nucleo (codice / doc / combinata) come tool MCP. Sostituisce il
vecchio server del prototipo: usa il motore production-grade e la configurazione centralizzata
(`.env`: provider di embeddings, backend store, corpus). I tool di navigazione del grafo
(`find_symbol`/`who_calls`/`related_docs`/`get_context`) torneranno col motore GraphRAG (FEAT-005);
il reranking ibrido vero con il motore ibrido (FEAT-004).

Consumatore **sottile** (Principio I): i tool delegano alla facade di `sertor_core` e formattano
i risultati; nessuna logica di retrieval reimplementata. L'osservabilità del retrieval è già
emessa dal nucleo (la facade logga `retrieve`/`no_index`); qui si aggiunge un log per-tool.

Avvio (stdio): di norma lo lancia il client MCP via `.mcp.json` (`python -m sertor_mcp.server`).
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from functools import lru_cache

from mcp.server.fastmcp import FastMCP

from sertor_core.composition import build_facade
from sertor_core.config.settings import Settings
from sertor_core.domain.entities import RetrievalResult
from sertor_core.observability.logging import log_event

mcp = FastMCP(
    "sertor-rag",
    instructions=(
        "Retrieval su un corpus indicizzato (codice + documentazione) col motore Sertor. "
        "Usa search_code per implementazioni/simboli, search_docs per spiegazioni concettuali, "
        "search_combined quando servono entrambi. Cita sempre il file (path#chunk)."
    ),
)

# Lunghezza massima dell'anteprima testuale di un risultato: limita il payload verso il client
# (parametro di presentazione del server, non una scelta di dominio del core).
_PREVIEW = 300


@lru_cache(maxsize=1)
def _facade():
    """Facade del core, costruita una volta dalla configurazione (`.env`) e riusata."""
    return build_facade(Settings.load())


def _fmt(r: RetrievalResult) -> dict:
    """`RetrievalResult` -> dict con campi stabili; anteprima normalizzata e troncata."""
    flat = " ".join(r.text.split())
    return {
        "path": r.path,
        "source": r.doc_type.value,
        "chunk": r.chunk_id,
        "score": round(r.score, 4),
        "preview": flat if len(flat) <= _PREVIEW else flat[:_PREVIEW] + "…",
    }


def _run(
    tool: str,
    search: Callable[[str, int], list[RetrievalResult]],
    query: str,
    k: int,
) -> list[dict]:
    """Esegue una ricerca della facade, formatta i risultati ed emette un log di superficie."""
    results = [_fmt(r) for r in search(query, k)]
    log_event(logging.INFO, f"mcp.{tool}", k=k, results=len(results))
    return results


@mcp.tool()
def search_code(query: str, k: int = 5) -> list[dict]:
    """Cerca nel CODICE sorgente: implementazioni, funzioni, classi, usi."""
    return _run("search_code", _facade().search_code, query, k)


@mcp.tool()
def search_docs(query: str, k: int = 5) -> list[dict]:
    """Cerca nella DOCUMENTAZIONE Markdown: spiegazioni, guide, decisioni, spec, wiki."""
    return _run("search_docs", _facade().search_docs, query, k)


@mcp.tool()
def search_combined(query: str, k: int = 6) -> list[dict]:
    """Cerca su CODICE + DOC insieme: quando servono implementazione e spiegazione."""
    return _run("search_combined", _facade().search_combined, query, k)


def main() -> None:
    """Avvia il server MCP sul trasporto stdio.

    La facade viene costruita **prima** di avviare il loop stdio (warm-up eager): l'inizializzazione
    pigra di Chroma dentro la prima tool call ne parcheggia la risposta su Windows — il task non
    riprende finché stdin non riceve un altro evento (diagnosi 2026-06-12: prima query di sessione
    appesa indefinitamente, sbloccata solo dal cancel). Costo: ~1s all'avvio, dentro il timeout di
    connessione del client (30s).
    """
    _facade()
    mcp.run()


if __name__ == "__main__":
    main()
