"""Tests for the `--check` live probe of `sertor configure` (feature 051, T-700, US5 — Should).

The live probe is DEFERRED: `sertor-rag check` is not yet implemented in `sertor-core`. These
tests exercise the extension point with a `runner` MOCK only (zero network): the honest-degradation
branch, ok/fail branches. The two BLOCKED tasks (end-to-end with a real `sertor-rag check`) are not
implemented here — they wait for the core FEAT.
"""
from __future__ import annotations

from pathlib import Path

from sertor_install_kit.command_runner import CommandResult
from sertor_installer.configure import configure_rag


class _ProbeRunner:
    """Mock runner: simulates `sertor-rag check` outcomes without spawning a process."""

    def __init__(self, available: bool = True, returncode: int = 0, stderr: str = ""):
        self.available = available
        self.returncode = returncode
        self.stderr = stderr
        self.calls: list[list[str]] = []

    def is_available(self, tool: str) -> bool:
        return self.available

    def run(self, cmd: list[str], cwd: Path, env=None) -> CommandResult:
        self.calls.append(list(cmd))
        return CommandResult(self.returncode, "", self.stderr)


_LOCAL = dict(backend="local", store="local", explicit_values={}, overwrite=False,
              interactive=False)


def test_check_not_requested_no_network(tmp_path: Path):
    # T-700-NOCHECK: check=False → runner never called, live_check not requested.
    runner = _ProbeRunner()
    report = configure_rag(target_root=tmp_path, check=False, runner=runner, **_LOCAL)
    assert runner.calls == []
    assert report.live_check.requested is False
    assert report.live_check.ok is None


def test_check_degrades_when_sertor_rag_check_missing(tmp_path: Path):
    # T-700-UNAVAILABLE: exit 2 (unknown command) → ok=None, detail says "non disponibile".
    runner = _ProbeRunner(returncode=2, stderr="error: unknown command 'check'")
    report = configure_rag(target_root=tmp_path, check=True, runner=runner, **_LOCAL)
    assert report.live_check.requested is True
    assert report.live_check.ok is None
    assert "non disponibile" in report.live_check.detail


def test_check_degrades_when_vehicle_absent(tmp_path: Path):
    # Vehicle `sertor-rag` not on PATH → honest degradation, ok=None.
    runner = _ProbeRunner(available=False)
    report = configure_rag(target_root=tmp_path, check=True, runner=runner, **_LOCAL)
    assert report.live_check.ok is None
    assert "non disponibile" in report.live_check.detail
    assert runner.calls == []  # never tried to run an absent tool


def test_check_fails_env_intact(tmp_path: Path):
    # T-700-FAIL (mock): probe failed (exit 1, actionable) → ok=False, .env untouched.
    runner = _ProbeRunner(returncode=1, stderr="azure endpoint unreachable")
    report = configure_rag(target_root=tmp_path, check=True, runner=runner, **_LOCAL)
    assert report.live_check.ok is False
    assert "unreachable" in report.live_check.detail
    assert (tmp_path / ".sertor" / ".env").exists()  # env not removed/altered


def test_check_ok(tmp_path: Path):
    # T-700-OK (mock): probe exit 0 → ok=True.
    runner = _ProbeRunner(returncode=0)
    report = configure_rag(target_root=tmp_path, check=True, runner=runner, **_LOCAL)
    assert report.live_check.ok is True


def test_check_fail_drives_exit_1(tmp_path: Path):
    # A failed probe with a complete static config still yields exit 1 (contracts §7).
    runner = _ProbeRunner(returncode=1, stderr="boom")
    report = configure_rag(target_root=tmp_path, check=True, runner=runner, **_LOCAL)
    assert report.validation.complete is True
    assert report.exit_code() == 1
