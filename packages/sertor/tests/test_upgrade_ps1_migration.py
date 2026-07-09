"""A-09: `sertor upgrade` migrates a legacy `.ps1` host to single-impl portable `.py` (DA-1).

A host installed by a PREVIOUS version carries PowerShell hooks (`.ps1` files) and their `.ps1`
wiring entries in `settings.json`. An `upgrade` with the portable bundle must leave it single-impl:
the legacy `.ps1` FILES removed (obsolete phase, they are declared legacy-owned) and the legacy
`.ps1` WIRING entries stripped (basename match), while the portable `.py` files/wiring remain.
"""
from __future__ import annotations

import json
from pathlib import Path

from sertor_install_kit.artifacts import LifecycleOp
from sertor_install_kit.assistant import AssistantId
from sertor_installer.install_rag import (
    build_rag_plan,
    execute_rag_lifecycle,
    execute_rag_plan,
)
from sertor_installer.rag_profile import RagHostProfile, RagInstallOptions

_SETTINGS = ".claude/settings.json"
_RAG_PS1 = (
    "sertor-rag-usage-check.ps1", "memory-capture.ps1", "rag-freshness.ps1",
    "rag-freshness-start.ps1", "version-check.ps1", "version-check-start.ps1",
)


def _rag_profile(target: Path) -> RagHostProfile:
    return RagHostProfile.from_options(
        RagInstallOptions(target_root=target, backend="azure", with_deps=False)
    )


def _install_rag(target: Path, runner) -> RagHostProfile:
    profile = _rag_profile(target)
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
    execute_rag_plan(plan, profile, runner, assistant=AssistantId.CLAUDE)
    return profile


def _seed_legacy_ps1(target: Path, basenames: tuple[str, ...]) -> None:
    """Simulate a host installed by a prior version: legacy `.ps1` files + a `.ps1` wiring entry."""
    hooks = target / ".claude" / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    for name in basenames:
        (hooks / name).write_text("# legacy powershell hook\n", encoding="utf-8")
    settings_path = target / _SETTINGS
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    legacy_cmd = (
        "$d = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { '.' }; "
        "& (Join-Path $d '.claude/hooks/rag-freshness.ps1')"
    )
    settings.setdefault("hooks", {}).setdefault("SessionEnd", []).append(
        {"hooks": [{"type": "command", "shell": "powershell", "command": legacy_cmd}]}
    )
    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def test_upgrade_removes_legacy_ps1_files_rag(tmp_path: Path, make_runner):
    profile = _install_rag(tmp_path, make_runner())
    _seed_legacy_ps1(tmp_path, _RAG_PS1)
    for name in _RAG_PS1:
        assert (tmp_path / ".claude/hooks" / name).is_file()  # legacy present pre-upgrade

    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
    execute_rag_lifecycle(
        plan, profile, make_runner(), op=LifecycleOp.UPGRADE, assistant=AssistantId.CLAUDE
    )
    for name in _RAG_PS1:
        assert not (tmp_path / ".claude/hooks" / name).exists()  # legacy `.ps1` removed
    # portable `.py` present (single-impl)
    assert (tmp_path / ".claude/hooks/rag-freshness.py").is_file()
    assert (tmp_path / ".claude/hooks/_hooklib.py").is_file()


def test_upgrade_strips_legacy_ps1_wiring_rag(tmp_path: Path, make_runner):
    profile = _install_rag(tmp_path, make_runner())
    _seed_legacy_ps1(tmp_path, _RAG_PS1)
    settings = json.loads((tmp_path / _SETTINGS).read_text(encoding="utf-8"))
    end_cmds = [h["command"] for e in settings["hooks"]["SessionEnd"] for h in e.get("hooks", [])]
    assert any(".ps1" in c for c in end_cmds)  # legacy wiring present pre-upgrade

    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
    execute_rag_lifecycle(
        plan, profile, make_runner(), op=LifecycleOp.UPGRADE, assistant=AssistantId.CLAUDE
    )
    settings = json.loads((tmp_path / _SETTINGS).read_text(encoding="utf-8"))
    end_cmds = [h["command"] for e in settings["hooks"]["SessionEnd"] for h in e.get("hooks", [])]
    assert not any(".ps1" in c for c in end_cmds)                      # legacy wiring stripped
    assert any("rag-freshness.py" in c for c in end_cmds)             # portable wiring present


def test_upgrade_preserves_user_hook_during_migration(tmp_path: Path, make_runner):
    """The migration strips only Sertor's legacy `.ps1` entries — a user's hook is preserved."""
    profile = _install_rag(tmp_path, make_runner())
    _seed_legacy_ps1(tmp_path, _RAG_PS1)
    settings_path = tmp_path / _SETTINGS
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    settings["hooks"].setdefault("SessionEnd", []).append(
        {"hooks": [{"type": "command", "command": "echo my-own-hook"}]}
    )
    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")

    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
    execute_rag_lifecycle(
        plan, profile, make_runner(), op=LifecycleOp.UPGRADE, assistant=AssistantId.CLAUDE
    )
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    end_cmds = [h["command"] for e in settings["hooks"]["SessionEnd"] for h in e.get("hooks", [])]
    assert "echo my-own-hook" in end_cmds  # user hook survives the migration
