"""Test US3 — embeddings via interchangeable providers (REQ-012/014/015/016)."""
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
        # one vector per input; deterministic based on position
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
    assert len(vecs) == len(texts)          # count (REQ-014)
    assert vecs[0][0] == 1.0 and vecs[3][0] == 4.0  # order preserved across batches
    assert emb.dim == 2                       # discovered dimension


def test_empty_input_returns_empty_without_network():
    seen: list[str] = []
    client = httpx.Client(transport=_ollama_transport(seen))
    emb = OllamaEmbedder("http://localhost:11434", "nomic", client=client)
    assert emb.embed([]) == []
    assert seen == []                         # no network call


def test_local_only_contacts_only_local_host():
    seen: list[str] = []
    client = httpx.Client(transport=_ollama_transport(seen))
    emb = OllamaEmbedder("http://localhost:11434", "nomic", client=client)
    emb.embed(["x", "y"])
    assert set(seen) == {"localhost"}         # local-only: no cloud host (REQ-016)


def test_provider_error_raises_structured_embedding_error():
    def boom(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="unavailable")

    client = httpx.Client(transport=httpx.MockTransport(boom))
    emb = OllamaEmbedder("http://localhost:11434", "nomic", client=client)
    with pytest.raises(EmbeddingError) as ei:
        emb.embed(["x"])
    assert ei.value.provider == "ollama:nomic"
    assert ei.value.retriable is True         # 503 is retriable (REQ-015)


def test_azure_requires_complete_config():
    with pytest.raises(EmbeddingError):
        AzureEmbedder(endpoint="", api_key="", deployment="")


def _azure_capture(seen_api_version: list[str | None]):
    def handler(request: httpx.Request) -> httpx.Response:
        seen_api_version.append(request.url.params.get("api-version"))
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [1.0]}]})

    return httpx.MockTransport(handler)


def test_azure_v1_endpoint_omits_api_version():
    # v1 surface (`/openai/v1`): sending `api-version` ⇒ HTTP 400, so it must NOT be sent.
    seen: list[str | None] = []
    client = httpx.Client(transport=_azure_capture(seen))
    emb = AzureEmbedder("https://x.openai.azure.com/openai/v1", "k", "dep", client=client)
    emb.embed(["a"])
    assert seen == [None]                      # no api-version on the v1 endpoint


def test_azure_classic_endpoint_sends_api_version():
    seen: list[str | None] = []
    client = httpx.Client(transport=_azure_capture(seen))
    emb = AzureEmbedder(
        "https://x.openai.azure.com", "k", "dep", api_version="2024-10-21", client=client
    )
    emb.embed(["a"])
    assert seen == ["2024-10-21"]              # classic surface: api-version present


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
    assert vecs == [[1.0], [2.0]]             # sorted by index
