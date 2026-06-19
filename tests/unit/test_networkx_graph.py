"""Test US1/US2 — `NetworkxCodeGraph` adapter: JSON build (no extra), navigation (with extra).

The two absence semantics (FR-007/FR-017), the versioned artifact `sertor.graph/1` (FR-005),
the `graph_build`/`graph_query` events (FR-026/027). No network.
"""
from __future__ import annotations

import json
import logging
import os
import sys

import pytest

from sertor_core.adapters.graph.networkx_graph import NetworkxCodeGraph
from sertor_core.domain.entities import GraphData, GraphEdge, GraphNode
from sertor_core.domain.errors import ConfigError, GraphNotFoundError

CORPUS = "demo"


def _data() -> GraphData:
    nodes = (
        GraphNode("mod.py", "module", "mod.py", "mod.py"),
        GraphNode("mod.py::Base", "class", "Base", "mod.py", 1, "Base"),
        GraphNode("mod.py::Greeter", "class", "Greeter", "mod.py", 5, "Greeter"),
        GraphNode("mod.py::Greeter.salute", "method", "salute", "mod.py", 6, "Greeter.salute"),
        GraphNode("mod.py::aiuta", "function", "aiuta", "mod.py", 10, "aiuta"),
        GraphNode("guida.md", "doc", "guida.md", "guida.md"),
    )
    edges = (
        GraphEdge("mod.py", "mod.py::Base", "contains"),
        GraphEdge("mod.py", "mod.py::Greeter", "contains"),
        GraphEdge("mod.py::Greeter", "mod.py::Greeter.salute", "contains"),
        GraphEdge("mod.py::Greeter.salute", "mod.py::aiuta", "calls"),
        GraphEdge("mod.py::Greeter", "mod.py::Base", "inherits"),
        GraphEdge("guida.md", "mod.py::aiuta", "mentions"),
    )
    return GraphData(nodes=nodes, edges=edges, coverage=(("python", ("calls",)),))


def _data_aiuta_line(line: int) -> GraphData:
    base = _data()
    nodes = tuple(
        GraphNode(n.id, n.kind, n.name, n.path, line, n.qualname) if n.name == "aiuta" else n
        for n in base.nodes
    )
    return GraphData(nodes=nodes, edges=base.edges, coverage=base.coverage)


def _graph(tmp_path, *, build: bool = True) -> NetworkxCodeGraph:
    g = NetworkxCodeGraph(tmp_path, CORPUS)
    if build:
        g.build(CORPUS, _data())
    return g


# --- build and artifact (FR-005/FR-008, US1) ----------------------------------------------------

def test_build_writes_versioned_json_without_networkx(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "networkx", None)   # BUILD does not require the extra (G1)
    _graph(tmp_path)
    artifact = tmp_path / "graph" / f"{CORPUS}.json"
    assert artifact.exists()
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    assert payload["format"] == "sertor.graph/1"
    assert payload["corpus"] == CORPUS
    assert payload["coverage"] == {"python": ["calls"]}
    assert len(payload["nodes"]) == 6 and len(payload["edges"]) == 6


def test_build_is_idempotent_and_atomic(tmp_path):
    g = _graph(tmp_path)
    artifact = tmp_path / "graph" / f"{CORPUS}.json"
    first = artifact.read_text(encoding="utf-8")
    g.build(CORPUS, _data())
    assert artifact.read_text(encoding="utf-8") == first  # same input → same artifact
    leftovers = [p for p in (tmp_path / "graph").iterdir() if p.suffix != ".json"]
    assert leftovers == []                                # no leftover tmp files (atomic)


def test_load_reloads_when_artifact_rewritten_on_disk(tmp_path):
    # A graph cached in memory must not go stale when the artifact is rebuilt by another writer
    # (e.g. a re-index in a separate process): the next query reloads via the artifact's identity.
    reader = NetworkxCodeGraph(tmp_path, CORPUS)
    reader.build(CORPUS, _data())                       # aiuta at line 10
    assert reader.find_symbol("aiuta")[0].line == 10    # caches the line-10 graph
    # "another process" rewrites the same artifact with aiuta at a different line
    NetworkxCodeGraph(tmp_path, CORPUS).build(CORPUS, _data_aiuta_line(99))
    art = tmp_path / "graph" / f"{CORPUS}.json"
    bump = art.stat().st_mtime_ns + 1_000_000_000       # force a distinct mtime (coarse-clock safe)
    os.utime(art, ns=(bump, bump))
    assert reader.find_symbol("aiuta")[0].line == 99    # reloaded from disk, not the stale 10


