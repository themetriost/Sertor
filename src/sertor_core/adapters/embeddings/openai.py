"""Embedding adapter for the OpenAI API (cloud provider, 137 / FEAT-012).

Implements the `EmbeddingProvider` port on the shared OpenAI-protocol base: `POST
{base_url}/embeddings` with a bearer credential. `base_url` defaults to the OpenAI API and can point
to any OpenAI-compatible service. The key comes from centralised configuration and travels only in
the `Authorization` header — never logged, never in an error (FR-015).
"""
from __future__ import annotations

import random
import time
from collections.abc import Callable

import httpx

from sertor_core.adapters.embeddings._openai_protocol import OpenAIProtocolEmbedder
from sertor_core.adapters.embeddings._retry import RetryPolicy
from sertor_core.domain.errors import EmbeddingError


class OpenAIEmbedder(OpenAIProtocolEmbedder):
    """`EmbeddingProvider` on the OpenAI API. `client` is injectable for tests (NFR-01)."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        batch_size: int = 64,
        client: httpx.Client | None = None,
        retry: RetryPolicy | None = None,
        sleep: Callable[[float], None] = time.sleep,
        rng: Callable[[], float] = random.random,
    ):
        missing = [
            label
            for label, value in (("base_url", base_url), ("api_key", api_key), ("model", model))
            if not value
        ]
        if missing:
            raise EmbeddingError(
                "incomplete OpenAI configuration",
                provider="openai",
                reason=f"{'/'.join(missing)} missing",
                retriable=False,
            )
        super().__init__(
            name=f"openai:{model}",
            url=base_url.rstrip("/") + "/embeddings",
            headers={"Authorization": f"Bearer {api_key}"},
            model=model,
            batch_size=batch_size,
            client=client,
            retry=retry,
            sleep=sleep,
            rng=rng,
        )
