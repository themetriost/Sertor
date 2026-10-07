"""Shared base for embedding providers speaking the OpenAI `/embeddings` protocol (137, D-1).

Azure OpenAI and the OpenAI API (or any OpenAI-compatible service) accept the same request
(`{"model", "input"}`) and return the same response (`data[].embedding`, `usage.total_tokens`).
They differ only in URL, credential header, query parameters and provider name — which the
subclasses fix in their constructor. Batching, error classification (Principle IV), per-batch
retry (018, REQ-H3) and the token cost signal (REQ-H5) live here, once.

Credentials travel only in the request headers: they are never logged nor put in an error.
"""
from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable, Mapping

import httpx

from sertor_core.adapters.embeddings._retry import RetryPolicy, with_retry
from sertor_core.domain.errors import EmbeddingError
from sertor_core.observability.logging import log_event


class OpenAIProtocolEmbedder:
    """`EmbeddingProvider` over the OpenAI `/embeddings` protocol; `client` injectable (NFR-01)."""

    def __init__(
        self,
        *,
        name: str,
        url: str,
        headers: Mapping[str, str],
        model: str,
        params: Mapping[str, str] | None = None,
        batch_size: int = 64,
        client: httpx.Client | None = None,
        retry: RetryPolicy | None = None,
        sleep: Callable[[float], None] = time.sleep,
        rng: Callable[[], float] = random.random,
    ):
        self.name = name
        self.dim: int | None = None
        self.batch_size = batch_size
        self._url = url
        self._headers = dict(headers)
        self._params = dict(params) if params else None
        self._model = model
        self._client = client or httpx.Client(timeout=300)
        self._retry = retry
        self._sleep = sleep
        self._rng = rng

    def _embed_batch(self, texts: list[str]) -> tuple[list[list[float]], int | None]:
        try:
            r = self._client.post(
                self._url,
                params=self._params,
                headers=self._headers,
                json={"model": self._model, "input": texts},
            )
            r.raise_for_status()
            payload = r.json()
            data = sorted(payload["data"], key=lambda d: d["index"])
            tokens = (payload.get("usage") or {}).get("total_tokens")  # cost signal (REQ-H5)
            return [d["embedding"] for d in data], tokens
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
