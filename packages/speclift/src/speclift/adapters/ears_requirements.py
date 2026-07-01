"""Adapter `EarsAuthor` — **STUB** (dipendenza esterna non ancora disponibile).

L'unico stadio LLM delega la stesura EARS alla capacità `requirements` di Sertor in modalità
*bundle-driven non interattiva* (clarify 2026-06-26). Quella modalità **non esiste ancora** in
sertor-flow → questo adapter è uno stub che, per ogni `EvidenceItem`, emette requisiti *placeholder*
(uno per quota) con l'**àncora presa dal bundle** (così verify/render sono esercitabili end-to-end), e
**riporta** la dipendenza mancante in `open_questions` (Constitution XI: degrada *e* segnala, non
nasconde). Vedi `contracts/ears-author-port.md`. Quando Sertor fornirà la modalità, si scriverà
l'adapter reale dietro lo stesso port — zero modifiche al core.
"""

from __future__ import annotations

from speclift.domain.models import ALL_QUOTAS, EarsRequirement, EvidenceBundle, Quota
from speclift.domain.ports import EarsAuthoringResult

_NOTE = (
    "Stesura EARS demandata alla modalità bundle-driven di `requirements` (Sertor), "
    "non ancora disponibile: i requisiti sono placeholder ancorati all'evidenza."
)
_PREFIX = "[EARS DEMANDATO A SERTOR]"


class StubEarsAuthor:
    """Stub deterministico: placeholder ancorati al bundle, una nota di dipendenza aperta."""

    def __init__(self, quotas: tuple[Quota, ...] = ALL_QUOTAS) -> None:
        self._quotas = quotas

    def author(self, bundle: EvidenceBundle) -> EarsAuthoringResult:
        requirements: list[EarsRequirement] = []
        for idx, item in enumerate(bundle.items):
            descr = _describe(item)
            for quota in self._quotas:
                requirements.append(
                    EarsRequirement(
                        id=f"REQ-{idx:03d}-{quota.value}",
                        quota=quota,
                        statement=f"{_PREFIX} {descr}",
                        anchor=item.anchor,
                        source_item=f"item-{idx}",
                    )
                )
        open_questions = [_NOTE] if bundle.items else []
        return EarsAuthoringResult(requirements=requirements, open_questions=open_questions)


def _describe(item) -> str:
    target = item.anchor.symbol or item.anchor.file
    return f"modifica in {target} ({item.granularity_used})"
