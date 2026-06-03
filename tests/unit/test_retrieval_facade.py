"""Test US5 — facade di retrieval riusabile come libreria (REQ-023..029)."""
from __future__ import annotations

import logging

import pytest

from sertor_core.domain.entities import EmbeddedChunk
from sertor_core.domain.errors import EmbeddingError
from sertor_core.services.retrieval import RetrievalFacade
from tests.fixtures.mocks import FakeEmbedder, InMemoryStore

COLL = "test-collection"


def _populated_store(embedder: FakeEmbedder) -> InMemoryStore:
    store = InMemoryStore()
    items = [
        ("a.py#0", "code", "a.py", "def validate(x): ..."),
        ("b.md#0", "doc", "b.md", "come configurare il backend"),
        ("c.py#0", "code", "c.py", "class Server: ..."),
    ]
    records = [
        EmbeddedChunk(
            chunk_id=cid,
            vector=embedder.embed([text])[0],
            payload={"text": text, "path": path, "doc_type": dt},
        )
        for cid, dt, path, text in items
    ]
    store.upsert(COLL, records)
    return store


def test_results_carry_required_fields():
    emb = FakeEmbedder(dim=8)
    facade = RetrievalFacade(emb, _populated_store(emb), COLL, default_k=5)
    hits = facade.search_combined("validate")
    assert hits
    h = hits[0]
    assert h.text and h.path and h.chunk_id           # REQ-025
    assert h.doc_type is not None and isinstance(h.score, float)


def test_filter_by_type():
    emb = FakeEmbedder(dim=8)
    facade = RetrievalFacade(emb, _populated_store(emb), COLL, default_k=5)
    assert {h.doc_type.value for h in facade.search_code("x")} == {"code"}   # REQ-027
    assert {h.doc_type.value for h in facade.search_docs("x")} == {"doc"}


def test_k_default_and_override():
    emb = FakeEmbedder(dim=8)
    facade = RetrievalFacade(emb, _populated_store(emb), COLL, default_k=1)
    assert len(facade.search_combined("x")) == 1            # default_k
    assert len(facade.search_combined("x", k=10)) == 3      # k>disponibili -> tutti (REQ-026)


def test_empty_index_returns_empty_with_warning(caplog):
    emb = FakeEmbedder(dim=8)
    facade = RetrievalFacade(emb, InMemoryStore(), "vuota", default_k=5)
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        out = facade.search_combined("qualsiasi")
    assert out == []                                       # REQ-028: vuoto, non eccezione
    assert any("no_index" in r.message for r in caplog.records)
    assert emb.calls == 0                                  # non interroga l'embedder se vuoto


def test_errors_propagate_not_silently_empty():
    class BrokenEmbedder(FakeEmbedder):
        def embed(self, texts):
            raise EmbeddingError("down", provider="fake", reason="x", retriable=True)

    emb = FakeEmbedder(dim=8)
    store = _populated_store(emb)
    facade = RetrievalFacade(BrokenEmbedder(dim=8), store, COLL, default_k=5)
    with pytest.raises(EmbeddingError):                    # REQ-012: errore esplicito
        facade.search_combined("x")


def test_usable_as_imported_library():
    # Importabile e usabile senza toccare store/embeddings concreti (REQ-029).
    from sertor_core import RetrievalResult, build_facade  # noqa: F401

    assert callable(build_facade)
