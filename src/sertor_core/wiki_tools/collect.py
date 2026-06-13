"""`collect`: wiki page enumeration + metadata, without body (FR-007).

Returns a structured map (`wiki.collect/1`) with, for each page, the relative POSIX path
(stable identity, FR-009/REQ-051), the taxonomy area, type/title/tags from the frontmatter and
outgoing wikilinks. The **full content** is never included. `iter_pages` is reused by `lint`,
`validate` and `structure` to share the enumeration.
"""
from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

from sertor_core.observability.logging import log_event
from sertor_core.wiki_tools.contracts import CollectResult
from sertor_core.wiki_tools.frontmatter import (
    extract_wikilinks,
    has_frontmatter,
    parse_frontmatter,
)
from sertor_core.wiki_tools.profile import WikiProfile


def iter_pages(profile: WikiProfile) -> Iterator[tuple[str, Path]]:
    """Iterates `(rel_path_posix, full_path)` for every `.md` page under the wiki root.

    Excludes the index file and the log file (they are not content pages). Order is
    deterministic (sorted by rel_path) to guarantee repeatable output (SC-002).
    """
    root = profile.root_path
    if not root.is_dir():
        return
    reserved = {profile.index_file, profile.log_file}
    log_dir = profile.log_dir  # log partition directory (append-only, not content pages)
    pages: list[tuple[str, Path]] = []
    for path in root.rglob("*.md"):
        rel = path.relative_to(root)
        # Index and log live at the wiki root: they are not content pages.
        if len(rel.parts) == 1 and rel.name in reserved:
            continue
        # Log partitions (rotation, FEAT-008) are append-only files, not pages: exclude them.
        if log_dir and rel.parts[0] == log_dir:
            continue
        pages.append((rel.as_posix(), path))
    pages.sort(key=lambda t: t[0])
    yield from pages


def _area_of(rel_path: str, profile: WikiProfile) -> str:
    head = rel_path.split("/", 1)[0]
    for entry in profile.taxonomy:
        if entry.dir == head:
            return entry.name
    return head


def _page_meta(rel_path: str, full_path: Path, profile: WikiProfile) -> dict:
    try:
        text = full_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        log_event(
            logging.WARNING, "collect", profile=profile.profile,
            page=rel_path, note="unreadable-skip",
        )
        text = ""
    fields = parse_frontmatter(text)
    tags = fields.get("tags")
    return {
        "rel_path": rel_path,
        "area": _area_of(rel_path, profile),
        "type": str(fields.get("type", "")),
        "title": str(fields.get("title", "")),
        "tags": list(tags) if isinstance(tags, list) else ([str(tags)] if tags else []),
        "status": str(fields.get("status", "")),  # feature 017: additive, forward-compatible
        "frontmatter_present": has_frontmatter(text),
        "wikilinks": extract_wikilinks(text),
    }


def collect(profile: WikiProfile) -> CollectResult:
    """Enumerates wiki pages with metadata; no body content (FR-007)."""
    pages = [_page_meta(rel, full, profile) for rel, full in iter_pages(profile)]
    result = CollectResult(
        root=profile.root,
        index=profile.index_file,
        log=profile.log_file,
        pages=pages,
    )
    log_event(logging.INFO, "collect", profile=profile.profile, pages=len(pages))
    return result
