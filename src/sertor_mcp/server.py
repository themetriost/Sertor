"""Server MCP `sertor-rag` basato su `sertor-core`.

Espone il retrieval del nucleo come **7 tool MCP**: i 3 di ricerca (codice / doc / combinata —
col motore selezionato da `SERTOR_ENGINE`, default ibrido BM25+RRF, FEAT-004) e i 4 di
navigazione strutturale sul code-graph (`find_symbol`/`who_calls`/`related_docs`/`get_context`,
FEAT-005). Configurazione centralizzata (`.env`: provider di embeddings, backend store, corpus,
motore).

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

from sertor_core.composition import build_facade, build_graph_service
from sertor_core.config.settings import Settings
from sertor_core.domain.entities import RetrievalResult, SymbolHit
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


@lru_cache(maxsize=1)
def _graph():
    """Servizio di code-graph (FEAT-005), memoizzato come la facade — ortogonale al motore."""
    return build_graph_service(Settings.load())


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


# --- Navigazione strutturale (FEAT-005): superfici sottili sul code-graph -----------------------

def _hit_dict(hit: SymbolHit) -> dict:
    """`SymbolHit` -> dict citabile (`ref = path#qualname`, coerente con path#chunk)."""
    return {"path": hit.path, "line": hit.line, "kind": hit.kind,
            "qualname": hit.qualname, "ref": hit.ref}


@mcp.tool()
def find_symbol(name: str) -> list[dict]:
    """Dove è DEFINITO il simbolo (classe/funzione/metodo): path, riga, kind, qualname.

    Lookup esatto sul code-graph, senza retrieval per similarità. Lista vuota = simbolo
    assente dal grafo; errore esplicito = grafo non costruito (lancia un index).
    """
    hits = [_hit_dict(h) for h in _graph().find_symbol(name)]
    log_event(logging.INFO, "mcp.find_symbol", results=len(hits))
    return hits


@mcp.tool()
def who_calls(name: str) -> list[dict]:
    """CHI CHIAMA il simbolo: i chiamanti diretti nel corpus (archi `calls` del code-graph)."""
    hits = [_hit_dict(h) for h in _graph().who_calls(name)]
    log_event(logging.INFO, "mcp.who_calls", results=len(hits))
    return hits


@mcp.tool()
def related_docs(name: str) -> list[dict]:
    """Quali DOCUMENTI menzionano il simbolo (archi `mentions` doc→simbolo)."""
    docs = [{"path": p, "ref": p} for p in _graph().related_docs(name)]
    log_event(logging.INFO, "mcp.related_docs", results=len(docs))
    return docs


@mcp.tool()
def get_context(name: str) -> dict:
    """CONTESTO multi-hop del simbolo: definizioni + chiamanti + chiamate + basi + doc collegati."""
    bundle = _graph().get_context(name)
    out = {
        "definitions": [_hit_dict(h) for h in bundle.definitions],
        "callers": [_hit_dict(h) for h in bundle.callers],
        "callees": [_hit_dict(h) for h in bundle.callees],
        "bases": [_hit_dict(h) for h in bundle.bases],
        "docs": list(bundle.docs),
    }
    log_event(logging.INFO, "mcp.get_context", results=len(out["definitions"]))
    return out


def main() -> None:
    """Avvia il server MCP sul trasporto stdio.

    La facade viene costruita **prima** di avviare il loop stdio (warm-up eager): l'inizializzazione
    pigra di Chroma dentro la prima tool call ne parcheggia la risposta su Windows — il task non
    riprende finché stdin non riceve un altro evento (diagnosi 2026-06-12: prima query di sessione
    appesa indefinitamente, sbloccata solo dal cancel). Costo: ~1s all'avvio, dentro il timeout di
    connessione del client (30s). Stesso warm-up per il code-graph (FEAT-005, R-7): il caricamento
    è TOLLERANTE — grafo non costruito o extra assente non impediscono l'avvio (l'errore esplicito
    arriva alla chiamata del tool, DA-5).
    """
    _facade()
    try:
        _graph().find_symbol("__warmup__")  # carica artefatto + networkx, se disponibili
    except Exception:  # noqa: BLE001 — warm-up best-effort, mai bloccante per l'avvio
        pass
    mcp.run()


if __name__ == "__main__":
    main()
