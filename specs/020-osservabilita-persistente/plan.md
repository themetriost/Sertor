# Implementation Plan: Strato di osservabilità persistente

**Branch**: `020-osservabilita-persistente` | **Date**: 2026-06-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/020-osservabilita-persistente/spec.md`

## Summary

Dare agli eventi strutturati che il core **già** emette via `log_event` un **archivio locale
interrogabile**, additivo e con default spento. Approccio scelto (research D1): **un `logging.Handler`
stdlib** attaccato dal composition root al logger `sertor_core` quando la persistenza è abilitata. Il
handler legge i campi **già strutturati e redatti** dal `LogRecord` (`operation` + campi in `extra`,
istante da `record.created`) e li scrive in uno **store SQLite locale** (stdlib, sotto `index_dir`,
gitignored — simmetrico alla cache della feat. 019). Lo store espone una porta `ObservabilityStore`
(record + query per operation/intervallo) che la feature di aggregazione (FEAT-002) consumerà.

Perché l'handler è la scelta cardine: **(a)** zero modifiche a `log_event` e ai call-site (massima
additività, FR-005); **(b)** non-fatale **by design** — il framework logging non propaga mai
un'eccezione di un handler al chiamante (`Handler.handleError`), quindi FR-007 è soddisfatto senza
codice difensivo nei call-site; **(c)** a persistenza spenta nessun handler è attaccato → zero
overhead, nessuno store creato (FR-004); **(d)** la redazione è già applicata a monte (`extra` contiene
i campi `safe`), quindi FR-009 è gratis.

## Technical Context

**Language/Version**: Python ≥ 3.11

**Primary Dependencies**: **solo stdlib** per la novità — `logging` (Handler), `sqlite3` (store),
`json` (serializzazione campi), `time` (istante). Nessuna nuova dipendenza, nessun extra obbligatorio.

**Storage**: store SQLite `observability.sqlite` sotto `Settings.index_dir` (gitignored). Tabella
`events(id, ts, operation, fields_json)` con indici su `(operation, ts)` e `(ts)`.

**Testing**: pytest, offline. Eventi simulati emessi via `log_event`/logger; store in `tmp_path`;
verifica di cattura, query per operation/tempo, non-fatalità (store corrotto), default-off.

**Target Platform**: libreria `sertor-core`; il consumatore a valle (FEAT-002/TUI) gira ovunque.

**Project Type**: libreria in Clean Architecture (domain/services/adapters/engines/config/observability).

**Performance Goals**: overhead trascurabile sul percorso caldo — gli eventi sono **per-operazione**
(bassa cardinalità: un `index` per indicizzazione, pochi `embeddings`/`retrieve` per operazione), quindi
un insert SQLite sincrono è nell'ordine dei microsecondi; `QueueHandler` documentato come via di fuga se
in futuro la cardinalità crescesse.

**Constraints**: offline-capable; firma `log_event` **invariata** (additivo puro); default off
(retro-compat); degrado non-fatale; privacy-by-default solo-metriche; host-agnostico; append
non-distruttivo.

**Scale/Scope**: corpora/sessioni tipici → migliaia di eventi nell'arco di settimane; SQLite regge con
margine. Retention = solo il **gancio** (politica rinviata, DA-O-b).

## Constitution Check

*GATE: PASS prima della Phase 0 e dopo la Phase 1.* — Costituzione v1.1.0.

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** la persistenza è un **adapter** (handler +
  store SQLite) dietro la porta `ObservabilityStore`; `domain`/`services` non la conoscono — emettono
  via `log_event` (stdlib) come oggi. Wiring solo in `composition.py`. Esercitabile senza cloud. **PASS**
- [x] **II — Boundary & local-first:** `sqlite3`/`logging` (stdlib, locale) dietro l'adapter; nessun
  servizio esterno; funziona identico locale/cloud (è a valle del logging). **PASS**
- [x] **III — YAGNI & unità piccole:** un handler + uno store + una porta (giustificata da un consumatore
  reale, FEAT-002). Nessuna nuova dipendenza/extra. Insert sincrono (no coda) finché la cardinalità non
  lo richiede. SRP (cattura ≠ store ≠ query). **PASS**
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** il degrado non-fatale dell'osservabilità **non** è
  "null silenzioso": un guasto dello store è loggato (warning) e l'operazione osservata prosegue — è la
  policy corretta per un'aggiunta di servizio (come la cache 019). Gli errori reali del core restano
  espliciti. **PASS**
- [x] **V — Testabilità & misure:** test F.I.R.S.T. offline (eventi simulati, store in `tmp_path`,
  store corrotto per la non-fatalità, default-off). Non è feature di qualità-retrieval → no hit@k. **PASS**
- [x] **VI — Idempotenza & non-distruttività:** append non-distruttivo tra run; lo store è un artefatto
  rigenerabile e cancellabile senza perdita di correttezza del core; install≠run (nessuna persistenza
  finché non abilitata e finché non si svolge un'operazione). **PASS**
- [x] **VII — Leggibilità:** naming di dominio (`ObservabilityStore`, `record_event`, `query_events`,
  handler `EventPersistenceHandler`). **PASS**
- [x] **VIII — Configurabilità centralizzata:** nuove manopole **solo** in `Settings`
  (`observability_enabled` default off; sede derivata da `index_dir`; gancio retention), nessun default
  hardcoded. **PASS**
- [x] **IX — Osservabilità:** è *letteralmente* osservabilità; nessun segreto persistito (la redazione è
  già applicata in `extra`); l'attivazione e i guasti dello store sono a loro volta loggati. **PASS**
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** nessuna assunzione d'ospite; sede dello store da config;
  gira su qualunque corpus (code+doc/solo-doc/solo-code) senza modifiche al corpo. **PASS**

**Esito: PASS 10/10 senza deroghe.** Nessuna voce in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/020-osservabilita-persistente/
├── plan.md
├── research.md          # D1 meccanismo (handler) · D2 store · D3 redazione · D4 porta · D5 non-blocking
├── data-model.md        # evento persistito, schema store, manopole
├── quickstart.md        # come abilitare + verificare la cattura
├── contracts/
│   ├── observability-store.md   # porta ObservabilityStore (record + query) — il seam con FEAT-002
│   └── event-capture.md         # il handler: cosa cattura, come, garanzie
└── checklists/requirements.md
```

### Source Code (repository root)

```text
src/sertor_core/
├── domain/ports.py            # MODIF: + porta ObservabilityStore (Protocol runtime_checkable) — la 7ª
├── observability/
│   ├── logging.py             # INVARIATO (la firma di log_event non cambia)
│   ├── store.py               # NUOVO: SqliteObservabilityStore (adapter, sqlite3) — record/query
│   └── capture.py             # NUOVO: EventPersistenceHandler (logging.Handler → store)
├── config/settings.py         # MODIF: + observability_enabled (SERTOR_OBSERVABILITY, default False) + sede/retention-hook
└── composition.py             # MODIF: build dello store + attach del handler al logger SOLO se abilitato (import lazy)

tests/unit/
├── test_observability_store.py     # NUOVO: record/query per operation+tempo, append tra istanze, store corrotto
└── test_observability_capture.py   # NUOVO: cattura via log_event, default-off (no store/no handler), non-fatalità, solo-metriche
```

**Structure Decision**: libreria singola in Clean Architecture (struttura esistente). La novità vive in
`observability/` (store + capture) + una porta in `domain/ports.py` + il wiring in `composition.py` +
una manopola in `config/settings.py`. `domain`/`services` invariati; `log_event` invariato.

## Complexity Tracking

Nessuna violazione costituzionale: tabella non compilata.
