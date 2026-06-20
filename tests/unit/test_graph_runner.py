"""Test the graph-navigation runner (066, TASK-F06): run, event privacy, ref validation.

`CodeGraph` is mocked via structural typing (no inheritance, no networkx). The event must be
metrics-only (RNF-3): no target/ref/missing/extra.
"""
from __future__ import annotations

from sertor_core.domain.errors import GraphNotFoundError
from sertor_core.services.eval import graph_runner
from sertor_core.services.eval.graph_runner import (
    emit_graph_eval_event,
    run_graph_evaluation,
    validate_refs,
)
from sertor_core.services.eval.models import (
    EvalSuite,
    GraphCase,
    GraphRegressionVerdict,
)


class _StubGraph:
    def __init__(self, callers=None, defs=None, *, built=True):
        self._callers = callers or {}
        self._defs = defs or {}
        self._built = built

    class _Hit:
        def __init__(self, ref):
            self.ref = ref

    def who_calls(self, name):
        if not self._built:
            raise GraphNotFoundError("not built", corpus="x")
        return [self._Hit(r) for r in self._callers.get(name, [])]

    def find_symbol(self, name):
        if not self._built:
            raise GraphNotFoundError("not built", corpus="x")
        return [self._Hit(r) for r in self._defs.get(name, [])]


def test_run_computes_metrics():
    g = _StubGraph(callers={"X": ["a.py#A", "b.py#B"]}, defs={"Y": ["y.py#Y"]})
    suite = EvalSuite(
        graph_cases=(
            GraphCase("who_calls", "X", ("a.py#A", "b.py#B")),
            GraphCase("defines", "Y", ("y.py#Y",)),
        )
    )
    rep = run_graph_evaluation(g, suite)
    assert rep.cases_count == 2 and rep.mean_f1 == 1.0
    assert rep.by_relation["who_calls"] == 1.0


def test_run_empty_suite_is_honest_empty():
    g = _StubGraph()
    rep = run_graph_evaluation(g, EvalSuite())
    assert rep.cases_count == 0 and rep.mean_f1 == 0.0


def test_run_propagates_graph_not_found():
    g = _StubGraph(built=False)
    suite = EvalSuite(graph_cases=(GraphCase("who_calls", "X", ()),))
    try:
        run_graph_evaluation(g, suite)
    except GraphNotFoundError:
        return
    raise AssertionError("expected GraphNotFoundError")


def test_event_is_metrics_only(monkeypatch):
    captured = {}

    def _fake(level, op, **fields):
        captured["op"] = op
        captured["fields"] = fields

    monkeypatch.setattr(graph_runner, "log_event", _fake)
    g = _StubGraph(callers={"X": ["a.py#A"]})
    suite = EvalSuite(graph_cases=(GraphCase("who_calls", "X", ("a.py#A",)),))
    rep = run_graph_evaluation(g, suite)
    verdict = GraphRegressionVerdict(verdict="pass", deltas=(), tolerance=0.0)
    emit_graph_eval_event(rep, verdict, exact_gate=False)
    fields = captured["fields"]
    assert captured["op"] == "graph_eval"
    assert fields["relations"] == {"who_calls": 1}
    for forbidden in ("target", "ref", "missing", "extra", "got", "expected"):
        assert forbidden not in fields


def test_event_tolerance_null_on_no_baseline(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        graph_runner, "log_event", lambda level, op, **f: captured.update(f)
    )
    g = _StubGraph()
    rep = run_graph_evaluation(g, EvalSuite())
    verdict = GraphRegressionVerdict(verdict="no-baseline", deltas=(), tolerance=0.0)
    emit_graph_eval_event(rep, verdict, exact_gate=False)
    assert captured["tolerance"] is None


def test_validate_refs_graph_unavailable():
    g = _StubGraph(built=False)
    rv = validate_refs(g, "who_calls", "X", ("a.py#A",))
    assert rv.graph_available is False and rv.unverifiable == ()


def test_validate_refs_flags_unverifiable():
    g = _StubGraph(callers={"X": ["a.py#A"]})
    rv = validate_refs(g, "who_calls", "X", ("a.py#A", "z.py#Z"))
    assert rv.graph_available is True and rv.unverifiable == ("z.py#Z",)
