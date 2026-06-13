"""Guardia di lingua (tema lingua): gli asset INSTALLATI sono in inglese.

Decisione: tooling/infrastruttura (asset installati) in inglese canonico; il contenuto del wiki è
nella lingua scelta dall'host. Il test scansiona gli asset installabili per parole italiane ad alto
segnale (function word assenti in inglese e negli identificatori): se ne trova, un blocco è rimasto
non tradotto. Non è un rilevatore di lingua, è una rete contro l'italiano grossolano sfuggito.
"""
from __future__ import annotations

import re

from sertor_installer.resources import iter_asset_dir, read_asset_text

# Parole italiane distintive (nessun falso positivo plausibile in inglese o negli identificatori).
_ITALIAN = [
    "della", "delle", "degli", "dello", "nella", "nelle", "negli", "dell",
    "perché", "perche", "però", "pero", "poiché", "poiche", "anche", "oppure",
    "sono", "viene", "vengono", "essere", "questo", "questa", "quello", "quella",
    "ospite", "configurazione", "esegui", "eseguire", "radice", "cartella",
    "pagina", "registro", "giudizio", "contraddizione", "senza", "quando",
    "ogni", "tutti", "tutte", "fonte", "voce",
]
_PATTERN = re.compile(r"\b(" + "|".join(_ITALIAN) + r")\b", re.IGNORECASE)


def _assets() -> list[tuple[str, str]]:
    items = list(iter_asset_dir("claude"))
    items.append(("claude-md-block.md", read_asset_text("claude-md-block.md")))
    items.append(("wiki.config.toml.tmpl", read_asset_text("wiki.config.toml.tmpl")))
    return items


def test_installed_assets_are_english():
    offenders: list[str] = []
    for rel, content in _assets():
        for i, line in enumerate(content.splitlines(), 1):
            m = _PATTERN.search(line)
            if m:
                offenders.append(f"{rel}:{i}: «{m.group(0)}» :: {line.strip()[:90]}")
    assert not offenders, (
        "Italiano residuo negli asset installati (devono essere in inglese):\n"
        + "\n".join(offenders[:40])
    )
