"""Observability reports (feature 021): turn the persisted events into readable answers.

Reads the events kept by the persistence layer (feature 020) THROUGH the `ObservabilityStore` port
and aggregates them with PURE, deterministic functions into five report families: cache (hit/miss +
estimated savings), cost (tokens per provider/bucket), corpus health, latency (p50/p95),
reliability.

A service of the core (Principio I): no UI (the TUI of F3/F4 will render these), no persistence (F1
owns it), no currency conversion (FEAT-007 builds on `CostReport`). Stdlib only. Missing data → an
explicit EMPTY report (zeros), never an exception (Principio IV / FR-010).
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

from sertor_core.domain.ports import ObservabilityStore

# --- report dataclasses (immutable values) -----------------------------------------------------


@dataclass(frozen=True)
class CacheBucket:
    bucket: str
    hits: int
    misses: int


@dataclass(frozen=True)
class CacheReport:
    total_hits: int = 0
    total_misses: int = 0
    series: list[CacheBucket] = field(default_factory=list)
    estimated_tokens_saved: int = 0  # estimate (in-call dedup of feat. 019 → not exact)


@dataclass(frozen=True)
class CostBucket:
    bucket: str
    tokens: int


@dataclass(frozen=True)
class CostReport:
    total_tokens: int = 0
    by_provider: dict[str, int] = field(default_factory=dict)
    series: list[CostBucket] = field(default_factory=list)


@dataclass(frozen=True)
class HealthBucket:
    bucket: str
    documents: int
    chunks: int


@dataclass(frozen=True)
class HealthReport:
    documents: int = 0
    chunks: int = 0
    embedding_dim: int | None = None
    last_index_ts: float | None = None
    series: list[HealthBucket] = field(default_factory=list)


@dataclass(frozen=True)
class LatencyStat:
    p50_ms: float
    p95_ms: float
    count: int


@dataclass(frozen=True)
class LatencyReport:
    by_operation: dict[str, LatencyStat] = field(default_factory=dict)


@dataclass(frozen=True)
class ReliabilityReport:
    errors: int = 0
    retries: int = 0
    low_confidence: int = 0
    retrieves: int = 0
    abstention_rate: float = 0.0


# --- pure helpers ------------------------------------------------------------------------------


def bucket_key(ts: float, granularity: str) -> str:
    """Map an epoch instant to a UTC time-bucket key (deterministic). Default granularity: day."""
    t = time.gmtime(ts)
    if granularity == "hour":
        return time.strftime("%Y-%m-%dT%H", t)
    return time.strftime("%Y-%m-%d", t)


def percentiles(values: list[float], ps: tuple[int, ...]) -> dict[int, float]:
    """Nearest-rank percentiles on a copy-sorted list (deterministic, no interpolation)."""
    ordered = sorted(values)
    n = len(ordered)
    out: dict[int, float] = {}
    for p in ps:
        if n == 0:
            out[p] = 0.0
            continue
        idx = min(max(math.ceil(p / 100 * n) - 1, 0), n - 1)
        out[p] = float(ordered[idx])
    return out


# --- the service -------------------------------------------------------------------------------


class ObservabilityReports:
    """Aggregates the persisted events (via `ObservabilityStore`) into report values."""

    def __init__(self, store: ObservabilityStore, default_bucket: str = "day"):
        self._store = store
        self._default_bucket = default_bucket

    def cache_report(
        self, since: float | None = None, until: float | None = None, bucket: str | None = None
    ) -> CacheReport:
        bucket = bucket or self._default_bucket
        events = self._store.query_events("embeddings_cache", since, until)
        total_hits = sum(e.fields.get("hits", 0) for e in events)
        total_misses = sum(e.fields.get("misses", 0) for e in events)
        per: dict[str, list[int]] = {}
        for e in events:
            slot = per.setdefault(bucket_key(e.ts, bucket), [0, 0])
            slot[0] += e.fields.get("hits", 0)
            slot[1] += e.fields.get("misses", 0)
        series = [CacheBucket(k, h, m) for k, (h, m) in sorted(per.items())]
        # Estimated savings: hits × (tokens-per-element observed on embeddings events). It is an
        # ESTIMATE: the in-call dedup of feat. 019 means tokens/elements is not exact.
        emb = self._store.query_events("embeddings", since, until)
        total_tokens = sum(e.fields["tokens"] for e in emb if e.fields.get("tokens") is not None)
        total_texts = sum(e.fields.get("texts", 0) for e in emb)
        per_elem = (total_tokens / total_texts) if total_texts else 0.0
        return CacheReport(total_hits, total_misses, series, int(round(total_hits * per_elem)))

    def cost_report(
        self, since: float | None = None, until: float | None = None, bucket: str | None = None
    ) -> CostReport:
        bucket = bucket or self._default_bucket
        events = self._store.query_events("embeddings", since, until)
        by_provider: dict[str, int] = {}
        per_bucket: dict[str, int] = {}
        total = 0
        for e in events:
            tok = e.fields.get("tokens")
            if tok is None:  # provider did not report tokens → not counted as zero (FR-004)
                continue
            provider = e.fields.get("provider", "unknown")
            by_provider[provider] = by_provider.get(provider, 0) + tok
            key = bucket_key(e.ts, bucket)
            per_bucket[key] = per_bucket.get(key, 0) + tok
            total += tok
        series = [CostBucket(k, t) for k, t in sorted(per_bucket.items())]
        return CostReport(total, by_provider, series)

    def health_report(
        self, since: float | None = None, until: float | None = None, bucket: str | None = None
    ) -> HealthReport:
        bucket = bucket or self._default_bucket
        events = self._store.query_events("index", since, until)  # ordered by ts
        if not events:
            return HealthReport()
        last = events[-1]
        per_bucket: dict[str, object] = {}
        for e in events:
            per_bucket[bucket_key(e.ts, bucket)] = e  # later events overwrite → last in bucket
        series = [
            HealthBucket(k, e.fields.get("documents", 0), e.fields.get("chunks", 0))  # type: ignore[union-attr]
            for k, e in sorted(per_bucket.items())
        ]
        return HealthReport(
            documents=last.fields.get("documents", 0),
            chunks=last.fields.get("chunks", 0),
            embedding_dim=last.fields.get("embedding_dim"),
            last_index_ts=last.ts,
            series=series,
        )

    def latency_report(
        self, since: float | None = None, until: float | None = None
    ) -> LatencyReport:
        by_op: dict[str, LatencyStat] = {}
        for op in ("index", "retrieve"):
            values = [
                e.fields["elapsed_ms"]
                for e in self._store.query_events(op, since, until)
                if e.fields.get("elapsed_ms") is not None
            ]
            if not values:
                continue
            pct = percentiles(values, (50, 95))
            by_op[op] = LatencyStat(p50_ms=pct[50], p95_ms=pct[95], count=len(values))
        return LatencyReport(by_op)

    def recent_events(
        self, limit: int = 20, since: float | None = None, until: float | None = None
    ) -> list:
        """The last `limit` events of any kind, ordered by ts (tail). For the live panel (022)."""
        events = self._store.query_events(None, since, until)
        return events[-limit:] if limit > 0 else []

    def reliability_report(
        self, since: float | None = None, until: float | None = None
    ) -> ReliabilityReport:
        errors = len(self._store.query_events("embeddings_error", since, until))
        retries = len(self._store.query_events("embeddings_retry", since, until))
        low_conf = len(self._store.query_events("low_confidence", since, until))
        retrieves = len(self._store.query_events("retrieve", since, until))
        rate = (low_conf / retrieves) if retrieves else 0.0
        return ReliabilityReport(errors, retries, low_conf, retrieves, rate)
