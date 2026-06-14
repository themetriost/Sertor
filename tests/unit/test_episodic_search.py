"""Offline F.I.R.S.T. tests for episodic full-text search (033, FEAT-002).

Everything runs locally on a synthetic archive in `tmp_path` — no cloud, no network (the search is
pure local SQLite). FEAT-001 (`MemoryArchive`) is used as-is to populate the archive; it is never
modified. Maps to the contract `sertor.episodic-search/1` (P-* empty states, C-* invariants).
"""
from __future__ import annotations

import logging
import sqlite3

import pytest

from sertor_core.adapters.memory.archive import MemoryArchive
from sertor_core.domain.errors import InvalidTimeWindowError
from sertor_core.domain.memory import ArchivedSession, TranscriptTurn
from sertor_core.services.episodic_search import (
    EpisodicHit,
    EpisodicResults,
    EpisodicSearch,
    SearchQuery,
)

# --- helpers -------------------------------------------------------------------------------------


def _archive(
    index_dir,
    session_key: str,
    *,
    captured_at: float,
    turns: tuple[TranscriptTurn, ...],
    project_id: str = "p",
    adapter_kind: str = "claude-code",
) -> None:
    """Archive a synthetic session via FEAT-001 (read path under test, write path trusted)."""
    MemoryArchive(index_dir).upsert(
        ArchivedSession(
            session_key=session_key,
            project_id=project_id,
            captured_at=captured_at,
            adapter_kind=adapter_kind,
            turns=turns,
        )
    )


def _turn(index: int, text: str, *, role: str = "user", ts: float = 1000.0) -> TranscriptTurn:
    return TranscriptTurn(index=index, role=role, text=text, ts=ts)


# --- Phase 3: US1 — keyword retrieval (MVP) ------------------------------------------------------


def test_finds_turn_by_keyword(tmp_path):
    """T008 — keyword present → the turn appears with citation + snippet (C-CITE/C-SNIP)."""
    _archive(
        tmp_path, "s1", captured_at=1000.0,
        turns=(_turn(0, "decidiamo Azure per il backend"),),
    )
    results = EpisodicSearch(tmp_path).search(SearchQuery(text="Azure"))
    assert len(results.hits) == 1
    hit = results.hits[0]
    assert hit.session_key == "s1"
    assert hit.turn_index == 0
    assert "Azure" in hit.snippet


def test_no_match_returns_empty(tmp_path):
    """T009 — known content, absent word → empty, no exception (P-NOMATCH)."""
    _archive(tmp_path, "s1", captured_at=1000.0, turns=(_turn(0, "parliamo di retrieval"),))
    results = EpisodicSearch(tmp_path).search(SearchQuery(text="kubernetes"))
    assert results.hits == ()


def test_missing_archive_is_empty_not_error(tmp_path):
    """T010 — archive file never created → empty state, not an error (P-NOARCH)."""
    results = EpisodicSearch(tmp_path / "nope").search(SearchQuery(text="x"))
    assert results.hits == ()


def test_empty_query_returns_empty(tmp_path):
    """T011 — empty / whitespace-only query → empty, no error (P-EMPTY)."""
    _archive(tmp_path, "s1", captured_at=1000.0, turns=(_turn(0, "qualcosa"),))
    search = EpisodicSearch(tmp_path)
    assert search.search(SearchQuery(text="")).hits == ()
    assert search.search(SearchQuery(text="   ")).hits == ()


def test_all_citation_fields_present(tmp_path):
    """T012 — every hit carries the full citation; source_path may be None (C-CITE)."""
    _archive(
        tmp_path, "s1", captured_at=1234.5,
        turns=(_turn(0, "ricerca episodica full-text", role="assistant"),),
    )
    hit = EpisodicSearch(tmp_path).search(SearchQuery(text="episodica")).hits[0]
    assert isinstance(hit, EpisodicHit)
    assert hit.session_key and isinstance(hit.session_key, str)
    assert isinstance(hit.captured_at, float)
    assert isinstance(hit.role, str) and hit.role == "assistant"
    assert isinstance(hit.turn_index, int)
    assert isinstance(hit.snippet, str) and hit.snippet
    assert isinstance(hit.score, float)
    assert hit.source_path is None


def test_zero_network_io(tmp_path):
    """T013 — the search opens no socket (network disabled → must still work) (SC-004)."""
    _archive(tmp_path, "s1", captured_at=1000.0, turns=(_turn(0, "decidiamo Azure"),))
    with mock_no_network():
        results = EpisodicSearch(tmp_path).search(SearchQuery(text="Azure"))
    assert len(results.hits) == 1


