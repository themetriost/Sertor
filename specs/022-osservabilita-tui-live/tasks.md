# Tasks — Pannello TUI vista live dell'osservabilità (feature 022)

**Branch**: `022-osservabilita-tui-live` | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Per dipendenze, per user story. MVP = US1. Test offline (Principio V); lo smoke Textual via Pilot.

## Phase 1 — Setup
- **T001** — Baseline verde: `uv run pytest -m "not cloud"` + `uv run ruff check src/ tests/`.
- **T002** — `pyproject.toml`: `optional-dependencies.tui = ["textual>=8,<9"]` + `textual` nel gruppo
  `dev`; `uv sync --extra dev --extra tui` (aggiorna `uv.lock`).

## Phase 2 — Foundational
- **T003** — `config/settings.py`: `observability_refresh_s: float = 2.0` + load (`SERTOR_OBSERVABILITY_REFRESH`).
- **T004** — `services/observability_report.py`: `recent_events(limit=20, since=None, until=None)`
  (additivo: ultimi `limit` eventi via `query_events`, coda). [data-model §2, research D4]

## Phase 3 — US1: Cruscotto dal vivo (Priority P1, MVP)
- **T005** — `observability/live.py` (NUOVO): `LiveSnapshot` (frozen dataclass) + `live_snapshot(reports,
  recent_limit=20, since=None, until=None)` — funzione PURA che compone cache/cost/health/reliability +
  recent_events; `has_data` da presenza eventi; cache_hit_rate calcolato. Nessun Textual. [FR-001/003/011,
  data-model §1]
- **T006** — `observability/tui.py` (NUOVO): `ObservabilityApp(reports, refresh_s)` (Textual `App`,
  import textual al top del modulo) che disegna lo snapshot e lo aggiorna su `set_interval`; sola
  lettura. + `run_live_panel(settings)`: `build_observability_reports` + lancio app; import lazy del
  modulo `tui`; `ImportError` → `ConfigError` con istruzione `[tui]`. [FR-002/004/006/009, research D5]
- **T007** — `cli/__main__.py`: sottocomando `observe` → `run_live_panel(Settings.load())`. [FR-008]
- **T008** — `tests/unit/test_observability_live.py` (NUOVO): `live_snapshot` su eventi simulati (via
  `InMemoryObservabilityStore` + `ObservabilityReports`): stato corrente coerente (SC-001);
  `has_data=False` + zeri su store vuoto (FR-005/SC-003); `recent_events` coda corretta; determinismo
  (SC-005); **nessun import di textual** in questo test. [SC-001/003/005]

## Phase 4 — US2: Degradazione onesta (Priority P2)
- **T009** — `tests/unit/test_observability_tui.py` (NUOVO):
  - **extra mancante** → `run_live_panel` solleva `ConfigError` con l'istruzione (simula ImportError del
    modulo `tui`, es. monkeypatch). [FR-006/SC-004]
  - **smoke Textual** (skip se `textual` non installato): `async with ObservabilityApp(...).run_test()
    as pilot:` → l'app monta e mostra dati (un widget contiene es. il numero di chunk). [FR-001/002]
  - **stato vuoto onesto**: snapshot a store vuoto → l'app mostra il messaggio «nessun dato/abilita». [FR-005]

## Phase 5 — Polish
- **T010** — `pyproject.toml`/docs: documenta l'extra `[tui]` e `sertor-rag observe` in `docs/install.md`
  + nota `SERTOR_OBSERVABILITY_REFRESH` nei template `.env`. Verifica guardia lingua asset (inglese).
- **T011** — Suite completa verde + ruff: `uv run pytest -m "not cloud"` (root + packages) e
  `uv run ruff check src/ tests/ packages/`. Nessuna regressione; default-off invariato.
- **T012** — *(post-merge)*: abilitabile `SERTOR_OBSERVABILITY=true` sul dogfood + `sertor-rag observe`
  per un riscontro reale; re-index.

## Coverage FR → task
| FR | Task | | FR | Task |
|---|---|---|---|---|
| FR-001 | T005,T008,T009 | | FR-007 | T003 |
| FR-002 | T006,T009 | | FR-008 | T007 |
| FR-003 | T005 (solo via F2) | | FR-009 | T006 |
| FR-004 | T005/T006 (read-only) | | FR-010 | T005,T008 (stato senza TTY) |
| FR-005 | T005,T009 | | FR-011 | T005 |
| FR-006 | T006,T009 | | | |

## Percorso critico
Setup (T001/T002) → Foundational (T003/T004) → **US1** T005 (modello) → T006/T007 (guscio+CLI) → T008
(test modello, MVP). US2 (T009) dopo il guscio. Polish (T010/T011).
