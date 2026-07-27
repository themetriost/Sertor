"""`scan`: pending-work detection (FR-005; derived anchor since E10-FEAT-045).

Answers "is there work not yet recorded in the wiki?" by comparing the project's source files
against the **anchor** — the most recent recording.

Two modes, and the output always says which one produced the answer:

- **derived** (host is a git repository): the anchor is the last *commit* that touched the log, and
  the pending set is the union of what changed since it and what is still uncommitted in the work
  tree. This survives pull/merge/rebase/checkout/clone because it lives in history, not on the
  filesystem clock.
- **declared proxy** (host is not a repository, or history cannot be read): file mtimes, exactly as
  before — but reported as an estimate, with the reason.

The mtime version was not merely imprecise: `git pull` after a merge rewrites the merged files *and*
the log together, so their relative order became arbitrary and the Stop-time gate could turn
**unsatisfiable** — satisfying it required writing to the wiki again, which produced more work to
merge, which reproduced the condition. A `pending == 0` was a race won, not a correct answer.

Host-agnostic by design (Principle X): a host without version control is a *supported* shape, not a
fault, so git is never required — only used when present, and its absence is declared, never silent
(Principle XII/XIV).
"""
from __future__ import annotations

import fnmatch
import logging
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from sertor_core.observability.logging import log_event
from sertor_core.wiki_tools.contracts import ScanResult
from sertor_core.wiki_tools.profile import WikiProfile
from sertor_core.wiki_tools.vcs import git_available, is_repository, repo_prefix, run_git

ANCHOR_GIT = "git"
ANCHOR_MTIME = "mtime"

# Closed taxonomy: a proxy that cannot say WHY it is a proxy lets the reader invent an explanation.
REASON_NOT_A_REPOSITORY = "not_a_repository"
REASON_GIT_UNAVAILABLE = "git_unavailable"
REASON_LOG_NEVER_COMMITTED = "log_never_committed"

_DEFAULT_PATHS_LIMIT = 10


@dataclass(frozen=True)
class _Anchor:
    """The most recent recording, carrying **its own nature** (that is the whole point)."""

    kind: str | None
    timestamp: float | None
    ref: str | None = None
    fallback_reason: str | None = None


def _is_excluded(rel_parts: tuple[str, ...], patterns: list[str]) -> bool:
    """`True` if any path segment matches an exclusion pattern (glob)."""
    for part in rel_parts:
        for pattern in patterns:
            if fnmatch.fnmatch(part, pattern):
                return True
    return False


def _file_mtime(path: Path) -> float | None:
    """mtime of a non-empty file (None if absent/empty/unreadable)."""
    if not path.is_file():
        return None
    try:
        if path.stat().st_size == 0:
            return None
        return path.stat().st_mtime
    except OSError:
        return None


def _latest_log_mtime(profile: WikiProfile) -> float | None:
    """Time anchor of the last log entry (the PROXY; see module docstring).

    Rotation active → mtime of the **most recent partition** (max over `YYYY-MM-DD.md` files,
    excluding the index). Single-file mode (back-compat) → mtime of the single log file. In both
    cases: absent/empty → `None` (everything is pending).
    """
    if profile.rotation_enabled:
        log_dir = profile.log_dir_path
        if not log_dir.is_dir():
            return None
        mtimes = [
            m
            for p in log_dir.glob("*.md")
            if p.name != profile.log_index_file
            and (m := _file_mtime(p)) is not None
        ]
        return max(mtimes) if mtimes else None
    return _file_mtime(profile.log_path)


def _log_target(profile: WikiProfile) -> Path:
    """The log location the anchor is derived from: the partition directory, or the single file."""
    return profile.log_dir_path if profile.rotation_enabled else profile.log_path


def _relative_to_project(profile: WikiProfile, path: Path) -> str | None:
    """`path` expressed relative to the project root, POSIX-style (None if outside)."""
    try:
        return path.relative_to(profile.config_dir).as_posix()
    except ValueError:
        return None


