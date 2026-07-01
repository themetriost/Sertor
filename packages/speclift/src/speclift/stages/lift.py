"""Stadio 5 — lift: l'UNICO stadio LLM. Delega a `EarsAuthor` e fa rispettare l'invariante chiave.

Invariante (REQ-X01, il cuore del moat lato stesura): l'autore EARS **non può introdurre àncore** che
non siano già nel bundle. `lift` verifica ogni requisito contro le àncore del bundle e fallisce *loud*
(`BundleContractError`) se ne trova una estranea — non la corregge in silenzio.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from speclift.domain.errors import BundleContractError
from speclift.domain.models import (
    ALL_QUOTAS,
    Anchor,
    DriftFlag,
    EarsRequirement,
    EvidenceBundle,
    Hunk,
    Quota,
)
from speclift.domain.ports import EarsAuthor


@dataclass(frozen=True)
class LiftResult:
    requirements: list[EarsRequirement]
    open_questions: list[str]


def lift(bundle: EvidenceBundle, author: EarsAuthor) -> LiftResult:
    result = author.author(bundle)
    allowed = {item.anchor for item in bundle.items}

    for req in result.requirements:
        if req.anchor not in allowed:
            raise BundleContractError(
                f"requisito {req.id!r} introduce un'àncora non presente nel bundle "
                f"({req.anchor.file}:{req.anchor.lines}) — violazione REQ-X01"
            )

    open_questions = list(result.open_questions)
    open_questions.extend(_missing_quota_notes(bundle, result.requirements))

    return LiftResult(requirements=list(result.requirements), open_questions=open_questions)


def _missing_quota_notes(bundle: EvidenceBundle, requirements: list[EarsRequirement]) -> list[str]:
    """US2: per ogni elemento del bundle, una quota priva di requisito è **segnalata**, non omessa.

    Mappa i requisiti all'elemento d'origine (`source_item`); se per un elemento manca una delle tre
    quote, emette una nota esplicita. Non inventa requisiti: rende visibile la lacuna (Constitution XI).
    """
    by_item: dict[str, set[Quota]] = defaultdict(set)
    for req in requirements:
        if req.source_item is not None:
            by_item[req.source_item].add(req.quota)

    notes: list[str] = []
    for idx in range(len(bundle.items)):
        key = f"item-{idx}"
        present = by_item.get(key, set())
        if not present:
            # Item del tutto scoperto: è drift (detect_drift), non una lacuna di quota → niente nota.
            continue
        for quota in ALL_QUOTAS:
            if quota not in present:
                notes.append(
                    f"quota '{quota.value}' mancante per {key} "
                    f"({bundle.items[idx].anchor.file}:{bundle.items[idx].anchor.lines[0]}): "
                    "segnalata, non omessa"
                )
    return notes


def detect_drift(
    bundle: EvidenceBundle, requirements: list[EarsRequirement]
) -> list[DriftFlag]:
    """US3/FR-010: pezzi del changeset non coperti da alcun requisito **confermato** → drift *proposed*.

    Baseline = la **stessa esecuzione** (spec, Assumptions): si confronta col solo output di questo run,
    non con una spec esterna — quel confronto (requisiti originali ↔ generati) è **SpecAudit**, fuori MVP.
    Sono drift:
      - un `EvidenceItem` che **nessun** requisito confermato referenzia (`source_item`): l'agente non lo
        ha descritto, oppure i suoi requisiti sono stati esclusi dal moat;
      - un hunk `unresolved` (nessuna evidenza ancorabile nel nuovo stato del file).
    Mai auto-confermato (`status="proposed"`): è un'ipotesi di comportamento non documentato, tenuta
    distinta dai requisiti confermati. L'àncora è `unverified` perché è una proposta, non garanzia del moat.
    """
    covered = {r.source_item for r in requirements if r.source_item is not None}
    drifts: list[DriftFlag] = []

    for idx, item in enumerate(bundle.items):
        if f"item-{idx}" in covered:
            continue
        drifts.append(
            DriftFlag(
                description=(
                    f"modifica in {_item_label(item)} non coperta da alcun requisito emesso — "
                    "possibile comportamento non documentato"
                ),
                anchor=_item_drift_anchor(item),
                status="proposed",
            )
        )

    for hunk in bundle.unresolved:
        drifts.append(
            DriftFlag(
                description=(
                    f"modifica in {hunk.file_path} (righe vecchie {hunk.old_range[0]}+"
                    f"{hunk.old_range[1]}) non coperta da alcun requisito — possibile comportamento "
                    "non documentato"
                ),
                anchor=_drift_anchor(hunk),
                status="proposed",
            )
        )
    return drifts


def _item_label(item) -> str:
    a = item.anchor
    if a.symbol:
        return f"{a.symbol} ({a.file}:{a.lines[0]}-{a.lines[1]})"
    return f"{a.file}:{a.lines[0]}-{a.lines[1]}"


def _item_drift_anchor(item) -> Anchor:
    a = item.anchor
    return Anchor(
        file=a.file,
        lines=a.lines,
        granularity=a.granularity,
        status="unverified",
        symbol=a.symbol,
        test=a.test,
    )


def _drift_anchor(hunk: Hunk) -> Anchor:
    start = hunk.new_range[0] or hunk.old_range[0]
    return Anchor(file=hunk.file_path, lines=(start, start), granularity="hunk", status="unverified")
