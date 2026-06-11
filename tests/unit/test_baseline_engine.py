"""Test US1/US2/US5 — BaselineEngine: index, query, errori, modalità (REQ-001..014)."""
from __future__ import annotations

import pytest

from sertor_core.adapters.embeddings.ollama import OllamaEmbedder
from sertor_core.adapters.vectorstores.chroma import ChromaStore
from sertor_core.composition import build_baseline_engine
from sertor_core.config.settings import Settings
from sertor_core.domain.entities import EmbeddedChunk
from sertor_core.domain.errors import EmbeddingError, IndexNotFoundError
from sertor_core.engines.baseline import BaselineEngine
from tests.fixtures.mocks import FakeEmbedder, InMemoryStore

S = Settings.load(env_file=None)
COLL = "baseline-coll"


class _Boom(FakeEmbedder):
    """Embedder che simula un provider non disponibile."""

    def embed(self, texts):
        raise EmbeddingError("down", provider="fake", reason="net", retriable=True)


# --------------------------------------------------------------------- US1: index
def test_index_produces_report(sample_repo):
    engine = BaselineEngine(FakeEmbedder(dim=8), InMemoryStore(), COLL, S)
    report = engine.index(sample_repo)
    assert report.chunks >= report.documents >= 4    # py, js, go, md, ps1 (REQ-001/003)
    assert report.embedding_dim == 8


def test_index_aborts_without_corrupting_existing_index(sample_repo):
    store = InMemoryStore()
    old = EmbeddedChunk("old#0", [0.0] * 8, {"text": "old", "path": "old.py", "doc_type": "code"})
    store.upsert(COLL, [old])
    engine = BaselineEngine(_Boom(dim=8), store, COLL, S)
    with pytest.raises(EmbeddingError):
        engine.index(sample_repo)
    # provider down durante l'embed (prima del reset): indice preesistente intatto (REQ-004)
    assert store.exists(COLL)
    assert "old#0" in store._data[COLL]


# --------------------------------------------------------------------- US2: query
def _indexed_engine(sample_repo):
    engine = BaselineEngine(FakeEmbedder(dim=8), InMemoryStore(), COLL, S)
    engine.index(sample_repo)
    return engine


def test_query_returns_results_with_fields(sample_repo):
    engine = _indexed_engine(sample_repo)
    hits = engine.query("calculator", k=5)
    assert hits
    h = hits[0]
    assert h.path and h.chunk_id and isinstance(h.score, float)   # REQ-006/007
    assert h.doc_type is not None


def test_query_k_default_and_override(sample_repo):
    engine = BaselineEngine(FakeEmbedder(dim=8), InMemoryStore(), COLL, S, default_k=2)
    engine.index(sample_repo)
    assert len(engine.query("x")) == 2              # default_k (REQ-008)
    assert len(engine.query("x", k=1000)) >= 4      # k>disponibili -> tutti


def test_query_missing_index_raises(sample_repo):
    engine = BaselineEngine(FakeEmbedder(dim=8), InMemoryStore(), "mai-creata", S)
    with pytest.raises(IndexNotFoundError):          # REQ-009: errore esplicito, non []
        engine.query("x")


# -------------------------------------------- FEAT-011: ensure_index (check strict estratto, D6)
def test_ensure_index_missing_raises():
    engine = BaselineEngine(FakeEmbedder(dim=8), InMemoryStore(), "mai-creata", S)
    with pytest.raises(IndexNotFoundError):          # via strict riusabile dalla CLI (FR-012)
        engine.ensure_index()


def test_ensure_index_populated_returns_none(sample_repo):
    engine = _indexed_engine(sample_repo)
    assert engine.ensure_index() is None             # indice presente -> nessuna eccezione


def test_query_delegates_to_ensure_index(sample_repo, monkeypatch):
    # query() non deve duplicare il check: deve invocare ensure_index() (Boy Scout Rule, fix F1)
    engine = _indexed_engine(sample_repo)
    calls = {"n": 0}
    monkeypatch.setattr(engine, "ensure_index", lambda: calls.__setitem__("n", calls["n"] + 1))
    engine.query("x")
    assert calls["n"] == 1


def test_query_provider_down_raises(sample_repo):
    store = InMemoryStore()
    BaselineEngine(FakeEmbedder(dim=8), store, COLL, S).index(sample_repo)  # popola l'indice
    engine = BaselineEngine(_Boom(dim=8), store, COLL, S)
    with pytest.raises(EmbeddingError):              # REQ-010
        engine.query("x")


# --------------------------------------------------------------------- US5: modalità/config
def test_mode_name_is_stable():
    assert BaselineEngine.name == "baseline"         # REQ-013


def test_build_baseline_engine_local(monkeypatch, tmp_path):
    monkeypatch.setenv("RAG_BACKEND", "local")
    monkeypatch.setenv("SERTOR_INDEX_DIR", str(tmp_path / "idx"))
    engine = build_baseline_engine(Settings.load(env_file=None))
    assert engine.name == "baseline"
    assert isinstance(engine._embedder, OllamaEmbedder)   # provider locale via config (REQ-012)
    assert isinstance(engine._store, ChromaStore)
