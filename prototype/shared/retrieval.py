"""Facade unica sui motori di retrieval delle Tappe 01–03, per l'Agentic RAG.

Espone funzioni-tool pulite e provider-agnostiche (search_code/docs/combined,
find_symbol/who_calls/related_docs) indipendenti dai dettagli delle singole tappe.
**Riusa** gli indici esistenti — non riscrive né reindicizza nulla.

I moduli delle tappe vivono in cartelle con nome non-pacchetto (`02-hybrid-reranking`,
`03-graphrag`), quindi vengono caricati via `importlib` dal path del file.
"""
from __future__ import annotations

import importlib.util
import sys
from functools import lru_cache
from pathlib import Path

from shared.config import settings

ROOT = Path(__file__).resolve().parent.parent


def _load(rel: str, name: str, dir_on_path: str):
    """Carica un modulo per path, mettendo la sua cartella su sys.path per gli import locali."""
    d = ROOT / dir_on_path
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_hybrid = _load("02-hybrid-reranking/hybrid.py", "t02_hybrid", "02-hybrid-reranking")
_rerank = _load("02-hybrid-reranking/rerank.py", "t02_rerank", "02-hybrid-reranking")
_gq = _load("03-graphrag/graph_query.py", "t03_graph_query", "03-graphrag")


def default_provider() -> str:
    """Provider di embedding coerente col backend: azure-large in Azure, ollama in locale."""
    return "azure-large" if settings.backend == "azure" else "ollama"


@lru_cache(maxsize=4)
def _index(provider: str):
    return _hybrid.HybridIndex(provider)


@lru_cache(maxsize=1)
def _graph():
    return _gq.CodeGraph()


def _fmt(h: dict) -> dict:
    return {"path": h["path"], "source": h["source"], "kind": h.get("kind"),
            "chunk": h.get("chunk"), "qualname": h.get("qualname"),
            "preview": h.get("preview") or " ".join(h["text"].split())[:200]}


# --------------------------------------------------------------------------- vector / hybrid
def search_code(query: str, k: int = 5, provider: str | None = None) -> list[dict]:
    """Cerca nel CODICE sorgente (hybrid BM25+dense, filtrato su `source=code`)."""
    idx = _index(provider or default_provider())
    hits = idx.search(query, k=k, pool=max(30, k * 5), mode="hybrid", source="code")
    return [_fmt(h) for h in hits]


def search_docs(query: str, k: int = 5, provider: str | None = None) -> list[dict]:
    """Cerca nella DOCUMENTAZIONE Markdown (hybrid, filtrato su `source=doc`)."""
    idx = _index(provider or default_provider())
    hits = idx.search(query, k=k, pool=max(30, k * 5), mode="hybrid", source="doc")
    return [_fmt(h) for h in hits]


def search_combined(query: str, k: int = 6, provider: str | None = None) -> list[dict]:
    """Cerca su CODICE + DOC insieme e applica il reranking (fusione cross-encoder)."""
    idx = _index(provider or default_provider())
    pool = idx.search(query, k=max(30, k * 5), pool=max(30, k * 5), mode="hybrid")
    return [_fmt(h) for h in _rerank.rerank(query, pool, k)]


# --------------------------------------------------------------------------- code graph (AST)
def find_symbol(name: str) -> list[str]:
    """Dove è DEFINITO un simbolo (classe/funzione/metodo): `path:lineno`."""
    g = _graph()
    return [g.label(n) for n in g.definitions(name)]


def who_calls(name: str) -> list[str]:
    """Chi CHIAMA un simbolo (chiamanti nel call graph)."""
    g = _graph()
    return [g.label(n) for n in g.callers(name)]


def related_docs(name: str) -> list[str]:
    """Documenti Markdown che MENZIONANO un simbolo."""
    g = _graph()
    return [g.label(n) for n in g.related_docs(name)]


# --------------------------------------------------------------------------- fusione dual-RAG
def _code_for_symbol(idx, symbol: str, limit: int = 2) -> list[dict]:
    """Chunk di CODICE il cui simbolo/qualname combacia (link via metadati, nessun embedding)."""
    out = []
    for _id, (doc, meta) in idx.by_id.items():
        if meta.get("source") == "code" and symbol in (meta.get("qualname"), meta.get("symbol")):
            out.append({"path": meta["path"], "qualname": meta.get("qualname"),
                        "start_line": meta.get("start_line"), "end_line": meta.get("end_line"),
                        "text": doc})
    return out[:limit]


def get_context(target: str, max_callers: int = 8, max_docs: int = 5,
                semantic_docs: bool = False, provider: str | None = None) -> dict:
    """**Fusione dual-RAG**: unisce in un solo bundle CODICE e DOC *collegati* per un simbolo.

    A differenza di search_code/search_docs (che restano separati) e di search_combined (che
    li *co-classifica*), qui codice e doc sono **uniti tramite il grafo** (definizione, chiamanti,
    doc che menzionano il simbolo) e i metadati dei chunk (qualname/righe). È **deterministico**
    e **senza LLM**; con `semantic_docs=True` arricchisce i doc anche per similarità (usa embedding).
    """
    g = _graph()
    idx = _index(provider or default_provider())
    defs = g.definitions(target)
    symbol = target if defs else None
    if symbol is None and semantic_docs:  # NL → simbolo via ricerca, poi espansione sul grafo
        hits = search_code(target, k=1, provider=provider)
        symbol = (hits[0].get("symbol") or hits[0].get("qualname")) if hits else None
        defs = g.definitions(symbol) if symbol else []

    docs, seen = [], set()
    if symbol:
        for lbl in (g.label(n) for n in g.related_docs(symbol)):  # link esplicito grafo (mentions)
            path = lbl.split()[0]
            if path not in seen:
                seen.add(path)
                docs.append({"path": path, "why": "grafo:mentions"})
    if semantic_docs:
        for h in search_docs(symbol or target, k=max_docs, provider=provider):
            if h["path"] not in seen:
                seen.add(h["path"])
                docs.append({"path": h["path"], "why": "semantico", "preview": h["preview"]})

    return {
        "target": target,
        "symbol": symbol,
        "definitions": [g.label(n) for n in defs],
        "code": _code_for_symbol(idx, symbol) if symbol else [],
        "callers": [g.label(n) for n in g.callers(symbol)][:max_callers] if symbol else [],
        "docs": docs[:max_docs],
    }
