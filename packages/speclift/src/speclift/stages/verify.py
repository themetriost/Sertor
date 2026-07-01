"""Stadio 6 — verify: il **moat**. Verifica ogni àncora e scarta i requisiti non ancorabili.

Per ogni requisito, l'`AnchorResolver` produce un verdetto deterministico (`verified`/`unverified`).
Un requisito la cui àncora non verifica è **escluso** dall'output confermato e **segnalato** (trasparenza,
Constitution XI), mai silenziosamente tenuto. Idempotente: ri-eseguirlo sui requisiti già verificati dà
lo stesso esito.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from speclift.domain.models import EarsRequirement, ExcludedRequirement
from speclift.domain.ports import AnchorResolver


@dataclass(frozen=True)
class VerifyResult:
    requirements: list[EarsRequirement]
    excluded: list[ExcludedRequirement]


def verify(requirements: list[EarsRequirement], resolver: AnchorResolver) -> VerifyResult:
    kept: list[EarsRequirement] = []
    excluded: list[ExcludedRequirement] = []

    for req in requirements:
        anchor = resolver.verify(req.anchor)
        if anchor.status == "verified":
            kept.append(replace(req, anchor=anchor))
        else:
            excluded.append(
                ExcludedRequirement(
                    statement=req.statement,
                    reason=(
                        f"àncora non verificabile ({anchor.file}:{anchor.lines[0]}-{anchor.lines[1]}"
                        f"{', simbolo ' + anchor.symbol if anchor.symbol else ''})"
                    ),
                )
            )

    return VerifyResult(requirements=kept, excluded=excluded)
