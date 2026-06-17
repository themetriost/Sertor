"""Unit tests for `GovernanceProfile` (T007, feature 045): default assistant, pinned
SpecKit version, validation of the assistant value."""
from __future__ import annotations

from pathlib import Path

import pytest

from sertor_flow.profile import (
    DEFAULT_ASSISTANT,
    SPECKIT_VERSION,
    GovernanceProfile,
    build_governance_profile,
)
from sertor_install_kit import ConfigError


def test_default_assistant_is_documented(tmp_path: Path):
    """The default assistant is `claude` (FR-002, aligned with FEAT-007)."""
    assert DEFAULT_ASSISTANT == "claude"
    profile = build_governance_profile(tmp_path)
    assert profile.assistant == "claude"


def test_speckit_version_is_pinned(tmp_path: Path):
    """The pinned SpecKit version is present on the profile (Principle VIII, config)."""
    assert SPECKIT_VERSION  # non-empty
    profile = build_governance_profile(tmp_path)
    assert profile.speckit_version == SPECKIT_VERSION


def test_copilot_cli_assistant_accepted(tmp_path: Path):
    """`copilot-cli` is a valid assistant (FEAT-012)."""
    profile = build_governance_profile(tmp_path, assistant="copilot-cli")
    assert profile.assistant == "copilot-cli"


def test_legacy_copilot_assistant_rejected(tmp_path: Path):
    """FEAT-012 (FR-001): the legacy VS Code value `copilot` is no longer accepted; the error
    names `copilot-cli`."""
    with pytest.raises(ConfigError) as exc:
        build_governance_profile(tmp_path, assistant="copilot")
    assert "copilot-cli" in str(exc.value)


def test_unknown_assistant_raises(tmp_path: Path):
    """An unknown assistant value raises an explicit `ConfigError` (Principle IV)."""
    with pytest.raises(ConfigError):
        build_governance_profile(tmp_path, assistant="codex")
    with pytest.raises(ConfigError):
        GovernanceProfile(target_root=tmp_path, assistant="bogus")
