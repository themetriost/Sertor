"""`scan`: ricerca di lavoro pendente via mtime (FR-005, research D3).

Confronta il `mtime` dei file nelle `source_dirs` del profilo (con le esclusioni della config)
con l'ancora temporale dell'ultima voce di registro. Host-agnostico: funziona anche su ospiti
non-git (nessuna dipendenza da git; il refresh git-driven è competenza di FEAT-003-N). Replica
la logica dell'attuale `wiki-pending-check.ps1` (SC-003) per parità di conteggio.
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
    """`True` se un qualunque segmento di path combacia con un pattern di esclusione (glob)."""
    for part in rel_parts:
        for pattern in patterns:
            if fnmatch.fnmatch(part, pattern):
                return True
    return False


def _file_mtime(path: Path) -> float | None:
    """mtime di un file non vuoto (None se assente/vuoto/illeggibile)."""
    if not path.is_file():
        return None
    try:
        if path.stat().st_size == 0:
            return None
        return path.stat().st_mtime
    except OSError:
        return None


def _latest_log_mtime(profile: WikiProfile) -> float | None:
    """Àncora temporale dell'ultima voce di registro.

    Rotazione attiva → mtime della **partizione più recente** (max sui file `YYYY-MM-DD.md`,
    escluso l'indice). Modalità file-unico (back-compat) → mtime del registro unico. In entrambi i
    casi: assente/vuoto → `None` (tutto pendente). Il contratto `wiki.scan/1` resta invariato.
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
    """Conta i file-sorgente più recenti dell'ultima voce di registro.

    `anchor` assente (registro mancante/vuoto) → tutto è pendente. `message` proviene dalle
    `strings` localizzate del profilo (`{n}` sostituito col conteggio).
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
        "{n} file più recenti dell'ultima voce di log."
        if pending
        else "Nessun file più recente dell'ultima voce di log.",
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
