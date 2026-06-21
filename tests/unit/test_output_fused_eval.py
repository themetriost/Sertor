"""Test the fused output formatters (070, TASK-R08): pure, human↔JSON equivalence.

Zero I/O. Builds report/verdict entities directly. After 070 the eval report carries TWO surfaces
(search_code/search_docs); the fusion measure is the UNION hit-rate (OR), not the AND coverage; also
covers the new `format_fused_search_results` (two labelled flows, taken as a tuple `(docs, code)`).
"""
from __future__ import annotations

import json

from sertor_core.cli.output import (
    format_fused_eval_report,
    format_fused_regression,
    format_fused_search_results,
)
from sertor_core.config.settings import Settings
from sertor_core.domain.entities import DocType, RetrievalResult
from sertor_core.engines.evaluation import EvalReport
from sertor_core.services.eval.models import (
    FusedEvalReport,
    FusedRegressionVerdict,
    FusionCaseResult,
    FusionReport,
    MetricDelta,
    SurfaceEvalReport,
)


def _surface(name: str, mrr: float) -> SurfaceEvalReport:
    return SurfaceEvalReport(
        surface=name,
        report=EvalReport(hit_rate={1: 0.5, 3: 0.8, 5: 0.9}, mrr=mrr, queries=2, provider="hash"),
    )


def _report() -> FusedEvalReport:
    fusion = FusionReport(
        cases=(
            # hit in both streams (union hit)
            FusionCaseResult("req+impl", ("r.md", "x.py"), True, True, True),
            # hit only via docs → still a UNION hit (OR)
            FusionCaseResult("doc only", ("r.md", "x.py"), True, False, True),
        ),
        union_hit_rate=1.0,
        cases_count=2,
    )
    return FusedEvalReport(
        surfaces=(
            _surface("search_code", 0.64),
            _surface("search_docs", 0.73),
        ),  # 070: two surfaces, no search_combined
        fusion=fusion,
        provider="hash",
    )


def _pass_verdict() -> FusedRegressionVerdict:
    return FusedRegressionVerdict(
        deltas=(MetricDelta("union_hit_rate", 1.0, 0.97, 0.03, False),),
        tolerance=0.0,
        verdict="pass",
    )


def test_human_output_has_all_blocks():
    out = format_fused_eval_report(_report(), _pass_verdict(), json=False)
    assert "union hit-rate" in out
    assert "[hit ]" in out
    assert "MRR=0.64" in out
    assert "non-regression: PASS" in out
    assert "doc only" in out  # the doc-only case is rendered with its detail


def test_json_output_is_valid_and_equivalent():
    out = format_fused_eval_report(_report(), _pass_verdict(), json=True)
    obj = json.loads(out)
    assert obj["provider"] == "hash"
    assert obj["cases"] == {"code": 2, "doc": 2, "both": 2}
    assert obj["fusion"]["union_hit_rate"] == 1.0
    assert obj["fusion"]["cases_count"] == 2
    assert obj["fusion"]["cases"][1]["hit"] is True       # doc-only case is a union hit
    assert obj["non_regression"]["verdict"] == "pass"
    assert len(obj["surfaces"]) == 2  # 070: two surfaces


def test_format_fused_regression_regressed():
    verdict = FusedRegressionVerdict(
        deltas=(
            MetricDelta("search_code mrr", 0.4, 0.64, -0.24, True),
            MetricDelta("union_hit_rate", 0.3, 0.5, -0.2, True),
        ),
        tolerance=0.0,
        verdict="regressed",
    )
    out = format_fused_regression(verdict, json=False)
    assert "REGRESSED" in out
    assert "search_code mrr" in out
    assert "union_hit_rate" in out


def test_empty_report_does_not_crash():
    empty = FusedEvalReport(
        surfaces=(
            _surface("search_code", 0.0),
            _surface("search_docs", 0.0),
        ),  # 070: two surfaces
        fusion=FusionReport(cases=(), union_hit_rate=0.0, cases_count=0),
        provider="hash",
    )
    verdict = FusedRegressionVerdict(deltas=(), tolerance=0.0, verdict="no-baseline")
    out = format_fused_eval_report(empty, verdict, json=False)
    assert "union hit-rate: 0.00" in out
    assert "no baseline" in out


# --- format_fused_search_results: the two labelled flows (070, TASK-R05/DA-d) ---


def _settings() -> Settings:
    return Settings()


def _r(name: str, doc_type: DocType) -> RetrievalResult:
    return RetrievalResult(
        text=f"body of {name}", path=f"{name}.x", chunk_id=f"{name}#0",
        doc_type=doc_type, score=0.5,
    )


def test_fused_search_human_has_two_labelled_sections():
    out = format_fused_search_results(
        [_r("d0", DocType.DOC)], [_r("c0", DocType.CODE)], _settings(), json=False, full=False
    )
    assert "docs:" in out and "code:" in out
    assert "d0.x" in out and "c0.x" in out


def test_fused_search_empty_flow_is_honest():
    out = format_fused_search_results(
        [], [_r("c0", DocType.CODE)], _settings(), json=False, full=False
    )
    assert "docs:" in out
    assert "(no results)" in out  # empty docs flow → honest empty state, never silence


def test_fused_search_json_has_docs_and_code_keys():
    obj = json.loads(
        format_fused_search_results(
            [_r("d0", DocType.DOC)], [_r("c0", DocType.CODE)], _settings(), json=True, full=False
        )
    )
    assert set(obj) == {"docs", "code"}
    assert obj["docs"][0]["path"] == "d0.x"
    assert obj["code"][0]["chunk_id"] == "c0#0"


def test_fused_search_json_empty_flow_is_empty_list():
    obj = json.loads(
        format_fused_search_results([], [], _settings(), json=True, full=False)
    )
    assert obj == {"docs": [], "code": []}
