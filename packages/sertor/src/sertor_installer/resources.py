"""Access to bundled assets via `importlib.resources` (D2).

Non-Python artifacts (skill, command, agent, hook, config templates) live as package-data under
`sertor_installer/assets/`. They are read **only** via `importlib.resources` (no
`__file__`/`pathlib` on disk layout): works identically from editable installs and from
installed/zipped wheels.
"""
from __future__ import annotations

from collections.abc import Iterator
from importlib.resources import files
from importlib.resources.abc import Traversable

_ANCHOR = "sertor_installer"
_ASSETS = "assets"


def asset_path(relative: str) -> Traversable:
    """`Traversable` for an asset relative to `sertor_installer/assets/` (e.g. the config
    template)."""
    node: Traversable = files(_ANCHOR) / _ASSETS
    for part in relative.replace("\\", "/").split("/"):
        if part:
            node = node / part
    return node


def read_asset_text(relative: str) -> str:
    """Text content (UTF-8) of an asset."""
    return asset_path(relative).read_text(encoding="utf-8")


def iter_asset_dir(relative: str) -> Iterator[tuple[str, str]]:
    """Recursively walks an asset subdirectory.

    Yields pairs `(rel_path, content)` where `rel_path` is relative to the given directory
    (using `/` separators), and `content` is the UTF-8 text of the file. Deterministic
    (alphabetical) order makes reports and tests reproducible.
    """
    base = asset_path(relative)

    def _walk(node: Traversable, prefix: str) -> Iterator[tuple[str, str]]:
        for child in sorted(node.iterdir(), key=lambda c: c.name):
            child_rel = f"{prefix}{child.name}"
            if child.is_dir():
                yield from _walk(child, f"{child_rel}/")
            else:
                yield child_rel, child.read_text(encoding="utf-8")

    yield from _walk(base, "")
