"""Stadio 4 — bundle: assembla gli `EvidenceItem` localizzati in un `EvidenceBundle` versionato.

Il bundle è la **fonte di verità** consumata dallo stadio di stesura EARS: deve essere autoconsistente
(lo stadio a valle non deve ri-interrogare le fasi precedenti) e conforme allo schema versionato.
"""

from __future__ import annotations

from speclift.config import DEFAULT_CONFIG, Config
from speclift.domain.models import EvidenceBundle, EvidenceItem, Hunk


def build_bundle(
    changeset_ref: str,
    items: list[EvidenceItem],
    unresolved: list[Hunk],
    *,
    config: Config = DEFAULT_CONFIG,
) -> EvidenceBundle:
    return EvidenceBundle(
        version=config.contract_version,
        changeset_ref=changeset_ref,
        items=list(items),
        unresolved=list(unresolved),
    )
