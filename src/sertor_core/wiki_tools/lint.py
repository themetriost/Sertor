"""`lint`: lint strutturale meccanico del wiki (FR-006, SC-004).

Rileva **solo** difetti strutturali — link interni rotti, pagine orfane, frontmatter
mancante/incompleto — **senza** alcun giudizio semantico (le contraddizioni e i claim superati
sono giudizio LLM, FEAT-003-N). Deterministico e ripetibile (SC-005): nessuna rete, nessun LLM.
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
    """Forme con cui un wikilink può riferirsi a questa pagina (con/senza estensione, stem)."""
    posix = rel_path
    no_ext = posix[:-3] if posix.endswith(".md") else posix
    stem = posix.rsplit("/", 1)[-1]
    stem = stem[:-3] if stem.endswith(".md") else stem
    return {posix, no_ext, stem}


def lint(profile: WikiProfile) -> LintResult:
    """Lint strutturale: link rotti, orfani, frontmatter mancante (FR-006)."""
    pages: dict[str, str] = {}  # rel_path -> testo
    for rel_path, full_path in iter_pages(profile):
        try:
            pages[rel_path] = full_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            log_event(
                logging.WARNING, "lint", profile=profile.profile,
                page=rel_path, note="unreadable-skip",
            )

    # Mappa di tutti i bersagli risolvibili a una pagina esistente.
    target_index: dict[str, str] = {}
    for rel_path in pages:
        for alias in _link_targets(rel_path):
            target_index.setdefault(alias, rel_path)

    # Riferimenti dell'indice: una pagina linkata dall'indice non è orfana.
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

    for rel_path, text in pages.items():
        fields = parse_frontmatter(text)
        missing = missing_required(fields, profile.frontmatter_required)
        if missing:
            missing_frontmatter.append({"page": rel_path, "missing": missing})
        for target in extract_wikilinks(text):
            resolved = target_index.get(target)
            if resolved is None:
                broken_links.append({"page": rel_path, "target": target})
            elif resolved != rel_path:
                referenced.add(resolved)  # link page→page: il bersaglio non è orfano

    orphans = sorted(rel for rel in pages if rel not in referenced)

    result = LintResult(
        broken_links=sorted(broken_links, key=lambda d: (d["page"], d["target"])),
        orphans=orphans,
        missing_frontmatter=sorted(missing_frontmatter, key=lambda d: d["page"]),
    )
    log_event(
        logging.INFO,
        "lint",
        profile=profile.profile,
        broken_links=len(result.broken_links),
        orphans=len(result.orphans),
        missing_frontmatter=len(result.missing_frontmatter),
    )
    return result
