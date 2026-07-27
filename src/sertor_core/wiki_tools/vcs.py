"""Shared version-control helpers for the wiki tools (E10-FEAT-045).

Extracted from `ritual_check.py` so that BOTH the ritual-candidate discovery and the pending-work
`scan` derive facts from the same machinery. Before the extraction the two lived two files apart and
measured *different realities* — one derived from git, the other estimated from file clocks — the
exact signature Principle XIV forbids (a derivable fact kept as a copy, nothing reconciling them).

Design rules for everything in here:

- **Never raise.** Every helper returns a value the caller can branch on. The main consumer is a
  Stop-time gate that must never trap a turn: an exception escaping from here would turn "this host
  has no git" — a *supported* configuration (Principle X) — into a failure.
- **Never assume a repository.** Absence of git is a normal host shape, not a fault. Callers decide
  what to do; this module only reports what is true.
- **stdlib only, offline, zero LLM.** Same contract as the rest of `wiki_tools`.
"""
from __future__ import annotations

import subprocess
from pathlib import Path


def run_git(args: list[str], cwd: Path) -> tuple[int, str]:
    """Run `git <args>` at `cwd`; return `(returncode, stdout)`.

    Never raises: a missing binary, a non-repository, or any git error all surface as a non-zero
    return code, so the caller keeps the decision (fail-open, fall back, or report).
    """
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
        )
    except OSError:
        return 1, ""
    return proc.returncode, proc.stdout


def git_available() -> bool:
    """True if a `git` binary can be executed at all.

    Only meaningful in the fallback path: it separates "this host has no git installed" from "this
    host has git but is not a repository". Both fall back to the mtime proxy, but they are different
    facts and the contract reports which one — a proxy that cannot say *why* it is a proxy is the
    defect this module exists to remove.
    """
    rc, _ = run_git(["--version"], Path.cwd())
    return rc == 0


def is_repository(cwd: Path) -> bool:
    """True if `cwd` sits inside a git work tree.

    Distinguishes the two supported host shapes. A `False` here is NOT an error: it selects the
    declared-proxy mode of `scan` (Principle X — the capability works on non-git hosts too).
    """
    rc, out = run_git(["rev-parse", "--is-inside-work-tree"], cwd)
    return rc == 0 and out.strip() == "true"


def repo_prefix(cwd: Path) -> str:
    """Path of `cwd` relative to the repository root, without leading/trailing slashes.

    git reports paths relative to the REPO ROOT, while the wiki profile anchors them to the project
    directory; when the project lives in a subdirectory of the repo the two differ. Empty string
    when `cwd` IS the repo root (or when git cannot answer).
    """
    rc, out = run_git(["rev-parse", "--show-prefix"], cwd)
    if rc != 0:
        return ""
    return out.strip().strip("/")
