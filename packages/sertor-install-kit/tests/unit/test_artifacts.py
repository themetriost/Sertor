"""Tests for `Artifact` validation + lifecycle taxonomy (feature 048: LifecycleOp, Outcome)."""
from __future__ import annotations

import pytest

from sertor_install_kit.artifacts import (
    Artifact,
    ArtifactKind,
    LifecycleOp,
    Outcome,
    WriteStrategy,
)
from sertor_install_kit.errors import ConfigError


def _make(target_rel: str) -> Artifact:
    return Artifact(
        kind=ArtifactKind.FILE,
        source="claude/x.md",
        target_rel=target_rel,
        strategy=WriteStrategy.CREATE_IF_ABSENT,
    )


def test_relative_target_ok():
    art = _make(".claude/skills/x.md")
    assert art.target_rel == ".claude/skills/x.md"


def test_absolute_target_rejected():
    with pytest.raises(ConfigError):
        _make("/etc/passwd")


def test_windows_drive_target_rejected():
    with pytest.raises(ConfigError):
        _make("C:/Windows/system32")


def test_parent_escape_rejected():
    with pytest.raises(ConfigError):
        _make("../outside.md")


# --- feature 048: lifecycle taxonomy ------------------------------------------------------------


def test_lifecycle_op_install_is_default_value():
    assert LifecycleOp.INSTALL.value == "install"
    assert str(LifecycleOp.UPGRADE.value) == "upgrade"
    assert LifecycleOp.UNINSTALL.value == "uninstall"
    # str-Enum: usable directly as a string verb
    assert LifecycleOp("upgrade") is LifecycleOp.UPGRADE


def test_outcome_new_members_exist_and_keep_existing_values():
    assert Outcome.UPDATED.value == "updated"
    assert Outcome.REMOVED.value == "removed"
    # the pre-existing members are untouched (retro-compat of the install report)
    assert Outcome.CREATED.value == "created"
    assert Outcome.SKIPPED.value == "skipped"
    assert Outcome.MERGED.value == "merged"
    assert Outcome.BLOCK.value == "block"
    assert Outcome.ERROR.value == "error"
