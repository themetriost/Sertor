"""Tests for the `distill-floor` hook (E10-FEAT-039): BLOCK the merge until the day has a distill.

Offline, host-agnostic, stdlib-only. Subprocess style (parity suite): per-assistant output +
fail-safe (exit 0 always). Plus direct unit tests of the pure merge-matcher. The gate is
deterministic: a `distill` entry in today's dated log partition, read from `wiki.config.toml`.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

_HOOK = (Path(__file__).resolve().parents[1] / "src" / "sertor_installer" / "assets"
         / "claude" / "hooks" / "distill-floor.py")

_CONFIG = """\
profile = "code+doc"
language = "en"
root = "wiki"
log_dir = "log"

[[taxonomy]]
name = "concepts"
dir = "concepts"
type = "concept"
"""

_CONFIG_NO_ROTATION = """\
profile = "code+doc"
language = "en"
root = "wiki"

[[taxonomy]]
name = "concepts"
dir = "concepts"
type = "concept"
"""


def _load_module():
    spec = importlib.util.spec_from_file_location("distill_floor_hook", _HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _host(tmp_path: Path, config: str = _CONFIG, *, distill_today: bool = False,
          activity_today: bool = False) -> Path:
    """A host root with `wiki/wiki.config.toml` and (optionally) today's log partition."""
    wiki = tmp_path / "wiki"
    (wiki / "log").mkdir(parents=True)
    (wiki / "wiki.config.toml").write_text(config, encoding="utf-8")
    lines = ["# partition\n"]
    if activity_today:
        lines.append(f"## [{date.today().isoformat()}] record | did work\nbody\n")
    if distill_today:
        lines.append(f"## [{date.today().isoformat()}] distill | an entity\nbody\n")
    if activity_today or distill_today:
        part = wiki / "log" / f"{date.today().isoformat()}.md"
        part.write_text("".join(lines), encoding="utf-8")
    return tmp_path


def _run(root: Path, *, mode: str, event: dict, assistant: str = "claude"):
    env = {"CLAUDE_PROJECT_DIR": str(root)}
    import os
    env["PATH"] = os.environ.get("PATH", "")
    return subprocess.run(
        [sys.executable, str(_HOOK), "--mode", mode, "--assistant", assistant],
        input=json.dumps(event), capture_output=True, text=True, env=env, timeout=30,
    )


_MERGE_EVENT = {"tool_input": {"command": "gh pr merge 5 --squash"}}


# --- pure merge matcher --------------------------------------------------------------------------

def test_is_delivery_merge():
    m = _load_module()
    assert m._is_delivery_merge("gh pr merge 5 --squash")
    assert m._is_delivery_merge("git merge 116-daily-distill-floor")
    assert m._is_delivery_merge("git checkout master && git merge feature-x")
    assert not m._is_delivery_merge("git merge master")           # updating a feature branch
    assert not m._is_delivery_merge("git merge origin/main")      # updating
    assert not m._is_delivery_merge("git merge --abort")          # no ref
    assert not m._is_delivery_merge("git status")
    assert not m._is_delivery_merge("git commit -m 'x'")


# --- PreToolUse gate -----------------------------------------------------------------------------

@pytest.mark.parametrize("assistant", ["claude", "copilot"])
def test_merge_blocked_when_no_distill_today(tmp_path, assistant):
    root = _host(tmp_path, activity_today=True)  # worked today, no distill
    r = _run(root, mode="PreToolUse", event=_MERGE_EVENT, assistant=assistant)
    assert r.returncode == 0
    assert r.stdout.strip()  # a deny payload is emitted
    if assistant == "claude":
        payload = json.loads(r.stdout.splitlines()[-1])
        assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "distill" in payload["hookSpecificOutput"]["permissionDecisionReason"].lower()


def test_merge_blocked_even_with_no_partition_today(tmp_path):
    root = _host(tmp_path)  # rotation on, no partition today at all
    r = _run(root, mode="PreToolUse", event=_MERGE_EVENT)
    assert r.returncode == 0
    payload = json.loads(r.stdout.splitlines()[-1])
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_merge_allowed_when_distill_present_today(tmp_path):
    root = _host(tmp_path, distill_today=True, activity_today=True)
    r = _run(root, mode="PreToolUse", event=_MERGE_EVENT)
    assert r.returncode == 0
    assert r.stdout.strip() == ""  # allowed: no deny payload


def test_non_merge_command_is_ignored(tmp_path):
    root = _host(tmp_path, activity_today=True)
    r = _run(root, mode="PreToolUse", event={"tool_input": {"command": "git status"}})
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_mainline_update_merge_is_allowed(tmp_path):
    root = _host(tmp_path, activity_today=True)
    r = _run(root, mode="PreToolUse", event={"tool_input": {"command": "git merge origin/master"}})
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_single_file_log_fails_open(tmp_path):
    # rotation off → cannot date-scope "today" → never trap a merge.
    root = _host(tmp_path, _CONFIG_NO_ROTATION)
    (root / "wiki" / "wiki.config.toml").write_text(_CONFIG_NO_ROTATION, encoding="utf-8")
    r = _run(root, mode="PreToolUse", event=_MERGE_EVENT)
    assert r.returncode == 0
    assert r.stdout.strip() == ""  # fail open


def test_no_wiki_config_fails_open(tmp_path):
    r = _run(tmp_path, mode="PreToolUse", event=_MERGE_EVENT)
    assert r.returncode == 0
    assert r.stdout.strip() == ""


# --- SessionStart heads-up -----------------------------------------------------------------------

def test_sessionstart_headsup_when_no_distill(tmp_path):
    root = _host(tmp_path, activity_today=True)
    r = _run(root, mode="SessionStart", event={})
    assert r.returncode == 0
    assert "distill floor" in r.stdout.lower()


def test_sessionstart_copilot_additional_context(tmp_path):
    root = _host(tmp_path, activity_today=True)
    r = _run(root, mode="SessionStart", event={}, assistant="copilot")
    assert r.returncode == 0
    payload = json.loads(r.stdout.splitlines()[-1])
    assert "distill" in payload["additionalContext"].lower()


def test_sessionstart_silent_when_distill_present(tmp_path):
    root = _host(tmp_path, distill_today=True, activity_today=True)
    r = _run(root, mode="SessionStart", event={})
    assert r.returncode == 0
    assert r.stdout.strip() == ""
