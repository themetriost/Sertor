"""Generic plan executor (D5): `execute_plan(plan, apply) -> InstallReport`.

The loop is identical across wiki/rag/governance; only the per-`kind` dispatch differs. Instead of
duplicating the loop in every bundle, the kit exposes it once with an `apply` callback supplied by
the consumer (which closes over `target_root`/profile/runner and dispatches by `kind`).

**Fail-fast no-rollback** (D5, FR-019): the first `InstallerError` raised by `apply` is recorded as
an `ERROR` outcome, `failed_step` is set, and the loop stops; already-written artifacts remain (no
rollback). Only `InstallerError` is caught — programming bugs propagate. Consumers that bridge a
third party (e.g. `sertor-core`) MUST wrap its errors in `InstallerError` at the boundary (D3), so
this fail-fast still applies.
"""
from __future__ import annotations

from collections.abc import Callable

from sertor_install_kit.artifacts import Artifact, ArtifactOutcome, Outcome
from sertor_install_kit.errors import InstallerError
from sertor_install_kit.report import InstallReport


def execute_plan(
    plan: list[Artifact],
    apply: Callable[[Artifact], ArtifactOutcome],
    *,
    target: str,
    capability: str,
    assistant: str | None = None,
) -> InstallReport:
    """Executes `plan` in order via `apply`, with fail-fast no-rollback.

    `apply(artifact)` deposits the artifact and returns its `ArtifactOutcome`, raising
    `InstallerError` on a domain error. `target`/`capability`/`assistant` populate the report
    (`assistant` is optional/informative, Principio IX, feature 044).
    """
    report = InstallReport(target=target, capability=capability, assistant=assistant)
    for art in plan:
        try:
            outcome = apply(art)
        except InstallerError as exc:
            report.add(ArtifactOutcome(art.target_rel, Outcome.ERROR, str(exc)))
            break  # fail-fast: stop on the first domain error (no rollback)
        report.add(outcome)
    return report
