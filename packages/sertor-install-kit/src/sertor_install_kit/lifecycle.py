"""Lifecycle primitives for `upgrade`/`uninstall` (feature 048, data-model §4/§6).

This module hosts the inverse/lifecycle helpers that do NOT attach to an existing additive file
(`update_file_if_changed`, `remove_path`, `deregister_mcp_client`), the static Sertor-owned-path
value objects (`SertorOwnedPaths`/`SharedEdit`/`SharedEditKind`, decision D3), and the verb-aware
orchestrator `execute_lifecycle`. The other inverse functions live next to their additive dual
(`remove_marker_block` in `claude_md`, `remove_settings_entries` in `settings_merge`, etc.) so the
anti-drift "same file, same recognition logic" holds.

stdlib-only (NFR-07): no dependency on `sertor-core`/`sertor`/`sertor-flow`. The lifecycle
primitives never raise for absence (idempotency, FR-026) and never touch anything outside the path
they are given (FR-031/FR-050).
"""
from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from sertor_install_kit.artifacts import Artifact, ArtifactOutcome, LifecycleOp, Outcome
from sertor_install_kit.command_runner import CommandRunner
from sertor_install_kit.errors import ConfigError, InstallerError
from sertor_install_kit.report import InstallReport

_CLAUDE = "claude"
_SERVER_NAME = "sertor-rag"


class McpRegistrationError(InstallerError):
    """MCP (de)registration in `local` scope failed: `claude` not found or command failed.

    Lives in the kit (not in `sertor`) so both vehicles reuse the same de-registration primitive
    (`deregister_mcp_client`) without duplicating it (SC-010). It is an `InstallerError`, so the
    executor's fail-fast catches it.
    """


# --- D3 static ownership value objects ----------------------------------------------------------


class SharedEditKind(StrEnum):
    """Kind of Sertor-owned portion inside a SHARED host file (data-model §4)."""

    MARKER = "marker"        # a marker-delimited block (e.g. SERTOR:RAG-USAGE)
    SETTINGS = "settings"    # hook entries whose `command` is Sertor's
    GITIGNORE = "gitignore"  # the RUNTIME_IGNORES lines + header
    MCP_ENTRY = "mcp_entry"  # the `sertor-rag` server entry under a root key


@dataclass(frozen=True)
class SharedEdit:
    """A shared host file with a Sertor-owned portion (data-model §4).

    `key` is the selector of the Sertor portion: a marker pair (MARKER), a fragment of Sertor hook
    commands (SETTINGS), `RUNTIME_IGNORES` (GITIGNORE), or `"sertor-rag"` + root_key (MCP_ENTRY).
    """

    target_rel: str
    kind: SharedEditKind
    key: str

    def __post_init__(self) -> None:
        rel = self.target_rel.replace("\\", "/")
        if rel.startswith("/") or (len(rel) > 1 and rel[1] == ":"):
            raise ConfigError("target_rel must be relative", key=self.target_rel)
        if ".." in rel.split("/"):
            raise ConfigError("target_rel must not ascend with '..'", key=self.target_rel)


@dataclass(frozen=True)
class SertorOwnedPaths:
    """Static declaration of the Sertor-owned paths for a (capability, assistant) pair (D3).

    The guard-rail that replaces a persisted manifest: a coverage test asserts that every
    `target_rel` produced by the plan-builder falls into `owned_dirs ∪ owned_files ∪
    {e.target_rel for e in shared_edits}` (FR-017).
    """

    owned_dirs: tuple[str, ...] = ()
    owned_files: tuple[str, ...] = ()
    shared_edits: tuple[SharedEdit, ...] = field(default=())

    def covered_targets(self) -> set[str]:
        """All `target_rel` this declaration owns (dirs + files + shared)."""
        return (
            set(self.owned_dirs)
            | set(self.owned_files)
            | {e.target_rel for e in self.shared_edits}
        )


