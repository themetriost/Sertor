"""`HostProfile` + generazione di `wiki.config.toml` (D7, data-model §2).

L'unico punto in cui l'installer "guarda" l'ospite: euristica delle `source_dirs` e iniezione di
`language`/`source_dirs` nel template degli assets. I default NON sono hard-coded nel codice: stanno
nel template `wiki.config.toml.tmpl` (Principio VIII / NFR-I-07); qui si inietta solo la specificità
inferita. Il file generato MUST superare `load_profile` del core (invariante verificata da test).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from sertor_installer.resources import read_asset_text

# Cartelle standard riconosciute (D7, ordine di controllo) — lista generica, host-agnostica.
_STANDARD_SOURCE_DIRS = (
    "src", "lib", "app", "pkg", "packages",
    "docs", "doc", "tests", "test", "requirements", "specs",
)

_CONFIG_TEMPLATE = "wiki.config.toml.tmpl"


@dataclass(frozen=True)
class HostProfile:
    """Specificità inferita dell'ospite, raccolta prima di generare `wiki.config.toml`."""

    target_root: Path
    source_dirs: list[str] = field(default_factory=lambda: ["."])
    language: str = "en"


def _infer_source_dirs(target_root: Path) -> list[str]:
    """Cartelle standard presenti come sottocartelle dirette del target; nessuna → `["."]` (D7)."""
    present = [d for d in _STANDARD_SOURCE_DIRS if (target_root / d).is_dir()]
    return present if present else ["."]


def build_host_profile(
    target_root: Path,
    source_dirs_override: list[str] | None = None,
    language: str = "en",
) -> HostProfile:
    """Costruisce l'`HostProfile`: `--source-dirs` (override) bypassa l'euristica (D7)."""
    if source_dirs_override:
        source_dirs = [d.strip() for d in source_dirs_override if d.strip()]
    else:
        source_dirs = _infer_source_dirs(target_root)
    return HostProfile(target_root=target_root, source_dirs=source_dirs, language=language or "en")


def _toml_str_list(values: list[str]) -> str:
    """Serializza una lista di stringhe come array TOML inline (`["a", "b"]`)."""
    inner = ", ".join(f'"{v}"' for v in values)
    return f"[{inner}]"


def generate_wiki_config(profile: HostProfile) -> str:
    """Compila `wiki.config.toml.tmpl` iniettando `language` e `source_dirs` (D7)."""
    template = read_asset_text(_CONFIG_TEMPLATE)
    return template.format(
        language=profile.language,
        source_dirs=_toml_str_list(profile.source_dirs),
    )
