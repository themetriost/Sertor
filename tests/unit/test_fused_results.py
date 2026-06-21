"""Test TASK-F01 — `FusedResults.flatten()` deterministic interleave (070, library-contract)."""
from __future__ import annotations

from sertor_core.domain.entities import DocType, FusedResults, RetrievalResult


def _r(name: str, doc_type: DocType) -> RetrievalResult:
    return RetrievalResult(
        text=name, path=f"{name}.x", chunk_id=f"{name}#0", doc_type=doc_type, score=0.5
    )


D0, D1, D2 = (_r(f"d{i}", DocType.DOC) for i in range(3))
C0, C1 = (_r(f"c{i}", DocType.CODE) for i in range(2))


def test_flatten_interleaves_equal_lengths():
    fused = FusedResults(docs=(D0, D1), code=(C0, C1))
    assert fused.flatten() == [D0, C0, D1, C1]


def test_flatten_appends_leftover_of_longer_list():
    fused = FusedResults(docs=(D0, D1, D2), code=(C0,))
    assert fused.flatten() == [D0, C0, D1, D2]


def test_flatten_with_empty_docs_keeps_code_order():
    fused = FusedResults(docs=(), code=(C0, C1))
    assert fused.flatten() == [C0, C1]


def test_flatten_both_empty():
    assert FusedResults().flatten() == []
    assert FusedResults(docs=(), code=()).flatten() == []


def test_flatten_is_deterministic_on_reexecution():
    fused = FusedResults(docs=(D0, D1, D2), code=(C0, C1))
    assert fused.flatten() == fused.flatten()


def test_fused_results_is_hashable():
    # Frozen dataclass with tuple fields → hashable by value.
    a = FusedResults(docs=(D0,), code=(C0,))
    b = FusedResults(docs=(D0,), code=(C0,))
    assert hash(a) == hash(b)
    assert {a, b} == {a}


def test_defaults_are_empty_tuples():
    fused = FusedResults()
    assert fused.docs == () and fused.code == ()