def _split_z(out: str) -> list[str]:
    """Split NUL-separated git output.

    `-z` is not a detail: without it git *quotes* paths containing spaces or non-ASCII characters,
    and this project has already paid for mis-handled paths with spaces once (E4-FEAT-011).
    """
    return [token for token in out.split("\0") if token]


def _git_anchor(profile: WikiProfile) -> _Anchor:
    """Derive the anchor from the last commit that touched the log; declare it if impossible."""
    target = _relative_to_project(profile, _log_target(profile))
    pathspec = [] if target is None else ["--", target]
    rc, out = run_git(["log", "-1", "--format=%H %ct", *pathspec], profile.config_dir)
    head = out.strip().splitlines()[0] if (rc == 0 and out.strip()) else ""
    if not head or " " not in head:
        # A repository whose log has never been committed: a new host, or a truncated history.
        return _Anchor(
            kind=ANCHOR_MTIME,
            timestamp=_latest_log_mtime(profile),
            fallback_reason=REASON_LOG_NEVER_COMMITTED,
        )
    sha, _, epoch = head.partition(" ")
    try:
        timestamp = float(epoch)
    except ValueError:  # pragma: no cover - git always emits a number for %ct
        timestamp = None
    return _Anchor(kind=ANCHOR_GIT, timestamp=timestamp, ref=sha)


def _resolve_anchor(profile: WikiProfile) -> _Anchor:
    """Pick the mode. Falling back is legitimate; falling back *silently* is not."""
    if is_repository(profile.config_dir):
        return _git_anchor(profile)
    reason = REASON_NOT_A_REPOSITORY if git_available() else REASON_GIT_UNAVAILABLE
    return _Anchor(
        kind=ANCHOR_MTIME, timestamp=_latest_log_mtime(profile), fallback_reason=reason,
    )


def _committed_since(profile: WikiProfile, ref: str) -> list[str]:
    """Repo-relative paths changed between `ref` and HEAD.

    Two-dot is correct here: `git log` only walks HEAD's history, so `ref` is always an ancestor.
    """
    rc, out = run_git(["diff", "--name-only", "-z", ref, "HEAD"], profile.config_dir)
    return _split_z(out) if rc == 0 else []


def _worktree_changes(profile: WikiProfile) -> list[str]:
    """Repo-relative paths modified or untracked in the work tree.

    Indispensable, not a refinement: at Stop time the session's work is typically **not yet
    committed**, so an anchor made of history alone would never see the very case the gate exists
    for. Files the VCS ignores never appear here — which is how E10-FEAT-048 is absorbed: not by
    filtering them out, but by never letting them in.

    The two halves come from DIFFERENT commands on purpose. `git diff HEAD` is **content-aware**: a
    file whose only difference is line-ending normalisation is *not* reported, because nothing was
    authored. `git status` reports it, and counting it would block a session over a file nobody
    edited — observed on the very first real use of this gate. `status` is therefore used only for
    what `diff` cannot see: untracked files.
    """
    tracked_rc, tracked_out = run_git(
        ["diff", "--name-only", "-z", "HEAD"], profile.config_dir,
    )
    paths: list[str] = _split_z(tracked_out) if tracked_rc == 0 else []

    # `-uall` matters: by default git COLLAPSES an untracked directory into a single entry (`src/`),
    # which would name a folder where the point is to name the files inside it.
    rc, out = run_git(["status", "--porcelain", "-z", "-uall"], profile.config_dir)
    if rc != 0:
        return paths
    tokens = _split_z(out)
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
    return paths


def _to_project_paths(profile: WikiProfile, repo_paths: list[str]) -> list[str]:
    """Map repo-root-relative paths onto the project root (they differ when nested in a repo)."""
    prefix = repo_prefix(profile.config_dir)
    if not prefix:
        return list(repo_paths)
    head = f"{prefix}/"
    return [p[len(head):] for p in repo_paths if p.startswith(head)]


def _in_scope(profile: WikiProfile, project_rel: str) -> bool:
    """True if the path lives under a configured source dir and survives the host's exclusions."""
    for source in profile.source_dirs:
        base = source.strip("/")
        if project_rel == base or project_rel.startswith(f"{base}/"):
            rest = project_rel[len(base):].strip("/")
            return not _is_excluded(tuple(rest.split("/")), profile.exclude)
    return False


