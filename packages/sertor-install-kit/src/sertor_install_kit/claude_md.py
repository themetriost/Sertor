"""Marker-delimited block in a host file (e.g. `CLAUDE.md`) — generalized (D4).

Idempotent and non-destructive algorithm: a ritual block is delimited by markers on their own
line; everything **outside** the markers belongs to the user and is preserved byte-for-byte. Three
cases: absent → create with the block only; present without markers → append; present with markers
→ skip.

Generalized over the markers (D4): `write_marker_block(path, content, marker_start, marker_end)`.
The markers are no longer hard-coded, so each consumer passes its own pair: `sertor` (wiki) passes
the `SERTOR:WIKI-RITUAL` markers (behaviour unchanged), `sertor-flow` passes `SERTOR:SDLC-RITUAL`.
The two blocks coexist in the same file, each idempotent on its own markers.
"""
from __future__ import annotations

from pathlib import Path

from sertor_install_kit.artifacts import Outcome


def _wrap(block_content: str, marker_start: str, marker_end: str) -> str:
    """Wraps block content between markers (each marker on its own line)."""
    return f"{marker_start}\n{block_content.rstrip()}\n{marker_end}\n"


def write_marker_block(
    path: Path, content: str, marker_start: str, marker_end: str
) -> Outcome:
    """Writes/leaves untouched a marker-delimited block in `path` (D4).

    Non-destructive guarantee: in the "present" cases, content outside the markers is preserved
    byte-for-byte (read via `read_text(encoding="utf-8")`, no line-ending normalization; the
    existing file is not rewritten if the markers are already there).

    - absent → create the file with the block only → `Outcome.BLOCK`;
    - present, markers absent → append the block at the end (empty separator line) → `BLOCK`;
    - present, markers present → leave everything untouched → `Outcome.SKIPPED`.
    """
    block = _wrap(content, marker_start, marker_end)

    if not path.exists():
        path.write_text(block, encoding="utf-8")
        return Outcome.BLOCK

    existing = path.read_text(encoding="utf-8")
    if marker_start in existing:
        return Outcome.SKIPPED

    # Non-destructive append: one empty separator line, then the block. The pre-existing content
    # is preserved byte-for-byte (we concatenate, not rewrite).
    separator = "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
    path.write_text(existing + separator + block, encoding="utf-8")
    return Outcome.BLOCK
