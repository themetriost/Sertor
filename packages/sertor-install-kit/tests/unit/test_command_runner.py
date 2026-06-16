"""Tests for `SubprocessRunner` — focused on the `env` overlay (UTF-8 fix for spec-kit launch).

The overlay must ADD keys to the child environment without replacing the inherited one (the child
still needs PATH etc.). Uses the current interpreter to echo an env var, no external tool needed.
"""
from __future__ import annotations

import sys
from pathlib import Path

from sertor_install_kit.command_runner import SubprocessRunner


def _echo_env(var: str) -> list[str]:
    return [sys.executable, "-c", f"import os;print(os.environ.get('{var}',''))"]


def test_env_overlay_adds_keys(tmp_path: Path):
    res = SubprocessRunner().run(
        _echo_env("SERTOR_TEST_X"), tmp_path, env={"SERTOR_TEST_X": "hello"}
    )
    assert res.ok
    assert res.stdout.strip() == "hello"


def test_env_overlay_preserves_inherited(tmp_path: Path, monkeypatch):
    # A parent-env var must survive the overlay (overlay = merge with os.environ, not replace).
    monkeypatch.setenv("SERTOR_TEST_INHERITED", "keepme")
    res = SubprocessRunner().run(
        _echo_env("SERTOR_TEST_INHERITED"), tmp_path, env={"SERTOR_TEST_OTHER": "1"}
    )
    assert res.ok
    assert res.stdout.strip() == "keepme"


def test_no_env_runs_with_inherited_only(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SERTOR_TEST_Y", "inherited")
    res = SubprocessRunner().run(_echo_env("SERTOR_TEST_Y"), tmp_path)
    assert res.ok
    assert res.stdout.strip() == "inherited"
