"""Test US3 — embeddings via provider intercambiabili (REQ-012/014/015/016)."""
from __future__ import annotations

import httpx
import pytest

from sertor_core.adapters.embeddings.azure import AzureEmbedder
from sertor_core.adapters.embeddings.ollama import OllamaEmbedder
from sertor_core.domain.errors import EmbeddingError


def _ollama_transport(seen_hosts: list[str]):
    def handler(request: httpx.Request) -> httpx.Response:
        seen_hosts.append(request.url.host)
        payload = request.read().decode()
        # un vettore per ciascun input; deterministico in base alla posizione
        import json

        texts = json.loads(payload)["input"]
        embs = [[float(len(t)), float(i)] for i, t in enumerate(texts)]
        return httpx.Response(200, json={"embeddings": embs})

    return httpx.MockTransport(handler)


def test_embed_preserves_count_and_order_in_batches():
    seen: list[str] = []
    client = httpx.Client(transport=_ollama_transport(seen))
    emb = OllamaEmbedder("http://localhost:11434", "nomic", batch_size=2, client=client)
    texts = ["a", "bb", "ccc", "dddd", "e"]
    vecs = emb.embed(texts)
    assert len(vecs) == len(texts)          # conteggio (REQ-014)
    assert vecs[0][0] == 1.0 and vecs[3][0] == 4.0  # ordine preservato fra i batch
    assert emb.dim == 2                       # dimensione scoperta


def test_empty_input_returns_empty_without_network():
    seen: list[str] = []
    client = httpx.Client(transport=_ollama_transport(seen))
    emb = OllamaEmbedder("http://localhost:11434", "nomic", client=client)
    assert emb.embed([]) == []
    assert seen == []                         # nessuna chiamata di rete


def test_local_only_contacts_only_local_host():
    seen: list[str] = []
    client = httpx.Client(transport=_ollama_transport(seen))
    emb = OllamaEmbedder("http://localhost:11434", "nomic", client=client)
    emb.embed(["x", "y"])
    assert set(seen) == {"localhost"}         # local-only: nessun host cloud (REQ-016)


def test_provider_error_raises_structured_embedding_error():
    def boom(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="unavailable")

    client = httpx.Client(transport=httpx.MockTransport(boom))
    emb = OllamaEmbedder("http://localhost:11434", "nomic", client=client)
    with pytest.raises(EmbeddingError) as ei:
        emb.embed(["x"])
    assert ei.value.provider == "ollama:nomic"
    assert ei.value.retriable is True         # 503 è ritentabile (REQ-015)


def test_azure_requires_complete_config():
    with pytest.raises(EmbeddingError):
        AzureEmbedder(endpoint="", api_key="", deployment="")


def test_azure_sorts_results_by_index():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"data": [
                {"index": 1, "embedding": [2.0]},
                {"index": 0, "embedding": [1.0]},
            ]},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    emb = AzureEmbedder("https://x.openai.azure.com", "k", "dep", client=client)
    vecs = emb.embed(["a", "b"])
    assert vecs == [[1.0], [2.0]]             # riordinati per index
