"""Test 021 — observability reports (aggregation service). Offline F.I.R.S.T.

Events are pushed into an in-memory `ObservabilityStore`; the reports are pure aggregations.
Covers FR-001..012 and SC-001..007.
"""
from __future__ import annotations

from sertor_core.config.settings import Settings
from sertor_core.services.observability_report import (
    ObservabilityReports,
    bucket_key,
    percentiles,
)
from tests.fixtures.mocks import InMemoryObservabilityStore

DAY1 = 1_700_000_000.0   # 2023-11-14 (UTC)
DAY2 = DAY1 + 86_400     # +1 day


def _reports(events):
    store = InMemoryObservabilityStore()
    for ts, op, fields in events:
        store.record_event(ts, op, fields)
    return ObservabilityReports(store, default_bucket="day")


def test_cache_report_hits_misses_series_and_savings():
    r = _reports([
        (DAY1, "embeddings_cache", {"hits": 10, "misses": 2, "total": 12}),
        (DAY2, "embeddings_cache", {"hits": 5, "misses": 0, "total": 5}),
        (DAY1, "embeddings", {"provider": "azure", "texts": 2, "tokens": 100}),
    ]).cache_report()
    assert r.total_hits == 15 and r.total_misses == 2          # SC-001
    assert len(r.series) == 2 and sum(b.hits for b in r.series) == 15
    assert r.estimated_tokens_saved == 750                      # hits 15 × (100/2), estimate FR-002


def test_cache_report_empty_is_zeros():
    r = _reports([]).cache_report()                             # FR-010 / SC-004
    assert r.total_hits == 0 and r.total_misses == 0
    assert r.series == [] and r.estimated_tokens_saved == 0


def test_cost_report_by_provider_and_bucket_excludes_tokenless():
    r = _reports([
        (DAY1, "embeddings", {"provider": "azure", "tokens": 100, "texts": 3}),
        (DAY2, "embeddings", {"provider": "azure", "tokens": 50, "texts": 1}),
        (DAY1, "embeddings", {"provider": "ollama", "texts": 4}),  # no tokens → excluded (FR-004)
    ]).cost_report()
    assert r.total_tokens == 150                                # SC-002
    assert r.by_provider == {"azure": 150}
    assert len(r.series) == 2


def test_health_report_last_index_and_series():
    r = _reports([
        (DAY1, "index", {"documents": 10, "chunks": 100, "embedding_dim": 3072}),
        (DAY2, "index", {"documents": 12, "chunks": 120, "embedding_dim": 3072}),
    ]).health_report()
    assert r.documents == 12 and r.chunks == 120 and r.embedding_dim == 3072  # last index, SC-003
    assert r.last_index_ts == DAY2 and len(r.series) == 2


def test_latency_report_percentiles():
    events = [(DAY1, "retrieve", {"elapsed_ms": float(v)}) for v in [10, 20, 30, 40, 100]]
    stat = _reports(events).latency_report().by_operation["retrieve"]
    assert stat.count == 5
    assert stat.p50_ms == 30.0      # nearest-rank ceil(.5*5)-1 = 2
    assert stat.p95_ms == 100.0     # ceil(.95*5)-1 = 4


def test_reliability_report_counts_and_abstention_rate():
    r = _reports([
        (DAY1, "embeddings_error", {}),
        (DAY1, "embeddings_retry", {}),
        (DAY1, "low_confidence", {}),
        (DAY1, "retrieve", {}),
        (DAY1, "retrieve", {}),
    ]).reliability_report()
    assert (r.errors, r.retries, r.low_confidence, r.retrieves) == (1, 1, 1, 2)
    assert r.abstention_rate == 0.5


def test_reports_are_deterministic():
    events = [
        (DAY1, "embeddings_cache", {"hits": 3, "misses": 1}),
        (DAY2, "embeddings_cache", {"hits": 2, "misses": 2}),
    ]
    assert _reports(events).cache_report() == _reports(events).cache_report()  # SC-005


def test_percentiles_and_bucket_helpers():
    assert percentiles([], (50, 95)) == {50: 0.0, 95: 0.0}
    assert bucket_key(DAY1, "day") == bucket_key(DAY1 + 3600, "day")  # same UTC day


def test_build_observability_reports_wiring(tmp_path):
    # FR-011 + FR-010: real wiring on an empty store → zeros, no error.
    from sertor_core import build_observability_reports

    reports = build_observability_reports(Settings(index_dir=tmp_path))
    assert reports.cache_report().total_hits == 0
    assert reports.health_report().documents == 0
