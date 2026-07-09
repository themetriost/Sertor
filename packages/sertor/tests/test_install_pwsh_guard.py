"""Guard tests for the install-time `pwsh` note (E10-FEAT-018, US1/US2/US3/US4).

OS mocking via `monkeypatch.setattr(host_env, ...)` keeps the non-Windows branch deterministic on
the Windows CI (INV-7). The note lands in `report.notes` (schema `install.report/1`, additive) on
both `install rag` and `install wiki`. Contracts: install-notes.md §Nota A, pwsh-guard.md.
"""
from __future__ import annotations

import json
from pathlib import Path

import sertor_install_kit.host_env as host_env
from sertor_install_kit.assistant import AssistantId
from sertor_installer.config_gen import build_host_profile
from sertor_installer.install_rag import build_rag_plan, execute_rag_plan
from sertor_installer.install_wiki import build_install_plan, execute_plan
from sertor_installer.rag_profile import RagHostProfile, RagInstallOptions

# --- G1: A-09 — the rag hooks are portable, so NO pwsh note fires (single-impl, DA-1) -----------


def test_rag_install_no_pwsh_note_now_hooks_are_portable(
    monkeypatch, tmp_path: Path, make_runner
):
    """A-09 (E2): the rag lifecycle hooks are portable Python (run via `uv run --no-project
    python`), so `install rag` deposits NO `.ps1` surface and the E10-FEAT-018 pwsh guard — which
    fired ONLY for `.ps1` hooks — no longer has anything to warn about. Even on non-Windows without
    `pwsh`, the rag report carries no pwsh note (the pwsh gap is closed by portability, not muted).
    """
    monkeypatch.setattr(host_env, "is_windows", lambda: False)
    monkeypatch.setattr(host_env, "pwsh_available", lambda: False)
    options = RagInstallOptions(target_root=tmp_path, backend="azure", with_deps=False)
    profile = RagHostProfile.from_options(options)
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
    # single-impl portable (DA-1): the plan carries no `.ps1` surface at all.
    assert not any(a.target_rel.endswith(".ps1") for a in plan)
    report = execute_rag_plan(plan, profile, make_runner(), AssistantId.CLAUDE)
    assert not any("pwsh" in n for n in report.notes)  # no pwsh gap → no note
    assert report.exit_code() == 0  # non-fatal (FR-005)
    # and nothing pwsh-related leaks into the JSON payload either (FR-003)
    payload = json.loads(report.render_json())
    assert not any("pwsh" in n for n in payload.get("notes", []))


# --- G2: Nota A absent — non-Windows with pwsh, install rag (US2/CS-2) --------------------------


def test_rag_install_no_pwsh_note_when_pwsh_present(monkeypatch, tmp_path: Path, make_runner):
    monkeypatch.setattr(host_env, "is_windows", lambda: False)
    monkeypatch.setattr(host_env, "pwsh_available", lambda: True)
    options = RagInstallOptions(target_root=tmp_path, backend="azure", with_deps=False)
    profile = RagHostProfile.from_options(options)
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
    report = execute_rag_plan(plan, profile, make_runner(), AssistantId.CLAUDE)
    assert not any("pwsh" in n and "non-operational" in n for n in report.notes)


# --- G3: Nota A present — non-Windows without pwsh, install wiki Claude (US1/CS-1) --------------


def test_wiki_install_emits_pwsh_note_on_non_windows_no_pwsh(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(host_env, "is_windows", lambda: False)
    monkeypatch.setattr(host_env, "pwsh_available", lambda: False)
    profile = build_host_profile(tmp_path)
    plan = build_install_plan(AssistantId.CLAUDE)
    report = execute_plan(plan, profile, AssistantId.CLAUDE)
    assert any("pwsh" in n for n in report.notes)  # A1
    assert report.exit_code() == 0  # non-fatal (FR-005)


# --- G4: non-regression Claude+Windows, install rag (US3/CS-3) ---------------------------------


def test_rag_claude_windows_no_notes(monkeypatch, tmp_path: Path, make_runner):
    """NR: report has no pwsh nor Copilot note on Windows + Claude (INV-5)."""
    monkeypatch.setattr(host_env, "is_windows", lambda: True)
    options = RagInstallOptions(target_root=tmp_path, backend="azure", with_deps=False)
    profile = RagHostProfile.from_options(options)
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
    report = execute_rag_plan(plan, profile, make_runner(), AssistantId.CLAUDE)
    assert not any("pwsh" in n and "non-operational" in n for n in report.notes)
    assert not any("memory-capture" in n for n in report.notes)  # FR-009: no Copilot note on Claude


# --- G5: non-regression Claude+Windows, install wiki (US3/CS-3) --------------------------------


def test_wiki_claude_windows_no_notes(monkeypatch, tmp_path: Path):
    """NR (explicit OS mocking): report.notes == [] on Windows + Claude (mirrors the existing
    test_claude_report_has_no_gap_note, more robust)."""
    monkeypatch.setattr(host_env, "is_windows", lambda: True)
    profile = build_host_profile(tmp_path)
    plan = build_install_plan(AssistantId.CLAUDE)
    report = execute_plan(plan, profile, AssistantId.CLAUDE)
    assert report.notes == []  # invariant (CS-3)
