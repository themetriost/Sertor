"""Adapter `SpecLiftSource`: legge l'output canonico di SpecLift (`*.speclift.json`, v1).

Consuma SpecLift **via il suo contratto pubblico versionato** (Principio III), mai i suoi interni.
Non riverifica le àncore (REQ-A02): le trasporta inalterate. Fail-loud (REQ-A04/R5).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import DEFAULT_CONFIG, Config
from ..domain.errors import (
    ChangesetMismatchError,
    SpecLiftArtifactError,
    SpecLiftVersionError,
)
from ..domain.models import Anchor, SpecLiftItem


def _anchor_from_speclift(d: dict[str, Any]) -> Anchor:
    """Mappa l'àncora SpecLift (test = testRef object|null) nella forma SpecAudit (test = str|null)."""

    test = d.get("test")
    test_citation: str | None = None
    if isinstance(test, dict):
        name = test.get("name", "")
        path = test.get("path", "")
        test_citation = f"{path}::{name}" if path or name else None
    elif isinstance(test, str):
        test_citation = test

    lines = d["lines"]
    return Anchor(
        file=d["file"],
        lines=(int(lines[0]), int(lines[1])),
        granularity=d["granularity"],
        status=d["status"],
        symbol=d.get("symbol"),
        test=test_citation,
    )


class SpecLiftJsonSource:
    """`SpecLiftSource` che legge un file `*.speclift.json` prodotto da `speclift assemble`."""

    def __init__(self, path: str | Path, config: Config = DEFAULT_CONFIG) -> None:
        self._path = Path(path)
        self._config = config

    def load(self, changeset_ref: str | None) -> tuple[str, list[SpecLiftItem]]:
        if not self._path.is_file():
            raise SpecLiftArtifactError(f"output SpecLift non trovato: {self._path}")
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SpecLiftArtifactError(
                f"output SpecLift illeggibile/malformato: {self._path}: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise SpecLiftArtifactError(f"output SpecLift non è un oggetto JSON: {self._path}")

        version = data.get("version")
        if version != self._config.supported_speclift_version:
            raise SpecLiftVersionError(
                f"versione output SpecLift non supportata: {version!r} "
                f"(attesa {self._config.supported_speclift_version!r})"
            )

        actual_ref = data.get("changeset_ref")
        if not isinstance(actual_ref, str) or not actual_ref:
            raise SpecLiftArtifactError("output SpecLift privo di changeset_ref")
        if changeset_ref is not None and changeset_ref != actual_ref:
            raise ChangesetMismatchError(
                f"changeset_ref richiesto {changeset_ref!r} ≠ output SpecLift {actual_ref!r}"
            )

        items: list[SpecLiftItem] = []
        idx = 0
        for req in data.get("requirements", []):
            try:
                items.append(
                    SpecLiftItem(
                        index=idx,
                        origin="requirement",
                        statement=req["statement"],
                        anchor=_anchor_from_speclift(req["anchor"]),
                        quota=req.get("quota"),
                    )
                )
            except (KeyError, TypeError) as exc:
                raise SpecLiftArtifactError(f"requisito SpecLift malformato (index {idx}): {exc}") from exc
            idx += 1
        for drift in data.get("drifts", []):
            try:
                items.append(
                    SpecLiftItem(
                        index=idx,
                        origin="drift",
                        statement=drift["description"],
                        anchor=_anchor_from_speclift(drift["anchor"]),
                        quota=None,
                    )
                )
            except (KeyError, TypeError) as exc:
                raise SpecLiftArtifactError(f"drift SpecLift malformato (index {idx}): {exc}") from exc
            idx += 1

        return actual_ref, items
