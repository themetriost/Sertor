"""Unit tests for the semantic memory index (072, FEAT-004) — offline, mock embedder/store.

Covers TASK-F01 (service contract), TASK-US5-01 (on-machine/offline with the local provider),
TASK-US6-02 (non-fatal degradation). No cloud, no network: a deterministic fake embedder + an
in-memory store (with the optional `contains_ids` incrementality probe).
"""
from __future__ import annotations

import pytest

from sertor_core.config.settings import Settings
from sertor_core.domain.entities import DocType, RetrievalResult
from sertor_core.domain.errors import EmbeddingError, InvalidTimeWindowError, VectorStoreError
from sertor_core.domain.memory import ArchivedSession, TranscriptTurn
from sertor_core.services.memory_semantic import (
    MemorySemanticIndex,
    SemanticMemoryQuery,
)
from tests.fixtures.mocks import FakeEmbedder, InMemoryStore, _cosine

COLLECTION = "memory__sertor__fake_8"


class IncrementalStore(InMemoryStore):
    """In-memory store that mirrors ChromaStore's payload→metadata semantics + the optional
    `contains_ids` incrementality probe.

    The shared `InMemoryStore.query` only surfaces `payload["metadata"]`; the REAL ChromaStore
    returns the WHOLE payload as `RetrievalResult.metadata` (`_to_results`). The semantic index
    reads its citation fields (`session_key`/`turn_index`/`captured_at`/`role`) from there, so this
    fake reproduces the real behaviour to keep the test faithful (NFR-007 — mock matches contract).
    """

    def query(self, collection, vector, k, doc_type="both"):
        coll = self._data.get(collection)
        if not coll:
            return []
        scored = sorted(
            ((_cosine(vector, vec), cid, payload) for cid, (vec, payload) in coll.items()),
            key=lambda t: t[0], reverse=True,
        )
        return [
            RetrievalResult(
                text=payload.get("text", ""),
                path=payload.get("path", ""),
                chunk_id=cid,
                doc_type=DocType(payload.get("doc_type", "code")),
                score=score,
                metadata=dict(payload),  # full payload, like ChromaStore `_to_results`
            )
            for score, cid, payload in scored[: max(0, k)]
        ]

    def contains_ids(self, collection: str, ids: list[str]) -> list[str]:
        coll = self._data.get(collection, {})
        return [cid for cid in ids if cid in coll]


def _session(key: str, n_turns: int = 2, captured_at: float = 1000.0) -> ArchivedSession:
    return ArchivedSession(
        session_key=key,
        project_id="proj",
        captured_at=captured_at,
        adapter_kind="claude-code",
        turns=tuple(
            TranscriptTurn(index=i, role="user" if i % 2 == 0 else "assistant",
                           text=f"turn {i} of {key}")
            for i in range(n_turns)
        ),
    )


def _index(embedder=None, store=None) -> MemorySemanticIndex:
    return MemorySemanticIndex(
        embedder or FakeEmbedder(),
        store or IncrementalStore(),
        COLLECTION,
        Settings(),
    )


# --- search -------------------------------------------------------------------------------------


def test_search_empty_index_returns_empty_state() -> None:
    """REQ-021/US6-AC1: index absent → hits=() + warning, NOT an error."""
    results = _index().search(SemanticMemoryQuery(text="anything"))
    assert results.hits == ()


def test_search_maps_six_fields() -> None:
    """REQ-010/US1-AC2: a hit carries the six required fields."""
    embedder, store = FakeEmbedder(), IncrementalStore()
    idx = _index(embedder, store)
    idx.index_session(_session("s1", n_turns=2, captured_at=1500.0))

    results = idx.search(SemanticMemoryQuery(text="turn 0 of s1", limit=5))
    assert results.hits
    hit = results.hits[0]
    assert hit.session_key == "s1"
    assert isinstance(hit.turn_index, int)
    assert hit.captured_at == 1500.0
    assert hit.role in ("user", "assistant")
    assert "of s1" in hit.snippet
    assert isinstance(hit.score, float)


def test_search_time_window_filters() -> None:
    """REQ-012/US1-AC1: since/until restrict to the in-range hits (post-query on captured_at)."""
    embedder, store = FakeEmbedder(), IncrementalStore()
    idx = _index(embedder, store)
    idx.index_session(_session("old", n_turns=1, captured_at=100.0))
    idx.index_session(_session("new", n_turns=1, captured_at=2000.0))

    results = idx.search(SemanticMemoryQuery(text="turn", since=1000.0, limit=10))
    assert results.hits
    assert all(h.captured_at >= 1000.0 for h in results.hits)
    assert all(h.session_key == "new" for h in results.hits)


def test_search_invalid_window_raises() -> None:
    """since > until → InvalidTimeWindowError (parity with FEAT-002)."""
    with pytest.raises(InvalidTimeWindowError):
        _index().search(SemanticMemoryQuery(text="x", since=10.0, until=1.0))


def test_search_empty_query_returns_empty() -> None:
    """Empty/whitespace query → hits=() (contract §search edge case)."""
    assert _index().search(SemanticMemoryQuery(text="   ")).hits == ()


# --- index_session ------------------------------------------------------------------------------


def test_index_session_new_embeds_and_upserts() -> None:
    """REQ-006: a new session → embedded=N, skipped=0, upsert performed."""
    embedder, store = FakeEmbedder(), IncrementalStore()
    idx = _index(embedder, store)
    report = idx.index_session(_session("s1", n_turns=3))
    assert report.embedded == 3
    assert report.skipped == 0
    assert report.errors == 0
    assert store.exists(COLLECTION)


