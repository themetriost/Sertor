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
from sertor_core.adapters.memory.archive import MemoryArchive
from sertor_core.config.settings import Settings
from sertor_core.domain.entities import EmbeddedChunk
from sertor_core.domain.memory import ArchivedSession, TranscriptTurn
from sertor_core.services.episodic_search import EpisodicSearch
from sertor_core.services.memory_semantic import SemanticMemoryHit, SemanticMemoryResults
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


def test_tool_error_detail_is_secret_scrubbed(monkeypatch, caplog):
    """A-14: the persisted `detail` of an error event is secret-scrubbed — a secret-shaped
    exception message is redacted (scrub_text) before it reaches the observability store."""
    secret = "sk-abc123DEF456ghi789"

    class _Boom:
        def search_code(self, *_a, **_k):
            raise RuntimeError(f"auth failed with key {secret}")

    _use(monkeypatch, lambda _s=None: _Boom())
    try:
        with caplog.at_level(logging.ERROR, logger="sertor_core"):
            with pytest.raises(RuntimeError):
                srv.search_code("x")
        errors = [r for r in caplog.records
                  if getattr(r, "operation", None) == "mcp.search_code.error"]
        assert errors, "expected an mcp.search_code.error event"
        detail = getattr(errors[0], "detail", "")
        assert secret not in detail        # the raw secret never reaches the store
        assert "[REDACTED]" in detail      # scrub_text placeholder applied
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


# --- E4-FEAT-010: conversation-memory read parity (memory_list / memory_show / memory_search) ----

def _seed_archive(index_dir) -> None:
    """Write two archived sessions into <index_dir>/memory.sqlite (recency: s2 newer than s1)."""
    archive = MemoryArchive(index_dir)
    archive.upsert(ArchivedSession(
        session_key="s1", project_id="proj", captured_at=1000.0, adapter_kind="claude-code",
        turns=(TranscriptTurn(0, "user", "we discussed alpha retrieval"),
               TranscriptTurn(1, "assistant", "yes, the alpha plan")),
    ))
    archive.upsert(ArchivedSession(
        session_key="s2", project_id="proj", captured_at=2000.0, adapter_kind="claude-code",
        turns=(TranscriptTurn(0, "user", "beta topic only"),),
    ))


def _use_memory(monkeypatch, reader, search) -> None:
    """Wire the memory builders + a fixed defaults Settings, clearing the memoized caches."""
    defaults = Settings.load(env_file=None)  # captured BEFORE patching (avoid self-recursion)
    monkeypatch.setattr(srv, "build_memory_reader", lambda *a, **k: reader)
    monkeypatch.setattr(srv, "build_episodic_search", lambda *a, **k: search)
    monkeypatch.setattr(srv.Settings, "load", lambda *a, **k: defaults)
    srv._memory_reader.cache_clear()
    srv._episodic.cache_clear()


def _clear_memory() -> None:
    srv._memory_reader.cache_clear()
    srv._episodic.cache_clear()


def test_memory_tools_registered():
    tools = asyncio.run(srv.mcp.list_tools())
    names = {t.name for t in tools}
    assert {"memory_list", "memory_show", "memory_search"} <= names


def test_memory_tools_disabled_when_memory_off(monkeypatch):
    """Gate off (builders return None) → explicit `disabled` on all three (not [] / not error)."""
    _use_memory(monkeypatch, reader=None, search=None)
    try:
        assert srv.memory_list()["status"] == "disabled"
        assert srv.memory_show("s1")["status"] == "disabled"
        assert srv.memory_search("alpha")["status"] == "disabled"
        assert "SERTOR_MEMORY" in srv.memory_list()["hint"]
    finally:
        _clear_memory()


