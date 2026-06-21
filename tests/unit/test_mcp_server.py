"""Tests for the sertor-core-based MCP server (registered tools, result format, degradation).

All with mock facade/store (NFR-02): no network, no real indexes. Covers:
US1 — the 3 registered tools, stable format, filter by type;
US2 — missing index -> empty list (clean degradation) and propagation of a real error.
"""
from __future__ import annotations

import asyncio
import logging

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
    with `override=True` would pollute the global `os.environ` (e.g. `SERTOR_EMBED_PROVIDER`),
    breaking
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


def test_mono_type_tool_returns_formatted_dicts(monkeypatch):
    _use(monkeypatch, _populated_facade)
    try:
        out = srv.search_code("alpha")
        assert isinstance(out, list) and out
        assert set(out[0]) == {"path", "source", "chunk", "score", "preview"}
        assert out[0]["source"] == "code"
    finally:
        srv._facade.cache_clear()


def test_combined_returns_two_labelled_flows(monkeypatch):
    # 070: search_combined returns {"docs":[...],"code":[...]}, each element with the _fmt fields.
    _use(monkeypatch, _populated_facade)
    try:
        out = srv.search_combined("alpha")
        assert set(out) == {"docs", "code"}
        for item in out["docs"] + out["code"]:
            assert set(item) == {"path", "source", "chunk", "score", "preview"}
        assert all(r["source"] == "doc" for r in out["docs"])
        assert all(r["source"] == "code" for r in out["code"])
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
        # 070: combined returns the labelled object with empty flows (keys always present).
        assert srv.search_combined("x") == {"docs": [], "code": []}
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
    monkeypatch.setattr(srv, "enable_observability", lambda *a, **k: False)
    monkeypatch.setattr(srv, "_self_test", lambda: True)
    monkeypatch.setattr(srv.mcp, "run", lambda *a, **k: calls.append("run"))
    try:
        srv.main()
        assert calls == ["facade", "run"]
    finally:
        srv._facade.cache_clear()


def test_main_starts_server_even_if_warmup_fails(monkeypatch, capsys):
    """A config fault during warm-up (e.g. AZURE_OPENAI_* missing → EmbeddingError) must NOT
    prevent `mcp.run()`. Otherwise build_facade() crashes the process before the stdio loop and the
    client only sees an opaque "-32000 Connection closed" (regression fix, wiki/log/2026-06-17):
    the actionable error must instead surface at the first tool call.
    """
    calls: list[str] = []

    def _boom(*_a, **_k):
        raise RuntimeError("incomplete Azure configuration")

    monkeypatch.setattr(srv, "build_facade", _boom)
    monkeypatch.setattr(srv.Settings, "load", lambda *a, **k: None)
    srv._facade.cache_clear()
    monkeypatch.setattr(srv, "enable_observability", lambda *a, **k: False)
    monkeypatch.setattr(srv.mcp, "run", lambda *a, **k: calls.append("run"))
    try:
        srv.main()  # must NOT raise despite the warm-up failure
        assert calls == ["run"]  # the server still started
        assert "warm-up FAILED" in capsys.readouterr().err  # loud + actionable
    finally:
        srv._facade.cache_clear()


def test_main_wires_observability(monkeypatch):
    """`main()` calls enable_observability (else SERTOR_OBSERVABILITY is a no-op for the server)."""
    enabled: list[object] = []
    _use(monkeypatch, lambda _s=None: None)
    monkeypatch.setattr(srv, "enable_observability", lambda s: enabled.append(s) or False)
    monkeypatch.setattr(srv, "_self_test", lambda: True)
    monkeypatch.setattr(srv.mcp, "run", lambda *a, **k: None)
    try:
        srv.main()
        assert len(enabled) == 1
    finally:
        srv._facade.cache_clear()


def test_main_runs_self_test_before_stdio_loop(monkeypatch):
    """`main()` runs the end-to-end self-test BEFORE the stdio loop (catches faults at connect)."""
    calls: list[str] = []
    _use(monkeypatch, lambda _s=None: None)
    monkeypatch.setattr(srv, "enable_observability", lambda *a, **k: False)
    monkeypatch.setattr(srv, "_self_test", lambda: calls.append("self_test") or True)
    monkeypatch.setattr(srv.mcp, "run", lambda *a, **k: calls.append("run"))
    try:
        srv.main()
        assert calls == ["self_test", "run"]  # probe runs, then the loop starts
    finally:
        srv._facade.cache_clear()


# --- error signalling (observability) -----------------------------------------------------------

def test_tool_error_emits_event_and_reraises(monkeypatch, caplog):
    """A failing tool re-raises (FR-013) AND records an `mcp.<tool>.error` event (not swallowed)."""
    class _Boom:
        def search_code(self, *_a, **_k):
            raise RuntimeError("store non raggiungibile")

    _use(monkeypatch, lambda _s=None: _Boom())
    try:
        with caplog.at_level(logging.ERROR, logger="sertor_core"):
            with pytest.raises(RuntimeError):
                srv.search_code("x")
        ops = [getattr(r, "operation", None) for r in caplog.records]
        assert "mcp.search_code.error" in ops
    finally:
        srv._facade.cache_clear()


def test_combined_tool_error_emits_event_and_reraises(monkeypatch, caplog):
    """search_combined failing re-raises AND records `mcp.search_combined.error` (070)."""
    class _Boom:
        def search_combined(self, *_a, **_k):
            raise RuntimeError("store non raggiungibile")

    _use(monkeypatch, lambda _s=None: _Boom())
    try:
        with caplog.at_level(logging.ERROR, logger="sertor_core"):
            with pytest.raises(RuntimeError):
                srv.search_combined("x")
        ops = [getattr(r, "operation", None) for r in caplog.records]
        assert "mcp.search_combined.error" in ops
    finally:
        srv._facade.cache_clear()


def test_self_test_ok_on_healthy_facade(monkeypatch):
    """The self-test returns True and logs an ok event when a search completes (even empty)."""
    _use(monkeypatch, _empty_facade)  # empty index -> [] is NOT a failure
    try:
        assert srv._self_test() is True
    finally:
        srv._facade.cache_clear()


def test_self_test_is_loud_and_nonfatal_on_failure(monkeypatch, capsys, caplog):
    """A broken search makes the self-test return False (non-fatal): stderr print + error event."""
    class _Boom:
        def search_code(self, *_a, **_k):
            raise RuntimeError("http 401")

    _use(monkeypatch, lambda _s=None: _Boom())
    try:
        with caplog.at_level(logging.ERROR, logger="sertor_core"):
            assert srv._self_test() is False  # does not raise
        assert "self-test FAILED" in capsys.readouterr().err
        ops = [getattr(r, "operation", None) for r in caplog.records]
        assert "mcp.self_test.error" in ops
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