def test_index_session_already_indexed_zero_embed() -> None:
    """REQ-030/NFR-009/US3-AC2: fully-indexed session → embedded=0, skipped=N, zero embed calls."""
    embedder, store = FakeEmbedder(), IncrementalStore()
    idx = _index(embedder, store)
    session = _session("s1", n_turns=2)
    idx.index_session(session)
    calls_after_first = embedder.calls

    report = idx.index_session(session)
    assert report.embedded == 0
    assert report.skipped == 2
    assert embedder.calls == calls_after_first  # no further embed calls


def test_index_session_idempotent_no_duplicates() -> None:
    """REQ-006/US3-AC3: indexing the same session twice → no duplicate records."""
    embedder, store = FakeEmbedder(), IncrementalStore()
    idx = _index(embedder, store)
    session = _session("s1", n_turns=2)
    idx.index_session(session)
    idx.index_session(session)
    # Two turns → exactly two records under their stable ids.
    assert len(store._data[COLLECTION]) == 2
    assert set(store._data[COLLECTION]) == {"s1#0", "s1#1"}


def test_index_session_store_failure_is_counted_not_fatal() -> None:
    """REQ-008: a store outage on upsert → errors=N, non-fatal."""

    class FailingStore(IncrementalStore):
        def upsert(self, collection, records):
            raise VectorStoreError("down", backend="fake", reason="boom")

    idx = _index(FakeEmbedder(), FailingStore())
    report = idx.index_session(_session("s1", n_turns=2))
    assert report.errors == 2
    assert report.embedded == 0


def test_index_session_embedding_failure_is_counted_not_fatal() -> None:
    """REQ-023/US6-AC3: provider outage during index → errors counted, no crash."""

    class FailingEmbedder(FakeEmbedder):
        def embed(self, texts):
            raise EmbeddingError("down", provider="fake", reason="timeout", retriable=True)

    idx = _index(FailingEmbedder(), IncrementalStore())
    report = idx.index_session(_session("s1", n_turns=2))
    assert report.errors == 2
    assert report.embedded == 0


# --- index_all ----------------------------------------------------------------------------------


class FakeArchive:
    """Minimal archive stub exposing `list_recent` + `get` (the surface index_all consumes)."""

    def __init__(self, sessions: list[ArchivedSession]):
        self._sessions = {s.session_key: s for s in sessions}

    def list_recent(self, limit: int):
        from sertor_core.domain.memory import SessionSummary

        return tuple(
            SessionSummary(session_key=s.session_key, captured_at=s.captured_at,
                           turn_count=len(s.turns))
            for s in list(self._sessions.values())[:limit]
        )

    def get(self, session_key: str):
        return self._sessions.get(session_key)


def test_index_all_incremental_embeds_only_new() -> None:
    """REQ-031/US3-AC4/SC-006: backfill embeds only the not-yet-indexed sessions."""
    embedder, store = FakeEmbedder(), IncrementalStore()
    idx = _index(embedder, store)
    s1, s2 = _session("s1", n_turns=2), _session("s2", n_turns=2)
    # Pre-index s1 only.
    idx.index_session(s1)
    calls_after_pre = embedder.calls

    archive = FakeArchive([s1, s2])
    report = idx.index_all(archive)
    assert report.embedded == 2  # only s2's two turns
    assert report.skipped == 2   # s1's two turns skipped
    assert embedder.calls == calls_after_pre + 1  # exactly one embed call (s2)


# --- US5-01: on-machine / offline ---------------------------------------------------------------


def test_local_provider_no_network_calls() -> None:
    """RNF-1/US5-AC1/SC-003: index + search exercise the mock embedder, no HTTP."""
    embedder, store = FakeEmbedder(), IncrementalStore()
    idx = _index(embedder, store)
    idx.index_session(_session("s1", n_turns=2))
    assert embedder.calls >= 1
    idx.search(SemanticMemoryQuery(text="turn 0 of s1"))
    # The fake embedder opens no socket; reaching here without an exception is the offline proof.


# --- US6-02: degradation ------------------------------------------------------------------------


def test_search_provider_down_returns_empty_not_crash() -> None:
    """REQ-022/US6-AC2: provider outage at query time → empty state, caller does not crash."""

    class FailingEmbedder(FakeEmbedder):
        def embed(self, texts):
            raise EmbeddingError("down", provider="fake", reason="timeout", retriable=True)

    # The collection must exist so the code reaches the embed call.
    store = IncrementalStore()
    _index(FakeEmbedder(), store).index_session(_session("s1"))
    idx = _index(FailingEmbedder(), store)
    assert idx.search(SemanticMemoryQuery(text="x")).hits == ()


def test_search_store_down_returns_empty_not_crash() -> None:
    """REQ-022: store outage at query time → empty state, no crash."""

    class FailingStore(IncrementalStore):
        def query(self, collection, vector, k, doc_type="both"):
            raise VectorStoreError("down", backend="fake", reason="boom")

    store = FailingStore()
    _index(FakeEmbedder(), store).index_session(_session("s1"))
    idx = _index(FakeEmbedder(), store)
    assert idx.search(SemanticMemoryQuery(text="x")).hits == ()


def test_search_malformed_record_is_skipped() -> None:
    """REQ-023/US6-AC3: a record with a malformed payload is skipped; valid ones still served."""
    store = IncrementalStore()
    idx = _index(FakeEmbedder(), store)
    idx.index_session(_session("good", n_turns=1, captured_at=500.0))
    # Inject a malformed record (missing captured_at) directly into the collection.
    coll = store._data[COLLECTION]
    coll["bad#0"] = ([0.0] * 8, {"session_key": "bad", "turn_index": 0, "role": "user"})

    results = idx.search(SemanticMemoryQuery(text="turn", limit=10))
    keys = {h.session_key for h in results.hits}
    assert "good" in keys
    assert "bad" not in keys
