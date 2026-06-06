"""Test del server MCP basato su sertor-core (tool registrati, formato risultati, degrado).

Tutto con facade/store mock (NFR-02): nessuna rete né indici reali. Copre:
US1 — i 3 tool registrati, formato stabile, filtro per tipo;
US2 — indice mancante -> lista vuota (degrado pulito) e propagazione di un errore reale.
"""
from __future__ import annotations

import asyncio

import pytest

import sertor_mcp.server as srv
from sertor_core.domain.entities import EmbeddedChunk
from sertor_core.services.retrieval import RetrievalFacade
from tests.fixtures.mocks import FakeEmbedder, InMemoryStore

COLL = "mcp-test"


def _populated_facade(_settings=None) -> RetrievalFacade:
    """Facade mock con un indice popolato (un chunk code + uno doc)."""
    emb = FakeEmbedder(dim=8)
    store = InMemoryStore()
    store.upsert(COLL, [
        EmbeddedChunk("a.py#0", emb.embed(["alpha code"])[0],
                      {"text": "alpha → unità con àccénti", "path": "a.py", "doc_type": "code"}),
        EmbeddedChunk("b.md#0", emb.embed(["beta doc"])[0],
                      {"text": "beta doc", "path": "b.md", "doc_type": "doc"}),
    ])
    return RetrievalFacade(FakeEmbedder(dim=8), store, COLL, default_k=5)


def _empty_facade(_settings=None) -> RetrievalFacade:
    """Facade mock SENZA indice: lo store è vuoto -> exists() == False."""
    return RetrievalFacade(FakeEmbedder(dim=8), InMemoryStore(), COLL, default_k=5)


def _use(monkeypatch, factory) -> None:
    """Sostituisce la costruzione della facade e azzera la cache memoizzata."""
    monkeypatch.setattr(srv, "build_facade", factory)
    srv._facade.cache_clear()


# --- US1 ---------------------------------------------------------------------------------------

def test_three_search_tools_registered():
    tools = asyncio.run(srv.mcp.list_tools())
    names = {t.name for t in tools}
    assert {"search_code", "search_docs", "search_combined"} <= names


def test_tool_returns_formatted_dicts(monkeypatch):
    _use(monkeypatch, _populated_facade)
    try:
        out = srv.search_combined("alpha")
        assert out
        assert set(out[0]) == {"path", "source", "chunk", "score", "preview"}
        assert out[0]["source"] in {"code", "doc"}
    finally:
        srv._facade.cache_clear()


def test_tool_filters_by_type(monkeypatch):
    _use(monkeypatch, _populated_facade)
    try:
        assert all(r["source"] == "code" for r in srv.search_code("x"))
        assert all(r["source"] == "doc" for r in srv.search_docs("x"))
    finally:
        srv._facade.cache_clear()


def test_preview_is_truncated(monkeypatch):
    """Anteprima troncata oltre la soglia, con marcatore (FR-011)."""
    long_text = "parola " * 200
    emb = FakeEmbedder(dim=8)
    store = InMemoryStore()
    store.upsert(COLL, [EmbeddedChunk(
        "big.py#0", emb.embed(["big"])[0],
        {"text": long_text, "path": "big.py", "doc_type": "code"},
    )])
    _use(monkeypatch, lambda _s=None: RetrievalFacade(FakeEmbedder(8), store, COLL, default_k=5))
    try:
        out = srv.search_code("big")
        assert out and len(out[0]["preview"]) <= srv._PREVIEW + 1  # +1 = marcatore "…"
        assert out[0]["preview"].endswith("…")
    finally:
        srv._facade.cache_clear()


# --- US2 ---------------------------------------------------------------------------------------

def test_missing_index_returns_empty_without_crash(monkeypatch):
    """Indice assente -> lista vuota + (warning loggato dal core), nessuna eccezione (FR-012)."""
    _use(monkeypatch, _empty_facade)
    try:
        assert srv.search_code("x") == []
        assert srv.search_docs("x") == []
        assert srv.search_combined("x") == []  # il server resta invocabile dopo
    finally:
        srv._facade.cache_clear()


def test_internal_error_propagates_then_server_recovers(monkeypatch):
    """Un errore reale del motore NON viene inghiottito (FR-013); dopo, il server torna usabile."""
    class _Boom:
        def search_code(self, *_a, **_k):
            raise RuntimeError("store non raggiungibile")

    _use(monkeypatch, lambda _s=None: _Boom())
    try:
        with pytest.raises(RuntimeError):
            srv.search_code("x")
    finally:
        srv._facade.cache_clear()

    # Ripristino di una facade sana: le chiamate successive funzionano (server vivo).
    _use(monkeypatch, _populated_facade)
    try:
        assert isinstance(srv.search_code("x"), list)
    finally:
        srv._facade.cache_clear()
