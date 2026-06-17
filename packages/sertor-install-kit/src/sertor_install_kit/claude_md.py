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
        path.parent.mkdir(parents=True, exist_ok=True)
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


def _split_around_block(
    existing: str, marker_start: str, marker_end: str
) -> tuple[str, str] | None:
    """Splits `existing` into (before, after) around the marker block (markers + content removed).

    Returns `None` if the start/end markers are not both present in order. The split is byte-exact:
    `before + after` is the file content with ONLY the block (and its surrounding-but-owned newline)
    stripped. The leading newline that separated the block from the preceding content is removed so
    a re-install/remove round-trip is stable.
    """
    start = existing.find(marker_start)
    if start == -1:
        return None
    end = existing.find(marker_end, start)
    if end == -1:
        return None
    end += len(marker_end)
    # Absorb the trailing newline that closes the marker_end line (write_marker_block ends "\n").
    if end < len(existing) and existing[end] == "\n":
        end += 1
    before = existing[:start]
    after = existing[end:]
    # The block was appended after a separator ("\n" or "\n\n"): drop one trailing newline from
    # `before` so removing the block does not leave a dangling blank line (byte-for-byte symmetry
    # with write_marker_block's separator). Only when `before` is non-empty user content.
    if before.endswith("\n\n"):
        before = before[:-1]
    return before, after


def remove_marker_block(path: Path, marker_start: str, marker_end: str) -> Outcome:
    """Removes ONLY the marker-delimited block from `path` — inverse of `write_marker_block`.

    Everything outside the markers is preserved byte-for-byte. If the markers are absent (the user
    deleted the block, or the file does not exist), it is a no-op observable as `Outcome.SKIPPED`
    (idempotency, FR-026). If, after removal, the file is empty (the block was the only content),
    the file is deleted (`Outcome.REMOVED`).
    """
    if not path.exists():
        return Outcome.SKIPPED
    existing = path.read_text(encoding="utf-8")
    parts = _split_around_block(existing, marker_start, marker_end)
    if parts is None:
        return Outcome.SKIPPED
    before, after = parts
    remaining = before + after
    if remaining.strip() == "":
        # The block was the entire file → remove it (the file existed only for the block).
        path.unlink()
        return Outcome.REMOVED
    path.write_text(remaining, encoding="utf-8")
    return Outcome.REMOVED


def update_marker_block(
    path: Path, content: str, marker_start: str, marker_end: str
) -> Outcome:
    """Updates the marker-delimited block in `path` if the bundled content differs — inverse-aware.

    - markers present, block region differs from the freshly-wrapped `content` → replace JUST the
      block region in place (`UPDATED`), preserving everything outside the markers byte-for-byte;
    - markers present, block region equal → `SKIPPED`;
    - markers absent (or file missing) → delegate to `write_marker_block` (creates/appends →
      `BLOCK`).

    The replacement is an exact slice swap (`existing[:start] + new_block_region +
    existing[end:]`): the bytes before `marker_start` and after `marker_end` are untouched.
    """
    if not path.exists():
        return write_marker_block(path, content, marker_start, marker_end)
    existing = path.read_text(encoding="utf-8")
    start = existing.find(marker_start)
    if start == -1:
        return write_marker_block(path, content, marker_start, marker_end)
    end = existing.find(marker_end, start)
    if end == -1:
        return write_marker_block(path, content, marker_start, marker_end)
    end += len(marker_end)
    new_region = _wrap(content, marker_start, marker_end).rstrip("\n")
    if existing[start:end] == new_region:
        return Outcome.SKIPPED
    rebuilt = existing[:start] + new_region + existing[end:]
    path.write_text(rebuilt, encoding="utf-8")
    return Outcome.UPDATED
