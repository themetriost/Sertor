"""US2 — `scrub_text` pure function (031, FR-017..020, SC-004).

Synthetic secrets only (no real credentials). Offline, deterministic.
"""
from __future__ import annotations

import logging

from sertor_core.observability.scrub import scrub_text

_REDACTED = "[REDACTED]"


def test_openai_style_api_key_redacted():
    out = scrub_text("here is sk-abc123DEF456ghi789 done")
    assert "sk-abc123DEF456ghi789" not in out
    assert _REDACTED in out


def test_aws_access_key_redacted():
    out = scrub_text("key AKIA1234567890ABCDEF in config")
    assert "AKIA1234567890ABCDEF" not in out
    assert _REDACTED in out


def test_bearer_authorization_redacted():
    out = scrub_text("Authorization: Bearer tok_abcdef123 stuff")
    assert "tok_abcdef123" not in out
    assert _REDACTED in out


def test_key_value_with_hint_redacted():
    for line in ("API_KEY=secretvalue", "PASSWORD=mysecret", "auth_token: zzz999"):
        out = scrub_text(line)
        assert _REDACTED in out, line
        assert "secretvalue" not in out
        assert "mysecret" not in out
        assert "zzz999" not in out


def test_plain_text_unchanged():
    text = "the quick brown fox jumps over the lazy dog"
    assert scrub_text(text) == text


def test_non_secret_key_value_not_over_redacted():
    # A KEY=VALUE without a secret hint must survive (no over-redaction of ordinary text).
    text = "count=42 and name=mario"
    assert scrub_text(text) == text


def test_extra_patterns_applied():
    out = scrub_text("token GH_PAT_abc123 here", extra_patterns=("GH_PAT_[A-Za-z0-9]+",))
    assert "GH_PAT_abc123" not in out
    assert _REDACTED in out


def test_invalid_extra_pattern_degrades_conservatively(caplog):
    # FR-019: a broken extra regex must not leak; warn + redact wholesale, base patterns still ran.
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        out = scrub_text("some content", extra_patterns=("([unclosed",))
    assert out == _REDACTED
    assert any("memory_scrub_fallback" in r.getMessage() for r in caplog.records)


def test_empty_text_returns_empty():
    assert scrub_text("") == ""
