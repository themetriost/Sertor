"""Test US1/US2 — HybridEngine: fusione dense+lessicale, via strict, degradazione (FR-004..016).

Tutto con mock (FakeEmbedder, InMemoryStore, InMemoryLexicalIndex), senza rete (NFR-03/LSC-5).
"""
from __future__ import annotations

import logging

import pytest

from sertor_core.config.settings import Settings
from sertor_core.domain.entities import EmbeddedChunk, RetrievalResult
from sertor_core.domain.errors import IndexNotFoundError
from sertor_core.engines.hybrid import HybridEngine
from tests.fixtures.mocks import FakeEmbedder, InMemoryLexicalIndex, InMemoryStore

COLL = "hybrid-test"


def _payload(text: str, path: str, doc_type: str = "code") -> dict:
    return {"text": text, "path": path, "doc_type": doc_type}


def _populated(emb: FakeEmbedder) -> tuple[InMemoryStore, InMemoryLexicalIndex]:
    """Store + lessicale con 3 chunk: solo `ports.py#0` contiene il simbolo raro."""
    from sertor_core.domain.entities import LexicalEntry

    texts = {
        "ports.py#0": ("class EmbeddingProvider il provider di embeddings", "ports.py"),
        "retrieval.py#0": ("la facade fonde i risultati delle collezioni", "retrieval.py"),
        "indexing.py#0": ("la pipeline ingerisce e produce chunk", "indexing.py"),
    }
    store = InMemoryStore()
    store.upsert(COLL, [
        EmbeddedChunk(cid, emb.embed([t])[0], _payload(t, p))
        for cid, (t, p) in texts.items()
    ])
    lexical = InMemoryLexicalIndex()
    lexical.build(COLL, [
        LexicalEntry(cid, t, "code", p) for cid, (t, p) in texts.items()
    ])
    return store, lexical


def _engine(store=None, lexical=None, emb=None, settings=None) -> HybridEngine:
    emb = emb or FakeEmbedder(dim=8)
    settings = settings or Settings.load(env_file=None)
    if store is None:
        store, lexical = _populated(emb)
    return HybridEngine(emb, store, lexical, COLL, settings)


# --- US1: fusione --------------------------------------------------------------------------------

def test_engine_has_baseline_compatible_interface():
    eng = _engine()
    assert eng.name == "hybrid"                      # FR-019: stessa interfaccia del baseline
    assert eng.provider.startswith("fake:")
    assert callable(eng.index) and callable(eng.query) and callable(eng.ensure_index)


def test_exact_symbol_query_surfaces_lexical_match_on_top():
    # Il simbolo raro vive in UN chunk: la via lessicale lo mette rank 1; con la fusione RRF
    # il suo score (lessicale + densa) batte ogni candidato di sola via densa (FR-006).
    hits = _engine().query("EmbeddingProvider", k=3)
    assert hits and hits[0].chunk_id == "ports.py#0"
    assert all(isinstance(h, RetrievalResult) for h in hits)   # FR-009: entità invariata


def test_results_are_deterministic():
    eng = _engine()
    first = [h.chunk_id for h in eng.query("provider di embeddings", k=3)]
    second = [h.chunk_id for h in eng.query("provider di embeddings", k=3)]
    assert first == second                                     # FR-008


def test_query_without_any_index_raises_strict_error():
    eng = _engine(store=InMemoryStore(), lexical=InMemoryLexicalIndex())
    with pytest.raises(IndexNotFoundError):
        eng.query("qualunque")                                 # FR-004: corpus mai indicizzato


def test_index_builds_vector_and_lexical_together(tmp_path):
    # REQ-001/002/003: stesso insieme di chunk nelle due vie, in un solo passaggio.
    (tmp_path / "app.py").write_text("def collection_name():\n    return 'x'\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Guida\n\nIl progetto demo.\n", encoding="utf-8")
    emb = FakeEmbedder(dim=8)
    store, lexical = InMemoryStore(), InMemoryLexicalIndex()
    eng = HybridEngine(emb, store, lexical, COLL, Settings.load(env_file=None))
    report = eng.index(tmp_path)
    assert report.chunks > 0
    vector_ids = set(store._data[COLL])
    lexical_ids = {e.chunk_id for e in lexical._data[COLL]}
    assert vector_ids == lexical_ids                           # specchio (FR-002)


def test_hybrid_query_log_event_has_contract_fields(caplog):
    eng = _engine()
    with caplog.at_level(logging.INFO, logger="sertor_core"):
        eng.query("EmbeddingProvider", k=3)
    events = [r for r in caplog.records if getattr(r, "operation", "") == "hybrid_query"]
    assert events, "manca l'evento hybrid_query (FR-027)"
    rec = events[-1]
    for field in ("engine", "provider", "collection", "lexical_hits", "dense_hits",
                  "fused_k", "rerank_applied", "elapsed_ms"):
        assert hasattr(rec, field), f"campo mancante nel contratto log-events: {field}"
    assert rec.engine == "hybrid" and rec.rerank_applied is False
    assert rec.lexical_hits >= 1 and rec.dense_hits >= 1


# --- US2: degradazione REQ-034 (FR-016) -----------------------------------------------------------

def test_missing_lexical_index_degrades_to_dense_with_warning(caplog):
    # Corpus pre-ibrido: vettoriale presente, sidecar assente → dense-only + WARNING, MAI errore.
    emb = FakeEmbedder(dim=8)
    store, _ = _populated(emb)
    eng = HybridEngine(emb, store, InMemoryLexicalIndex(), COLL, Settings.load(env_file=None))
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        hits = eng.query("provider di embeddings", k=3)
    assert hits                                                # la query NON fallisce
    warnings = [r for r in caplog.records
                if getattr(r, "operation", "") == "lexical_index_missing"]
    assert warnings and warnings[-1].collection == COLL
    assert "re-index" in str(warnings[-1].hint)                # hint azionabile (REQ-034)


def test_degraded_results_equal_dense_only_baseline():
    # In degradazione i risultati sono equivalenti al retrieval vettoriale puro (FR-016/031).
    emb = FakeEmbedder(dim=8)
    store, _ = _populated(emb)
    eng = HybridEngine(emb, store, InMemoryLexicalIndex(), COLL, Settings.load(env_file=None))
    degraded = [h.chunk_id for h in eng.query("la facade fonde", k=3)]
    vector = emb.embed(["la facade fonde"])[0]
    dense = [r.chunk_id for r in store.query(COLL, vector, 3, "both")]
    assert degraded == dense
