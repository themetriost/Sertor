"""GloVe embedder — static word vectors, the default provider (068, FEAT-011, DA-3).

A deterministic `EmbeddingProvider` that averages pre-trained GloVe 6B 300d vectors (PDDL/public
domain). NO model is executed: it reads `glove.6B.300d.txt` and computes the mean of the in-vocab
token vectors, then L2-normalises (REQ-020/021). Out-of-vocabulary tokens are retried after a
camelCase/snake_case split (`getUserId` → `get`, `user`, `id`); still-OOV sub-tokens are dropped;
an all-OOV / empty text yields a deterministic zero vector (REQ-023) — a valid result, not a hidden
absence.

`numpy` (already transitive via chromadb) is imported **lazy** inside the methods, so selecting
another provider neither imports it nor reads the data file (REQ-024/053). The vocabulary is loaded
**lazy on the first `embed`** (install≠run).
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sertor_core.domain.errors import GloveUnavailableError
from sertor_core.observability.logging import log_event

if TYPE_CHECKING:
    import numpy

_DIM = 300
_SPLIT_RE = re.compile(r"[^0-9a-zA-Z]+")
_CAMEL_RE = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|[0-9]+")


def _tokenize(text: str) -> list[str]:
    """Tokens split on non-alphanumerics, preserving original case (REQ-021).

    Case is preserved here so the OOV camelCase retry (`_subsplit`) can see word boundaries; the
    in-vocab lookup itself lowercases each token.
    """
    return [t for t in _SPLIT_RE.split(text) if t]


def _subsplit(token: str) -> list[str]:
    """Split a camelCase/snake_case identifier into lowercased sub-tokens (REQ-023).

    snake_case is already handled by `_tokenize` (`_` is non-alphanumeric); this catches camelCase
    within a single token. Applied on the ORIGINAL-case token, then the pieces are lowercased.
    """
    parts = _CAMEL_RE.findall(token)
    return [p.lower() for p in parts if p]


class GloveEmbedder:
    """`EmbeddingProvider` averaging static GloVe vectors. Vocabulary loaded lazily."""

    def __init__(self, glove_file: Path, batch_size: int = 64):
        self.name = "glove:300"
        self.dim: int = _DIM
        self.batch_size = batch_size
        self._glove_file = glove_file
        self._vocab: dict[str, numpy.ndarray] | None = None

    def _load_vocab(self) -> dict[str, Any]:
        """Load `token → vector` lazily from the resolved file (numpy imported lazily)."""
        import numpy as np

        vocab: dict[str, np.ndarray] = {}
        try:
            with self._glove_file.open(encoding="utf-8") as fh:
                for line in fh:
                    parts = line.rstrip("\n").split(" ")
                    if len(parts) != _DIM + 1:
                        raise GloveUnavailableError(
                            "unexpected GloVe line format", reason="parse_error"
                        )
                    word = parts[0]
                    vocab[word] = np.asarray(parts[1:], dtype=np.float32)
        except OSError as exc:
            raise GloveUnavailableError(
                "could not read the GloVe vectors file", reason=type(exc).__name__
            ) from exc
        except ValueError as exc:
            raise GloveUnavailableError(
                "could not parse the GloVe vectors file", reason="parse_error"
            ) from exc
        return vocab

    def _vectors_for(self, text: str, vocab: dict[str, Any]) -> list[Any]:
        """In-vocab vectors for the tokens of `text` (with camel/snake OOV retry)."""
        vectors: list[Any] = []
        for token in _tokenize(text):
            vec = vocab.get(token.lower())
            if vec is not None:
                vectors.append(vec)
                continue
            for sub in _subsplit(token):
                sub_vec = vocab.get(sub)
                if sub_vec is not None:
                    vectors.append(sub_vec)
        return vectors

    def embed(self, texts: list[str]) -> list[list[float]]:
        import numpy as np

        if not texts:
            return []
        if self._vocab is None:
            self._vocab = self._load_vocab()
        else:
            log_event(logging.INFO, "glove_cache_hit", hit=True)  # vocab reused from a prior call
        out: list[list[float]] = []
        for text in texts:
            vectors = self._vectors_for(text, self._vocab)
            if not vectors:
                out.append([0.0] * _DIM)  # all-OOV / empty → deterministic zero vector
                continue
            mean = np.mean(np.stack(vectors), axis=0)
            norm = float(np.linalg.norm(mean))
            if norm == 0.0:
                out.append([0.0] * _DIM)
            else:
                out.append((mean / norm).astype(float).tolist())
        return out
