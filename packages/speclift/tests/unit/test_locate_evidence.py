"""T016 — locate_evidence con fake EvidenceLocator: unione/dedup, fallback hunk, deletion→unresolved."""

from __future__ import annotations

from speclift.domain.models import Changeset, FileChange, Hunk, Symbol, TestRef
from speclift.stages.locate_evidence import locate_evidence


class FakeLocator:
    def __init__(self, symbols=None, tests=None) -> None:
        self._symbols = symbols or {}
        self._tests = tests or {}
        self.symbol_calls: list[str] = []

    def locate_symbols(self, file_path, identifiers, snippet):
        self.symbol_calls.append(file_path)
        return list(self._symbols.get(file_path, []))

    def locate_tests(self, symbol):
        return list(self._tests.get(symbol.name, []))


def _changeset(hunks):
    return Changeset(
        ref="HEAD",
        kind="commit",
        files=[FileChange(path="calc.py", change_type="modified", hunks=hunks)],
    )


def test_symbol_resolved_one_item_per_symbol():
    sym = Symbol(name="multiply", path="calc.py", line=5, kind="function")
    loc = FakeLocator(
        symbols={"calc.py": [sym]},
        tests={"multiply": [TestRef(name="test_multiply", path="t.py", covers_symbol="multiply")]},
    )
    hunk = Hunk("calc.py", (5, 0), (5, 2), candidate_identifiers=["multiply"])
    items, unresolved = locate_evidence(_changeset([hunk]), loc)
    assert len(items) == 1
    item = items[0]
    assert item.granularity_used == "symbol"
    assert item.anchor.granularity == "symbol"
    assert item.anchor.symbol == "multiply"
    assert item.anchor.status == "unverified"
    assert item.tests and item.tests[0].name == "test_multiply"
    assert unresolved == []


def test_duplicate_symbols_deduped():
    sym = Symbol(name="multiply", path="calc.py", line=5)
    loc = FakeLocator(symbols={"calc.py": [sym, sym]})
    hunk = Hunk("calc.py", (5, 0), (5, 2), candidate_identifiers=["multiply"])
    items, _ = locate_evidence(_changeset([hunk]), loc)
    assert len(items) == 1


def test_no_symbol_falls_back_to_hunk():
    loc = FakeLocator(symbols={})
    hunk = Hunk("calc.py", (10, 2), (10, 3), candidate_identifiers=[])
    items, unresolved = locate_evidence(_changeset([hunk]), loc)
    assert len(items) == 1
    assert items[0].granularity_used == "hunk"
    assert items[0].anchor.granularity == "hunk"
    assert items[0].anchor.lines == (10, 12)  # new_range (10,3) → righe 10..12
    assert unresolved == []


def test_deletion_only_hunk_is_unresolved():
    loc = FakeLocator(symbols={})
    hunk = Hunk("calc.py", (10, 3), (10, 0), candidate_identifiers=[])  # new_len 0
    items, unresolved = locate_evidence(_changeset([hunk]), loc)
    assert items == []
    assert len(unresolved) == 1


def test_multiple_hunks_same_symbol_merge_into_one_item():
    """G4: più hunk che risolvono lo stesso simbolo → UN item (range = span, diff = unione)."""
    sym = Symbol(name="foo", path="calc.py", line=5)
    loc = FakeLocator(
        symbols={"calc.py": [sym]},
        tests={"foo": [TestRef(name="t_foo", path="t.py", covers_symbol="foo")]},
    )
    h1 = Hunk("calc.py", (5, 1), (5, 2), lines=["+a", "+b"], candidate_identifiers=["foo"])
    h2 = Hunk("calc.py", (20, 1), (20, 3), lines=["+c"], candidate_identifiers=["foo"])
    items, _ = locate_evidence(_changeset([h1, h2]), loc)
    assert len(items) == 1
    item = items[0]
    assert item.anchor.symbol == "foo"
    assert item.anchor.lines == (5, 22)  # span: 5 .. (20+3-1)
    assert "+a" in item.hunk.lines and "+c" in item.hunk.lines  # diff unito
    assert item.tests and item.tests[0].name == "t_foo"  # test agganciato una volta


def test_symbolless_hunks_merge_into_one_hunk_item():
    """G4: più hunk senza simbolo same-file → UN item-hunk per file (non uno per hunk)."""
    loc = FakeLocator(symbols={})
    h1 = Hunk("calc.py", (1, 1), (1, 2), lines=["+x"], candidate_identifiers=[])
    h2 = Hunk("calc.py", (30, 1), (30, 1), lines=["+y"], candidate_identifiers=[])
    items, unresolved = locate_evidence(_changeset([h1, h2]), loc)
    assert len(items) == 1
    assert items[0].granularity_used == "hunk"
    assert items[0].anchor.lines == (1, 30)  # span
    assert unresolved == []
