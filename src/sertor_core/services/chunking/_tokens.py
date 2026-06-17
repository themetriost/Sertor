"""Token-aware capping of oversized chunks.

Structural chunkers (markdown by heading, code by symbol) can emit a unit larger than the embedding
model's token budget (text-embedding-3-large: 8192 tokens → http 400). This module caps a chunk at
`max_tokens`, sub-splitting an oversized one so the full large-model window is used for coherent
sections without ever exceeding the limit.

Token counting uses **tiktoken** (`cl100k_base`, the tokenizer of text-embedding-3) when the extra
`tokenizer` is installed — precise. Without it, the core stays installable and offline-safe by
falling back to a **conservative per-char estimate** (~2 chars/token, an over-estimate that never
under-splits). tiktoken is imported lazily and the encoder is cached for the process.
"""
from __future__ import annotations

from sertor_core.services.chunking.fallback import size_chunks

# ~2 chars/token is a safe over-estimate (real text is 3–4): the fallback never under-splits, so an
# oversized chunk is never sent whole even without a precise tokenizer.
_FALLBACK_CHARS_PER_TOKEN = 2

_encoder = None  # cached tiktoken Encoding | None; None once a load attempt has failed
_tried = False


def _get_encoder():
    """Load + cache the tiktoken encoder; return None if unavailable (offline / not installed)."""
    global _encoder, _tried
    if _tried:
        return _encoder
    _tried = True
    try:
        import tiktoken

        _encoder = tiktoken.get_encoding("cl100k_base")
    except Exception:  # not installed, or vocab unavailable offline → safe fallback
        _encoder = None
    return _encoder


def count_tokens(text: str) -> int:
    """Token count: exact via tiktoken when available, else a safe per-char over-estimate."""
    enc = _get_encoder()
    if enc is not None:
        return len(enc.encode(text))
    return -(-len(text) // _FALLBACK_CHARS_PER_TOKEN)  # ceil(len / chars_per_token)


def cap_to_tokens(text: str, max_tokens: int, overlap_tokens: int) -> list[str]:
    """Return `[text]` if within `max_tokens`, else sub-split so each piece fits the budget.

    With tiktoken: split on exact token windows (overlap in tokens). Without: split on line
    boundaries via `size_chunks`, budgeting characters at the safe per-char ratio. Either way no
    returned piece exceeds `max_tokens`.
    """
    max_tokens = max(1, max_tokens)
    enc = _get_encoder()
    if enc is not None:
        tokens = enc.encode(text)
        if len(tokens) <= max_tokens:
            return [text]
        step = max(1, max_tokens - max(0, overlap_tokens))
        pieces: list[str] = []
        start = 0
        while start < len(tokens):
            pieces.append(enc.decode(tokens[start : start + max_tokens]))
            if start + max_tokens >= len(tokens):
                break
            start += step
        return pieces
    # Fallback: no tokenizer — budget characters conservatively and split on line boundaries.
    if len(text) <= max_tokens * _FALLBACK_CHARS_PER_TOKEN:
        return [text]
    char_budget = max_tokens * _FALLBACK_CHARS_PER_TOKEN
    overlap_chars = max(0, overlap_tokens) * _FALLBACK_CHARS_PER_TOKEN
    return [piece["text"] for piece in size_chunks(text, char_budget, overlap_chars)]
