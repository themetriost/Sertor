"""Tests for `.env` merge: creation, idempotence, preservation, M1 (`.sertor`)."""
from __future__ import annotations

from pathlib import Path

from sertor_install_kit.artifacts import Outcome
from sertor_install_kit.env_merge import merge_env

AZURE = (
    "SERTOR_EMBED_PROVIDER=azure\n"
    "SERTOR_CORPUS=myapp\n"
    "AZURE_OPENAI_API_KEY=\n"
    "SERTOR_EXCLUDE_PATTERNS=.venv,.index,.sertor\n"
)


def test_create_writes_template(tmp_path: Path):
    env = tmp_path / ".env"
    outcome, _ = merge_env(env, AZURE)
    assert outcome is Outcome.CREATED
    assert "SERTOR_EMBED_PROVIDER=azure" in env.read_text(encoding="utf-8")


def test_secret_left_empty(tmp_path: Path):
    env = tmp_path / ".env"
    merge_env(env, AZURE)
    pairs = dict(
        ln.split("=", 1)
        for ln in env.read_text().splitlines()
        if "=" in ln and not ln.startswith("#")
    )
    assert pairs["AZURE_OPENAI_API_KEY"] == ""


def test_idempotent_skip(tmp_path: Path):
    env = tmp_path / ".env"
    merge_env(env, AZURE)
    outcome, _ = merge_env(env, AZURE)
    assert outcome is Outcome.SKIPPED


def test_preserve_user_value_add_missing(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text("SERTOR_CORPUS=mio\n", encoding="utf-8")
    outcome, _ = merge_env(env, AZURE)
    assert outcome is Outcome.MERGED
    text = env.read_text(encoding="utf-8")
    assert "SERTOR_CORPUS=mio" in text  # user value NOT overwritten
    assert "SERTOR_EMBED_PROVIDER=azure" in text  # missing key added


def test_m1_ensure_sertor_in_existing_excludes(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text("SERTOR_EXCLUDE_PATTERNS=.venv,.index\n", encoding="utf-8")
    outcome, detail = merge_env(env, AZURE)
    assert outcome is Outcome.MERGED
    line = next(
        ln for ln in env.read_text().splitlines() if ln.startswith("SERTOR_EXCLUDE_PATTERNS=")
    )
    assert ".sertor" in line and ".venv" in line  # added without losing pre-existing entries
    assert ".sertor" in detail
