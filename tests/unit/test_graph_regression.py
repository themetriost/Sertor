"""Test the pure graph non-regression comparison (066, TASK-F03): zero I/O, deterministic.

The gate fires ONLY on mean_f1 (DA-a); mean_recall/mean_precision are informative deltas.
"""
from __future__ import annotations

from sertor_core.services.eval.graph_regression import compare_graph_to_baseline
from sertor_core.services.eval.models import GraphBaseline, GraphEvalReport


def _report(f1=0.80, recall=0.90, precision=0.79) -> GraphEvalReport:
    return GraphEvalReport(
        cases=(),
        mean_precision=precision,
        mean_recall=recall,
        mean_f1=f1,
        by_relation={},
        cases_count=3,
    )


def _baseline(f1=0.80, recall=0.90, precision=0.79) -> GraphBaseline:
    return GraphBaseline(
        mean_f1=f1, mean_recall=recall, mean_precision=precision, cases=3, recorded_at="t"
    )


def test_no_baseline_passes():
    v = compare_graph_to_baseline(_report(), None, 0.0)
    assert v.verdict == "no-baseline" and v.exit_code() == 0 and v.deltas == ()


def test_regression_beyond_tolerance():
    v = compare_graph_to_baseline(_report(f1=0.60), _baseline(f1=0.80), 0.0)
    assert v.verdict == "regressed" and v.exit_code() == 1


def test_within_tolerance_passes():
    v = compare_graph_to_baseline(_report(f1=0.78), _baseline(f1=0.80), 0.05)
    assert v.verdict == "pass" and v.exit_code() == 0


def test_recall_drop_does_not_gate():
    # mean_f1 stable, recall collapsed: recall is informative only (DA-a).
    v = compare_graph_to_baseline(
        _report(f1=0.80, recall=0.20), _baseline(f1=0.80, recall=0.90), 0.0
    )
    assert v.verdict == "pass"
    recall_delta = next(d for d in v.deltas if d.name == "mean_recall")
    assert recall_delta.regressed is False and recall_delta.delta < 0


def test_deltas_order_and_gate_flag():
    v = compare_graph_to_baseline(_report(f1=0.50), _baseline(f1=0.80), 0.0)
    assert [d.name for d in v.deltas] == ["mean_f1", "mean_recall", "mean_precision"]
    f1_delta = next(d for d in v.deltas if d.name == "mean_f1")
    assert f1_delta.regressed is True


def test_pure():
    a = compare_graph_to_baseline(_report(f1=0.60), _baseline(f1=0.80), 0.0)
    b = compare_graph_to_baseline(_report(f1=0.60), _baseline(f1=0.80), 0.0)
    assert a == b
