"""Access to bundled assets via `importlib.resources` (D2), with a **parametric anchor**.

Non-Python artifacts (skill, command, agent, hook, config templates) live as package-data under
`<package>/assets/`. They are read **only** via `importlib.resources` (no `__file__`/`pathlib` on
disk layout): works identically from editable installs and from installed/zipped wheels.

The anchor is the **package of the consumer** (e.g. `"sertor_installer"` for `sertor`,
`"sertor_flow"` for governance): the kit must read the assets of whichever package calls it, so it
never hard-codes a single anchor (contract `install-kit/1`, D2).
"""
from __future__ import annotations

from collections.abc import Iterator
from importlib.resources import files
from importlib.resources.abc import Traversable

_ASSETS = "assets"


def asset_path(anchor: str, relative: str) -> Traversable:
    """`Traversable` for an asset relative to `<anchor>/assets/` (e.g. a config template)."""
    node: Traversable = files(anchor) / _ASSETS
    for part in relative.replace("\\", "/").split("/"):
        if part:
            node = node / part
    return node


def read_asset_text(anchor: str, relative: str) -> str:
    """Text content (UTF-8) of an asset under `<anchor>/assets/`."""
    return asset_path(anchor, relative).read_text(encoding="utf-8")


def iter_asset_dir(anchor: str, relative: str) -> Iterator[tuple[str, str]]:
    """Recursively walks an asset subdirectory under `<anchor>/assets/`.

    Yields pairs `(rel_path, content)` where `rel_path` is relative to the given directory
    (using `/` separators), and `content` is the UTF-8 text of the file. Deterministic
    (alphabetical) order makes reports and tests reproducible.
    """
    base = asset_path(anchor, relative)

    def _walk(node: Traversable, prefix: str) -> Iterator[tuple[str, str]]:
        for child in sorted(node.iterdir(), key=lambda c: c.name):
            # Skip Python bytecode caches: portable `.py` hooks (A-09) live in the asset tree, so a
            # test/run that imports them materializes `__pycache__/*.pyc` alongside — binary files
            # that must never be walked as UTF-8 text nor deposited on a host.
            if child.name == "__pycache__" or child.name.endswith(".pyc"):
                continue
            child_rel = f"{prefix}{child.name}"
            if child.is_dir():
                yield from _walk(child, f"{child_rel}/")
            else:
                yield child_rel, child.read_text(encoding="utf-8")

    yield from _walk(base, "")
