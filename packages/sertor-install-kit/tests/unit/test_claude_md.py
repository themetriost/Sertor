"""Tests for `write_marker_block` (T012, D4): parametric markers, idempotent + byte-for-byte."""
from __future__ import annotations

from pathlib import Path

import pytest

from sertor_install_kit.artifacts import Outcome
from sertor_install_kit.claude_md import (
    remove_marker_block,
    update_marker_block,
    write_marker_block,
)
from sertor_install_kit.errors import MarkerBlockCorruptError

_START = "<!-- SERTOR:SDLC-RITUAL START -->"
_END = "<!-- SERTOR:SDLC-RITUAL END -->"
_BLOCK = "## Rituale\nContenuto del blocco.\n"


def test_corrupt_block_start_without_end_fails_loud(tmp_path: Path):
    # A-16: a start marker without its matching end (truncated/tampered block) FAILS LOUD on every
    # operation, instead of silently skipping and trapping the block forever (Principio XII).
    p = tmp_path / "CLAUDE.md"
    p.write_text(f"# User\n\n{_START}\nhalf a block, end marker lost\n", encoding="utf-8")
    with pytest.raises(MarkerBlockCorruptError):
        remove_marker_block(p, _START, _END)
    with pytest.raises(MarkerBlockCorruptError):
        write_marker_block(p, _BLOCK, _START, _END)
    with pytest.raises(MarkerBlockCorruptError):
        update_marker_block(p, _BLOCK, _START, _END)


def test_corrupt_block_end_without_start_fails_loud(tmp_path: Path):
    p = tmp_path / "CLAUDE.md"
    p.write_text(f"# User\n\nstray end only\n{_END}\n", encoding="utf-8")
    with pytest.raises(MarkerBlockCorruptError):
        remove_marker_block(p, _START, _END)


def test_wellformed_block_not_flagged_corrupt(tmp_path: Path):
    # Sanity: a normal (both markers, ordered) block round-trips without a false corruption raise.
    p = tmp_path / "CLAUDE.md"
    write_marker_block(p, _BLOCK, _START, _END)
    assert write_marker_block(p, _BLOCK, _START, _END) is Outcome.SKIPPED
    assert remove_marker_block(p, _START, _END) is Outcome.REMOVED


def test_absent_creates_with_block_only(tmp_path: Path):
    p = tmp_path / "CLAUDE.md"
    outcome = write_marker_block(p, _BLOCK, _START, _END)
    assert outcome is Outcome.BLOCK
    text = p.read_text(encoding="utf-8")
    assert text.startswith(_START)
    assert _END in text
    assert "Contenuto del blocco." in text


def test_present_without_marker_appends_preserving_prefix(tmp_path: Path):
    p = tmp_path / "CLAUDE.md"
    user = "# Mio progetto\n\nRegole personali.\n"
    p.write_text(user, encoding="utf-8")

    outcome = write_marker_block(p, _BLOCK, _START, _END)
    assert outcome is Outcome.BLOCK
    text = p.read_text(encoding="utf-8")
    assert text.startswith(user)  # user content byte-identical at the top
    assert _START in text


def test_present_with_marker_skips_byte_identical(tmp_path: Path):
    p = tmp_path / "CLAUDE.md"
    write_marker_block(p, _BLOCK, _START, _END)
    before = p.read_bytes()

    outcome = write_marker_block(p, _BLOCK, _START, _END)
    assert outcome is Outcome.SKIPPED
    assert p.read_bytes() == before


def test_rerun_no_duplication(tmp_path: Path):
    p = tmp_path / "CLAUDE.md"
    write_marker_block(p, _BLOCK, _START, _END)
    write_marker_block(p, _BLOCK, _START, _END)
    write_marker_block(p, _BLOCK, _START, _END)
    text = p.read_text(encoding="utf-8")
    assert text.count(_START) == 1
    assert text.count(_END) == 1


