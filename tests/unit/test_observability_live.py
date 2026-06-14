"""Test 022 US1 — live snapshot model (pure, NO terminal). Offline F.I.R.S.T.

The *what to show* logic is verifiable without Textual (FR-010/SC-005).
"""
from __future__ import annotations

from sertor_core.observability.live import live_snapshot, render_snapshot
from sertor_core.services.observability_report import ObservabilityReports
from tests.fixtures.mocks import InMemoryObservabilityStore

DAY1 = 1_700_000_000.0


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
