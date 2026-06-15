"""Access to `sertor`'s bundled assets — thin wrapper over the kit's parametric `resources` (037).

The generic asset reader migrated to `sertor-install-kit` with a **parametric anchor**. `sertor`'s
assets live under `sertor_installer/assets/`, so this wrapper binds the anchor to
`"sertor_installer"` and preserves the historical single-argument API (`asset_path(rel)`,
`read_asset_text(rel)`, `iter_asset_dir(rel)`) used by `sertor`'s code and tests.
"""
from __future__ import annotations

from collections.abc import Iterator
from importlib.resources.abc import Traversable

from sertor_install_kit import resources as _kit

_ANCHOR = "sertor_installer"


def asset_path(relative: str) -> Traversable:
    """`Traversable` for an asset relative to `sertor_installer/assets/`."""
    return _kit.asset_path(_ANCHOR, relative)


def read_asset_text(relative: str) -> str:
    """Text content (UTF-8) of an asset."""
    return _kit.read_asset_text(_ANCHOR, relative)


def iter_asset_dir(relative: str) -> Iterator[tuple[str, str]]:
    """Recursively walks an asset subdirectory under `sertor_installer/assets/`."""
    return _kit.iter_asset_dir(_ANCHOR, relative)
