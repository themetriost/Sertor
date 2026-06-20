"""Test the set-based graph-navigation oracle (066, TASK-F02): pure functions, zero network.

`evaluate_graph_case`/`evaluate_graph_suite` are pure; `navigate` depends only on the `CodeGraph`
port (mocked via structural typing — no inheritance).
"""
from __future__ import annotations

import pytest

from sertor_core.domain.errors import GraphNotFoundError, GraphSuiteValidationError
from sertor_core.services.eval.graph_eval import (
    evaluate_graph_case,
    evaluate_graph_suite,
    navigate,
)
from sertor_core.services.eval.models import GraphCaseResult


class _StubGraph:
    """Structural `CodeGraph` stub: maps names to canned hits (or raises GraphNotFoundError)."""

    def __init__(self, callers=None, defs=None, *, built=True):
        self._callers = callers or {}
        self._defs = defs or {}
        self._built = built

    class _Hit:
        def __init__(self, ref):
            self.ref = ref

    def who_calls(self, name):
        if not self._built:
            raise GraphNotFoundError("graph not built", corpus="x")
        return [self._Hit(r) for r in self._callers.get(name, [])]

    def find_symbol(self, name):
        if not self._built:
            raise GraphNotFoundError("graph not built", corpus="x")
        return [self._Hit(r) for r in self._defs.get(name, [])]


A, B, C = "a.py#A", "b.py#B", "c.py#C"


def test_perfect_match():
    m = evaluate_graph_case(frozenset({A, B}), frozenset({A, B}))
    assert m.precision == 1.0 and m.recall == 1.0 and m.f1 == 1.0
    assert m.exact is True and m.missing == () and m.extra == ()


def test_partial_missing():
    m = evaluate_graph_case(frozenset({A}), frozenset({A, B}))
    assert m.precision == 1.0 and m.recall == 0.5
    assert round(m.f1, 2) == 0.67 and m.exact is False and m.missing == (B,)


def test_extra_and_missing():
    m = evaluate_graph_case(frozenset({A, C}), frozenset({A, B}))
    assert m.precision == 0.5 and m.recall == 0.5 and m.f1 == 0.5
    assert m.extra == (C,) and m.missing == (B,)


def test_both_empty_is_perfect():
    m = evaluate_graph_case(frozenset(), frozenset())
    assert m.precision == 1.0 and m.recall == 1.0 and m.f1 == 1.0 and m.exact is True


def test_got_empty_expected_nonempty():
    m = evaluate_graph_case(frozenset(), frozenset({A}))
    assert m.precision == 1.0 and m.recall == 0.0 and m.f1 == 0.0


def test_expected_empty_got_nonempty():
    m = evaluate_graph_case(frozenset({A}), frozenset())
    assert m.precision == 0.0 and m.recall == 1.0 and m.f1 == 0.0


def test_evaluate_empty_suite():
    rep = evaluate_graph_suite([])
    assert rep.cases_count == 0 and rep.mean_f1 == 0.0
    assert rep.mean_recall == 0.0 and rep.mean_precision == 0.0 and rep.by_relation == {}


def test_evaluate_suite_by_relation():
    r1 = GraphCaseResult("who_calls", "X", evaluate_graph_case(frozenset({A}), frozenset({A})))
    r2 = GraphCaseResult("defines", "Y", evaluate_graph_case(frozenset({A}), frozenset({A, B})))
    rep = evaluate_graph_suite([r1, r2])
    assert rep.cases_count == 2
    assert rep.by_relation["who_calls"] == 1.0
    assert round(rep.by_relation["defines"], 2) == 0.67


def test_navigate_who_calls():
    g = _StubGraph(callers={"X": [A, B]})
    assert navigate(g, "who_calls", "X") == frozenset({A, B})


def test_navigate_defines():
    g = _StubGraph(defs={"X": [A]})
    assert navigate(g, "defines", "X") == frozenset({A})


def test_navigate_absent_symbol_is_empty():
    g = _StubGraph(callers={})
    assert navigate(g, "who_calls", "missing") == frozenset()


def test_navigate_unsupported_relation_raises():
    g = _StubGraph()
    with pytest.raises(GraphSuiteValidationError):
        navigate(g, "related_docs", "X")


def test_navigate_graph_not_built_propagates():
    g = _StubGraph(built=False)
    with pytest.raises(GraphNotFoundError):
        navigate(g, "who_calls", "X")


def test_determinism():
    a = evaluate_graph_case(frozenset({A, C}), frozenset({A, B}))
    b = evaluate_graph_case(frozenset({A, C}), frozenset({A, B}))
    assert a == b
