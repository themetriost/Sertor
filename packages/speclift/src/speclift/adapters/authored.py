"""Adapter `EarsAuthor` — materializza i requisiti **scritti dall'agente chiamante**.

È la realizzazione di produzione del port (vedi `contracts/ears-author-port.md`): l'agente non è un
callable in-process, quindi la pipeline si spezza al confine del bundle. La marcia `bundle` della CLI
emette il fascicolo; l'agente scrive le frasi referenziando gli **item per indice**; questo adapter le
rilegge e le àncora prendendo l'`anchor` **dal bundle** (mai inventata). Così l'invariante REQ-X01
("nessuna àncora nuova") vale per costruzione, e un indice fuori range fallisce *loud*.
"""

from __future__ import annotations

from speclift.domain.errors import BundleContractError
from speclift.domain.models import EarsRequirement, EvidenceBundle, Quota
from speclift.domain.ports import EarsAuthoringResult


class AuthoredRequirementsAuthor:
    """Trasforma il file `authored` dell'agente in requisiti ancorati al bundle per indice."""

    def __init__(self, authored: dict) -> None:
        self._requirements = authored.get("requirements", [])
        self._open_questions = list(authored.get("open_questions", []))

    def author(self, bundle: EvidenceBundle) -> EarsAuthoringResult:
        out: list[EarsRequirement] = []
        n = len(bundle.items)
        for entry in self._requirements:
            idx = _require_int(entry, "item")
            if not 0 <= idx < n:
                raise BundleContractError(
                    f"requisito riferisce item {idx} fuori range (0..{n - 1})"
                )
            quota = _parse_quota(entry.get("quota"))
            statement = entry.get("statement")
            if not statement or not str(statement).strip():
                raise BundleContractError(f"requisito su item {idx}/{quota.value} senza statement")
            out.append(
                EarsRequirement(
                    id=f"REQ-{idx:03d}-{quota.value}",
                    quota=quota,
                    statement=str(statement).strip(),
                    anchor=bundle.items[idx].anchor,  # àncora presa dal bundle, mai nuova
                    source_item=f"item-{idx}",
                )
            )
        return EarsAuthoringResult(requirements=out, open_questions=self._open_questions)


def _require_int(entry: dict, key: str) -> int:
    value = entry.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise BundleContractError(f"campo '{key}' mancante o non intero in {entry!r}")
    return value


def _parse_quota(value: object) -> Quota:
    try:
        return Quota(str(value))
    except ValueError as exc:
        valid = ", ".join(q.value for q in Quota)
        raise BundleContractError(f"quota '{value}' non valida (ammesse: {valid})") from exc
