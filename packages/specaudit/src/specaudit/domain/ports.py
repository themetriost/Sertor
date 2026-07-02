"""Port (Protocol) — le astrazioni verso cui puntano le dipendenze (Constitution I/II).

Gli adapter concreti (filesystem, file dell'agente, stub) stanno dietro questi Protocol; il
wiring avviene nel composition root `pipeline.py`.
"""

from __future__ import annotations

from typing import Protocol

from .models import Adjudication, AuditBundle, OriginalRequirement, SpecLiftItem


class SpecLiftSource(Protocol):
    """Recupera l'output SpecLift (già ancorato) come lista di item.

    Fail-loud se l'artefatto è assente/malformato/di versione o changeset non corrispondente.
    """

    def load(self, changeset_ref: str | None) -> tuple[str, list[SpecLiftItem]]:
        """Restituisce (changeset_ref_effettivo, items). Non riverifica le àncore (REQ-A02)."""
        ...


class OriginalSourceResolver(Protocol):
    """Risolve la fonte del requisito originale (cascata). Mai codice sorgente (REQ-A01).

    Restituisce (requisiti, provenienza). Lista vuota + provenienza 'absent' quando nessuna
    fonte è risolvibile (gap dichiarato, non errore — FR-003).
    """

    def resolve(self, changeset_ref: str) -> tuple[list[OriginalRequirement], str]:
        ...


class Adjudicator(Protocol):
    """Il giudizio (allineamento + classificazione). In produzione è l'agente chiamante.

    Lo `StubAdjudicator` deterministico serve solo a test/offline.
    """

    def adjudicate(self, bundle: AuditBundle) -> Adjudication:
        ...
