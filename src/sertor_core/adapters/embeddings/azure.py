"""Adapter di embeddings per Azure OpenAI (provider cloud, REQ-013).

Implementa la porta `EmbeddingProvider` via REST (`/embeddings`). Le credenziali (endpoint, chiave)
arrivano dalla configurazione centralizzata e non vengono mai loggate (REQ-032). Gli errori sono
avvolti in `EmbeddingError` (Principio IV).

Supporta due superfici Azure: la "v1" (endpoint `.../openai/v1`, che NON accetta `api-version`) e
quella classica (con `?api-version=`). `api-version` è inviato solo se l'endpoint NON è v1.
"""
from __future__ import annotations

import logging

import httpx

from sertor_core.domain.errors import EmbeddingError
from sertor_core.observability.logging import log_event


class AzureEmbedder:
    """`EmbeddingProvider` su Azure OpenAI. `client` è iniettabile per i test (NFR-01)."""

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
                "configurazione Azure incompleta",
                provider="azure",
                reason="endpoint/api_key/deployment mancanti",
                retriable=False,
            )
        self.name = f"azure:{deployment}"
        self.dim: int | None = None
        self.batch_size = batch_size
        self._url = endpoint.rstrip("/") + "/embeddings"
        self._key = api_key
        self._deployment = deployment
        self._api_version = api_version
        self._v1 = "/openai/v1" in endpoint  # superficie v1: niente api-version
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
            # Evento strutturato al boundary PRIMA di propagare (FR-020): osservabilità additiva,
            # il comportamento d'errore resta invariato.
            log_event(logging.ERROR, "embeddings_error",
                      provider=self.name, reason=f"http {status}", retriable=retriable)
            raise EmbeddingError(
                "errore dal provider di embeddings",
                provider=self.name,
                reason=f"http {status}",
                retriable=retriable,
            ) from exc
        except httpx.HTTPError as exc:
            log_event(logging.ERROR, "embeddings_error",
                      provider=self.name, reason=type(exc).__name__, retriable=True)
            raise EmbeddingError(
                "provider di embeddings non raggiungibile",
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
