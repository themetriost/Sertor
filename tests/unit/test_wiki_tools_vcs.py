"""Tests for the shared VCS helpers (E10-FEAT-045, T003).

The contract these guard is "never raise, always report": the main consumer is a Stop-time gate that
must not trap a turn, and a host without git is a SUPPORTED shape (Principle X), not a fault.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from sertor_core.wiki_tools.vcs import is_repository, repo_prefix, run_git


def _git_repo(path: Path) -> None:
    """Initialise a minimal repo with one commit (identity set locally, no global config needed)."""
    path.mkdir(parents=True, exist_ok=True)
    for args in (
        ["init", "-q"],
        ["config", "user.email", "t@example.invalid"],
        ["config", "user.name", "T"],
    ):
        subprocess.run(["git", *args], cwd=str(path), capture_output=True, check=True)
    (path / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=str(path), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "seed"], cwd=str(path), capture_output=True, check=True,
    )


def test_run_git_reports_failure_without_raising(tmp_path):
    """A bad subcommand must surface as a return code, never as an exception."""
    rc, out = run_git(["definitely-not-a-git-subcommand"], tmp_path)
    assert rc != 0
    assert out == ""


def test_run_git_outside_a_repository_does_not_raise(tmp_path):
    """A plain directory is a supported host shape: report it, do not blow up."""
    rc, _ = run_git(["rev-parse", "--is-inside-work-tree"], tmp_path)
    assert rc != 0


def test_run_git_returns_stdout_on_success(tmp_path):
    _git_repo(tmp_path)
    rc, out = run_git(["rev-parse", "--is-inside-work-tree"], tmp_path)
    assert rc == 0
    assert out.strip() == "true"


def test_is_repository_true_inside_a_repo(tmp_path):
    _git_repo(tmp_path)
    assert is_repository(tmp_path) is True


def test_is_repository_false_in_a_plain_directory(tmp_path):
    """False is NOT an error: it selects the declared-proxy mode of `scan` (Principle X)."""
    plain = tmp_path / "plain"
    plain.mkdir()
    assert is_repository(plain) is False


def test_repo_prefix_empty_at_repo_root(tmp_path):
    _git_repo(tmp_path)
    assert repo_prefix(tmp_path) == ""


def test_repo_prefix_reports_subdirectory_without_slashes(tmp_path):
    """The project may live in a subdirectory of the repo; git paths must be mappable onto it."""
    _git_repo(tmp_path)
    sub = tmp_path / "nested" / "project"
    sub.mkdir(parents=True)
    assert repo_prefix(sub) == "nested/project"


def test_repo_prefix_empty_outside_a_repository(tmp_path):
    """No repo → no prefix, and no exception."""
    plain = tmp_path / "plain"
    plain.mkdir()
    assert repo_prefix(plain) == ""
