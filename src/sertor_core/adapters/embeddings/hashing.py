"""Hashing embedder — zero-download lexical floor (068, FEAT-011, DA-2).

A deterministic, dependency-free `EmbeddingProvider` for airgapped/CI use: char-n-gram feature
hashing into a fixed 512-dim space. NO model, NO network, NO credentials — sola stdlib.

The character n-grams give signal even to out-of-vocabulary tokens (code identifiers like
`build_indexer`), which a word-vector model would drop. The hash is **stable** across runs,
machines, and Python versions: it uses `hashlib.blake2b`, never the builtin `hash()` (salted
per-process via `PYTHONHASHSEED`) — REQ-013/RNF-1. The signal is lexical, not semantic: the
composition root warns to configure glove/ollama/azure for NL search (REQ-014).
"""
from __future__ import annotations

import hashlib
import math

_DIM = 512
_NGRAM_SIZES = (3, 4, 5)
_PAD = " "  # word-boundary padding so short tokens still produce n-grams


def _char_ngrams(text: str) -> list[str]:
    """Char-n-grams (n=3..5) of a lowercased text, with word-boundary padding.

    Each whitespace-separated token is padded with a leading/trailing space so that short tokens
    (and the boundary itself) contribute n-grams; the n-grams of every token are concatenated.
    """
    ngrams: list[str] = []
    for token in text.lower().split():
        padded = _PAD + token + _PAD
        for n in _NGRAM_SIZES:
            if len(padded) < n:
                continue
            for i in range(len(padded) - n + 1):
                ngrams.append(padded[i : i + n])
    return ngrams


class HashingEmbedder:
    """`EmbeddingProvider` via char-n-gram feature hashing (stdlib only, deterministic)."""

    def __init__(self, batch_size: int = 64):
        self.name = "hash:512"
        self.dim: int = _DIM
        self.batch_size = batch_size

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * _DIM
        for ngram in _char_ngrams(text):
            # blake2b is stable cross-run/machine/Python (unlike the salted builtin hash()).
            digest = hashlib.blake2b(ngram.encode("utf-8"), digest_size=8).digest()
            h = int.from_bytes(digest, "big")
            idx = h % _DIM
            sign = 1.0 if (h >> 8) & 1 else -1.0  # sign-hashing reduces systematic positive bias
            vec[idx] += sign
        norm = math.sqrt(sum(x * x for x in vec))
        if norm == 0.0:
            return vec  # empty / no-ngram text → 512 zeros (deterministic, not a failure)
        return [x / norm for x in vec]

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return [self._embed_one(t) for t in texts]
