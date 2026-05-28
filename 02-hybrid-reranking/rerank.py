"""Reranking dei candidati con un cross-encoder leggero (FlashRank, ONNX).

Riordina i risultati fusi (dense+BM25) in base alla rilevanza query-passaggio.
Il modello viene scaricato e cache-ato da FlashRank al primo uso.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from flashrank import Ranker, RerankRequest  # noqa: E402

_ranker: Ranker | None = None


def get_ranker() -> Ranker:
    global _ranker
    if _ranker is None:
        _ranker = Ranker(max_length=512)  # default: ms-marco-MiniLM-L-12-v2
    return _ranker


def rerank(query: str, hits: list[dict], k: int = 10) -> list[dict]:
    if not hits:
        return []
    passages = [{"id": i, "text": h["text"]} for i, h in enumerate(hits)]
    results = get_ranker().rerank(RerankRequest(query=query, passages=passages))
    out = []
    for r in results[:k]:
        h = hits[int(r["id"])]
        out.append({**h, "rerank_score": float(r["score"])})
    return out
