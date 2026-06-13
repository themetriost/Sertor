"""Language guard (language topic): INSTALLED assets are in English.

Decision: tooling/infrastructure (installed assets) in canonical English; wiki content is in the
language chosen by the host. The test scans installable assets for high-signal Italian words
(function words absent in English and identifiers): if any are found, a block was not translated.
This is not a language detector — it is a net against coarse Italian that slipped through.
"""
from __future__ import annotations

import re

from sertor_installer.resources import iter_asset_dir, read_asset_text

# Distinctive Italian words (no plausible false positives in English or identifiers).
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
    items = list(iter_asset_dir("claude"))           # skill/agent/command/hook
    items += list(iter_asset_dir("rag"))             # .env/.mcp templates for the RAG runtime
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
