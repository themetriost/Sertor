"""Guard: the dogfood runtime re-lock stays correct and dogfood-only (E15-FEAT-008).

Two invariants this feature must not regress:

1. Tracking of the runtime lock. `.sertor/uv.lock` is a VOLATILE artifact (it pins the
   resolved `sertor-core` commit and is rewritten by the post-merge re-lock). Committing it
   would create churn (a diff every merge) and a potential loop. It must be git-ignored and
   untracked; only the stable spec `.sertor/pyproject.toml` stays tracked.
2. Dogfood-only boundary. The re-lock is dogfood-only (hosts pin a version and get the
   auto-updater, E2-FEAT-013; they do NOT track HEAD). The mechanism
   `scripts/dev/relock-runtime.ps1` must never leak into distributed assets nor into the
   `rag-freshness.ps1` host hook.

Offline and presence-agnostic: asserts git-tracking and absences, never that a regenerable
artifact is present, so it passes in CI and on a fresh clone.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=_REPO_ROOT, capture_output=True, text=True, check=True
    )
    return out.stdout.splitlines()


def test_runtime_lock_not_tracked():
    tracked = set(_tracked_files())
    assert ".sertor/uv.lock" not in tracked, (
        ".sertor/uv.lock must NOT be tracked (volatile runtime lock; tracking it causes "
        "churn/loop on every re-lock, E15-FEAT-008). Run `git rm --cached .sertor/uv.lock`."
    )


def test_runtime_pyproject_stays_tracked():
    tracked = set(_tracked_files())
    assert ".sertor/pyproject.toml" in tracked, (
        ".sertor/pyproject.toml must stay tracked (the stable runtime spec); do not "
        "over-ignore the .sertor/ directory."
    )


def test_runtime_lock_is_gitignored():
    gitignore = (_REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert any(
        line.strip() in ("**/.sertor/uv.lock", ".sertor/uv.lock")
        for line in gitignore.splitlines()
    ), ".gitignore must ignore the runtime lock (e.g. `**/.sertor/uv.lock`), E15-FEAT-008."


def test_relock_script_not_in_distributed_assets():
    offenders = sorted(
        p.relative_to(_REPO_ROOT).as_posix()
        for p in _REPO_ROOT.glob("packages/**/assets/**/relock-runtime.ps1")
    )
    assert not offenders, (
        "relock-runtime.ps1 must stay dogfood-only (scripts/dev/), never bundled into "
        f"distributed assets (E15-FEAT-008): {offenders}"
    )


def test_relock_not_referenced_by_rag_freshness_hooks():
    offenders: list[str] = []
    for hook in _REPO_ROOT.glob("**/rag-freshness*.ps1"):
        if "relock-runtime" in hook.read_text(encoding="utf-8"):
            offenders.append(hook.relative_to(_REPO_ROOT).as_posix())
    assert not offenders, (
        "the distributed rag-freshness hook must NOT reference the dogfood-only "
        f"relock-runtime script (would leak HEAD-tracking to hosts, E15-FEAT-008): {offenders}"
    )
