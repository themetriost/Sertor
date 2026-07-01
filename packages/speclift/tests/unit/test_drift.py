"""T036 / G2 — US3 FR-010: pezzo del changeset non coperto da requisito confermato → DriftFlag `proposed`.

Baseline = stessa esecuzione: il drift si misura sui requisiti emessi in questo run (non vs spec esterna,
che è SpecAudit). Un item senza requisito confermato è drift; un item coperto non lo è.
"""

from __future__ import annotations

from speclift.domain.models import (
    Anchor,
    EarsRequirement,
    EvidenceBundle,
    EvidenceItem,
    Hunk,
    Quota,
)
from speclift.stages.lift import detect_drift


def _item(idx: int) -> EvidenceItem:
    hunk = Hunk(f"f{idx}.py", (1, 0), (1, 2))
    anchor = Anchor(file=f"f{idx}.py", lines=(1, 2), granularity="symbol", symbol=f"sym{idx}")
    return EvidenceItem(hunk=hunk, anchor=anchor, granularity_used="symbol")


def _req(idx: int) -> EarsRequirement:
    return EarsRequirement(
        id=f"REQ-{idx}",
        quota=Quota.IMPLEMENTATION,
        statement="s",
        anchor=_item(idx).anchor,
        source_item=f"item-{idx}",
    )


def test_unresolved_hunk_becomes_proposed_drift():
    unresolved = Hunk("legacy.py", (10, 3), (10, 0))  # cancellazione: nessuna evidenza
    bundle = EvidenceBundle(version="1", changeset_ref="HEAD", items=[], unresolved=[unresolved])
    drifts = detect_drift(bundle, [])
    assert len(drifts) == 1
    assert drifts[0].status == "proposed"
    assert "legacy.py" in drifts[0].description


def test_uncovered_item_becomes_drift():
    bundle = EvidenceBundle(version="1", changeset_ref="HEAD", items=[_item(0)], unresolved=[])
    drifts = detect_drift(bundle, [])  # nessun requisito emesso per l'item → drift
    assert len(drifts) == 1
    assert drifts[0].status == "proposed"
    assert "sym0" in drifts[0].description


def test_covered_item_no_drift():
    bundle = EvidenceBundle(version="1", changeset_ref="HEAD", items=[_item(0)], unresolved=[])
    assert detect_drift(bundle, [_req(0)]) == []  # item-0 coperto → niente drift


def test_only_uncovered_items_drift():
    bundle = EvidenceBundle(
        version="1", changeset_ref="HEAD", items=[_item(0), _item(1)], unresolved=[]
    )
    drifts = detect_drift(bundle, [_req(0)])  # item-0 coperto, item-1 no
    assert len(drifts) == 1
    assert "sym1" in drifts[0].description


def test_drift_is_never_auto_confirmed():
    bundle = EvidenceBundle(
        version="1", changeset_ref="HEAD", items=[_item(0)], unresolved=[Hunk("x.py", (1, 1), (1, 0))]
    )
    assert all(d.status == "proposed" for d in detect_drift(bundle, []))
