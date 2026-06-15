"""Test US4 — Chroma vector store (REQ-017/019/027/028)."""
from __future__ import annotations

from sertor_core.adapters.vectorstores.chroma import ChromaStore
from sertor_core.domain.entities import EmbeddedChunk


def _rec(cid: str, vec: list[float], doc_type: str, path: str, text: str) -> EmbeddedChunk:
    return EmbeddedChunk(
        chunk_id=cid,
        vector=vec,
        payload={"text": text, "path": path, "doc_type": doc_type},
    )


def _store(tmp_path):
    return ChromaStore(persist_dir=tmp_path / "idx")


def test_upsert_and_query_by_similarity(tmp_path):
    store = _store(tmp_path)
    store.upsert("main", [
        _rec("a#0", [1.0, 0.0], "code", "a.py", "alpha"),
        _rec("b#0", [0.0, 1.0], "code", "b.py", "beta"),
    ])
    hits = store.query("main", [1.0, 0.0], k=2)
    assert hits[0].chunk_id == "a#0"           # the most similar first (REQ-017)
    assert hits[0].path == "a.py"


def test_namespaces_are_isolated(tmp_path):
    store = _store(tmp_path)
    store.upsert("corpusA", [_rec("x#0", [1.0, 0.0], "code", "x.py", "x")])
    store.upsert("corpusB", [_rec("y#0", [1.0, 0.0], "code", "y.py", "y")])
    hits = store.query("corpusA", [1.0, 0.0], k=5)
    ids = {h.chunk_id for h in hits}
    assert ids == {"x#0"}                       # no results from the other corpus (REQ-019)


def test_filter_by_doc_type(tmp_path):
    store = _store(tmp_path)
    store.upsert("main", [
        _rec("code#0", [1.0, 0.0], "code", "a.py", "main"),
        _rec("doc#0", [1.0, 0.0], "doc", "a.md", "d"),
    ])
    code_hits = store.query("main", [1.0, 0.0], k=5, doc_type="code")
    assert {h.doc_type.value for h in code_hits} == {"code"}   # type filter (REQ-027)


def test_k_greater_than_available_returns_all(tmp_path):
    store = _store(tmp_path)
    store.upsert("main", [_rec("a#0", [1.0, 0.0], "code", "a.py", "a")])
    hits = store.query("main", [1.0, 0.0], k=10)
    assert len(hits) == 1                        # no error (edge case)


def test_missing_collection_returns_empty_and_not_exists(tmp_path):
    store = _store(tmp_path)
    assert store.query("mai-creata", [1.0, 0.0], k=3) == []   # REQ-028
    assert store.exists("mai-creata") is False


def test_list_collections_names_existing(tmp_path):
    # Port capability for provider detection (feature 010, FR-009).
    store = _store(tmp_path)
    assert store.list_collections() == []
    store.upsert("beta", [_rec("b#0", [1.0, 0.0], "code", "b.py", "b")])
    store.upsert("alfa", [_rec("a#0", [1.0, 0.0], "code", "a.py", "a")])
    assert store.list_collections() == ["alfa", "beta"]       # sorted, deterministic


def test_inmemory_list_collections():
    from tests.fixtures.mocks import InMemoryStore

    store = InMemoryStore()
    assert store.list_collections() == []
    store.upsert("solo", [_rec("s#0", [1.0], "code", "s.py", "s")])
    assert store.list_collections() == ["solo"]


def test_upsert_is_idempotent(tmp_path):
    store = _store(tmp_path)
    rec = _rec("a#0", [1.0, 0.0], "code", "a.py", "a")
    store.upsert("main", [rec])
    store.upsert("main", [rec])                     # same id -> replacement, not duplicate
    hits = store.query("main", [1.0, 0.0], k=10)
    assert len([h for h in hits if h.chunk_id == "a#0"]) == 1


# --- Batch upsert under the backend cap (regression: corpus crossing Chroma's max batch size) ---

class _FakeColl:
    """Records each upsert call size and raises like Chroma when a single call exceeds the cap."""

    def __init__(self, max_batch: int):
        self._max = max_batch
        self.batch_sizes: list[int] = []
        self.ids: list[str] = []

    def upsert(self, ids, embeddings, documents, metadatas):
        if len(ids) > self._max:
            raise ValueError(
                f"Batch size of {len(ids)} is greater than max batch size of {self._max}"
            )
        self.batch_sizes.append(len(ids))
        self.ids.extend(ids)


class _FakeClient:
    def __init__(self, max_batch: int):
        self.coll = _FakeColl(max_batch)
        self.max_batch_size = max_batch

    def get_or_create_collection(self, name, metadata=None):
        return self.coll


def test_upsert_splits_into_batches_under_max(tmp_path):
    client = _FakeClient(max_batch=3)
    store = ChromaStore(client=client)
    records = [_rec(f"r#{i}", [1.0, 0.0], "code", f"f{i}.py", f"t{i}") for i in range(7)]
    store.upsert("main", records)                   # must NOT raise (7 > cap 3)
    assert client.coll.batch_sizes == [3, 3, 1]     # split deterministically
    assert client.coll.ids == [f"r#{i}" for i in range(7)]   # all records, in order


def test_max_batch_size_prefers_client_getter():
    class _C:
        def get_max_batch_size(self):
            return 4242

    assert ChromaStore(client=_C())._max_batch_size() == 4242


def test_max_batch_size_fallback_when_unavailable():
    class _C:
        pass

    assert ChromaStore(client=_C())._max_batch_size() == 5000
