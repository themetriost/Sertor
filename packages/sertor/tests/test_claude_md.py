"""Test di `claude_md` (T023, US2): marker idempotente + byte-per-byte fuori dai marker (D4)."""
from __future__ import annotations

from pathlib import Path

from sertor_installer.artifacts import Outcome
from sertor_installer.claude_md import MARKER_END, MARKER_START, write_ritual_block

_BLOCK = "## Rituale\nContenuto del blocco.\n"


def test_absent_creates_with_block_only(tmp_path: Path):
    p = tmp_path / "CLAUDE.md"
    outcome = write_ritual_block(p, _BLOCK)
    assert outcome is Outcome.BLOCK
    text = p.read_text(encoding="utf-8")
    assert text.startswith(MARKER_START)
    assert MARKER_END in text
    assert "Contenuto del blocco." in text


def test_present_without_marker_appends_preserving_prefix(tmp_path: Path):
    p = tmp_path / "CLAUDE.md"
    user = "# Mio progetto\n\nRegole personali.\n"
    p.write_text(user, encoding="utf-8")

    outcome = write_ritual_block(p, _BLOCK)
    assert outcome is Outcome.BLOCK
    text = p.read_text(encoding="utf-8")
    assert text.startswith(user)  # contenuto utente byte-identico in testa
    assert MARKER_START in text


def test_present_with_marker_skips_byte_identical(tmp_path: Path):
    p = tmp_path / "CLAUDE.md"
    write_ritual_block(p, _BLOCK)
    before = p.read_bytes()

    outcome = write_ritual_block(p, _BLOCK)
    assert outcome is Outcome.SKIPPED
    assert p.read_bytes() == before  # file invariato


def test_rerun_no_duplication(tmp_path: Path):
    p = tmp_path / "CLAUDE.md"
    write_ritual_block(p, _BLOCK)
    write_ritual_block(p, _BLOCK)
    write_ritual_block(p, _BLOCK)
    text = p.read_text(encoding="utf-8")
    assert text.count(MARKER_START) == 1
    assert text.count(MARKER_END) == 1


def test_user_content_before_and_after_block_untouched(tmp_path: Path):
    p = tmp_path / "CLAUDE.md"
    # contenuto utente che include il blocco a marker già piazzato + testo dopo
    write_ritual_block(p, _BLOCK)
    with_suffix = p.read_text(encoding="utf-8") + "\n## Sezione utente dopo il blocco\nciao.\n"
    p.write_text(with_suffix, encoding="utf-8")
    before = p.read_bytes()

    # re-run: marker presente → skip, anche il testo dopo resta intatto
    outcome = write_ritual_block(p, _BLOCK)
    assert outcome is Outcome.SKIPPED
    assert p.read_bytes() == before
