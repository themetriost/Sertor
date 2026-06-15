"""Wiki ritual block in `CLAUDE.md` — thin wrapper over the kit's `write_marker_block` (037, D4).

The generic marker-block writer migrated to `sertor-install-kit` (`write_marker_block(path,
content, marker_start, marker_end)`). `sertor` (wiki) binds the historical `SERTOR:WIKI-RITUAL`
markers and preserves the `write_ritual_block(path, content)` API used by its code and tests; the
behaviour is byte-for-byte unchanged.
"""
from __future__ import annotations

from pathlib import Path

from sertor_install_kit.artifacts import Outcome
from sertor_install_kit.claude_md import write_marker_block

MARKER_START = "<!-- SERTOR:WIKI-RITUAL START -->"
MARKER_END = "<!-- SERTOR:WIKI-RITUAL END -->"


def write_ritual_block(claude_md_path: Path, block_content: str) -> Outcome:
    """Writes/leaves untouched the wiki step-ritual block in `CLAUDE.md` (D4).

    Delegates to the kit's `write_marker_block` with the wiki markers (`SERTOR:WIKI-RITUAL`).
    """
    return write_marker_block(claude_md_path, block_content, MARKER_START, MARKER_END)
