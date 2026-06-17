"""Tests for `execute_plan` (T013/D5, T010/feature 048): callback, fail-fast, verb-aware."""
from __future__ import annotations

from sertor_install_kit.artifacts import (
    Artifact,
    ArtifactKind,
    ArtifactOutcome,
    LifecycleOp,
    Outcome,
    WriteStrategy,
)
from sertor_install_kit.errors import InstallerError
from sertor_install_kit.executor import execute_plan


def _art(target: str) -> Artifact:
    return Artifact(ArtifactKind.FILE, f"src/{target}", target, WriteStrategy.CREATE_IF_ABSENT)


def test_all_applied_in_order():
    plan = [_art("a"), _art("b"), _art("c")]
    seen: list[str] = []

    def apply(art: Artifact, op: LifecycleOp) -> ArtifactOutcome:
        seen.append(art.target_rel)
        return ArtifactOutcome(art.target_rel, Outcome.CREATED)

    report = execute_plan(plan, apply, target="/tmp/x", capability="governance")
    assert seen == ["a", "b", "c"]
    assert report.created == 3
    assert report.exit_code() == 0
    assert report.capability == "governance"
    assert report.target == "/tmp/x"
    assert report.op is LifecycleOp.INSTALL  # default verb (non-regression)


def test_fail_fast_stops_and_names_failed_step():
    plan = [_art("a"), _art("b"), _art("c")]
    seen: list[str] = []

    def apply(art: Artifact, op: LifecycleOp) -> ArtifactOutcome:
        seen.append(art.target_rel)
        if art.target_rel == "b":
            raise InstallerError("boom on b")
        return ArtifactOutcome(art.target_rel, Outcome.CREATED)

    report = execute_plan(plan, apply, target="/tmp/x", capability="governance")
    assert seen == ["a", "b"]  # stops at b, c never attempted (no rollback of a)
    assert report.created == 1
    assert report.errors == 1
    assert report.failed_step == "b"
    assert report.exit_code() == 1


def test_non_installer_error_propagates():
    plan = [_art("a")]

    def apply(art: Artifact, op: LifecycleOp) -> ArtifactOutcome:
        raise ValueError("programming bug, not a domain error")

    try:
        execute_plan(plan, apply, target="/tmp/x", capability="governance")
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("ValueError should propagate, not be caught as InstallerError")


# --- feature 048: verb-aware behaviour ----------------------------------------------------------


def test_install_op_is_default_and_passes_verb_to_callback():
    plan = [_art("a")]
    seen_ops: list[LifecycleOp] = []

    def apply(art: Artifact, op: LifecycleOp) -> ArtifactOutcome:
        seen_ops.append(op)
        return ArtifactOutcome(art.target_rel, Outcome.CREATED)

    execute_plan(plan, apply, target="/tmp/x", capability="rag")
    assert seen_ops == [LifecycleOp.INSTALL]


def test_uninstall_verb_counts_removed():
    plan = [_art("a"), _art("b")]

    def apply(art: Artifact, op: LifecycleOp) -> ArtifactOutcome:
        assert op is LifecycleOp.UNINSTALL
        return ArtifactOutcome(art.target_rel, Outcome.REMOVED)

    report = execute_plan(
        plan, apply, target="/tmp/x", capability="rag", op=LifecycleOp.UNINSTALL
    )
    assert report.removed == 2
    assert report.op is LifecycleOp.UNINSTALL
    assert report.exit_code() == 0


def test_upgrade_verb_counts_updated():
    plan = [_art("a")]

    def apply(art: Artifact, op: LifecycleOp) -> ArtifactOutcome:
        assert op is LifecycleOp.UPGRADE
        return ArtifactOutcome(art.target_rel, Outcome.UPDATED)

    report = execute_plan(
        plan, apply, target="/tmp/x", capability="rag", op=LifecycleOp.UPGRADE
    )
    assert report.updated == 1
    assert report.op is LifecycleOp.UPGRADE


def test_fail_fast_invariant_per_verb():
    plan = [_art("a"), _art("b")]

    def apply(art: Artifact, op: LifecycleOp) -> ArtifactOutcome:
        if art.target_rel == "a":
            raise InstallerError("boom")
        return ArtifactOutcome(art.target_rel, Outcome.REMOVED)  # pragma: no cover

    report = execute_plan(
        plan, apply, target="/tmp/x", capability="rag", op=LifecycleOp.UNINSTALL
    )
    assert report.errors == 1
    assert report.failed_step == "a"
    assert report.exit_code() == 1
