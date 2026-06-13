"""Adapter `Reranker` on FlashRank (ONNX cross-encoder, no torch) — extra `rerank` (FEAT-004).

Lazy import inside the constructor (REQ-021): the module is importable without the extra; it is
the composition root that translates the `ImportError` into an actionable `ConfigError` (REQ-022).
The model is downloaded and cached by FlashRank on first use (pattern from prototype 02,
`rerank.py`).
"""
from __future__ import annotations

from dataclasses import replace

from sertor_core.domain.entities import RetrievalResult

_DEFAULT_MODEL = "ms-marco-MiniLM-L-12-v2"


class FlashRankReranker:
    """`Reranker` on FlashRank: re-scores the fused query-passage pool."""

    def __init__(self, model: str = _DEFAULT_MODEL, max_length: int = 512):
        from flashrank import Ranker  # lazy import: extra `rerank` (REQ-021)

        self.model = model
        self._ranker = Ranker(model_name=model, max_length=max_length)

    def rerank(
        self, query: str, results: list[RetrievalResult], k: int
    ) -> list[RetrievalResult]:
        if not results:
            return []
        from flashrank import RerankRequest

        passages = [{"id": i, "text": r.text} for i, r in enumerate(results)]
        ranked = self._ranker.rerank(RerankRequest(query=query, passages=passages))
        return [
            replace(results[int(item["id"])], score=float(item["score"]))
            for item in ranked[:k]
        ]
