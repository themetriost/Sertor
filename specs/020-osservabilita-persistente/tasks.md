# Tasks — Strato di osservabilità persistente (feature 020)

**Branch**: `020-osservabilita-persistente` | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Task ordinati per dipendenze, per user story. `[P]` = parallelizzabile (file diversi). MVP = **US1**.
Tutti i test sono **offline** (Principio V): `uv run pytest -m "not cloud"`; lint `uv run ruff check .`.

---

## Phase 1 — Setup

- **T001** — Baseline verde: `uv run pytest -m "not cloud"` e `uv run ruff check src/ tests/` passano sullo
  stato attuale del branch (punto di partenza pulito).

## Phase 2 — Foundational (prerequisiti condivisi)

- **T002** — `domain/ports.py`: aggiungi `ObservedEvent` (dataclass di dominio `(ts: float,
  operation: str, fields: dict)`) e la **7ª porta** `ObservabilityStore` (`Protocol`
  `runtime_checkable`): `record_event(ts, operation, fields)` + `query_events(operation, since, until)
  -> list[ObservedEvent]`. [data-model §2, contracts/observability-store]
- **T003** — `config/settings.py`: campo `observability_enabled: bool = False` + wiring in `load()`
  (`_bool_env("SERTOR_OBSERVABILITY", False)`). Commento d'intenzione (manopola di osservabilità,
  default off). [FR-004/010, data-model §5]

## Phase 3 — US1: I numeri restano e si possono ritrovare (Priority P1, MVP)

**Obiettivo**: gli eventi emessi vengono conservati e recuperabili per operation+intervallo (SC-001/002).

- **T004** — `observability/store.py` (NUOVO): `SqliteObservabilityStore(index_dir)` implementa
  `ObservabilityStore`. File `<index_dir>/observability.sqlite`; tabella
  `events(id INTEGER PK, ts REAL, operation TEXT, fields TEXT)` con indici `(operation, ts)` e `(ts)`,
  `CREATE IF NOT EXISTS` lazy. `record_event` → `INSERT` (serializza `fields` in JSON); `query_events`
  → `SELECT ... WHERE` con filtri opzionali (operation/since/until), ordinato per `ts`, deserializza
  JSON → `ObservedEvent`. **Degrado non-fatale**: cattura `sqlite3.Error` in record/query →
  no-op/`[]` + `log_event(WARNING, "observability_store_unavailable", reason=…)`, mai solleva.
  [FR-001/003/007/012, data-model §1/§3]
- **T005** — `observability/capture.py` (NUOVO): `EventPersistenceHandler(store)` (`logging.Handler`).
  `emit(record)`: se `record` NON ha `operation` → return (ignora i log non strutturati); altrimenti
  estrai i **campi applicativi** = `record.__dict__` meno gli attributi standard del `LogRecord`
  (`RESERVED = set(vars(logging.makeLogRecord({})))`) meno `operation`, e chiama
  `store.record_event(record.created, record.operation, fields)`. Le eccezioni in `emit` sono gestite
  dal framework (`handleError`) → non-fatali. [FR-002/005/006/007/008/009, contracts/event-capture]
- **T006** — `composition.py`: factory `build_observability_store(settings)` (import lazy di
  `SqliteObservabilityStore`) e funzione di **attach** che, **solo se** `settings.observability_enabled`,
  costruisce lo store e fa `logging.getLogger("sertor_core").addHandler(EventPersistenceHandler(store))`.
  Idempotente (non attaccare due volte lo stesso tipo di handler). Esponi `build_observability_store`
  da `__init__.py` (seam per FEAT-002). [FR-004/010/011/013, contracts/event-capture §wiring]
- **T007** — `tests/unit/test_observability_store.py` (NUOVO):
  1. record + query_events per **operation e intervallo** → restituisce esattamente gli eventi attesi,
     ordinati per ts. [SC-001/002]
  2. `query_events(None, None, None)` → tutti gli eventi.
  3. **append tra istanze**: una nuova `SqliteObservabilityStore` sullo stesso `index_dir` vede gli
     eventi scritti prima (FR-012).
  4. **degrado non-fatale**: file corrotto (byte spazzatura) → `record_event` no-op + warning,
     `query_events` → `[]` + warning, nessuna eccezione. [FR-007]
  5. `fields` round-trip (dict con int/str/list) corretto via JSON.
