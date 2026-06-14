# Data Model — feature 021

Nessuna entità di dominio del retrieval cambia. Le entità qui sono i **report** (output del servizio) e
le manopole. Vivono in `services/observability_report.py` (auto-contenuti per F2, come `EvalReport`).

## 1. Report dataclasses (immutabili, frozen)

| Report | Campi principali |
|---|---|
| `CacheReport` | `total_hits: int`, `total_misses: int`, `series: list[CacheBucket]`, `estimated_tokens_saved: int` |
| `CostReport` | `total_tokens: int`, `by_provider: dict[str, int]`, `series: list[CostBucket]` |
| `HealthReport` | `documents: int`, `chunks: int`, `embedding_dim: int \| None`, `last_index_ts: float \| None`, `series: list[HealthBucket]` |
| `LatencyReport` | `by_operation: dict[str, LatencyStat]` (LatencyStat = `p50_ms`, `p95_ms`, `count`) |
| `ReliabilityReport` | `errors: int`, `retries: int`, `low_confidence: int`, `retrieves: int`, `abstention_rate: float` |

Punti di serie (uno per bucket temporale, ordinati per `bucket`):
- `CacheBucket(bucket: str, hits: int, misses: int)`
- `CostBucket(bucket: str, tokens: int)`
- `HealthBucket(bucket: str, documents: int, chunks: int)` — fotografia dell'ultimo index nel bucket.

Tutti i report **a zeri** quando non ci sono eventi rilevanti (FR-010): liste vuote, totali 0,
`embedding_dim`/`last_index_ts` `None`, `abstention_rate` 0.0.

## 2. Servizio `ObservabilityReports`

```
ObservabilityReports(store: ObservabilityStore)
  cache_report(since=None, until=None, bucket="day") -> CacheReport
  cost_report(since=None, until=None, bucket="day") -> CostReport
  health_report(since=None, until=None, bucket="day") -> HealthReport
  latency_report(since=None, until=None) -> LatencyReport
  reliability_report(since=None, until=None) -> ReliabilityReport
```

Ogni metodo: `store.query_events(<operation rilevante>, since, until)` → aggregazione pura → report.
Mappa eventi → report:
- cache: eventi `embeddings_cache` (`hits`/`misses`/`total`); risparmio stimato dal rapporto
  token/elemento degli eventi `embeddings`.
- cost: eventi `embeddings` (`provider`/`tokens`).
- health: eventi `index` (`documents`/`chunks`/`embedding_dim`); `last_index_ts` = `ts` dell'ultimo.
- latency: eventi `index` e `retrieve` (`elapsed_ms`) → p50/p95 per operation.
- reliability: eventi `embeddings_error`, `embeddings_retry`, `low_confidence`, `retrieve` → conteggi +
  `abstention_rate` = low_confidence / retrieves (0.0 se nessun retrieve).

## 3. Funzioni pure (interne)

- `bucket_key(ts: float, granularity: str) -> str` — epoch → chiave di bucket UTC (default giorno).
- `percentiles(values: list[float], ps: tuple[int,...]) -> dict[int,float]` — nearest-rank.
- aggregatori per famiglia (deterministici).

## 4. Manopola (`Settings`)

| Campo | Env | Default | Significato |
|---|---|---|---|
| `observability_bucket` | `SERTOR_OBSERVABILITY_BUCKET` | `"day"` | Granularità di default dei bucket temporali dei report. |

## 5. Relazioni

```
build_observability_reports(settings)            [composition.py]
  └─ ObservabilityReports(build_observability_store(settings))   # riusa lo store di F1 (porta)
       └─ store.query_events(operation, since, until)  → aggregazione pura → *Report

FEAT-003/004 (pannello TUI) e CLI → ObservabilityReports.*_report(...) → rendering
```