def test_build_event_emitted_by_adapter(tmp_path, caplog):
    with caplog.at_level(logging.INFO, logger="sertor_core"):
        _graph(tmp_path)
    events = [r for r in caplog.records if getattr(r, "operation", "") == "graph_build"]
    assert events, "missing graph_build event (FR-026, fix analyze I1)"
    rec = events[-1]
    for field in ("corpus", "graph_path", "nodes_by_kind", "edges_by_type", "elapsed_ms"):
        assert hasattr(rec, field), field
    assert rec.nodes_by_kind["class"] == 2 and rec.edges_by_type["calls"] == 1


def test_exists_and_reset_are_idempotent(tmp_path):
    g = _graph(tmp_path)
    assert g.exists(CORPUS)
    g.reset(CORPUS)
    g.reset(CORPUS)  # absent = no-op
    assert not g.exists(CORPUS)


# --- the two absence semantics (FR-007/FR-017) ---------------------------------------------------

def test_query_without_graph_raises_explicit_error(tmp_path):
    g = _graph(tmp_path, build=False)
    with pytest.raises(GraphNotFoundError):
        g.find_symbol("aiuta")


def test_unknown_symbol_returns_explicit_empty(tmp_path):
    g = _graph(tmp_path)
    assert g.find_symbol("inesistente") == []
    assert g.who_calls("inesistente") == []
    assert g.related_docs("inesistente") == []
    bundle = g.get_context("inesistente")
    assert bundle.definitions == () and bundle.callers == ()


def test_unknown_format_raises_config_error(tmp_path):
    _graph(tmp_path)
    artifact = tmp_path / "graph" / f"{CORPUS}.json"
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["format"] = "sconosciuto/9"
    artifact.write_text(json.dumps(payload), encoding="utf-8")
    fresh = NetworkxCodeGraph(tmp_path, CORPUS)
    with pytest.raises(ConfigError):
        fresh.find_symbol("aiuta")


def test_query_without_extra_raises_actionable_config_error(tmp_path, monkeypatch):
    _graph(tmp_path)                                       # build ok without extra
    monkeypatch.setitem(sys.modules, "networkx", None)     # simulate absent extra (DA-5)
    fresh = NetworkxCodeGraph(tmp_path, CORPUS)
    with pytest.raises(ConfigError) as exc:
        fresh.find_symbol("aiuta")
    assert "sertor-core[graph]" in str(exc.value)


# --- navigation (US2: FR-013..018) ---------------------------------------------------------------

def test_find_symbol_returns_citable_hits(tmp_path):
    hits = _graph(tmp_path).find_symbol("aiuta")
    assert len(hits) == 1
    hit = hits[0]
    assert (hit.path, hit.line, hit.kind, hit.qualname) == ("mod.py", 10, "function", "aiuta")
    assert hit.ref == "mod.py#aiuta"                       # citable (FR-018)


def test_who_calls_follows_calls_edges(tmp_path):
    hits = _graph(tmp_path).who_calls("aiuta")
    assert [h.qualname for h in hits] == ["Greeter.salute"]


def test_related_docs_follows_mentions(tmp_path):
    assert _graph(tmp_path).related_docs("aiuta") == ["guida.md"]


def test_get_context_bundle_with_limits(tmp_path):
    g = NetworkxCodeGraph(tmp_path, CORPUS, limits=(10, 8, 8))
    g.build(CORPUS, _data())
    bundle = g.get_context("Greeter")
    assert [h.qualname for h in bundle.definitions] == ["Greeter"]
    assert [h.qualname for h in bundle.bases] == ["Base"]          # base classes (FR-016)
    salute = g.get_context("salute")
    assert [h.qualname for h in salute.callees] == ["aiuta"]       # outgoing calls
    tight = NetworkxCodeGraph(tmp_path, CORPUS, limits=(10, 0, 0))
    assert tight.get_context("aiuta").callers == ()                # limits respected


def test_query_event_emitted(tmp_path, caplog):
    g = _graph(tmp_path)
    with caplog.at_level(logging.INFO, logger="sertor_core"):
        g.who_calls("aiuta")
    events = [r for r in caplog.records if getattr(r, "operation", "") == "graph_query"]
    assert events, "missing graph_query event (FR-027)"
    rec = events[-1]
    assert rec.graph_operation == "who_calls" and rec.symbol == "aiuta" and rec.results == 1
    assert hasattr(rec, "elapsed_ms")


def test_results_are_deterministic(tmp_path):
    g = _graph(tmp_path)
    assert g.find_symbol("salute") == g.find_symbol("salute")
    assert g.who_calls("aiuta") == g.who_calls("aiuta")
