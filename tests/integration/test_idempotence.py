"""Polish — idempotenza del full re-index (SC-005, NFR-02, REQ-010).

Rieseguire l'indicizzazione su un corpus invariato produce lo stesso insieme di chunk id, senza
duplicati. Test offline con `FakeEmbedder` + `InMemoryStore` (introspezione degli id).
"""
from __future__ import annotations

from sertor_core.config.settings import Settings
from sertor_core.services.indexing import IndexingService
from tests.fixtures.mocks import FakeEmbedder, InMemoryStore

COLL = "idem-collection"
S = Settings.load(env_file=None)


def _index_once(store: InMemoryStore, root) -> set[str]:
    svc = IndexingService(FakeEmbedder(dim=8), store, COLL, S)
    svc.index(root)
    return set(store._data.get(COLL, {}).keys())


def test_reindex_same_corpus_yields_same_chunk_ids(sample_repo):
    store_a = InMemoryStore()
    store_b = InMemoryStore()
    ids_first = _index_once(store_a, sample_repo)
    ids_second = _index_once(store_b, sample_repo)
    assert ids_first == ids_second           # stesso insieme di id (SC-005)
    assert ids_first                          # non vuoto


def test_reindex_into_same_store_has_no_duplicates(sample_repo):
    store = InMemoryStore()
    ids_run1 = _index_once(store, sample_repo)
    ids_run2 = _index_once(store, sample_repo)
    assert ids_run1 == ids_run2
    # upsert sugli stessi id sostituisce: il numero di record non cresce (NFR-02)
    assert len(store._data[COLL]) == len(ids_run1)
