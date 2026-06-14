# Tasks — Pannello TUI report sfogliabili (feature 023)

**Branch**: `023-osservabilita-tui-report` | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Per dipendenze, per user story. MVP = US1. Test offline; smoke Textual via Pilot. Estende F3.

## Phase 1 — Setup
- **T001** — Baseline verde: `uv run pytest -m "not cloud"` + `uv run ruff check src/ tests/`.

## Phase 2 — Foundational (funzioni pure)
- **T002** — `observability/live.py`: `time_window(preset, now) -> (since, until)` (all/7d/24h) +
  `next_window(preset)` (ciclo all→7d→24h→all). [research D3, data-model §2]
- **T003** — `observability/live.py`: `render_cache_report(CacheReport)`,
  `render_cost_report(CostReport)`, `render_corpus_report(HealthReport, now)` — funzioni di resa PURE,
  con stato vuoto onesto e freschezza `now-last_index_ts`. [research D2/D4, FR-001/006/007/011]

## Phase 3 — US1: Report sfogliabili (Priority P1, MVP)
- **T004** — `observability/tui.py`: `ObservabilityApp` a **schede** (`TabbedContent`:
  Live/Cache/Cost/Corpus, ogni scheda un `Static`); `_update` ricalcola le 4 viste sulla finestra
  corrente; `self._window` default `all`; sub-title = preset. Sola lettura. [FR-001/002/005/008/010]
- **T005** — `tests/unit/test_observability_live.py` (estendi): test PURI di `render_cache_report`/
  `render_cost_report`/`render_corpus_report` (contenuto coerente con eventi; stato vuoto; freschezza con
  `now` noto). [SC-001/004/006]

## Phase 4 — US2: Intervallo selezionabile (Priority P2)
- **T006** — `observability/tui.py`: binding `t` → `action_cycle_window` (`next_window` + `_update`);
  sub-title aggiornato. [FR-003/004]
- **T007** — `tests/unit/test_observability_live.py` (estendi): `time_window` (finestre corrette per
  preset, con `now` noto) + `next_window` (ciclo). + test che i report su una finestra includono solo
  gli eventi della finestra (via `ObservabilityReports` + store in memoria). [SC-002]

## Phase 5 — US3: Degradazione & coerenza
- **T008** — `tests/unit/test_observability_tui.py` (estendi): smoke a SCHEDE via Pilot (skip se extra
  assente): le 4 schede esistono; la scheda Cache mostra il contenuto atteso; con store vuoto le viste
  mostrano lo stato vuoto onesto; ciclo intervallo aggiorna il sub-title. [SC-003/004]

## Phase 6 — Polish
- **T009** — `docs/install.md`: aggiorna la sezione pannello (schede report + tasto `t` per l'intervallo).
- **T010** — Suite completa verde + ruff: `uv run pytest -m "not cloud"` (root + packages) e
  `uv run ruff check src/ tests/ packages/`. Nessuna regressione (F3 live invariata).
- **T011** — *(post-merge)*: chiude l'MVP osservabilità (F1→F4); roadmap a DONE; re-index.

## Coverage FR → task
| FR | Task | | FR | Task |
|---|---|---|---|---|
| FR-001 | T003,T004,T005 | | FR-007 | T003 (ripiego token) |
| FR-002 | T004 (schede) | | FR-008 | T004 (stessa app) |
| FR-003 | T002,T006,T007 | | FR-009 | T003,T005 (resa senza TTY) |
| FR-004 | T006 (sub-title) | | FR-010 | T004 (sola lettura) |
| FR-005 | T003,T004 (rende F2) | | FR-011 | T003 |
| FR-006 | T003,T005,T008 | | | |

## Percorso critico
Setup → Foundational puri (T002/T003) → US1 T004/T005 (MVP) → US2 (T006/T007) → smoke (T008) → polish.