def mock_no_network():
    """Context manager: any DNS resolution raises — proves the query path touches no network."""
    from unittest import mock

    return mock.patch("socket.getaddrinfo", side_effect=OSError("network disabled"))


# --- Phase 4: US2 — time window filter -----------------------------------------------------------


def test_since_filter_excludes_older(tmp_path):
    """T014 — since=1500 keeps only the newer session (C-TIME, SC-003)."""
    _archive(tmp_path, "old", captured_at=1000.0, turns=(_turn(0, "deciso Azure"),))
    _archive(tmp_path, "new", captured_at=2000.0, turns=(_turn(0, "deciso Azure"),))
    results = EpisodicSearch(tmp_path).search(SearchQuery(text="Azure", since=1500.0))
    keys = {h.session_key for h in results.hits}
    assert keys == {"new"}


def test_until_filter_excludes_newer(tmp_path):
    """T015 — until=1500 keeps only the older session (C-TIME)."""
    _archive(tmp_path, "old", captured_at=1000.0, turns=(_turn(0, "deciso Azure"),))
    _archive(tmp_path, "new", captured_at=2000.0, turns=(_turn(0, "deciso Azure"),))
    results = EpisodicSearch(tmp_path).search(SearchQuery(text="Azure", until=1500.0))
    keys = {h.session_key for h in results.hits}
    assert keys == {"old"}


def test_since_and_until_combined(tmp_path):
    """T016 — since+until keep only the central session (SC-003)."""
    _archive(tmp_path, "a", captured_at=1000.0, turns=(_turn(0, "Azure deciso"),))
    _archive(tmp_path, "b", captured_at=2000.0, turns=(_turn(0, "Azure deciso"),))
    _archive(tmp_path, "c", captured_at=3000.0, turns=(_turn(0, "Azure deciso"),))
    results = EpisodicSearch(tmp_path).search(
        SearchQuery(text="Azure", since=1500.0, until=2500.0)
    )
    keys = {h.session_key for h in results.hits}
    assert keys == {"b"}


def test_invalid_window_raises_error(tmp_path):
    """T017 — since > until → InvalidTimeWindowError describing the interval (C-ERR, FR-007)."""
    _archive(tmp_path, "s1", captured_at=1000.0, turns=(_turn(0, "x"),))
    with pytest.raises(InvalidTimeWindowError) as exc_info:
        EpisodicSearch(tmp_path).search(SearchQuery(text="x", since=2000.0, until=1000.0))
    assert "2000" in str(exc_info.value) and "1000" in str(exc_info.value)


def test_window_with_no_matching_sessions(tmp_path):
    """T018 — a window covering no session → empty, no exception (edge)."""
    _archive(tmp_path, "s1", captured_at=1000.0, turns=(_turn(0, "Azure"),))
    results = EpisodicSearch(tmp_path).search(
        SearchQuery(text="Azure", since=5000.0, until=6000.0)
    )
    assert results.hits == ()


# --- Phase 5: US3 — ordering + useful citation ---------------------------------------------------


def test_results_limited_by_limit(tmp_path):
    """T019 — N matching turns, limit=3 → exactly 3 hits (C-LIMIT)."""
    turns = tuple(_turn(i, "Azure ricorre qui") for i in range(10))
    _archive(tmp_path, "s1", captured_at=1000.0, turns=turns)
    results = EpisodicSearch(tmp_path).search(SearchQuery(text="Azure", limit=3))
    assert len(results.hits) == 3


def test_default_order_relevance_with_recency_tiebreak(tmp_path):
    """T020 — equal relevance → the more recent session's turn comes first (C-ORDER-R)."""
    _archive(tmp_path, "old", captured_at=1000.0, turns=(_turn(0, "Azure backend deciso"),))
    _archive(tmp_path, "new", captured_at=2000.0, turns=(_turn(0, "Azure backend deciso"),))
    results = EpisodicSearch(tmp_path).search(SearchQuery(text="Azure"))
    assert results.hits[0].session_key == "new"


def test_recency_order_ignores_relevance(tmp_path):
    """T021 — order=recency → most recent first regardless of relevance (C-ORDER-T)."""
    # Older session has a far richer match; newer has a thin one. Recency must still win.
    _archive(
        tmp_path, "old", captured_at=1000.0,
        turns=(_turn(0, "Azure Azure Azure Azure dominante"),),
    )
    _archive(tmp_path, "new", captured_at=2000.0, turns=(_turn(0, "Azure marginale"),))
    results = EpisodicSearch(tmp_path).search(SearchQuery(text="Azure", order="recency"))
    assert results.hits[0].session_key == "new"


