"""Test US2 — code-graph composition (FR-010/FR-012/FR-029/FR-031).

The graph is ORTHOGONAL to `SERTOR_ENGINE`: dedicated factory, sink wired from `graph_enabled`,
engines and facade unchanged.
"""
from __future__ import annotations

from dataclasses import replace

from sertor_core import composition
from sertor_core.adapters.graph.networkx_graph import NetworkxCodeGraph
from sertor_core.config.settings import Settings
from sertor_core.engines.baseline import BaselineEngine
from sertor_core.engines.hybrid import HybridEngine


def _settings(tmp_path, **overrides) -> Settings:
    base = Settings(index_dir=tmp_path / ".index", corpus="graph-sel")
    return replace(base, **overrides) if overrides else base


def test_build_graph_service_returns_configured_adapter(tmp_path):
    service = composition.build_graph_service(
        _settings(tmp_path, graph_limit_definitions=3, graph_limit_relations=2,
                  graph_limit_docs=1))
    assert isinstance(service, NetworkxCodeGraph)
    assert service._limits == (3, 2, 1)                  # limits from Settings (FR-016)


def test_indexer_gets_graph_sink_only_when_enabled(tmp_path):
    with_graph = composition.build_indexer(_settings(tmp_path))
    assert with_graph._graph is not None                 # default: integrated build (DA-2)
    without = composition.build_indexer(_settings(tmp_path, graph_enabled=False))
    assert without._graph is None


def test_graph_is_orthogonal_to_engine_selection(tmp_path):
    # Changing SERTOR_ENGINE does not affect the graph and vice versa (FR-012/FR-031).
    baseline = composition.build_indexer(_settings(tmp_path, engine="baseline"))
    assert baseline._graph is not None and baseline._lexical is None
    hybrid_no_graph = composition.build_indexer(
        _settings(tmp_path, engine="hybrid", graph_enabled=False))
    assert hybrid_no_graph._graph is None and hybrid_no_graph._lexical is not None
    assert isinstance(composition.build_engine(_settings(tmp_path)), HybridEngine)
    assert isinstance(
        composition.build_engine(_settings(tmp_path, engine="baseline")), BaselineEngine)


def test_graph_service_is_exported_from_package():
    import sertor_core

    assert sertor_core.build_graph_service is composition.build_graph_service
