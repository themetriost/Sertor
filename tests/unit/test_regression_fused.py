"""Test `compare_fused_to_baseline` (070, TASK-R07): pure non-regression gate.

Zero I/O. Covers no-baseline, per-surface MRR regression, fusion coverage regression (R-3), the
tolerance window, the «better MRR but worse coverage» case, and determinism. After 070 the surfaces
are TWO (search_code/search_docs); `search_combined` is no longer an IR surface — the fused surface
is gated only via `fusion_coverage`.
"""
from __future__ import annotations

from sertor_core.engines.evaluation import EvalReport
from sertor_core.services.eval.models import (
    FusedBaseline,
    FusedEvalReport,
    FusionReport,
    SurfaceBaseline,
    SurfaceEvalReport,
)
from sertor_core.services.eval.regression import compare_fused_to_baseline


def _report(docs_mrr: float = 0.73, coverage: float = 0.5) -> FusedEvalReport:
    def surf(name, mrr):
        return SurfaceEvalReport(
            name, EvalReport({3: 0.8}, mrr, 1, "hash")
        )

    return FusedEvalReport(
        surfaces=(
            surf("search_code", 0.64),
            surf("search_docs", docs_mrr),
        ),  # 070: two surfaces, no search_combined
        fusion=FusionReport(cases=(), coverage=coverage, cases_count=1, hit_but_not_covered=0),
        provider="hash",
    )


def _baseline(docs_mrr: float = 0.73, coverage: float = 0.5) -> FusedBaseline:
    return FusedBaseline(
        surfaces=(
            SurfaceBaseline("search_code", {3: 0.8}, 0.64),
            SurfaceBaseline("search_docs", {3: 0.8}, docs_mrr),
        ),  # 070: two surfaces, no search_combined
        fusion_coverage=coverage,
        queries=1,
        provider="hash",
        recorded_at="2026-06-21T00:00:00Z",
    )


def test_no_baseline_passes():
    v = compare_fused_to_baseline(_report(), None, 0.0)
    assert v.verdict == "no-baseline"
    assert v.exit_code() == 0


def test_surface_mrr_regression():
    v = compare_fused_to_baseline(_report(docs_mrr=0.40), _baseline(docs_mrr=0.73), 0.0)
    assert v.verdict == "regressed"
    assert v.exit_code() == 1


def test_fusion_coverage_regression():
    v = compare_fused_to_baseline(_report(coverage=0.2), _baseline(coverage=0.5), 0.0)
    assert v.verdict == "regressed"
    assert any(d.name == "fusion_coverage" and d.regressed for d in v.deltas)


def test_within_tolerance_passes():
    v = compare_fused_to_baseline(_report(docs_mrr=0.70), _baseline(docs_mrr=0.73), 0.05)
    assert v.verdict == "pass"
    assert v.exit_code() == 0


def test_all_within_tolerance_passes():
    v = compare_fused_to_baseline(_report(), _baseline(), 0.0)
    assert v.verdict == "pass"


def test_better_mrr_worse_coverage_regresses():
    # surface MRR up, fusion coverage down past tolerance → still regressed (R-3)
    v = compare_fused_to_baseline(
        _report(docs_mrr=0.90, coverage=0.2), _baseline(docs_mrr=0.73, coverage=0.5), 0.0
    )
    assert v.verdict == "regressed"


def test_deterministic():
    r, b = _report(), _baseline()
    assert compare_fused_to_baseline(r, b, 0.0) == compare_fused_to_baseline(r, b, 0.0)


def test_fusion_coverage_delta_separate_from_mrr():
    v = compare_fused_to_baseline(_report(), _baseline(), 0.0)
    names = {d.name for d in v.deltas}
    assert "fusion_coverage" in names
    assert "search_docs mrr" in names
    assert "search_combined mrr" not in names  # 070: combined no longer an IR surface
