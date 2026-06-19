"""Offline guard for the OTel export (feature 061, FEAT-005).

The export is a twin of F1's persistence handler: a `logging.Handler` that maps `log_event` records
to OpenTelemetry spans. These tests verify the pure mapping + the end-to-end emission via an
`InMemorySpanExporter` (no network, no collector), and the privacy/optionality invariants.
"""
from __future__ import annotations

import logging
import sys

import pytest

from sertor_core.observability.logging import get_logger, log_event
from sertor_core.observability.otel import (
    OtelExportHandler,
    build_otel_handler,
    event_to_span,
)

# --- pure mapping (no OTel) -------------------------------------------------------------------

def test_embeddings_event_maps_to_genai_span():
    name, attrs = event_to_span("embeddings", {"provider": "azure", "texts": 3, "tokens": 50})
    assert name == "embeddings"
    assert attrs["gen_ai.operation.name"] == "embeddings"
    assert attrs["gen_ai.provider.name"] == "azure"
    assert attrs["gen_ai.usage.input_tokens"] == 50
    assert attrs["sertor.texts"] == 3  # non-genai numeric field → sertor namespace


def test_search_event_maps_to_retrieval_span():
    name, attrs = event_to_span("search", {"results": 5, "engine": "hybrid"})
    assert name == "retrieval"
    assert attrs["gen_ai.operation.name"] == "retrieval"
    assert attrs["sertor.results"] == 5
    assert attrs["sertor.engine"] == "hybrid"  # whitelisted categorical string


def test_hybrid_query_maps_to_retrieval_span():
    """FEAT-013: the hybrid engine's `hybrid_query` op is labelled GenAI `retrieval`."""
    name, attrs = event_to_span("hybrid_query", {"fused_k": 5, "dense_hits": 30, "engine": "h"})
    assert name == "retrieval"
    assert attrs["gen_ai.operation.name"] == "retrieval"
    assert attrs["sertor.fused_k"] == 5  # final result count (0 = miss) → hit/miss readable


def test_unknown_operation_maps_to_sertor_namespace():
    name, attrs = event_to_span("index", {"documents": 12, "chunks": 240})
    assert name == "sertor.index"
    assert "gen_ai.operation.name" not in attrs
    assert attrs["sertor.documents"] == 12
    assert attrs["sertor.chunks"] == 240


def test_free_text_and_paths_are_dropped_privacy_by_default():
    """No free text / path / unknown string leaks into the span (metrics-only by default)."""
    _name, attrs = event_to_span(
        "search",
        {"query": "what is my secret plan", "source_path": "C:/secret/file.md", "results": 2},
    )
    assert all("secret" not in str(v) for v in attrs.values())
    assert "sertor.query" not in attrs          # free text dropped
    assert "sertor.source_path" not in attrs    # path dropped
    assert attrs["sertor.results"] == 2         # numeric kept


# --- end-to-end via InMemorySpanExporter -----------------------------------------------------

@pytest.fixture()
def in_memory_handler():
    """An `OtelExportHandler` wired to an in-memory exporter; yields (handler, exporter)."""
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    yield OtelExportHandler(provider.get_tracer("test")), exporter


def test_log_event_emits_span_via_handler(in_memory_handler):
    handler, exporter = in_memory_handler
    logger = get_logger()
    prev_level = logger.level
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    try:
        log_event(logging.INFO, "embeddings", provider="ollama", texts=2, tokens=12)
    finally:
        logger.removeHandler(handler)
        logger.setLevel(prev_level)

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "embeddings"
    assert span.attributes["gen_ai.operation.name"] == "embeddings"
    assert span.attributes["gen_ai.provider.name"] == "ollama"
    assert span.attributes["gen_ai.usage.input_tokens"] == 12


def test_plain_log_is_not_exported(in_memory_handler):
    """A non-structured log (no `operation`) produces no span."""
    handler, exporter = in_memory_handler
    logger = get_logger()
    logger.addHandler(handler)
    try:
        logger.info("just a plain message")
    finally:
        logger.removeHandler(handler)
    assert exporter.get_finished_spans() == ()


# --- optionality / config --------------------------------------------------------------------

def test_build_otel_handler_missing_extra_raises_configerror(monkeypatch):
    """If the `[otel]` extra is absent, the builder raises an actionable ConfigError (REQ-006)."""
    from sertor_core.domain.errors import ConfigError

    # Simulate the extra being absent: make the OTLP exporter import fail.
    monkeypatch.setitem(
        sys.modules, "opentelemetry.exporter.otlp.proto.http.trace_exporter", None
    )
    with pytest.raises(ConfigError) as exc:
        build_otel_handler()
    assert "otel" in str(exc.value).lower()


def test_otel_disabled_attaches_no_handler():
    """`enable_observability` with OTel off attaches no `OtelExportHandler` (REQ-005/011)."""
    from sertor_core.composition import enable_observability
    from sertor_core.config.settings import Settings

    settings = Settings(observability_enabled=False, observability_otel_enabled=False)
    logger = get_logger()
    before = list(logger.handlers)
    assert enable_observability(settings) is False
    assert not any(isinstance(h, OtelExportHandler) for h in logger.handlers)
    assert logger.handlers == before  # nothing attached


# --- enrichment (FEAT-013): outcome/status, level, service.name ------------------------------

def test_event_carries_level_attr(in_memory_handler):
    """Every span gets `sertor.level` (severity visible at a glance)."""
    handler, exporter = in_memory_handler
    logger = get_logger()
    prev = logger.level
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    try:
        log_event(logging.INFO, "embeddings", provider="ollama", texts=1, tokens=4)
    finally:
        logger.removeHandler(handler)
        logger.setLevel(prev)
    assert exporter.get_finished_spans()[0].attributes["sertor.level"] == "INFO"


def test_error_event_sets_span_status_error(in_memory_handler):
    """An error-level event becomes a span with ERROR status + the reason (the OUTCOME)."""
    from opentelemetry.trace import StatusCode

    handler, exporter = in_memory_handler
    logger = get_logger()
    prev = logger.level
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    try:
        log_event(logging.ERROR, "embeddings_error", provider="azure", error="rate limited")
    finally:
        logger.removeHandler(handler)
        logger.setLevel(prev)
    span = exporter.get_finished_spans()[0]
    assert span.name == "sertor.embeddings_error"
    assert span.status.status_code is StatusCode.ERROR
    assert "rate limited" in (span.status.description or "")
    assert span.attributes["sertor.level"] == "ERROR"


def test_resource_service_name_defaults_and_env_override(monkeypatch):
    """`service.name` defaults to the given name; `OTEL_SERVICE_NAME` env wins when set."""
    from sertor_core.observability.otel import _otel_resource

    monkeypatch.delenv("OTEL_SERVICE_NAME", raising=False)
    assert _otel_resource("sertor").attributes["service.name"] == "sertor"
    monkeypatch.setenv("OTEL_SERVICE_NAME", "my-host")
    assert _otel_resource("sertor").attributes["service.name"] == "my-host"
