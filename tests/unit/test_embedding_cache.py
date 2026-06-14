"""Test 019 US1 — embedding cache by content-hash (REQ-H4).

Offline F.I.R.S.T.: a `CountingEmbedder` records every text it embeds, so hits never reaching the
inner are observable. SQLite store under `tmp_path`. Covers SC-001/002/004 and FR-001..006/010.
"""
from __future__ import annotations

import logging

from sertor_core.adapters.embeddings.cache import CachingEmbedder, EmbeddingCache
from tests.fixtures.mocks import CountingEmbedder


def _caching(tmp_path, inner):
    return CachingEmbedder(inner, EmbeddingCache(tmp_path))


def test_second_embed_is_full_cache_hit(tmp_path):
    # SC-001: re-embedding the same texts does not call the inner again.
    inner = CountingEmbedder(name="m1")
    emb = _caching(tmp_path, inner)
    first = emb.embed(["a", "b", "c"])
    assert inner.embedded == ["a", "b", "c"]
    second = emb.embed(["a", "b", "c"])
    assert second == first
    assert inner.embedded == ["a", "b", "c"]   # not touched the second time
    assert inner.calls == 1


def test_partial_miss_only_embeds_changed(tmp_path):
    # SC-002: only changed/new texts are embedded; cached ones come from the store.
    inner = CountingEmbedder(name="m1")
    emb = _caching(tmp_path, inner)
    emb.embed(["a", "b"])
    inner.embedded.clear()
    emb.embed(["a", "b", "c", "d"])
    assert inner.embedded == ["c", "d"]


def test_in_call_dedup(tmp_path):
    # D8: identical texts in one call embed once; duplicates reuse the same vector, order kept.
    inner = CountingEmbedder(name="m1")
    emb = _caching(tmp_path, inner)
    out = emb.embed(["x", "x", "y", "x"])
    assert inner.embedded == ["x", "y"]
    assert out[0] == out[1] == out[3]
    assert len(out) == 4


def test_cross_model_isolation(tmp_path):
    # SC-004: same text under a different model name must not serve the other model's vectors.
    cache = EmbeddingCache(tmp_path)
    a = CachingEmbedder(CountingEmbedder(dim=8, name="model-a"), cache)
    b_inner = CountingEmbedder(dim=16, name="model-b")
    b = CachingEmbedder(b_inner, cache)
    a.embed(["t"])
    b.embed(["t"])
    assert b_inner.embedded == ["t"]


def test_cached_vectors_equivalent_to_inner(tmp_path):
    # FR-005: a cached vector equals the one the inner would produce (exact float64 round-trip).
    fresh = CountingEmbedder(name="m1").embed(["solo"])
    _caching(tmp_path, CountingEmbedder(name="m1")).embed(["solo"])  # populate the store
    inner = CountingEmbedder(name="m1")
    cached = _caching(tmp_path, inner).embed(["solo"])  # served from the store
    assert cached[0] == fresh[0]
    assert inner.embedded == []


def test_dim_set_on_full_cache_hit(tmp_path):
    # D8: with 100% hit the inner is never called, yet dim must still be correct (IndexReport).
    _caching(tmp_path, CountingEmbedder(dim=8, name="m1")).embed(["a"])
    inner = CountingEmbedder(dim=8, name="m1")
    emb = _caching(tmp_path, inner)
    emb.embed(["a"])
    assert inner.embedded == []
    assert emb.dim == 8


def test_store_failure_degrades_to_miss(tmp_path, caplog):
    # FR-004: a corrupt store → embed behaves as all-miss, no exception, warning emitted.
    (tmp_path / "embed_cache.sqlite").write_bytes(b"not a database at all")
    inner = CountingEmbedder(name="m1")
    emb = _caching(tmp_path, inner)
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        out = emb.embed(["a", "b"])
    assert len(out) == 2
    assert inner.embedded == ["a", "b"]
    assert any(
        getattr(r, "operation", None) == "embeddings_cache_unavailable" for r in caplog.records
    )


def test_persistence_across_instances(tmp_path):
    # FR-006: a fresh cache object on the same dir sees previously written vectors.
    CachingEmbedder(CountingEmbedder(name="m1"), EmbeddingCache(tmp_path)).embed(["k"])
    inner = CountingEmbedder(name="m1")
    CachingEmbedder(inner, EmbeddingCache(tmp_path)).embed(["k"])
    assert inner.embedded == []


def test_cache_hit_event(tmp_path, caplog):
    # FR-010: the embeddings_cache event distinguishes hits from misses (SC-001/006 observable).
    inner = CountingEmbedder(name="m1")
    emb = _caching(tmp_path, inner)
    emb.embed(["a", "b"])
    with caplog.at_level(logging.INFO, logger="sertor_core"):
        emb.embed(["a", "b", "c"])
    events = [r for r in caplog.records if getattr(r, "operation", None) == "embeddings_cache"]
    assert events
    rec = events[-1]
    assert (rec.hits, rec.misses, rec.total) == (2, 1, 3)


def test_empty_input(tmp_path):
    assert _caching(tmp_path, CountingEmbedder(name="m1")).embed([]) == []
