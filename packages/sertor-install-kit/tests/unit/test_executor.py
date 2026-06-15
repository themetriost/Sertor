"""Tests for `execute_plan` (T013, D5): generic callback, fail-fast no-rollback."""
from __future__ import annotations

from sertor_install_kit.artifacts import (
    Artifact,
    ArtifactKind,
    ArtifactOutcome,
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

    def apply(art: Artifact) -> ArtifactOutcome:
        seen.append(art.target_rel)
        return ArtifactOutcome(art.target_rel, Outcome.CREATED)

    report = execute_plan(plan, apply, target="/tmp/x", capability="governance")
    assert seen == ["a", "b", "c"]
    assert report.created == 3
    assert report.exit_code() == 0
    assert report.capability == "governance"
    assert report.target == "/tmp/x"


def test_fail_fast_stops_and_names_failed_step():
    plan = [_art("a"), _art("b"), _art("c")]
    seen: list[str] = []

    def apply(art: Artifact) -> ArtifactOutcome:
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

    def apply(art: Artifact) -> ArtifactOutcome:
        raise ValueError("programming bug, not a domain error")

    try:
        execute_plan(plan, apply, target="/tmp/x", capability="governance")
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("ValueError should propagate, not be caught as InstallerError")
