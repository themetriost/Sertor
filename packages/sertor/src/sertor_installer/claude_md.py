"""Marker-delimited block in `CLAUDE.md` (D4, contracts/claude-md-block.md).

Idempotent and non-destructive algorithm: the step-ritual block is delimited by markers on their
own line; everything **outside** the markers belongs to the user and is preserved byte-for-byte.
Three cases: absent → create with the block only; present without markers → append; present with
markers → skip.
"""
from __future__ import annotations

from pathlib import Path

from sertor_installer.artifacts import Outcome

MARKER_START = "<!-- SERTOR:WIKI-RITUAL START -->"
MARKER_END = "<!-- SERTOR:WIKI-RITUAL END -->"


def _wrap(block_content: str) -> str:
    """Wraps block content between markers (each marker on its own line)."""
    return f"{MARKER_START}\n{block_content.rstrip()}\n{MARKER_END}\n"


def write_ritual_block(claude_md_path: Path, block_content: str) -> Outcome:
    """Writes/leaves untouched the step-ritual block in `CLAUDE.md` (D4).

    Non-destructive guarantee: in the "present" cases, content outside the markers is preserved
    byte-for-byte (read via `read_text(encoding="utf-8")`, no line-ending normalization;
    the existing file is not rewritten if the markers are already there).

    - absent → create the file with the block only → `Outcome.BLOCK`;
    - present, markers absent → append the block at the end (empty separator line) → `BLOCK`;
    - present, markers present → leave everything untouched → `Outcome.SKIPPED`.
    """
    block = _wrap(block_content)

    if not claude_md_path.exists():
        claude_md_path.write_text(block, encoding="utf-8")
        return Outcome.BLOCK

    existing = claude_md_path.read_text(encoding="utf-8")
    if MARKER_START in existing:
        return Outcome.SKIPPED

    # Non-destructive append: one empty separator line, then the block. The pre-existing content
    # is preserved byte-for-byte (we concatenate, not rewrite).
    separator = "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
    claude_md_path.write_text(existing + separator + block, encoding="utf-8")
    return Outcome.BLOCK
