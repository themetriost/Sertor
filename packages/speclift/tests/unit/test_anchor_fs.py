"""Test adapter FilesystemAnchorResolver: verdetto deterministico su file reali (tmp)."""

from __future__ import annotations

from speclift.adapters.anchor_fs import FilesystemAnchorResolver
from speclift.domain.models import Anchor, TestRef


def _repo(tmp_path):
    (tmp_path / "calc.py").write_text(
        "def add(a, b):\n    return a + b\n\n\ndef multiply(a, b):\n    return a * b\n", "utf-8"
    )
    (tmp_path / "test_calc.py").write_text(
        "from calc import multiply\n\n\ndef test_multiply():\n    assert multiply(2, 3) == 6\n", "utf-8"
    )
    return FilesystemAnchorResolver(tmp_path)


def test_valid_symbol_and_test_verified(tmp_path):
    resolver = _repo(tmp_path)
    anchor = Anchor(
        file="calc.py",
        lines=(5, 6),
        granularity="symbol",
        symbol="multiply",
        test=TestRef(name="test_calc", path="test_calc.py", covers_symbol="multiply"),
    )
    assert resolver.verify(anchor).status == "verified"


def test_missing_file_unverified(tmp_path):
    resolver = _repo(tmp_path)
    anchor = Anchor(file="ghost.py", lines=(1, 1), granularity="hunk")
    assert resolver.verify(anchor).status == "unverified"


def test_lines_out_of_bounds_unverified(tmp_path):
    resolver = _repo(tmp_path)
    anchor = Anchor(file="calc.py", lines=(100, 200), granularity="hunk")
    assert resolver.verify(anchor).status == "unverified"


def test_symbol_absent_unverified(tmp_path):
    resolver = _repo(tmp_path)
    anchor = Anchor(file="calc.py", lines=(1, 2), granularity="symbol", symbol="nonexistent")
    assert resolver.verify(anchor).status == "unverified"


def test_test_not_referencing_symbol_unverified(tmp_path):
    resolver = _repo(tmp_path)
    anchor = Anchor(
        file="calc.py",
        lines=(5, 6),
        granularity="symbol",
        symbol="multiply",
        test=TestRef(name="t", path="test_calc.py", covers_symbol="absent_symbol"),
    )
    assert resolver.verify(anchor).status == "unverified"


def test_idempotent_on_already_verified(tmp_path):
    resolver = _repo(tmp_path)
    anchor = Anchor(file="calc.py", lines=(5, 6), granularity="symbol", symbol="multiply")
    once = resolver.verify(anchor)
    twice = resolver.verify(once)
    assert once.status == twice.status == "verified"