def test_snippet_is_non_empty_and_finite(tmp_path):
    """T022 — snippet non-empty; fewer tokens → shorter snippet; matches at the edges (C-SNIP)."""
    long_text = "Azure " + " ".join(f"parola{i}" for i in range(60)) + " fine Azure"
    _archive(tmp_path, "s1", captured_at=1000.0, turns=(_turn(0, long_text),))
    search = EpisodicSearch(tmp_path)
    short = search.search(SearchQuery(text="Azure", snippet_tokens=5)).hits[0].snippet
    wide = search.search(SearchQuery(text="Azure", snippet_tokens=20)).hits[0].snippet
    assert short and wide
    assert len(short) < len(wide)
    # Match at the very start and the very end of the text → still produces a valid snippet.
    assert "Azure" in search.search(SearchQuery(text="fine")).hits[0].snippet


def test_multi_turn_same_session_returns_multiple_hits(tmp_path):
    """T023 — two matching turns in one session → two distinct hits, same session (C-MULTI)."""
    _archive(
        tmp_path, "s1", captured_at=1000.0,
        turns=(_turn(0, "Azure primo"), _turn(1, "Azure secondo", role="assistant")),
    )
    results = EpisodicSearch(tmp_path).search(SearchQuery(text="Azure"))
    assert len(results.hits) == 2
    assert {h.session_key for h in results.hits} == {"s1"}
    assert {h.turn_index for h in results.hits} == {0, 1}


# --- Phase 6: US4 — robustness + host-agnostic ---------------------------------------------------


def test_corrupt_row_is_skipped_not_fatal(tmp_path, caplog):
    """T024 — a malformed turn row is skipped (warning), valid turns still returned (P-BADROW)."""
    _archive(tmp_path, "s1", captured_at=1000.0, turns=(_turn(0, "Azure valido"),))
    # Inject a row whose captured_at is non-numeric → _rows_to_hits raises ValueError on float().
    db = tmp_path / "memory.sqlite"
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO sessions (session_key, project_id, captured_at, adapter_kind, metadata) "
        "VALUES ('bad', 'p', 'not-a-number', 'x', '{}')"
    )
    conn.execute(
        "INSERT INTO turns (session_key, turn_index, role, ts, content) "
        "VALUES ('bad', 0, 'user', 1000.0, 'Azure rotto')"
    )
    conn.commit()
    conn.close()
    with caplog.at_level(logging.WARNING):
        results = EpisodicSearch(tmp_path).search(SearchQuery(text="Azure"))
    keys = {h.session_key for h in results.hits}
    assert "s1" in keys
    assert "bad" not in keys
    assert any("episodic_search_bad_row" in r.getMessage() for r in caplog.records)


def test_empty_archive_returns_empty(tmp_path):
    """T025 — archive with schema but zero rows → empty, no error (P-EMPTYARCH)."""
    MemoryArchive(tmp_path)._connect()  # creates schema, no rows
    results = EpisodicSearch(tmp_path).search(SearchQuery(text="Azure"))
    assert results.hits == ()


def test_observability_event_emitted_with_hash(tmp_path, caplog):
    """T026 — event has query_hash; the clear-text query never appears in the log (C-OBS)."""
    _archive(tmp_path, "s1", captured_at=1000.0, turns=(_turn(0, "contiene segreto qui"),))
    with caplog.at_level(logging.INFO, logger="sertor_core"):
        EpisodicSearch(tmp_path).search(SearchQuery(text="segreto"))
    event_records = [r for r in caplog.records if "op=episodic_search " in r.getMessage()]
    assert event_records, "episodic_search event not emitted"
    joined = " ".join(r.getMessage() for r in event_records)
    assert "query_hash=" in joined
    assert "segreto" not in joined


def test_observability_failure_is_non_fatal(tmp_path, monkeypatch):
    """T027 — if log_event raises, search still returns a valid result (P-OBSFAIL)."""
    _archive(tmp_path, "s1", captured_at=1000.0, turns=(_turn(0, "Azure deciso"),))
    import sertor_core.services.episodic_search as mod

    def _boom(*args, **kwargs):
        raise RuntimeError("observability down")

    monkeypatch.setattr(mod, "log_event", _boom)
    results = EpisodicSearch(tmp_path).search(SearchQuery(text="Azure"))
    assert isinstance(results, EpisodicResults)
    assert len(results.hits) == 1


