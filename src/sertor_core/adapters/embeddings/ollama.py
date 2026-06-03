"""Adapter di embeddings per Ollama (provider locale, REQ-013/016).

Implementa la porta `EmbeddingProvider` via REST (`/api/embed`). Opera interamente in locale: in
configurazione local-only non contatta alcun servizio cloud. Gli errori del provider sono avvolti
in `EmbeddingError` (Principio IV) con indicazione di ritentabilità.
"""
from __future__ import annotations

import httpx

from sertor_core.domain.errors import EmbeddingError


class OllamaEmbedder:
    """`EmbeddingProvider` su Ollama. `client` è iniettabile per i test (NFR-01)."""

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
            raise EmbeddingError(
                "errore dal provider di embeddings",
                provider=self.name,
                reason=f"http {status}",
                retriable=status >= 500 or status == 429,
            ) from exc
        except httpx.HTTPError as exc:
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
