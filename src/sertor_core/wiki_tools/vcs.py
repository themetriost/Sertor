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


def run_git(args: list[str], cwd: Path, *, stdin: str | None = None) -> tuple[int, str]:
    """Run `git <args>` at `cwd`; return `(returncode, stdout)`.

    Never raises: a missing binary, a non-repository, or any git error all surface as a non-zero
    return code, so the caller keeps the decision (fail-open, fall back, or report).
    """
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
            input=stdin,
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


def content_ids(paths: list[str], cwd: Path) -> dict[str, str] | None:
    """Content identity of each path **as it is on disk**, or `None` if it cannot be determined.

    Identity of the *content*, not of the commit: it is what makes a coverage expire on its own once
    the file changes again, and it works on content that was never committed — which is the normal
    state of a session in progress.

    One process for N paths (`--stdin-paths`), not one per path: this runs at the end of every turn,
    where the dominant cost is process startup. A path that is not a file gets `ABSENT`, because a
    deletion is work and must be coverable.

    Returns `None` — never a partial or empty dict — when git cannot answer. Fabricating an empty
    result here is exactly the silent degradation this feature removes: the caller must be able to
    say
    "I could not look" instead of "there is nothing".
    """
    from sertor_core.wiki_tools.coverage import ABSENT

    on_disk = [p for p in paths if (cwd / p).is_file()]
    ids = {p: ABSENT for p in paths}
    if not on_disk:
        return ids
    rc, out = run_git(["hash-object", "--stdin-paths"], cwd, stdin="\n".join(on_disk) + "\n")
    if rc != 0:
        return None
    hashed = out.strip().splitlines()
    if len(hashed) != len(on_disk):
        return None  # a partial answer is not an answer
    ids.update(dict(zip(on_disk, (h.strip() for h in hashed), strict=True)))
    return ids


def split_z(out: str) -> list[str]:
    """Split NUL-separated git output.

    `-z` is not a detail: without it git *quotes* paths containing spaces or non-ASCII characters,
    and this project has already paid for mis-handled paths with spaces once (E4-FEAT-011).
    """
    return [token for token in out.split("\0") if token]


def worktree_changes(cwd: Path) -> tuple[list[str], list[str]] | None:
    """`(changed, untracked)` repo-relative work-tree paths, or `None` if git could not answer.

    **Why this lives here and not in a caller (E10-FEAT-060).** Two capabilities need "what has been
    touched but not yet delivered": the pending-work `scan` behind the blocking Stop gate, and the
    per-step `ritual-check` that prepares the closure declaration. They used to answer *different*
    questions — one counted the work tree, the other only the committed diff — so the gate blocked
    while the helper reported "nothing to declare", and nothing compared the two. Deriving both from
    one place is what makes that divergence impossible rather than merely fixed once.

    The two halves come from DIFFERENT commands on purpose. `git diff HEAD` is **content-aware**: a
    file whose only difference is line-ending normalisation is *not* reported, because nothing was
    authored. `git status` reports it, and counting it would block a session over a file nobody
    edited — observed on the very first real use of the gate. `status` is therefore used only for
    what `diff` cannot see: untracked files.

    Files the VCS ignores never appear here — not because they are filtered out, but because neither
    command lets them in.

    Returns `None`, never `([], [])`, on failure: an empty change set reads as "nothing was
    touched", and this function must not be able to say that when it did not manage to look.
    """
    tracked_rc, tracked_out = run_git(["diff", "--name-only", "-z", "HEAD"], cwd)
    if tracked_rc != 0:
        return None
    paths: list[str] = split_z(tracked_out)
    untracked: list[str] = []

    # `-uall` matters: by default git COLLAPSES an untracked directory into a single entry (`src/`),
    # which would name a folder where the point is to name the files inside it.
    rc, out = run_git(["status", "--porcelain", "-z", "-uall"], cwd)
    if rc != 0:
        return None
    tokens = split_z(out)
    index = 0
    while index < len(tokens):
        entry = tokens[index]
        index += 1
        if len(entry) < 4:
            continue
        status, path = entry[:2], entry[3:]
        if "R" in status or "C" in status:
            index += 1  # a rename/copy is followed by its ORIGINAL path; we keep the destination
        if status == "??":
            paths.append(path)
            untracked.append(path)
    return paths, untracked


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
