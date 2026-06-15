"""Tests for `Artifact` validation: path-traversal guard raises the kit's `ConfigError`."""
from __future__ import annotations

import pytest

from sertor_install_kit.artifacts import Artifact, ArtifactKind, WriteStrategy
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
