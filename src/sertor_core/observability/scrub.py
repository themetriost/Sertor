"""Free-text secret scrubbing for archived content (feature 031, FR-017..020).

Extends the per-KEY redaction of `observability/logging.py` (`redact()`, which masks values of
fields *named* like secrets) to free TEXTUAL content: a transcript turn is a string, not a
key→value map, so secrets must be matched by their *shape* (API keys, bearer tokens, `KEY=VALUE`
assignments with a secret hint). Pure, deterministic, stdlib-only (`re`) → testable offline
(SC-004). Never bypassable: the service applies it to every turn before persisting.
"""
from __future__ import annotations

import logging
import re

from sertor_core.observability.logging import _SECRET_HINTS, log_event

_PLACEHOLDER = "[REDACTED]"

# Secret hints reused from the per-field redaction (D6, DRY): the same vocabulary drives the
# `KEY=VALUE` pattern below — no duplicated secret list.
_HINTS_ALT = "|".join(re.escape(h) for h in _SECRET_HINTS)

# Pre-compiled base patterns (compiled once at import, like `_WORD` in logging.py). Each redacts
# the whole secret-shaped span.
_BASE_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Provider API keys: OpenAI-style `sk-...` and AWS access key ids `AKIA...`.
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    # Bearer / Authorization header value (inline or on its own): redact the credential.
    re.compile(r"(?i)\b(?:authorization\s*:?\s*)?bearer\s+[A-Za-z0-9._~+/=-]{6,}"),
    re.compile(r"(?i)\bauthorization\s*[:=]\s*\S+"),
    # `KEY=VALUE` / `KEY: VALUE` where KEY contains a secret hint (api_key, password, token, ...).
    re.compile(rf"(?i)\b[A-Za-z0-9_.-]*(?:{_HINTS_ALT})[A-Za-z0-9_.-]*\s*[:=]\s*\S+"),
)


def scrub_text(text: str, extra_patterns: tuple[str, ...] = ()) -> str:
    """Replace secret-shaped spans in free text with a placeholder (FR-017/018).

    Pure and deterministic. Base patterns cover API keys (`sk-…`, `AKIA…`), bearer/Authorization
    and `KEY=VALUE` with a secret hint; `extra_patterns` (config, FR-020) are compiled per call.
    A pattern that fails to compile/apply degrades conservatively: the input is returned redacted
    wholesale for that pattern is impossible, so we redact nothing extra for it but emit a warning
    (FR-019) — the base patterns still apply, so known secrets are never leaked by an invalid extra.
    """
    if not text:
        return text

    out = text
    for pattern in _BASE_PATTERNS:
        out = pattern.sub(_PLACEHOLDER, out)

    for raw in extra_patterns:
        out = _apply_extra(out, raw)
    return out


def _apply_extra(text: str, raw: str) -> str:
    """Apply one extra (config) pattern, degrading conservatively on a bad regex (FR-019)."""
    try:
        return re.sub(raw, _PLACEHOLDER, text)
    except re.error as exc:
        # Conservative fallback: an unusable extra pattern must not leak the text it meant to
        # guard. We cannot know its intended span, so we redact the whole text and warn — privacy
        # wins over fidelity (FR-019). Base patterns already ran, so this only loses readability.
        log_event(logging.WARNING, "memory_scrub_fallback",
                  pattern=raw, reason=type(exc).__name__, detail=str(exc))
        return _PLACEHOLDER
