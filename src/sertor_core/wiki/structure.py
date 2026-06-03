"""Inizializzazione non-distruttiva della struttura del wiki (REQ-001/002)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from sertor_core.observability.logging import log_event
from sertor_core.wiki.conventions import THEMATIC_DIRS, log_entry, today_str

_INDEX_HEADER = (
    "---\ntitle: Indice del Wiki\ntype: index\ntags: [wiki, index]\n"
    "created: {date}\nupdated: {date}\nsources: []\n---\n\n"
    "# Wiki\n\nCatalogo delle pagine. Aggiornato a ogni operazione.\n\n## Pagine\n\n"
)
_LOG_HEADER = "# Log del Wiki\n\nRegistro append-only delle operazioni.\n\n"


@dataclass
class WikiOpResult:
    """Esito di un'operazione del wiki (osservabilità + idempotenza)."""

    operation: str
    page_path: str | None = None
    changed: bool = False
    log_appended: bool = False


def create_wiki(root: Path | str, today: str | None = None) -> WikiOpResult:
    """Crea la struttura del wiki se assente; non sovrascrive un wiki esistente.

    Cartelle tematiche create se mancanti (idempotente). `index.md`/`log.md` scritti **solo** se
    assenti: un wiki esistente resta intatto (REQ-002).
    """
    root = Path(root)
    today = today or today_str()
    root.mkdir(parents=True, exist_ok=True)
    for d in THEMATIC_DIRS:
        (root / d).mkdir(exist_ok=True)

    changed = False
    index = root / "index.md"
    if not index.exists():
        index.write_text(_INDEX_HEADER.format(date=today), encoding="utf-8")
        changed = True
    log = root / "log.md"
    if not log.exists():
        log.write_text(_LOG_HEADER + log_entry(today, "setup", "Inizializzazione del wiki"),
                       encoding="utf-8")
        changed = True

    log_event(logging.INFO, "wiki_create", root=str(root), changed=changed)
    return WikiOpResult(operation="create", changed=changed, log_appended=changed)