def test_two_distinct_marker_blocks_coexist(tmp_path: Path):
    """Two different marker pairs (wiki + sdlc) coexist, each idempotent on its own markers (D4)."""
    p = tmp_path / "CLAUDE.md"
    wiki_start = "<!-- SERTOR:WIKI-RITUAL START -->"
    wiki_end = "<!-- SERTOR:WIKI-RITUAL END -->"

    write_marker_block(p, "wiki body", wiki_start, wiki_end)
    write_marker_block(p, "sdlc body", _START, _END)
    text = p.read_text(encoding="utf-8")
    assert wiki_start in text and _START in text
    assert "wiki body" in text and "sdlc body" in text

    # re-run of the SDLC block: skipped, wiki block untouched
    before = p.read_bytes()
    outcome = write_marker_block(p, "sdlc body", _START, _END)
    assert outcome is Outcome.SKIPPED
    assert p.read_bytes() == before


# --- feature 048: remove_marker_block / update_marker_block (T012) ------------------------------


def test_remove_marker_block_strips_only_block(tmp_path: Path):
    p = tmp_path / "CLAUDE.md"
    before_user = "# Mio progetto\n\nRegole personali.\n"
    after_user = "\n## Sezione utente in coda\nTesto.\n"
    p.write_text(before_user, encoding="utf-8")
    write_marker_block(p, _BLOCK, _START, _END)
    # append more user content AFTER the block
    p.write_text(p.read_text(encoding="utf-8") + after_user, encoding="utf-8")

    outcome = remove_marker_block(p, _START, _END)
    assert outcome is Outcome.REMOVED
    text = p.read_text(encoding="utf-8")
    assert _START not in text and _END not in text
    assert before_user in text
    assert "Sezione utente in coda" in text


def test_remove_marker_block_absent_markers_skips(tmp_path: Path):
    p = tmp_path / "CLAUDE.md"
    user = "# Solo utente\nNiente blocco Sertor.\n"
    p.write_text(user, encoding="utf-8")
    before = p.read_bytes()

    outcome = remove_marker_block(p, _START, _END)
    assert outcome is Outcome.SKIPPED
    assert p.read_bytes() == before


def test_remove_marker_block_missing_file_skips(tmp_path: Path):
    p = tmp_path / "CLAUDE.md"
    assert remove_marker_block(p, _START, _END) is Outcome.SKIPPED


def test_remove_marker_block_idempotent(tmp_path: Path):
    p = tmp_path / "CLAUDE.md"
    p.write_text("# Header\n\n", encoding="utf-8")
    write_marker_block(p, _BLOCK, _START, _END)
    remove_marker_block(p, _START, _END)
    second = remove_marker_block(p, _START, _END)
    assert second is Outcome.SKIPPED


def test_remove_marker_block_only_content_removes_file(tmp_path: Path):
    p = tmp_path / "CLAUDE.md"
    write_marker_block(p, _BLOCK, _START, _END)  # file = block only
    outcome = remove_marker_block(p, _START, _END)
    assert outcome is Outcome.REMOVED
    assert not p.exists()


def test_update_marker_block_replaces_when_differs(tmp_path: Path):
    p = tmp_path / "CLAUDE.md"
    user = "# Mio progetto\n\nRegole.\n"
    p.write_text(user, encoding="utf-8")
    write_marker_block(p, _BLOCK, _START, _END)

    outcome = update_marker_block(p, "## Rituale\nContenuto NUOVO.\n", _START, _END)
    assert outcome is Outcome.UPDATED
    text = p.read_text(encoding="utf-8")
    assert "Contenuto NUOVO." in text
    assert "Contenuto del blocco." not in text
    assert user in text  # outside the markers untouched


def test_update_marker_block_skips_when_equal(tmp_path: Path):
    p = tmp_path / "CLAUDE.md"
    write_marker_block(p, _BLOCK, _START, _END)
    before = p.read_bytes()
    outcome = update_marker_block(p, _BLOCK, _START, _END)
    assert outcome is Outcome.SKIPPED
    assert p.read_bytes() == before


def test_update_marker_block_absent_delegates_to_write(tmp_path: Path):
    p = tmp_path / "CLAUDE.md"
    p.write_text("# Solo utente\n", encoding="utf-8")
    outcome = update_marker_block(p, _BLOCK, _START, _END)
    assert outcome is Outcome.BLOCK
    assert _START in p.read_text(encoding="utf-8")
