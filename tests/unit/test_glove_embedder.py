"""Unit tests for GloveEmbedder (068, TASK-A02): fixture vocab, OOV, lazy load."""
from __future__ import annotations

import math
from pathlib import Path

import pytest

from sertor_core.adapters.embeddings.glove import GloveEmbedder

FIXTURE = Path(__file__).parent.parent / "fixtures" / "glove_mini.txt"


def _l2(vec: list[float]) -> float:
    return math.sqrt(sum(v * v for v in vec))


def test_embed_shape_and_norm():
    vec = GloveEmbedder(FIXTURE).embed(["hello world"])[0]
    assert len(vec) == 300
    assert _l2(vec) == pytest.approx(1.0, abs=1e-5)


def test_determinism():
    emb = GloveEmbedder(FIXTURE)
    assert emb.embed(["hello world"]) == emb.embed(["hello world"])


def test_oov_camelcase_split():
    """`getUserId` → get, user, id (all in fixture) → non-zero vector (REQ-023)."""
    vec = GloveEmbedder(FIXTURE).embed(["getUserId"])[0]
    assert any(v != 0.0 for v in vec)


def test_all_oov_zero_vector():
    vec = GloveEmbedder(FIXTURE).embed(["xqzjvbk"])[0]
    assert vec == [0.0] * 300


def test_empty_text_zero_vector():
    vec = GloveEmbedder(FIXTURE).embed([""])[0]
    assert vec == [0.0] * 300


def test_lazy_load(monkeypatch):
    """The vocabulary is loaded only on the first embed, not at construction."""
    emb = GloveEmbedder(FIXTURE)
    calls = {"n": 0}
    real = emb._load_vocab

    def counting():
        calls["n"] += 1
        return real()

    monkeypatch.setattr(emb, "_load_vocab", counting)
    assert calls["n"] == 0  # constructing did not load
    emb.embed(["hello"])
    assert calls["n"] == 1
    emb.embed(["world"])
    assert calls["n"] == 1  # vocab reused, not reloaded


def test_batch_order_preserved():
    emb = GloveEmbedder(FIXTURE)
    a, b = emb.embed(["hello", "world"])
    assert a == emb.embed(["hello"])[0]
    assert b == emb.embed(["world"])[0]


def test_empty_input():
    assert GloveEmbedder(FIXTURE).embed([]) == []
