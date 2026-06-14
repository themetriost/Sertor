# Implementation Plan: Servizio di aggregazione e report dell'osservabilità

**Branch**: `021-osservabilita-report` | **Date**: 2026-06-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/021-osservabilita-report/spec.md` (F2 epica osservabilità)

## Summary

Un **servizio nel core** (`ObservabilityReports`) che legge gli eventi conservati dallo store di F1
(porta `ObservabilityStore.query_events`, già su master) e li **aggrega** in report leggibili: cache
(hit/miss + risparmio stimato), costo (token per provider/intervallo), salute del corpus, latenze
(p50/p95) e affidabilità. Le aggregazioni sono **funzioni pure e deterministiche** sugli eventi; il
servizio non persiste nulla, non fa rete, non ha UI (la consumeranno F3/F4). Solo stdlib.

## Technical Context

**Language/Version**: Python ≥ 3.11

**Primary Dependencies**: **solo stdlib** — `statistics`/calcolo manuale (percentili), `time`/`datetime`
(bucket temporali), `collections` (aggregazioni). Nessuna nuova dipendenza, nessun extra.

**Storage**: nessuno proprio — **legge** dallo store di F1 via la porta `ObservabilityStore`.

**Testing**: pytest, offline. Lo store viene popolato con eventi simulati (in `tmp_path` o un fake
store in memoria che implementa la porta) e si verificano i report.

**Target Platform**: libreria `sertor-core`; consumatori a valle = pannello TUI (F3/F4), CLI.

**Project Type**: libreria in Clean Architecture.

**Performance Goals**: aggregazioni in memoria su migliaia di eventi → millisecondi; nessun requisito
stringente.

**Constraints**: servizio nel core (no UI, Principio I); deterministico (Principio VI); offline
(Principio V); privacy-by-default (aggrega solo metriche conservate); additivo; zero nuove dipendenze.

**Scale/Scope**: migliaia di eventi per intervallo; aggregazione lineare.

## Constitution Check

*GATE: PASS prima della Phase 0 e dopo la Phase 1.* — Costituzione v1.1.0.

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** servizio in `services/`, dipende **solo**
  dalla porta `ObservabilityStore` (astrazione), non dall'adapter SQLite né da UI. Esercitabile con un
  fake store. **PASS**
- [x] **II — Boundary & local-first:** nessun servizio esterno; legge dietro la porta; funziona ovunque. **PASS**
- [x] **III — YAGNI & unità piccole:** funzioni di aggregazione pure + un servizio facciata; nessuna
  dipendenza nuova. SRP per famiglia di report. **PASS**
- [x] **IV — Errori espliciti:** dati assenti → report **vuoto esplicito** (zeri), non un'eccezione né
  `None` ambiguo; è la degradazione onesta richiesta (FR-010). **PASS**
- [x] **V — Testabilità & misure:** test F.I.R.S.T. offline con eventi simulati; le aggregazioni sono
  pure (stesso input → stesso output). **PASS**
- [x] **VI — Idempotenza & determinismo:** i report sono **deterministici** sugli stessi eventi
  (FR-009); nessuno stato mutato. **PASS**
- [x] **VII — Leggibilità:** naming di dominio (`cache_report`, `cost_report`, `latency_report`,
  `SeriesPoint`). **PASS**
- [x] **VIII — Configurabilità centralizzata:** l'unica manopola eventuale (granularità di default) sta
  in `Settings`; nessun default hardcoded nei componenti. **PASS**
- [x] **IX — Osservabilità:** il servizio è *parte* dell'osservabilità; non introduce segreti (aggrega
  campi già redatti). **PASS**
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** nessuna assunzione d'ospite; opera su qualunque corpus. **PASS**

**Esito: PASS 10/10 senza deroghe.**

## Project Structure

```text
src/sertor_core/
├── services/
│   └── observability_report.py   # NUOVO: ObservabilityReports (facciata) + report dataclasses
│                                  #   + funzioni pure di aggregazione (bucket, percentili, savings)
├── composition.py                # MODIF: + build_observability_reports(settings) (riusa build_observability_store)
└── __init__.py                   # MODIF: export build_observability_reports + i report dataclass

tests/unit/
└── test_observability_report.py  # NUOVO: i 5 report su eventi simulati; vuoto esplicito; determinismo
```

**Structure Decision**: il servizio e i suoi report dataclass vivono in
`services/observability_report.py` (auto-contenuti per F2, come `engines/evaluation.py` tiene
`EvalReport` accanto al suo servizio). Il dominio e gli altri servizi non cambiano.

## Complexity Tracking

Nessuna violazione: tabella non compilata.