# --- standalone lifecycle primitives ------------------------------------------------------------


def update_file_if_changed(dest: Path, content: bytes | str) -> Outcome:
    """Writes `content` to `dest` only if it differs — for standalone (FILE) assets.

    - `dest` absent → create it (`CREATED`);
    - `dest` present, content differs → overwrite (`UPDATED`);
    - `dest` present, content equal → no-op (`SKIPPED`).

    For `str` content the comparison is **text-mode, line-ending insensitive** (`\\r\\n` vs `\\n`):
    the install path writes assets via `write_text` (platform newline) while the bundled asset uses
    `\\n`, so a byte compare would spuriously flag an aligned host as `UPDATED`. The write also uses
    `write_text`, matching the install path exactly (idempotency on re-run). `bytes` content is
    compared/written verbatim.
    """
    if isinstance(content, str):
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            return Outcome.CREATED
        current = dest.read_text(encoding="utf-8")
        if current.replace("\r\n", "\n") == content.replace("\r\n", "\n"):
            return Outcome.SKIPPED
        dest.write_text(content, encoding="utf-8")
        return Outcome.UPDATED
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        return Outcome.CREATED
    if dest.read_bytes() == content:
        return Outcome.SKIPPED
    dest.write_bytes(content)
    return Outcome.UPDATED


def remove_path(dest: Path) -> Outcome:
    """Removes a file or a whole tree at `dest`; absent → `SKIPPED` (idempotency, FR-026).

    Never touches anything outside `dest` (FR-031/FR-050). A directory is removed in block
    (`shutil.rmtree`); a file/symlink with `unlink`.
    """
    if not dest.exists() and not dest.is_symlink():
        return Outcome.SKIPPED
    if dest.is_dir() and not dest.is_symlink():
        shutil.rmtree(dest)
    else:
        dest.unlink()
    return Outcome.REMOVED


def remove_file_if_owned(
    dest: Path, expected_content: str, *, dry_run: bool = False
) -> tuple[Outcome, str | None]:
    """Remove a standalone FILE only if its content is what Sertor deposited (A-16 content-guard).

    Guards against deleting a file the user MODIFIED (or a pre-existing file at an owned path with
    different content): if `dest`'s current text differs from `expected_content` (line-ending
    insensitive, matching the deposit path in `update_file_if_changed`), the file is PRESERVED and
    the outcome is `SKIPPED` with a reason — never a blind deletion (FR-013 spirit). Absent →
    `SKIPPED`. A content match → `REMOVED`. `dry_run` projects the same verdict without mutating.

    Only for regular files (FILE artifacts): a matching symlink is unlinked; owned DIRECTORIES
    removed in block keep using `remove_path` (a dir has no single "deposited content" to compare).
    """
    if not dest.exists() and not dest.is_symlink():
        return Outcome.SKIPPED, "absent"
    if dest.is_file() and not dest.is_symlink():
        current = dest.read_text(encoding="utf-8").replace("\r\n", "\n")
        if current != expected_content.replace("\r\n", "\n"):
            return Outcome.SKIPPED, "preserved: modified since install"
    if dry_run:
        return Outcome.REMOVED, None
    dest.unlink()
    return Outcome.REMOVED, None


