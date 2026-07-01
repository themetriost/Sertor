"""T033 — US2: lift produce le 3 quote per elemento; quota assente segnalata (non omessa)."""

from __future__ import annotations

from speclift.adapters.ears_requirements import StubEarsAuthor
from speclift.domain.models import (
    ALL_QUOTAS,
    Anchor,
    EarsRequirement,
    EvidenceBundle,
    EvidenceItem,
    Hunk,
    Quota,
)
from speclift.domain.ports import EarsAuthoringResult
from speclift.stages.lift import lift


def _bundle(n_items=1):
    items = []
    for i in range(n_items):
        hunk = Hunk(f"f{i}.py", (1, 0), (1, 1))
        anchor = Anchor(file=f"f{i}.py", lines=(1, 1), granularity="hunk")
        items.append(EvidenceItem(hunk=hunk, anchor=anchor, granularity_used="hunk"))
    return EvidenceBundle(version="1", changeset_ref="HEAD", items=items)


def test_three_quotas_per_item():
    bundle = _bundle(n_items=2)
    result = lift(bundle, StubEarsAuthor())
    by_item: dict[str, set[Quota]] = {}
    for r in result.requirements:
        by_item.setdefault(r.source_item, set()).add(r.quota)
    assert by_item["item-0"] == set(ALL_QUOTAS)
    assert by_item["item-1"] == set(ALL_QUOTAS)


def test_missing_quota_is_flagged_not_omitted():
    bundle = _bundle(n_items=1)
    anchor = bundle.items[0].anchor

    class PartialAuthor:
        """Emette solo la quota implementation per l'item: le altre due devono essere segnalate."""

        def author(self, b: EvidenceBundle) -> EarsAuthoringResult:
            return EarsAuthoringResult(
                requirements=[
                    EarsRequirement(
                        id="REQ-000-impl",
                        quota=Quota.IMPLEMENTATION,
                        statement="s",
                        anchor=anchor,
                        source_item="item-0",
                    )
                ]
            )

    result = lift(bundle, PartialAuthor())
    notes = " ".join(result.open_questions)
    assert "user_capability' mancante" in notes
    assert "behaviour' mancante" in notes
    assert "implementation' mancante" not in notes  # quella c'è
