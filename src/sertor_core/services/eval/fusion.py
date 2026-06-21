"""Pure fusion coverage metric for the fused code+doc eval (069, data-model §2/§3).

The fusion coverage is the SIGNATURE measure of the mission's differentiator: on a `both`-intent
case (a query that should return documentation AND source together), a case is «covered» only when
the top-k carries ≥1 relevant DOC result AND ≥1 relevant CODE result (REQ-020). The type is read
from `RetrievalResult.doc_type` at RUNTIME — never double-labelled in the `expected` set (less
drift, data-model §11). `fusion_coverage` is a PURE function: it takes a search callable, so it is
testable with `search_fn=lambda q, k: [...]` (zero adapter/composition import).
"""
from __future__ import annotations

from collections.abc import Callable

from sertor_core.domain.entities import FusedResults
from sertor_core.services.eval.models import EvalCase, FusionCaseResult, FusionReport

# Unique source of the intent→surface mapping (Principio VII): the `intent` of a case decides which
# `search_*` measures it. Used by `fused_runner.py` and the CLI.
INTENT_SURFACE: dict[str, str] = {
    "code": "search_code",
    "doc": "search_docs",
    "both": "search_combined",
}


def fusion_coverage(
    cases: tuple[EvalCase, ...],
    search_fn: Callable[[str, int], FusedResults],
    k: int,
) -> FusionReport:
    """Compute the fusion coverage of the `both`-intent `cases` via `search_fn` (070, REQ-020/022).

    `search_fn` now returns a `FusedResults(docs, code)` (the structured combined surface). For each
    case: `has_doc` = an expected path appears in the **docs** list (own top-k), `has_code` = an
    expected path appears in the **code** list (own top-k); `covered = has_doc AND has_code`;
    `hit_at_k` = any expected path is in either list (≡ `flatten()`). A case `hit_at_k=True,
    covered=False` increments `hit_but_not_covered` (the visible lacuna). `cases` empty → an honest
    empty report (coverage 0.0, `cases_count=0`) — not an error. Pure and deterministic (REQ-041).
    """
    results: list[FusionCaseResult] = []
    for case in cases:
        expected = set(case.expected)
        fused = search_fn(case.query, k)
        has_doc = any(r.path in expected for r in fused.docs)
        has_code = any(r.path in expected for r in fused.code)
        covered = has_doc and has_code
        hit_at_k = any(r.path in expected for r in fused.flatten())
        results.append(
            FusionCaseResult(
                query=case.query,
                expected=case.expected,
                has_doc=has_doc,
                has_code=has_code,
                covered=covered,
                hit_at_k=hit_at_k,
            )
        )
    cases_count = len(results)
    covered_count = sum(1 for c in results if c.covered)
    hit_but_not_covered = sum(1 for c in results if c.hit_at_k and not c.covered)
    coverage = covered_count / cases_count if cases_count else 0.0
    return FusionReport(
        cases=tuple(results),
        coverage=coverage,
        cases_count=cases_count,
        hit_but_not_covered=hit_but_not_covered,
    )