def prune_empty_dirs(dest: Path) -> Outcome:
    """Remove `dest` and its empty subdirectories, bottom-up — post-uninstall orphan cleanup (A-17).

    Only EMPTY directories are removed (an empty dir has nothing to lose); any directory still
    holding a file — the user's content, or a Sertor asset preserved by the content-guard — is kept,
    and so is its parent chain. Absent / not-a-dir → `SKIPPED`. Never touches files. Fixes the
    `.claude/` orphan shell (empty `hooks/` + `.claude/` left after the Sertor hook files were
    removed). Returns `REMOVED` if any directory was removed, else `SKIPPED`.
    """
    if not dest.is_dir() or dest.is_symlink():
        return Outcome.SKIPPED
    removed_any = False
    # Deepest-first: a child directory empties before its parent is examined.
    for sub in sorted(dest.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if sub.is_dir() and not sub.is_symlink() and not any(sub.iterdir()):
            sub.rmdir()
            removed_any = True
    if not any(dest.iterdir()):
        dest.rmdir()
        return Outcome.REMOVED
    return Outcome.REMOVED if removed_any else Outcome.SKIPPED


def project_removal(dest: Path) -> Outcome:
    """Read-only projection of `remove_path` (for `--dry-run`): exists → `REMOVED`; else `SKIPPED`.

    Touches nothing on disk. Mirrors `remove_path`'s outcome so a dry-run report matches the real
    run's removals.
    """
    if dest.exists() or dest.is_symlink():
        return Outcome.REMOVED
    return Outcome.SKIPPED


def project_update(dest: Path, content: bytes | str) -> Outcome:
    """Read-only projection of `update_file_if_changed` (for `--dry-run`). No write.

    `CREATED` if absent, `SKIPPED` if equal, `UPDATED` if it would change. Mirrors the (line-ending
    insensitive for `str`) comparison of `update_file_if_changed`.
    """
    if not dest.exists():
        return Outcome.CREATED
    if isinstance(content, str):
        current = dest.read_text(encoding="utf-8").replace("\r\n", "\n")
        return Outcome.SKIPPED if current == content.replace("\r\n", "\n") else Outcome.UPDATED
    return Outcome.SKIPPED if dest.read_bytes() == content else Outcome.UPDATED


def deregister_mcp_client(
    runner: CommandRunner, server_name: str = _SERVER_NAME
) -> Outcome:
    """De-registers the MCP server from the client — inverse of `_apply_mcp_register` (local scope).

    Runs `claude mcp remove <server_name>` via the injectable `runner`. If `claude` is not on the
    PATH, raises `McpRegistrationError` with the manual fallback command (FR-024, US3 sc.2;
    fail-fast). If the command fails because the server is not registered, it is treated as already
    removed (`SKIPPED`) — idempotency; any other failure raises with the manual command.
    """
    manual = f"{_CLAUDE} mcp remove {server_name}"
    if not runner.is_available(_CLAUDE):
        raise McpRegistrationError(
            f"`{_CLAUDE}` is not available on the PATH: cannot de-register the MCP server in "
            f"local scope. Remove it manually: {manual}"
        )
    res = runner.run([_CLAUDE, "mcp", "remove", server_name], cwd=Path.cwd())
    if res.ok:
        return Outcome.REMOVED
    # `claude mcp remove` fails when the server is not registered → idempotent no-op.
    combined = f"{res.stdout}\n{res.stderr}".lower()
    if "not found" in combined or "no such" in combined or "not registered" in combined:
        return Outcome.SKIPPED
    raise McpRegistrationError(
        f"`{_CLAUDE} mcp remove` failed: {res.stderr.strip() or res.returncode}. "
        f"Remove it manually: {manual}"
    )


# --- verb-aware orchestrator --------------------------------------------------------------------


ApplyFn = Callable[[Artifact, LifecycleOp], ArtifactOutcome]


def _iter_owned_disk_paths(target_root: Path, owned: SertorOwnedPaths) -> set[str]:
    """Sertor-owned paths (dirs + files) that currently EXIST on disk under `target_root`."""
    present: set[str] = set()
    for rel in (*owned.owned_dirs, *owned.owned_files):
        if (target_root / rel).exists():
            present.add(rel.replace("\\", "/"))
    return present


def execute_lifecycle(
    plan: list[Artifact],
    owned: SertorOwnedPaths,
    apply_fn: ApplyFn,
    *,
    op: LifecycleOp,
    target: str,
    capability: str,
    assistant: str | None = None,
    dry_run: bool = False,
    obsolete_owned: SertorOwnedPaths | None = None,
    uninstall_dirs_in_block: tuple[str, ...] = (),
    uninstall_prune_empty: tuple[str, ...] = (),
) -> InstallReport:
    """Verb-aware orchestrator for `upgrade`/`uninstall` (data-model §6).

    1. Walks `plan` with `apply_fn(artifact, op)`, recording each outcome (fail-fast no-rollback,
       like `execute_plan`).
    2. On `UNINSTALL`, removes the `uninstall_dirs_in_block` owned trees in block (FR-030, e.g.
       `.sertor/`): a single `remove_path` per dir instead of per-sub-artifact. Then prunes the
       `uninstall_prune_empty` dirs bottom-up if they are left EMPTY (A-17 orphan cleanup, e.g. the
       `.claude/` shell after its hook files were removed) — a non-empty dir (user content) is kept.
    3. On `UPGRADE`, runs the **obsolete phase**: any path under `obsolete_owned` (or `owned` if not
       given) that exists on disk but is NOT produced by the current plan is removed via
       `remove_path` (decision D3). A disk path that is NOT Sertor-owned is never removed (FR-013) —
       only owned paths are candidates here.
    4. `dry_run=True`: nothing is written. The consumer's `apply_fn` projects (no mutation); the
       orchestrator itself performs no filesystem writes (it projects the obsolete/block removals).

    The orchestrator stays thin: the actual inverse/additive action per `kind` lives in `apply_fn`
    (the consumer dispatch), the inverse primitives live in the kit. `obsolete_owned` lets the CLI
    pass the union of OTHER assistants' owned paths for the cross-assistant case (FR-016).
    """
    report = InstallReport(
        target=target, capability=capability, assistant=assistant, op=op
    )
    plan_targets = {a.target_rel.replace("\\", "/") for a in plan}

    target_root = Path(target)

    for art in plan:
        try:
            outcome = apply_fn(art, op)
        except InstallerError as exc:
            report.add(ArtifactOutcome(art.target_rel, Outcome.ERROR, str(exc)))
            return report  # fail-fast no-rollback
        report.add(outcome)

    if op is LifecycleOp.UNINSTALL:
        for rel in uninstall_dirs_in_block:
            dest = target_root / rel
            if dry_run:
                report.add(ArtifactOutcome(rel, project_removal(dest), "runtime block"))
            else:
                report.add(ArtifactOutcome(rel, remove_path(dest), "runtime block"))
        # A-17 orphan cleanup: drop the Sertor-created dir shells (e.g. `.claude/hooks`, `.claude/`)
        # left empty after the file removals. dry-run cannot know post-removal emptiness (the files
        # were not removed) → reported as a no-op.
        for rel in uninstall_prune_empty:
            dest = target_root / rel
            if dry_run:
                report.add(ArtifactOutcome(rel, Outcome.SKIPPED, "prune empty (dry-run)"))
            else:
                report.add(ArtifactOutcome(rel, prune_empty_dirs(dest), "prune empty orphan dirs"))

    if op is LifecycleOp.UPGRADE:
        scope = obsolete_owned if obsolete_owned is not None else owned
        norm_plan = {t.rstrip("/") for t in plan_targets}
        for rel in sorted(_iter_owned_disk_paths(target_root, scope)):
            norm = rel.rstrip("/")
            # An owned path is obsolete only if it is NOT a plan target AND it does not CONTAIN a
            # plan target (a dir holding live artifacts, e.g. `.sertor/` with `.sertor/.env`).
            if norm in norm_plan:
                continue
            if any(t == norm or t.startswith(norm + "/") for t in norm_plan):
                continue
            dest = target_root / rel
            if dry_run:
                report.add(ArtifactOutcome(rel, Outcome.REMOVED, "obsolete (dry-run)"))
                continue
            outcome = remove_path(dest)
            report.add(ArtifactOutcome(rel, outcome, "obsolete"))

    return report
