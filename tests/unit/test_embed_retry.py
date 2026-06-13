"""Test 018 US1 — embedding resilience: retry with backoff on transient failures (REQ-H3).

Offline F.I.R.S.T. (`httpx.MockTransport`, injected `sleep`/`rng` → no real wait, deterministic).
Covers SC-001/002/005 and FR-001..006.
"""
from __future__ import annotations

import httpx
import pytest

from sertor_core.adapters.embeddings._retry import RetryPolicy, with_retry
from sertor_core.adapters.embeddings.azure import AzureEmbedder
from sertor_core.adapters.embeddings.ollama import OllamaEmbedder
from sertor_core.domain.errors import EmbeddingError


def _err(retriable: bool) -> EmbeddingError:
    return EmbeddingError("boom", provider="fake", reason="http 429", retriable=retriable)


# --- with_retry (the shared helper) ----------------------------------------------------------

def test_succeeds_after_one_retriable_failure():
    # SC-001: a transient failure followed by success completes without intervention.
    calls = {"n": 0}
    waits: list[float] = []

    def fn():
        calls["n"] += 1
        if calls["n"] == 1:
            raise _err(True)
        return "ok"

    out = with_retry(fn, RetryPolicy(3, 0.5), sleep=waits.append, rng=lambda: 0.0)
    assert out == "ok"
    assert calls["n"] == 2
    assert waits == [0.25]  # base*2**0*(0.5+0.0) = 0.5*1*0.5


def test_exhausts_attempts_then_raises():
    # SC-002: persistent retriable failures raise EmbeddingError after `attempts`, bounded waits.
    calls = {"n": 0}
    waits: list[float] = []

    def fn():
        calls["n"] += 1
        raise _err(True)

    with pytest.raises(EmbeddingError):
        with_retry(fn, RetryPolicy(3, 0.5), sleep=waits.append, rng=lambda: 0.0)
    assert calls["n"] == 3            # total attempts
    assert len(waits) == 2            # one wait between each attempt (no wait after the last)


def test_non_retriable_fails_immediately():
    # FR-004: a non-retriable failure is not retried.
    calls = {"n": 0}
    waits: list[float] = []

    def fn():
        calls["n"] += 1
        raise _err(False)

    with pytest.raises(EmbeddingError):
        with_retry(fn, RetryPolicy(3, 0.5), sleep=waits.append, rng=lambda: 0.0)
    assert calls["n"] == 1
    assert waits == []


def test_single_attempt_disables_retry():
    # FR-006: max_attempts=1 → one call, no retry (today's behaviour).
    calls = {"n": 0}
    waits: list[float] = []

    def fn():
        calls["n"] += 1
        raise _err(True)

    with pytest.raises(EmbeddingError):
        with_retry(fn, RetryPolicy(1, 0.5), sleep=waits.append, rng=lambda: 0.0)
    assert calls["n"] == 1
    assert waits == []


def test_backoff_is_exponential():
    waits: list[float] = []

    def fn():
        raise _err(True)

    with pytest.raises(EmbeddingError):
        with_retry(fn, RetryPolicy(3, 1.0), sleep=waits.append, rng=lambda: 0.0)
    assert waits == [0.5, 1.0]  # 1*2**0*0.5, 1*2**1*0.5


def test_attempts_below_one_normalised():
    assert RetryPolicy(0, 0.5).attempts == 1
    assert RetryPolicy(3, 0.5).attempts == 3


# --- embedder level: retry is applied per batch ----------------------------------------------

def _transport(fail_times: int, status: int = 429):
    state = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if state["n"] < fail_times:
            state["n"] += 1
            return httpx.Response(status, text="transient")
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [1.0, 2.0]}]})

    return httpx.MockTransport(handler)


def test_azure_retries_then_succeeds():
    waits: list[float] = []
    client = httpx.Client(transport=_transport(fail_times=1))
    emb = AzureEmbedder(
        "https://x.openai.azure.com", "k", "dep", client=client,
        retry=RetryPolicy(3, 0.5), sleep=waits.append, rng=lambda: 0.0,
    )
    assert emb.embed(["q"]) == [[1.0, 2.0]]   # SC-001 at embedder level
    assert len(waits) == 1                      # one retry happened


def test_azure_exhausts_and_raises():
    waits: list[float] = []
    client = httpx.Client(transport=_transport(fail_times=99, status=500))
    emb = AzureEmbedder(
        "https://x.openai.azure.com", "k", "dep", client=client,
        retry=RetryPolicy(3, 0.5), sleep=waits.append, rng=lambda: 0.0,
    )
    with pytest.raises(EmbeddingError) as ei:
        emb.embed(["q"])
    assert ei.value.retriable is True
    assert len(waits) == 2


def test_retry_is_per_batch_not_whole_call():
    # batch_size=1, two texts → 3 requests: batch1 fails once then ok, batch2 ok at once.
    # A single retry (not two) proves the retry wraps the BATCH, not the whole embed().
    waits: list[float] = []
    client = httpx.Client(transport=_transport(fail_times=1))
    emb = AzureEmbedder(
        "https://x.openai.azure.com", "k", "dep", batch_size=1, client=client,
        retry=RetryPolicy(3, 0.5), sleep=waits.append, rng=lambda: 0.0,
    )
    vecs = emb.embed(["a", "b"])
    assert len(vecs) == 2          # both texts embedded
    assert len(waits) == 1         # exactly one retry, only for the failed batch


def test_ollama_retries_then_succeeds():
    state = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if state["n"] == 0:
            state["n"] += 1
            return httpx.Response(429, text="rate limited")
        return httpx.Response(200, json={"embeddings": [[3.0, 4.0]]})

    waits: list[float] = []
    client = httpx.Client(transport=httpx.MockTransport(handler))
    emb = OllamaEmbedder(
        "http://localhost:11434", "nomic", client=client,
        retry=RetryPolicy(3, 0.5), sleep=waits.append, rng=lambda: 0.0,
    )
    assert emb.embed(["q"]) == [[3.0, 4.0]]
    assert len(waits) == 1


def test_no_retry_policy_behaves_as_before():
    # retry=None (default direct construction) → a transient error propagates at the first failure.
    client = httpx.Client(transport=_transport(fail_times=99, status=503))
    emb = OllamaEmbedder("http://localhost:11434", "nomic", client=client)
    with pytest.raises(EmbeddingError):
        emb.embed(["q"])