def test_host_agnostic_two_archives(tmp_path):
    """T028 — two archives from different hosts, same text → equivalent results (C-HOST, SC-007)."""
    host_a = tmp_path / "host_a"
    host_b = tmp_path / "host_b"
    _archive(
        host_a, "sa", captured_at=1000.0,
        turns=(_turn(0, "decidiamo Azure"),), adapter_kind="claude-code", project_id="proj-a",
    )
    _archive(
        host_b, "sb", captured_at=1000.0,
        turns=(_turn(0, "decidiamo Azure"),), adapter_kind="cursor", project_id="proj-b",
    )
    hits_a = EpisodicSearch(host_a).search(SearchQuery(text="Azure")).hits
    hits_b = EpisodicSearch(host_b).search(SearchQuery(text="Azure")).hits
    assert len(hits_a) == len(hits_b) == 1
    assert hits_a[0].snippet == hits_b[0].snippet
    assert hits_a[0].turn_index == hits_b[0].turn_index


def test_latency_under_budget(tmp_path):
    """T029 — ≥500 turns; latency_ms < 200 (SC-006, DA-FT-003)."""
    turns = tuple(_turn(i, f"turno {i} parla di Azure e retrieval") for i in range(500))
    _archive(tmp_path, "big", captured_at=1000.0, turns=turns)
    # Warm the index (one-shot rebuild) outside the measured query.
    search = EpisodicSearch(tmp_path)
    search.search(SearchQuery(text="Azure", limit=50))
    results = search.search(SearchQuery(text="Azure", limit=50))
    assert results.latency_ms < 200.0


def test_fts5_unavailable_returns_empty(tmp_path, monkeypatch, caplog):
    """A2 — sqlite3 without FTS5 (CREATE VIRTUAL TABLE fts5 raises) → empty + warning (P-NOINDEX).

    `sqlite3.Connection` is an immutable C type (cannot patch `.execute`), so we patch the module's
    `sqlite3.connect` to return a thin proxy that raises on any FTS5 statement and delegates the
    rest to the real connection — simulating a host whose `sqlite3` was built without FTS5.
    """
    _archive(tmp_path, "s1", captured_at=1000.0, turns=(_turn(0, "Azure deciso"),))
    import sertor_core.services.episodic_search as mod

    real_connect = sqlite3.connect

    class _NoFts5Conn:
        def __init__(self, *args, **kwargs):
            self._conn = real_connect(*args, **kwargs)

        def execute(self, sql, *args, **kwargs):
            if "fts5" in sql.lower():
                raise sqlite3.OperationalError("no such module: fts5")
            return self._conn.execute(sql, *args, **kwargs)

        def __getattr__(self, name):
            return getattr(self._conn, name)

    monkeypatch.setattr(mod.sqlite3, "connect", _NoFts5Conn)
    with caplog.at_level(logging.WARNING):
        results = EpisodicSearch(tmp_path).search(SearchQuery(text="Azure"))
    assert results.hits == ()
    assert any("fts5_unavailable" in r.getMessage() for r in caplog.records)


# --- Phase 7: Polish & cross-cutting -------------------------------------------------------------


def test_full_cycle_via_composition(tmp_path):
    """T030 — end-to-end through build_episodic_search + Settings (quickstart pattern)."""
    from sertor_core import build_episodic_search
    from sertor_core.config.settings import Settings

    settings = Settings(memory_enabled=True, index_dir=tmp_path)
    _archive(tmp_path, "s1", captured_at=1000.0, turns=(_turn(0, "decidiamo Azure"),))
    search = build_episodic_search(settings)
    assert search is not None
    results = search.search(SearchQuery(text="Azure"))
    assert results.hits and results.hits[0].session_key == "s1"


def test_fresh_turn_is_searchable_after_archive(tmp_path):
    """T031 — build EpisodicSearch, THEN archive, THEN search → turn is found (I-SYNC, SC-008)."""
    search = EpisodicSearch(tmp_path)
    _archive(tmp_path, "s1", captured_at=1000.0, turns=(_turn(0, "appena archiviato Azure"),))
    results = search.search(SearchQuery(text="archiviato"))
    assert len(results.hits) == 1
    assert results.hits[0].session_key == "s1"


def test_schema_creation_is_idempotent(tmp_path):
    """T032 — two EpisodicSearch over the same path → no error, no duplicate hits (I-IDEMP)."""
    _archive(tmp_path, "s1", captured_at=1000.0, turns=(_turn(0, "Azure unico"),))
    EpisodicSearch(tmp_path).search(SearchQuery(text="Azure"))
    results = EpisodicSearch(tmp_path).search(SearchQuery(text="Azure"))
    assert len(results.hits) == 1  # no duplicate from a second schema/trigger creation


def test_latency_field_present_on_empty(tmp_path):
    """Latency is always measured, even on the empty-state paths (FR-017 plumbing)."""
    results = EpisodicSearch(tmp_path / "nope").search(SearchQuery(text="x"))
    assert isinstance(results.latency_ms, float)
