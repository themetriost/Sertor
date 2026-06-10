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


# --- Fan-out multi-collezione della ricerca combinata (feature 010, FR-001..009) ---

WIKI_COLL = "wiki__fake_8"


def _two_collection_store(emb: FakeEmbedder) -> InMemoryStore:
    """Primaria (codice) + collezione wiki, popolate con contenuti distinti."""
    store = _populated_store(emb)
    wiki_items = [
        ("concepts/retrieval.md#0", "doc", "concepts/retrieval.md", "come configurare il backend"),
        ("tech/chroma.md#0", "doc", "tech/chroma.md", "persistenza locale degli indici"),
    ]
    store.upsert(WIKI_COLL, [
        EmbeddedChunk(
            chunk_id=cid,
            vector=emb.embed([text])[0],
            payload={"text": text, "path": path, "doc_type": dt},
        )
        for cid, dt, path, text in wiki_items
    ])
    return store


def _multi_facade(emb: FakeEmbedder, store: InMemoryStore, k: int = 5) -> RetrievalFacade:
    return RetrievalFacade(emb, store, COLL, default_k=k,
                           extra_collections={"wiki": WIKI_COLL})


def test_combined_fuses_results_from_both_collections():
    emb = FakeEmbedder(dim=8)
    facade = _multi_facade(emb, _two_collection_store(emb))
    hits = facade.search_combined("come configurare il backend")
    sources = {h.chunk_id.split("#")[0] for h in hits}
    assert any(s.endswith(".md") and "/" in s for s in sources)   # hit dal wiki (FR-001)
    assert any(s in ("a.py", "b.md", "c.py") for s in sources)    # hit dalla primaria
    assert len(hits) <= 5                                          # ≤ k complessivi (FR-002)
    scores = [h.score for h in hits]
    assert scores == sorted(scores, reverse=True)                  # ordinati per pertinenza


def test_combined_merge_is_deterministic_on_ties():
    # A parità di score l'ordinamento è stabile per chunk_id (FR-003, Principio VI).
    emb = FakeEmbedder(dim=8)
    store = InMemoryStore()
    same_text = "identico"
    for coll, cid in ((COLL, "z.py#0"), (WIKI_COLL, "a.md#0")):
        store.upsert(coll, [EmbeddedChunk(
            chunk_id=cid,
            vector=emb.embed([same_text])[0],
            payload={"text": same_text, "path": cid.split("#")[0], "doc_type": "code"},
        )])
    facade = _multi_facade(emb, store)
    first = facade.search_combined(same_text)
    assert [h.chunk_id for h in first] == ["a.md#0", "z.py#0"]    # tie-break per chunk_id
    assert [h.chunk_id for h in facade.search_combined(same_text)] == \
        [h.chunk_id for h in first]                                # output stabile


def test_combined_no_quota_when_relevance_is_concentrated():
    # Se i migliori k stanno tutti in una collezione, nessuna quota minima (edge case).
    emb = FakeEmbedder(dim=8)
    store = _populated_store(emb)   # solo primaria popolata
    store.upsert(WIKI_COLL, [EmbeddedChunk(
        chunk_id="lontano.md#0",
        vector=[0.0] * 8,           # ortogonale: pertinenza nulla
        payload={"text": "x", "path": "lontano.md", "doc_type": "doc"},
    )])
    facade = _multi_facade(emb, store, k=3)
    hits = facade.search_combined("def validate(x): ...", k=3)
    assert [h.chunk_id for h in hits][0] == "a.py#0"
    assert "lontano.md#0" not in [h.chunk_id for h in hits][:1]


def test_combined_degrades_when_extra_corpus_never_indexed(caplog):
    # Corpus extra mai indicizzato → warning + risultati della sola primaria (FR-004).
    emb = FakeEmbedder(dim=8)
    facade = _multi_facade(emb, _populated_store(emb))
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        hits = facade.search_combined("validate")
    assert hits                                                    # la primaria risponde
    assert any("no_index" in r.message for r in caplog.records)


def test_combined_all_collections_absent_returns_empty(caplog):
    emb = FakeEmbedder(dim=8)
    facade = RetrievalFacade(emb, InMemoryStore(), COLL, default_k=5,
                             extra_collections={"wiki": WIKI_COLL})
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        out = facade.search_combined("qualsiasi")
    assert out == []                                               # FR-005
    assert any("no_index" in r.message for r in caplog.records)
    assert emb.calls == 0                                          # niente embed a vuoto


def test_combined_raises_on_provider_mismatch():
    # Corpus wiki indicizzato con un ALTRO provider → errore esplicito, mai fusione (FR-009).
    from sertor_core.domain.errors import ProviderMismatchError

    emb = FakeEmbedder(dim=8)
    store = _populated_store(emb)
    store.upsert("wiki__altro_provider", [EmbeddedChunk(
        chunk_id="p.md#0", vector=emb.embed(["x"])[0],
        payload={"text": "x", "path": "p.md", "doc_type": "doc"},
    )])
    facade = _multi_facade(emb, store)
    with pytest.raises(ProviderMismatchError) as exc:
        facade.search_combined("x")
    assert "wiki" in str(exc.value) and "wiki__altro_provider" in str(exc.value)


def test_combined_without_extra_collections_unchanged():
    # Regressione: senza corpora extra il percorso è quello storico (FR-006).
    emb = FakeEmbedder(dim=8)
    store = _populated_store(emb)
    legacy = RetrievalFacade(emb, store, COLL, default_k=5)
    multi_empty = RetrievalFacade(emb, store, COLL, default_k=5, extra_collections={})
    q = "come configurare il backend"
    assert [h.chunk_id for h in legacy.search_combined(q)] == \
        [h.chunk_id for h in multi_empty.search_combined(q)]


def test_code_and_docs_do_not_fan_out():
    # FR-006bis: il fan-out è solo della ricerca combinata.
    emb = FakeEmbedder(dim=8)
    facade = _multi_facade(emb, _two_collection_store(emb))
    assert all(not h.path.startswith(("concepts/", "tech/"))
               for h in facade.search_docs("come configurare il backend"))
