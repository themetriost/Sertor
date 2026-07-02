"""Adapter `Adjudicator`.

- `FileAdjudicator`: legge l'`adjudicated.json` scritto dall'**agente chiamante** (la via di
  produzione: il giudizio è dell'agente).
- `StubAdjudicator`: giudizio banale e deterministico per **test/offline** — allinea 1:1 per
  posizione, emette verdetti placeholder. NON è la via di produzione (vedi adjudicator-port.md).
"""

from __future__ import annotations

import json
from pathlib import Path

from ..domain.errors import InvalidAdjudicationError
from ..domain.models import (
    Adjudication,
    AlignedGroup,
    AuditBundle,
    ExtraItem,
    Level,
    VerdictKind,
)
from ..serialize import adjudication_from_dict


class FileAdjudicator:
    """`Adjudicator` che rilegge il file JSON prodotto dall'agente."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def adjudicate(self, bundle: AuditBundle) -> Adjudication:
        if not self._path.is_file():
            raise InvalidAdjudicationError(f"file adjudication non trovato: {self._path}")
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InvalidAdjudicationError(
                f"adjudication illeggibile/malformata: {self._path}: {exc}"
            ) from exc
        try:
            return adjudication_from_dict(data)
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidAdjudicationError(f"adjudication strutturalmente invalida: {exc}") from exc


class StubAdjudicator:
    """Giudizio deterministico per test/offline: allineamento 1:1 per posizione, verdetti placeholder."""

    def adjudicate(self, bundle: AuditBundle) -> Adjudication:
        n_orig = len(bundle.original)
        n_spec = len(bundle.speclift)

        groups: list[AlignedGroup] = []
        for i in range(n_orig):
            if i < n_spec:
                groups.append(
                    AlignedGroup(
                        original=i,
                        speclift=[i],
                        alignment_confidence=Level.MEDIA,
                        verdict=VerdictKind.SODDISFATTO,
                        verdict_confidence=Level.MEDIA,
                    )
                )
            else:
                groups.append(
                    AlignedGroup(
                        original=i,
                        speclift=[],
                        alignment_confidence=Level.MEDIA,
                        verdict=VerdictKind.MANCANTE,
                        verdict_confidence=Level.BASSA,
                        explanation="[stub] nessun item SpecLift allineato a questo requisito",
                        severity=Level.MEDIA,
                        detectability=Level.MEDIA,
                    )
                )

        extras: list[ExtraItem] = []
        for j in range(n_orig, n_spec):
            extras.append(
                ExtraItem(
                    speclift=j,
                    verdict=VerdictKind.NON_DOCUMENTATO,
                    explanation="[stub] item SpecLift senza requisito originale corrispondente",
                    verdict_confidence=Level.BASSA,
                    severity=Level.BASSA,
                    detectability=Level.MEDIA,
                )
            )

        return Adjudication(
            changeset_ref=bundle.changeset_ref,
            groups=groups,
            extras=extras,
            open_questions=["giudizio demandato all'agente chiamante (StubAdjudicator, solo test/offline)"],
        )
