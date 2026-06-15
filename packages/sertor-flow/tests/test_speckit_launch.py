"""US1 — `speckit_launch.launch_speckit` (T008, contracts/speckit-launch.md).

SpecKit is no longer vendored: it is obtained by LAUNCHING `specify init --ai <assistant>` via the
kit's `CommandRunner`. The runner is MOCKED here (no network, no real spec-kit): the fake simulates
success (and writes the expected layout) and the failure modes (tool absent / command failed /
layout missing). Asserts the command shape, the verification of the produced layout, and the
fail-fast on every error path.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sertor_flow.profile import build_governance_profile
from sertor_flow.speckit_launch import SPECKIT_TOOL, launch_speckit
from sertor_install_kit import CommandResult, InstallerError, Outcome


class FakeRunner:
    """CommandRunner double: records the command, optionally writes a layout, returns a result."""

    def __init__(self, *, available: bool = True, returncode: int = 0, layout=None):
        self.available = available
        self.returncode = returncode
        self.layout = layout or []  # list of relative paths to create on `run`
        self.calls: list[tuple[list[str], Path]] = []

    def is_available(self, tool: str) -> bool:
        return self.available

    def run(self, cmd: list[str], cwd: Path) -> CommandResult:
        self.calls.append((cmd, cwd))
        if self.returncode == 0:
            for rel in self.layout:
                dest = cwd / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text("x", encoding="utf-8")
        return CommandResult(self.returncode, "ok", "" if self.returncode == 0 else "boom")


# Minimal layout `specify init --ai claude` is expected to deposit.
_CLAUDE_LAYOUT = [
    ".claude/commands/speckit.specify.md",
    ".specify/templates/plan-template.md",
]
_COPILOT_LAYOUT = [
    ".github/prompts/speckit.specify.prompt.md",
    ".specify/templates/plan-template.md",
]


def test_launch_claude_runs_specify_with_ai_claude(tmp_path: Path):
    """assistant=claude → command carries `--ai claude` + the script flavor; layout → created."""
    profile = build_governance_profile(tmp_path, assistant="claude", script="ps")
    runner = FakeRunner(layout=_CLAUDE_LAYOUT)
    outcome = launch_speckit(profile, runner)
    assert outcome is Outcome.CREATED
    cmd, cwd = runner.calls[0]
    assert "--ai" in cmd and "claude" in cmd
    assert "--script" in cmd
    assert profile.speckit_version in " ".join(cmd)
    assert cwd == tmp_path


def test_launch_copilot_runs_specify_with_ai_copilot(tmp_path: Path):
    """assistant=copilot → command carries `--ai copilot`; copilot layout → created."""
    profile = build_governance_profile(tmp_path, assistant="copilot", script="bash")
    runner = FakeRunner(layout=_COPILOT_LAYOUT)
    outcome = launch_speckit(profile, runner)
    assert outcome is Outcome.CREATED
    cmd, _ = runner.calls[0]
    assert "--ai" in cmd and "copilot" in cmd


def test_launch_tool_absent_fails_fast(tmp_path: Path):
    """spec-kit not available → InstallerError with actionable message; nothing launched."""
    profile = build_governance_profile(tmp_path, assistant="claude")
    runner = FakeRunner(available=False)
    with pytest.raises(InstallerError) as exc:
        launch_speckit(profile, runner)
    assert not runner.calls  # never invoked
    assert SPECKIT_TOOL in str(exc.value) or "spec-kit" in str(exc.value).lower()


def test_launch_command_failed_fails_fast(tmp_path: Path):
    """`specify init` returns non-zero → InstallerError, no partial success swallowed."""
    profile = build_governance_profile(tmp_path, assistant="claude")
    runner = FakeRunner(returncode=1)
    with pytest.raises(InstallerError):
        launch_speckit(profile, runner)


def test_launch_layout_missing_fails_fast(tmp_path: Path):
    """Command succeeds but the expected layout is missing → InstallerError (FR-004)."""
    profile = build_governance_profile(tmp_path, assistant="claude")
    runner = FakeRunner(returncode=0, layout=[])  # writes nothing
    with pytest.raises(InstallerError):
        launch_speckit(profile, runner)


def test_launch_skips_when_already_present(tmp_path: Path):
    """Layout already on disk (re-run) → skipped, no second launch (idempotency)."""
    profile = build_governance_profile(tmp_path, assistant="claude")
    for rel in _CLAUDE_LAYOUT:
        dest = tmp_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("pre", encoding="utf-8")
    runner = FakeRunner(layout=_CLAUDE_LAYOUT)
    outcome = launch_speckit(profile, runner)
    assert outcome is Outcome.SKIPPED
    assert not runner.calls  # idempotent: no relaunch


def test_script_flavor_maps_to_specify_value(tmp_path: Path):
    """`script=ps`→`ps`, `script=bash`→`sh` for `specify init --script` (cross-platform)."""
    runner = FakeRunner(layout=_CLAUDE_LAYOUT)
    launch_speckit(build_governance_profile(tmp_path, script="ps"), runner)
    cmd_ps = runner.calls[0][0]
    idx = cmd_ps.index("--script")
    assert cmd_ps[idx + 1] == "ps"

    tmp2 = tmp_path / "b"
    tmp2.mkdir()
    runner2 = FakeRunner(layout=_CLAUDE_LAYOUT)
    launch_speckit(build_governance_profile(tmp2, script="bash"), runner2)
    cmd_sh = runner2.calls[0][0]
    idx2 = cmd_sh.index("--script")
    assert cmd_sh[idx2 + 1] == "sh"
