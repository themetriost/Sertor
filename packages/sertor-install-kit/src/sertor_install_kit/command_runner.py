"""Injectable boundary for external commands in the installer (R3, NFR-5).

`install rag` must invoke `uv` (init/add) on the host: the only impure side-effect of the setup
layer. It is isolated behind the `CommandRunner` Protocol so tests can use a fake (no network, no
real `uv`) and the production implementation (`SubprocessRunner`) stays thin. Does not raise on
returncode != 0: the result is returned to the caller, which decides the policy (fail-fast in the
plan).
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class CommandResult:
    """Result of an external command."""

    returncode: int
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class CommandRunner(Protocol):
    """Installer port (NOT a core port) for running external tools in a testable way."""

    def is_available(self, tool: str) -> bool: ...

    def run(
        self, cmd: list[str], cwd: Path, env: dict[str, str] | None = None
    ) -> CommandResult: ...


class SubprocessRunner:
    """Real implementation via `subprocess`. `is_available` uses `shutil.which`."""

    def is_available(self, tool: str) -> bool:
        return shutil.which(tool) is not None

    def run(
        self, cmd: list[str], cwd: Path, env: dict[str, str] | None = None
    ) -> CommandResult:
        # `env`, when given, is an OVERLAY on the current environment (not a replacement): the child
        # inherits everything plus these keys. Used to force UTF-8 on launched tools whose output
        # crashes on a legacy Windows console (cp1252) — see `speckit_launch`.
        child_env = {**os.environ, **env} if env else None
        # Decode captured output as UTF-8 with `replace` rather than the locale default: on Windows
        # the default is cp1252, which raises UnicodeDecodeError on the UTF-8 a child emits (e.g.
        # spec-kit's rich banner, forced to UTF-8 above). `errors="replace"` keeps capture lossless
        # of control flow (never crashes on odd bytes).
        proc = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True, check=False, env=child_env,
            encoding="utf-8", errors="replace",
        )
        return CommandResult(proc.returncode, proc.stdout, proc.stderr)
