"""`scan`: pending-work detection via mtime (FR-005, research D3).

Compares the `mtime` of files in the profile's `source_dirs` (with config exclusions) against
the time anchor of the last log entry. Host-agnostic: works on non-git hosts too (no git
dependency; git-driven refresh is the responsibility of FEAT-003-N). Replicates the logic of
the current `wiki-pending-check.ps1` (SC-003) for count parity.
"""
from __future__ import annotations

import fnmatch
import logging
from datetime import datetime
from pathlib import Path

from sertor_core.observability.logging import log_event
from sertor_core.wiki_tools.contracts import ScanResult
from sertor_core.wiki_tools.profile import WikiProfile


def _is_excluded(rel_parts: tuple[str, ...], patterns: list[str]) -> bool:
    """`True` if any path segment matches an exclusion pattern (glob)."""
    for part in rel_parts:
        for pattern in patterns:
            if fnmatch.fnmatch(part, pattern):
                return True
    return False


def _file_mtime(path: Path) -> float | None:
    """mtime of a non-empty file (None if absent/empty/unreadable)."""
    if not path.is_file():
        return None
    try:
        if path.stat().st_size == 0:
            return None
        return path.stat().st_mtime
    except OSError:
        return None


def _latest_log_mtime(profile: WikiProfile) -> float | None:
    """Time anchor of the last log entry.

    Rotation active → mtime of the **most recent partition** (max over `YYYY-MM-DD.md` files,
    excluding the index). Single-file mode (back-compat) → mtime of the single log file. In both
    cases: absent/empty → `None` (everything is pending). The `wiki.scan/1` contract is unchanged.
    """
    if profile.rotation_enabled:
        log_dir = profile.log_dir_path
        if not log_dir.is_dir():
            return None
        mtimes = [
            m
            for p in log_dir.glob("*.md")
            if p.name != profile.log_index_file
            and (m := _file_mtime(p)) is not None
        ]
        return max(mtimes) if mtimes else None
    return _file_mtime(profile.log_path)


def scan(profile: WikiProfile) -> ScanResult:
    """Counts source files newer than the last log entry.

    Absent `anchor` (missing/empty log) → everything is pending. `message` comes from the
    profile's localised `strings` (`{n}` replaced with the count).
    """
    anchor = _latest_log_mtime(profile)
    anchor_iso = (
        datetime.fromtimestamp(anchor).isoformat(timespec="seconds")
        if anchor is not None
        else None
    )

    dirs_scanned: list[str] = []
    pending = 0
    for source in profile.source_dirs:
        base = profile.config_dir / source
        if not base.is_dir():
            continue
        dirs_scanned.append(source)
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(base)
            if _is_excluded(rel.parts, profile.exclude):
                continue
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            if anchor is None or mtime > anchor:
                pending += 1

    template = profile.strings.get(
        "pending" if pending else "clean",
        "{n} file(s) newer than the last log entry."
        if pending
        else "No files newer than the last log entry.",
    )
    message = template.replace("{n}", str(pending))

    result = ScanResult(
        pending=pending,
        anchor=anchor_iso,
        dirs_scanned=dirs_scanned,
        message=message,
    )
    log_event(
        logging.INFO,
        "scan",
        profile=profile.profile,
        pending=pending,
        anchor=anchor_iso,
        dirs_scanned=len(dirs_scanned),
    )
    return result
