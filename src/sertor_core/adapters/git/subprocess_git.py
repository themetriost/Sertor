"""Implementazione di `GitPort` via `subprocess` (adapter, fuori dal dominio).

Avvolge i comandi `git` necessari alla verifica incrementale (US3): file cambiati per scope,
commit di HEAD, rename. Best-effort: ogni fallimento (non un repo, git assente, comando in errore)
degrada a `[]`/`None` senza sollevare, così il chiamante ripiega su baseline (REQ-091). Nessun
import di questo modulo dal dominio.
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from sertor_core.domain.ports import GitScope
from sertor_core.observability.logging import log_event


class SubprocessGitAdapter:
    """`GitPort` concreto basato sulla CLI `git`.

    `repo_root` è la radice del repo (default: cwd). I path restituiti sono relativi alla radice
    del repo, in stile POSIX (come li emette git).
    """

    name = "subprocess-git"

    def __init__(self, repo_root: str | Path = "."):
        self.repo_root = Path(repo_root)

    def _run(self, *args: str) -> str | None:
        """Esegue `git <args>` nella radice repo; ritorna stdout o `None` in caso di errore."""
        try:
            proc = subprocess.run(
                ["git", *args],
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                check=False,
            )
        except (OSError, ValueError) as exc:  # git assente, cwd inesistente, ...
            log_event(logging.WARNING, "git_subprocess_error", args=" ".join(args), error=str(exc))
            return None
        if proc.returncode != 0:
            log_event(logging.WARNING, "git_subprocess_nonzero", args=" ".join(args),
                      code=proc.returncode, stderr=proc.stderr.strip()[:200])
            return None
        return proc.stdout

    def changed_paths(self, scope: GitScope, watermark: str | None = None) -> list[str]:
        if scope == "staged":
            out = self._run("diff", "--name-only", "--cached")
        elif scope == "working":
            # working tree vs HEAD: include modifiche staged e non staged, ma non gli untracked.
            out = self._run("diff", "--name-only", "HEAD")
        elif scope == "since_watermark":
            if not watermark:
                return []
            out = self._run("diff", "--name-only", f"{watermark}..HEAD")
        else:  # scope sconosciuto: nessuna assunzione
            return []
        if out is None:
            return []
        return [line.strip() for line in out.splitlines() if line.strip()]

    def head_commit(self) -> str | None:
        out = self._run("rev-parse", "HEAD")
        if out is None:
            return None
        sha = out.strip()
        return sha or None

    def renamed_paths(self) -> list[tuple[str, str]]:
        out = self._run("diff", "--name-status", "-M", "HEAD")
        if out is None:
            return []
        renames: list[tuple[str, str]] = []
        for line in out.splitlines():
            parts = line.split("\t")
            # Formato rename: "R<score>\told\tnew"
            if parts and parts[0].startswith("R") and len(parts) >= 3:
                renames.append((parts[1].strip(), parts[2].strip()))
        return renames
