"""Query-time dedup of near-duplicate retrieval results (E5-FEAT-003 / A-07 lever).

The same content often lives in multiple paths — e.g. the `CLAUDE.md` governance blocks are
byte-identical to the copies bundled under the installer's `assets/**` — and those duplicates
saturate the top-k, burying the canonical pages (a `wiki/concepts/*.md` gets pushed to rank 4-6).

Exact content-hash dedup is **not enough**: the same block chunked from two different files gets
different chunk boundaries, so the chunk *texts* differ even though the underlying document is a
byte-copy (measured 2026-07-07: both copies still surfaced at rank 1-2). So the key is a **near-
duplicate** test on word-shingles with a **containment** coefficient (overlap / smaller set), which
is robust to two chunks of the same content having different lengths. Pure, deterministic, no LLM
and no extra embeddings (RNF-1).
"""
from __future__ import annotations

import re

from sertor_core.domain.entities import RetrievalResult

_WHITESPACE = re.compile(r"\s+")

# Word-shingle size and near-duplicate threshold (containment coefficient). Tuned against the eval:
# high enough to avoid collapsing genuinely-distinct results, low enough to catch the same block
# chunked with different boundaries.
_SHINGLE_K = 5
_CONTAINMENT_THRESHOLD = 0.8


def _shingles(text: str) -> frozenset[str]:
    """Set of `_SHINGLE_K`-word shingles over the whitespace-collapsed, case-preserving text.

    Case is preserved (the byte-copies share their case); collapsing whitespace makes shingles
    robust to EOL/indentation differences (CRLF↔LF). Texts shorter than one shingle fall back to a
    single shingle = the whole normalised text, so short results are matched **exactly** (no fuzzy
    over-merge on a handful of words).
    """
    words = _WHITESPACE.sub(" ", text).strip().split(" ")
    if words == [""]:
        return frozenset()
    if len(words) < _SHINGLE_K:
        return frozenset({" ".join(words)})
    return frozenset(
        " ".join(words[i : i + _SHINGLE_K]) for i in range(len(words) - _SHINGLE_K + 1)
    )


def _is_near_duplicate(a: frozenset[str], b: frozenset[str]) -> bool:
    """True when `a` and `b` overlap enough to be the same content (containment coefficient).

    Containment = |a ∩ b| / min(|a|, |b|): measures how much of the *smaller* set is inside the
    larger, so a shorter chunk fully covered by a longer one (same block, different boundaries)
    scores ~1.0 even though their sizes differ.
    """
    if not a or not b:
        return a == b
    overlap = len(a & b)
    return overlap / min(len(a), len(b)) >= _CONTAINMENT_THRESHOLD


def dedup_results(results: list[RetrievalResult]) -> tuple[list[RetrievalResult], int]:
    """Keep the first (highest-ranked) instance of each near-duplicate group; drop the rest.

    The input is assumed **already rank-ordered** (descending relevance), so the first occurrence
    of a content group is the highest-ranked one. Returns `(deduped, removed_count)`. It is a
    **no-op** on already-distinct results (equivalent list, `removed_count == 0`) and fully
    deterministic (no dependency on unstable ordering).
    """
    kept: list[RetrievalResult] = []
    kept_shingles: list[frozenset[str]] = []
    for result in results:
        shingles = _shingles(result.text)
        if any(_is_near_duplicate(shingles, ks) for ks in kept_shingles):
            continue
        kept.append(result)
        kept_shingles.append(shingles)
    return kept, len(results) - len(kept)
