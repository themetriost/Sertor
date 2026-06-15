"""Tests for `resources` (T008): parametric anchor reads assets of the calling package."""
from __future__ import annotations

from sertor_install_kit.resources import iter_asset_dir, read_asset_text

_ANCHOR = "_assetpkg"


def test_read_asset_text_with_anchor():
    assert read_asset_text(_ANCHOR, "a.txt") == "hello root"


def test_read_nested_asset():
    assert read_asset_text(_ANCHOR, "sub/b.txt") == "nested"


def test_iter_asset_dir_recursive_sorted():
    items = list(iter_asset_dir(_ANCHOR, ""))
    rels = [rel for rel, _ in items]
    assert rels == ["a.txt", "sub/b.txt"]  # deterministic alphabetical order
    contents = dict(items)
    assert contents["a.txt"] == "hello root"
    assert contents["sub/b.txt"] == "nested"


def test_iter_subdir():
    items = list(iter_asset_dir(_ANCHOR, "sub"))
    assert items == [("b.txt", "nested")]
