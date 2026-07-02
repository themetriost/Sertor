"""Stadio 1a — ingest dell'output SpecLift via il port `SpecLiftSource`.

Thin: la logica di lettura/validazione sta nell'adapter (fail-loud lì). Qui è il seam nominato che
la pipeline compone e che i test esercitano con un fake.
"""

from __future__ import annotations

from ..domain.models import SpecLiftItem
from ..domain.ports import SpecLiftSource


def ingest_speclift(source: SpecLiftSource, changeset_ref: str | None) -> tuple[str, list[SpecLiftItem]]:
    """Restituisce (changeset_ref effettivo, item SpecLift). Non riverifica le àncore (REQ-A02)."""

    return source.load(changeset_ref)
