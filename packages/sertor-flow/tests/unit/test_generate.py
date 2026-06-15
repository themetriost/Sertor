"""Unit tests for the per-host generation of init/integration files (T036)."""
from __future__ import annotations

import json
from pathlib import Path

from sertor_flow import generate
from sertor_flow.profile import GovernanceProfile, build_governance_profile


def _profile(tmp_path: Path, script: str = "bash") -> GovernanceProfile:
    return build_governance_profile(tmp_path, script=script)


def test_init_options_schema_and_profile_values(tmp_path: Path):
    """init-options.json has the expected schema and reflects the profile."""
    profile = _profile(tmp_path, script="bash")
    data = json.loads(generate.generate_init_options(profile))
    assert data["ai"] == "claude"
    assert data["integration"] == "claude"
    assert data["script"] == "bash"
    assert data["speckit_version"] == "0.8.18"
    assert data["context_file"] == "CLAUDE.md"


def test_integration_schema_and_profile_values(tmp_path: Path):
    """integration.json has the expected schema and reflects the profile."""
    profile = _profile(tmp_path, script="ps")
    data = json.loads(generate.generate_integration(profile))
    assert data["version"] == "0.8.18"
    assert data["installed_integrations"] == ["claude"]
    assert data["integration_settings"]["claude"]["script"] == "ps"
    assert data["default_integration"] == "claude"


def test_script_flavor_injection(tmp_path: Path):
    """The inferred script flavor flows into the generated files."""
    ps = json.loads(generate.generate_init_options(_profile(tmp_path, script="ps")))
    bash = json.loads(generate.generate_init_options(_profile(tmp_path, script="bash")))
    assert ps["script"] == "ps"
    assert bash["script"] == "bash"


def test_speckit_manifest_reflects_script_dir(tmp_path: Path):
    """The speckit manifest records the script subdir/ext matching the profile."""
    data = json.loads(
        generate.generate_file(generate.SPECKIT_MANIFEST_TMPL, _profile(tmp_path, script="bash"))
    )
    keys = list(data["files"].keys())
    assert any(".specify/scripts/bash/check-prerequisites.sh" == k for k in keys)
    assert data["version"] == "0.8.18"


def test_claude_manifest_is_valid_json(tmp_path: Path):
    """The claude manifest renders to valid JSON with the assistant injected."""
    data = json.loads(
        generate.generate_file(generate.CLAUDE_MANIFEST_TMPL, _profile(tmp_path, script="ps"))
    )
    assert data["integration"] == "claude"
    assert data["version"] == "0.8.18"
    assert isinstance(data["files"], dict) and data["files"]


def test_generated_files_have_installed_at(tmp_path: Path):
    """Manifests carry a generated `installed_at` timestamp (not the placeholder)."""
    data = json.loads(
        generate.generate_file(generate.CLAUDE_MANIFEST_TMPL, _profile(tmp_path))
    )
    assert "@@" not in data["installed_at"]
    assert "T" in data["installed_at"]  # ISO-8601
