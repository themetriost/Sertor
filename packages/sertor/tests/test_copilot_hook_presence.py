"""Shape-guard: the Copilot rag wiring contains every expected hook event (E10-FEAT-024, US1/US4).

The existing schema guard (`assert_valid_copilot_hook_file` in `test_schema_copilot_hooks.py`)
validates the *structure* of each entry but NOT the *presence* of each per-event group. The
historical FEAT-049 defect (a whole event silently missing from `sertor-hooks.json`) would slip
past a structure-only check. This file complements it (FR-004/CS-3): a removed fragment → a red,
event-naming assertion. Fully OFFLINE (no `uv`, no `pwsh`, no network): the rag plan is built and
executed on `tmp_path` with the `FakeCommandRunner` fixture.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sertor_install_kit.assistant import AssistantId
from sertor_installer.install_rag import build_rag_plan, execute_rag_plan
from sertor_installer.rag_profile import RagHostProfile, RagInstallOptions

# 6 hook fragments: PreToolUse×1 (usage-check), SessionEnd×3 (memory-capture,
# rag-freshness, version-check), SessionStart×2 (static prompts).
# Update this list if _rag_hook_fragment() in install_rag.py changes.
_EXPECTED_RAG_EVENTS = ("SessionEnd", "SessionStart", "PreToolUse")


def assert_events_present(data: dict, expected: tuple[str, ...]) -> None:
    """Assert that each expected event has >=1 entry in the Copilot hook wiring.

    Fails with a message naming the missing event (FR-002). PreToolUse additionally
    requires a non-empty 'matcher' field in at least one entry (FR-001/CS-1).
    """
    for event in expected:
        entries = data.get("hooks", {}).get(event, [])
        assert len(entries) >= 1, (
            f"hook event '{event}' is missing from sertor-hooks.json "
            f"(copilot-cli rag wiring); found events: {list(data.get('hooks', {}).keys())}"
        )
    pre_entries = data.get("hooks", {}).get("PreToolUse", [])
    assert any(e.get("matcher") for e in pre_entries), (
        "PreToolUse entries must have a non-empty 'matcher' field (FR-001)"
    )


def _rag_wiring(tmp_path: Path, make_runner, assistant: AssistantId) -> dict:
    """Build and execute the rag install plan for COPILOT_CLI; return the parsed hook JSON."""
    options = RagInstallOptions(target_root=tmp_path, backend="azure", with_deps=False)
    profile = RagHostProfile.from_options(options)
    plan = build_rag_plan(profile, with_deps=False, assistant=assistant)
    execute_rag_plan(plan, profile, make_runner(), assistant)
    return json.loads(
        (tmp_path / ".github/hooks/sertor-hooks.json").read_text(encoding="utf-8")
    )


def test_real_rag_wiring_has_all_events(tmp_path: Path, make_runner):
    """The rendered sertor-hooks.json for COPILOT_CLI contains all expected events."""
    data = _rag_wiring(tmp_path, make_runner, AssistantId.COPILOT_CLI)
    assert_events_present(data, _EXPECTED_RAG_EVENTS)


def test_missing_pretooluse_fails_naming_event(tmp_path: Path, make_runner):
    """Anti-pattern: removing PreToolUse from the rendered JSON makes the guard fail,
    and the failure message names the missing event.  This proves the guard is non-vacuous
    (the single PreToolUse fragment is the most fragile: removing it erases the event).
    """
    data = _rag_wiring(tmp_path, make_runner, AssistantId.COPILOT_CLI)
    del data["hooks"]["PreToolUse"]          # simulate removal of the sole fragment
    with pytest.raises(AssertionError, match="PreToolUse"):
        assert_events_present(data, _EXPECTED_RAG_EVENTS)


def test_missing_sessionend_fails_naming_event():
    """Meta-guard on a synthetic dict: missing SessionEnd → AssertionError naming it."""
    data = {"hooks": {"SessionStart": [{"type": "prompt", "prompt": "x"}]}}
    with pytest.raises(AssertionError, match="SessionEnd"):
        assert_events_present(data, _EXPECTED_RAG_EVENTS)
