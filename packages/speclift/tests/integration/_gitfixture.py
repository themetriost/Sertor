"""Helper per costruire un piccolo repo git temporaneo e deterministico per i test di integrazione."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

_ENV = {
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "test@example.com",
    "GIT_CONFIG_NOSYSTEM": "1",
    "HOME": "",  # evita di leggere ~/.gitconfig dell'utente
}


def _git(repo: Path, *args: str) -> str:
    import os

    env = {**os.environ, **_ENV, "HOME": str(repo)}
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    return proc.stdout.strip()


@dataclass
class GitFixture:
    path: Path
    base_sha: str
    head_sha: str


def make_repo(tmp_path: Path) -> GitFixture:
    """Crea un repo con due commit: il secondo aggiunge una funzione e il suo test."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")

    src = repo / "calc.py"
    src.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    _git(repo, "add", "calc.py")
    _git(repo, "commit", "-q", "-m", "feat: add")
    base_sha = _git(repo, "rev-parse", "HEAD")

    # Secondo commit: nuova funzione + relativo test (evidenza simbolo+test).
    src.write_text(
        "def add(a, b):\n    return a + b\n\n\ndef multiply(a, b):\n    return a * b\n",
        encoding="utf-8",
    )
    test = repo / "test_calc.py"
    test.write_text(
        "from calc import multiply\n\n\ndef test_multiply():\n    assert multiply(2, 3) == 6\n",
        encoding="utf-8",
    )
    _git(repo, "add", "calc.py", "test_calc.py")
    _git(repo, "commit", "-q", "-m", "feat: multiply + test")
    head_sha = _git(repo, "rev-parse", "HEAD")

    return GitFixture(path=repo, base_sha=base_sha, head_sha=head_sha)
