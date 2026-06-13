"""Test US4 — optional reranking as a second stage (FR-010..014, FR-028).

With a fake reranker conforming to the port (structural typing): no extra, no network.
The absence of the extra is simulated by forcing an ImportError
(robust even if `flashrank` is installed).
"""
from __future__ import annotations

import logging
import sys
from dataclasses import replace

import pytest

from sertor_core import composition
from sertor_core.config.settings import Settings
from sertor_core.domain.entities import RetrievalResult
from sertor_core.domain.errors import ConfigError
from sertor_core.engines.hybrid import HybridEngine
from tests.fixtures.mocks import FakeEmbedder, InMemoryLexicalIndex, InMemoryStore

COLL = "rerank-test"


class FakeReranker:
    """Fake cross-encoder: favours texts that CONTAIN the query (deterministic)."""

    model = "fake-cross-encoder"

    def __init__(self) -> None:
        self.seen_pool_sizes: list[int] = []

    def rerank(self, query: str, results: list[RetrievalResult], k: int):
        self.seen_pool_sizes.append(len(results))
        rescored = [
            replace(r, score=float(r.text.lower().count(query.lower().split()[0])))
            for r in results
        ]
        rescored.sort(key=lambda r: (-r.score, r.chunk_id))
        return rescored[:k]


def _populated(emb: FakeEmbedder):
    from sertor_core.domain.entities import EmbeddedChunk, LexicalEntry

    texts = {
        "a.py#0": "alpha beta gamma",
        "b.py#0": "bersaglio bersaglio bersaglio",   # the cross-encoder's preferred hit
        "c.py#0": "bersaglio una volta sola",
    }
    store, lexical = InMemoryStore(), InMemoryLexicalIndex()
    store.upsert(COLL, [
        EmbeddedChunk(cid, emb.embed([t])[0], {"text": t, "path": cid.split("#")[0],
                                               "doc_type": "code"})
        for cid, t in texts.items()
    ])
    lexical.build(COLL, [
        LexicalEntry(cid, t, "code", cid.split("#")[0]) for cid, t in texts.items()
    ])
    return store, lexical


def _engine(settings, reranker=None) -> HybridEngine:
    emb = FakeEmbedder(dim=8)
    store, lexical = _populated(emb)
    return HybridEngine(emb, store, lexical, COLL, settings, reranker=reranker)


def test_enabled_reranker_reorders_fused_pool_with_its_scores(caplog):
    settings = replace(Settings.load(env_file=None), rerank_enabled=True, rerank_pool=3)
    fake = FakeReranker()
    eng = _engine(settings, reranker=fake)
    with caplog.at_level(logging.INFO, logger="sertor_core"):
        hits = eng.query("bersaglio", k=2)
    assert hits[0].chunk_id == "b.py#0"                # reordered by cross-encoder (FR-010)
    assert hits[0].score == 3.0                        # score = reranker score
    assert fake.seen_pool_sizes == [3]                 # pool truncated to rerank_pool (FR-014)
    events = [r for r in caplog.records if getattr(r, "operation", "") == "rerank"]
    assert events, "missing rerank event (FR-028)"
    rec = events[-1]
    assert rec.reranker_model == "fake-cross-encoder"
    assert rec.pool_size == 3 and rec.top_k == 2 and hasattr(rec, "elapsed_ms")
    hybrid_events = [r for r in caplog.records if getattr(r, "operation", "") == "hybrid_query"]
    assert hybrid_events[-1].rerank_applied is True


def test_disabled_reranker_returns_pure_rrf_without_event(caplog):
    settings = Settings.load(env_file=None)            # rerank_enabled=False by default
    fake = FakeReranker()
    eng = _engine(settings, reranker=fake)
    with caplog.at_level(logging.INFO, logger="sertor_core"):
        hits = eng.query("bersaglio", k=2)
    assert hits and fake.seen_pool_sizes == []         # never invoked (FR-013)
    assert not [r for r in caplog.records if getattr(r, "operation", "") == "rerank"]
    no_rerank = _engine(settings)                      # without reranker: identical
    assert [h.chunk_id for h in no_rerank.query("bersaglio", k=2)] == [h.chunk_id for h in hits]


def test_rerank_configured_without_extra_raises_actionable_error(tmp_path, monkeypatch):
    # Simulate the extra being absent even if installed: importing `flashrank` → ImportError.
    monkeypatch.setitem(sys.modules, "flashrank", None)
    settings = Settings(index_dir=tmp_path, corpus="x", rerank_enabled=True)
    with pytest.raises(ConfigError) as exc:
        composition.build_engine(settings)
    assert "sertor-core[rerank]" in str(exc.value)     # actionable (FR-012), never silent fallback


def test_engine_importable_without_extra(monkeypatch):
    # FR-011: the engine module does not import flashrank; only the adapter does, and lazily.
    monkeypatch.setitem(sys.modules, "flashrank", None)
    import importlib

    import sertor_core.engines.hybrid as hybrid_module
    importlib.reload(hybrid_module)                    # no ImportError
    assert hasattr(hybrid_module, "HybridEngine")
