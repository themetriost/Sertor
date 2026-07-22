"""Versioned result contracts for wiki operations (FR-011, research D4).

Each operation returns a pure, serialisable dataclass with a versioned `schema` field
(`<name>/<version>`). Contracts contain **metadata and references**, never the full page content.
Consumers (hooks, skills, LLM half FEAT-003-N) verify `schema` and tolerate future additional
fields (forward-compatible).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field


def _to_json(payload: dict) -> str:
    """Serialises a contract to stable JSON (ordered keys, non-escaped UTF-8)."""
    return json.dumps(payload, ensure_ascii=False, sort_keys=False)


@dataclass(frozen=True)
class ScanResult:
    """`wiki.scan/1` — outcome of the pending-work scan (FR-005)."""

    pending: int
    anchor: str | None
    dirs_scanned: list[str]
    message: str
    schema: str = "wiki.scan/1"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return _to_json(self.to_dict())


@dataclass(frozen=True)
class StructureResult:
    """`wiki.structure/1` — outcome of structure initialisation (FR-003, SC-006)."""

    created: list[str]
    skipped_existing: list[str]
    schema: str = "wiki.structure/1"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return _to_json(self.to_dict())


@dataclass(frozen=True)
class LintResult:
    """`wiki.lint/1` — structural defects (FR-006); also used by `validate`.

    `stubs` lists placeholder pages (frontmatter `status: stub`) to be filled in: they are NOT
    defects (a forward-link resolved to a stub is intentional, not `broken`), but a worklist of
    intentional nodes.
    Additive field, forward-compatible (older consumers ignore it).
    """

    broken_links: list[dict] = field(default_factory=list)
    orphans: list[str] = field(default_factory=list)
    missing_frontmatter: list[dict] = field(default_factory=list)
    naming_violations: list[dict] = field(default_factory=list)
    stubs: list[str] = field(default_factory=list)
    schema: str = "wiki.lint/1"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return _to_json(self.to_dict())


@dataclass(frozen=True)
class CollectResult:
    """`wiki.collect/1` — page map + metadata, without body content (FR-007)."""

    root: str
    index: str
    log: str
    pages: list[dict] = field(default_factory=list)
    schema: str = "wiki.collect/1"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return _to_json(self.to_dict())


@dataclass(frozen=True)
class IndexResult:
    """`wiki.index/1` — indexing orchestration outcome (FR-010, US5)."""

    collection: str | None
    documents: int
    regenerated: bool
    schema: str = "wiki.index/1"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return _to_json(self.to_dict())


@dataclass(frozen=True)
class AppendLogResult:
    """`wiki.append_log/1` — outcome of a log entry write-back (FR-005/007)."""

    written: bool
    partition: str | None
    created: bool
    schema: str = "wiki.append_log/1"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return _to_json(self.to_dict())


@dataclass(frozen=True)
class UpsertIndexResult:
    """`wiki.upsert_index/1` — outcome of an idempotent index row write (feature 010).

    `action`: `insert` (new row) | `update` (summary changed, row replaced in place) |
    `noop` (identical row already present, nothing written).
    """

    written: bool
    action: str
    page: str
    schema: str = "wiki.upsert_index/1"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return _to_json(self.to_dict())


@dataclass(frozen=True)
class MigrateResult:
    """`wiki.migrate/1` — outcome of the retroactive monolithic log split (FR-009)."""

    migrated_entries: int
    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    schema: str = "wiki.migrate/1"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return _to_json(self.to_dict())


@dataclass(frozen=True)
class MoveResult:
    """`wiki.move/1` — outcome of a page move with link rewriting (feature 017).

    `rewritten`: list of `{"page": rel_path, "occurrences": int}` for files where links were
    rewritten. `moved`: True if the file was moved (False in `--dry-run` or in recovery when
    the file was already at the destination).
    """

    source: str
    destination: str
    rewritten: list[dict] = field(default_factory=list)
    moved: bool = False
    dry_run: bool = False
    schema: str = "wiki.move/1"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return _to_json(self.to_dict())


@dataclass(frozen=True)
class ReconcileResult:
    """`wiki.reconcile/1` — candidates for obsolescence (read-only, feature 017).

    `candidates`: list of `{"path", "status", "updated", "superseded_by", "reason"}`. `clean`:
    True if there are no pages with `status: superseded`. The command never modifies any file.
    """

    candidates: list[dict] = field(default_factory=list)
    clean: bool = True
    schema: str = "wiki.reconcile/1"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return _to_json(self.to_dict())


@dataclass(frozen=True)
class RitualCheckResult:
    """`wiki.ritual_check/1` — deterministic ritual candidates (read-only, E10-FEAT-026).

    The tool FINDS (structural signals only), the agent JUDGES (D↔N). `distill_candidates`: list of
    `{"pages": [...], "shared_new_backlinks": int, "reason": str}` — groups of changed pages that
    likely surface a durable entity not yet distilled. `drift_candidates`: list of
    `{"page", "signal", "detail"}` — pages worth a semantic lint (`signal` ∈ `stale-updated` |
    `neighbor-of-change` | `capability-exec`). `declaration_scaffold`: the pre-populated
    `Rituale: record · distill · lint` line for the step closure. NEVER contains a semantic verdict.
    """

    scope: str
    pages_in_scope: list[str] = field(default_factory=list)
    distill_candidates: list[dict] = field(default_factory=list)
    drift_candidates: list[dict] = field(default_factory=list)
    declaration_scaffold: str = ""
    schema: str = "wiki.ritual_check/1"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return _to_json(self.to_dict())


@dataclass(frozen=True)
class DistillAuditResult:
    """`wiki.distill_audit/1` — cross-session distill debt (read-only, E10-FEAT-039).

    The tool FINDS (deterministic structural signals), the agent JUDGES durability (D↔N). Unlike
    `ritual_check` (git-diff of ONE step), this audits the WHOLE corpus so entities made durable BY
    ACCUMULATION surface regardless of when they were introduced. `candidates`: list of
    `{"name", "points", "signal", "sample_refs"}` — entities referenced from ≥`threshold` distinct
    points with no dedicated page (`signal` ∈ `wikilink` | `prose` | `both`). `debt`: the count N of
    such candidates (a lightweight, rising wiki-health metric). NEVER a durability verdict.
    """

    debt: int
    threshold: int
    corpus_files: int
    candidates: list[dict] = field(default_factory=list)
    schema: str = "wiki.distill_audit/1"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return _to_json(self.to_dict())


@dataclass(frozen=True)
class ErrorResult:
    """`wiki.error/1` — explicit error (Principio IV); no partial state."""

    error: str
    message: str
    schema: str = "wiki.error/1"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return _to_json(self.to_dict())
