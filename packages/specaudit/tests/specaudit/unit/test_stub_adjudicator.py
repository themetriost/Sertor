"""T019 — StubAdjudicator: allineamento 1:1 per posizione, copertura completa, indici validi."""

from __future__ import annotations

from specaudit.adapters.adjudication_file import StubAdjudicator
from specaudit.domain.models import Anchor, AuditBundle, OriginalRequirement, SpecLiftItem, VerdictKind


def _bundle(n_orig, n_spec):
    return AuditBundle(
        version="1",
        changeset_ref="ref",
        original=[OriginalRequirement(i, f"FR-{i}", "t", "p") for i in range(n_orig)],
        speclift=[
            SpecLiftItem(i, "requirement", f"s{i}", Anchor(f"f{i}.py", (1, 2), "hunk", "verified"))
            for i in range(n_spec)
        ],
        declared_gaps=[],
        source_provenance={"original": "requirements/", "speclift": "speclift-output"},
    )


def test_stub_aligns_one_to_one():
    adj = StubAdjudicator().adjudicate(_bundle(2, 2))
    assert [g.original for g in adj.groups] == [0, 1]
    assert [g.speclift for g in adj.groups] == [[0], [1]]
    assert adj.extras == []


def test_stub_marks_missing_when_more_originals():
    adj = StubAdjudicator().adjudicate(_bundle(3, 1))
    verdicts = [g.verdict for g in adj.groups]
    assert verdicts[0] == VerdictKind.SODDISFATTO
    assert verdicts[1] == VerdictKind.MANCANTE
    assert verdicts[2] == VerdictKind.MANCANTE


def test_stub_extras_when_more_speclift():
    adj = StubAdjudicator().adjudicate(_bundle(1, 3))
    assert [e.speclift for e in adj.extras] == [1, 2]
    assert all(e.verdict == VerdictKind.NON_DOCUMENTATO for e in adj.extras)


def test_stub_coverage_is_complete():
    bundle = _bundle(2, 3)
    adj = StubAdjudicator().adjudicate(bundle)
    covered_spec = [s for g in adj.groups for s in g.speclift] + [e.speclift for e in adj.extras]
    assert sorted(covered_spec) == [0, 1, 2]
    assert sorted(g.original for g in adj.groups) == [0, 1]
