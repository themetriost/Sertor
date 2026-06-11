"""Accesso agli assets bundlati via `importlib.resources` (D2).

Gli artefatti non-Python (skill, comando, agente, hook, template di config) vivono come
package-data sotto `sertor_installer/assets/`. Si leggono **solo** con `importlib.resources`
(niente `__file__`/`pathlib` sul layout del disco): funziona identico da editable e da wheel
installato/zippato.
"""
from __future__ import annotations

from collections.abc import Iterator
from importlib.resources import files
from importlib.resources.abc import Traversable

_ANCHOR = "sertor_installer"
_ASSETS = "assets"


def asset_path(relative: str) -> Traversable:
    """`Traversable` di un asset relativo a `sertor_installer/assets/` (es. il template config)."""
    node: Traversable = files(_ANCHOR) / _ASSETS
    for part in relative.replace("\\", "/").split("/"):
        if part:
            node = node / part
    return node


def read_asset_text(relative: str) -> str:
    """Contenuto testuale (UTF-8) di un asset."""
    return asset_path(relative).read_text(encoding="utf-8")


def iter_asset_dir(relative: str) -> Iterator[tuple[str, str]]:
    """Percorre ricorsivamente una sottodirectory degli assets.

    Restituisce coppie `(rel_path, content)` dove `rel_path` è relativo alla directory passata
    (separatori `/`), e `content` è il testo UTF-8 del file. Ordine deterministico (alfabetico)
    per rendere riproducibili report e test.
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
