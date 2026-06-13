"""Installer test fixtures. `FakeCommandRunner` isolates `uv` (NFR-5: no network)."""
from __future__ import annotations

from pathlib import Path

import pytest

from sertor_installer.command_runner import CommandResult


class FakeCommandRunner:
    """Fake runner: records invoked commands, does not touch the network or real `uv`/`claude`.

    - `available=False` → simulates `uv` (and tools in general) as absent.
    - `claude_available=False` → simulates ONLY `claude` as absent (feature 016, scope local).
    - `claude_has_server=True` → `claude mcp get` returns ok (already registered → idempotent).
    - `fail_on="add"`/`"init"`/`"add-json"` → fails the command that contains that token.
    """

    def __init__(
        self,
        available: bool = True,
        fail_on: str | None = None,
        stderr: str = "boom",
        claude_available: bool | None = None,
        claude_has_server: bool = False,
    ):
        self.available = available
        self.fail_on = fail_on
        self.stderr = stderr
        # default: `claude` follows the general availability, unless explicitly overridden
        self.claude_available = available if claude_available is None else claude_available
        self.claude_has_server = claude_has_server
        self.calls: list[tuple[list[str], Path]] = []

    def is_available(self, tool: str) -> bool:
        return self.claude_available if tool == "claude" else self.available

    def run(self, cmd: list[str], cwd: Path) -> CommandResult:
        self.calls.append((list(cmd), Path(cwd)))
        # `claude mcp get <name>`: ok only if the server is "registered" (idempotent)
        if "claude" in cmd and "get" in cmd:
            return CommandResult(0 if self.claude_has_server else 1, "", "")
        if self.fail_on and self.fail_on in cmd:
            return CommandResult(1, "", self.stderr)
        return CommandResult(0, "", "")


@pytest.fixture
def make_runner():
    """Factory: `make_runner(available=False)` / `make_runner(fail_on="add")`."""
    return FakeCommandRunner
