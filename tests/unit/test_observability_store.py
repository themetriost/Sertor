"""Test 020 US1 — persistent observability store (SQLite). Offline F.I.R.S.T.

Store in `tmp_path`, no network. Covers FR-001/003/007/012 and SC-001/002.
"""
from __future__ import annotations

import logging

from sertor_core.observability.store import SqliteObservabilityStore


def test_record_and_query_by_operation_and_time(tmp_path):
    s = SqliteObservabilityStore(tmp_path)
    s.record_event(100.0, "index", {"documents": 3})
    s.record_event(200.0, "retrieve", {"k": 5})
    s.record_event(300.0, "index", {"documents": 4})
    # by operation (ordered by ts)
    idx = s.query_events("index", None, None)
    assert [e.fields["documents"] for e in idx] == [3, 4]
    # by time window
    win = s.query_events(None, 150.0, 250.0)
    assert len(win) == 1 and win[0].operation == "retrieve"


def test_query_all(tmp_path):
    s = SqliteObservabilityStore(tmp_path)
    s.record_event(1.0, "a", {})
    s.record_event(2.0, "b", {})
    assert [e.operation for e in s.query_events(None, None, None)] == ["a", "b"]


def test_append_across_instances(tmp_path):
    # FR-012: a fresh store on the same dir sees previously written events (non-destructive append).
    SqliteObservabilityStore(tmp_path).record_event(1.0, "index", {"n": 1})
    s2 = SqliteObservabilityStore(tmp_path)
    s2.record_event(2.0, "index", {"n": 2})
    assert [e.fields["n"] for e in s2.query_events("index", None, None)] == [1, 2]


def test_fields_roundtrip(tmp_path):
    s = SqliteObservabilityStore(tmp_path)
    payload = {"documents": 3, "provider": "azure", "paths": ["a", "b"]}
    s.record_event(1.0, "index", payload)
    assert s.query_events("index", None, None)[0].fields == payload


def test_store_failure_is_non_fatal(tmp_path, caplog):
    # FR-007: a corrupt store → record/query degrade (no-op / []) with a warning, never raise.
    (tmp_path / "observability.sqlite").write_bytes(b"not a database")
    s = SqliteObservabilityStore(tmp_path)
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        s.record_event(1.0, "index", {"n": 1})
        out = s.query_events("index", None, None)
    assert out == []
    assert any(
        getattr(r, "operation", None) == "observability_store_unavailable" for r in caplog.records
    )
