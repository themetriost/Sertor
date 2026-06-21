"""Test US5 — retrieval facade reusable as a library (REQ-023..029).

`search_combined` returns the tuple `(docs, code)` (070): the two labelled flows, each with its own
top-k (separate budget), unpackable as `docs, code = facade.search_combined(q)`. Tests unpack the
tuple for the per-flow contract and use the free `merge_fused` for the single-list view.
"""
from __future__ import annotations

import logging

import pytest

from sertor_core.domain.entities import DocType, EmbeddedChunk
from sertor_core.domain.errors import EmbeddingError
from sertor_core.services.retrieval import RetrievalFacade, merge_fused
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


def test_combined_returns_tuple_of_two_flows():
    emb = FakeEmbedder(dim=8)
    facade = RetrievalFacade(emb, _populated_store(emb), COLL, default_k=5)
    result = facade.search_combined("validate")
    assert isinstance(result, tuple) and len(result) == 2
    docs, code = result
    assert all(r.doc_type is DocType.DOC for r in docs)    # 070: docs flow is DOC only
    assert all(r.doc_type is DocType.CODE for r in code)   # 070: code flow is CODE only


def test_results_carry_required_fields():
    emb = FakeEmbedder(dim=8)
    facade = RetrievalFacade(emb, _populated_store(emb), COLL, default_k=5)
    docs, code = facade.search_combined("validate")
    hits = merge_fused(docs, code)
    assert hits
    h = hits[0]
    assert h.text and h.path and h.chunk_id           # REQ-025
    assert h.doc_type is not None and isinstance(h.score, float)


def test_combined_budget_is_separate_code_not_starved():
    # 070/SC-001: even when docs would dominate a shared top-k, the code flow has its own budget,
    # so it is NOT empty (the 069 root cause does not re-appear).
    emb = FakeEmbedder(dim=8)
    facade = RetrievalFacade(emb, _populated_store(emb), COLL, default_k=1)
    docs, code = facade.search_combined("come configurare il backend")
    assert docs            # a doc surfaces
    assert code            # AND code is present (separate budget), not starved


def test_filter_by_type():
    emb = FakeEmbedder(dim=8)
    facade = RetrievalFacade(emb, _populated_store(emb), COLL, default_k=5)
    assert {h.doc_type.value for h in facade.search_code("x")} == {"code"}   # REQ-027
    assert {h.doc_type.value for h in facade.search_docs("x")} == {"doc"}


def test_code_and_docs_unchanged_return_lists():
    # SC-002: mono-type surfaces still return list[RetrievalResult] (invariant).
    emb = FakeEmbedder(dim=8)
    facade = RetrievalFacade(emb, _populated_store(emb), COLL, default_k=5)
    assert isinstance(facade.search_code("x"), list)
    assert isinstance(facade.search_docs("x"), list)


def test_combined_without_code_in_index_yields_empty_code_flow():
    # Edge case: a corpus with no code → code=[], docs populated; the pair is still structured.
    emb = FakeEmbedder(dim=8)
    store = InMemoryStore()
    store.upsert(COLL, [EmbeddedChunk(
        chunk_id="only.md#0", vector=emb.embed(["solo documentazione"])[0],
        payload={"text": "solo documentazione", "path": "only.md", "doc_type": "doc"},
    )])
    facade = RetrievalFacade(emb, store, COLL, default_k=5)
    docs, code = facade.search_combined("documentazione")
    assert code == []
    assert docs


def test_k_default_and_override():
    emb = FakeEmbedder(dim=8)
    facade = RetrievalFacade(emb, _populated_store(emb), COLL, default_k=1)
    # default_k applies per flow: 1 doc + 1 code at most.
    docs, code = facade.search_combined("x")
    assert len(merge_fused(docs, code)) <= 2
    # k > available per flow → all of each (REQ-026): 1 doc + 2 code = 3.
    docs, code = facade.search_combined("x", k=10)
    assert len(merge_fused(docs, code)) == 3


def test_empty_index_returns_empty_with_warning(caplog):
    emb = FakeEmbedder(dim=8)
    facade = RetrievalFacade(emb, InMemoryStore(), "vuota", default_k=5)
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        docs, code = facade.search_combined("qualsiasi")
    assert merge_fused(docs, code) == []                   # REQ-028: empty, not an exception
    assert docs == [] and code == []
    assert any("no_index" in r.message for r in caplog.records)
    assert emb.calls == 0                                  # does not query the embedder when empty


