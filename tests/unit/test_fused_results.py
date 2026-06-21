"""Test the `merge_fused` courtesy helper — deterministic interleave (070, library-contract).

`search_combined` returns the tuple `(docs, code)`; `merge_fused` is the free function (not a method
on an object) that produces a single deterministic list by interleaving the two flows by rank.
"""
from __future__ import annotations

from sertor_core.domain.entities import DocType, RetrievalResult
from sertor_core.services.retrieval import merge_fused


def _r(name: str, doc_type: DocType) -> RetrievalResult:
    return RetrievalResult(
        text=name, path=f"{name}.x", chunk_id=f"{name}#0", doc_type=doc_type, score=0.5
    )


D0, D1, D2 = (_r(f"d{i}", DocType.DOC) for i in range(3))
C0, C1 = (_r(f"c{i}", DocType.CODE) for i in range(2))


def test_merge_interleaves_equal_lengths():
    assert merge_fused([D0, D1], [C0, C1]) == [D0, C0, D1, C1]


def test_merge_appends_leftover_of_longer_list():
    assert merge_fused([D0, D1, D2], [C0]) == [D0, C0, D1, D2]


def test_merge_with_empty_docs_keeps_code_order():
    assert merge_fused([], [C0, C1]) == [C0, C1]


def test_merge_both_empty():
    assert merge_fused([], []) == []


def test_merge_is_deterministic_on_reexecution():
    assert merge_fused([D0, D1, D2], [C0, C1]) == merge_fused([D0, D1, D2], [C0, C1])
