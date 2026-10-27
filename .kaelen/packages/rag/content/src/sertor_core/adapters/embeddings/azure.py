"""Embedding adapter for Azure OpenAI (cloud provider, REQ-013).

Implements the `EmbeddingProvider` port via REST (`/embeddings`) on the shared OpenAI-protocol base
(137, D-1). Credentials (endpoint, key) come from centralised configuration and are never logged
(REQ-032). Errors are wrapped in `EmbeddingError` (Principle IV).

Supports two Azure surfaces: "v1" (endpoint `.../openai/v1`, which does NOT accept `api-version`)
and the classic surface (with `?api-version=`). `api-version` is sent only when the endpoint is
NOT v1.
"""
from __future__ import annotations

import random
import time
from collections.abc import Callable

import httpx

from sertor_core.adapters.embeddings._openai_protocol import OpenAIProtocolEmbedder
from sertor_core.adapters.embeddings._retry import RetryPolicy
from sertor_core.domain.errors import EmbeddingError


class AzureEmbedder(OpenAIProtocolEmbedder):
    """`EmbeddingProvider` on Azure OpenAI. `client` is injectable for tests (NFR-01)."""

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        deployment: str,
        api_version: str = "2024-10-21",
        batch_size: int = 64,
        client: httpx.Client | None = None,
        retry: RetryPolicy | None = None,
        sleep: Callable[[float], None] = time.sleep,
        rng: Callable[[], float] = random.random,
    ):
        if not endpoint or not api_key or not deployment:
            raise EmbeddingError(
                "incomplete Azure configuration",
                provider="azure",
                reason="endpoint/api_key/deployment missing",
                retriable=False,
            )
        v1 = "/openai/v1" in endpoint  # v1 surface: no api-version
        super().__init__(
            name=f"azure:{deployment}",
            url=endpoint.rstrip("/") + "/embeddings",
            headers={"api-key": api_key},
            model=deployment,
            params=None if v1 else {"api-version": api_version},
            batch_size=batch_size,
            client=client,
            retry=retry,
            sleep=sleep,
            rng=rng,
        )
