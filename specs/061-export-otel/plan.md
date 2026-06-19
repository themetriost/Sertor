# Implementation Plan: Export OpenTelemetry (FEAT-005)

**Branch**: `061-export-otel` · **Spec**: `specs/061-export-otel/spec.md` · **Requirements**:
`requirements/osservabilita/export-otel/requirements.md` (FEAT-005, epica `osservabilita`).

## Summary

Export OTel **additivo e opzionale** che rispecchia F1: un secondo `logging.Handler`
(`OtelExportHandler`) attaccato in `enable_observability` SOLO con extra `[otel]` + manopola on, che
mappa gli eventi di `log_event` a **span OTel** (GenAI semconv dove applicabile, namespace `sertor.*`
altrove) ed esporta via OTLP. `log_event`/call-site/F1 invariati; core senza dipendenze OTel obbligatorie
(extra lazy, `ConfigError` se assente); non-bloccante/non-fatale; privacy metrics-only. Verifica offline
con `InMemorySpanExporter`.

## Technical Context
- **Pacchetto**: `sertor-core`. Nuovo modulo `src/sertor_core/observability/otel.py`; manopola in
  `Settings`; ramo in `composition.enable_observability`; extra `[otel]` in `pyproject.toml` (+ in `dev`).
- **Seam riusato**: `enable_observability` (composition.py:213) attacca già `EventPersistenceHandler`
  (F1); aggiungiamo accanto `OtelExportHandler`. Stesse 3 proprietà gratis (additivo/non-fatale/privacy).
- **Eventi** (da `log_event`): `embeddings` (provider, texts, tokens?), `index`/`index_file`,
  `query`/`retrieve`/`search`, `rerank`, `low_confidence`, `embeddings_cache`. Campi già **redatti**.
- **OTel**: `opentelemetry-sdk` + `opentelemetry-exporter-otlp-proto-http`; TracerProvider +
  BatchSpanProcessor + OTLPSpanExporter (endpoint/trasporto da env standard OTel). Test:
  `InMemorySpanExporter` + `SimpleSpanProcessor` (offline, deterministico).
- **Tooling**: `uv` (aggiungere `--extra otel`/incluso in `dev`); offline nei test.

