"""`reconcile`: detection (sola lettura) delle pagine obsolete (FR-008..012, feature 017).

Elenca le pagine con frontmatter `status: superseded` come candidate all'obsolescenza, con il
successore dichiarato (`superseded_by`, D6) e la data `updated`. **Non modifica mai** alcun file: la
risoluzione (aggiornare/fondere/archiviare) è giudizio, su conferma, fuori da questo comando
(Principio VI). Deterministico/offline.
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
    """Candidate all'obsolescenza = pagine con `status: superseded`. Read-only."""
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
