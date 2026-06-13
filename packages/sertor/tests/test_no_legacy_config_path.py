"""Guardia REQ-303 (feature 016, T016): nessun asset invoca il vecchio path radice della config.

Dopo lo spostamento di `wiki.config.toml` in `wiki/`, nessuna invocazione installata deve usare la
forma legacy `--config wiki.config.toml` (path in radice). La forma corretta è
`--config wiki/wiki.config.toml --root .` o l'auto-discovery del CLI. Il fallback legacy nel hook
usa una variabile (`--config $config`), non il literal, quindi non è un'occorrenza.
"""
from __future__ import annotations

from sertor_installer.resources import iter_asset_dir, read_asset_text

# Forma legacy del FLAG (con path radice). NB: `--config wiki/wiki.config.toml` NON contiene questo
# literal, quindi la nuova forma non genera falsi positivi.
_LEGACY_FLAG = "--config wiki.config.toml"


def test_no_asset_uses_legacy_root_config_flag():
    offenders: list[str] = []
    for rel, content in iter_asset_dir("claude"):
        if _LEGACY_FLAG in content:
            offenders.append(f"claude/{rel}")
    for extra in ("claude-md-block.md", "wiki.config.toml.tmpl"):
        if _LEGACY_FLAG in read_asset_text(extra):
            offenders.append(extra)
    assert not offenders, (
        f"asset con invocazione --config legacy (path radice): {offenders}. "
        f"Usa `--config wiki/wiki.config.toml --root .` o l'auto-discovery."
    )
