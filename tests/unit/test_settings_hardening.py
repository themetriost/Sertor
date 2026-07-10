"""Test 018 Foundational — the hardening knobs live in Settings (Principio VIII).

Env-driven, with `.env` loading disabled (`env_file=None`) for isolation.
"""
from __future__ import annotations

import pytest

from sertor_core.config.settings import Settings
from sertor_core.domain.errors import ConfigError


def test_hardening_knobs_from_env(monkeypatch):
    monkeypatch.setenv("SERTOR_EMBED_RETRY_ATTEMPTS", "5")
    monkeypatch.setenv("SERTOR_EMBED_RETRY_BASE", "0.25")
    monkeypatch.setenv("SERTOR_MIN_SCORE", "0.4")
    s = Settings.load(env_file=None)
    assert s.embed_retry_attempts == 5
    assert s.embed_retry_base_s == 0.25
    assert s.retrieval_min_score == 0.4


def test_hardening_defaults_when_env_absent(monkeypatch):
    for key in ("SERTOR_EMBED_RETRY_ATTEMPTS", "SERTOR_EMBED_RETRY_BASE", "SERTOR_MIN_SCORE"):
        monkeypatch.delenv(key, raising=False)
    s = Settings.load(env_file=None)
    assert s.embed_retry_attempts == 3          # conservative default (retry active)
    assert s.embed_retry_base_s == 0.5
    assert s.retrieval_min_score is None        # confidence threshold disabled = today's behaviour


def test_min_score_blank_env_is_none(monkeypatch):
    monkeypatch.setenv("SERTOR_MIN_SCORE", "   ")
    assert Settings.load(env_file=None).retrieval_min_score is None


def test_embed_cache_knob_from_env(monkeypatch):
    # 019, REQ-H4: the cache is configurable; explicit false disables it.
    monkeypatch.setenv("SERTOR_EMBED_CACHE", "false")
    assert Settings.load(env_file=None).embed_cache_enabled is False


def test_embed_cache_default_on(monkeypatch):
    # A-08 security review: default ON — the unconditional SessionEnd re-index would otherwise
    # re-embed identical content on a paid provider every session.
    monkeypatch.delenv("SERTOR_EMBED_CACHE", raising=False)
    assert Settings.load(env_file=None).embed_cache_enabled is True


# --- A-14: numeric parsing is guarded (fail loud, not a raw ValueError traceback) --------------

def test_invalid_int_env_fails_loud(monkeypatch):
    # A set-but-non-integer knob raises ConfigError NAMING the variable, not a raw
    # `ValueError: invalid literal for int()` that hides which knob is misconfigured.
    monkeypatch.setenv("SERTOR_RRF_C", "not-a-number")
    with pytest.raises(ConfigError) as exc:
        Settings.load(env_file=None)
    assert "SERTOR_RRF_C" in str(exc.value)


def test_invalid_float_env_fails_loud(monkeypatch):
    monkeypatch.setenv("SERTOR_EMBED_RETRY_BASE", "fast")
    with pytest.raises(ConfigError) as exc:
        Settings.load(env_file=None)
    assert "SERTOR_EMBED_RETRY_BASE" in str(exc.value)


def test_invalid_optional_float_env_fails_loud(monkeypatch):
    # The `_or_none` variant is guarded too: a set-but-invalid value fails loud, not a silent None.
    monkeypatch.setenv("SERTOR_MIN_SCORE", "high")
    with pytest.raises(ConfigError) as exc:
        Settings.load(env_file=None)
    assert "SERTOR_MIN_SCORE" in str(exc.value)


def test_blank_numeric_env_uses_default(monkeypatch):
    # A blank value is treated as unset -> default, never a crash.
    monkeypatch.setenv("SERTOR_RRF_C", "   ")
    assert Settings.load(env_file=None).rrf_c == 60
