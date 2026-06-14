"""Test US3 — the 4 graph tools in the MCP server (FR-019..022).

With `FakeCodeGraph` (NFR-03): thin surfaces, structured errors, 3 search tools
unchanged, eager warm-up extended to the graph (lesson from PR #23 / R-7).
"""
from __future__ import annotations

import asyncio

import pytest

import sertor_mcp.server as srv
from sertor_core.domain.entities import GraphData, GraphEdge, GraphNode
from sertor_core.domain.errors import ConfigError, GraphNotFoundError
from tests.fixtures.mocks import FakeCodeGraph

CORPUS = "fake"


def _populated_graph(_settings=None) -> FakeCodeGraph:
    g = FakeCodeGraph(CORPUS)
    g.build(CORPUS, GraphData(
        nodes=(
            GraphNode("a.py", "module", "a.py", "a.py"),
            GraphNode("a.py::aiuta", "function", "aiuta", "a.py", 3, "aiuta"),
            GraphNode("a.py::Capo.lancia", "method", "lancia", "a.py", 9, "Capo.lancia"),
            GraphNode("guida.md", "doc", "guida.md", "guida.md"),
        ),
        edges=(
            GraphEdge("a.py::Capo.lancia", "a.py::aiuta", "calls"),
            GraphEdge("guida.md", "a.py::aiuta", "mentions"),
        ),
    ))
    return g


def _use(monkeypatch, factory) -> None:
    monkeypatch.setattr(srv, "build_graph_service", factory)
    monkeypatch.setattr(srv.Settings, "load", lambda *a, **k: None)
    srv._graph.cache_clear()


# --- registration and invariance (FR-019) --------------------------------------------------------

def test_seven_tools_registered():
    tools = asyncio.run(srv.mcp.list_tools())
    names = {t.name for t in tools}
    assert {"search_code", "search_docs", "search_combined"} <= names   # invariati
    assert {"find_symbol", "who_calls", "related_docs", "get_context"} <= names


# --- delegation and citable format (FR-020, contracts/mcp-graph-tools.md) -----------------------

def test_find_symbol_returns_citable_hits(monkeypatch):
    _use(monkeypatch, _populated_graph)
    try:
        out = srv.find_symbol("aiuta")
        assert out == [{"path": "a.py", "line": 3, "kind": "function",
                        "qualname": "aiuta", "ref": "a.py#aiuta"}]
    finally:
        srv._graph.cache_clear()


def test_who_calls_and_related_docs(monkeypatch):
    _use(monkeypatch, _populated_graph)
    try:
        assert [h["qualname"] for h in srv.who_calls("aiuta")] == ["Capo.lancia"]
        assert srv.related_docs("aiuta") == [{"path": "guida.md", "ref": "guida.md"}]
    finally:
        srv._graph.cache_clear()


def test_get_context_bundle_sections(monkeypatch):
    _use(monkeypatch, _populated_graph)
    try:
        out = srv.get_context("aiuta")
        assert set(out) == {"definitions", "callers", "callees", "bases", "docs"}
        assert out["callers"][0]["ref"] == "a.py#Capo.lancia"
        assert out["docs"] == ["guida.md"]
    finally:
        srv._graph.cache_clear()


def test_unknown_symbol_returns_empty_lists(monkeypatch):
    _use(monkeypatch, _populated_graph)
    try:
        assert srv.find_symbol("inesistente") == []        # explicit empty, not an error (FR-017)
    finally:
        srv._graph.cache_clear()


# --- structured errors (FR-021/FR-022) -----------------------------------------------------------

def test_graph_not_built_propagates_explicit_error(monkeypatch):
    _use(monkeypatch, lambda _s=None: FakeCodeGraph("vuoto"))
    try:
        with pytest.raises(GraphNotFoundError):
            srv.find_symbol("aiuta")                       # the server does NOT swallow it (FR-021)
    finally:
        srv._graph.cache_clear()


def test_missing_extra_propagates_actionable_error(monkeypatch):
    class _NoExtra:
        def find_symbol(self, name):
            raise ConfigError('serve l\'extra: uv add "sertor-core[graph]"', key="graph")

    _use(monkeypatch, lambda _s=None: _NoExtra())
    try:
        with pytest.raises(ConfigError):
            srv.find_symbol("aiuta")                       # DA-5: actionable error
    finally:
        srv._graph.cache_clear()


# --- extended eager warm-up (R-7, lesson from PR #23) --------------------------------------------

def test_main_warms_facade_and_graph_before_stdio_loop(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(srv, "build_facade", lambda _s=None: calls.append("facade"))
    monkeypatch.setattr(srv, "build_graph_service",
                        lambda _s=None: calls.append("graph") or _populated_graph())
    monkeypatch.setattr(srv.Settings, "load", lambda *a, **k: None)
    monkeypatch.setattr(srv, "enable_observability", lambda *a, **k: False)
    srv._facade.cache_clear()
    srv._graph.cache_clear()
    monkeypatch.setattr(srv.mcp, "run", lambda *a, **k: calls.append("run"))
    try:
        srv.main()
        assert calls[-1] == "run" and "facade" in calls and "graph" in calls
        assert calls.index("facade") < calls.index("run")
        assert calls.index("graph") < calls.index("run")
    finally:
        srv._facade.cache_clear()
        srv._graph.cache_clear()


def test_main_warmup_tolerates_missing_graph(monkeypatch):
    # Graph not built or extra absent: warm-up must NOT prevent the server from starting.
    class _Boom:
        def exists(self, corpus):
            raise ConfigError("extra assente", key="graph")

    monkeypatch.setattr(srv, "build_facade", lambda _s=None: None)
    monkeypatch.setattr(srv, "build_graph_service", lambda _s=None: _Boom())
    monkeypatch.setattr(srv.Settings, "load", lambda *a, **k: None)
    monkeypatch.setattr(srv, "enable_observability", lambda *a, **k: False)
    srv._facade.cache_clear()
    srv._graph.cache_clear()
    ran: list[bool] = []
    monkeypatch.setattr(srv.mcp, "run", lambda *a, **k: ran.append(True))
    try:
        srv.main()                                          # no exception
        assert ran == [True]
    finally:
        srv._facade.cache_clear()
        srv._graph.cache_clear()
