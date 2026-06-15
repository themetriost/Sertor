"""Per-host generation of the SpecKit init/integration files (D7).

`init-options.json`, `integration.json` and `integrations/*.manifest.json` are
**generated** from `.tmpl` assets by injecting the inferred values of the
`GovernanceProfile`, exactly as `config_gen.generate_wiki_config` does for
`wiki.config.toml`. Defaults are NOT hard-coded here: they come from the profile
(itself centralized in `profile.py`) and the template text (Principle VII).

The generated files MUST be valid JSON and consumable by the SpecKit skills (same
schema as the real `.specify/init-options.json` / `integration.json`): tests pin
this invariant. The templates use `@@TOKEN@@` placeholders (plain string
substitution, not `str.format`) so the JSON braces in the templates need no
escaping.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

from sertor_flow.profile import GovernanceProfile
from sertor_install_kit import read_asset_text

# Anchor of THIS package: the kit reads the bundled assets relative to it (D2).
_ANCHOR = "sertor_flow"

# Generated init/integration files: (asset template relative to assets/, target_rel
# relative to the host root). The script flavor selects the manifest's script dir.
INIT_OPTIONS_TMPL = "init-options.json.tmpl"
INTEGRATION_TMPL = "integration.json.tmpl"
CLAUDE_MANIFEST_TMPL = "integrations/claude.manifest.json.tmpl"
SPECKIT_MANIFEST_TMPL = "integrations/speckit.manifest.json.tmpl"

INIT_OPTIONS_TARGET = ".specify/init-options.json"
INTEGRATION_TARGET = ".specify/integration.json"
CLAUDE_MANIFEST_TARGET = ".specify/integrations/claude.manifest.json"
SPECKIT_MANIFEST_TARGET = ".specify/integrations/speckit.manifest.json"

# Mapping from the inferred `script` flavor to the scripts subdir / file extension
# recorded in the speckit manifest (both shells are shipped regardless).
_SCRIPT_DIR = {"ps": "powershell", "bash": "bash"}
_SCRIPT_EXT = {"ps": "ps1", "bash": "sh"}


def _render(template: str, replacements: dict[str, str]) -> str:
    """Substitutes `@@TOKEN@@` placeholders in `template` (plain string replace)."""
    rendered = template
    for token, value in replacements.items():
        rendered = rendered.replace(f"@@{token}@@", value)
    return rendered


def _now_iso() -> str:
    """UTC ISO-8601 timestamp for the `installed_at` field of the manifests."""
    return datetime.now(UTC).isoformat()


def _replacements(profile: GovernanceProfile, *, installed_at: str) -> dict[str, str]:
    return {
        "ASSISTANT": profile.assistant,
        "SCRIPT": profile.script,
        "SPECKIT_VERSION": profile.speckit_version,
        "INSTALLED_AT": installed_at,
        "SCRIPT_DIR": _SCRIPT_DIR.get(profile.script, profile.script),
        "SCRIPT_EXT": _SCRIPT_EXT.get(profile.script, profile.script),
    }


def _generate_one(template_rel: str, profile: GovernanceProfile, *, installed_at: str) -> str:
    """Renders one template and validates it parses as JSON (D7: generated valid)."""
    template = read_asset_text(_ANCHOR, template_rel)
    rendered = _render(template, _replacements(profile, installed_at=installed_at))
    json.loads(rendered)  # fail fast if the substitution broke the JSON schema
    return rendered


def generate_init_options(profile: GovernanceProfile) -> str:
    """Generates `.specify/init-options.json` from the profile (D7)."""
    return _generate_one(INIT_OPTIONS_TMPL, profile, installed_at=_now_iso())


def generate_integration(profile: GovernanceProfile) -> str:
    """Generates `.specify/integration.json` from the profile (D7)."""
    return _generate_one(INTEGRATION_TMPL, profile, installed_at=_now_iso())


def generate_file(template_rel: str, profile: GovernanceProfile) -> str:
    """Generates an arbitrary init/integration/manifest file from its template (D7)."""
    return _generate_one(template_rel, profile, installed_at=_now_iso())