def test_memory_list_returns_sessions_recency_first(monkeypatch, tmp_path):
    _seed_archive(tmp_path)
    _use_memory(monkeypatch, reader=MemoryArchive(tmp_path), search=None)
    try:
        out = srv.memory_list()
        assert out["status"] == "ok"
        keys = [s["session_key"] for s in out["sessions"]]
        assert keys == ["s2", "s1"]                        # recency-first (parity with list_recent)
        assert set(out["sessions"][0]) == {"session_key", "captured_at", "turn_count"}
        assert out["sessions"][1]["turn_count"] == 2       # s1 has two turns
    finally:
        _clear_memory()


def test_memory_show_returns_turns_or_null(monkeypatch, tmp_path):
    _seed_archive(tmp_path)
    _use_memory(monkeypatch, reader=MemoryArchive(tmp_path), search=None)
    try:
        out = srv.memory_show("s1")
        assert out["status"] == "ok"
        sess = out["session"]
        assert sess["session_key"] == "s1" and sess["adapter_kind"] == "claude-code"
        assert [t["index"] for t in sess["turns"]] == [0, 1]      # ordered
        assert sess["turns"][0]["text"] == "we discussed alpha retrieval"  # full text, not preview
        # unknown key → explicit null session, still status ok (not disabled, not error)
        assert srv.memory_show("nope") == {"status": "ok", "session": None}
    finally:
        _clear_memory()


def test_memory_search_full_text_hits(monkeypatch, tmp_path):
    _seed_archive(tmp_path)
    _use_memory(monkeypatch, reader=None, search=EpisodicSearch(tmp_path))
    try:
        out = srv.memory_search("alpha")
        assert out["status"] == "ok"
        assert out["hits"], "expected a full-text hit for 'alpha'"
        hit = out["hits"][0]
        assert hit["session_key"] == "s1"
        assert set(hit) == {"session_key", "captured_at", "role", "turn_index", "snippet", "score"}
        # a non-matching query → explicit empty hits (not disabled, not error)
        assert srv.memory_search("zzznomatch")["hits"] == []
    finally:
        _clear_memory()


def test_memory_search_does_not_log_query_in_clear(monkeypatch, tmp_path, caplog):
    """The query text must never appear in the observability events (EpisodicSearch hashes it)."""
    _seed_archive(tmp_path)
    _use_memory(monkeypatch, reader=None, search=EpisodicSearch(tmp_path))
    try:
        with caplog.at_level(logging.INFO, logger="sertor_core"):
            srv.memory_search("alpha")
        blob = " ".join(r.getMessage() for r in caplog.records)
        assert "alpha" not in blob                      # query hashed, never in clear
    finally:
        _clear_memory()


def test_memory_tools_degrade_on_absent_archive(monkeypatch, tmp_path):
    """Memory ON but no archive file yet → status ok with empty collections, no crash."""
    _use_memory(monkeypatch, reader=MemoryArchive(tmp_path), search=EpisodicSearch(tmp_path))
    try:
        assert srv.memory_list() == {"status": "ok", "sessions": []}
        assert srv.memory_search("alpha") == {"status": "ok", "hits": []}
        assert srv.memory_show("s1") == {"status": "ok", "session": None}
    finally:
        _clear_memory()


# --- E4-FEAT-013: semantic memory search via MCP (memory_search semantic=true) --------------------

class _FakeSemanticIndex:
    """Stand-in for SemanticMemorySearch: returns fixed hits, records the query text it received."""

    def __init__(self, hits=()):
        self._hits = tuple(hits)
        self.queries: list[str] = []

    def search(self, query):
        self.queries.append(query.text)
        return SemanticMemoryResults(hits=self._hits, latency_ms=0.0)


def _use_semantic(monkeypatch, index, *, memory_on: bool) -> None:
    """Wire the semantic builder + a Settings whose SERTOR_MEMORY gate matches `memory_on`."""
    if memory_on:
        monkeypatch.setenv("SERTOR_MEMORY", "true")
    else:
        monkeypatch.delenv("SERTOR_MEMORY", raising=False)
    defaults = Settings.load(env_file=None)  # captured with the gate set as requested
    monkeypatch.setattr(srv, "build_memory_semantic_index", lambda *a, **k: index)
    monkeypatch.setattr(srv.Settings, "load", lambda *a, **k: defaults)
    srv._memory_semantic.cache_clear()


