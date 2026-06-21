"""Test the pure fusion coverage metric (070, TASK-R02).

Functions are pure: a `search_fn` mock returning `FusedResults(docs, code)` drives every case. Zero
network, zero adapters, zero composition. `has_doc` comes from the docs flow, `has_code` from the
code flow (070 contract): covered = ≥1 relevant DOC in `docs` AND ≥1 relevant CODE in `code`
(REQ-020); a hit@k (in either flow) but not covered → hit_but_not_covered (REQ-022); empty report.
"""
from __future__ import annotations

from sertor_core.domain.entities import DocType, FusedResults, RetrievalResult
from sertor_core.services.eval.fusion import INTENT_SURFACE, fusion_coverage
from sertor_core.services.eval.models import EvalCase


def _hit(path: str, doc_type: DocType) -> RetrievalResult:
    return RetrievalResult(
        text="", path=path, chunk_id=f"{path}#0", doc_type=doc_type, score=1.0
    )


def _fused(docs=(), code=()) -> FusedResults:
    return FusedResults(docs=tuple(docs), code=tuple(code))


def _both_case() -> EvalCase:
    return EvalCase(
        query="requirements and where implemented",
        expected=("requirements/req.md", "src/impl.py"),
        kind="nl",
        intent="both",
    )


def test_covered_when_doc_and_code_present():
    case = _both_case()
    fn = lambda q, k: _fused(  # noqa: E731
        docs=[_hit("requirements/req.md", DocType.DOC)],
        code=[_hit("src/impl.py", DocType.CODE)],
    )
    report = fusion_coverage((case,), fn, 5)
    assert report.cases_count == 1
    assert report.coverage == 1.0
    assert report.hit_but_not_covered == 0
    assert report.cases[0].covered is True
    assert report.cases[0].has_doc and report.cases[0].has_code


def test_doc_only_is_hit_but_not_covered():
    case = _both_case()
    fn = lambda q, k: _fused(docs=[_hit("requirements/req.md", DocType.DOC)])  # noqa: E731
    report = fusion_coverage((case,), fn, 5)
    assert report.coverage == 0.0
    assert report.hit_but_not_covered == 1
    c = report.cases[0]
    assert c.hit_at_k is True and c.covered is False
    assert c.has_doc and not c.has_code


def test_code_only_is_hit_but_not_covered():
    case = _both_case()
    fn = lambda q, k: _fused(code=[_hit("src/impl.py", DocType.CODE)])  # noqa: E731
    report = fusion_coverage((case,), fn, 5)
    assert report.coverage == 0.0
    assert report.hit_but_not_covered == 1
    c = report.cases[0]
    assert c.hit_at_k is True and c.covered is False
    assert c.has_code and not c.has_doc


def test_empty_cases_is_honest_empty_report():
    report = fusion_coverage((), lambda q, k: _fused(docs=[_hit("x", DocType.DOC)]), 5)
    assert report.cases == ()
    assert report.coverage == 0.0
    assert report.cases_count == 0
    assert report.hit_but_not_covered == 0


def test_no_relevant_result_is_not_hit_not_counted():
    case = _both_case()
    fn = lambda q, k: _fused(code=[_hit("src/other.py", DocType.CODE)])  # noqa: E731  irrelevant
    report = fusion_coverage((case,), fn, 5)
    c = report.cases[0]
    assert c.hit_at_k is False and c.covered is False
    assert report.hit_but_not_covered == 0  # only hit@k=True & covered=False counts


def test_deterministic_same_fn_same_report():
    case = _both_case()
    fn = lambda q, k: _fused(  # noqa: E731
        docs=[_hit("requirements/req.md", DocType.DOC)],
        code=[_hit("src/impl.py", DocType.CODE)],
    )
    r1 = fusion_coverage((case,), fn, 5)
    r2 = fusion_coverage((case,), fn, 5)
    assert r1 == r2


def test_intent_surface_mapping():
    assert INTENT_SURFACE == {
        "code": "search_code",
        "doc": "search_docs",
        "both": "search_combined",
    }
