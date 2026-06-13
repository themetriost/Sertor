"""Retrieval relevance evaluation (REQ-011 of FEAT-002).

Measures hit-rate@k and MRR@10 against an external ground-truth (query → expected files).
"A feature without a measure is not done" (Principle V): the measure is the objective
acceptance criterion.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from sertor_core.domain.entities import RetrievalResult

GroundTruth = list[tuple[str, list[str]]]  # (query, expected_paths)


@runtime_checkable
class QueryableEngine(Protocol):
    """Any measurable RAG engine: only `query` + `provider` needed (structural typing).

    Generalisation FEAT-004 (REQ-051): evaluation compares baseline, hybrid and
    hybrid+rerank with the same function — annotation only, zero behaviour changes.
    """

    @property
    def provider(self) -> str: ...

    def query(self, query: str, k: int | None = None) -> list[RetrievalResult]: ...


@dataclass(frozen=True)
class EvalReport:
    """Evaluation result."""

    hit_rate: dict[int, float]
    mrr: float
    queries: int
    provider: str


def evaluate(
    engine: QueryableEngine,
    ground_truth: GroundTruth,
    ks: tuple[int, ...] = (1, 3, 5, 10),
) -> EvalReport:
    """Computes hit-rate@k (for each k) and MRR@10 on the ground-truth.

    A result is relevant if its `path` is among the `expected_paths` for the query. Empty
    ground-truth → metrics at 0, no error.
    """
    n = len(ground_truth)
    if n == 0:
        return EvalReport({k: 0.0 for k in ks}, 0.0, 0, engine.provider)

    hits = {k: 0 for k in ks}
    rr_sum = 0.0
    for query, expected in ground_truth:
        expected_set = set(expected)
        paths = [r.path for r in engine.query(query, k=10)]
        rank = next((i + 1 for i, p in enumerate(paths) if p in expected_set), None)
        if rank is not None:
            for k in ks:
                if rank <= k:
                    hits[k] += 1
            if rank <= 10:
                rr_sum += 1.0 / rank
    return EvalReport(
        hit_rate={k: hits[k] / n for k in ks},
        mrr=rr_sum / n,
        queries=n,
        provider=engine.provider,
    )
