"""STRICT precision@5 test via facade — the consumer surface (REQ-052, SC-003).

Former `xfail` (US5 of FEAT-002): completed by FEAT-004. Same ground-truth and same index as
the quality test, but measured through the `RetrievalFacade` (with and without hybrid strategy):
verifies that the improvement reaches consumers via the stable surface, not just the raw engine.
No network.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sertor_core.adapters.lexical.bm25 import Bm25LexicalIndex
from sertor_core.config.settings import Settings
from sertor_core.engines.hybrid import HybridEngine
from sertor_core.services.indexing import IndexingService
from sertor_core.services.retrieval import RetrievalFacade
from tests.fixtures.ground_truth import relative_to
from tests.fixtures.mocks import FakeEmbedder, InMemoryStore

pytestmark = pytest.mark.integration

_CORPUS_ROOT = Path(__file__).resolve().parents[2] / "src" / "sertor_core"
_COLL = "precision-gt"
_GT = relative_to("src/sertor_core")


@pytest.fixture(scope="module")
def facades(tmp_path_factory):
    """Two facades on the same index: current dense path vs injected hybrid strategy."""
    tmp = tmp_path_factory.mktemp("precision-index")
    settings = Settings(index_dir=tmp, corpus="precision")
    emb = FakeEmbedder(dim=8)
    store = InMemoryStore()
    lexical = Bm25LexicalIndex(tmp)
    IndexingService(emb, store, _COLL, settings, lexical=lexical).index(
        _CORPUS_ROOT, rebuild=True
    )
    dense = RetrievalFacade(emb, store, _COLL, default_k=5)
    hybrid = RetrievalFacade(
        emb, store, _COLL, default_k=5,
        retriever=HybridEngine(emb, store, lexical, _COLL, settings),
    )
    return dense, hybrid


def _precision_at_5(facade: RetrievalFacade) -> float:
    hits_ok = 0
    for query, expected, _ in _GT:
        paths = {h.path for h in facade.search_combined(query, k=5).flatten()}
        hits_ok += 1 if paths & set(expected) else 0
    return hits_ok / len(_GT)


def test_hybrid_facade_precision_meets_dense_baseline(facades):
    dense, hybrid = facades
    p_dense, p_hybrid = _precision_at_5(dense), _precision_at_5(hybrid)
    print(f"precision@5 — dense: {p_dense:.2f} · hybrid: {p_hybrid:.2f} ({len(_GT)} query)")
    assert p_hybrid >= p_dense                          # REQ-052: never worse
    assert p_hybrid >= 0.5                              # sanity: hybrid resolves at least half
