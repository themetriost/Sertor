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
