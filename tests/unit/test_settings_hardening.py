"""Test 018 Foundational — the hardening knobs live in Settings (Principio VIII).

Env-driven, with `.env` loading disabled (`env_file=None`) for isolation.
"""
from __future__ import annotations

from sertor_core.config.settings import Settings


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
