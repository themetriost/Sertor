"""Fixture dei test dell'installer. `FakeCommandRunner` isola `uv` (NFR-5: niente rete)."""
from __future__ import annotations

from pathlib import Path

import pytest

from sertor_installer.command_runner import CommandResult


class FakeCommandRunner:
    """Runner fittizio: registra i comandi invocati, non tocca rete né `uv`/`claude` reali.

    - `available=False` → simula `uv` (e in generale i tool) assenti.
    - `claude_available=False` → simula il SOLO `claude` assente (feature 016, scope local).
    - `claude_has_server=True` → `claude mcp get` ritorna ok (server già registrato → idempotenza).
    - `fail_on="add"`/`"init"`/`"add-json"` → fa fallire il comando che contiene quel token.
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
        # default: `claude` segue la disponibilità generale, salvo override esplicito
        self.claude_available = available if claude_available is None else claude_available
        self.claude_has_server = claude_has_server
        self.calls: list[tuple[list[str], Path]] = []

    def is_available(self, tool: str) -> bool:
        return self.claude_available if tool == "claude" else self.available

    def run(self, cmd: list[str], cwd: Path) -> CommandResult:
        self.calls.append((list(cmd), Path(cwd)))
        # `claude mcp get <name>`: ok solo se il server è "registrato" (idempotenza)
        if "claude" in cmd and "get" in cmd:
            return CommandResult(0 if self.claude_has_server else 1, "", "")
        if self.fail_on and self.fail_on in cmd:
            return CommandResult(1, "", self.stderr)
        return CommandResult(0, "", "")


@pytest.fixture
def make_runner():
    """Factory: `make_runner(available=False)` / `make_runner(fail_on="add")`."""
    return FakeCommandRunner
