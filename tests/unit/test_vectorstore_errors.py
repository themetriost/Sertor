"""Test US4 — vector store backend errors (REQ-021): never silent empty."""
from __future__ import annotations

import pytest

from sertor_core.adapters.vectorstores.chroma import ChromaStore
from sertor_core.domain.entities import EmbeddedChunk
from sertor_core.domain.errors import VectorStoreError


class _BoomClient:
    """Failing client stub: simulates an unavailable backend."""

    def get_or_create_collection(self, **_):
        raise RuntimeError("backend down")

    def get_collection(self, **_):
        raise RuntimeError("backend down")


def test_upsert_raises_vector_store_error_on_backend_failure():
    store = ChromaStore(client=_BoomClient())
    rec = EmbeddedChunk(chunk_id="a#0", vector=[1.0], payload={"text": "a", "doc_type": "code"})
    with pytest.raises(VectorStoreError) as ei:
        store.upsert("c", [rec])
    assert ei.value.backend == "chroma"


def test_query_on_missing_collection_is_empty_not_error():
    # get_collection failing with 'missing' -> [] (not a backend error) (REQ-028)
    store = ChromaStore(client=_BoomClient())
    assert store.query("c", [1.0], k=3) == []


def test_init_failure_raises_vector_store_error(tmp_path):
    # Force an initialization failure by passing an invalid path (a file, not a directory).
    bad = tmp_path / "afile"
    bad.write_text("x", encoding="utf-8")
    with pytest.raises(VectorStoreError):
        ChromaStore(persist_dir=bad)


class _StubColl:
    """Collection stub whose metadata-filter query fails or succeeds (drives the refresh path)."""

    def __init__(self, fail: bool):
        self._fail = fail

    def query(self, **_):
        if self._fail:
            raise RuntimeError("InternalError: stale metadata segment")
        return {
            "ids": [["a.py#0"]],
            "documents": [["code body"]],
            "metadatas": [[{"doc_type": "code", "path": "a.py"}]],
            "distances": [[0.1]],
        }


class _StubClient:
    def __init__(self, fail: bool):
        self._fail = fail

    def get_collection(self, **_):
        return _StubColl(self._fail)


def test_query_refreshes_owned_client_and_retries_once():
    # The first (stale) client fails the metadata-filter query; the refresh factory yields a fresh
    # client that succeeds. Mirrors the 2026-06-19 stale-server failure recovering after a refresh.
    clients = iter([_StubClient(fail=True), _StubClient(fail=False)])
    store = ChromaStore(client_factory=lambda: next(clients))
    res = store.query("c", [1.0], k=3, doc_type="code")
    assert [r.chunk_id for r in res] == ["a.py#0"]


def test_query_raises_when_retry_also_fails():
    # The refresh yields another failing client: the backend error is surfaced (never silent empty).
    clients = iter([_StubClient(fail=True), _StubClient(fail=True)])
    store = ChromaStore(client_factory=lambda: next(clients))
    with pytest.raises(VectorStoreError) as ei:
        store.query("c", [1.0], k=3, doc_type="code")
    assert ei.value.backend == "chroma"


def test_injected_client_is_not_refreshed():
    # An injected client (no factory) is not refreshable: a query failure raises immediately.
    store = ChromaStore(client=_StubClient(fail=True))
    with pytest.raises(VectorStoreError):
        store.query("c", [1.0], k=3, doc_type="code")
