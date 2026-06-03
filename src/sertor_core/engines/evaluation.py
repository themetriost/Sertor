"""Valutazione della pertinenza del retrieval (REQ-011 di FEAT-002).

Misura hit-rate@k e MRR@10 su un ground-truth esterno (query → file attesi). "Una feature senza
misura non è fatta" (Principio V): la misura è il criterio oggettivo di accettazione.
"""
from __future__ import annotations

from dataclasses import dataclass

from sertor_core.engines.baseline import BaselineEngine

GroundTruth = list[tuple[str, list[str]]]  # (query, expected_paths)


@dataclass(frozen=True)
class EvalReport:
    """Esito della valutazione."""

    hit_rate: dict[int, float]
    mrr: float
    queries: int
    provider: str


def evaluate(
    engine: BaselineEngine,
    ground_truth: GroundTruth,
    ks: tuple[int, ...] = (1, 3, 5, 10),
) -> EvalReport:
    """Calcola hit-rate@k (per ogni k) e MRR@10 sul ground-truth.

    Un risultato è pertinente se il suo `path` è tra gli `expected_paths` della query. Ground-truth
    vuoto → metriche a 0, senza errore.
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
