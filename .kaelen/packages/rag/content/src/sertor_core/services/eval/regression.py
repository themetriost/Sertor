"""Pure non-regression comparison (065, REQ-042/043).

`compare_to_baseline` is a pure, deterministic function (zero I/O, zero side effects): same input →
same `RegressionVerdict`. It compares the current `EvalReport` against the recorded `Baseline` for
every common metric (mrr + each hit@k) and flags a metric as regressed when it dropped by MORE than
the absolute tolerance. Testable without network/files (Principio V/VI).
"""
from __future__ import annotations

from sertor_core.engines.evaluation import EvalReport
from sertor_core.services.eval.models import (
    Baseline,
    FusedBaseline,
    FusedEvalReport,
    FusedRegressionVerdict,
    MetricDelta,
    RegressionVerdict,
)

# Representative hit@k for the per-surface gate (069, R-3): @3 is the standard CI signal; the full
# @k spectrum lives in the report, not in the gate (mirrors the IR `eval`/`graph_eval` choices).
_GATE_K: int = 3


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


def compare_fused_to_baseline(
    report: FusedEvalReport,
    baseline: FusedBaseline | None,
    tolerance: float,
) -> FusedRegressionVerdict:
    """Compare a fused `report` to `baseline` within `tolerance` → verdict (069, REQ-040/R-3).

    `baseline is None` → `verdict="no-baseline"` (no reference to gate against, exit 0). Otherwise a
    `MetricDelta` per surface (MRR and hit@3, the representative k) matched by `surface`, plus one
    for `union_hit_rate`: `delta = current - baseline`, `regressed = delta < -tolerance`. ANY
    regressed metric (a surface OR the union hit-rate) → `verdict="regressed"` (gate, exit 1, R-3),
    else `"pass"`. Pure and deterministic (zero I/O). Reuses `MetricDelta` (IR), no new dataclass.
    """
    if baseline is None:
        return FusedRegressionVerdict(deltas=(), tolerance=tolerance, verdict="no-baseline")

    base_by_surface = {b.surface: b for b in baseline.surfaces}
    deltas: list[MetricDelta] = []
    for surface in report.surfaces:
        base = base_by_surface.get(surface.surface)
        if base is None:
            continue  # a surface absent from the baseline has nothing to gate against
        deltas.append(
            _delta(f"{surface.surface} mrr", surface.report.mrr, base.mrr, tolerance)
        )
        if _GATE_K in surface.report.hit_rate and _GATE_K in base.hit_rate:
            deltas.append(
                _delta(
                    f"{surface.surface} hit@{_GATE_K}",
                    surface.report.hit_rate[_GATE_K],
                    base.hit_rate[_GATE_K],
                    tolerance,
                )
            )
    deltas.append(
        _delta(
            "union_hit_rate",
            report.fusion.union_hit_rate,
            baseline.union_hit_rate,
            tolerance,
        )
    )
    regressed = any(d.regressed for d in deltas)
    return FusedRegressionVerdict(
        deltas=tuple(deltas),
        tolerance=tolerance,
        verdict="regressed" if regressed else "pass",
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
