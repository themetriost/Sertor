"""OpenTelemetry export: a SECOND sink for the events the core already emits (061, FEAT-005).

Twin of `EventPersistenceHandler` (F1, `capture.py`): `OtelExportHandler` is a `logging.Handler` the
composition root attaches to the `sertor_core` logger ONLY when the `[otel]` extra is installed AND
the export is enabled. It maps each structured `log_event` record to an OpenTelemetry **span**
(GenAI semantic conventions where applicable, a `sertor.*` namespace otherwise) and lets the
configured OTLP exporter ship it — IN ADDITION to (never instead of) the local store (REQ-E4).

Same three properties as F1, for free from the logging framework:
- **additive**: `log_event`'s signature and the call-sites are unchanged;
- **non-fatal**: a handler exception goes to `Handler.handleError`, never to the caller — an export
  outage cannot fail an indexing/search;
- **privacy**: `log_event` puts ALREADY-redacted fields on the record; on top of that the handler is
  **metrics-only by default** — it exports numeric/bool fields and a small whitelist of safe
  categorical strings, and **never** free text (query text, paths) — no content reaches the backend.

Span timing is **flat/post-hoc**: one span per event (the GenAI attributes carry the data). Nested
tracing (parent/child spans around live operations) is a declared follow-up. The OTLP
endpoint/transport come from the standard `OTEL_EXPORTER_OTLP_*` env vars (honoured by the SDK).
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sertor_core.domain.errors import ConfigError

if TYPE_CHECKING:  # pragma: no cover - typing only; no runtime OTel import in the core
    from opentelemetry.trace import Tracer

# Standard LogRecord attribute names: everything else on the record is an applicative field that
# `log_event` added via `extra` (same computation as `capture._RESERVED`).
_RESERVED = set(vars(logging.makeLogRecord({}))) | {
    "operation", "message", "asctime", "taskName",
}

# Event field → GenAI semantic-convention attribute (single source, R-1: easy to update when the
# conventions evolve). Other fields fall back to `sertor.<field>` (numeric/bool) or are dropped.
_GENAI_ATTR = {
    "provider": "gen_ai.provider.name",
    "tokens": "gen_ai.usage.input_tokens",
    "model": "gen_ai.request.model",
    "dim": "gen_ai.embeddings.dimension.count",
}

# Operation → (span name, gen_ai.operation.name | None). Ops with a GenAI convention map to it; the
# rest get a `sertor.<op>` span (no convention forced).
_OP_SPEC = {
    "embeddings": ("embeddings", "embeddings"),
    "search": ("retrieval", "retrieval"),
    "retrieve": ("retrieval", "retrieval"),
    "query": ("retrieval", "retrieval"),
    "hybrid_query": ("retrieval", "retrieval"),  # hybrid engine's retrieval op (engine in a tag)
}

# Categorical string fields safe to export. Any OTHER string value is dropped (privacy-by-default:
# query text, file paths, free text never reach the backend).
_SAFE_STR_FIELDS = frozenset(
    {"provider", "backend", "model", "engine", "store", "corpus", "reason", "kind"}
)


def event_to_span(operation: str, fields: dict) -> tuple[str, dict]:
    """Pure mapping: (span_name, attributes) for an event. Testable without OTel.

    GenAI attributes for known fields; `sertor.<field>` for other numeric/bool fields; safe
    categorical strings whitelisted; everything else (free text) is dropped (privacy-by-default).
    """
    span_name, genai_op = _OP_SPEC.get(operation, (f"sertor.{operation}", None))
    attrs: dict = {}
    if genai_op is not None:
        attrs["gen_ai.operation.name"] = genai_op
    for key, value in fields.items():
        if key in _RESERVED:
            continue
        if key in _GENAI_ATTR:
            attrs[_GENAI_ATTR[key]] = value
        elif isinstance(value, bool) or isinstance(value, (int, float)):
            attrs[f"sertor.{key}"] = value
        elif isinstance(value, str) and key in _SAFE_STR_FIELDS:
            attrs[f"sertor.{key}"] = value
        # else: dropped (free text / unknown string / path) — privacy-by-default
    return span_name, attrs


class OtelExportHandler(logging.Handler):
    """Exports structured `log_event` records as OpenTelemetry spans (twin of F1's handler)."""

    def __init__(self, tracer: Tracer):
        super().__init__()
        self._tracer = tracer
        self._in_emit = False  # re-entrancy guard: a failed export emits its own log_event

    def emit(self, record: logging.LogRecord) -> None:
        operation = getattr(record, "operation", None)
        if operation is None:
            return  # plain log, not a structured event
        if self._in_emit:
            return
        self._in_emit = True
        try:
            fields = {k: v for k, v in record.__dict__.items() if k not in _RESERVED}
            span_name, attrs = event_to_span(operation, fields)
            attrs["sertor.level"] = record.levelname  # severity on every span (INFO/WARNING/ERROR)
            span = self._tracer.start_span(span_name, attributes=attrs)
            # The OUTCOME of the operation: an error-level event (embeddings_error, store_error, …)
            # becomes a RED span carrying the reason — visible at a glance, not just another span.
            if record.levelno >= logging.ERROR:
                from opentelemetry.trace import Status, StatusCode

                reason = fields.get("error") or fields.get("reason") or record.getMessage()
                span.set_status(Status(StatusCode.ERROR, str(reason)[:300]))
            span.end()
        finally:
            self._in_emit = False


def _otel_resource(service_name: str):
    """OTel `Resource` carrying `service.name` (lazy import). The standard `OTEL_SERVICE_NAME` env
    wins when set; otherwise the default is `service_name` (so the backend labels the service
    `sertor` out of the box, without requiring the env var)."""
    import os

    from opentelemetry.sdk.resources import Resource

    name = os.getenv("OTEL_SERVICE_NAME") or service_name
    return Resource.create({"service.name": name})


def build_otel_handler(service_name: str = "sertor") -> OtelExportHandler:
    """Build the OTel export handler from the configured OTLP exporter (lazy import of the extra).

    Missing extra → actionable `ConfigError` (like `[tui]`). The OTLP exporter reads its endpoint
    and transport from the standard `OTEL_EXPORTER_OTLP_*` env vars; a `BatchSpanProcessor` keeps
    the export non-blocking (the hot path never waits on the network). `service.name` defaults to
    `service_name` so the backend labels the service correctly without extra config (FEAT-013).
    """
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as exc:  # pragma: no cover - exercised via a simulated-missing test
        raise ConfigError(
            'the OTel export requires the extra: uv add "sertor-core[otel]" '
            "(opentelemetry-sdk + otlp exporter)",
            key="otel",
        ) from exc
    provider = TracerProvider(resource=_otel_resource(service_name))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    return OtelExportHandler(provider.get_tracer(service_name))
