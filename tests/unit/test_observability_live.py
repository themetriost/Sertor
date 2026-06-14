"""Test 022 US1 — live snapshot model (pure, NO terminal). Offline F.I.R.S.T.

The *what to show* logic is verifiable without Textual (FR-010/SC-005).
"""
from __future__ import annotations

from sertor_core.observability.live import (
    live_snapshot,
    next_window,
    render_cache_report,
    render_corpus_report,
    render_cost_report,
    render_snapshot,
    time_window,
)
from sertor_core.services.observability_report import ObservabilityReports
from tests.fixtures.mocks import InMemoryObservabilityStore

DAY1 = 1_700_000_000.0
DAY2 = DAY1 + 86_400


def _reports(events):
    store = InMemoryObservabilityStore()
    for ts, op, fields in events:
        store.record_event(ts, op, fields)
    return ObservabilityReports(store)


def test_live_snapshot_current_state():
    s = live_snapshot(_reports([
        (DAY1, "index", {"documents": 5, "chunks": 50, "embedding_dim": 3072}),
        (DAY1, "embeddings_cache", {"hits": 8, "misses": 2}),
        (DAY1, "embeddings", {"provider": "azure", "tokens": 100, "texts": 2}),
        (DAY1, "retrieve", {"elapsed_ms": 10.0}),
    ]))
    assert s.has_data is True                                   # SC-001
    assert s.last_index.documents == 5 and s.last_index.chunks == 50
    assert (s.cache_hits, s.cache_misses) == (8, 2)
    assert s.cache_hit_rate == 0.8
    assert s.total_tokens == 100 and s.tokens_by_provider == {"azure": 100}
    assert len(s.recent_events) == 4


def test_live_snapshot_empty_is_honest():
    s = live_snapshot(_reports([]))                             # FR-005 / SC-003
    assert s.has_data is False
    assert s.cache_hits == 0 and s.total_tokens == 0 and s.recent_events == []


def test_recent_events_tail_limit():
    reports = _reports([(DAY1 + i, "retrieve", {"i": i}) for i in range(30)])
    recent = reports.recent_events(limit=5)
    assert [e.fields["i"] for e in recent] == [25, 26, 27, 28, 29]


def test_render_snapshot_content():
    text = render_snapshot(live_snapshot(_reports([
        (DAY1, "index", {"documents": 5, "chunks": 50, "embedding_dim": 3072}),
        (DAY1, "embeddings_cache", {"hits": 8, "misses": 2}),
    ])))
    assert "50 chunks" in text and "8 hits" in text


def test_render_snapshot_empty_has_call_to_action():
    text = render_snapshot(live_snapshot(_reports([])))
    assert "No observability data" in text and "SERTOR_OBSERVABILITY" in text


def test_live_snapshot_deterministic():
    events = [(DAY1, "embeddings_cache", {"hits": 1, "misses": 1})]
    assert live_snapshot(_reports(events)) == live_snapshot(_reports(events))  # SC-005


# --- F4: report views (pure) + time window ---------------------------------------------------


def test_time_window_presets():
    now = 1_000_000.0
    assert time_window("all", now) == (None, None)
    assert time_window("7d", now) == (now - 7 * 86400, None)
    assert time_window("24h", now) == (now - 86400, None)


def test_next_window_cycles():
    assert next_window("all") == "7d"
    assert next_window("7d") == "24h"
    assert next_window("24h") == "all"


def test_render_cache_report_totals_and_buckets():
    r = _reports([
        (DAY1, "embeddings_cache", {"hits": 4, "misses": 1}),
        (DAY2, "embeddings_cache", {"hits": 2, "misses": 0}),
        (DAY1, "embeddings", {"tokens": 50, "texts": 1}),
    ]).cache_report()
    text = render_cache_report(r)
    assert "6 hits / 1 misses" in text          # SC-001
    assert text.count("hits /") >= 3            # totals + 2 buckets


def test_render_cache_report_empty():
    assert "no data" in render_cache_report(_reports([]).cache_report())  # SC-004


def test_render_cost_report():
    reports = _reports([(DAY1, "embeddings", {"provider": "azure", "tokens": 100, "texts": 1})])
    text = render_cost_report(reports.cost_report())
    assert "100 tokens" in text and "azure=100" in text


def test_render_corpus_report_freshness():
    r = _reports([
        (DAY1, "index", {"documents": 3, "chunks": 30, "embedding_dim": 8}),
    ]).health_report()
    text = render_corpus_report(r, now=DAY1 + 3 * 3600)   # 3h after the index
    assert "30 chunks" in text and "3h ago" in text


def test_render_corpus_report_empty():
    assert "no index" in render_corpus_report(_reports([]).health_report(), now=DAY1)


def test_report_window_filters_events():
    # SC-002: a 24h window includes only events within it.
    now = DAY2 + 100
    events = [
        (DAY1, "embeddings_cache", {"hits": 5, "misses": 0}),   # ~1 day before DAY2 → outside 24h
        (DAY2, "embeddings_cache", {"hits": 2, "misses": 1}),   # within 24h of `now`
    ]
    reports = _reports(events)
    since, until = time_window("24h", now)
    r = reports.cache_report(since, until)
    assert r.total_hits == 2 and r.total_misses == 1
