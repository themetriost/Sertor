# Tasks — Servizio di aggregazione/report dell'osservabilità (feature 021)

**Branch**: `021-osservabilita-report` | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Task per dipendenze, per user story. Tutti i test **offline** (Principio V). MVP = US1 (report cache).

## Phase 1 — Setup
- **T001** — Baseline verde: `uv run pytest -m "not cloud"` + `uv run ruff check src/ tests/`.

## Phase 2 — Foundational
- **T002** — `config/settings.py`: `observability_bucket: str = "day"` + load (`SERTOR_OBSERVABILITY_BUCKET`).
- **T003** — `services/observability_report.py` (NUOVO): definisci i **report dataclass** (frozen) e i
  `SeriesPoint` (CacheReport/CacheBucket, CostReport/CostBucket, HealthReport/HealthBucket,
  LatencyReport/LatencyStat, ReliabilityReport) + le **funzioni pure** interne `bucket_key(ts, gran)`
  (UTC, default giorno) e `percentiles(values, ps)` (nearest-rank). [data-model §1/§3, research D3/D4]
- **T004** — Fake store per i test: usa un'implementazione in-memory della porta `ObservabilityStore`
  (in `tests/fixtures/mocks.py`) che restituisce eventi simulati filtrati per operation/intervallo.

## Phase 3 — US1: Report cache (Priority P1, MVP)
- **T005** — `ObservabilityReports.cache_report(since, until, bucket)`: aggrega gli eventi
  `embeddings_cache` → total_hits/misses + serie per bucket; `estimated_tokens_saved` = hit ×
  (token/elemento dagli eventi `embeddings`), **dichiarato stima**. [FR-001/002, SC-001]
- **T006** — `tests/unit/test_observability_report.py` (NUOVO): cache_report su eventi simulati →
  hit/miss totali e per bucket corretti; risparmio stimato coerente; **intervallo vuoto → report a
  zeri** (FR-010/SC-004). [SC-001/004]

## Phase 4 — US2: Report costo (Priority P2)
- **T007** — `cost_report`: aggrega `embeddings` → token per provider e per bucket; eventi senza
  `tokens` esclusi dal totale (non zero). [FR-003/004, SC-002]
- **T008** — test: cost_report (token per provider/bucket; evento senza token escluso). [SC-002]

## Phase 5 — US3: Salute, latenze, affidabilità (Priority P3)
- **T009** — `health_report` (ultimo `index`: documents/chunks/embedding_dim + last_index_ts + serie),
  `latency_report` (p50/p95 per operation da `elapsed_ms` di `index`/`retrieve`), `reliability_report`
  (conteggi `embeddings_error`/`embeddings_retry`/`low_confidence`/`retrieve` + abstention_rate).
  [FR-005/006/007, SC-003]
- **T010** — test: health (ultimo index + serie), latency (p50/p95 su valori noti), reliability
  (conteggi + abstention_rate); determinismo (stesso input → stesso report, SC-005). [SC-003/005]

## Phase 6 — Wiring & Polish
- **T011** — `composition.py`: `build_observability_reports(settings)` (riusa `build_observability_store`);
  export da `__init__.py` (+ i report dataclass principali). Test di wiring (build su store con eventi
  → report popolato). [FR-011]
- **T012** — Suite completa verde + ruff: `uv run pytest -m "not cloud"` (root + packages) e
  `uv run ruff check src/ tests/ packages/`. Nessuna regressione.
- **T013** — *(post-merge)*: opzionale abilitare `SERTOR_OBSERVABILITY=true` sul dogfood per dati reali;
  re-index del corpus.

## Coverage FR → task
| FR | Task | | FR | Task |
|---|---|---|---|---|
| FR-001 | T005,T006 | | FR-007 | T009,T010 |
| FR-002 | T005 | | FR-008 | T005/T007/T009 (since/until/bucket) |
| FR-003 | T007,T008 | | FR-009 | T010 (determinismo) |
| FR-004 | T007,T008 | | FR-010 | T006 (vuoto esplicito) |
| FR-005 | T009,T010 | | FR-011 | T003/T005 (solo via porta), T011 |
| FR-006 | T009,T010 | | FR-012 | T003 (solo metriche conservate) |

## Percorso critico
Setup → Foundational (T002/T003/T004) → US1 (T005/T006, MVP) → US2/US3 (parallelizzabili, stesso file
servizio → in serie) → wiring/polish.
