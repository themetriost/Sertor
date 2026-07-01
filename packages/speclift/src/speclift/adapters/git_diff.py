"""Adapter `DiffSource` via `git` (subprocess). Nessuna dipendenza libgit (research R5).

Read-only sul repo analizzato. Exit non-zero di `git` → `InvalidRefError` (fail-loud, Constitution XI).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from speclift.domain.errors import InvalidRefError
from speclift.domain.models import STAGED_REF, ChangeKind


class GitDiffSource:
    """Ottiene il testo unified-diff eseguendo `git` nel repo indicato (default: cwd)."""

    def __init__(self, repo_path: str | Path = ".") -> None:
        self.repo_path = str(repo_path)

    def raw_diff(self, ref: str, kind: ChangeKind) -> str:
        if kind == "staged":
            args = ["diff", "--staged", "--no-color", "--unified=3"]
        elif kind == "range":
            args = ["diff", "--no-color", "--unified=3", ref]
        else:  # commit
            args = ["show", "--format=", "--no-color", "--unified=3", ref]
        return self._run(args, ref)

    def _run(self, args: list[str], ref: str) -> str:
        cmd = ["git", "-C", self.repo_path, *args]
        try:
            # Cattura byte e decodifica UTF-8 con errori sostituiti: un diff git può contenere
            # byte arbitrari (contenuto non-UTF-8); `text=True` userebbe l'encoding di locale
            # (es. cp1252 su Windows) e crollerebbe su un byte non mappabile.
            proc = subprocess.run(  # noqa: S603 — comando git fisso, niente shell
                cmd,
                capture_output=True,
                check=False,
            )
        except FileNotFoundError as exc:  # git non sul PATH
            raise InvalidRefError("`git` non trovato sul PATH") from exc

        stdout = proc.stdout.decode("utf-8", errors="replace")
        if proc.returncode != 0:
            stderr = proc.stderr.decode("utf-8", errors="replace")
            detail = stderr.strip() or stdout.strip()
            target = "diff staged" if ref == STAGED_REF else ref
            raise InvalidRefError(f"git non risolve '{target}': {detail}")
        return stdout
