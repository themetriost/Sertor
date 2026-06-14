# Implementation Plan: Pannello TUI — vista live dell'osservabilità

**Branch**: `022-osservabilita-tui-live` | **Date**: 2026-06-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/022-osservabilita-tui-live/spec.md` (F3 epica osservabilità)

## Summary

La prima superficie **visibile**: un pannello da terminale (Textual, extra `[tui]` isolato) che mostra
lo stato corrente di Sertor e si aggiorna dal vivo. Architettura a due strati per la testabilità
(Principio V) e la sottilezza (Principio I):

1. **Modello di stato (puro, testabile senza terminale):** `LiveSnapshot` + `live_snapshot(reports)`
   che compone una fotografia (ultimo index, cache hit/miss + risparmio, consumo token, ultimi eventi,
   affidabilità) **leggendo i report di F2** (`ObservabilityReports`, già su master). Nessuna logica di
   aggregazione qui (la fa F2): è pura composizione.
2. **Rendering Textual (guscio sottile):** un'app Textual che disegna lo snapshot e lo **rinfresca su
   timer** rileggendo i report (DA-O-c = rilettura periodica, *pull*). Dietro l'extra `[tui]`; se manca
   → errore azionabile (come gli extra `rerank`/`graph`). Avviata da `sertor-rag observe`.

## Technical Context

**Language/Version**: Python ≥ 3.11

**Primary Dependencies**: **Textual** come **extra opzionale `[tui]`** (import lazy; aggiunto anche al
`dev` per i test). Il core resta senza nuove dipendenze **obbligatorie** (Principio III). Il modello di
stato usa solo stdlib + F2.

**Storage**: nessuno proprio — legge i report di F2 (che leggono lo store di F1). Sola lettura.

**Testing**: pytest, offline. (a) Modello di stato: test puri con uno store in memoria + F2 (senza
Textual). (b) App Textual: smoke test via il test-harness di Textual (`run_test`/Pilot) quando l'extra è
installato. (c) Extra mancante → errore azionabile (simulando ImportError).

**Target Platform**: terminale (qualunque OS). Consumatore sottile del core.

**Project Type**: libreria + superficie TUI (guscio).

**Performance Goals**: refresh ogni ~2s (configurabile); rendering di poche metriche → trascurabile.

**Constraints**: sola lettura (non scrive nulla); thin consumer; host-agnostico; il modello di stato
testabile senza TTY; extra isolato; degradazione onesta (persistenza spenta → stato vuoto onesto; extra
assente → errore azionabile).

**Scale/Scope**: una manciata di metriche + ultimi N eventi; nessun limite di scala.

## Constitution Check

*GATE: PASS prima della Phase 0 e dopo la Phase 1.* — Costituzione v1.1.0.

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** il pannello è un **thin consumer**: il
  modello di stato legge `ObservabilityReports` (F2); la logica di aggregazione **non** è qui. Textual
  vive solo nel guscio di rendering. **PASS**
- [x] **II — Boundary & local-first:** nessun servizio esterno; tutto locale; Textual è un dettaglio di
  interfaccia dietro l'extra. **PASS**
- [x] **III — YAGNI & unità piccole:** Textual è un **extra opzionale** `[tui]` (import lazy); il core
  resta senza dipendenze obbligatorie nuove (come `rerank`/`graph`). Modello di stato piccolo e puro. **PASS**
- [x] **IV — Errori espliciti:** persistenza spenta → **stato vuoto onesto** (non crash); extra assente
  → **errore azionabile** con istruzione d'installazione (come gli altri extra). Niente null silenzioso. **PASS**
- [x] **V — Testabilità & misure:** il **modello di stato** è testabile **senza terminale**
  (FR-010/SC-005); l'app Textual ha uno smoke test via Pilot. **PASS**
- [x] **VI — Idempotenza & non-distruttività:** il pannello è **sola lettura** (FR-004/SC-007): non
  scrive store/indici/file; aprirlo/aggiornarlo non ha effetti collaterali. **PASS**
- [x] **VII — Leggibilità:** naming di dominio (`LiveSnapshot`, `live_snapshot`, `ObservabilityApp`,
  `run_live_panel`). **PASS**
- [x] **VIII — Configurabilità centralizzata:** la frequenza di refresh sta in `Settings`
  (`observability_refresh_s`, default 2.0). **PASS**
- [x] **IX — Osservabilità:** è la superficie dell'osservabilità; mostra solo metriche (privacy). **PASS**
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** gira su qualunque progetto ospite senza modifiche al
  corpo (FR-008/SC-006). **PASS**

**Esito: PASS 10/10 senza deroghe.**

## Project Structure

```text
src/sertor_core/
├── observability/
│   ├── live.py                 # NUOVO: LiveSnapshot (dataclass) + live_snapshot(reports, limit) [PURO, testabile]
│   └── tui.py                  # NUOVO: ObservabilityApp (Textual) + run_live_panel(settings) [guscio, lazy textual]
├── services/observability_report.py  # MODIF: + recent_events(limit, since, until) (additivo, per gli ultimi eventi)
├── config/settings.py          # MODIF: + observability_refresh_s (SERTOR_OBSERVABILITY_REFRESH, default 2.0)
├── cli/__main__.py             # MODIF: + sottocomando `observe` → run_live_panel (errore azionabile se manca [tui])
└── composition.py              # (riusa build_observability_reports)

pyproject.toml                  # MODIF: optional-dependencies [tui] = textual; + textual nel dev

tests/unit/
├── test_observability_live.py  # NUOVO: live_snapshot (stato corrente, vuoto onesto, recent_events); senza textual
└── test_observability_tui.py   # NUOVO: smoke Textual via Pilot (skip se extra assente) + errore azionabile
```

**Structure Decision**: la novità vive in `observability/` (modello di stato puro + guscio Textual) + un
sottocomando CLI + una manopola. La logica resta nel core (F2); Textual è confinato in `tui.py` dietro
l'extra. Coerente con il pattern degli extra esistenti (`rerank`/`graph`).

## Complexity Tracking

Nessuna violazione: tabella non compilata.
