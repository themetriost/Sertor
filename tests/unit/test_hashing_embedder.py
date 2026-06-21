"""Unit tests for HashingEmbedder (068, TASK-A01): determinism, OOV, empty text."""
from __future__ import annotations

import json
import subprocess
import sys

import pytest

from sertor_core.adapters.embeddings.hashing import HashingEmbedder


def test_embed_shape_and_floats():
    vecs = HashingEmbedder().embed(["x"])
    assert len(vecs) == 1
    assert len(vecs[0]) == 512
    assert all(isinstance(v, float) for v in vecs[0])


def test_determinism_same_run():
    emb = HashingEmbedder()
    assert emb.embed(["hello world"]) == emb.embed(["hello world"])


def test_determinism_cross_pythonhashseed():
    """Identical vector regardless of PYTHONHASHSEED (no builtin hash() — REQ-013, SC-003)."""
    code = (
        "import json;"
        "from sertor_core.adapters.embeddings.hashing import HashingEmbedder;"
        "print(json.dumps(HashingEmbedder().embed(['test text'])[0]))"
    )

    def _run(seed: str) -> list[float]:
        out = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, env={**_base_env(), "PYTHONHASHSEED": seed},
            check=True,
        )
        return json.loads(out.stdout.strip())

    assert _run("0") == _run("42")


def _base_env() -> dict[str, str]:
    import os

    return {k: v for k, v in os.environ.items()}


def test_oov_identifier_nonzero():
    """Code identifiers (OOV for any word model) still get char-n-gram signal (REQ-011)."""
    vec = HashingEmbedder().embed(["build_indexer"])[0]
    assert any(v != 0.0 for v in vec)


def test_empty_text_zero_vector():
    vec = HashingEmbedder().embed([""])[0]
    assert vec == [0.0] * 512


def test_batch_order_preserved():
    emb = HashingEmbedder()
    a, b = emb.embed(["a", "b"])
    assert a == emb.embed(["a"])[0]
    assert b == emb.embed(["b"])[0]


def test_empty_input():
    assert HashingEmbedder().embed([]) == []


@pytest.mark.parametrize("text", ["hello world", "GetUserId", ""])
def test_l2_norm_unit_or_zero(text):
    import math

    vec = HashingEmbedder().embed([text])[0]
    norm = math.sqrt(sum(v * v for v in vec))
    assert norm == pytest.approx(1.0) or norm == 0.0
