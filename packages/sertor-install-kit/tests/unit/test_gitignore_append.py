"""Tests for `.gitignore` append: creation, idempotence, preservation, dedup."""
from __future__ import annotations

from pathlib import Path

from sertor_install_kit.artifacts import Outcome
from sertor_install_kit.gitignore_append import (
    RUNTIME_IGNORES,
    append_gitignore,
    remove_gitignore_lines,
)


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


# --- feature 048: remove_gitignore_lines (T016) -------------------------------------------------


def test_remove_gitignore_lines_removes_only_sertor(tmp_path: Path):
    gi = tmp_path / ".gitignore"
    gi.write_text("bin/\nobj/\n", encoding="utf-8")
    append_gitignore(gi)  # adds header + RUNTIME_IGNORES
    outcome, _ = remove_gitignore_lines(gi)
    assert outcome is Outcome.REMOVED
    text = gi.read_text(encoding="utf-8")
    assert "bin/" in text and "obj/" in text  # user lines preserved
    for entry in RUNTIME_IGNORES:
        assert entry not in text
    assert "Sertor RAG runtime" not in text  # header removed


def test_remove_gitignore_lines_no_sertor_skips(tmp_path: Path):
    gi = tmp_path / ".gitignore"
    gi.write_text("bin/\nobj/\n", encoding="utf-8")
    before = gi.read_bytes()
    outcome, _ = remove_gitignore_lines(gi)
    assert outcome is Outcome.SKIPPED
    assert gi.read_bytes() == before


def test_remove_gitignore_lines_robust_to_whitespace(tmp_path: Path):
    gi = tmp_path / ".gitignore"
    # Sertor lines with extra surrounding whitespace (reformatting) + a user line.
    gi.write_text("keep/\n   .sertor/.env  \n\t.sertor/.venv/\n", encoding="utf-8")
    outcome, _ = remove_gitignore_lines(gi)
    assert outcome is Outcome.REMOVED
    text = gi.read_text(encoding="utf-8")
    assert "keep/" in text
    assert ".sertor/.env" not in text
    assert ".sertor/.venv/" not in text


def test_remove_gitignore_lines_missing_file_skips(tmp_path: Path):
    gi = tmp_path / ".gitignore"
    outcome, _ = remove_gitignore_lines(gi)
    assert outcome is Outcome.SKIPPED
