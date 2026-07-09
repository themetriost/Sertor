"""Tests for `settings_merge` (D5): dedup by command, malformed → fail-fast with kit ConfigError."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sertor_install_kit.artifacts import Outcome
from sertor_install_kit.errors import ConfigError
from sertor_install_kit.settings_merge import (
    merge_settings,
    remove_hook_entries_by_command_substring,
    remove_settings_entries,
)

_FRAGMENT = {
    "hooks": {
        "SessionStart": [{"hooks": [{"type": "command", "command": "echo start"}]}],
        "Stop": [{"hooks": [{"type": "command", "command": "echo stop"}]}],
        "SessionEnd": [{"hooks": [{"type": "command", "command": "echo end"}]}],
    }
}


def test_absent_creates_with_three_entries(tmp_path: Path):
    p = tmp_path / "settings.json"
    outcome, detail = merge_settings(p, _FRAGMENT)
    assert outcome is Outcome.CREATED
    assert detail == "+3 hook entries"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert set(data["hooks"].keys()) == {"SessionStart", "Stop", "SessionEnd"}


def test_present_with_user_hook_merges_additively(tmp_path: Path):
    p = tmp_path / "settings.json"
    user = {
        "$schema": "x",
        "hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "echo mine"}]}]},
    }
    p.write_text(json.dumps(user), encoding="utf-8")

    outcome, _ = merge_settings(p, _FRAGMENT)
    assert outcome is Outcome.MERGED
    data = json.loads(p.read_text(encoding="utf-8"))
    cmds = [h["command"] for e in data["hooks"]["SessionStart"] for h in e["hooks"]]
    assert "echo mine" in cmds  # user entry preserved
    assert data["$schema"] == "x"  # existing keys preserved
    assert len(data["hooks"]["SessionStart"]) == 2  # user + ours


def test_rerun_zero_new_entries(tmp_path: Path):
    p = tmp_path / "settings.json"
    merge_settings(p, _FRAGMENT)
    outcome, detail = merge_settings(p, _FRAGMENT)
    assert outcome is Outcome.MERGED
    assert detail == "no new entries"


def test_malformed_raises_configerror_file_untouched(tmp_path: Path):
    p = tmp_path / "settings.json"
    p.write_text('{"hooks": {oops', encoding="utf-8")
    before = p.read_bytes()
    with pytest.raises(ConfigError) as exc:
        merge_settings(p, _FRAGMENT)
    assert str(p) in str(exc.value)
    assert p.read_bytes() == before


# --- feature 048: remove_settings_entries (T014) ------------------------------------------------


def test_remove_settings_entries_removes_only_sertor(tmp_path: Path):
    p = tmp_path / "settings.json"
    user = {
        "$schema": "x",
        "hooks": {
            "SessionStart": [
                {"hooks": [{"type": "command", "command": "echo mine"}]},
                {"hooks": [{"type": "command", "command": "echo start"}]},  # Sertor
            ],
            "Stop": [{"hooks": [{"type": "command", "command": "echo stop"}]}],  # Sertor
        },
    }
    p.write_text(json.dumps(user), encoding="utf-8")

    outcome, detail = remove_settings_entries(p, _FRAGMENT)
    assert outcome is Outcome.REMOVED
    data = json.loads(p.read_text(encoding="utf-8"))
    cmds = [h["command"] for e in data["hooks"]["SessionStart"] for h in e["hooks"]]
    assert cmds == ["echo mine"]  # user entry kept, Sertor entry removed
    assert "Stop" not in data["hooks"]  # event emptied → pruned
    assert data["$schema"] == "x"  # non-hook keys preserved


def test_remove_settings_entries_no_sertor_skips(tmp_path: Path):
    p = tmp_path / "settings.json"
    user = {"hooks": {"SessionStart": [{"hooks": [{"command": "echo mine"}]}]}}
    p.write_text(json.dumps(user), encoding="utf-8")
    before = p.read_bytes()
    outcome, _ = remove_settings_entries(p, _FRAGMENT)
    assert outcome is Outcome.SKIPPED
    assert p.read_bytes() == before


def test_remove_settings_entries_idempotent(tmp_path: Path):
    p = tmp_path / "settings.json"
    merge_settings(p, _FRAGMENT)
    remove_settings_entries(p, _FRAGMENT)
    outcome, _ = remove_settings_entries(p, _FRAGMENT)
    assert outcome is Outcome.SKIPPED


def test_remove_settings_entries_missing_file_skips(tmp_path: Path):
    p = tmp_path / "settings.json"
    outcome, _ = remove_settings_entries(p, _FRAGMENT)
    assert outcome is Outcome.SKIPPED


# --- FEAT-011: schema-aware dedup (Copilot flat form + Claude nested form) ----------------------

# Copilot wiring: top-level `version` + FLAT entries (`entry["command"]`, no nested `hooks`).
_COPILOT_FRAGMENT = {
    "version": 1,
    "hooks": {
        "SessionStart": [{"type": "command", "command": "pwsh start", "timeoutSec": 15}],
        "Stop": [{"type": "command", "command": "pwsh stop", "timeoutSec": 10}],
    },
}


def test_copilot_flat_fragment_creates_and_keeps_version(tmp_path: Path):
    p = tmp_path / "sertor-hooks.json"
    outcome, detail = merge_settings(p, _COPILOT_FRAGMENT)
    assert outcome is Outcome.CREATED
    assert detail == "+2 hook entries"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["version"] == 1  # R1 schema requirement preserved
    cmds = [e["command"] for e in data["hooks"]["SessionStart"]]
    assert cmds == ["pwsh start"]


def test_copilot_flat_fragment_dedup_on_rerun(tmp_path: Path):
    p = tmp_path / "sertor-hooks.json"
    merge_settings(p, _COPILOT_FRAGMENT)
    outcome, detail = merge_settings(p, _COPILOT_FRAGMENT)
    assert outcome is Outcome.MERGED
    assert detail == "no new entries"  # flat command recognized → no duplication


def test_mixed_claude_nested_and_copilot_flat_in_same_file(tmp_path: Path):
    """A file holding BOTH shapes: dedup recognizes the command in either form (R-3)."""
    p = tmp_path / "settings.json"
    existing = {
        "version": 1,
        "hooks": {
            "Stop": [
                {"hooks": [{"type": "command", "command": "pwsh stop"}]},  # Claude nested
            ],
        },
    }
    p.write_text(json.dumps(existing), encoding="utf-8")
    # Fragment carries the SAME command in the flat Copilot form → must be deduped, not duplicated.
    outcome, detail = merge_settings(p, _COPILOT_FRAGMENT)
    assert outcome is Outcome.MERGED
    data = json.loads(p.read_text(encoding="utf-8"))
    assert len(data["hooks"]["Stop"]) == 1  # the flat "pwsh stop" was recognized as already present
    # the new SessionStart entry is added
    assert any(e.get("command") == "pwsh start" for e in data["hooks"]["SessionStart"])


def test_copilot_flat_remove_entries(tmp_path: Path):
    p = tmp_path / "sertor-hooks.json"
    merge_settings(p, _COPILOT_FRAGMENT)
    outcome, _ = remove_settings_entries(p, _COPILOT_FRAGMENT)  # default: keep the file
    assert outcome is Outcome.REMOVED
    data = json.loads(p.read_text(encoding="utf-8"))
    assert not data.get("hooks")  # all Sertor flat entries removed


def test_dedicated_file_deleted_when_empty(tmp_path: Path):
    """delete_if_empty=True: a Sertor-dedicated hooks file left with no hooks is DELETED, not left
    as a `{"version": 1}` shell (regression fix 2026-06-17)."""
    p = tmp_path / "sertor-hooks.json"
    merge_settings(p, _COPILOT_FRAGMENT)
    assert p.exists()
    outcome, detail = remove_settings_entries(p, _COPILOT_FRAGMENT, delete_if_empty=True)
    assert outcome is Outcome.REMOVED
    assert not p.exists()  # empty shell removed
    assert "removed" in detail.lower()


def test_shared_file_kept_when_empty(tmp_path: Path):
    """Default (delete_if_empty=False): a SHARED settings file is kept even if emptied — the user's
    file/structure must survive (e.g. Claude `.claude/settings.json`)."""
    p = tmp_path / "settings.json"
    merge_settings(p, _COPILOT_FRAGMENT)
    outcome, _ = remove_settings_entries(p, _COPILOT_FRAGMENT)
    assert outcome is Outcome.REMOVED
    assert p.exists()  # NOT deleted


def test_dedicated_file_with_leftover_user_hook_kept(tmp_path: Path):
    """delete_if_empty deletes ONLY when nothing remains: a non-Sertor hook keeps the file."""
    p = tmp_path / "sertor-hooks.json"
    user = {"version": 1, "hooks": {"Stop": [{"type": "command", "command": "echo mine"}]}}
    p.write_text(json.dumps(user), encoding="utf-8")
    merge_settings(p, _COPILOT_FRAGMENT)  # add Sertor entries alongside the user one
    outcome, _ = remove_settings_entries(p, _COPILOT_FRAGMENT, delete_if_empty=True)
    assert outcome is Outcome.REMOVED
    assert p.exists()  # the user's "echo mine" survives → file kept
    data = json.loads(p.read_text(encoding="utf-8"))
    assert any(e.get("command") == "echo mine" for e in data["hooks"]["Stop"])


# --- A-09: remove_hook_entries_by_command_substring (legacy `.ps1` migration) ------------------

# Old Claude wiring (nested, `"shell": "powershell"`) and old Copilot wiring (flat, `pwsh -File`).
_LEGACY_CLAUDE = {
    "hooks": {
        "SessionEnd": [{"hooks": [{"type": "command", "shell": "powershell", "command": (
            "$d = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { '.' }; "
            "& (Join-Path $d '.claude/hooks/rag-freshness.ps1')"
        )}]}],
    }
}
_PS1_BASENAMES = ("rag-freshness.ps1", "version-check.ps1", "memory-capture.ps1")


def test_removes_legacy_ps1_entry_by_substring(tmp_path: Path):
    p = tmp_path / "settings.json"
    p.write_text(json.dumps(_LEGACY_CLAUDE), encoding="utf-8")
    outcome, detail = remove_hook_entries_by_command_substring(p, _PS1_BASENAMES)
    assert outcome is Outcome.REMOVED and "1" in detail
    assert json.loads(p.read_text(encoding="utf-8")).get("hooks", {}) == {}


def test_preserves_new_py_and_user_entries(tmp_path: Path):
    """Only the legacy `.ps1` entry is stripped; the `.py` entry and a user hook survive."""
    p = tmp_path / "settings.json"
    py_cmd = "uv run --no-project python .claude/hooks/rag-freshness.py --assistant claude"
    p.write_text(json.dumps({"hooks": {"SessionEnd": [
        {"hooks": [{"type": "command", "shell": "powershell", "command":
                    "& (Join-Path $d '.claude/hooks/rag-freshness.ps1')"}]},
        {"hooks": [{"type": "command", "command": py_cmd}]},
        {"hooks": [{"type": "command", "command": "echo mine"}]},
    ]}}), encoding="utf-8")
    outcome, _ = remove_hook_entries_by_command_substring(p, _PS1_BASENAMES)
    assert outcome is Outcome.REMOVED
    cmds = [h["command"] for e in json.loads(p.read_text(encoding="utf-8"))["hooks"]["SessionEnd"]
            for h in e["hooks"]]
    assert any("rag-freshness.py" in c for c in cmds)   # portable entry kept
    assert "echo mine" in cmds                          # user entry kept
    assert not any(".ps1" in c for c in cmds)           # legacy entry gone


def test_copilot_flat_legacy_ps1_removed(tmp_path: Path):
    p = tmp_path / "sertor-hooks.json"
    old = "pwsh -File .github/hooks/rag-freshness.ps1"
    p.write_text(json.dumps({"version": 1, "hooks": {"SessionEnd": [
        {"type": "command", "command": old, "timeoutSec": 15},
    ]}}), encoding="utf-8")
    outcome, _ = remove_hook_entries_by_command_substring(
        p, _PS1_BASENAMES, delete_if_empty=True
    )
    assert outcome is Outcome.REMOVED
    assert not p.exists()  # dedicated file emptied → deleted


def test_no_legacy_entry_skips(tmp_path: Path):
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"hooks": {"SessionEnd": [
        {"hooks": [{"type": "command", "command":
                    "uv run --no-project python .claude/hooks/rag-freshness.py"}]},
    ]}}), encoding="utf-8")
    outcome, _ = remove_hook_entries_by_command_substring(p, _PS1_BASENAMES)
    assert outcome is Outcome.SKIPPED  # nothing legacy → idempotent no-op


def test_missing_file_skips(tmp_path: Path):
    outcome, _ = remove_hook_entries_by_command_substring(
        tmp_path / "nope.json", _PS1_BASENAMES
    )
    assert outcome is Outcome.SKIPPED
