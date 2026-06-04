"""Adapter `GitPort` via `subprocess` (l'UNICO posto dove `subprocess`/git sono importati).

Best-effort (Principio IV): git assente, radice non-repo, `returncode != 0` o qualunque eccezione
del processo → `[]`/`None`. Ogni fallimento è loggato (osservabilità, Principio IX) ma non solleva,
così la generazione del wiki ricade sul baseline invece di rompersi.
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from sertor_core.domain.ports import GitScope
from sertor_core.observability.logging import log_event


class SubprocessGitAdapter:
    """Implementazione di `GitPort` che invoca il binario `git` nella radice del repo."""

    def __init__(self, root: Path | str = "."):
        self._root = Path(root)

    def _run(self, args: list[str]) -> str | None:
        """Esegue `git <args>` nella radice; `None` (con log) su qualunque errore."""
        try:
            proc = subprocess.run(
                ["git", *args],
                cwd=str(self._root),
                capture_output=True,
                text=True,
                check=False,
            )
        except (OSError, ValueError) as exc:  # git assente o argomenti invalidi
            log_event(logging.WARNING, "git_unavailable", args=" ".join(args),
                      reason=type(exc).__name__)
            return None
        if proc.returncode != 0:
            log_event(logging.WARNING, "git_error", args=" ".join(args),
                      returncode=proc.returncode)
            return None
        return proc.stdout

    def changed_paths(self, scope: GitScope, watermark: str | None = None) -> list[str]:
        if scope == "staged":
            args = ["diff", "--name-only", "--cached"]
        elif scope == "working":
            args = ["diff", "--name-only", "HEAD"]
        else:  # since_watermark
            if not watermark:
                return []
            args = ["diff", "--name-only", f"{watermark}..HEAD"]
        out = self._run(args)
        if out is None:
            return []
        return [line.strip() for line in out.splitlines() if line.strip()]

    def head_commit(self) -> str | None:
        out = self._run(["rev-parse", "HEAD"])
        if out is None:
            return None
        sha = out.strip()
        return sha or None

    def renamed_paths(self) -> list[tuple[str, str]]:
        out = self._run(["diff", "--name-status", "-M", "HEAD"])
        if out is None:
            return []
        renames: list[tuple[str, str]] = []
        for line in out.splitlines():
            parts = line.split("\t")
            # Rinominati: `R<score>\told\tnew`.
            if len(parts) >= 3 and parts[0].startswith("R"):
                renames.append((parts[1].strip(), parts[2].strip()))
        return renames
