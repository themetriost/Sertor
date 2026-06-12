"""Fixture dei test dell'installer. `FakeCommandRunner` isola `uv` (NFR-5: niente rete)."""
from __future__ import annotations

from pathlib import Path

import pytest

from sertor_installer.command_runner import CommandResult


class FakeCommandRunner:
    """Runner fittizio: registra i comandi invocati, non tocca rete né `uv` reale.

    - `available=False` → simula `uv` assente.
    - `fail_on="add"`/`"init"` → fa fallire il comando che contiene quel token (returncode 1).
    """

    def __init__(self, available: bool = True, fail_on: str | None = None, stderr: str = "boom"):
        self.available = available
        self.fail_on = fail_on
        self.stderr = stderr
        self.calls: list[tuple[list[str], Path]] = []

    def is_available(self, tool: str) -> bool:
        return self.available

    def run(self, cmd: list[str], cwd: Path) -> CommandResult:
        self.calls.append((list(cmd), Path(cwd)))
        if self.fail_on and self.fail_on in cmd:
            return CommandResult(1, "", self.stderr)
        return CommandResult(0, "", "")


@pytest.fixture
def make_runner():
    """Factory: `make_runner(available=False)` / `make_runner(fail_on="add")`."""
    return FakeCommandRunner
