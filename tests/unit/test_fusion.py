"""Test the pure union hit-rate metric (070, TASK-R02).

Functions are pure: a `search_fn` mock returning the tuple `(docs, code)` drives every case. Zero
network, zero adapters, zero composition. `has_doc` comes from the docs flow, `has_code` from the
code flow (070 contract): the headline `hit` = `has_doc OR has_code` (the UNION, REQ-020); `has_doc`
and `has_code` are informative detail only, never aggregated; empty report is honest.
"""
from __future__ import annotations

from sertor_core.domain.entities import DocType, RetrievalResult
from sertor_core.services.eval.fusion import INTENT_SURFACE, union_hit_rate
from sertor_core.services.eval.models import EvalCase


def _hit(path: str, doc_type: DocType) -> RetrievalResult:
    return RetrievalResult(
        text="", path=path, chunk_id=f"{path}#0", doc_type=doc_type, score=1.0
    )


def _both_case() -> EvalCase:
    return EvalCase(
        query="requirements and where implemented",
        expected=("requirements/req.md", "src/impl.py"),
        kind="nl",
        intent="both",
    )


def test_hit_when_doc_and_code_present():
    case = _both_case()
    fn = lambda q, k: (  # noqa: E731
        [_hit("requirements/req.md", DocType.DOC)],
        [_hit("src/impl.py", DocType.CODE)],
    )
    report = union_hit_rate((case,), fn, 5)
    assert report.cases_count == 1
    assert report.union_hit_rate == 1.0
    assert report.cases[0].hit is True
    assert report.cases[0].has_doc and report.cases[0].has_code


def test_doc_only_is_a_union_hit():
    case = _both_case()
    fn = lambda q, k: ([_hit("requirements/req.md", DocType.DOC)], [])  # noqa: E731
    report = union_hit_rate((case,), fn, 5)
    assert report.union_hit_rate == 1.0  # OR: doc alone is enough
    c = report.cases[0]
    assert c.hit is True
    assert c.has_doc and not c.has_code


def test_code_only_is_a_union_hit():
    case = _both_case()
    fn = lambda q, k: ([], [_hit("src/impl.py", DocType.CODE)])  # noqa: E731
    report = union_hit_rate((case,), fn, 5)
    assert report.union_hit_rate == 1.0  # OR: code alone is enough
    c = report.cases[0]
    assert c.hit is True
    assert c.has_code and not c.has_doc


def test_empty_cases_is_honest_empty_report():
    report = union_hit_rate((), lambda q, k: ([_hit("x", DocType.DOC)], []), 5)
    assert report.cases == ()
    assert report.union_hit_rate == 0.0
    assert report.cases_count == 0


def test_no_relevant_result_is_a_miss():
    case = _both_case()
    fn = lambda q, k: ([], [_hit("src/other.py", DocType.CODE)])  # noqa: E731  irrelevant
    report = union_hit_rate((case,), fn, 5)
    c = report.cases[0]
    assert c.hit is False
    assert not c.has_doc and not c.has_code
    assert report.union_hit_rate == 0.0


def test_deterministic_same_fn_same_report():
    case = _both_case()
    fn = lambda q, k: (  # noqa: E731
        [_hit("requirements/req.md", DocType.DOC)],
        [_hit("src/impl.py", DocType.CODE)],
    )
    r1 = union_hit_rate((case,), fn, 5)
    r2 = union_hit_rate((case,), fn, 5)
    assert r1 == r2


def test_intent_surface_mapping():
    assert INTENT_SURFACE == {
        "code": "search_code",
        "doc": "search_docs",
        "both": "search_combined",
    }
