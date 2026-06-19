# Requisiti — Export OpenTelemetry (FEAT-005, epica osservabilità)

> Epica: **`osservabilita`** · decomposizione di **FEAT-005** (Should). Assorbe **REQ-H9** dell'hardening
> (tracing/OTel). Branch: `061-export-otel`. Si innesta sullo strato F1 (eventi già emessi da `log_event`).

## 1. Contesto e problema

Sertor emette eventi strutturati a ogni operazione (`index`, `embeddings` con token/dim, `embeddings_cache`,
`low_confidence`, ricerche/rerank) via `log_event`. F1 (feature 020) li **persiste** localmente con un
`logging.Handler` (`EventPersistenceHandler`) attaccato dal composition root in `enable_observability`,
**senza** toccare `log_event` né i call-site (additivo, non-fatale, privacy-safe). Chi usa già uno stack
di osservabilità LLM (Langfuse/Phoenix/Grafana) non può però **vedere** questi eventi nel proprio backend.

**FEAT-005** aggiunge un **export OpenTelemetry opzionale**: gli stessi eventi sono emessi **anche** verso
un backend OTel esterno (in aggiunta, non al posto, dello store locale — REQ-E4), seguendo le **GenAI
semantic conventions** dove applicabile, **senza** vincolare la licenza di Sertor né aggiungere dipendenze
obbligatorie al core.

