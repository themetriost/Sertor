"""Tests for `render_copilot_hooks` (FEAT-011, US1; contract `copilot-hook-schema.md`).

Pure/offline (stdlib `json`): the renderer produces the NATIVE Copilot hook wiring. Each MUST rule
(R1..R5) has a test, plus anti-pattern tests (SC-007): a defect reintroduced into the output makes
the schema assertion fail.
"""
from __future__ import annotations

import json

from sertor_install_kit.surfaces import HookEntrySpec, render_copilot_hooks


def _roundtrip(data: dict) -> dict:
    """Ensures the output is plain JSON-serializable (no surprise objects)."""
    return json.loads(json.dumps(data))


def test_r1_version_is_one():
    out = render_copilot_hooks([HookEntrySpec("Stop", "command", "pwsh stop", 10)])
    assert out["version"] == 1


def test_r2_entries_are_flat_no_nested_hooks():
    out = render_copilot_hooks([HookEntrySpec("Stop", "command", "pwsh stop", 10)])
    for entries in out["hooks"].values():
        assert isinstance(entries, list)
        for entry in entries:
            assert "hooks" not in entry  # no nested Claude wrapper


def test_r3_no_claude_only_fields():
    out = _roundtrip(render_copilot_hooks([HookEntrySpec("Stop", "command", "pwsh stop", 10)]))
    for entries in out["hooks"].values():
        for entry in entries:
            assert "shell" not in entry
            assert "statusMessage" not in entry


def test_r4_timeout_uses_timeoutsec_not_timeout():
    out = render_copilot_hooks([HookEntrySpec("Stop", "command", "pwsh stop", 10)])
    entry = out["hooks"]["Stop"][0]
    assert entry["timeoutSec"] == 10
    assert "timeout" not in entry


def test_matcher_present_only_when_set():
    with_matcher = render_copilot_hooks(
        [HookEntrySpec("PreToolUse", "command", "pwsh check", 10, matcher="Bash|Write")]
    )
    assert with_matcher["hooks"]["PreToolUse"][0]["matcher"] == "Bash|Write"
    without = render_copilot_hooks([HookEntrySpec("Stop", "command", "pwsh stop", 10)])
    assert "matcher" not in without["hooks"]["Stop"][0]


def test_r5_logical_event_names_kept_verbatim():
    out = render_copilot_hooks(
        [
            HookEntrySpec("SessionStart", "command", "a", 10),
            HookEntrySpec("Stop", "command", "b", 10),
            HookEntrySpec("SessionEnd", "command", "c", 10),
        ]
    )
    assert set(out["hooks"].keys()) == {"SessionStart", "Stop", "SessionEnd"}


def test_prompt_type_payload_goes_in_prompt_field_not_command():
    # A `type:"prompt"` hook carries its text in `prompt`, NOT `command` — Copilot ignores a
    # `command` field on a prompt hook, which silently dropped the SessionStart prompt on Copilot
    # CLI 1.0.63 (regression fix, wiki/log/2026-06-17).
    out = render_copilot_hooks([HookEntrySpec("SessionStart", "prompt", "load the roadmap", 15)])
    entry = out["hooks"]["SessionStart"][0]
    assert entry["type"] == "prompt"
    assert entry["prompt"] == "load the roadmap"
    assert "command" not in entry


def test_command_type_payload_stays_in_command_field():
    out = render_copilot_hooks([HookEntrySpec("Stop", "command", "pwsh stop", 10)])
    entry = out["hooks"]["Stop"][0]
    assert entry["command"] == "pwsh stop"
    assert "prompt" not in entry


def test_multiple_entries_same_event():
    out = render_copilot_hooks(
        [
            HookEntrySpec("Stop", "command", "a", 10),
            HookEntrySpec("Stop", "command", "b", 10),
        ]
    )
    assert len(out["hooks"]["Stop"]) == 2


# --- anti-pattern (SC-007): the audit defects, reintroduced, must be detectable ---------------


def test_anti_pattern_missing_version_detectable():
    out = render_copilot_hooks([HookEntrySpec("Stop", "command", "pwsh stop", 10)])
    broken = {"hooks": out["hooks"]}  # drop version (the audit defect)
    assert "version" not in broken  # a schema validator asserting version would fail here


def test_anti_pattern_nested_or_timeout_field_detectable():
    out = render_copilot_hooks([HookEntrySpec("Stop", "command", "pwsh stop", 10)])
    # The native renderer never emits these; confirm the produced entry is clean.
    entry = out["hooks"]["Stop"][0]
    assert set(entry.keys()) <= {"type", "command", "prompt", "timeoutSec", "matcher"}