def test_errors_propagate_not_silently_empty():
    class BrokenEmbedder(FakeEmbedder):
        def embed(self, texts):
            raise EmbeddingError("down", provider="fake", reason="x", retriable=True)

    emb = FakeEmbedder(dim=8)
    store = _populated_store(emb)
    facade = RetrievalFacade(BrokenEmbedder(dim=8), store, COLL, default_k=5)
    with pytest.raises(EmbeddingError):                    # REQ-012: explicit error
        facade.search_combined("x")


def test_usable_as_imported_library():
    # Importable and usable without touching concrete store/embeddings (REQ-029).
    from sertor_core import RetrievalResult, build_facade  # noqa: F401

    assert callable(build_facade)


# --- Multi-collection fan-out of combined search (feature 010, FR-001..009, 070 per-type) ---

WIKI_COLL = "wiki__fake_8"


def _two_collection_store(emb: FakeEmbedder) -> InMemoryStore:
    """Primary (code) + wiki collection, populated with distinct contents."""
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
    docs, code = facade.search_combined("come configurare il backend")
    # The docs flow fans out across primary + wiki collections (FR-001), all DOC type.
    doc_sources = {h.chunk_id.split("#")[0] for h in docs}
    assert any(s.endswith(".md") and "/" in s for s in doc_sources)   # hit from wiki
    assert all(h.doc_type is DocType.DOC for h in docs)
    assert len(docs) <= 5 and len(code) <= 5                          # per-flow ≤ k (FR-002)


def test_combined_merge_is_deterministic_on_ties():
    # On equal scores the ordering within a flow is stable by chunk_id (FR-003, Principio VI).
    emb = FakeEmbedder(dim=8)
    store = InMemoryStore()
    same_text = "identico"
    for coll, cid in ((COLL, "z.py#0"), (WIKI_COLL, "a.py#0")):
        store.upsert(coll, [EmbeddedChunk(
            chunk_id=cid,
            vector=emb.embed([same_text])[0],
            payload={"text": same_text, "path": cid.split("#")[0], "doc_type": "code"},
        )])
    facade = _multi_facade(emb, store)
    _, first_code = facade.search_combined(same_text)
    assert [h.chunk_id for h in first_code] == ["a.py#0", "z.py#0"]   # tie-break by chunk_id
    _, again_code = facade.search_combined(same_text)
    assert [h.chunk_id for h in again_code] == \
        [h.chunk_id for h in first_code]                             # stable output


def test_combined_degrades_when_extra_corpus_never_indexed(caplog):
    # Extra corpus never indexed → warning + results from primary only (FR-004).
    emb = FakeEmbedder(dim=8)
    facade = _multi_facade(emb, _populated_store(emb))
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        docs, code = facade.search_combined("validate")
    assert merge_fused(docs, code)                                 # primary responds
    assert any("no_index" in r.message for r in caplog.records)


def test_combined_all_collections_absent_returns_empty(caplog):
    emb = FakeEmbedder(dim=8)
    facade = RetrievalFacade(emb, InMemoryStore(), COLL, default_k=5,
                             extra_collections={"wiki": WIKI_COLL})
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        docs, code = facade.search_combined("qualsiasi")
    assert merge_fused(docs, code) == []                           # FR-005
    assert emb.calls == 0                                          # no embed on empty


def test_combined_raises_on_provider_mismatch():
    # Wiki corpus indexed with a DIFFERENT provider → explicit error, never fused (FR-009).
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
    # Regression: without extra corpora the legacy mono-type path composes the pair (FR-006).
    emb = FakeEmbedder(dim=8)
    store = _populated_store(emb)
    legacy = RetrievalFacade(emb, store, COLL, default_k=5)
    multi_empty = RetrievalFacade(emb, store, COLL, default_k=5, extra_collections={})
    q = "come configurare il backend"
    legacy_docs, legacy_code = legacy.search_combined(q)
    multi_docs, multi_code = multi_empty.search_combined(q)
    assert [h.chunk_id for h in merge_fused(legacy_docs, legacy_code)] == \
        [h.chunk_id for h in merge_fused(multi_docs, multi_code)]


def test_code_and_docs_do_not_fan_out():
    # FR-006bis: fan-out applies only to combined search.
    emb = FakeEmbedder(dim=8)
    facade = _multi_facade(emb, _two_collection_store(emb))
    assert all(not h.path.startswith(("concepts/", "tech/"))
               for h in facade.search_docs("come configurare il backend"))
