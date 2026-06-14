"""Test 019 US2 — token count in the `embeddings` log event (REQ-H5).

Offline F.I.R.S.T. with `httpx.MockTransport`. The field is present when the provider reports it
and OMITTED (not 0/None) when it does not (FR-008/009, SC-005).
"""
from __future__ import annotations

import logging

import httpx

from sertor_core.adapters.embeddings.azure import AzureEmbedder
from sertor_core.adapters.embeddings.ollama import OllamaEmbedder


def _azure(json_body, batch_size: int = 64):
    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=json_body)

    return AzureEmbedder(
        "https://x.openai.azure.com", "k", "dep", batch_size=batch_size,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def _ollama(json_body):
    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=json_body)

    return OllamaEmbedder(
        "http://localhost:11434", "nomic",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def _events(caplog):
    return [r for r in caplog.records if getattr(r, "operation", None) == "embeddings"]


def test_azure_logs_tokens_when_reported(caplog):
    emb = _azure({"data": [{"index": 0, "embedding": [1.0, 2.0]}], "usage": {"total_tokens": 42}})
    with caplog.at_level(logging.INFO, logger="sertor_core"):
        emb.embed(["q"])
    events = _events(caplog)
    assert events
    assert events[-1].tokens == 42
    assert events[-1].texts == 1


def test_azure_omits_tokens_when_absent(caplog):
    emb = _azure({"data": [{"index": 0, "embedding": [1.0, 2.0]}]})  # no usage block
    with caplog.at_level(logging.INFO, logger="sertor_core"):
        emb.embed(["q"])
    events = _events(caplog)
    assert events
    assert not hasattr(events[-1], "tokens")  # omitted, not 0/None (FR-009)


def test_azure_accumulates_tokens_across_batches(caplog):
    # batch_size=1, two texts → two batches; the per-call event sums the token counts.
    emb = _azure(
        {"data": [{"index": 0, "embedding": [1.0]}], "usage": {"total_tokens": 10}}, batch_size=1
    )
    with caplog.at_level(logging.INFO, logger="sertor_core"):
        emb.embed(["a", "b"])
    events = _events(caplog)
    assert events[-1].tokens == 20
    assert events[-1].texts == 2


def test_ollama_tokens_best_effort(caplog):
    emb = _ollama({"embeddings": [[3.0]], "prompt_eval_count": 7})
    with caplog.at_level(logging.INFO, logger="sertor_core"):
        emb.embed(["q"])
    assert _events(caplog)[-1].tokens == 7


def test_ollama_omits_tokens_when_absent(caplog):
    emb = _ollama({"embeddings": [[3.0]]})
    with caplog.at_level(logging.INFO, logger="sertor_core"):
        emb.embed(["q"])
    events = _events(caplog)
    assert events
    assert not hasattr(events[-1], "tokens")
