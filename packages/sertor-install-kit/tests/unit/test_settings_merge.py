"""Tests for `settings_merge` (D5): dedup by command, malformed → fail-fast with kit ConfigError."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sertor_install_kit.artifacts import Outcome
from sertor_install_kit.errors import ConfigError
from sertor_install_kit.settings_merge import merge_settings, remove_settings_entries

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