**Decisione di design (innesto):** si **rispecchia F1** — un secondo `logging.Handler`
(`OtelExportHandler`) attaccato da `enable_observability` SOLO quando l'extra `[otel]` è installato **e**
l'export è configurato. Legge gli stessi event-record e li mappa a span OTel esportati via OTLP. Additivo,
non-fatale (handleError del framework), privacy-safe (legge i campi già redatti). **Span "flat"** (un span
per evento, timing dall'evento) — niente instrumentazione nidificata invasiva (gap dichiarato, vedi §7).

## 2. User stories
- **US1 (P1) — Export verso il mio backend OTel.** Come operatore che usa già Langfuse/Phoenix/Grafana,
  configuro un endpoint OTLP e vedo gli eventi di Sertor (embeddings, retrieval, index) nel mio backend,
  con gli attributi GenAI standard (modello, provider, token), **senza** strumenti Sertor aggiuntivi.
- **US2 (P1) — Zero impatto se non lo uso.** Come utente che non usa OTel, se non installo l'extra `[otel]`
  o non configuro l'export, **nulla cambia**: nessuna dipendenza, nessun overhead, comportamento identico.
- **US3 (P2) — Privacy by default.** Come utente, di default vengono esportate **solo metriche/attributi**
  (provider, modello, token, conteggi), **mai** il testo delle query, salvo opt-in esplicito (REQ-E8).
- **US4 (P2) — In aggiunta, non al posto.** Come utente con osservabilità persistente attiva, l'export OTel
  **non sostituisce** lo store locale: entrambi ricevono gli eventi.

## 3. Decisioni di design (vincolanti)
- **D1** Innesto = **secondo `logging.Handler`** (`OtelExportHandler`), gemello di `EventPersistenceHandler`,
  attaccato in `enable_observability`. NON si modifica `log_event` né i call-site (additivo).
- **D2** Dipendenze OTel (`opentelemetry-sdk`, `opentelemetry-exporter-otlp`) in **extra opzionale `[otel]`**
  (come `[tui]`/`[graph]`): import **lazy**; assente + export richiesto → `ConfigError` azionabile.
- **D3** Mappatura agli **attributi GenAI semconv**: `embeddings` → span `gen_ai.operation.name=embeddings`
  (`gen_ai.provider.name`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`,
  `gen_ai.embeddings.dimension.count`); ricerca → `gen_ai.operation.name=retrieval`
  (`gen_ai.retrieval.documents`; `query.text` SOLO con opt-in raw-text); `index` e altri → span con
  namespace Sertor (`sertor.operation`, conteggi). Span **flat** (timing dall'evento, `elapsed_ms` se c'è).
- **D4** Config: manopola `SERTOR_OBSERVABILITY_OTEL` (default **off**); l'**endpoint/trasporto** si appoggia
  alle **env var standard OTel** (`OTEL_EXPORTER_OTLP_ENDPOINT`, …) onorate dall'SDK (non si reinventa).
- **D5** Privacy: di default solo attributi-metrica; il testo (`gen_ai.retrieval.query.text`) richiede
  l'opt-in raw-text già definito (REQ-E8/E9). I campi letti sono **già redatti** (come F1).

## 4. Requisiti funzionali (EARS)
### Export (US1/US4)
- **REQ-001 (Optional):** DOVE l'export OTel è abilitato (`SERTOR_OBSERVABILITY_OTEL` on + extra `[otel]`),
  il sistema DEVE emettere gli eventi strutttati che già produce verso un backend OTLP, **in aggiunta**
  allo store locale (mai al suo posto).
- **REQ-002 (Ubiquitous):** L'export DEVE rispecchiare l'innesto di F1 (un `logging.Handler` attaccato in
  `enable_observability`), **senza** modificare `log_event` né i call-site.
- **REQ-003 (Ubiquitous):** Gli span emessi DEVONO usare gli **attributi GenAI semconv** dove applicabile
  (embeddings/retrieval) e un namespace Sertor per le operazioni senza convenzione standard (index, ecc.).
- **REQ-004 (Event):** QUANDO un evento porta i token (`embeddings`), lo span DEVE riportarli in
  `gen_ai.usage.input_tokens`; QUANDO porta la dimensione embedding, in `gen_ai.embeddings.dimension.count`.

### Opzionalità e non-regressione (US2)
- **REQ-005 (Unwanted):** SE l'extra `[otel]` non è installato o l'export non è configurato, ALLORA il
  sistema DEVE comportarsi **esattamente come oggi** (nessun handler OTel, nessun import OTel, nessun
  overhead, nessuna dipendenza).
- **REQ-006 (Unwanted):** SE l'export è richiesto ma l'extra `[otel]` manca, ALLORA il sistema DEVE
  sollevare un `ConfigError` **azionabile** (nomina l'extra), come per `[tui]`.
- **REQ-007 (Ubiquitous):** Il **core** NON DEVE acquisire dipendenze OTel obbligatorie (solo l'extra).

### Robustezza e privacy (US3)
- **REQ-008 (State-driven):** MENTRE un'operazione è in corso, l'export NON DEVE bloccarla né rallentarla
  in modo misurabile (export non-bloccante: batch processor; un guasto dell'export è **non-fatale** —
  il framework di logging instrada l'eccezione a `handleError`, non al chiamante).
- **REQ-009 (Unwanted, privacy):** SE l'opt-in raw-text non è abilitato, ALLORA l'export NON DEVE includere
  il testo delle query/contenuti (solo attributi-metrica); i campi esportati sono quelli **già redatti**.

### Verifica
- **REQ-010 (Ubiquitous):** Una suite **offline** DEVE verificare la mappatura usando un **exporter
  in-memory** OTel (`InMemorySpanExporter`), senza rete né collector reale: asserisce nome span,
  `gen_ai.operation.name`, attributi token/modello/provider per gli eventi chiave.
- **REQ-011 (Unwanted):** SE l'export è disabilitato, ALLORA i test DEVONO attestare che nessun handler
  OTel è attaccato e nessun modulo OTel è importato (non-regressione, REQ-005).

## 5. Requisiti non funzionali
- **NFR-01:** Additivo: `log_event`, i call-site, F1 (store) e i suoi test **invariati**.
- **NFR-02:** Extra `[otel]` isolato; import lazy; core senza nuove dipendenze obbligatorie (NFR coerente con `[tui]`/`[graph]`).
- **NFR-03:** Non-fatale e non-bloccante (batch span processor; handleError).
- **NFR-04:** Privacy-by-default (solo metriche/attributi salvo opt-in raw-text).
- **NFR-05:** Host-agnostico (Principio X): funziona su qualunque ospite, configurato non presunto.

## 6. Criteri di successo
- **CS-1:** Con export abilitato + collector in-memory, dopo N operazioni gli span corrispondenti sono
  emessi con gli attributi GenAI attesi (token/modello/provider/operation).
- **CS-2:** Con export disabilitato/extra assente: 0 handler OTel, 0 import OTel, comportamento identico a oggi.
- **CS-3:** Extra mancante + export richiesto → `ConfigError` che nomina `[otel]`.
- **CS-4:** Lo store locale F1 continua a ricevere gli eventi quando l'export è attivo (REQ-E4).
- **CS-5:** Nessun testo di query negli span senza opt-in raw-text.
- **CS-6:** Suite offline verde (in-memory exporter); suite F1/osservabilità esistenti invariate verdi.

## 7. Ambito
**In ambito:** handler OTel additivo, mappatura GenAI semconv (embeddings/retrieval/index), extra `[otel]`,
manopola config + onoramento env OTel standard, privacy-by-default, suite offline in-memory.
**Fuori ambito / gap dichiarati:**
- **Tracing nidificato idiomatico** (span padre/figlio con context propagation attorno alle operazioni
  live): qui gli span sono **flat/post-hoc** dall'event stream (additivo, gemello di F1). Eventuale
  upgrade a instrumentazione nidificata = follow-up.
- **Metriche OTel** (signal Metrics) e **logs** OTel: qui si esportano **span**; metriche aggregate =
  FEAT-006. Export CSV/MD = FEAT-011.
- Scelta del backend/collector (è dell'ospite); web GUI (FEAT-008).

## 8. Rischi
- **R-1 (semconv in evoluzione):** le GenAI conventions cambiano (sono migrate su repo GitHub versionato).
  *Mitigazione:* attributi centralizzati in un punto unico (mappa), test che pinnano i nomi; aggiornabile.
- **R-2 (span flat poco idiomatici):** alcuni backend preferiscono trace nidificate. *Mitigazione:* gap
  dichiarato; gli span flat con attributi GenAI sono comunque ingeribili da Langfuse/Phoenix.
- **R-3 (overhead export):** *Mitigazione:* batch processor non-bloccante; default off.

## 9. Domande aperte — risolte
- **Q-1** Innesto → **secondo handler gemello di F1** (D1).
- **Q-2** Span vs log/metrics → **span** (GenAI semconv è span-oriented; ingeribile dai backend) (D3).
- **Q-3** Endpoint/config → manopola on/off Sertor + **env var standard OTel** per trasporto/endpoint (D4).
- **Q-4** Privacy → metrics-only di default, testo solo con opt-in raw-text (D5, coerente REQ-E8/E9).
