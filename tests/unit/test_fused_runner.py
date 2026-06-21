"""Test the fused runner + event (070, TASK-R03).

The facade is a structural-typing fake (no inheritance): it exposes `provider`, the two mono-type
`search_*` methods, and `search_combined` returning `FusedResults`. The runner reuses the invariant
`evaluate` for the two IR surfaces (`search_combined` is NOT an IR surface anymore). The event is
asserted metrics-only (no query/path/expected/names) with exactly two `surface_*` keys.
"""
from __future__ import annotations

import logging

from sertor_core.domain.entities import DocType, FusedResults, RetrievalResult
from sertor_core.services.eval.fused_runner import (
    emit_fused_eval_event,
    run_fused_evaluation,
)
from sertor_core.services.eval.models import (
    EvalCase,
    EvalSuite,
    FusedRegressionVerdict,
)


def _hit(path: str, doc_type: DocType) -> RetrievalResult:
    return RetrievalResult(
        text="", path=path, chunk_id=f"{path}#0", doc_type=doc_type, score=1.0
    )


class _FakeFacade:
    """Structural QueryableEngine source: provider + the three search surfaces."""

    provider = "hash"

    def search_code(self, query, k=None):
        return [_hit("src/impl.py", DocType.CODE)]

    def search_docs(self, query, k=None):
        return [_hit("requirements/req.md", DocType.DOC)]

    def search_combined(self, query, k=None):
        return FusedResults(
            docs=(_hit("requirements/req.md", DocType.DOC),),
            code=(_hit("src/impl.py", DocType.CODE),),
        )


def _suite_with_intents() -> EvalSuite:
    return EvalSuite(
        cases=(
            EvalCase("where is X", ("src/impl.py",), "nl", "code"),
            EvalCase("why Y", ("requirements/req.md",), "nl", "doc"),
            EvalCase(
                "req and impl",
                ("requirements/req.md", "src/impl.py"),
                "nl",
                "both",
            ),
        )
    )


def test_run_fused_produces_two_surfaces_and_fusion():
    report = run_fused_evaluation(_FakeFacade(), _suite_with_intents(), (1, 3, 5), 5)
    assert [s.surface for s in report.surfaces] == [
        "search_code",
        "search_docs",
    ]  # 070: search_combined is no longer an IR surface
    assert report.provider == "hash"
    assert report.fusion.cases_count == 1
    assert report.fusion.coverage == 1.0  # combined returns doc + code (separate flows)
    # each surface measured only its own intent cases
    by_surface = {s.surface: s.report for s in report.surfaces}
    assert by_surface["search_code"].queries == 1
    assert by_surface["search_docs"].queries == 1


def test_run_fused_no_intent_cases_is_empty_honest():
    suite = EvalSuite(cases=(EvalCase("Q", ("src/x.py",), "symbol", None),))
    report = run_fused_evaluation(_FakeFacade(), suite, (1, 3, 5), 5)
    assert report.fusion.cases_count == 0
    for s in report.surfaces:
        assert s.report.queries == 0


def test_emit_event_is_metrics_only(caplog):
    report = run_fused_evaluation(_FakeFacade(), _suite_with_intents(), (1, 3, 5), 5)
    verdict = FusedRegressionVerdict(deltas=(), tolerance=0.0, verdict="no-baseline")
    with caplog.at_level(logging.INFO, logger="sertor_core"):
        emit_fused_eval_event(report, verdict)
    records = [r for r in caplog.records if getattr(r, "operation", "") == "fused_eval"]
    assert records, "the fused_eval event was not emitted"
    rec = records[0]
    fields = {
        k: v
        for k, v in rec.__dict__.items()
        if k not in ("operation", "msg", "args", "levelname", "levelno")
    }
    blob = repr(fields)
    # no free text / query / path / expected / symbol leaks (RNF-3, Principio IX)
    assert "req and impl" not in blob
    assert "requirements/req.md" not in blob
    assert "src/impl.py" not in blob
    assert rec.cases == {"code": 1, "doc": 1, "both": 1}
    assert rec.fusion_coverage == 1.0
    assert rec.tolerance is None  # no-baseline → null tolerance
    # 070: surface metrics have exactly the two mono-type keys (closed cardinality), not 3.
    assert set(rec.surface_mrr) == {"search_code", "search_docs"}
    assert set(rec.surface_hit3) == {"search_code", "search_docs"}
    assert "search_combined" not in rec.surface_mrr
