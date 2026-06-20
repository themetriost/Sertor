"""Pure non-regression comparison for graph navigation (066, REQ-032/033).

Twin of `regression.py` (IR), but the gate fires ONLY on `mean_f1` (DA-a): `mean_recall` and
`mean_precision` are reported as INFORMATIVE deltas (never `regressed=True`). `compare_graph_to_
baseline` is pure and deterministic (zero I/O): same input → same `GraphRegressionVerdict`.
"""
from __future__ import annotations

from sertor_core.services.eval.models import (
    GraphBaseline,
    GraphEvalReport,
    GraphMetricDelta,
    GraphRegressionVerdict,
)


def compare_graph_to_baseline(
    report: GraphEvalReport, baseline: GraphBaseline | None, tolerance: float
) -> GraphRegressionVerdict:
    """Compare `report` to `baseline` within `tolerance` → `GraphRegressionVerdict` (REQ-032/033).

    `baseline is None` → `verdict="no-baseline"` (no reference to gate against, exit 0). Otherwise a
    `GraphMetricDelta` per metric in order `(mean_f1, mean_recall, mean_precision)`. The gate is the
    `mean_f1` delta (`regressed = delta < -tolerance`); recall/precision are informative
    (`regressed=False`). At least one regressed metric → `"regressed"` (gate), else `"pass"`.
    """
    if baseline is None:
        return GraphRegressionVerdict(verdict="no-baseline", deltas=(), tolerance=tolerance)

    f1_delta = report.mean_f1 - baseline.mean_f1
    deltas = (
        GraphMetricDelta(
            name="mean_f1",
            current=report.mean_f1,
            baseline=baseline.mean_f1,
            delta=f1_delta,
            regressed=f1_delta < -tolerance,
        ),
        _informative("mean_recall", report.mean_recall, baseline.mean_recall),
        _informative("mean_precision", report.mean_precision, baseline.mean_precision),
    )
    regressed = any(d.regressed for d in deltas)
    return GraphRegressionVerdict(
        verdict="regressed" if regressed else "pass",
        deltas=deltas,
        tolerance=tolerance,
    )


def _informative(name: str, current: float, baseline: float) -> GraphMetricDelta:
    """A secondary metric delta that NEVER gates (DA-a): `regressed=False` always."""
    return GraphMetricDelta(
        name=name,
        current=current,
        baseline=baseline,
        delta=current - baseline,
        regressed=False,
    )
