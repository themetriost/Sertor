"""Shared test fixtures for `sertor-flow` (feature 045).

The SpecKit launch (`specify init`) is ALWAYS mocked in tests: no network, no real spec-kit. The
`FakeSpecifyRunner` simulates `specify init --ai <assistant>` by depositing a representative layout
for the assistant, so the governance install path runs end-to-end hermetically.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sertor_install_kit import CommandResult

# Representative layouts the mocked `specify init` deposits per assistant.
CLAUDE_LAUNCH_LAYOUT = (
    ".claude/commands/speckit.specify.md",
    ".claude/commands/speckit.plan.md",
    ".claude/agents/speckit-specify.md",
    ".specify/templates/plan-template.md",
    ".specify/scripts/bash/check-prerequisites.sh",
    ".specify/scripts/powershell/check-prerequisites.ps1",
)
COPILOT_LAUNCH_LAYOUT = (
    ".github/prompts/speckit.specify.prompt.md",
    ".github/prompts/speckit.plan.prompt.md",
    ".github/agents/speckit-specify.agent.md",
    ".specify/templates/plan-template.md",
    ".specify/scripts/bash/check-prerequisites.sh",
    ".specify/scripts/powershell/check-prerequisites.ps1",
)


class FakeSpecifyRunner:
    """CommandRunner double: simulates `specify init` depositing the right layout per assistant.

    Picks the layout from the `--ai <assistant>` flag of the command, so the same runner works for
    both Claude and Copilot installs.
    """

    def __init__(self, *, available: bool = True, returncode: int = 0):
        self.available = available
        self.returncode = returncode
        self.calls: list[tuple[list[str], Path]] = []

    def is_available(self, tool: str) -> bool:
        return self.available

    def run(
        self, cmd: list[str], cwd: Path, env: dict[str, str] | None = None
    ) -> CommandResult:
        self.calls.append((cmd, cwd))
        if self.returncode != 0:
            return CommandResult(self.returncode, "", "boom")
        assistant = cmd[cmd.index("--ai") + 1] if "--ai" in cmd else "claude"
        layout = COPILOT_LAUNCH_LAYOUT if assistant == "copilot" else CLAUDE_LAUNCH_LAYOUT
        for rel in layout:
            dest = cwd / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text("# speckit asset (mocked launch)\n", encoding="utf-8")
        return CommandResult(0, "ok", "")


@pytest.fixture()
def fake_runner() -> FakeSpecifyRunner:
    """A fresh `FakeSpecifyRunner` (success path) for governance install tests."""
    return FakeSpecifyRunner()
