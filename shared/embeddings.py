"""Embeddings layer intercambiabile sui 3 provider (Ollama + Azure small/large).

Ogni embedder espone `embed(texts) -> list[list[float]]` con batching interno e
`embed_one(text)`. I vettori sono calcolati qui e passati espliciti a Chroma.
"""
from __future__ import annotations

import httpx

from shared.config import settings

PROVIDERS = ["ollama", "azure-small", "azure-large"]


class Embedder:
    name: str
    dim: int | None = None
    batch_size: int = 64

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            embs = self._embed_batch(texts[i : i + self.batch_size])
            if self.dim is None and embs:
                self.dim = len(embs[0])
            out.extend(embs)
        return out

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


class OllamaEmbedder(Embedder):
    def __init__(self, host: str, model: str):
        self.name = f"ollama:{model}"
        self.host = host.rstrip("/")
        self.model = model

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        r = httpx.post(
            f"{self.host}/api/embed",
            json={"model": self.model, "input": texts},
            timeout=300,
        )
        r.raise_for_status()
        return r.json()["embeddings"]


class AzureEmbedder(Embedder):
    def __init__(self, endpoint: str, api_key: str, deployment: str, name: str):
        self.name = name
        self.url = endpoint.rstrip("/") + "/embeddings"
        self.key = api_key
        self.deployment = deployment

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        r = httpx.post(
            self.url,
            headers={"api-key": self.key},
            json={"model": self.deployment, "input": texts},
            timeout=300,
        )
        r.raise_for_status()
        data = sorted(r.json()["data"], key=lambda d: d["index"])
        return [d["embedding"] for d in data]


def get_embedder(provider: str) -> Embedder:
    s = settings
    if provider == "ollama":
        return OllamaEmbedder(s.ollama_host, s.ollama_embed_model)
    if provider == "azure-small":
        return AzureEmbedder(s.azure_endpoint, s.azure_key, s.azure_embed_small,
                             "azure:text-embedding-3-small")
    if provider == "azure-large":
        return AzureEmbedder(s.azure_endpoint, s.azure_key, s.azure_embed_large,
                             "azure:text-embedding-3-large")
    raise ValueError(f"provider sconosciuto: {provider!r} (attesi: {PROVIDERS})")
