"""Test US4 — vector store Chroma (REQ-017/019/027/028)."""
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
    assert hits[0].chunk_id == "a#0"           # il più simile per primo (REQ-017)
    assert hits[0].path == "a.py"


def test_namespaces_are_isolated(tmp_path):
    store = _store(tmp_path)
    store.upsert("corpusA", [_rec("x#0", [1.0, 0.0], "code", "x.py", "x")])
    store.upsert("corpusB", [_rec("y#0", [1.0, 0.0], "code", "y.py", "y")])
    hits = store.query("corpusA", [1.0, 0.0], k=5)
    ids = {h.chunk_id for h in hits}
    assert ids == {"x#0"}                       # nessun risultato dall'altro corpus (REQ-019)


def test_filter_by_doc_type(tmp_path):
    store = _store(tmp_path)
    store.upsert("main", [
        _rec("code#0", [1.0, 0.0], "code", "a.py", "main"),
        _rec("doc#0", [1.0, 0.0], "doc", "a.md", "d"),
    ])
    code_hits = store.query("main", [1.0, 0.0], k=5, doc_type="code")
    assert {h.doc_type.value for h in code_hits} == {"code"}   # filtro tipo (REQ-027)


def test_k_greater_than_available_returns_all(tmp_path):
    store = _store(tmp_path)
    store.upsert("main", [_rec("a#0", [1.0, 0.0], "code", "a.py", "a")])
    hits = store.query("main", [1.0, 0.0], k=10)
    assert len(hits) == 1                        # nessun errore (edge case)


def test_missing_collection_returns_empty_and_not_exists(tmp_path):
    store = _store(tmp_path)
    assert store.query("mai-creata", [1.0, 0.0], k=3) == []   # REQ-028
    assert store.exists("mai-creata") is False


def test_list_collections_names_existing(tmp_path):
    # Capacità di porta per il rilevamento provider (feature 010, FR-009).
    store = _store(tmp_path)
    assert store.list_collections() == []
    store.upsert("beta", [_rec("b#0", [1.0, 0.0], "code", "b.py", "b")])
    store.upsert("alfa", [_rec("a#0", [1.0, 0.0], "code", "a.py", "a")])
    assert store.list_collections() == ["alfa", "beta"]       # ordinato, deterministico


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
    store.upsert("main", [rec])                     # stesso id -> sostituzione, non duplicato
    hits = store.query("main", [1.0, 0.0], k=10)
    assert len([h for h in hits if h.chunk_id == "a#0"]) == 1
