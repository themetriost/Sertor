"""G3 — filtro sorgenti: esclude dal changeset ciò che NON è fonte di requisiti.

Principio: SpecLift solleva requisiti da *cosa fa il codice*. La **specifica** e i **requisiti** sono
ciò CONTRO cui l'output va confrontato (lavoro di SpecAudit), non la fonte — generarli dalla spec è
circolare. La **documentazione** è opzionale (i "due SpecLift": con e senza), via `include_docs`. Le
**configurazioni** e il **codice** restano sempre inclusi (decisione utente 2026-06-30).

Trasparenza (Constitution XI): i file esclusi sono restituiti col motivo, mai scartati in silenzio.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import PurePosixPath

from speclift.config import Config
from speclift.domain.models import Changeset

#: Esito del filtro: (path, motivo) per ogni file escluso.
Excluded = list[tuple[str, str]]

_REASON_SPEC = "specifica/requisiti"
_REASON_DOC = "documentazione"


def filter_source_files(
    changeset: Changeset, config: Config, *, include_docs: bool
) -> tuple[Changeset, Excluded]:
    """Ritorna il changeset coi soli file-fonte + l'elenco (path, motivo) degli esclusi."""
    kept = []
    excluded: Excluded = []
    for f in changeset.files:
        reason = _exclusion_reason(f.path, config, include_docs=include_docs)
        if reason is None:
            kept.append(f)
        else:
            excluded.append((f.path, reason))
    return replace(changeset, files=kept), excluded


def _exclusion_reason(path: str, config: Config, *, include_docs: bool) -> str | None:
    norm = path.replace("\\", "/").lstrip("/")
    top = norm.split("/", 1)[0]
    if top in config.non_source_top_dirs:
        return _REASON_SPEC
    if not include_docs:
        if top in config.doc_top_dirs:
            return _REASON_DOC
        if PurePosixPath(norm).suffix.lower() in config.doc_extensions:
            return _REASON_DOC
    return None


def excluded_notes(excluded: Excluded) -> list[str]:
    """Una nota di trasparenza (lista breve) sui file esclusi, da accodare a `open_questions`."""
    if not excluded:
        return []
    listing = ", ".join(f"{path} ({reason})" for path, reason in excluded)
    return [f"Esclusi {len(excluded)} file non-fonte dall'analisi: {listing}"]
