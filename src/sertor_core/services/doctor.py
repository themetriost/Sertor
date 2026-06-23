"""Deterministic health diagnosis for `sertor-rag doctor` (074, E12-FEAT-001).

Pure decision layer (Principio I/V): from the already-collected signals (missing env keys, manifest
state + current file mtimes, MCP registration, optional provider probe) → per-area verdicts, rollup
and exit-code gate. NO I/O here — reading `.mcp.json`, `os.stat`, building the embedder live in thin
helpers of the composition root / the handler, passed in as inputs. Entities are frozen dataclasses
(no SDK), separate from rendering (`cli/output.py::format_health_report`).

The JSON schema `doctor.report/1` (data-model.md) is the stable contract for skills/CI (SC-003).

DA-D4 (criteria, deterministic): CRITICAL (exit ≠ 0) = a missing env key OR an absent/incompatible
index; WARN (exit 0) = stale index, MCP not registered, provider unreachable. MCP never has a
critical outcome.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class Severity(StrEnum):
    """Severity of a single diagnosed problem (the gate keys off ``CRITICAL``)."""

    CRITICAL = "critical"
    WARN = "warn"
    INFO = "info"


class AreaStatus(StrEnum):
    """Per-area rollup status (and the global ``overall``)."""

    pass_ = "pass"
    warn = "warn"
    fail = "fail"


class AreaName(StrEnum):
    """The four diagnosed areas (FR-001), in a deterministic report order."""

    config = "config"
    provider = "provider"
    index = "index"
    mcp = "mcp"


class ProbeStatus(StrEnum):
    """Outcome of the opt-in provider reachability probe (DA-D5a)."""

    reachable = "reachable"
    unreachable = "unreachable"
    skipped = "skipped"            # offline / no `--online` flag
    not_applicable = "not_applicable"  # local provider, already covered statically


@dataclass(frozen=True)
class Problem:
    """An anomaly found in an area: cause + concrete remedy (FR-002).

    `code` is a stable, machine-readable identifier (schema `doctor.report/1`); `message` is the
    already-scrubbed cause (FR-013); `fields` carries the env KEY NAMES involved — never values.
    """

    severity: Severity
    code: str
    message: str
    remedy: str
    fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProviderProbe:
    """Outcome of the live provider probe (DA-D5a). `reason` is scrubbed; empty unless relevant."""

    status: ProbeStatus
    reason: str = ""


def _rollup(problems: tuple[Problem, ...]) -> AreaStatus:
    """Pure rollup of problems → area status: ≥1 CRITICAL → fail; ≥1 WARN/INFO → warn; else pass."""
    if any(p.severity is Severity.CRITICAL for p in problems):
        return AreaStatus.fail
    if problems:
        return AreaStatus.warn
    return AreaStatus.pass_


@dataclass(frozen=True)
class AreaReport:
    """Verdict for one area: rollup status + the problems + non-secret informational metadata."""

    name: AreaName
    status: AreaStatus
    problems: tuple[Problem, ...] = ()
    detail: dict[str, str | bool | None] = field(default_factory=dict)

    @staticmethod
    def of(
        name: AreaName,
        problems: tuple[Problem, ...] = (),
        detail: dict[str, str | bool | None] | None = None,
    ) -> AreaReport:
        """Build an `AreaReport` deriving `status` from `problems` (the only way to set it)."""
        return AreaReport(
            name=name,
            status=_rollup(problems),
            problems=problems,
            detail=detail or {},
        )


@dataclass(frozen=True)
class HealthReport:
    """Root of the health outcome: the four areas (fixed order) + the global rollup."""

    areas: tuple[AreaReport, ...]
    online: bool
    overall: AreaStatus

    def is_healthy(self) -> bool:
        """`True` ⇔ no area failed (gate: `False` ⇔ exit ≠ 0)."""
        return self.overall is not AreaStatus.fail

    def exit_code(self) -> int:
        """`1` if any `Problem` is `CRITICAL`, else `0` (FR-011/SC-004)."""
        for area in self.areas:
            if any(p.severity is Severity.CRITICAL for p in area.problems):
                return 1
        return 0


# --------------------------------------------------------------------------------------------------
# Pure diagnosis functions (signals → AreaReport). Testable with synthetic inputs, no FS/network.
# --------------------------------------------------------------------------------------------------


def check_config(missing: list[str]) -> AreaReport:
    """Diagnose the config/env area from `validate_backend()` output (FR-003/004, A-001).

    `missing` is the SINGLE source of «which keys the selected provider/store need» — this function
    accepts any list, it does NOT keep its own key catalogue (no duplicated truth). No missing key →
    `pass`; ≥1 → `fail` with one `CRITICAL` `Problem` per key (`code="env_missing_key"`).
    """
    problems = tuple(
        Problem(
            severity=Severity.CRITICAL,
            code="env_missing_key",
            message=f"missing {key}",
            remedy=f"set {key} in .sertor/.env (or run `sertor configure`)",
            fields=(key,),
        )
        for key in missing
    )
    return AreaReport.of(AreaName.config, problems)


def check_provider(
    missing_provider: list[str], probe: ProviderProbe | None
) -> AreaReport:
    """Diagnose the provider area: static config (+ optional reachability probe) (DA-D4/FR-007/008).

    Provider config incomplete (the provider keys missing from `validate_backend()`) → CRITICAL
    fail; config complete + probe `unreachable` → WARN; probe `skipped`/`None` → pass (offline-safe,
    only static checked); probe `reachable` → pass.
    """
    if missing_provider:
        problems = (
            Problem(
                severity=Severity.CRITICAL,
                code="provider_config_incomplete",
                message=f"provider config incomplete ({', '.join(missing_provider)})",
                remedy=(
                    f"set {', '.join(missing_provider)} in .sertor/.env "
                    "(or run `sertor configure`)"
                ),
                fields=tuple(missing_provider),
            ),
        )
        return AreaReport.of(
            AreaName.provider, problems, {"probe": probe.status.value if probe else "skipped"}
        )

    probe_status = probe.status.value if probe is not None else "skipped"
    detail: dict[str, str | bool | None] = {"probe": probe_status}
    if probe is not None and probe.status is ProbeStatus.unreachable:
        problems = (
            Problem(
                severity=Severity.WARN,
                code="provider_unreachable",
                message=f"provider unreachable: {probe.reason}",
                remedy="check the provider endpoint/credentials and network connectivity",
            ),
        )
        return AreaReport.of(AreaName.provider, problems, detail)
    return AreaReport.of(AreaName.provider, (), detail)


def freshness_from_manifest(
    state, current_stats: list[tuple[Path, float]]
) -> AreaReport:
    """Diagnose the index area: presence + freshness from the manifest, no re-scan (FR-005/006).

    `state is None` (manifest absent/incompatible) → CRITICAL fail `index_absent`, remedy
    `sertor-rag index .` (FR-005). With a state: compare the current file mtimes (`current_stats`)
    against the mtimes recorded in the manifest; any file modified (mtime greater) or deleted
    (mtime `0.0`) → WARN `index_stale`; otherwise `pass` with `detail["last_index"]` (the most
    recent recorded mtime, ISO-8601). No heuristic, no repo re-scan (SC-007).
    """
    if state is None:
        problem = Problem(
            severity=Severity.CRITICAL,
            code="index_absent",
            message="no index found (or the manifest is incompatible)",
            remedy="build the index with `sertor-rag index .`",
        )
        return AreaReport.of(AreaName.index, (problem,))

    recorded: dict[str, float] = {p: m for p, (m, _h, _lv) in state.files.items()}
    last_index = max(recorded.values()) if recorded else None
    detail: dict[str, str | bool | None] = {"last_index": _iso(last_index)}

    stale = False
    for path, mtime in current_stats:
        key = path.as_posix() if isinstance(path, Path) else str(path)
        prev = recorded.get(key)
        if prev is None:
            continue  # a path not in the manifest does not make the index stale (additive only)
        if mtime == 0.0 or mtime > prev:
            stale = True
            break

    if stale:
        problem = Problem(
            severity=Severity.WARN,
            code="index_stale",
            message="sources changed since the last index",
            remedy="refresh the index with `sertor-rag index .`",
        )
        return AreaReport.of(AreaName.index, (problem,), detail)
    return AreaReport.of(AreaName.index, (), detail)


def check_mcp(registered: bool, index_stale: bool) -> AreaReport:
    """Diagnose the MCP area: registration in `.mcp.json` (FR-009, DA-D4/DA-D5).

    Not registered → WARN `mcp_not_registered`, remedy `sertor install rag`; registered + index
    stale → WARN best-effort `mcp_stale_after_reindex` (restart the server); registered + fresh →
    pass. MCP NEVER has a critical outcome (DA-D4): the exit code is never driven by MCP.
    """
    if not registered:
        problem = Problem(
            severity=Severity.WARN,
            code="mcp_not_registered",
            message="the MCP server `sertor-rag` is not registered in .mcp.json",
            remedy="register it with `sertor install rag` (or edit .mcp.json)",
        )
        return AreaReport.of(AreaName.mcp, (problem,), {"registered": False})

    if index_stale:
        problem = Problem(
            severity=Severity.WARN,
            code="mcp_stale_after_reindex",
            message="the index changed; the running MCP server may serve stale content",
            remedy="restart the MCP server so it reloads the refreshed index",
        )
        return AreaReport.of(AreaName.mcp, (problem,), {"registered": True})

    return AreaReport.of(AreaName.mcp, (), {"registered": True})


_AREA_ORDER = (AreaName.config, AreaName.provider, AreaName.index, AreaName.mcp)


def assemble(areas: tuple[AreaReport, ...], online: bool) -> HealthReport:
    """Compose the four area reports into a `HealthReport` (fixed order, computed `overall`).

    `areas` is reordered to the canonical `(config, provider, index, mcp)` (schema stability,
    SC-003): the caller may pass a subset (with `--area`), missing areas keep their position by
    skipping. `overall` = `fail` if ≥1 area `fail`; `warn` if ≥1 `warn`; else `pass`.
    """
    by_name = {a.name: a for a in areas}
    ordered = tuple(by_name[n] for n in _AREA_ORDER if n in by_name)
    if any(a.status is AreaStatus.fail for a in ordered):
        overall = AreaStatus.fail
    elif any(a.status is AreaStatus.warn for a in ordered):
        overall = AreaStatus.warn
    else:
        overall = AreaStatus.pass_
    return HealthReport(areas=ordered, online=online, overall=overall)


def _iso(mtime: float | None) -> str | None:
    """Render an epoch mtime as a UTC ISO-8601 timestamp, or `None` (pure, no external dep)."""
    if mtime is None:
        return None
    import time

    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(mtime))