## Constitution Check (pre-design) — **PASS 11/11, nessuna deroga**
- **I (core libreria):** `sertor-core` resta importabile **senza** OTel (import lazy nell'extra); il
  dominio non importa l'SDK. ✅
- **II (provider dietro boundary, local-first):** OTel è un *sink* opzionale dietro l'handler; local-first
  preservato (default off, nessun backend richiesto). ✅
- **III (YAGNI, unità piccole, dipendenze isolate):** extra opzionale `[otel]` (come `[tui]`/`[graph]`);
  un handler + una mappa dati. Nessuna nuova astrazione di dominio. ✅
- **IV (errori espliciti):** extra mancante → `ConfigError` azionabile; guasto export → non-fatale via
  `handleError` (nessun null silenzioso nel percorso caldo). ✅
- **V (testabilità da misure):** suite offline con `InMemorySpanExporter` che asserisce span+attributi;
  test "disabilitato → 0 handler/import". ✅
- **VI (idempotenza/non-distruttività):** `enable_observability` idempotente (già); export *in aggiunta*
  allo store, non lo sostituisce; default off = nessun cambiamento. ✅
- **VII (leggibilità):** mappa semconv centralizzata e dati-driven; handler piccolo gemello di F1. ✅
- **VIII (config centralizzata):** manopola `SERTOR_OBSERVABILITY_OTEL` in `Settings`; endpoint via env
  standard OTel (non reinventato). ✅
- **IX (osservabilità):** è osservabilità; non logga segreti (campi già redatti). ✅
- **X (host-agnostico):** funziona su qualunque ospite, configurato non presunto. ✅
- **XI (vehicles):** wiring nel composition root (`enable_observability`), percorso consumer uniforme. ✅

## Phase 1 — Design

**Settings (`config/settings.py`):** `observability_otel_enabled: bool` ← `SERTOR_OBSERVABILITY_OTEL`
(default `False`). (Endpoint/headers: NON nuove manopole — si onorano `OTEL_EXPORTER_OTLP_*` dell'SDK.)

**`observability/otel.py`:**
- `_SEMCONV`: mappa **dati-driven** `operation -> SpanSpec(span_name, gen_ai_operation|None, field_map)`
  dove `field_map: {event_field: otel_attr}` per i campi con attributo GenAI standard
  (`provider→gen_ai.provider.name`, `tokens→gen_ai.usage.input_tokens`, `dim→gen_ai.embeddings.dimension.count`,
  `model→gen_ai.request.model`). I campi non mappati diventano `sertor.<field>`. Punto unico aggiornabile (R-1).
  - `embeddings` → (`embeddings`, op=`embeddings`); `search`/`retrieve`/`query` → (`retrieval`, op=`retrieval`);
    `index`/`index_file` → (`index`, op=None, namespace sertor); `rerank`/`low_confidence`/`embeddings_cache`
    → span sertor.*. **Mai** esportare campi di testo libero (privacy metrics-only, REQ-009).
- `class OtelExportHandler(logging.Handler)`: `__init__(self, tracer)`; `emit(record)`: se `operation`
  presente → costruisce attributi dalla mappa → `span = tracer.start_span(name, attributes=attrs)` →
  `span.end()`. Re-entrancy guard come F1. (Timing: end=record.created; se `elapsed_ms` presente,
  start=end-elapsed.)
- `def build_otel_handler(settings) -> OtelExportHandler`: **import lazy** di `opentelemetry`; se manca →
  `ConfigError('the OTel export requires the extra: uv add "sertor-core[otel]"', key="otel")`. Costruisce
  `TracerProvider` + `BatchSpanProcessor(OTLPSpanExporter())` (endpoint da env), `tracer = provider.get_tracer("sertor")`.

**`composition.enable_observability`:** dopo aver attaccato `EventPersistenceHandler`, se
`settings.observability_otel_enabled` e non già presente un `OtelExportHandler` → `logger.addHandler(build_otel_handler(settings))`.
Idempotente; *in aggiunta* allo store (REQ-E4). Import locale (lazy) come per F1.

**`pyproject.toml`:** `[project.optional-dependencies] otel = ["opentelemetry-sdk>=1.20",
"opentelemetry-exporter-otlp-proto-http>=1.20"]`; aggiungere `otel` all'extra `dev` (per i test, come
mcp/graph). Re-lock `uv`.

**Contratti:** nessuna API runtime nuova; la "guardia" è il test offline.

**Quickstart/verifica:** TracerProvider con `InMemorySpanExporter` + `SimpleSpanProcessor`; `tracer` →
`OtelExportHandler(tracer)` attaccato al logger; emettere eventi (via `log_event` o record sintetici);
asserire `exporter.get_finished_spans()` → nomi/attributi attesi. + `enable_observability` con otel off →
nessun `OtelExportHandler`; import OTel non avvenuto sul percorso disabilitato.

## Fasi di implementazione (mappate alle US)
1. **Foundational (US-verifica):** test `tests/unit/test_otel_export.py` con InMemory exporter (fallisce: modulo assente).
2. **US1 (P1):** `observability/otel.py` (mappa + handler + builder); `Settings.observability_otel_enabled`;
   ramo in `enable_observability`; extra `[otel]` in pyproject (+dev) + `uv sync`.
3. **US2 (P1):** test "disabilitato → 0 handler/0 import"; `ConfigError` se extra assente (simulato).
4. **US3 (P2):** test privacy: nessun campo di testo libero negli attributi span.
5. **Verifica:** suite osservabilità esistente invariata verde; `sertor-core` importabile senza OTel; ruff.

## Constitution Check (post-design) — **PASS 11/11**
Additivo (handler gemello di F1), extra opzionale lazy (core senza dipendenze nuove), non-fatale,
privacy-by-default, host-agnostico. Nessun nuovo concern di complessità da tracciare. Gap dichiarato: span
**flat** post-hoc (non tracing nidificato) — follow-up, non un debito costituzionale.

## Complexity Tracking
Nessuna deviazione. Rischio non-costituzionale: evoluzione delle GenAI semconv (R-1) → mappa centralizzata
+ test che pinnano i nomi degli attributi.
