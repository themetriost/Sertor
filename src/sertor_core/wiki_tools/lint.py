"""`lint`: mechanical structural lint of the wiki (FR-006, SC-004).

Detects **only** structural defects — broken internal links, orphan pages, missing/incomplete
frontmatter — **without** any semantic judgment (contradictions and superseded claims are LLM
judgment, FEAT-003-N). Deterministic and repeatable (SC-005): no network, no LLM.
"""
from __future__ import annotations

import logging

from sertor_core.observability.logging import log_event
from sertor_core.wiki_tools.collect import iter_pages
from sertor_core.wiki_tools.contracts import LintResult
from sertor_core.wiki_tools.frontmatter import (
    extract_wikilinks,
    missing_required,
    parse_frontmatter,
)
from sertor_core.wiki_tools.profile import WikiProfile


def _link_targets(rel_path: str) -> set[str]:
    """Forms by which a wikilink can refer to this page (with/without extension, stem)."""
    posix = rel_path
    no_ext = posix[:-3] if posix.endswith(".md") else posix
    stem = posix.rsplit("/", 1)[-1]
    stem = stem[:-3] if stem.endswith(".md") else stem
    return {posix, no_ext, stem}


def lint(profile: WikiProfile) -> LintResult:
    """Structural lint: broken links, orphans, missing frontmatter (FR-006)."""
    pages: dict[str, str] = {}  # rel_path -> testo
    for rel_path, full_path in iter_pages(profile):
        try:
            pages[rel_path] = full_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            log_event(
                logging.WARNING, "lint", profile=profile.profile,
                page=rel_path, note="unreadable-skip",
            )

    # Map of all targets resolvable to an existing page.
    target_index: dict[str, str] = {}
    for rel_path in pages:
        for alias in _link_targets(rel_path):
            target_index.setdefault(alias, rel_path)

    # Index references: a page linked from the index is not an orphan.
    index_text = ""
    if profile.index_path.is_file():
        try:
            index_text = profile.index_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            index_text = ""
    referenced: set[str] = set()
    for target in extract_wikilinks(index_text):
        resolved = target_index.get(target)
        if resolved:
            referenced.add(resolved)

    broken_links: list[dict] = []
    missing_frontmatter: list[dict] = []
    stubs: list[str] = []

    for rel_path, text in pages.items():
        fields = parse_frontmatter(text)
        if str(fields.get("status", "")).strip().lower() == "stub":
            stubs.append(rel_path)
        missing = missing_required(fields, profile.frontmatter_required)
        if missing:
            missing_frontmatter.append({"page": rel_path, "missing": missing})
        for target in extract_wikilinks(text):
            resolved = target_index.get(target)
            if resolved is None:
                broken_links.append({"page": rel_path, "target": target})
            elif resolved != rel_path:
                referenced.add(resolved)  # page→page link: the target is not an orphan

    orphans = sorted(rel for rel in pages if rel not in referenced)

    result = LintResult(
        broken_links=sorted(broken_links, key=lambda d: (d["page"], d["target"])),
        orphans=orphans,
        missing_frontmatter=sorted(missing_frontmatter, key=lambda d: d["page"]),
        stubs=sorted(stubs),
    )
    log_event(
        logging.INFO,
        "lint",
        profile=profile.profile,
        broken_links=len(result.broken_links),
        orphans=len(result.orphans),
        missing_frontmatter=len(result.missing_frontmatter),
        stubs=len(result.stubs),
    )
    return result
