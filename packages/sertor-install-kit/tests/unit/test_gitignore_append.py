"""Tests for `.gitignore` append: creation, idempotence, preservation, dedup."""
from __future__ import annotations

from pathlib import Path

from sertor_install_kit.artifacts import Outcome
from sertor_install_kit.gitignore_append import RUNTIME_IGNORES, append_gitignore


def test_create(tmp_path: Path):
    gi = tmp_path / ".gitignore"
    outcome, _ = append_gitignore(gi)
    assert outcome is Outcome.CREATED
    text = gi.read_text(encoding="utf-8")
    assert all(entry in text for entry in RUNTIME_IGNORES)


def test_idempotent_skip(tmp_path: Path):
    gi = tmp_path / ".gitignore"
    append_gitignore(gi)
    outcome, _ = append_gitignore(gi)
    assert outcome is Outcome.SKIPPED


def test_preserve_existing(tmp_path: Path):
    gi = tmp_path / ".gitignore"
    gi.write_text("bin/\nobj/\n", encoding="utf-8")
    outcome, _ = append_gitignore(gi)
    assert outcome is Outcome.MERGED
    text = gi.read_text(encoding="utf-8")
    assert "bin/" in text and ".sertor/.env" in text


def test_partial_dedup(tmp_path: Path):
    gi = tmp_path / ".gitignore"
    gi.write_text(".sertor/.env\n", encoding="utf-8")
    outcome, _ = append_gitignore(gi)
    assert outcome is Outcome.MERGED
    assert gi.read_text(encoding="utf-8").count(".sertor/.env") == 1  # not duplicated
