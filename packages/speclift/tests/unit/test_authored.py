"""G1 — AuthoredRequirementsAuthor: materializza le frasi dell'agente ancorandole al bundle."""

from __future__ import annotations

import pytest

from speclift.adapters.authored import AuthoredRequirementsAuthor
from speclift.domain.errors import BundleContractError
from speclift.domain.models import (
    Anchor,
    EvidenceBundle,
    EvidenceItem,
    Hunk,
    Quota,
)


def _bundle(n_items: int = 1) -> EvidenceBundle:
    items = []
    for i in range(n_items):
        hunk = Hunk(file_path=f"f{i}.py", old_range=(1, 1), new_range=(1, 2))
        anchor = Anchor(file=f"f{i}.py", lines=(1, 2), granularity="symbol", symbol=f"sym{i}")
        items.append(EvidenceItem(hunk=hunk, anchor=anchor, granularity_used="symbol"))
    return EvidenceBundle(version="1", changeset_ref="REF", items=items)


def test_authors_anchor_from_bundle_not_invented():
    bundle = _bundle(1)
    authored = {
        "requirements": [
            {"item": 0, "quota": "user_capability", "statement": "WHEN x, the system SHALL y."},
            {"item": 0, "quota": "implementation", "statement": "The code calls sym0()."},
        ],
        "open_questions": ["q1"],
    }
    result = AuthoredRequirementsAuthor(authored).author(bundle)

    assert len(result.requirements) == 2
    assert {r.quota for r in result.requirements} == {Quota.USER_CAPABILITY, Quota.IMPLEMENTATION}
    # l'àncora è ESATTAMENTE quella del bundle (mai nuova)
    assert all(r.anchor is bundle.items[0].anchor for r in result.requirements)
    assert result.requirements[0].source_item == "item-0"
    assert result.open_questions == ["q1"]


def test_item_out_of_range_fails_loud():
    with pytest.raises(BundleContractError):
        AuthoredRequirementsAuthor(
            {"requirements": [{"item": 5, "quota": "behaviour", "statement": "s"}]}
        ).author(_bundle(1))


def test_invalid_quota_fails_loud():
    with pytest.raises(BundleContractError):
        AuthoredRequirementsAuthor(
            {"requirements": [{"item": 0, "quota": "nonexistent", "statement": "s"}]}
        ).author(_bundle(1))


def test_empty_statement_fails_loud():
    with pytest.raises(BundleContractError):
        AuthoredRequirementsAuthor(
            {"requirements": [{"item": 0, "quota": "behaviour", "statement": "   "}]}
        ).author(_bundle(1))


def test_missing_item_index_fails_loud():
    with pytest.raises(BundleContractError):
        AuthoredRequirementsAuthor(
            {"requirements": [{"quota": "behaviour", "statement": "s"}]}
        ).author(_bundle(1))


def test_no_requirements_yields_empty():
    result = AuthoredRequirementsAuthor({}).author(_bundle(1))
    assert result.requirements == []
    assert result.open_questions == []
