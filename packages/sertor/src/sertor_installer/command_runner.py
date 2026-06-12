"""Confine iniettabile sui comandi esterni dell'installer (R3, NFR-5).

`install rag` deve lanciare `uv` (init/add) sull'ospite: l'unico side-effect non puro del layer
di setup. Lo si isola dietro il Protocol `CommandRunner` così i test usano un fake (nessuna rete,
nessun `uv` reale) e l'impl di produzione (`SubprocessRunner`) resta sottile. Non solleva su
returncode != 0: l'esito è dato a chi chiama, che decide la policy (fail-fast nel piano).
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class CommandResult:
    """Esito di un comando esterno."""

    returncode: int
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class CommandRunner(Protocol):
    """Porta dell'installer (NON del core) per eseguire tool esterni in modo testabile."""

    def is_available(self, tool: str) -> bool: ...

    def run(self, cmd: list[str], cwd: Path) -> CommandResult: ...


class SubprocessRunner:
    """Impl reale via `subprocess`. `is_available` usa `shutil.which`."""

    def is_available(self, tool: str) -> bool:
        return shutil.which(tool) is not None

    def run(self, cmd: list[str], cwd: Path) -> CommandResult:
        proc = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True, check=False
        )
        return CommandResult(proc.returncode, proc.stdout, proc.stderr)
