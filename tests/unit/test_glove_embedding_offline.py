"""Offline smoke tests for GloVe on the mini fixture (068, TASK-B02)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from sertor_core.adapters.embeddings.glove import GloveEmbedder

FIXTURE = Path(__file__).parent.parent / "fixtures" / "glove_mini.txt"


def _load_raw_vocab() -> dict[str, list[float]]:
    vocab: dict[str, list[float]] = {}
    for line in FIXTURE.read_text(encoding="utf-8").splitlines():
        parts = line.split(" ")
        vocab[parts[0]] = [float(x) for x in parts[1:]]
    return vocab


def test_mean_plus_norm_deterministic():
    import math

    vocab = _load_raw_vocab()
    expected = [(a + b) / 2 for a, b in zip(vocab["hello"], vocab["world"], strict=True)]
    norm = math.sqrt(sum(x * x for x in expected))
    expected = [x / norm for x in expected]
    got = GloveEmbedder(FIXTURE).embed(["hello world"])[0]
    assert got == pytest.approx(expected, abs=1e-5)


def test_oov_camel_split_with_fixture():
    # worldCode → world (in vocab), code (in vocab) → non-zero vector
    vec = GloveEmbedder(FIXTURE).embed(["worldCode"])[0]
    assert any(v != 0.0 for v in vec)


def test_all_oov_zero():
    assert GloveEmbedder(FIXTURE).embed(["zzqqxx"])[0] == [0.0] * 300


def test_batch_deterministic():
    emb = GloveEmbedder(FIXTURE)
    assert emb.embed(["hello", "world"]) == emb.embed(["hello", "world"])


def test_numpy_not_imported_for_hashing():
    """Importing the hashing adapter does not pull numpy (RNF-2/REQ-053)."""
    code = (
        "import sys;"
        "import sertor_core.adapters.embeddings.hashing;"
        "print('numpy' in sys.modules)"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert out.stdout.strip() == "False"
