"""`move`: moves a wiki page and rewrites incoming links (FR-001..006, feature 017).

Deterministic/offline (D side of the D↔N boundary). Rewrites wikilinks **form-preserving**
(the same forms that `lint` recognises: POSIX path, without extension, stem) preserving
`|alias`/`#anchor`, and **relative** Markdown links that resolve to the moved page. Processes
content pages + the index file; **not** log partitions (append-only history). Order
`rewrite-then-move` with recovery from partial state; collision (destination exists with
source present) → explicit error.
"""
from __future__ import annotations

import logging
import posixpath
import re

from sertor_core.domain.errors import ConfigError
from sertor_core.observability.logging import log_event
from sertor_core.wiki_tools.collect import iter_pages
from sertor_core.wiki_tools.contracts import MoveResult
from sertor_core.wiki_tools.profile import WikiProfile

# Wikilink `[[target(|alias)(#anchor)]]`: group 1 = target, group 2 = suffix (alias/anchor).
# Consistent with `_WIKILINK` in frontmatter.py (RNF-006: move ↔ lint see the same links).
_WIKILINK = re.compile(r"\[\[([^\[\]|#]+)((?:[#|][^\[\]]*)?)\]\]")
# Markdown link `](path)` (captures the content inside the parentheses).
_MDLINK = re.compile(r"\]\(([^)]+)\)")


def _forms(rel: str) -> dict[str, str]:
    """The 3 forms of a wikilink to `rel` (like `lint._link_targets`, but by category)."""
    posix = rel
    no_ext = posix[:-3] if posix.endswith(".md") else posix
    stem = posix.rsplit("/", 1)[-1]
    stem = stem[:-3] if stem.endswith(".md") else stem
    return {"posix": posix, "no_ext": no_ext, "stem": stem}


def _validate_rel(rel: str, label: str) -> str:
    rel = rel.replace("\\", "/").strip()
    if not rel.endswith(".md"):
        raise ConfigError(f"{label} must be a .md page", key=rel)
    if rel.startswith("/") or ".." in rel.split("/"):
        raise ConfigError(f"{label} must be relative to the wiki root", key=rel)
    return rel


def _rewrite(text: str, page_rel: str, src_posix: str, dest_posix: str,
             mapping: dict[str, str]) -> tuple[str, int]:
    """Rewrites wikilinks and relative links that resolve to `src_posix`. Returns (new_text, n)."""
    occ = 0

    def _wl(m: re.Match) -> str:
        nonlocal occ
        target = m.group(1).strip()
        new = mapping.get(target)
        if new is None:
            return m.group(0)
        occ += 1
        return f"[[{new}{m.group(2)}]]"

    text = _WIKILINK.sub(_wl, text)

    page_dir = posixpath.dirname(page_rel)

    def _md(m: re.Match) -> str:
        nonlocal occ
        raw = m.group(1).strip()
        if "://" in raw or raw.startswith(("#", "/", "<", "mailto:")):
            return m.group(0)
        base, sep, frag = raw.partition("#")
        if not base:
            return m.group(0)
        resolved = posixpath.normpath(posixpath.join(page_dir, base)) if page_dir else \
            posixpath.normpath(base)
        if resolved != src_posix:
            return m.group(0)
        occ += 1
        new_rel = posixpath.relpath(dest_posix, page_dir) if page_dir else dest_posix
        return f"]({new_rel}{sep}{frag})"

    text = _MDLINK.sub(_md, text)
    return text, occ


def move(profile: WikiProfile, src: str, dest: str, dry_run: bool = False) -> MoveResult:
    """Moves `src`→`dest` (relative to the wiki root) and rewrites all incoming links.

    States (D5): src+!dest = move; src+dest = collision (error, REQ-013); !src+dest =
    recovery (only completes rewrites, REQ-014); !src+!dest = source not found.
    """
    src = _validate_rel(src, "sorgente")
    dest = _validate_rel(dest, "destinazione")
    root = profile.root_path
    src_path = root / src
    dest_path = root / dest
    src_exists = src_path.is_file()
    dest_exists = dest_path.is_file()

    if not src_exists and not dest_exists:
        raise ConfigError("source page not found", key=src)
    if src_exists and dest_exists and src != dest:
        raise ConfigError("destination already exists (no overwrite)", key=dest)

    old, new = _forms(src), _forms(dest)
    mapping = {old[k]: new[k] for k in ("posix", "no_ext", "stem")}

    # Files to scan: content pages + index; never log partitions (D3).
    targets = list(iter_pages(profile))
    if profile.index_path.is_file():
        targets.append((profile.index_file, profile.index_path))

    rewritten: list[dict] = []
    for rel, full in targets:
        try:
            text = full.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            log_event(logging.WARNING, "move", profile=profile.profile, page=rel,
                      note="unreadable-skip")
            continue
        new_text, occ = _rewrite(text, rel, src, dest, mapping)
        if occ and new_text != text:
            if not dry_run:
                full.write_text(new_text, encoding="utf-8")
            rewritten.append({"page": rel, "occurrences": occ})

    moved = False
    if src_exists and not dest_exists:
        if not dry_run:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            src_path.rename(dest_path)
        moved = True

    log_event(logging.INFO, "move", profile=profile.profile, source=src, destination=dest,
              rewritten=len(rewritten), moved=moved, dry_run=dry_run)
    return MoveResult(source=src, destination=dest, rewritten=rewritten, moved=moved,
                      dry_run=dry_run)
