"""Unit tests for `sertor_install_kit.host_env` (E10-FEAT-018).

Pure builder + gating, OS mocking via `monkeypatch.setattr(host_env, ...)` — deterministic on the
Windows CI (the non-Windows branch is simulated, never the real OS — INV-7/R-6).
"""
from __future__ import annotations

from sertor_install_kit import host_env
from sertor_install_kit.report import InstallReport


def _make_report(tmp_path) -> InstallReport:
    return InstallReport(target=str(tmp_path), capability="rag")


# --- T1: pure builder, stable substrings -------------------------------------------------------


def test_pwsh_unavailability_note_contains_required_substrings():
    surfaces = [".github/hooks/rag-freshness.ps1", ".github/hooks/memory-capture.ps1"]
    note = host_env.pwsh_unavailability_note(surfaces)
    assert "pwsh" in note  # A1: mentions pwsh
    assert "learn.microsoft.com/powershell" in note  # A2: remediation URL
    assert ".ps1" in note  # A3: affected surfaces
    assert "non-operational" in note or "not-operational" in note  # A4: explicit state


# --- T2: maybe_note_pwsh truth table (contracts/pwsh-guard.md) ----------------------------------


def test_maybe_note_pwsh_emits_on_non_windows_no_pwsh(monkeypatch, tmp_path):
    """Row 1: non-Windows, pwsh absent, hooks deposited → Nota A."""
    monkeypatch.setattr(host_env, "is_windows", lambda: False)
    monkeypatch.setattr(host_env, "pwsh_available", lambda: False)
    report = _make_report(tmp_path)
    host_env.maybe_note_pwsh(report, [".github/hooks/rag-freshness.ps1"])
    assert len(report.notes) == 1
    assert "pwsh" in report.notes[0]


def test_maybe_note_pwsh_no_note_if_pwsh_present(monkeypatch, tmp_path):
    """Row 2: non-Windows, pwsh present → no note."""
    monkeypatch.setattr(host_env, "is_windows", lambda: False)
    monkeypatch.setattr(host_env, "pwsh_available", lambda: True)
    report = _make_report(tmp_path)
    host_env.maybe_note_pwsh(report, [".github/hooks/rag-freshness.ps1"])
    assert report.notes == []


def test_maybe_note_pwsh_no_note_on_windows(monkeypatch, tmp_path):
    """Row 3: Windows → no note (INV-5, no false positive)."""
    monkeypatch.setattr(host_env, "is_windows", lambda: True)
    # pwsh_available is not called on Windows — no patch needed
    report = _make_report(tmp_path)
    host_env.maybe_note_pwsh(report, [".claude/hooks/rag-freshness.ps1"])
    assert report.notes == []


def test_maybe_note_pwsh_no_note_if_no_hooks(monkeypatch, tmp_path):
    """Row 4 (edge): no hook in the plan → no note (no-op)."""
    monkeypatch.setattr(host_env, "is_windows", lambda: False)
    monkeypatch.setattr(host_env, "pwsh_available", lambda: False)
    report = _make_report(tmp_path)
    host_env.maybe_note_pwsh(report, [])  # no hooks
    assert report.notes == []


# --- T3: non-fatal (INV-1) ---------------------------------------------------------------------


def test_maybe_note_pwsh_does_not_raise(monkeypatch, tmp_path):
    monkeypatch.setattr(host_env, "is_windows", lambda: False)
    monkeypatch.setattr(host_env, "pwsh_available", lambda: False)
    report = _make_report(tmp_path)
    host_env.maybe_note_pwsh(report, [".github/hooks/rag-freshness.ps1"])
    assert report.exit_code() == 0  # INV-1: non-fatal, exit_code unchanged


# --- T4: idempotence (.note() dedup) -----------------------------------------------------------


def test_maybe_note_pwsh_idempotent(monkeypatch, tmp_path):
    monkeypatch.setattr(host_env, "is_windows", lambda: False)
    monkeypatch.setattr(host_env, "pwsh_available", lambda: False)
    report = _make_report(tmp_path)
    surfaces = [".github/hooks/rag-freshness.ps1"]
    host_env.maybe_note_pwsh(report, surfaces)
    host_env.maybe_note_pwsh(report, surfaces)  # second call → no-op
    assert len(report.notes) == 1  # no duplicate
