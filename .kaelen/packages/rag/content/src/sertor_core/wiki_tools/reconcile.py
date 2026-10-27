"""`reconcile`: read-only detection of obsolete pages (FR-008..012, feature 017).

Lists pages with frontmatter `status: superseded` as candidates for obsolescence, along with the
declared successor (`superseded_by`, D6) and the `updated` date. **Never modifies** any file: the
resolution (update/merge/archive) is judgment, on confirmation, outside this command
(Principio VI). Deterministic/offline.
"""
from __future__ import annotations

import logging

from sertor_core.observability.logging import log_event
from sertor_core.wiki_tools.collect import iter_pages
from sertor_core.wiki_tools.contracts import ReconcileResult
from sertor_core.wiki_tools.frontmatter import parse_frontmatter
from sertor_core.wiki_tools.profile import WikiProfile

_SUPERSEDED = "superseded"


def reconcile(profile: WikiProfile) -> ReconcileResult:
    """Candidates for obsolescence = pages with `status: superseded`. Read-only."""
    candidates: list[dict] = []
    for rel_path, full_path in iter_pages(profile):
        try:
            text = full_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            log_event(logging.WARNING, "reconcile", profile=profile.profile, page=rel_path,
                      note="unreadable-skip")
            continue
        fields = parse_frontmatter(text)
        if str(fields.get("status", "")).strip().lower() != _SUPERSEDED:
            continue
        candidates.append({
            "path": rel_path,
            "status": _SUPERSEDED,
            "updated": str(fields.get("updated", "")),
            "superseded_by": str(fields.get("superseded_by", "")),
            "reason": "status: superseded",
        })

    candidates.sort(key=lambda c: c["path"])
    result = ReconcileResult(candidates=candidates, clean=not candidates)
    log_event(logging.INFO, "reconcile", profile=profile.profile,
              candidates=len(candidates), clean=result.clean)
    return result
