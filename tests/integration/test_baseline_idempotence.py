"""Test US3 — idempotenza del re-index del motore baseline (SC-003, REQ-002)."""
from __future__ import annotations

from sertor_core.adapters.vectorstores.chroma import ChromaStore
from sertor_core.config.settings import Settings
from sertor_core.engines.baseline import BaselineEngine
from tests.fixtures.mocks import FakeEmbedder

S = Settings.load(env_file=None)
COLL = "idem-baseline"


def test_reindex_stable_chunk_count_and_results(sample_repo, tmp_path):
    store = ChromaStore(persist_dir=tmp_path / "idx")
    engine = BaselineEngine(FakeEmbedder(dim=8), store, COLL, S)

    r1 = engine.index(sample_repo)
    hits1 = [h.chunk_id for h in engine.query("calculator", k=10)]
    r2 = engine.index(sample_repo)                       # rebuild-from-scratch
    hits2 = [h.chunk_id for h in engine.query("calculator", k=10)]

    assert r1.chunks == r2.chunks                        # stesso n. di chunk (SC-003)
    assert hits1 == hits2                                 # stessi risultati alle stesse query


def test_rebuild_drops_stale_chunks(sample_repo, tmp_path):
    store = ChromaStore(persist_dir=tmp_path / "idx")
    engine = BaselineEngine(FakeEmbedder(dim=8), store, COLL, S)
    engine.index(sample_repo)

    # rimuove un file: dopo il rebuild i suoi chunk non devono più comparire (REQ-002)
    (sample_repo / "web" / "server.js").unlink()
    engine.index(sample_repo)
    paths = {h.path for h in engine.query("server", k=50)}
    assert "web/server.js" not in paths
