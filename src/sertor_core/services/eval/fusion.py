"""Pure union hit-rate metric for the fused code+doc eval (070, data-model §2/§3).

The fusion measure is the SIGNATURE of the mission's differentiator: on a `both`-intent case (a
query that should return documentation AND/OR source together), the headline number is the UNION
(OR), not the product (AND): a case `hits` when an expected path appears in the docs flow OR in the
code flow. This fixes the wrong metric of 069/0d89bf8 (`covered = has_doc AND has_code`, the
«multiplication» the user excluded) — the fusion is the union of the two flows, not their
intersection. `has_doc`/`has_code` survive ONLY as per-case detail (which stream found the
expected), never aggregated. The type is read from `RetrievalResult.doc_type` at RUNTIME — never
double-labelled in the `expected` set (less drift, data-model §11). `union_hit_rate` is a PURE
function: it takes a search callable returning the tuple `(docs, code)`, so it is testable with
`search_fn=lambda q, k: ([...], [...])` (zero adapter/composition import).
"""
from __future__ import annotations

from collections.abc import Callable

from sertor_core.domain.entities import RetrievalResult
from sertor_core.services.eval.models import EvalCase, FusionCaseResult, FusionReport

# Unique source of the intent→surface mapping (Principio VII): the `intent` of a case decides which
# `search_*` measures it. Used by `fused_runner.py` and the CLI.
INTENT_SURFACE: dict[str, str] = {
    "code": "search_code",
    "doc": "search_docs",
    "both": "search_combined",
}


def union_hit_rate(
    cases: tuple[EvalCase, ...],
    search_fn: Callable[[str, int], tuple[list[RetrievalResult], list[RetrievalResult]]],
    k: int,
) -> FusionReport:
    """Compute the union hit-rate of the `both`-intent `cases` via `search_fn` (070, REQ-020/022).

    `search_fn` returns the structured combined surface as a TUPLE `(docs, code)`. For each case:
    `has_doc` = an expected path appears in the **docs** flow (own top-k), `has_code` = an expected
    path appears in the **code** flow (own top-k); the headline `hit` = `has_doc OR has_code` (the
    UNION). `has_doc`/`has_code` are kept as informative per-case detail only — they NEVER enter the
    aggregate. `cases` empty → an honest empty report (`union_hit_rate=0.0`, `cases_count=0`) — not
    an error. Pure and deterministic (REQ-041).
    """
    results: list[FusionCaseResult] = []
    for case in cases:
        expected = set(case.expected)
        docs, code = search_fn(case.query, k)
        has_doc = any(r.path in expected for r in docs)
        has_code = any(r.path in expected for r in code)
        results.append(
            FusionCaseResult(
                query=case.query,
                expected=case.expected,
                has_doc=has_doc,
                has_code=has_code,
                hit=has_doc or has_code,
            )
        )
    cases_count = len(results)
    hit_count = sum(1 for c in results if c.hit)
    rate = hit_count / cases_count if cases_count else 0.0
    return FusionReport(
        cases=tuple(results),
        union_hit_rate=rate,
        cases_count=cases_count,
    )
