"""Embedding adapter for Azure OpenAI (cloud provider, REQ-013).

Implements the `EmbeddingProvider` port via REST (`/embeddings`). Credentials (endpoint, key)
come from centralised configuration and are never logged (REQ-032). Errors are
wrapped in `EmbeddingError` (Principle IV).

Supports two Azure surfaces: "v1" (endpoint `.../openai/v1`, which does NOT accept `api-version`)
and the classic surface (with `?api-version=`). `api-version` is sent only when the endpoint is
NOT v1.
"""
from __future__ import annotations

import logging

import httpx

from sertor_core.domain.errors import EmbeddingError
from sertor_core.observability.logging import log_event


class AzureEmbedder:
    """`EmbeddingProvider` on Azure OpenAI. `client` is injectable for tests (NFR-01)."""

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        deployment: str,
        api_version: str = "2024-10-21",
        batch_size: int = 64,
        client: httpx.Client | None = None,
    ):
        if not endpoint or not api_key or not deployment:
            raise EmbeddingError(
                "incomplete Azure configuration",
                provider="azure",
                reason="endpoint/api_key/deployment missing",
                retriable=False,
            )
        self.name = f"azure:{deployment}"
        self.dim: int | None = None
        self.batch_size = batch_size
        self._url = endpoint.rstrip("/") + "/embeddings"
        self._key = api_key
        self._deployment = deployment
        self._api_version = api_version
        self._v1 = "/openai/v1" in endpoint  # v1 surface: no api-version
        self._client = client or httpx.Client(timeout=300)

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        try:
            r = self._client.post(
                self._url,
                params=None if self._v1 else {"api-version": self._api_version},
                headers={"api-key": self._key},
                json={"model": self._deployment, "input": texts},
            )
            r.raise_for_status()
            data = sorted(r.json()["data"], key=lambda d: d["index"])
            return [d["embedding"] for d in data]
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
