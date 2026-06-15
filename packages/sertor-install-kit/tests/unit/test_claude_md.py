"""Tests for `write_marker_block` (T012, D4): parametric markers, idempotent + byte-for-byte."""
from __future__ import annotations

from pathlib import Path

from sertor_install_kit.artifacts import Outcome
from sertor_install_kit.claude_md import write_marker_block

_START = "<!-- SERTOR:SDLC-RITUAL START -->"
_END = "<!-- SERTOR:SDLC-RITUAL END -->"
_BLOCK = "## Rituale\nContenuto del blocco.\n"


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
