"""Tests for the `--check` live probe of `sertor configure` (feature 051 + 074, US8).

The live probe now invokes the vehicle `sertor-rag doctor --area config --json` (074, E12-FEAT-001),
closing the deferred E2/FEAT-003 US5. These tests exercise the extension point with a `runner` MOCK
only (zero network): honest-degradation, ok/fail branches, and the regression guard that `configure`
without `--check` never calls the runner.
"""
from __future__ import annotations

import json
from pathlib import Path

from sertor_install_kit.command_runner import CommandResult
from sertor_installer.configure import configure_rag


class _ProbeRunner:
    """Mock runner: simulates `sertor-rag doctor` outcomes without spawning a process."""

    def __init__(self, available: bool = True, returncode: int = 0,
                 stdout: str = "", stderr: str = ""):
        self.available = available
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.calls: list[list[str]] = []

    def is_available(self, tool: str) -> bool:
        return self.available

    def run(self, cmd: list[str], cwd: Path, env=None) -> CommandResult:
        self.calls.append(list(cmd))
        return CommandResult(self.returncode, self.stdout, self.stderr)


_LOCAL = dict(backend="local", store="local", explicit_values={}, overwrite=False,
              interactive=False)


def _doctor_json(overall: str, config_problems: list[dict]) -> str:
    return json.dumps(
        {
            "schema": "doctor.report/1",
            "overall": overall,
            "online": False,
            "exit_code": 1 if overall == "fail" else 0,
            "areas": [
                {"name": "config", "status": "fail" if config_problems else "pass",
                 "detail": {}, "problems": config_problems},
                {"name": "provider", "status": "pass", "detail": {}, "problems": []},
                {"name": "index", "status": "pass", "detail": {}, "problems": []},
                {"name": "mcp", "status": "pass", "detail": {}, "problems": []},
            ],
        }
    )


def test_check_not_requested_no_network(tmp_path: Path):
    # configure without --check → runner never called, live_check not requested (FR-017/SC-011).
    runner = _ProbeRunner()
    report = configure_rag(target_root=tmp_path, check=False, runner=runner, **_LOCAL)
    assert runner.calls == []
    assert report.live_check.requested is False
    assert report.live_check.ok is None


def test_probe_live_exit0_config_ok(tmp_path: Path):
    # exit 0 + doctor.report/1 overall=pass → ok=True, detail points to `sertor-rag doctor`.
    runner = _ProbeRunner(returncode=0, stdout=_doctor_json("pass", []))
    report = configure_rag(target_root=tmp_path, check=True, runner=runner, **_LOCAL)
    assert report.live_check.ok is True
    assert "sertor-rag doctor" in report.live_check.detail
    # invoked the new vehicle, NOT the old `sertor-rag check`
    assert runner.calls == [["sertor-rag", "doctor", "--area", "config", "--json"]]


def test_probe_live_exit1_config_incomplete(tmp_path: Path):
    problems = [{"severity": "critical", "code": "env_missing_key",
                 "message": "missing AZURE_OPENAI_API_KEY", "remedy": "set it", "fields": []}]
    runner = _ProbeRunner(returncode=1, stdout=_doctor_json("fail", problems))
    report = configure_rag(target_root=tmp_path, check=True, runner=runner, **_LOCAL)
    assert report.live_check.ok is False
    assert "AZURE_OPENAI_API_KEY" in report.live_check.detail


def test_probe_live_exit2_usage_error(tmp_path: Path):
    runner = _ProbeRunner(returncode=2, stderr="error: argument --area: invalid choice")
    report = configure_rag(target_root=tmp_path, check=True, runner=runner, **_LOCAL)
    assert report.live_check.ok is None
    assert "non disponibile" in report.live_check.detail


def test_probe_live_command_unavailable(tmp_path: Path):
    runner = _ProbeRunner(available=False)
    report = configure_rag(target_root=tmp_path, check=True, runner=runner, **_LOCAL)
    assert report.live_check.ok is None
    assert "non disponibile" in report.live_check.detail
    assert runner.calls == []  # never tried to run an absent tool


def test_check_degrades_when_doctor_missing(tmp_path: Path):
    # exit 2 (unknown command) → honest degradation, ok=None.
    runner = _ProbeRunner(returncode=2, stderr="error: unknown command 'doctor'")
    report = configure_rag(target_root=tmp_path, check=True, runner=runner, **_LOCAL)
    assert report.live_check.requested is True
    assert report.live_check.ok is None
    assert "non disponibile" in report.live_check.detail


def test_check_fails_env_intact(tmp_path: Path):
    # probe failed → ok=False, .env untouched (read-only probe).
    runner = _ProbeRunner(returncode=1, stderr="azure endpoint unreachable")
    report = configure_rag(target_root=tmp_path, check=True, runner=runner, **_LOCAL)
    assert report.live_check.ok is False
    assert (tmp_path / ".sertor" / ".env").exists()


def test_check_fail_drives_exit_1(tmp_path: Path):
    runner = _ProbeRunner(returncode=1, stderr="boom")
    report = configure_rag(target_root=tmp_path, check=True, runner=runner, **_LOCAL)
    assert report.validation.complete is True
    assert report.exit_code() == 1


def test_configure_without_check_no_runner_call(tmp_path: Path):
    # Regression guard: configure without --check → zero runner invocations (FR-017/SC-011/US8-AC2).
    runner = _ProbeRunner()
    configure_rag(target_root=tmp_path, check=False, runner=runner, **_LOCAL)
    assert runner.calls == []


def test_probe_uses_doctor_not_old_check(tmp_path: Path):
    # Regression guard: the old `sertor-rag check` command must NOT be reintroduced.
    runner = _ProbeRunner(returncode=0, stdout=_doctor_json("pass", []))
    configure_rag(target_root=tmp_path, check=True, runner=runner, **_LOCAL)
    assert runner.calls == [["sertor-rag", "doctor", "--area", "config", "--json"]]
    assert ["sertor-rag", "check"] not in runner.calls
