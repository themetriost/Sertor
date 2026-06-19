# Feature Specification: Export OpenTelemetry (FEAT-005)

**Feature Branch**: `061-export-otel` · **Created**: 2026-06-19 · **Status**: Draft

**Input**: Deriva da `requirements/osservabilita/export-otel/requirements.md` (FEAT-005, epica
`osservabilita`, Should; assorbe REQ-H9). MVP osservabilità F1–F4 già su `master`: gli eventi
strutturati di `log_event` sono persistiti localmente da un `logging.Handler` (F1). Questa feature li
esporta **anche** verso un backend OpenTelemetry esterno (Langfuse/Phoenix/Grafana), **in aggiunta** allo
store locale, seguendo le GenAI semantic conventions, **senza** dipendenze obbligatorie nel core.

---

> **Confine vincolante:** innesto = **secondo `logging.Handler`** (`OtelExportHandler`), gemello di
> `EventPersistenceHandler` di F1, attaccato in `enable_observability` SOLO con extra `[otel]` + export
> configurato. NON si tocca `log_event` né i call-site (additivo). Span **flat** dagli eventi (gap:
> niente tracing nidificato). Dipendenze OTel in **extra opzionale `[otel]`** (import lazy; assente →
> `ConfigError`). Privacy-by-default (solo attributi-metrica; testo solo con opt-in raw-text). `install ≠
> run`. Host-agnostico. `sertor-core` resta importabile senza OTel (Principio I/III).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Export verso il mio backend OTel (P1)
Operatore che usa già uno stack OTel: configura l'endpoint OTLP, abilita l'export, e vede gli eventi di
Sertor (embeddings, retrieval, index) nel backend con attributi GenAI standard (provider, modello, token).

**Independent Test**: con export abilitato e un `InMemorySpanExporter`, dopo alcune operazioni gli span
attesi sono emessi con `gen_ai.operation.name` e gli attributi token/provider corretti.

**Acceptance**:
1. **Given** export abilitato (extra `[otel]` + `SERTOR_OBSERVABILITY_OTEL` on), **When** avviene un
   evento `embeddings` con token, **Then** è emesso uno span `gen_ai.operation.name=embeddings` con
   `gen_ai.usage.input_tokens` = i token e `gen_ai.provider.name` = il provider.
2. **Given** lo stesso export, **When** avviene una ricerca, **Then** è emesso uno span
   `gen_ai.operation.name=retrieval`.
3. **Given** export + store locale entrambi attivi, **When** avviene un evento, **Then** **entrambi** lo
   ricevono (l'export è in aggiunta, non al posto).

### User Story 2 — Zero impatto se non lo uso (P1)
**Acceptance**:
1. **Given** extra `[otel]` non installato e export non configurato, **When** si eseguono index/ricerche,
   **Then** nessun handler OTel è attaccato, nessun modulo OTel è importato, comportamento identico a oggi.
2. **Given** export richiesto ma extra `[otel]` assente, **When** si abilita, **Then** `ConfigError`
   azionabile che nomina l'extra `[otel]`.

### User Story 3 — Privacy by default (P2)
**Acceptance**:
1. **Given** opt-in raw-text NON abilitato, **When** si esporta una ricerca, **Then** lo span NON contiene
   il testo della query (`gen_ai.retrieval.query.text` assente); solo attributi-metrica.

### Edge Cases
- **Guasto dell'export** (collector irraggiungibile) → non-fatale: il framework di logging instrada
  l'eccezione a `handleError`, l'operazione non fallisce; lo store locale e stderr non sono toccati.
- **Operazione senza convenzione GenAI** (`index`, `rerank`) → span con namespace `sertor.*` (no semconv forzato).
- **Evento senza token/modello** → l'attributo è semplicemente omesso (come F1 omette i campi assenti).

## Requirements *(mandatory)*
Vedi `requirements/.../export-otel/requirements.md` (REQ-001..011). In sintesi:
- **FR (export):** handler additivo gemello di F1 (REQ-002); span GenAI semconv dove applicabile +
  namespace Sertor altrove (REQ-003/004); in aggiunta allo store (REQ-001).
- **FR (opzionalità):** extra `[otel]` lazy; assente+richiesto → `ConfigError` (REQ-006); core senza
  dipendenze OTel obbligatorie (REQ-007); disabilitato → identico a oggi (REQ-005).
- **FR (robustezza/privacy):** non-bloccante/non-fatale (REQ-008); metrics-only di default (REQ-009).
- **FR (verifica):** suite offline con `InMemorySpanExporter` (REQ-010); disabilitato → 0 handler/import OTel (REQ-011).

### Key Entities
- **OtelExportHandler**: `logging.Handler` che mappa gli event-record di `log_event` a span OTel.
- **Mappa semconv**: la tabella operazione→(span name, attributi GenAI/Sertor), punto unico aggiornabile.
- **Builder OTel**: configura TracerProvider + OTLP exporter (batch) da config/env; import lazy dell'extra.

## Success Criteria *(mandatory)*
- **SC-001**: export on + in-memory exporter → span con attributi GenAI attesi per gli eventi chiave.
- **SC-002**: export off / extra assente → 0 handler OTel, 0 import OTel, comportamento identico.
- **SC-003**: extra assente + export richiesto → `ConfigError` che nomina `[otel]`.
- **SC-004**: store locale F1 riceve gli eventi anche con export attivo.
- **SC-005**: nessun testo query negli span senza opt-in raw-text.
- **SC-006**: suite offline verde; suite F1/osservabilità esistenti invariate verdi; `sertor-core` importabile senza OTel.

## Assumptions
- L'SDK OTel (`opentelemetry-sdk` + `opentelemetry-exporter-otlp`) è l'extra `[otel]`; il dev env lo
  include per i test (come `[tui]`/`graph` in `dev`).
- L'endpoint/trasporto OTLP è governato dalle **env var standard OTel**; Sertor fornisce solo on/off.
- Span **flat** (post-hoc dagli eventi): accettato come gap; tracing nidificato = follow-up.
- `sertor-core` invariato salvo: nuovo modulo `observability/otel.py`, manopola in `Settings`, ramo in
  `enable_observability`, extra in `pyproject`. F1/store/`log_event` invariati.
