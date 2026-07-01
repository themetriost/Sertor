"""T021 — lift: usa il port EarsAuthor e non lascia mai passare àncore non nel bundle."""

from __future__ import annotations

import pytest

from speclift.adapters.ears_requirements import StubEarsAuthor
from speclift.domain.errors import BundleContractError
from speclift.domain.models import (
    Anchor,
    EarsRequirement,
    EvidenceBundle,
    EvidenceItem,
    Hunk,
    Quota,
)
from speclift.domain.ports import EarsAuthoringResult
from speclift.stages.lift import lift


def _bundle():
    hunk = Hunk("calc.py", (5, 0), (5, 2))
    anchor = Anchor(file="calc.py", lines=(5, 6), granularity="symbol", symbol="multiply")
    item = EvidenceItem(hunk=hunk, anchor=anchor, granularity_used="symbol")
    return EvidenceBundle(version="1", changeset_ref="HEAD", items=[item]), anchor


def test_stub_author_emits_anchored_placeholders():
    bundle, anchor = _bundle()
    result = lift(bundle, StubEarsAuthor())
    assert result.requirements
    assert all(r.anchor == anchor for r in result.requirements)
    assert all(r.statement.startswith("[EARS DEMANDATO A SERTOR]") for r in result.requirements)
    assert result.open_questions  # la dipendenza mancante è segnalata


def test_foreign_anchor_is_rejected_fail_loud():
    bundle, _ = _bundle()
    foreign = Anchor(file="evil.py", lines=(1, 1), granularity="hunk")

    class RogueAuthor:
        def author(self, b: EvidenceBundle) -> EarsAuthoringResult:
            return EarsAuthoringResult(
                requirements=[
                    EarsRequirement(id="X", quota=Quota.IMPLEMENTATION, statement="s", anchor=foreign)
                ],
            )

    with pytest.raises(BundleContractError):
        lift(bundle, RogueAuthor())


def test_empty_bundle_no_requirements():
    bundle = EvidenceBundle(version="1", changeset_ref="HEAD", items=[])
    result = lift(bundle, StubEarsAuthor())
    assert result.requirements == []
    assert result.open_questions == []