def _today_recording(profile: WikiProfile) -> str | None:
    """Project-relative path of TODAY's log partition (or the single log file)."""
    target = (
        profile.partition_path(date.today())
        if profile.rotation_enabled
        else profile.log_path
    )
    return _relative_to_project(profile, target)


def _stale_recording(profile: WikiProfile, touched_logs: list[str]) -> str | None:
    """An uncommitted log partition that is NOT today's — it does not count, but must be named.

    Without naming it the host sees an already-modified journal and a gate that blocks anyway, and
    the diagnosis becomes an investigation (FR-004a).
    """
    today = _today_recording(profile)
    others = sorted(p for p in touched_logs if p != today)
    return others[-1] if others else None


def _paths_limit(profile: WikiProfile) -> int:
    """How many paths to name. Config `[ritual].pending_paths_limit`; default 10 (readability)."""
    value = profile.ritual.get("pending_paths_limit")
    return value if isinstance(value, int) and value > 0 else _DEFAULT_PATHS_LIMIT


def _pending_by_mtime(profile: WikiProfile, anchor: float | None) -> list[str]:
    """The proxy: source files whose clock is newer than the anchor's."""
    pending: list[str] = []
    for source in profile.source_dirs:
        base = profile.config_dir / source
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(base)
            if _is_excluded(rel.parts, profile.exclude):
                continue
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            if anchor is None or mtime > anchor:
                project_rel = _relative_to_project(profile, path)
                if project_rel is not None:
                    pending.append(project_rel)
    return sorted(pending)


def scan(profile: WikiProfile) -> ScanResult:
    """Report the work not yet recorded in the wiki, and how that answer was obtained.

    Absent anchor (missing/empty log) → everything is pending. `message` comes from the profile's
    localised `strings` and is left **verbatim** unless the host opts in with a `{files}`
    placeholder: it is the host's string, and naming the files belongs to the human/consumer
    rendering, not to a template the host controls.
    """
    anchor = _resolve_anchor(profile)
    dirs_scanned = [s for s in profile.source_dirs if (profile.config_dir / s).is_dir()]
    stale: str | None = None

    if anchor.kind == ANCHOR_GIT and anchor.ref:
        worktree = _to_project_paths(profile, _worktree_changes(profile))
        touched = _to_project_paths(profile, _committed_since(profile, anchor.ref)) + worktree
        today = _today_recording(profile)
        recorded_today = today is not None and today in worktree
        log_root = _relative_to_project(profile, _log_target(profile)) or ""
        touched_logs = [p for p in worktree if log_root and p.startswith(log_root)]
        stale = _stale_recording(profile, touched_logs)
        pending_paths = (
            [] if recorded_today else sorted({p for p in touched if _in_scope(profile, p)})
        )
    else:
        pending_paths = _pending_by_mtime(profile, anchor.timestamp)

    pending = len(pending_paths)
    anchor_iso = (
        datetime.fromtimestamp(anchor.timestamp).isoformat(timespec="seconds")
        if anchor.timestamp is not None
        else None
    )
    limit = _paths_limit(profile)
    shown, truncated = pending_paths[:limit], max(0, pending - limit)

    template = profile.strings.get(
        "pending" if pending else "clean",
        "{n} file(s) newer than the last log entry."
        if pending
        else "No files newer than the last log entry.",
    )
    message = template.replace("{n}", str(pending)).replace("{files}", ", ".join(shown))

    result = ScanResult(
        pending=pending,
        anchor=anchor_iso,
        dirs_scanned=dirs_scanned,
        message=message,
        anchor_kind=anchor.kind,
        anchor_ref=anchor.ref,
        anchor_fallback_reason=anchor.fallback_reason,
        pending_paths=shown,
        pending_truncated=truncated,
        stale_recording=stale,
    )
    log_event(
        logging.INFO,
        "scan",
        profile=profile.profile,
        pending=pending,
        anchor=anchor_iso,
        anchor_kind=anchor.kind,
        anchor_fallback_reason=anchor.fallback_reason,
        dirs_scanned=len(dirs_scanned),
    )
    return result
