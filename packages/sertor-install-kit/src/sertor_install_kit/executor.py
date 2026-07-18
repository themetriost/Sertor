"""Generic plan executor (D5): `execute_plan(plan, apply) -> InstallReport`.

The loop is identical across wiki/rag/governance; only the per-`kind` dispatch differs. Instead of
duplicating the loop in every bundle, the kit exposes it once with an `apply` callback supplied by
the consumer (which closes over `target_root`/profile/runner and dispatches by `kind`).

**Fail-fast no-rollback** (D5, FR-019): the first `InstallerError` raised by `apply` is recorded as
an `ERROR` outcome, `failed_step` is set, and the loop stops; already-written artifacts remain (no
rollback). Only `InstallerError` is caught — programming bugs propagate. Consumers that bridge a
third party (e.g. `sertor-core`) MUST wrap its errors in `InstallerError` at the boundary (D3), so
this fail-fast still applies.

**Verb-aware (feature 048):** `execute_plan(..., op=LifecycleOp.INSTALL)` passes `op` to the
callback (`apply(artifact, op)`). The `op` defaults to `INSTALL`, so every existing call site keeps
working unchanged (NFR-3); the loop, fail-fast and report are identical across verbs — only the
per-`kind` inverse action chosen by `apply` differs. The verb is recorded on the report (title).
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from sertor_install_kit.artifacts import Artifact, ArtifactOutcome, LifecycleOp, Outcome
from sertor_install_kit.errors import InstallerError
from sertor_install_kit.observability import log_install_event
from sertor_install_kit.report import InstallReport

# Callback shape: the consumer dispatches by `(kind, op)` to the additive or inverse primitive.
ApplyFn = Callable[[Artifact, LifecycleOp], ArtifactOutcome]


def execute_plan(
    plan: list[Artifact],
    apply: ApplyFn,
    *,
    target: str,
    capability: str,
    assistant: str | None = None,
    op: LifecycleOp = LifecycleOp.INSTALL,
    runtime_dir: Path | None = None,
    rev: str | None = None,
    dry_run: bool = False,
) -> InstallReport:
    """Executes `plan` in order via `apply`, with fail-fast no-rollback.

    `apply(artifact, op)` deposits/updates/removes the artifact and returns its `ArtifactOutcome`,
    raising `InstallerError` on a domain error. `target`/`capability`/`assistant`/`op` populate the
    report (`assistant` is optional/informative, Principio IX; `op` defaults to `INSTALL` so every
    existing call site is unchanged — feature 048).

    E2-FEAT-018: when `runtime_dir` is given, each outcome is also appended to the inspectable
    install log (`install.event/1`); `rev` stamps the resolved revision; `dry_run` writes nothing.
    All three default off, so existing call sites are unchanged.
    """
    report = InstallReport(
        target=target, capability=capability, assistant=assistant, op=op
    )
    for art in plan:
        try:
            outcome = apply(art, op)
        except InstallerError as exc:
            outcome = ArtifactOutcome(art.target_rel, Outcome.ERROR, str(exc))
            report.add(outcome)
            _record_event(runtime_dir, op, capability, outcome, rev, dry_run)
            break  # fail-fast: stop on the first domain error (no rollback)
        report.add(outcome)
        _record_event(runtime_dir, op, capability, outcome, rev, dry_run)
    return report


def _record_event(
    runtime_dir: Path | None,
    op: LifecycleOp,
    capability: str,
    outcome: ArtifactOutcome,
    rev: str | None,
    dry_run: bool,
) -> None:
    """Append one artifact outcome to the inspectable install log, if `runtime_dir` is given."""
    if runtime_dir is None:
        return
    log_install_event(
        runtime_dir, op=op.value, capability=capability, target=outcome.target_rel,
        outcome=outcome.outcome.value, reason=outcome.detail, rev=rev, dry_run=dry_run,
    )
