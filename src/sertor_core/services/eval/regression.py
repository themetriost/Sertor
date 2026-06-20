"""Pure non-regression comparison (065, REQ-042/043).

`compare_to_baseline` is a pure, deterministic function (zero I/O, zero side effects): same input →
same `RegressionVerdict`. It compares the current `EvalReport` against the recorded `Baseline` for
every common metric (mrr + each hit@k) and flags a metric as regressed when it dropped by MORE than
the absolute tolerance. Testable without network/files (Principio V/VI).
"""
from __future__ import annotations

from sertor_core.engines.evaluation import EvalReport
from sertor_core.services.eval.models import Baseline, MetricDelta, RegressionVerdict


def compare_to_baseline(
    report: EvalReport, baseline: Baseline | None, tolerance: float
) -> RegressionVerdict:
    """Compare `report` to `baseline` within `tolerance` → `RegressionVerdict` (REQ-042/043).

    `baseline is None` → `verdict="no-baseline"` (no reference to gate against, exit 0). Otherwise a
    `MetricDelta` per common metric: `delta = current - baseline`, `regressed = delta < -tolerance`.
    At least one regressed metric → `verdict="regressed"` (gate, exit 1), else `"pass"`.
    """
    if baseline is None:
        return RegressionVerdict(verdict="no-baseline", deltas=(), tolerance=tolerance)

    deltas: list[MetricDelta] = []
    deltas.append(_delta("mrr", report.mrr, baseline.mrr, tolerance))
    for k in sorted(set(report.hit_rate) & set(baseline.hit_rate)):
        deltas.append(
            _delta(f"hit@{k}", report.hit_rate[k], baseline.hit_rate[k], tolerance)
        )
    regressed = any(d.regressed for d in deltas)
    return RegressionVerdict(
        verdict="regressed" if regressed else "pass",
        deltas=tuple(deltas),
        tolerance=tolerance,
    )


def _delta(name: str, current: float, baseline: float, tolerance: float) -> MetricDelta:
    delta = current - baseline
    return MetricDelta(
        name=name,
        current=current,
        baseline=baseline,
        delta=delta,
        regressed=delta < -tolerance,
    )
