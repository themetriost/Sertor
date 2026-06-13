"""Guard REQ-303 (feature 016, T016): no asset invokes the old root config path.

After moving `wiki.config.toml` to `wiki/`, no installed invocation should use the legacy form
`--config wiki.config.toml` (root path). The correct form is
`--config wiki/wiki.config.toml --root .` or the CLI auto-discovery. The legacy fallback in the hook
uses a variable (`--config $config`), not the literal, so it is not an occurrence.
"""
from __future__ import annotations

from sertor_installer.resources import iter_asset_dir, read_asset_text

# Legacy form of the FLAG (with root path). NB: `--config wiki/wiki.config.toml` does NOT contain
# this literal, so the new form does not generate false positives.
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
