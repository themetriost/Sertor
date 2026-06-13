"""Tests for `settings_merge` (T024, US2): dedup by command, malformed → fail-fast (D5)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sertor_core.domain.errors import ConfigError
from sertor_installer.artifacts import Outcome
from sertor_installer.resources import read_asset_text
from sertor_installer.settings_merge import merge_settings

_FRAGMENT = json.loads(read_asset_text("settings.hooks.json"))


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

    outcome, detail = merge_settings(p, _FRAGMENT)
    assert outcome is Outcome.MERGED
    data = json.loads(p.read_text(encoding="utf-8"))
    cmds = [h["command"] for e in data["hooks"]["SessionStart"] for h in e["hooks"]]
    assert "echo mine" in cmds  # user entry preserved
    assert data["$schema"] == "x"  # existing keys preserved
    assert len(data["hooks"]["SessionStart"]) == 2  # utente + nostra


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


def test_present_without_hooks_section_creates_it(tmp_path: Path):
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"$schema": "x"}), encoding="utf-8")
    outcome, detail = merge_settings(p, _FRAGMENT)
    assert outcome is Outcome.MERGED
    data = json.loads(p.read_text(encoding="utf-8"))
    assert "hooks" in data
    assert set(data["hooks"].keys()) == {"SessionStart", "Stop", "SessionEnd"}
