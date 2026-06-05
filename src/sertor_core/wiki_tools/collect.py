"""`collect`: enumerazione delle pagine del wiki + metadati, senza corpo (FR-007).

Restituisce una mappa strutturata (`wiki.collect/1`) con, per ogni pagina, il percorso relativo
POSIX (identità stabile, FR-009/REQ-051), l'area di tassonomia, tipo/titolo/tag dal frontmatter e i
wikilink uscenti. Il **contenuto integrale** non è mai incluso. `iter_pages` è riusata da `lint`,
`validate` e `structure` per condividere l'enumerazione.
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
    """Itera `(rel_path_posix, full_path)` per ogni pagina `.md` sotto la radice del wiki.

    Esclude il file indice e il file di registro (non sono pagine di contenuto). L'ordine è
    deterministico (ordinamento per rel_path) per garantire output ripetibili (SC-002).
    """
    root = profile.root_path
    if not root.is_dir():
        return
    reserved = {profile.index_file, profile.log_file}
    pages: list[tuple[str, Path]] = []
    for path in root.rglob("*.md"):
        rel = path.relative_to(root)
        # Indice e registro stanno alla radice del wiki: non sono pagine di contenuto.
        if len(rel.parts) == 1 and rel.name in reserved:
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
        "frontmatter_present": has_frontmatter(text),
        "wikilinks": extract_wikilinks(text),
    }


def collect(profile: WikiProfile) -> CollectResult:
    """Enumera le pagine del wiki con i metadati; nessun corpo (FR-007)."""
    pages = [_page_meta(rel, full, profile) for rel, full in iter_pages(profile)]
    result = CollectResult(
        root=profile.root,
        index=profile.index_file,
        log=profile.log_file,
        pages=pages,
    )
    log_event(logging.INFO, "collect", profile=profile.profile, pages=len(pages))
    return result
