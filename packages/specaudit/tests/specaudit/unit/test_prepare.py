"""T017 — prepare: bundle schema-valido, indici densi, gap propagati."""

from __future__ import annotations

from specaudit.domain.models import Anchor, OriginalRequirement, SpecLiftItem
from specaudit.stages.prepare import prepare


class FakeSpecLift:
    def __init__(self, items):
        self._items = items

    def load(self, changeset_ref):
        return "ref-1", self._items


class FakeResolver:
    def __init__(self, reqs, provenance):
        self._reqs = reqs
        self._provenance = provenance

    def resolve(self, changeset_ref):
        return self._reqs, self._provenance


def _item(i):
    return SpecLiftItem(i, "requirement", f"stmt {i}", Anchor(f"f{i}.py", (1, 2), "hunk", "verified"))


def test_prepare_builds_indexed_bundle():
    src = FakeSpecLift([_item(0), _item(1)])
    res = FakeResolver([OriginalRequirement(0, "FR-1", "t", "p")], "requirements/")
    bundle = prepare(src, res, None)
    assert bundle.changeset_ref == "ref-1"
    assert [o.index for o in bundle.original] == [0]
    assert [s.index for s in bundle.speclift] == [0, 1]
    assert bundle.declared_gaps == []


def test_prepare_declares_absent_gap():
    src = FakeSpecLift([_item(0)])
    res = FakeResolver([], "absent")
    bundle = prepare(src, res, None)
    assert "original_source: absent" in bundle.declared_gaps
    assert bundle.original == []


def test_prepare_merges_extra_gaps():
    src = FakeSpecLift([_item(0)])
    res = FakeResolver([OriginalRequirement(0, "FR-1", "t", "p")], "requirements/")
    bundle = prepare(src, res, None, extra_gaps=["speclift-excluded: docs/x.md"])
    assert "speclift-excluded: docs/x.md" in bundle.declared_gaps
