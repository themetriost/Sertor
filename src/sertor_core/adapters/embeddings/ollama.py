"""Embedding adapter for Ollama (local provider, REQ-013/016).

Implements the `EmbeddingProvider` port via REST (`/api/embed`). Operates entirely locally: in
a local-only configuration it contacts no cloud service. Provider errors are wrapped
in `EmbeddingError` (Principle IV) with a retryability flag.
"""
from __future__ import annotations

import logging

import httpx

from sertor_core.domain.errors import EmbeddingError
from sertor_core.observability.logging import log_event


class OllamaEmbedder:
    """`EmbeddingProvider` on Ollama. `client` is injectable for tests (NFR-01)."""

    def __init__(
        self,
        host: str,
        model: str,
        batch_size: int = 64,
        client: httpx.Client | None = None,
    ):
        self.name = f"ollama:{model}"
        self.dim: int | None = None
        self.batch_size = batch_size
        self._host = host.rstrip("/")
        self._model = model
        self._client = client or httpx.Client(timeout=300)

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        try:
            r = self._client.post(
                f"{self._host}/api/embed",
                json={"model": self._model, "input": texts},
            )
            r.raise_for_status()
            return r.json()["embeddings"]
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            retriable = status >= 500 or status == 429
            # Structured event at the boundary BEFORE propagating (FR-020): additive observability,
            # error behaviour is unchanged.
            log_event(logging.ERROR, "embeddings_error",
                      provider=self.name, reason=f"http {status}", retriable=retriable)
            raise EmbeddingError(
                "error from embedding provider",
                provider=self.name,
                reason=f"http {status}",
                retriable=retriable,
            ) from exc
        except httpx.HTTPError as exc:
            log_event(logging.ERROR, "embeddings_error",
                      provider=self.name, reason=type(exc).__name__, retriable=True)
            raise EmbeddingError(
                "embedding provider unreachable",
                provider=self.name,
                reason=type(exc).__name__,
                retriable=True,
            ) from exc

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        out: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            embs = self._embed_batch(texts[i : i + self.batch_size])
            if self.dim is None and embs:
                self.dim = len(embs[0])
            out.extend(embs)
        return out
