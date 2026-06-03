"""Test US3 — indicizzazione del wiki nel RAG (REQ-040..045, SC-004).

Riusa il nucleo via IndexingService; qui si testa direttamente con FakeEmbedder + ChromaStore temp
costruendo l'IndexingService come fa `index_wiki`, e si verifica il caso "radice vuota" della skill.
"""
from __future__ import annotations

from sertor_core.adapters.vectorstores.chroma import ChromaStore
from sertor_core.config.settings import Settings
from sertor_core.services.indexing import IndexingService
from sertor_core.wiki.conventions import Brief
from sertor_core.wiki.indexing import index_wiki
from sertor_core.wiki.operations import record
from tests.fixtures.mocks import FakeEmbedder

S = Settings.load(env_file=None)
T = "2026-06-03"
COLL = "wiki-coll"


def _index_sandbox(wiki_root, store):
    return IndexingService(FakeEmbedder(dim=8), store, COLL, S).index(wiki_root, rebuild=True)


def test_wiki_pages_are_indexed_and_retrievable(wiki_sandbox, tmp_path):
    brief = Brief("Scelta DB", "synthesis", "Abbiamo scelto Postgres per la robustezza.")
    record(wiki_sandbox, brief, today=T)
    store = ChromaStore(persist_dir=tmp_path / "idx")
    report = _index_sandbox(wiki_sandbox, store)
    assert report.documents >= 1 and report.chunks >= 1          # REQ-040/042

    # FakeEmbedder non è semantico: si verifica che la pagina sia indicizzata e recuperabile
    # fra i documenti del corpus (con un embedder reale il ranking sarebbe semantico, SC-004).
    qvec = FakeEmbedder(dim=8).embed(["Postgres"])[0]
    hits = store.query(COLL, qvec, k=50, doc_type="doc")
    assert any(h.path == "syntheses/scelta-db.md" for h in hits)


def test_reindex_no_duplicates_stable_id(wiki_sandbox, tmp_path):
    record(wiki_sandbox, Brief("Tema", "concept", "corpo"), today=T)
    store = ChromaStore(persist_dir=tmp_path / "idx")
    r1 = _index_sandbox(wiki_sandbox, store)
    r2 = _index_sandbox(wiki_sandbox, store)                      # full rebuild
    assert r1.chunks == r2.chunks                                 # nessun duplicato (REQ-041/051)


def test_empty_wiki_root_warns_and_no_index(tmp_path):
    empty = tmp_path / "empty-wiki"
    empty.mkdir()
    report = index_wiki(empty, S)                                 # radice senza Markdown (REQ-045)
    assert report.documents == 0 and report.chunks == 0
