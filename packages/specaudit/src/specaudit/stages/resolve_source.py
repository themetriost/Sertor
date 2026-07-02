"""Stadio 1b — risoluzione della fonte originale via il port `OriginalSourceResolver`.

Traduce la provenienza restituita dall'adapter in **gap dichiarati** espliciti (FR-003): distingue
'assente' da 'presente ma vuota'. Mai un MANCANTE inventato per una fonte che non esiste.
"""

from __future__ import annotations

from ..domain.models import OriginalRequirement
from ..domain.ports import OriginalSourceResolver


def resolve_original(
    resolver: OriginalSourceResolver, changeset_ref: str
) -> tuple[list[OriginalRequirement], str, list[str]]:
    """Restituisce (requisiti, provenienza, gap_dichiarati)."""

    requirements, provenance = resolver.resolve(changeset_ref)
    gaps: list[str] = []
    if provenance == "absent":
        gaps.append("original_source: absent")
    elif provenance.startswith("present-but-empty"):
        gaps.append("original_source: present-but-empty")
    return requirements, provenance, gaps
