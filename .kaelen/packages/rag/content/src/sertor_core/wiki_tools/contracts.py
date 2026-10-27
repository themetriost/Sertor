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


# The scan contract identifier. FROZEN — see `ScanResult` and `SCAN_SCHEMA` usage note below.
SCAN_SCHEMA = "wiki.scan/1"


@dataclass(frozen=True)
class ScanResult:
    """`wiki.scan/1` — outcome of the pending-work scan (FR-005).

    **The schema string is frozen (E10-FEAT-045).** The installed hook consumers compare it for
    EQUALITY and go *fail-open* when it does not match — so bumping it would not break the wiki
    gate, it would make it **disappear** on every host that updated the library but not the assets:
    no error, no breadcrumb, just sessions that always close. Absence looks like success, which is
    the worst failure shape there is. While such consumers exist this contract evolves **by addition
    only**: new fields, identifier untouched. Guarded by `test_scan_schema_frozen.py`.

    The fields below the original four are additive; a consumer that ignores them keeps working.
    `anchor` deliberately stays an ISO-8601 instant in BOTH modes (FR-013), so a reader parsing it
    as a date is unaffected — `anchor_kind` is what says whether it was derived or estimated.
    """

    pending: int
    anchor: str | None
    dirs_scanned: list[str]
    message: str
    # --- additive (E10-FEAT-045) ---
    anchor_kind: str | None = None            # "git" | "mtime" | None (no recording at all)
    anchor_ref: str | None = None             # non-null iff anchor_kind == "git" (citable)
    anchor_fallback_reason: str | None = None  # non-null iff kind == "mtime" (never a mute proxy)
    pending_paths: list[str] = field(default_factory=list)  # WHICH files, not just how many
    pending_truncated: int = 0                # how many are left out of the list
    stale_recording: str | None = None        # uncommitted log partition from another day, if any
    # --- additive (E10-FEAT-062) ---
    # `pending == 0` is a claim about the world ONLY when determination == "ok". With "failed" it
    # means "I could not look", which used to be indistinguishable from "there is nothing".
    determination: str = "ok"                 # "ok" | "failed"
    determination_reason: str | None = None   # non-null iff determination == "failed"
    # recordings honoured for compatibility — declared, not implied
    legacy_coverage: int = 0
    schema: str = SCAN_SCHEMA

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
    # --- additive (E10-FEAT-062) ---
    # How many work items the entry declared itself about. Makes the write observable: without it
    # the
    # only way to know what was recorded would be to re-read the file.
    covered: int = 0
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
    perimeter: dict = field(default_factory=dict)
    schema: str = "wiki.ritual_check/1"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return _to_json(self.to_dict())


def perimeter_of(kind: str, sources: list[tuple[str, str | None, int]]) -> dict:
    """Build the `perimeter` field: where the step's scope came from, and how much from each.

    `sources` is `(name, ref, paths)` in a stable order. The entity exists because its ABSENCE is
    what made E10-FEAT-060 invisible: the scope was computed but had no provenance, so nothing could
    reveal that two capabilities were measuring different realities.
    """
    return {
        "kind": kind,
        "sources": [{"name": n, "ref": r, "paths": p} for n, r, p in sources],
    }


def scope_of(perimeter: dict) -> str:
    """DERIVE the human `scope` string from `perimeter` — never maintain the two in parallel.

    Principle XIV applied to this feature's own remedy: keeping a summary string BESIDE the
    structure it summarises creates two descriptions of one fact, free to drift. That is the
    disease being cured here, and it would have been reintroduced by the cure.

    Back-compatible by construction: for a committed-only scope and for an explicit one the
    string is byte-identical to what this capability emitted before.
    """
    sources = perimeter.get("sources") or []
    if perimeter.get("kind") == "explicit":
        total = sum(s.get("paths", 0) for s in sources)
        return f"explicit:{total}"
    names = [s.get("name") for s in sources]
    ref = next((s.get("ref") for s in sources if s.get("name") == "committed"), None) or ""
    suffix = "+worktree" if "worktree" in names else ""
    return f"git:{ref}{suffix}"


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
