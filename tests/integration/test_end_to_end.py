"""Polish — end-to-end quickstart validation (T040): index → search (REQ-023..029).

Full offline pipeline: mini-repo ingestion → chunking → embeddings (FakeEmbedder) →
store (Chroma on temp) → retrieval facade. Verifies the flows in `quickstart.md`.
"""
from __future__ import annotations

from sertor_core.adapters.vectorstores.chroma import ChromaStore
from sertor_core.config.settings import Settings
from sertor_core.services.indexing import IndexingService
from sertor_core.services.retrieval import RetrievalFacade, merge_fused
from tests.fixtures.mocks import FakeEmbedder

S = Settings.load(env_file=None)
COLL = "e2e-collection"


def _index_and_facade(sample_repo, tmp_path):
    store = ChromaStore(persist_dir=tmp_path / "e2e-index")
    report = IndexingService(FakeEmbedder(dim=8), store, COLL, S).index(sample_repo)
    facade = RetrievalFacade(FakeEmbedder(dim=8), store, COLL, default_k=5)
    return report, facade


def test_index_reports_documents_and_chunks(sample_repo, tmp_path):
    report, _ = _index_and_facade(sample_repo, tmp_path)
    assert report.documents >= 4          # py, js, go, md, ps1 (excluding .venv/secret.key)
    assert report.chunks >= report.documents
    assert report.embedding_dim == 8


def test_search_returns_results_with_required_fields(sample_repo, tmp_path):
    _, facade = _index_and_facade(sample_repo, tmp_path)
    for hits in (
        facade.search_code("calculator"),
        facade.search_docs("installazione"),
        merge_fused(*facade.search_combined("server")),  # 070: combined returns (docs, code)
    ):
        assert hits
        h = hits[0]
        assert h.text and h.path and h.chunk_id
        assert isinstance(h.score, float)


def test_search_filters_respect_doc_type(sample_repo, tmp_path):
    _, facade = _index_and_facade(sample_repo, tmp_path)
    assert {h.doc_type.value for h in facade.search_code("x", k=20)} == {"code"}
    assert {h.doc_type.value for h in facade.search_docs("x", k=20)} == {"doc"}


def test_empty_collection_returns_empty(tmp_path):
    store = ChromaStore(persist_dir=tmp_path / "empty-index")
    facade = RetrievalFacade(FakeEmbedder(dim=8), store, "vuota", default_k=5)
    assert merge_fused(*facade.search_combined("qualsiasi")) == []  # REQ-028 (070: (docs, code))
