# Implementation Plan: Pannello TUI — report sfogliabili

**Branch**: `023-osservabilita-tui-report` | **Date**: 2026-06-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/023-osservabilita-tui-report/spec.md` (F4 epica osservabilità)

## Summary

L'ultimo Must dell'osservabilità: dentro il **medesimo pannello** di F3 (`sertor-rag observe`), viste di
report **sfogliabili** a schede — cache (hit/miss nel tempo), costo (token per provider/giorno), salute
del corpus + **freschezza** (da quanto non si re-indicizza) — con **intervallo selezionabile** (tutto /
7g / 24h). Stessa architettura a due strati di F3: **funzioni di resa pure** (testabili senza terminale)
+ **schede Textual** (guscio). Rende i report di F2; nessuna aggregazione nel pannello.

## Technical Context

**Language/Version**: Python ≥ 3.11. **Dependencies**: Textual (extra `[tui]`, già introdotto in F3);
stdlib (`time`) per la finestra temporale. Nessuna nuova dipendenza.

**Storage**: nessuno proprio — rende i report di F2 (sola lettura).

**Testing**: pytest offline. (a) funzioni di resa + finestra temporale: test puri (senza Textual);
(b) app a schede: smoke via Textual `run_test`/Pilot (skip se l'extra assente).

**Project Type**: superficie TUI (guscio) sopra il core.

**Constraints**: sola lettura; thin consumer; host-agnostico; resa testabile senza TTY; degradazione
onesta (store vuoto → stato vuoto; € assente → ripiego token); stessa app di F3 (un'unica superficie).

## Constitution Check

*GATE: PASS prima della Phase 0 e dopo la Phase 1.* — Costituzione v1.1.0.

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** thin consumer; le viste rendono i report di
  F2; nessuna aggregazione nel pannello. **PASS**
- [x] **II — Boundary & local-first:** tutto locale; Textual dietro l'extra. **PASS**
- [x] **III — YAGNI & unità piccole:** riusa l'extra `[tui]` di F3 e i report di F2; aggiunge funzioni di
  resa + schede. Nessuna dipendenza nuova. **PASS**
- [x] **IV — Errori espliciti:** store vuoto → stato vuoto onesto; € assente → ripiego token; mai crash. **PASS**
- [x] **V — Testabilità & misure:** funzioni di resa + finestra temporale **pure**, testabili senza TTY;
  smoke Textual via Pilot. **PASS**
- [x] **VI — Idempotenza & non-distruttività:** sola lettura (non scrive nulla). **PASS**
- [x] **VII — Leggibilità:** naming di dominio (`render_cache_report`, `time_window`, `next_window`). **PASS**
- [x] **VIII — Configurabilità centralizzata:** riusa le manopole esistenti (refresh, bucket); i preset
  di intervallo sono nel pannello (UX), non config di prodotto. **PASS**
- [x] **IX — Osservabilità:** è la superficie dell'osservabilità; solo metriche. **PASS**
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** gira su qualunque ospite senza modifiche al corpo. **PASS**

**Esito: PASS 10/10 senza deroghe.**

## Project Structure

```text
src/sertor_core/
├── observability/
│   ├── live.py   # MODIF: + render_cache_report/render_cost_report/render_corpus_report (PURI)
│   │             #        + time_window(preset, now) + next_window(preset) [PURI]
│   └── tui.py    # MODIF: ObservabilityApp a SCHEDE (TabbedContent: Live/Cache/Cost/Corpus),
│                 #        binding per ciclare l'intervallo; usa le funzioni di resa pure
└── (composition/cli/settings invariati: stessa app, stesso `sertor-rag observe`)

tests/unit/
├── test_observability_live.py    # MODIF/estendi: render_* report + time_window/next_window (puri)
└── test_observability_tui.py     # MODIF/estendi: smoke a schede (Pilot) — le 4 schede presenti, contenuto
```

**Structure Decision**: F4 **estende** F3 — stessa app, stessi moduli. Le funzioni di resa pure vanno in
`live.py` (testabili); le schede in `tui.py`. Nessun nuovo entry point: `sertor-rag observe` apre il
pannello completo (live + report).

## Complexity Tracking

Nessuna violazione.
