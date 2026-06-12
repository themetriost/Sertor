"""Adapter `Reranker` su FlashRank (cross-encoder ONNX, niente torch) — extra `rerank` (FEAT-004).

Import pigro dentro il costruttore (REQ-021): il modulo è importabile senza l'extra; è il
composition root a tradurre l'`ImportError` in `ConfigError` azionabile (REQ-022). Il modello
viene scaricato e cache-ato da FlashRank al primo uso (pattern del prototipo 02, `rerank.py`).
"""
from __future__ import annotations

from dataclasses import replace

from sertor_core.domain.entities import RetrievalResult

_DEFAULT_MODEL = "ms-marco-MiniLM-L-12-v2"


class FlashRankReranker:
    """`Reranker` su FlashRank: ri-punteggia il pool fuso query-passaggio."""

    def __init__(self, model: str = _DEFAULT_MODEL, max_length: int = 512):
        from flashrank import Ranker  # lazy: extra `rerank` (REQ-021)

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
