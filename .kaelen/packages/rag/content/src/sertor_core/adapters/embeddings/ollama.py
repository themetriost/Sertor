"""Embedding adapter for Ollama (local provider, REQ-013/016).

Implements the `EmbeddingProvider` port via REST (`/api/embed`). Operates entirely locally: in
a local-only configuration it contacts no cloud service. Provider errors are wrapped
in `EmbeddingError` (Principle IV) with a retryability flag.
"""
from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable

import httpx

from sertor_core.adapters.embeddings._retry import RetryPolicy, with_retry
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
        retry: RetryPolicy | None = None,
        sleep: Callable[[float], None] = time.sleep,
        rng: Callable[[], float] = random.random,
    ):
        self.name = f"ollama:{model}"
        self.dim: int | None = None
        self.batch_size = batch_size
        self._host = host.rstrip("/")
        self._model = model
        self._client = client or httpx.Client(timeout=300)
        self._retry = retry
        self._sleep = sleep
        self._rng = rng

    def _embed_batch(self, texts: list[str]) -> tuple[list[list[float]], int | None]:
        try:
            r = self._client.post(
                f"{self._host}/api/embed",
                json={"model": self._model, "input": texts},
            )
            r.raise_for_status()
            payload = r.json()
            tokens = payload.get("prompt_eval_count")  # best-effort cost signal (REQ-H5)
            return payload["embeddings"], tokens
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

    def _embed_batch_resilient(self, batch: list[str]) -> tuple[list[list[float]], int | None]:
        """`_embed_batch` with retry on transient failures (018, REQ-H3), if a policy is set.

        Wrapping the BATCH (not the whole `embed`) avoids re-embedding batches that already
        succeeded. With no policy or a single attempt, calls through with zero overhead.
        """
        if self._retry is None or self._retry.attempts <= 1:
            return self._embed_batch(batch)
        return with_retry(
            lambda: self._embed_batch(batch),
            self._retry,
            sleep=self._sleep,
            rng=self._rng,
            provider=self.name,
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        out: list[list[float]] = []
        total_tokens = 0
        have_tokens = False  # distinguish "0 tokens" from "provider did not report" (FR-009)
        for i in range(0, len(texts), self.batch_size):
            embs, tokens = self._embed_batch_resilient(texts[i : i + self.batch_size])
            if tokens is not None:
                total_tokens += tokens
                have_tokens = True
            if self.dim is None and embs:
                self.dim = len(embs[0])
            out.extend(embs)
        # Success event with the token cost signal (REQ-H5); field omitted when unavailable.
        fields = {"provider": self.name, "texts": len(texts)}
        if have_tokens:
            fields["tokens"] = total_tokens
        log_event(logging.INFO, "embeddings", **fields)
        return out
