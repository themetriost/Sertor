"""Unit tests for 145 (E4-FEAT-016) — the semantic memory survives oversized and refused turns.

Reproduces the field report of node Kaelen (Acta, 2026-10-20): one ~290,000-char turn in a
181-turn session made the provider answer `http 400` to the whole batch, and all 181 turns were
lost under a misleading `provider_unavailable`. Offline: `LimitedEmbedder` applies the same rule
as the real service (any text over a budget → the WHOLE request is refused, non-retriable).
"""
from __future__ import annotations

import pytest

from sertor_core.config.settings import Settings
from sertor_core.domain.errors import EmbeddingError
from sertor_core.domain.memory import ArchivedSession, TranscriptTurn
from sertor_core.services import memory_semantic
from sertor_core.services.chunking._tokens import cap_to_tokens
from sertor_core.services.memory_semantic import (
    MemorySemanticIndex,
    RejectedTurn,
    SemanticMemoryQuery,
)
from tests.fixtures.mocks import FakeEmbedder
from tests.unit.test_memory_semantic import COLLECTION, FakeArchive, IncrementalStore

MAX_TOKENS = 500
CHAR_BUDGET = 8000  # every piece of MAX_TOKENS tokens fits; the raw big turn does not


class LimitedEmbedder(FakeEmbedder):
    """Refuses the WHOLE request (`http 400`, non-retriable) if any text exceeds `budget` chars."""

    def __init__(self, budget: int = CHAR_BUDGET, refuse_marker: str | None = None):
        super().__init__()
        self.budget = budget
        self.refuse_marker = refuse_marker
        self.texts_seen = 0

    def embed(self, texts):
        self.calls += 1
        self.texts_seen += len(texts)
        if any(len(t) > self.budget for t in texts) or (
            self.refuse_marker and any(self.refuse_marker in t for t in texts)
        ):
            raise EmbeddingError("refused", provider="fake", reason="http 400", retriable=False)
        return [self._vector(t) for t in texts]


