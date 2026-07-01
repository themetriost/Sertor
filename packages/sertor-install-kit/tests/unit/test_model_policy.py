"""Unit tests for the model-policy profile (E2-FEAT-015, contract C1).

Pure/offline: no I/O, no network. `resolve_model` is the single fail-loud accessor.
"""
from __future__ import annotations

import pytest

from sertor_install_kit.errors import ModelPolicyError
from sertor_install_kit.model_policy import IN_SCOPE_AGENTS, MODEL_POLICY_VERSION, resolve_model


def test_r1_all_five_in_scope_agents_resolve():
    for name in IN_SCOPE_AGENTS:
        assert resolve_model(name)  # non-empty


def test_r1_exactly_five_agents_in_scope():
    assert IN_SCOPE_AGENTS == frozenset({
        "concierge", "configuration-manager", "requirements-analyst",
        "requirements", "wiki-curator",
    })


def test_r2_deterministic():
    assert resolve_model("concierge") == resolve_model("concierge")


def test_r3_fail_loud_names_missing_agent():
    with pytest.raises(ModelPolicyError, match="unknown-agent"):
        resolve_model("unknown-agent")


def test_r3_anti_pattern_never_returns_none_or_empty():
    """Anti-pattern: an uncovered name never silently resolves to None/''."""
    try:
        value = resolve_model("nonexistent")
    except ModelPolicyError:
        pass
    else:
        pytest.fail(f"expected ModelPolicyError, got a silent value: {value!r}")


def test_r5_version_marker_is_a_non_empty_string():
    assert isinstance(MODEL_POLICY_VERSION, str) and MODEL_POLICY_VERSION


def test_pin_initial_reasoned_defaults():
    """Pin (regression on accidental edits): the initial reasoned policy values (spec table)."""
    assert resolve_model("concierge") == "claude-haiku-4.5"
    assert resolve_model("configuration-manager") == "claude-haiku-4.5"
    assert resolve_model("requirements-analyst") == "claude-sonnet-4.6"
    assert resolve_model("requirements") == "claude-sonnet-4.6"
    assert resolve_model("wiki-curator") == "claude-sonnet-4.6"
