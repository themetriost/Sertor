"""Integration: composing local providers via build_embedder on the fixture (068, TASK-B04)."""
from __future__ import annotations

import math
from pathlib import Path

import pytest

from sertor_core.composition import build_embedder, collection_name
from sertor_core.config.settings import Settings

pytestmark = pytest.mark.integration

FIXTURE = Path(__file__).parent.parent / "fixtures" / "glove_mini.txt"


def _l2(vec: list[float]) -> float:
    return math.sqrt(sum(v * v for v in vec))


def test_build_glove_embedder_and_embed():
    from sertor_core.adapters.embeddings.glove import GloveEmbedder

    settings = Settings(embed_provider="glove", glove_path=FIXTURE)
    embedder = build_embedder(settings)
    assert isinstance(embedder, GloveEmbedder)
    vec = embedder.embed(["hello world"])[0]
    assert len(vec) == 300
    assert _l2(vec) == pytest.approx(1.0, abs=1e-5)


def test_build_hash_embedder_and_embed():
    from sertor_core.adapters.embeddings.hashing import HashingEmbedder

    embedder = build_embedder(Settings(embed_provider="hash"))
    assert isinstance(embedder, HashingEmbedder)
    vec = embedder.embed(["hello"])[0]
    assert len(vec) == 512
    assert _l2(vec) == pytest.approx(1.0, abs=1e-6)


def test_collection_names_distinct_per_provider():
    glove = build_embedder(Settings(embed_provider="glove", glove_path=FIXTURE))
    hashed = build_embedder(Settings(embed_provider="hash"))
    glove_coll = collection_name(Settings(corpus="test"), glove)
    hash_coll = collection_name(Settings(corpus="test"), hashed)
    assert "glove" in glove_coll
    assert "hash" in hash_coll
    assert glove_coll != hash_coll