def _big_text(chars: int = 290_000, tail: str = "zebracodaterm") -> str:
    words = [f"lorem{i % 997}" for i in range(chars // 9)]
    return " ".join(words) + f" {tail}"


def _session(key: str, n_turns: int, big_at: int | None = None, text_of=None) -> ArchivedSession:
    def text(i: int) -> str:
        if text_of is not None and text_of(i) is not None:
            return text_of(i)
        if i == big_at:
            return _big_text()
        return f"turn {i} of {key}"

    return ArchivedSession(
        session_key=key,
        project_id="proj",
        captured_at=1000.0,
        adapter_kind="claude-code",
        turns=tuple(
            TranscriptTurn(index=i, role="user" if i % 2 == 0 else "assistant", text=text(i))
            for i in range(n_turns)
        ),
    )


def _index(embedder, store=None) -> MemorySemanticIndex:
    return MemorySemanticIndex(
        embedder, store or IncrementalStore(), COLLECTION, Settings(max_chunk_tokens=MAX_TOKENS)
    )


@pytest.fixture
def events(monkeypatch):
    recorded: list[tuple[str, dict]] = []

    def fake_log_event(level, op, **fields):
        recorded.append((op, fields))

    monkeypatch.setattr(memory_semantic, "log_event", fake_log_event)
    return recorded


# --- US1: an oversized turn no longer loses the session ----------------------------------------


def test_kaelen_case_all_181_turns_indexed() -> None:
    """SC-001: 181 turns, one of ~290,000 chars → 181 indexed, 0 errors (was 0 / 181)."""
    report = _index(LimitedEmbedder()).index_session(_session("k", 181, big_at=37))
    assert (report.embedded, report.errors, report.rejected) == (181, 0, ())


def test_turn_within_budget_keeps_historical_id_and_payload() -> None:
    """FR-002: a turn within the budget keeps `key#i` and the pre-145 payload (no part fields)."""
    store = IncrementalStore()
    _index(LimitedEmbedder(), store).index_session(_session("s", 2))
    coll = store._data[COLLECTION]
    assert set(coll) == {"s#0", "s#1"}
    assert "part" not in coll["s#0"][1] and "parts" not in coll["s#0"][1]


def test_split_turn_pieces_ids_payload_and_budget() -> None:
    """FR-001: an oversized turn → `key#i/p` pieces, each within the budget, with part/parts."""
    store = IncrementalStore()
    _index(LimitedEmbedder(), store).index_session(_session("s", 2, big_at=1))
    coll = store._data[COLLECTION]
    pieces = sorted((cid for cid in coll if cid.startswith("s#1/")), key=lambda c: int(c[4:]))
    assert len(pieces) > 1 and "s#1" not in coll
    for p, cid in enumerate(pieces):
        payload = coll[cid][1]
        assert (payload["part"], payload["parts"], payload["turn_index"]) == (p, len(pieces), 1)
        assert len(payload["text"]) <= CHAR_BUDGET


def test_second_run_is_incremental_with_zero_provider_calls() -> None:
    """SC-003/FR-010: re-indexing a fully indexed session (split turn included) → no calls."""
    store, embedder = IncrementalStore(), LimitedEmbedder()
    _index(embedder, store).index_session(_session("k", 181, big_at=37))
    calls = embedder.calls
    report = _index(embedder, store).index_session(_session("k", 181, big_at=37))
    assert (report.embedded, report.skipped, report.errors) == (0, 181, 0)
    assert embedder.calls == calls


def test_pre_145_index_is_not_reembedded() -> None:
    """REQ-036: an index built with the historical ids (`key#i`) is still «already indexed»."""
    store = IncrementalStore()
    _index(FakeEmbedder(), store).index_session(_session("old", 5))
    embedder = LimitedEmbedder()
    report = _index(embedder, store).index_session(_session("old", 5))
    assert (report.embedded, report.skipped) == (0, 5)
    assert embedder.calls == 0


def test_search_returns_split_turn_once() -> None:
    """SC-004/FR-003: a term only in the tail of a split turn → that turn, once."""
    store = IncrementalStore()
    idx = _index(LimitedEmbedder(), store)
    idx.index_session(_session("s", 3, big_at=1))
    last_piece = cap_to_tokens(_big_text(), MAX_TOKENS, Settings().chunk_overlap)[-1]
    hits = idx.search(SemanticMemoryQuery(text=last_piece, limit=50)).hits
    assert hits[0].session_key == "s" and hits[0].turn_index == 1
    turn_refs = [(h.session_key, h.turn_index) for h in hits]
    assert len(turn_refs) == len(set(turn_refs))
    assert sum(1 for ref in turn_refs if ref == ("s", 1)) == 1


# --- US2: a refusal hits only the refused turn ---------------------------------------------------


def test_refusal_confined_to_the_refused_turn_and_retried_next_run() -> None:
    """SC-002/FR-004/FR-010: provider refuses turn 4 of 10 → 9 indexed, 1 error, 4 retried later."""
    store, embedder = IncrementalStore(), LimitedEmbedder(refuse_marker="POISON")
    session = _session("s1", 10, text_of=lambda i: "POISON turn" if i == 4 else None)
    report = _index(embedder, store).index_session(session)
    assert (report.embedded, report.errors) == (9, 1)
    assert report.rejected == (RejectedTurn("s1", 4, "http 400"),)
    assert "s1#4" not in store._data[COLLECTION]

    seen_before = embedder.texts_seen
    again = _index(embedder, store).index_session(session)
    assert (again.embedded, again.skipped, again.errors) == (0, 9, 1)
    assert embedder.texts_seen - seen_before == 2  # batch with turn 4 alone, then its fallback


def test_split_turn_is_all_or_nothing() -> None:
    """FR-005: one refused piece of a split turn → no piece of that turn reaches the store."""
    poisoned = _big_text(tail="POISON")
    store = IncrementalStore()
    report = _index(LimitedEmbedder(refuse_marker="POISON"), store).index_session(
        _session("s", 3, text_of=lambda i: poisoned if i == 1 else None)
    )
    assert (report.embedded, report.errors) == (2, 1)
    assert report.rejected == (RejectedTurn("s", 1, "http 400"),)
    assert not any(cid.startswith("s#1") for cid in store._data[COLLECTION])


@pytest.mark.parametrize(
    ("reason", "retriable"), [("ConnectError", True), ("http 503", True), ("http 401", False)]
)
def test_unavailable_or_config_error_has_no_fallback(reason, retriable, events) -> None:
    """FR-006: outage / auth error → one call only, every new turn an error, nothing rejected."""

    class DownEmbedder(FakeEmbedder):
        def embed(self, texts):
            self.calls += 1
            raise EmbeddingError("down", provider="fake", reason=reason, retriable=retriable)

    embedder = DownEmbedder()
    report = _index(embedder).index_session(_session("s", 4))
    assert (report.embedded, report.errors, report.rejected) == (0, 4, ())
    assert embedder.calls == 1
    assert [f["reason"] for op, f in events if op == "memory_semantic_index_failed"] == [
        "provider_unavailable"
    ]


def test_outage_during_fallback_stops_it() -> None:
    """FR-006: service down mid-fallback → stop; remaining turns are errors, not rejected."""

    class FlakyEmbedder(LimitedEmbedder):
        def embed(self, texts):
            if self.calls >= 3:  # batch + 2 fallback calls succeed/refuse, then the service dies
                self.calls += 1
                raise EmbeddingError("down", provider="fake", reason="http 503", retriable=True)
            return super().embed(texts)

    session = _session("s", 6, text_of=lambda i: "POISON" if i == 0 else None)
    report = _index(FlakyEmbedder(refuse_marker="POISON")).index_session(session)
    assert report.rejected == (RejectedTurn("s", 0, "http 400"),)
    assert report.embedded == 1  # turn 1 made it before the outage
    assert report.errors == 5  # 1 rejected + 4 not handled
    assert report.embedded + report.errors == 6


# --- US3: the outcome says what happened, and where ----------------------------------------------


def test_rejection_event_is_input_rejected_and_metrics_only(events) -> None:
    """FR-007/FR-009: reason=input_rejected with a count; no transcript text, no session key."""
    session = _session("secret-key", 3, text_of=lambda i: "POISON words" if i == 2 else None)
    _index(LimitedEmbedder(refuse_marker="POISON")).index_session(session)
    failed = [f for op, f in events if op == "memory_semantic_index_failed"]
    assert failed == [{"reason": "input_rejected", "detail": "http 400", "rejected": 1}]
    rendered = repr(events)
    assert "secret-key" not in rendered and "POISON" not in rendered


def test_index_all_aggregates_rejected_and_reports_count(events) -> None:
    """index_all concatenates `rejected` across sessions; the final event carries the count."""
    sessions = [
        _session("a", 3, text_of=lambda i: "POISON" if i == 1 else None),
        _session("b", 2),
    ]
    idx = _index(LimitedEmbedder(refuse_marker="POISON"))
    report = idx.index_all(FakeArchive(sessions))
    assert (report.embedded, report.errors) == (4, 1)
    assert report.rejected == (RejectedTurn("a", 1, "http 400"),)
    final = [f for op, f in events if op == "memory_semantic_index"]
    assert final and final[-1]["rejected"] == 1


def test_cli_report_names_session_turn_and_reason() -> None:
    """FR-008/SC-005: human + JSON outcome list every rejected turn; counts unchanged."""
    import json

    from sertor_core.cli import output
    from sertor_core.services.memory_semantic import SemanticIndexReport

    report = SemanticIndexReport(
        embedded=180, skipped=1540, errors=1, rejected=(RejectedTurn("sess-1", 37, "http 400"),)
    )
    human = output.format_semantic_index_report(report, json=False).splitlines()
    assert human == [
        "embedded=180 skipped=1540 errors=1",
        "rejected session=sess-1 turn=37 reason=http 400",
    ]
    assert json.loads(output.format_semantic_index_report(report, json=True)) == {
        "embedded": 180, "skipped": 1540, "errors": 1,
        "rejected": [{"session": "sess-1", "turn": 37, "reason": "http 400"}],
    }


def test_cli_report_without_rejections_is_unchanged() -> None:
    """No refusal → the pre-145 output, byte for byte (compatibility for parsers)."""
    from sertor_core.cli import output
    from sertor_core.services.memory_semantic import SemanticIndexReport

    report = SemanticIndexReport(embedded=4, skipped=2, errors=1)
    assert output.format_semantic_index_report(report, json=False) == (
        "embedded=4 skipped=2 errors=1"
    )
    assert output.format_semantic_index_report(report, json=True) == (
        '{"embedded": 4, "skipped": 2, "errors": 1}'
    )