- **T008** — `tests/unit/test_observability_capture.py` (NUOVO):
  1. **cattura end-to-end**: attacca `EventPersistenceHandler(store)` al logger `sertor_core`, emetti
     via `log_event(INFO, "index", documents=3, chunks=12)` → lo store contiene un evento `index` con
     `fields={documents:3, chunks:12}` e un `ts`. [SC-001]
  2. **ignora i log non strutturati**: un `logger.info("ciao")` senza `operation` → nessun evento nello
     store. [FR-002 contrario]
  3. **privacy/redazione**: `log_event(INFO, "x", api_key="s3cr3t", n=1)` → nello store il campo
     `api_key` è `***` (già redatto a monte), `n=1` presente. [FR-008/009, SC-006]
  4. **non-fatale a livello handler**: store che solleva in `record_event` → `logger`/operazione non
     si interrompe (l'emit non propaga). [FR-007]

## Phase 4 — US2: Chi non la attiva non vede cambiamenti (Priority P2)

- **T009** — `tests/unit/test_observability_capture.py` (estendi): **default-off** — con
  `observability_enabled=False`, `build`/attach NON aggiunge alcun handler e NESSUN file
  `observability.sqlite` è creato dopo un'operazione simulata; il comportamento di logging resta
  invariato. [FR-004, SC-003]

## Phase 5 — US3: Non rompere né rallentare (Priority P3)

- **T010** — `tests/unit/test_observability_capture.py` (estendi): **resilienza** — con un handler
  attaccato e uno store guasto (non scrivibile/corrotto), un'operazione simulata (sequenza di
  `log_event`) **completa** senza eccezioni e il guasto è segnalato (warning
  `observability_store_unavailable`). [FR-007, SC-004]. *(Overhead: coperto dal design — insert sincrono
  a bassa cardinalità; nessun micro-benchmark in CI.)*

## Phase 6 — Polish & chiusura

- **T011** [P] — Git-ignore: `observability.sqlite` vive sotto `index_dir` (`.index*`) → già coperto;
  aggiungi nota/asserzione se serve. Template `.env` (`packages/sertor/.../assets/rag/env.*.tmpl`) +
  `docs/install.md`: documenta `SERTOR_OBSERVABILITY` (commento in inglese, tema lingua). [FR-010]
- **T012** — Suite completa verde + ruff pulito: `uv run pytest -m "not cloud"` (root + packages) e
  `uv run ruff check src/ tests/ packages/`. Retro-compatibilità: default-off invariato (SC-003).
- **T013** — *(post-merge, non in questa fase)*: re-index del corpus `sertor`; opzionale abilitare
  `SERTOR_OBSERVABILITY=true` sul dogfood per iniziare a raccogliere eventi (utile a FEAT-002).

---

## Coverage FR → task

| FR | Task |
|---|---|
| FR-001 (persistenza completa) | T004, T005, T008.1 |
| FR-002 (tutti i tipi, no sottoinsieme) | T005, T008.2 |
| FR-003 (query per operation/tempo) | T004, T007.1/2 |
| FR-004 (default off = oggi) | T003, T006, T009 |
| FR-005 (additivo, log_event invariato) | T005 (legge il record, non lo tocca), T012 |
| FR-006 (non-bloccante) | T005 (sincrono bassa cardinalità), design |
| FR-007 (degrado non-fatale) | T004, T005, T007.4, T008.4, T010 |
| FR-008 (solo metriche di default) | T005, T008.3 |
| FR-009 (redazione anche nello store) | T005 (legge `extra` già redatto), T008.3 |
| FR-010 (manopole in config) | T003, T006, T011 |
| FR-011 (sede da config, gitignored) | T004, T006, T011 |
| FR-012 (append non-distruttivo) | T004, T007.3 |
| FR-013 (host-agnostico) | T004/T006 (sede da index_dir), T012 |

## Percorso critico

Setup (T001) → Foundational (T002/T003) → **US1** T004→T005→T006→T007/T008 (MVP). US2 (T009) e US3
(T010) estendono i test dopo il wiring. Polish (T011-T012). T004/T005 in serie concettuale (capture usa
lo store), file diversi.
