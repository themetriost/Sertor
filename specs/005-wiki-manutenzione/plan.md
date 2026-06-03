# Implementation Plan: Skill — manutenzione del wiki (lint / indice / documentazione)

**Branch**: `spec/005-wiki-manutenzione` | **Date**: 2026-06-03 | **Spec**: [spec.md](spec.md)

**Input**: `specs/005-wiki-manutenzione/spec.md` (deriva da FEAT-007). Dipende da FEAT-003
(convenzioni/struttura wiki) e dalla porta `LLMProvider` — entrambi in `master`.

## Summary

FEAT-007 mantiene il wiki **vivo, coerente e completo** e ne afferma il ruolo di **documentazione
ufficiale**. È un'estensione del sottopacchetto `sertor_core/wiki/`: un modulo **`maintenance.py`**
(LLM-free) per il **lint** (link rotti, orfani, indice disallineato, coperture mancanti, contraddizioni
marcate) con **report pass/fail** consumabile come **gate ricorrente**, e per la **rigenerazione
idempotente dell'indice** (blocco tra marcatori). Aggiunge alla `distill.py` la **distillazione
documentale** assistita/non distruttiva da artifact (con backlink, richiede LLM). Riusa le convenzioni
di FEAT-003 (DRY). Cardine: **idempotenza e non-distruttività** (il lint segnala, `--fix` opt-in applica
solo fix sicuri).

## Technical Context

**Language/Version**: Python ≥ 3.11.

**Primary Dependencies**: solo `sertor_core` (wiki/conventions, structure, distill; porta `LLMProvider`)
e stdlib (`re`, `pathlib`, `dataclasses`). Nessuna nuova dipendenza.

**Storage**: file system del wiki (lettura per lint; scrittura solo per index-rebuild/`--fix` e
distillazione).

**Testing**: `pytest` su **wiki sandbox** in temp (mai produzione); lint deterministico; distillazione
con `FakeLLM`. Test di idempotenza (re-run → identico).

**Target Platform**: Linux + Windows.

**Project Type**: estensione della libreria `sertor_core` (sottopacchetto `wiki/`). Nessuna CLI in
questa feature (DA-6).

**Performance Goals**: lint deterministico in pochi secondi su wiki tipico (NFR-07) → adatto al gate
a fine feature.

**Constraints**: idempotenza/non-distruttività (cardine); lint sola lettura di default; index-rebuild
solo sul blocco tra marcatori; distillazione non sovrascrive il curato; LLM solo per distillazione.

**Scale/Scope**: ≥2 wiki; scope implementativo **Must + Should** (lint+report+gate, indice+`--fix`,
documentazione distillata, contraddizioni marcate). Contraddizioni **semantiche** (Could) fuori.

## Constitution Check

*GATE: prima della Phase 0, ri-verifica dopo Phase 1.*

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** `wiki/maintenance.py` usa convenzioni/porte
  del core; LLM dietro porta; nessun SDK/CLI. Esercitabile con `FakeLLM`. → **PASS.**
- [x] **II — Boundary & local-first:** lint LLM-free; distillazione dietro `LLMProvider`. → **PASS.**
- [x] **III — YAGNI & unità piccole:** riusa `conventions.py`/`structure.py`/`distill.py` (DRY);
  niente registry/CLI ora. → **PASS.**
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** lint **sola lettura**; `--fix` solo fix sicuri;
  distillazione senza LLM → errore esplicito; report pass/fail, niente vuoto silenzioso. → **PASS.**
- [x] **V — Testabilità & misure:** sandbox wiki; lint deterministico; `FakeLLM`. → **PASS.**
- [x] **VI — Idempotenza & non-distruttività (cardine):** index-rebuild idempotente sul blocco gestito;
  lint read-only; distillazione non sovrascrive il curato. → **PASS.**
- [x] **VII — Leggibilità:** `lint`/`regenerate_index`/`distill_artifact`/`LintReport`. → **PASS.**
- [x] **VIII — Config centralizzata:** path wiki + set di copertura atteso + LLM da config/parametri. → **PASS.**
- [x] **IX — Osservabilità:** ogni operazione emette log strutturati. → **PASS.**

**Esito (pre-Phase 0):** ✅ PASS 9/9. Estensioni additive a FEAT-003 (marcatori catalogo in
`conventions.py`; nuova `maintenance.py`; `distill_artifact` in `distill.py`). Complexity Tracking vuoto.

## Project Structure

```text
specs/005-wiki-manutenzione/
├── plan.md · research.md · data-model.md · quickstart.md
├── contracts/wiki-maintenance.md
├── checklists/requirements.md
└── tasks.md

src/sertor_core/wiki/
├── maintenance.py     # NUOVO — lint(), regenerate_index(), LintReport/Issue, coperture (LLM-free)
├── conventions.py     # + marcatori catalogo (CATALOG_BEGIN/END) + helper blocco gestito
├── distill.py         # + distill_artifact(): doc distillation assistita/non distruttiva, backlink
└── (structure.py, operations.py, indexing.py — invariati)

tests/
├── unit/
│   ├── test_wiki_maintenance.py     # lint (link/orfani/indice/coperture/contraddizioni) + report + gate (US1/US2/US5)
│   ├── test_wiki_index_rebuild.py   # rigenerazione idempotente + --fix (US3)
│   └── test_wiki_distill_doc.py     # distillazione documentale assistita (US4, FakeLLM)
└── integration/
    └── test_wiki_maintenance_idempotence.py  # re-run identico (idempotenza)
```

**Structure Decision**: estendere `sertor_core/wiki/` (non un nuovo pacchetto): la manutenzione è la
controparte della creazione (FEAT-003) e ne condivide convenzioni/struttura. `maintenance.py` è
LLM-free; la distillazione documentale vive in `distill.py` accanto a `distill()` esistente.

## Complexity Tracking

> Nessuna violazione.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
