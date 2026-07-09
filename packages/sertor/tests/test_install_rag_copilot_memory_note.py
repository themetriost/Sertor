"""Guard tests for the Copilot CLI `memory-capture` note.

The note (Nota B) is emitted on every `install rag --assistant copilot-cli`, independent of OS and
of the runtime `SERTOR_MEMORY` value (decision D-2). It must NOT appear on Claude (FR-009).

(A-09 removed the E10-FEAT-018 `pwsh` Nota A: the rag/wiki hooks are now portable Python with no
`.ps1` surface, so there is no OS/pwsh detection left to mock — Nota B stands alone.)
"""
from __future__ import annotations

from pathlib import Path

from sertor_install_kit.assistant import AssistantId
from sertor_installer.install_rag import build_rag_plan, execute_rag_plan
from sertor_installer.rag_profile import RagHostProfile, RagInstallOptions

# --- M1: Nota B present on install rag Copilot CLI (US5/CS-4) -----------------------------------


def test_rag_copilot_cli_emits_memory_note(tmp_path: Path, make_runner):
    """Nota B always present on Copilot CLI, independent of OS and SERTOR_MEMORY."""
    options = RagInstallOptions(target_root=tmp_path, backend="azure", with_deps=False)
    profile = RagHostProfile.from_options(options)
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.COPILOT_CLI)
    report = execute_rag_plan(plan, profile, make_runner(), AssistantId.COPILOT_CLI)
    assert any("memory-capture" in n for n in report.notes)  # B1
    assert any("SERTOR_MEMORY_ADAPTER" in n for n in report.notes)  # B2
    assert any("SERTOR_MEMORY" in n for n in report.notes)  # B2
    # B3: "nothing useful" or an equivalent explicit phrase
    assert any("nothing useful" in n or "not capture" in n for n in report.notes)
    # B4: reference to the planned capability
    assert any(
        "FEAT-009" in n or "planned" in n or "memory-conversations" in n for n in report.notes
    )


# --- M2: Nota B absent on install rag Claude (FR-009/CS-3) --------------------------------------


def test_rag_claude_no_memory_note(tmp_path: Path, make_runner):
    options = RagInstallOptions(target_root=tmp_path, backend="azure", with_deps=False)
    profile = RagHostProfile.from_options(options)
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
    report = execute_rag_plan(plan, profile, make_runner(), AssistantId.CLAUDE)
    assert not any("memory-capture" in n for n in report.notes)  # FR-009


# --- M3: no `pwsh` note anywhere (A-09 portable hooks) -----------------------------------------


def test_rag_copilot_cli_no_pwsh_note(tmp_path: Path, make_runner):
    """Post A-09 the rag hooks are portable Python (no `.ps1`), so no `pwsh` gap/note ever fires —
    Nota B (memory-capture) still stands, independent of OS."""
    options = RagInstallOptions(target_root=tmp_path, backend="azure", with_deps=False)
    profile = RagHostProfile.from_options(options)
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.COPILOT_CLI)
    report = execute_rag_plan(plan, profile, make_runner(), AssistantId.COPILOT_CLI)
    assert any("memory-capture" in n for n in report.notes)  # Nota B (still emitted)
    assert not any("pwsh" in n for n in report.notes)  # no pwsh gap: portable hooks
    assert report.exit_code() == 0  # non-fatal
    assert not any(a.target_rel.endswith(".ps1") for a in plan)  # single-impl (DA-1)
