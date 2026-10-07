"""Test 137 — embedding provider on the OpenAI API (contract: openai-embedding-provider.md).

Offline F.I.R.S.T. with `httpx.MockTransport`: request shape, ordering/batching, error
classification, per-batch retry, token signal, key never exposed, custom base URL.
"""
from __future__ import annotations

import json
import logging

import httpx
import pytest

from sertor_core.adapters.embeddings._retry import RetryPolicy
from sertor_core.adapters.embeddings.openai import OpenAIEmbedder
from sertor_core.domain.errors import EmbeddingError

_KEY = "sk-test-secret-0123456789"


def _ok_handler(seen: list[httpx.Request], usage: dict | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        texts = json.loads(request.read().decode())["input"]
        # Return data in REVERSE order: the adapter must restore input order from `index`.
        data = [
            {"index": i, "embedding": [float(len(t)), float(i), 0.5]}
            for i, t in reversed(list(enumerate(texts)))
        ]
        body: dict = {"data": data}
        if usage is not None:
            body["usage"] = usage
        return httpx.Response(200, json=body)

    return handler


def _embedder(handler, **kw) -> OpenAIEmbedder:
    kw.setdefault("base_url", "https://api.openai.com/v1")
    kw.setdefault("api_key", _KEY)
    kw.setdefault("model", "text-embedding-3-large")
    return OpenAIEmbedder(client=httpx.Client(transport=httpx.MockTransport(handler)), **kw)


# --- US1: request shape, ordering, batching, identity ------------------------------------------


@pytest.mark.parametrize("base_url", ["https://api.openai.com/v1", "https://api.openai.com/v1/"])
def test_posts_to_embeddings_under_base_url(base_url):
    seen: list[httpx.Request] = []
    _embedder(_ok_handler(seen), base_url=base_url).embed(["x"])
    assert str(seen[0].url) == "https://api.openai.com/v1/embeddings"
    assert seen[0].method == "POST"


def test_uses_bearer_credential_and_no_azure_specifics():
    seen: list[httpx.Request] = []
    _embedder(_ok_handler(seen)).embed(["x"])
    req = seen[0]
    assert req.headers["authorization"] == f"Bearer {_KEY}"
    assert "api-key" not in req.headers
    assert "api-version" not in req.url.params


def test_payload_carries_model_and_input():
    seen: list[httpx.Request] = []
    _embedder(_ok_handler(seen), model="text-embedding-3-small").embed(["a", "b"])
    assert json.loads(seen[0].read().decode()) == {
        "model": "text-embedding-3-small",
        "input": ["a", "b"],
    }


def test_order_restored_and_batched():
    seen: list[httpx.Request] = []
    emb = _embedder(_ok_handler(seen), batch_size=2)
    vecs = emb.embed(["a", "bb", "ccc", "dddd", "e"])
    assert [v[0] for v in vecs] == [1.0, 2.0, 3.0, 4.0, 1.0]   # input order, across batches
    assert len(seen) == 3                                       # ceil(5 / 2) requests
    assert emb.dim == 3                                         # from the first response


def test_name_includes_model():
    assert _embedder(_ok_handler([])).name == "openai:text-embedding-3-large"


def test_empty_input_makes_no_request():
    seen: list[httpx.Request] = []
    assert _embedder(_ok_handler(seen)).embed([]) == []
    assert seen == []


@pytest.mark.parametrize(
    ("field", "label"),
    [("api_key", "api_key"), ("model", "model"), ("base_url", "base_url")],
)
def test_incomplete_configuration_fails_at_construction(field, label):
    with pytest.raises(EmbeddingError) as ei:
        _embedder(_ok_handler([]), **{field: ""})
    assert ei.value.retriable is False
    assert label in ei.value.reason
    assert ei.value.provider == "openai"


# --- US2: errors, retry, token signal, no key leak ---------------------------------------------


def _status_handler(status: int):
    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"error": {"message": f"echo {_KEY}"}})

    return handler


@pytest.mark.parametrize(("status", "retriable"), [(401, False), (400, False), (429, True),
                                                    (503, True)])
def test_http_errors_are_classified(status, retriable):
    with pytest.raises(EmbeddingError) as ei:
        _embedder(_status_handler(status)).embed(["x"])
    assert ei.value.reason == f"http {status}"
    assert ei.value.retriable is retriable
    assert ei.value.provider == "openai:text-embedding-3-large"


def test_unreachable_service_is_retriable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(EmbeddingError) as ei:
        _embedder(handler).embed(["x"])
    assert ei.value.retriable is True
    assert ei.value.reason == "ConnectError"


def test_retry_is_per_batch():
    state = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if state["n"] == 0:
            state["n"] += 1
            return httpx.Response(429, text="rate limited")
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [1.0]}]})

    waits: list[float] = []
    emb = _embedder(handler, batch_size=1, retry=RetryPolicy(3, 0.5), sleep=waits.append,
                    rng=lambda: 0.0)
    assert len(emb.embed(["a", "b"])) == 2
    assert len(waits) == 1     # only the failed batch was retried


def test_key_never_exposed_in_error_or_events(caplog):
    with caplog.at_level(logging.DEBUG, logger="sertor_core"):
        with pytest.raises(EmbeddingError) as ei:
            _embedder(_status_handler(401)).embed(["x"])
    err = ei.value
    assert _KEY not in str(err)
    assert _KEY not in (err.reason or "")
    assert any(getattr(r, "operation", None) == "embeddings_error" for r in caplog.records)
    for record in caplog.records:
        assert _KEY not in record.getMessage()
        assert all(_KEY not in str(v) for v in vars(record).values())


def _embeddings_events(caplog):
    return [r for r in caplog.records if getattr(r, "operation", None) == "embeddings"]


def test_logs_tokens_when_reported(caplog):
    with caplog.at_level(logging.INFO, logger="sertor_core"):
        _embedder(_ok_handler([], usage={"total_tokens": 7})).embed(["q"])
    event = _embeddings_events(caplog)[-1]
    assert event.tokens == 7
    assert event.provider == "openai:text-embedding-3-large"


def test_omits_tokens_when_absent(caplog):
    with caplog.at_level(logging.INFO, logger="sertor_core"):
        _embedder(_ok_handler([])).embed(["q"])
    assert not hasattr(_embeddings_events(caplog)[-1], "tokens")


# --- US4: OpenAI-compatible service through the composition root -------------------------------


def test_custom_base_url_via_build_embedder(monkeypatch):
    from sertor_core.adapters.embeddings import _openai_protocol
    from sertor_core.composition import build_embedder
    from sertor_core.config.settings import Settings

    seen: list[httpx.Request] = []
    real_client = httpx.Client
    monkeypatch.setattr(
        _openai_protocol.httpx, "Client",
        lambda **_kw: real_client(transport=httpx.MockTransport(_ok_handler(seen))),
    )
    settings = Settings(embed_provider="openai", openai_api_key=_KEY,
                        openai_base_url="http://localhost:8080/v1", embed_cache_enabled=False)
    build_embedder(settings).embed(["x"])
    assert str(seen[0].url) == "http://localhost:8080/v1/embeddings"
