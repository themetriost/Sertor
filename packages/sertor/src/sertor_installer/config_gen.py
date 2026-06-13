"""`HostProfile` + generation of `wiki.config.toml` (D7, data-model §2).

The only point where the installer "inspects" the host: heuristic for `source_dirs` and injection
of `language`/`source_dirs` into the asset template. Defaults are NOT hard-coded here: they live in
the `wiki.config.toml.tmpl` template (Principio VIII / NFR-I-07); only the inferred specifics are
injected here. The generated file MUST pass `load_profile` of the core (invariant verified by
tests).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from sertor_installer.resources import read_asset_text

# Standard directories recognized (D7, inspection order) — generic, host-agnostic list.
_STANDARD_SOURCE_DIRS = (
    "src", "lib", "app", "pkg", "packages",
    "docs", "doc", "tests", "test", "requirements", "specs",
)

_CONFIG_TEMPLATE = "wiki.config.toml.tmpl"


@dataclass(frozen=True)
class HostProfile:
    """Inferred specifics of the host, collected before generating `wiki.config.toml`."""

    target_root: Path
    source_dirs: list[str] = field(default_factory=lambda: ["."])
    language: str = "en"


def _infer_source_dirs(target_root: Path) -> list[str]:
    """Standard directories present as direct subdirectories of the target; none found → `["."]`
    (D7)."""
    present = [d for d in _STANDARD_SOURCE_DIRS if (target_root / d).is_dir()]
    return present if present else ["."]


def build_host_profile(
    target_root: Path,
    source_dirs_override: list[str] | None = None,
    language: str = "en",
) -> HostProfile:
    """Builds the `HostProfile`: `--source-dirs` (override) bypasses the heuristic (D7)."""
    if source_dirs_override:
        source_dirs = [d.strip() for d in source_dirs_override if d.strip()]
    else:
        source_dirs = _infer_source_dirs(target_root)
    return HostProfile(target_root=target_root, source_dirs=source_dirs, language=language or "en")


def _toml_str_list(values: list[str]) -> str:
    """Serializes a list of strings as an inline TOML array (`["a", "b"]`)."""
    inner = ", ".join(f'"{v}"' for v in values)
    return f"[{inner}]"


def generate_wiki_config(profile: HostProfile) -> str:
    """Compiles `wiki.config.toml.tmpl` by injecting `language` and `source_dirs` (D7)."""
    template = read_asset_text(_CONFIG_TEMPLATE)
    return template.format(
        language=profile.language,
        source_dirs=_toml_str_list(profile.source_dirs),
    )
