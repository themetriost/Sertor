"""G1 — round-trip del bundle: `bundle_to_dict` → `bundle_from_dict` preserva àncore ed evidenza.

Necessario perché la marcia `assemble` ricostruisce il bundle dal file emesso dalla marcia `bundle`.
"""

from __future__ import annotations

from speclift.domain.models import (
    Anchor,
    Changeset,
    EvidenceBundle,
    EvidenceItem,
    FileChange,
    Hunk,
    Symbol,
    TestRef,
)
from speclift.serialize import (
    authoring_bundle_to_dict,
    bundle_from_dict,
    bundle_to_dict,
    changeset_from_dict,
    changeset_to_dict,
)


def _bundle() -> EvidenceBundle:
    hunk = Hunk(
        file_path="pkg/foo.py",
        old_range=(10, 2),
        new_range=(10, 5),
        lines=["+def foo():", "+    return 1"],
        candidate_identifiers=["foo"],
    )
    test = TestRef(name="test_foo", path="tests/test_foo.py", covers_symbol="foo", line=3)
    anchor = Anchor(
        file="pkg/foo.py", lines=(10, 14), granularity="symbol", symbol="foo", test=test
    )
    item = EvidenceItem(
        hunk=hunk,
        anchor=anchor,
        granularity_used="symbol",
        symbols=[Symbol(name="foo", path="pkg/foo.py", line=10)],
        tests=[test],
    )
    unresolved = Hunk(file_path="pkg/bar.py", old_range=(1, 3), new_range=(1, 0))
    return EvidenceBundle(version="1", changeset_ref="abc123", items=[item], unresolved=[unresolved])


def test_roundtrip_preserves_anchor_and_evidence():
    original = _bundle()
    restored = bundle_from_dict(bundle_to_dict(original))

    assert restored.version == "1"
    assert restored.changeset_ref == "abc123"
    assert len(restored.items) == 1

    a = restored.items[0].anchor
    assert a.file == "pkg/foo.py"
    assert a.lines == (10, 14)
    assert a.symbol == "foo"
    assert a.test is not None and a.test.path == "tests/test_foo.py"
    assert a.test.covers_symbol == "foo"

    assert restored.items[0].symbols[0].name == "foo"
    assert restored.items[0].tests[0].name == "test_foo"
    assert len(restored.unresolved) == 1
    assert restored.unresolved[0].file_path == "pkg/bar.py"


def test_authoring_view_carries_diff_and_index():
    payload = authoring_bundle_to_dict(_bundle())
    assert payload["items"][0]["index"] == 0
    assert payload["items"][0]["symbol"] == "foo"
    assert "def foo" in payload["items"][0]["diff"]  # il contenuto del diff è esposto all'agente
    assert payload["unresolved_count"] == 1
    # contiene anche il bundle stretto per `assemble`
    assert payload["bundle"]["items"][0]["anchor"]["file"] == "pkg/foo.py"


# --- Changeset (marcia 0, locator alternativo agente/MCP) --------------------------------------


def _changeset() -> Changeset:
    hunk = Hunk(
        file_path="pkg/foo.py",
        old_range=(10, 2),
        new_range=(10, 5),
        lines=["+def foo():", "+    return 1"],
        candidate_identifiers=["foo"],
    )
    file = FileChange(path="pkg/foo.py", change_type="modified", hunks=[hunk])
    return Changeset(ref="abc123", kind="commit", files=[file])


def test_changeset_roundtrip_preserves_diff_lines():
    """A differenza del bundle, il changeset porta `lines`: l'agente deve poter leggere il diff."""
    restored = changeset_from_dict(changeset_to_dict(_changeset(), [("README.md", "doc")]))

    assert restored.ref == "abc123"
    assert restored.kind == "commit"
    assert len(restored.files) == 1
    h = restored.files[0].hunks[0]
    assert h.lines == ["+def foo():", "+    return 1"]
    assert h.candidate_identifiers == ["foo"]


def test_changeset_to_dict_carries_excluded_sources():
    payload = changeset_to_dict(_changeset(), [("README.md", "doc")])
    assert payload["excluded_sources"] == [["README.md", "doc"]]
    assert payload["changeset_ref"] == "abc123"
