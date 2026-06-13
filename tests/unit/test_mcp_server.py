"""Tests for the sertor-core-based MCP server (registered tools, result format, degradation).

All with mock facade/store (NFR-02): no network, no real indexes. Covers:
US1 — the 3 registered tools, stable format, filter by type;
US2 — missing index -> empty list (clean degradation) and propagation of a real error.
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
    """Mock facade with a populated index (one code chunk + one doc chunk)."""
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
    """Mock facade WITHOUT an index: the store is empty -> exists() == False."""
    return RetrievalFacade(FakeEmbedder(dim=8), InMemoryStore(), COLL, default_k=5)


def _use(monkeypatch, factory) -> None:
    """Replaces facade construction and clears the memoized cache.

    Also neutralises `Settings.load`: `_facade()` calls it with the default `env_file=".env"`, which
    with `override=True` would pollute the global `os.environ` (e.g. `RAG_BACKEND`), breaking
    isolation for subsequent tests. Mock factories ignore settings anyway.
    """
    monkeypatch.setattr(srv, "build_facade", factory)
    monkeypatch.setattr(srv.Settings, "load", lambda *a, **k: None)
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
    """Preview truncated beyond the threshold, with ellipsis marker (FR-011)."""
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
        assert out and len(out[0]["preview"]) <= srv._PREVIEW + 1  # +1 = "…" marker
        assert out[0]["preview"].endswith("…")
    finally:
        srv._facade.cache_clear()


# --- US2 ---------------------------------------------------------------------------------------

def test_missing_index_returns_empty_without_crash(monkeypatch):
    """Missing index -> empty list + (warning logged by core), no exception (FR-012)."""
    _use(monkeypatch, _empty_facade)
    try:
        assert srv.search_code("x") == []
        assert srv.search_docs("x") == []
        assert srv.search_combined("x") == []  # server remains callable afterwards
    finally:
        srv._facade.cache_clear()


def test_main_warms_facade_before_stdio_loop(monkeypatch):
    """`main()` builds the facade BEFORE starting the stdio loop (eager warm-up).

    Chroma's lazy init inside the first tool call stalls the response on Windows until
    stdin receives another event (hang observed on 2026-06-12): the startup warm-up is the
    contract that prevents it.
    """
    calls: list[str] = []
    _use(monkeypatch, lambda _s=None: calls.append("facade"))
    monkeypatch.setattr(srv.mcp, "run", lambda *a, **k: calls.append("run"))
    try:
        srv.main()
        assert calls == ["facade", "run"]
    finally:
        srv._facade.cache_clear()


def test_internal_error_propagates_then_server_recovers(monkeypatch):
    """A real engine error is NOT swallowed (FR-013); afterwards, the server is usable again."""
    class _Boom:
        def search_code(self, *_a, **_k):
            raise RuntimeError("store non raggiungibile")

    _use(monkeypatch, lambda _s=None: _Boom())
    try:
        with pytest.raises(RuntimeError):
            srv.search_code("x")
    finally:
        srv._facade.cache_clear()

    # Restore a healthy facade: subsequent calls work (server alive).
    _use(monkeypatch, _populated_facade)
    try:
        assert isinstance(srv.search_code("x"), list)
    finally:
        srv._facade.cache_clear()
