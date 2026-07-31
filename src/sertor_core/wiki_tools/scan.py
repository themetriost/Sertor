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
from sertor_core.wiki_tools import coverage
from sertor_core.wiki_tools.contracts import ScanResult
from sertor_core.wiki_tools.profile import WikiProfile
from sertor_core.wiki_tools.vcs import (
    content_ids,
    git_available,
    is_repository,
    repo_prefix,
    run_git,
    split_z,
    worktree_changes,
)

ANCHOR_GIT = "git"
ANCHOR_MTIME = "mtime"

DETERMINATION_OK = "ok"
DETERMINATION_FAILED = "failed"

# Closed taxonomy, same reasoning as the anchor fallbacks: a failure that cannot say WHY lets the
# reader invent an explanation.
REASON_VCS_UNREADABLE = "vcs_unreadable"

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


def _committed_since(profile: WikiProfile, ref: str) -> list[str] | None:
    """Repo-relative paths changed between `ref` and HEAD, or `None` if git could not answer.

    Two-dot is correct here: `git log` only walks HEAD's history, so `ref` is always an ancestor.

    `None`, never `[]`, on failure: an empty change set reads as "nothing to record", and this
    function must not be able to say that when it did not manage to look (E10-FEAT-062).
    """
    rc, out = run_git(["diff", "--name-only", "-z", ref, "HEAD"], profile.config_dir)
    return split_z(out) if rc == 0 else None


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


def _journal_files(profile: WikiProfile) -> list[Path]:
    """Every file that can carry a recording: the partitions, or the single log file."""
    if not profile.rotation_enabled:
        return [profile.log_path] if profile.log_path.is_file() else []
    log_dir = profile.log_dir_path
    if not log_dir.is_dir():
        return []
    return sorted(p for p in log_dir.glob("*.md") if p.name != profile.log_index_file)


def _coverage_and_legacy(
    profile: WikiProfile, untracked: list[str],
) -> tuple[set[coverage.CoveredItem], int]:
    """The union of every declared coverage, plus how many recordings are honoured for
    compatibility.

    **The compatibility rule is deliberately narrow** (research R4). Read literally — *"an entry
    with
    no coverage block covers everything"* — it would blind the gate forever, because every journal
    holds entries written before this capability existed and one of them would be enough. Restricted
    to journal files that are **not yet delivered**, it does the job it was created for (do not
    block a
    host on its first upgrade over work it considers recorded) and extinguishes itself: once that
    file
    is committed the anchor moves past it. Real duration: one session.

    Delivered entries need no rule at all — the work they described is older than the anchor.

    The rule keys on **today's** partition, and that is the one place a date survives — on purpose.
    It
    is not the new logic: it is a shim that reproduces, for entries written before coverage existed,
    exactly the behaviour it replaces (which was date-based). It must not be wider than what it
    replaces either: an uncommitted entry from *another* day never counted as a recording (FR-015)
    and
    must keep not counting.
    """
    covered: set[coverage.CoveredItem] = set()
    legacy = 0
    never_delivered = set(untracked)
    today = _today_recording(profile)
    for path in _journal_files(profile):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        covered |= coverage.parse(text)
        rel = _relative_to_project(profile, path)
        if (
            rel is not None
            and rel == today
            and rel in never_delivered
            and not coverage.has_block(text)
            and coverage.has_entry(text, profile.log_format)
        ):
            legacy += 1
    return covered, legacy


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


def _undetermined(
    profile: WikiProfile, anchor: _Anchor, dirs_scanned: list[str], reason: str,
) -> ScanResult:
    """The outcome when the question could not be answered — declared, never dressed up as clean.

    `pending` is 0 because there is no list to report, and that is precisely why `determination` has
    to travel with it: the consumers must be able to tell "nothing to record" from "I could not
    look".
    """
    anchor_iso = (
        datetime.fromtimestamp(anchor.timestamp).isoformat(timespec="seconds")
        if anchor.timestamp is not None
        else None
    )
    result = ScanResult(
        pending=0,
        anchor=anchor_iso,
        dirs_scanned=dirs_scanned,
        message=profile.strings.get("undetermined", "Could not determine pending work."),
        anchor_kind=anchor.kind,
        anchor_ref=anchor.ref,
        anchor_fallback_reason=anchor.fallback_reason,
        determination=DETERMINATION_FAILED,
        determination_reason=reason,
    )
    log_event(
        logging.WARNING, "scan", profile=profile.profile,
        determination=DETERMINATION_FAILED, determination_reason=reason,
    )
    return result


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
    determination, determination_reason, legacy = DETERMINATION_OK, None, 0

    if anchor.kind == ANCHOR_GIT and anchor.ref:
        worktree_pair = worktree_changes(profile.config_dir)
        raw_committed = _committed_since(profile, anchor.ref)
        if worktree_pair is None or raw_committed is None:
            # Could not look. Saying `pending: 0` here would be indistinguishable from a clean
            # project — the false-clean this feature removes (US2).
            return _undetermined(profile, anchor, dirs_scanned, REASON_VCS_UNREADABLE)

        raw_worktree, raw_untracked = worktree_pair
        worktree = _to_project_paths(profile, raw_worktree)
        untracked = _to_project_paths(profile, raw_untracked)
        touched = _to_project_paths(profile, raw_committed) + worktree
        log_root = _relative_to_project(profile, _log_target(profile)) or ""
        touched_logs = [p for p in worktree if log_root and p.startswith(log_root)]
        stale = _stale_recording(profile, touched_logs)

        in_scope = sorted({p for p in touched if _in_scope(profile, p)})
        covered, legacy = _coverage_and_legacy(profile, untracked)
        if legacy:
            pending_paths = []          # compatibility, and DECLARED via `legacy_coverage`
        else:
            ids = content_ids(in_scope, profile.config_dir)
            if ids is None:
                return _undetermined(profile, anchor, dirs_scanned, REASON_VCS_UNREADABLE)
            pending_paths = [
                p for p in in_scope if not coverage.covers(covered, p, ids[p])
            ]
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
        determination=determination,
        determination_reason=determination_reason,
        legacy_coverage=legacy,
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
        determination=determination,
        legacy_coverage=legacy,
    )
    return result
