"""`init_structure` and `validate`: non-destructive structure + conventions (FR-003/004, SC-006).

`init_structure` creates taxonomy directories + index/log with minimal content, without
overwriting any pre-existing file (idempotent, non-destructive — SC-006). `validate` checks
the mechanical page conventions (required frontmatter, kebab-case naming, area) and reports
non-conformances in the `wiki.lint/1` schema.
"""
from __future__ import annotations

import logging
import re

from sertor_core.observability.logging import log_event
from sertor_core.wiki_tools.collect import iter_pages
from sertor_core.wiki_tools.contracts import LintResult, StructureResult
from sertor_core.wiki_tools.frontmatter import missing_required, parse_frontmatter
from sertor_core.wiki_tools.profile import WikiProfile

_KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\.md$")

# Seed localisation (D3): index/log are wiki CONTENT → they follow `profile.language`.
# English is the canonical fallback for languages not in the table (host-agnostic: selection is
# driven by config, not assumed). Only the two descriptive sentences; headings come from config.
_SEED_STRINGS: dict[str, dict[str, str]] = {
    "en": {"index": "Wiki index. Updated by the log operations.", "log": "Append-only wiki log."},
    "it": {
        "index": "Indice del wiki. Aggiornato dalle operazioni di registro.",
        "log": "Registro append-only del wiki.",
    },
}
_SEED_FALLBACK = "en"


def _seed_strings(profile: WikiProfile) -> dict[str, str]:
    """Seed strings in the host language (`en`/`it`); English fallback (e.g. `it-IT` → `it`)."""
    lang = profile.language.lower().split("-")[0]
    return _SEED_STRINGS.get(lang, _SEED_STRINGS[_SEED_FALLBACK])


def _index_seed(profile: WikiProfile) -> str:
    return f"# {profile.root}\n\n{_seed_strings(profile)['index']}\n"


def _log_seed(profile: WikiProfile) -> str:
    return f"# {profile.log_file}\n\n{_seed_strings(profile)['log']}\n"


def init_structure(profile: WikiProfile) -> StructureResult:
    """Creates taxonomy directories + index/log; leaves everything that already exists untouched.

    Idempotent: a second run on an already-initialised wiki creates or modifies nothing
    (everything ends up in `skipped_existing`).
    """
    created: list[str] = []
    skipped: list[str] = []

    root = profile.root_path
    if root.is_dir():
        skipped.append(profile.root)
    else:
        root.mkdir(parents=True, exist_ok=True)
        created.append(profile.root)

    for entry in profile.taxonomy:
        target = root / entry.dir
        if target.is_dir():
            skipped.append(entry.dir)
        else:
            target.mkdir(parents=True, exist_ok=True)
            created.append(entry.dir)

    for path, seed, label in (
        (profile.index_path, _index_seed(profile), profile.index_file),
        (profile.log_path, _log_seed(profile), profile.log_file),
    ):
        if path.exists():
            skipped.append(label)  # non-destructive: never overwrite user files (SC-006)
        else:
            path.write_text(seed, encoding="utf-8")
            created.append(label)

    result = StructureResult(created=created, skipped_existing=skipped)
    log_event(
        logging.INFO,
        "structure",
        profile=profile.profile,
        created=len(created),
        skipped_existing=len(skipped),
    )
    return result


def validate(profile: WikiProfile) -> LintResult:
    """Validates page conventions: required frontmatter + kebab-case naming (FR-004)."""
    missing_frontmatter: list[dict] = []
    naming_violations: list[dict] = []

    for rel_path, full_path in iter_pages(profile):
        try:
            text = full_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            log_event(
                logging.WARNING, "validate", profile=profile.profile,
                page=rel_path, note="unreadable-skip",
            )
            continue
        fields = parse_frontmatter(text)
        missing = missing_required(fields, profile.frontmatter_required)
        if missing:
            missing_frontmatter.append({"page": rel_path, "missing": missing})
        if not _KEBAB.match(full_path.name):
            naming_violations.append({"page": rel_path, "reason": "not-kebab-case"})

    result = LintResult(
        missing_frontmatter=missing_frontmatter,
        naming_violations=naming_violations,
    )
    log_event(
        logging.INFO,
        "validate",
        profile=profile.profile,
        missing_frontmatter=len(missing_frontmatter),
        naming_violations=len(naming_violations),
    )
    return result