def test_memory_search_semantic_disabled_when_memory_off(monkeypatch):
    """semantic=true, SERTOR_MEMORY off → disabled naming SERTOR_MEMORY (not the semantic knob)."""
    _use_semantic(monkeypatch, index=None, memory_on=False)
    try:
        out = srv.memory_search("alpha", semantic=True)
        assert out["status"] == "disabled"
        assert "SERTOR_MEMORY" in out["hint"] and "SEMANTIC" not in out["hint"]
    finally:
        srv._memory_semantic.cache_clear()


def test_memory_search_semantic_disabled_when_semantic_off(monkeypatch):
    """semantic=true, memory ON but SERTOR_MEMORY_SEMANTIC off (builder → None) → names the semantic
    knob + the backfill command, NEVER a silent fallback to full-text (parity with the CLI)."""
    _use_semantic(monkeypatch, index=None, memory_on=True)
    try:
        out = srv.memory_search("alpha", semantic=True)
        assert out["status"] == "disabled"
        assert "SERTOR_MEMORY_SEMANTIC" in out["hint"]
        assert "index-semantic" in out["hint"]
    finally:
        srv._memory_semantic.cache_clear()


def test_memory_search_semantic_hits(monkeypatch):
    """semantic=true, both gates on → delegates to the semantic index; hit shape == full-text."""
    hit = SemanticMemoryHit(session_key="s1", turn_index=1, captured_at=1000.0,
                            role="assistant", snippet="the alpha plan", score=0.9123)
    fake = _FakeSemanticIndex(hits=(hit,))
    _use_semantic(monkeypatch, index=fake, memory_on=True)
    try:
        out = srv.memory_search("alpha meaning", semantic=True)
        assert out["status"] == "ok"
        assert fake.queries == ["alpha meaning"]          # routed to the semantic index
        h = out["hits"][0]
        assert set(h) == {"session_key", "captured_at", "role", "turn_index", "snippet", "score"}
        assert h["session_key"] == "s1" and h["score"] == 0.9123
    finally:
        srv._memory_semantic.cache_clear()


def test_memory_search_semantic_empty_is_explicit(monkeypatch):
    """No match → explicit empty hits (status ok), not disabled and not an error."""
    _use_semantic(monkeypatch, index=_FakeSemanticIndex(hits=()), memory_on=True)
    try:
        assert srv.memory_search("x", semantic=True) == {"status": "ok", "hits": []}
    finally:
        srv._memory_semantic.cache_clear()


def test_memory_search_semantic_does_not_log_query_in_clear(monkeypatch, caplog):
    """The MCP tool's own event must not carry the query text (semantic branch)."""
    _use_semantic(monkeypatch, index=_FakeSemanticIndex(hits=()), memory_on=True)
    try:
        with caplog.at_level(logging.INFO, logger="sertor_core"):
            srv.memory_search("secretquery", semantic=True)
        blob = " ".join(r.getMessage() for r in caplog.records) + str(
            [getattr(r, "args", "") for r in caplog.records]
        )
        assert "secretquery" not in blob
    finally:
        srv._memory_semantic.cache_clear()


def test_memory_search_default_is_full_text(monkeypatch, tmp_path):
    """semantic defaults to false → full-text path runs, the semantic builder is NEVER called."""
    _seed_archive(tmp_path)
    calls = {"n": 0}

    def _boom(*a, **k):
        calls["n"] += 1
        return None

    monkeypatch.setattr(srv, "build_memory_semantic_index", _boom)
    _use_memory(monkeypatch, reader=None, search=EpisodicSearch(tmp_path))
    srv._memory_semantic.cache_clear()
    try:
        out = srv.memory_search("alpha")                  # no semantic arg → full-text
        assert out["status"] == "ok" and out["hits"]
        assert calls["n"] == 0                             # semantic builder untouched
    finally:
        _clear_memory()
        srv._memory_semantic.cache_clear()
