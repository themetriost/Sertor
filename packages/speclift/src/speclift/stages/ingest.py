"""Stadio 1 — ingest: risolve ref/range/staged in un `RawDiff` normalizzato.

Determina la `kind` dalle opzioni CLI (precedenza: staged > range > commit), invoca il
`DiffSource` per il testo unified-diff e lo impacchetta. Non parsa nulla (lo fa `parse_diff`).
Un diff vuoto NON è errore (esito "nessun requisito"); un ref invalido lo è (`InvalidRefError`,
sollevato dall'adapter e propagato).
"""

from __future__ import annotations

from speclift.domain.models import STAGED_REF, RawDiff
from speclift.domain.ports import DiffSource


def ingest(
    source: DiffSource,
    *,
    ref: str | None,
    staged: bool,
    range_spec: str | None,
) -> RawDiff:
    if staged:
        text = source.raw_diff(STAGED_REF, "staged")
        return RawDiff(ref=STAGED_REF, kind="staged", text=text)

    if range_spec:
        text = source.raw_diff(range_spec, "range")
        return RawDiff(ref=range_spec, kind="range", text=text)

    resolved_ref = ref or "HEAD"
    text = source.raw_diff(resolved_ref, "commit")
    return RawDiff(ref=resolved_ref, kind="commit", text=text)
