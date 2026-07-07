"""Unit tests for `dedup_results` (E5-FEAT-003 / A-07). Pure, offline, F.I.R.S.T."""
from __future__ import annotations

from sertor_core.domain.entities import DocType, RetrievalResult
from sertor_core.services.dedup import dedup_results


def _r(text: str, path: str, score: float, chunk_id: str | None = None) -> RetrievalResult:
    return RetrievalResult(
        text=text,
        path=path,
        chunk_id=chunk_id or f"{path}#0",
        doc_type=DocType.DOC,
        score=score,
    )


def test_collapses_identical_content_keeping_highest_ranked():
    # INV-1: N results with identical content → 1 (the first / highest-ranked).
    block = "## Step Ritual\nThis project maintains a local wiki."
    results = [
        _r(block, "CLAUDE.md", 0.9),
        _r(block, "assets/claude-md-block.md", 0.8),  # byte-copy
        _r("A distinct concept page", "wiki/concepts/step-ritual.md", 0.7),
    ]
    deduped, removed = dedup_results(results)
    assert removed == 1
    assert [r.path for r in deduped] == ["CLAUDE.md", "wiki/concepts/step-ritual.md"]


def test_whitespace_and_eol_differences_still_group():
    # The byte-copies differ only by EOL/indentation (CRLF↔LF churn) → still duplicates.
    a = _r("line one\nline two", "CLAUDE.md", 0.9)
    b = _r("line one\r\n  line two", "assets/x.md", 0.5)  # CRLF + extra indent
    deduped, removed = dedup_results([a, b])
    assert removed == 1
    assert deduped == [a]


def test_no_op_on_distinct_results():
    # INV-2: distinct content → same list, removed == 0 (order preserved).
    results = [
        _r("alpha content", "a.md", 0.9),
        _r("beta content", "b.md", 0.8),
        _r("gamma content", "c.md", 0.7),
    ]
    deduped, removed = dedup_results(results)
    assert removed == 0
    assert deduped == results


def test_case_preserving_does_not_over_merge():
    # Case differences are NOT collapsed (avoid over-merge).
    deduped, removed = dedup_results([_r("Hello", "a.md", 0.9), _r("hello", "b.md", 0.8)])
    assert removed == 0
    assert len(deduped) == 2


def test_count_invariant_and_empty():
    # INV-4: len(input) == len(deduped) + removed; empty is safe.
    assert dedup_results([]) == ([], 0)
    results = [_r("x", "a.md", 0.9), _r("x", "b.md", 0.8), _r("x", "c.md", 0.7)]
    deduped, removed = dedup_results(results)
    assert len(results) == len(deduped) + removed
    assert removed == 2


def test_deterministic():
    # INV-3: same input → same output.
    results = [_r("dup", "a.md", 0.9), _r("dup", "b.md", 0.8), _r("uniq", "c.md", 0.7)]
    assert dedup_results(results) == dedup_results(results)


def test_near_duplicate_same_block_different_boundaries():
    # The real case (measured): the same block chunked from two files → different chunk boundaries
    # (one longer) but high content overlap → containment ≥ threshold → collapsed. Exact-hash dedup
    # missed this; the shingle/containment test catches it.
    block = (
        "The step ritual is the definition of done for every significant step: at the end of the "
        "work the main flow records what it did and checks the wiki did not drift from the repo."
    )
    a = _r(block, "CLAUDE.md", 0.9)  # chunk from CLAUDE.md
    b = _r(block + " See also the playbook for the full list.", "assets/b.md", 0.8)  # longer copy
    distinct = _r(
        "Hybrid retrieval fuses dense vectors with BM25 lexical ranking via rank fusion.",
        "wiki/concepts/x.md",
        0.7,
    )
    deduped, removed = dedup_results([a, b, distinct])
    assert removed == 1
    assert [r.path for r in deduped] == ["CLAUDE.md", "wiki/concepts/x.md"]


def test_long_distinct_texts_not_merged():
    # Two long but genuinely different passages must NOT be collapsed (no false positive, SC-004).
    a = _r("The indexing pipeline ingests sources, chunks them, embeds each.", "a.py", 0.9)
    b = _r("The retrieval facade fuses results across collections by score.", "b.py", 0.8)
    deduped, removed = dedup_results([a, b])
    assert removed == 0
    assert len(deduped) == 2
