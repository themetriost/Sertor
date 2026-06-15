"""Polish — governance parity Claude ⊇/= Copilot (T019, contracts/governance-parity.md).

Every Sertor-authored governance surface produced for `claude` MUST be produced for `copilot` too,
with a valid container (possibly a different path), or be a declared gap. No silent omission
(FR-011). Plus: Claude and Copilot governance can coexist on one repo (different containers).
"""
from __future__ import annotations

from pathlib import Path

from sertor_flow.install_governance import build_governance_plan, execute_governance_plan
from sertor_flow.profile import build_governance_profile
from sertor_install_kit import ArtifactKind
from tests.conftest import FakeSpecifyRunner


def _logical_surfaces(assistant: str, tmp_path: Path) -> set[str]:
    """Logical Sertor-authored surfaces in the plan, keyed independent of the container path."""
    profile = build_governance_profile(tmp_path, assistant=assistant)
    plan = build_governance_plan(profile)
    surfaces: set[str] = set()
    for art in plan:
        t = art.target_rel
        if "requirements-analyst" in t:
            surfaces.add("agent:requirements-analyst")
        elif "configuration-manager" in t:
            surfaces.add("agent:configuration-manager")
        elif "requirements" in t and art.kind is ArtifactKind.FILE:
            surfaces.add("command:requirements")
        elif t.endswith("constitution.md"):
            surfaces.add("config:constitution")
        elif art.kind is ArtifactKind.MARKER_BLOCK:
            surfaces.add("instruction:sdlc-block")
        elif t == ".specify/init-options.json":
            surfaces.add("config:init-options")
        elif t == ".specify/integration.json":
            surfaces.add("config:integration")
    return surfaces


def test_copilot_covers_claude_surfaces(tmp_path: Path):
    """Copilot logical surfaces ⊇ Claude logical surfaces (no silent omission, SC-002)."""
    claude = _logical_surfaces("claude", tmp_path / "a")
    copilot = _logical_surfaces("copilot", tmp_path / "b")
    missing = claude - copilot
    assert not missing, f"Copilot is missing Claude surfaces (undeclared gap): {missing}"


def test_claude_and_copilot_coexist_on_one_repo(tmp_path: Path):
    """Installing both assistants on one repo does not collide (different containers)."""
    (tmp_path).mkdir(exist_ok=True)
    rc_claude = execute_governance_plan(
        build_governance_profile(tmp_path, assistant="claude"), runner=FakeSpecifyRunner()
    )
    rc_copilot = execute_governance_plan(
        build_governance_profile(tmp_path, assistant="copilot"), runner=FakeSpecifyRunner()
    )
    assert rc_claude.exit_code() == 0
    assert rc_copilot.exit_code() == 0
    # Claude containers
    assert (tmp_path / ".claude/agents/requirements-analyst.md").exists()
    assert (tmp_path / "CLAUDE.md").exists()
    # Copilot containers
    assert (tmp_path / ".github/agents/requirements-analyst.agent.md").exists()
    assert (tmp_path / ".github/copilot-instructions.md").exists()


def test_no_silent_gap_report(tmp_path: Path):
    """The install report names every artifact outcome — nothing omitted (FR-011)."""
    report = execute_governance_plan(
        build_governance_profile(tmp_path, assistant="copilot"), runner=FakeSpecifyRunner()
    )
    # Every plan artifact + the launch step is represented in the report.
    plan = build_governance_plan(build_governance_profile(tmp_path, assistant="copilot"))
    # +1 for the launch step recorded as its own outcome.
    assert len(report.outcomes) == len(plan) + 1
