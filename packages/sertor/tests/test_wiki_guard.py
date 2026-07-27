"""Tests for the `wiki-guard` hook (E10-FEAT-040): BLOCK stopping until the work is recorded.

Offline, host-agnostic, stdlib-only. The gate reuses `sertor-wiki-tools scan` (`wiki.scan/1`),
so the logic tests import the module and monkeypatch the `scan` subprocess + the event reader
(controlling `pending` deterministically). One real-subprocess smoke test proves exit 0 always.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import types
from pathlib import Path

import pytest

_HOOK = (Path(__file__).resolve().parents[1] / "src" / "sertor_installer" / "assets"
         / "claude" / "hooks" / "wiki-guard.py")

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


def _load_module():
    spec = importlib.util.spec_from_file_location("wiki_guard_hook", _HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _with_config(tmp_path: Path) -> Path:
    """A host root carrying `wiki/wiki.config.toml`."""
    (tmp_path / "wiki").mkdir(parents=True, exist_ok=True)
    (tmp_path / "wiki" / "wiki.config.toml").write_text(_CONFIG, encoding="utf-8")
    return tmp_path


def _fake_scan(pending: int, message: str = "", **extra):
    payload = {"schema": "wiki.scan/1", "pending": pending,
               "message": message or f"{pending} modified files not yet recorded"}
    payload.update(extra)

    def run(*_a, **_k):
        return types.SimpleNamespace(stdout=json.dumps(payload) + "\n")

    return run


def _drive(mod, monkeypatch, root: Path, *, event: dict, scan_run):
    """Run `main()` with the event reader and the scan subprocess stubbed."""
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    monkeypatch.setattr(mod._hooklib, "read_event", lambda: event)
    monkeypatch.setattr(mod.subprocess, "run", scan_run)
    mod.main()


# --- block path ----------------------------------------------------------------------------------

@pytest.mark.parametrize("assistant", ["claude", "copilot"])
def test_blocks_when_pending(tmp_path, monkeypatch, capsys, assistant):
    mod = _load_module()
    monkeypatch.setattr(sys, "argv", ["wiki-guard.py", "--mode", "Stop", "--assistant", assistant])
    _drive(mod, monkeypatch, _with_config(tmp_path), event={}, scan_run=_fake_scan(3))
    out = capsys.readouterr().out.strip()
    payload = json.loads(out.splitlines()[-1])
    assert payload["decision"] == "block"
    reason = payload["reason"].lower()
    assert "record" in reason and "distill" in reason and "lint" in reason


def test_reason_includes_scan_message(tmp_path, monkeypatch, capsys):
    mod = _load_module()
    _drive(mod, monkeypatch, _with_config(tmp_path), event={},
           scan_run=_fake_scan(2, message="2 files changed under src/ not recorded"))
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert "src/ not recorded" in payload["reason"]


# --- naming the files (E10-FEAT-045) --------------------------------------------------------------

def test_reason_names_the_pending_files(tmp_path, monkeypatch, capsys):
    """A block that says only HOW MANY forces the agent to reconstruct WHICH — the diagnosis gap
    a federation node had to close by hand before it could act."""
    mod = _load_module()
    _drive(mod, monkeypatch, _with_config(tmp_path), event={},
           scan_run=_fake_scan(2, pending_paths=["src/a.py", "specs/b.md"], pending_truncated=0))
    reason = json.loads(capsys.readouterr().out.strip().splitlines()[-1])["reason"]
    assert "src/a.py" in reason and "specs/b.md" in reason


def test_reason_declares_truncation_instead_of_hiding_it(tmp_path, monkeypatch, capsys):
    mod = _load_module()
    _drive(mod, monkeypatch, _with_config(tmp_path), event={},
           scan_run=_fake_scan(12, pending_paths=["src/a.py"], pending_truncated=11))
    reason = json.loads(capsys.readouterr().out.strip().splitlines()[-1])["reason"]
    assert "+11 more" in reason


def test_reason_names_a_stale_uncommitted_entry(tmp_path, monkeypatch, capsys):
    """Otherwise the journal looks already modified while the gate blocks anyway (FR-004a)."""
    mod = _load_module()
    _drive(mod, monkeypatch, _with_config(tmp_path), event={},
           scan_run=_fake_scan(1, pending_paths=["src/a.py"],
                               stale_recording="wiki/log/2026-07-24.md"))
    reason = json.loads(capsys.readouterr().out.strip().splitlines()[-1])["reason"]
    assert "wiki/log/2026-07-24.md" in reason and "not today" in reason.lower()


def test_reason_declares_when_the_anchor_is_only_an_estimate(tmp_path, monkeypatch, capsys):
    """Without version control the answer is a proxy, and it must say so (Principle XIV)."""
    mod = _load_module()
    _drive(mod, monkeypatch, _with_config(tmp_path), event={},
           scan_run=_fake_scan(1, anchor_kind="mtime",
                               anchor_fallback_reason="not_a_repository"))
    reason = json.loads(capsys.readouterr().out.strip().splitlines()[-1])["reason"]
    assert "estimate" in reason.lower() and "not_a_repository" in reason


def test_older_payload_without_the_new_fields_still_blocks(tmp_path, monkeypatch, capsys):
    """A host whose runtime is not upgraded yet must keep the previous behaviour, not an error."""
    mod = _load_module()
    _drive(mod, monkeypatch, _with_config(tmp_path), event={}, scan_run=_fake_scan(3))
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["decision"] == "block"


# --- no-block paths ------------------------------------------------------------------------------

def test_no_block_when_nothing_pending(tmp_path, monkeypatch, capsys):
    mod = _load_module()
    _drive(mod, monkeypatch, _with_config(tmp_path), event={}, scan_run=_fake_scan(0))
    assert capsys.readouterr().out.strip() == ""


def test_no_block_on_stop_hook_active(tmp_path, monkeypatch, capsys):
    """Anti-loop: an already-active Stop cycle never re-blocks (scan is never even consulted)."""
    mod = _load_module()

    def _boom(*_a, **_k):  # scan must NOT run
        raise AssertionError("scan should not be consulted when stop_hook_active")

    _drive(mod, monkeypatch, _with_config(tmp_path),
           event={"stop_hook_active": True}, scan_run=_boom)
    assert capsys.readouterr().out.strip() == ""


def test_no_block_without_wiki_config(tmp_path, monkeypatch, capsys):
    mod = _load_module()

    def _boom(*_a, **_k):  # scan must NOT run without a config
        raise AssertionError("scan should not run without a wiki config")

    _drive(mod, monkeypatch, tmp_path, event={}, scan_run=_boom)  # no wiki/wiki.config.toml
    assert capsys.readouterr().out.strip() == ""


def test_scan_failure_fails_open_with_breadcrumb(tmp_path, monkeypatch, capsys):
    mod = _load_module()

    def _raise(*_a, **_k):
        raise OSError("CLI unavailable")

    _drive(mod, monkeypatch, _with_config(tmp_path), event={}, scan_run=_raise)
    assert capsys.readouterr().out.strip() == ""  # fail open, no block
    assert (tmp_path / ".sertor" / ".last-hook-error").is_file()  # but the failure is visible (XII)


# --- fail-safe runner (real subprocess) ----------------------------------------------------------

def test_subprocess_exits_zero_and_silent_without_config(tmp_path):
    """The real hook, invoked as wired, never traps the turn (exit 0, no output)."""
    env = {"CLAUDE_PROJECT_DIR": str(tmp_path), "PATH": os.environ.get("PATH", "")}
    r = subprocess.run(
        [sys.executable, str(_HOOK), "--mode", "Stop", "--assistant", "claude"],
        input="{}", capture_output=True, text=True, env=env, timeout=30,
    )
    assert r.returncode == 0
    assert r.stdout.strip() == ""
