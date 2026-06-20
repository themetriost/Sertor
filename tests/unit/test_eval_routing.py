"""Per-kind routing of the eval engine (065 follow-up): symbol→graph, else→relevance engine.

Verifies the seam that makes the eval measure the *right tool* per case kind. Pure unit: fakes for
the relevance engine and the code graph, no composition/index/cloud.
"""
from __future__ import annotations

from sertor_core.domain.entities import DocType, RetrievalResult, SymbolHit
from sertor_core.services.eval.runner import RoutedEvalEngine


class _FakeEngine:
    provider = "hybrid:fake"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def query(self, query: str, k: int | None = None) -> list[RetrievalResult]:
        self.calls.append(query)
        return [RetrievalResult(text="t", path="nl/hit.py", chunk_id="c",
                                doc_type=DocType.DOC, score=0.5)]


class _FakeGraph:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def find_symbol(self, name: str) -> list[SymbolHit]:
        self.calls.append(name)
        return [SymbolHit(path="src/defs.py", line=1, kind="function", qualname=name,
                          ref=f"src/defs.py#{name}")]


def test_symbol_case_routes_to_graph_not_engine():
    engine, graph = _FakeEngine(), _FakeGraph()
    routed = RoutedEvalEngine(engine, graph, {"log_event": "symbol"})
    out = routed.query("log_event")
    assert [r.path for r in out] == ["src/defs.py"]   # the DEFINITION, from the graph
    assert graph.calls == ["log_event"]
    assert engine.calls == []                          # relevance engine NOT consulted


def test_nl_case_routes_to_engine_not_graph():
    engine, graph = _FakeEngine(), _FakeGraph()
    routed = RoutedEvalEngine(engine, graph, {"some concept": "nl"})
    out = routed.query("some concept")
    assert [r.path for r in out] == ["nl/hit.py"]
    assert engine.calls == ["some concept"]
    assert graph.calls == []


def test_unknown_kind_defaults_to_engine():
    engine, graph = _FakeEngine(), _FakeGraph()
    routed = RoutedEvalEngine(engine, graph, {})       # no kind known for the query
    routed.query("whatever")
    assert engine.calls == ["whatever"]
    assert graph.calls == []


def test_provider_marks_by_kind():
    routed = RoutedEvalEngine(_FakeEngine(), _FakeGraph(), {})
    assert "by-kind" in routed.provider and "hybrid:fake" in routed.provider
