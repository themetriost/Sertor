"""Unit tests for `build_governance_plan` (feature 045): Sertor-authored surfaces, order, targeting.

After the launch-installer pivot the plan covers ONLY the Sertor-authored surfaces (SpecKit is
obtained via `specify init`, not in the plan): the `requirements-analyst`/`configuration-manager`
agents, the `requirements` skill, the constitution-starter, the generated init/integration files and
the SDLC marker block. Each surface is routed per-assistant via the `AssistantProfile`.
"""
from __future__ import annotations

from pathlib import Path

from sertor_flow.install_governance import build_governance_plan
from sertor_flow.profile import build_governance_profile
from sertor_install_kit import ArtifactKind, WriteStrategy


def _plan(tmp_path: Path, assistant: str = "claude"):
    profile = build_governance_profile(tmp_path, assistant=assistant)
    return build_governance_plan(profile)


def test_plan_has_no_speckit_or_specify_file_entries(tmp_path: Path):
    """SpecKit/`.specify/**` come from the launch, never from the plan (feature 045)."""
    plan = _plan(tmp_path)
    assert all("speckit-" not in a.target_rel for a in plan)
    assert all(
        not a.target_rel.startswith(".specify/templates")
        and not a.target_rel.startswith(".specify/scripts")
        for a in plan
    )


def test_plan_claude_routes_sertor_authored_surfaces(tmp_path: Path):
    """Claude: agents/skill land under `.claude/**` (historical layout, non-regression)."""
    targets = {a.target_rel for a in _plan(tmp_path, "claude")}
    assert ".claude/agents/requirements-analyst.md" in targets
    assert ".claude/agents/configuration-manager.md" in targets
    assert ".claude/skills/requirements/SKILL.md" in targets


def test_plan_copilot_cli_routes_sertor_authored_surfaces(tmp_path: Path):
    """Copilot CLI: agents AND the `requirements` skill → `.github/agents/*.agent.md` (custom-agent;
    the prompt-file vehicle was removed with the VS Code target, FEAT-012)."""
    targets = {a.target_rel for a in _plan(tmp_path, "copilot-cli")}
    assert ".github/agents/requirements-analyst.agent.md" in targets
    assert ".github/agents/configuration-manager.agent.md" in targets
    assert ".github/agents/requirements.agent.md" in targets
    assert ".github/prompts/requirements.prompt.md" not in targets


def test_plan_canonical_order(tmp_path: Path):
    """Order: Sertor-authored FILEs → constitution → generated → marker."""
    plan = _plan(tmp_path)
    kinds_targets = [(a.kind, a.target_rel, a.strategy) for a in plan]

    constitution_idx = next(
        i for i, (k, t, _) in enumerate(kinds_targets) if t == ".specify/memory/constitution.md"
    )
    init_idx = next(
        i for i, (k, t, s) in enumerate(kinds_targets) if t == ".specify/init-options.json"
    )
    marker_idx = next(
        i for i, (k, t, _) in enumerate(kinds_targets) if k is ArtifactKind.MARKER_BLOCK
    )

    last_file_idx = max(
        i for i, (k, t, _) in enumerate(kinds_targets) if t.startswith(".claude/")
    )
    assert last_file_idx < constitution_idx < init_idx < marker_idx


def test_generated_init_uses_config_generate_no_new_kind(tmp_path: Path):
    """Generated init/integration files use CONFIG + GENERATE_CONFIG (no new kind)."""
    plan = _plan(tmp_path)
    generated = [a for a in plan if a.strategy is WriteStrategy.GENERATE_CONFIG]
    assert generated, "expected generated init/integration artifacts"
    for a in generated:
        assert a.kind is ArtifactKind.CONFIG
    targets = {a.target_rel for a in generated}
    assert ".specify/init-options.json" in targets
    assert ".specify/integration.json" in targets


def test_feature_json_never_in_plan(tmp_path: Path):
    """The runtime-only `.specify/feature.json` is never an asset / artifact (DA-e)."""
    plan = _plan(tmp_path)
    assert all(not a.target_rel.endswith("feature.json") for a in plan)
    assert all(a.source is None or "feature.json" not in a.source for a in plan)


def test_marker_block_targets_claude_md_for_claude(tmp_path: Path):
    """The SDLC ritual block targets CLAUDE.md for Claude."""
    plan = _plan(tmp_path, "claude")
    markers = [a for a in plan if a.kind is ArtifactKind.MARKER_BLOCK]
    assert len(markers) == 1
    assert markers[0].target_rel == "CLAUDE.md"


def test_marker_block_targets_copilot_instructions_for_copilot_cli(tmp_path: Path):
    """The SDLC ritual block targets `.github/copilot-instructions.md` for Copilot CLI (FR-008)."""
    plan = _plan(tmp_path, "copilot-cli")
    markers = [a for a in plan if a.kind is ArtifactKind.MARKER_BLOCK]
    assert len(markers) == 1
    assert markers[0].target_rel == ".github/copilot-instructions.md"
