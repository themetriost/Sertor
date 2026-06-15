# Implementation Plan: Consumo sicuro per costruzione (Gruppo A, Principio XI)

**Branch**: `041-consumo-sicuro-vehicles` | **Date**: 2026-06-15 | **Spec**: [spec.md](spec.md)

**Input**: `specs/041-consumo-sicuro-vehicles/spec.md` · requisiti
`requirements/sertor-core/enforcement-principio-xi/requirements.md` (gruppo A).

## Summary

Cablare l'attivazione dell'osservabilità **dentro le factory consumer-entry del composition root**
(`build_indexer`/`build_facade`/`build_engine`/`build_baseline_engine`/`build_graph_service`), così che
**qualunque** percorso d'ingresso — incluso `build_indexer().index()` diretto — applichi i concern
trasversali come fanno oggi solo CLI/MCP. Chiude il gap verificato (re-index via libreria non tracciato).
Additivo, idempotente, no-op a osservabilità disabilitata. Principio I preservato (libreria importabile;
eccezione test). `__init__` non ristretto (FR-007 rinviato).

## Technical Context

**Language/Version**: Python ≥ 3.11. **Primary Dependencies**: nessuna nuova (riusa
`enable_observability` esistente, stdlib). **Storage**: invariato (`observability.sqlite` solo se
abilitato). **Testing**: pytest. **Project Type**: libreria (`sertor-core`). **Constraints**: additivo,
idempotente, default-off invariato, nessuna dipendenza core→CLI/MCP.

## Design (decisione)

- **D1 — Helper di wiring nel composition root.** Introdurre `_wire_runtime(settings)` (interno a
  `composition.py`) che chiama `enable_observability(settings)` (già idempotente, già no-op se off).
  Invocarlo all'inizio delle factory **consumer-entry**: `build_indexer`, `build_facade`,
  `build_engine`, `build_baseline_engine`, `build_graph_service`. È il punto unico dei concern
  trasversali (estendibile in futuro: validazioni/config). Le dipendenze restano verso l'interno
  (NFR-1/Principio I): il wiring vive nel root, non nei servizi.
- **D2 — CLI/MCP invariati.** `cli/__main__.py` e `sertor_mcp/server.py` continuano a chiamare
  `enable_observability` (idempotente → nessun doppio effetto); i test
  `test_index_wires_observability`/`test_main_wires_observability` restano validi (SC-004). Nessuna
  rimozione ora (churn minimo).
- **D3 — Gli altri concern sono già a posto.** Configurazione già centralizzata in `Settings`;
  avvolgimento errori già al boundary negli adapter (es. `VectorStoreError`). REQ-A1 "uniforme" è quindi
  soddisfatto dal cablaggio dell'osservabilità (l'unico bypassato). Documentare in `research.md`.
- **D4 — Superficie pubblica.** `__init__` NON ristretto (FR-007 Should rinviato): nessuna rimozione di
  export. Le factory restano l'ingresso documentato.

## Constitution Check (v1.2.0)

- [x] **I — Dipendenze verso l'interno (NON-NEG.):** il wiring resta nel composition root; nessun import
  core→CLI/MCP; libreria importabile, test diretti (FR-003). **PASS.**
- [x] **II — Boundary & local-first:** invariato. **PASS.**
- [x] **III — YAGNI & unità piccole:** un helper minimo, nessuna astrazione speculativa. **PASS.**
- [x] **IV — Errori espliciti:** invariato (wrapping già al boundary). **PASS.**
- [x] **V — Testabilità:** test diretto del gap-closure + non-regressione; mock/no cloud. **PASS.**
- [x] **VI — Idempotenza & non-distruttività:** attivazione idempotente; default-off no-op. **PASS.**
- [x] **VII — Leggibilità:** helper nominato, guard-clause. **PASS.**
- [x] **VIII — Config centralizzata:** osservabilità governata da `SERTOR_OBSERVABILITY` (invariato). **PASS.**
- [x] **IX — Osservabilità:** è il cuore — rende il cablaggio uniforme su ogni percorso. **PASS.**
- [x] **X — Host-agnostico:** invariato. **PASS.**
- [x] **XI — Consumo via vehicles:** lo **realizza per costruzione** (rende sicuro anche il percorso
  libreria). **PASS.**

**Esito:** PASS 11/11, nessuna deroga. Complexity Tracking vuoto.

## Project Structure

```text
specs/041-consumo-sicuro-vehicles/
├── plan.md · research.md · spec.md · checklists/requirements.md · tasks.md

src/sertor_core/
└── composition.py        # NUOVO _wire_runtime(settings) + chiamata nelle 5 factory consumer-entry
tests/unit/
└── test_composition.py   # + test gap-closure (build_indexer().index() con osservabilità → evento)
```

**Structure Decision**: nessun nuovo modulo/entità; modifica chirurgica a `composition.py` + test.
Nessun data-model/contract nuovo (il "contratto" è il comportamento delle factory; descritto qui).

## Complexity Tracking

> Nessuna violazione. Tabella vuota.
