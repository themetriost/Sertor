"""Tests for E2-FEAT-013: auto-update version check via `sertor install rag`.

`install rag` now also deposits the version-check hook (`version-check.ps1`, SessionEnd: GET the
remote `/VERSION` + compare with the install-time stamp + persist the verdict) plus a SessionStart
signal (`version-check-start.ps1` on Claude; a static native prompt on Copilot CLI — W5). Routed
per-assistant (Claude `.claude/settings.json`, Copilot native `.github/hooks/sertor-hooks.json`).
The installer also writes the version stamp `.sertor/.sertor-version` IN-PROCESS at install/upgrade
time (D-3 — never the hook at runtime). Additive, isolated from rag-freshness/memory-capture; the
hook is non-fatal (exit 0 always) and does only HTTP+file (no `sertor_core`, FR-014). Twin of the
rag-freshness hook pattern (FILE + SETTINGS_MERGE), no new ArtifactKind.
"""
from __future__ import annotations

import json
from pathlib import Path

from sertor_install_kit.artifacts import ArtifactKind, LifecycleOp, WriteStrategy
from sertor_install_kit.assistant import AssistantId
from sertor_install_kit.gitignore_append import RUNTIME_IGNORES
from sertor_installer.install_rag import (
    _COPILOT_VERSION_CHECK_END_WIRING_SENTINEL,
    _COPILOT_VERSION_CHECK_START_WIRING_SENTINEL,
    _VERSION_CHECK_HOOK_TARGET,
    _VERSION_CHECK_START_TARGET,
    _VERSION_STAMP_TARGET,
    build_rag_plan,
    execute_rag_lifecycle,
    execute_rag_plan,
    sertor_owned_paths,
)
from sertor_installer.rag_profile import RagHostProfile, RagInstallOptions
from sertor_installer.resources import asset_path

_VC_HOOK_REL = ".claude/hooks/version-check.ps1"
_VC_START_REL = ".claude/hooks/version-check-start.ps1"
_VC_HOOK_REL_COPILOT = ".github/hooks/version-check.ps1"
_VC_START_REL_COPILOT = ".github/hooks/version-check-start.ps1"
_SETTINGS_REL = ".claude/settings.json"
_COPILOT_WIRING_REL = ".github/hooks/sertor-hooks.json"


def _profile(target: Path, **opts) -> RagHostProfile:
    return RagHostProfile.from_options(RagInstallOptions(target_root=target, **opts))


def _run(target: Path, runner, assistant=AssistantId.CLAUDE, **opts):
    options = RagInstallOptions(target_root=target, **opts)
    profile = RagHostProfile.from_options(options)
    plan = build_rag_plan(
        profile, with_deps=options.with_deps, mcp_scope=options.mcp_scope, assistant=assistant
    )
    return execute_rag_plan(plan, profile, runner, assistant=assistant), profile


def _norm(rel: str) -> str:
    return rel.replace("\\", "/")


# --- US8-AC1: Claude deposit (script + wiring entries) ----------------------------------------

def test_version_check_hook_deposited_claude(tmp_path: Path):
    profile = _profile(tmp_path, backend="azure")
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
    files = [_norm(a.target_rel) for a in plan if a.kind is ArtifactKind.FILE]
    assert _VC_HOOK_REL in files
    file_arts = [a for a in plan if a.kind is ArtifactKind.FILE]
    assert all(a.strategy is WriteStrategy.CREATE_IF_ABSENT for a in file_arts)


def test_version_check_start_deposited_claude(tmp_path: Path):
    profile = _profile(tmp_path, backend="azure")
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
    files = [_norm(a.target_rel) for a in plan if a.kind is ArtifactKind.FILE]
    assert _VC_START_REL in files


def test_version_check_session_end_settings_claude(tmp_path: Path):
    profile = _profile(tmp_path, backend="azure")
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
    settings = [a for a in plan if a.kind is ArtifactKind.SETTINGS_MERGE]
    sources = {a.source for a in settings}
    assert "rag/settings.version-check.json" in sources
    end = [a for a in settings if a.source == "rag/settings.version-check.json"]
    assert _norm(end[0].target_rel) == _SETTINGS_REL


def test_version_check_session_start_settings_claude(tmp_path: Path):
    profile = _profile(tmp_path, backend="azure")
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
    settings = [a for a in plan if a.kind is ArtifactKind.SETTINGS_MERGE]
    sources = {a.source for a in settings}
    assert "rag/settings.version-check-start.json" in sources


def test_version_check_isolated_from_freshness(tmp_path: Path):
    """The plan carries BOTH the rag-freshness AND the version-check SessionEnd as DISTINCT
    artifacts — not fused into a single script (W3/FR-016)."""
    profile = _profile(tmp_path, backend="azure")
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
    files = [_norm(a.target_rel) for a in plan if a.kind is ArtifactKind.FILE]
    assert ".claude/hooks/rag-freshness.ps1" in files
    assert _VC_HOOK_REL in files
    settings = [a for a in plan if a.kind is ArtifactKind.SETTINGS_MERGE]
    sources = {a.source for a in settings}
    assert "rag/settings.rag-freshness.json" in sources
    assert "rag/settings.version-check.json" in sources


def test_version_check_settings_merge_both_events_claude(tmp_path: Path, make_runner):
    """After install, `.claude/settings.json` carries both the SessionEnd and SessionStart
    version-check entries, alongside the pre-existing hooks (additive, FR-016)."""
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    settings = json.loads((tmp_path / _SETTINGS_REL).read_text(encoding="utf-8"))
    end_cmds = [h["command"] for e in settings["hooks"]["SessionEnd"] for h in e.get("hooks", [])]
    assert any("version-check.ps1" in c for c in end_cmds)
    start_cmds = [
        h["command"] for e in settings["hooks"]["SessionStart"] for h in e.get("hooks", [])
    ]
    assert any("version-check-start.ps1" in c for c in start_cmds)
    # rag-freshness still present (isolation)
    assert any("rag-freshness.ps1" in c for c in end_cmds)


# --- install behaviour: script content / non-fatal --------------------------------------------

def test_version_check_hook_content(tmp_path: Path, make_runner):
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    hook = tmp_path / _VC_HOOK_REL
    assert hook.is_file()
    text = hook.read_text(encoding="utf-8")
    assert "Invoke-WebRequest" in text          # GET of the remote /VERSION
    assert "SERTOR_VERSION_CHECK_URL" in text   # overridable URL (env)
    assert "version.check/1" in text            # writes the contract schema
    assert ".sertor-version" in text            # reads the install-time stamp (no Python)
    assert "exit 0" in text                     # non-fatal


def test_version_check_start_content(tmp_path: Path, make_runner):
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    start = tmp_path / _VC_START_REL
    assert start.is_file()
    text = start.read_text(encoding="utf-8")
    assert ".version-check.json" in text   # reads the persisted state
    assert "exit 0" in text                # non-fatal
    # D<->N (FR-014): the start hook only WARNS; it must NOT apply any update.
    assert "Invoke-WebRequest" not in text   # zero network at SessionStart (W6/RNF-1)


def test_version_check_scripts_no_sertor_core(tmp_path: Path, make_runner):
    """Principio XI + D<->N: the scripts never import the library, run Python, nor invoke an LLM."""
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    for rel in (_VC_HOOK_REL, _VC_START_REL):
        text = (tmp_path / rel).read_text(encoding="utf-8").lower()
        assert "import sertor_core" not in text
        assert "openai" not in text and "anthropic" not in text
        # No Python is run in the hot path (D-3): the installed version is read from the stamp.
        assert "importlib.metadata.version" not in text
        assert "python -c" not in text


# --- US8-AC2: Copilot deposit (native format + parity) ----------------------------------------

def test_version_check_hook_deposited_copilot(tmp_path: Path):
    profile = _profile(tmp_path, backend="azure")
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.COPILOT_CLI)
    files = [_norm(a.target_rel) for a in plan if a.kind is ArtifactKind.FILE]
    assert _VC_HOOK_REL_COPILOT in files


def test_version_check_start_NOT_deposited_copilot(tmp_path: Path):
    """W5/R-3: the Copilot SessionStart is a static prompt — NO `version-check-start.ps1` script."""
    profile = _profile(tmp_path, backend="azure")
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.COPILOT_CLI)
    files = [_norm(a.target_rel) for a in plan if a.kind is ArtifactKind.FILE]
    assert _VC_START_REL_COPILOT not in files
    assert _VC_START_REL not in files


def test_version_check_end_wiring_copilot_native_format(tmp_path: Path, make_runner):
    _run(
        tmp_path, make_runner(), assistant=AssistantId.COPILOT_CLI,
        backend="azure", with_deps=False,
    )
    wiring = json.loads((tmp_path / _COPILOT_WIRING_REL).read_text(encoding="utf-8"))
    assert wiring["version"] == 1                       # native schema (R-1/W1)
    assert "SessionEnd" in wiring["hooks"]
    entry = next(
        e for e in wiring["hooks"]["SessionEnd"] if "version-check.ps1" in e.get("command", "")
    )
    assert entry["type"] == "command"
    assert "timeoutSec" in entry and "timeout" not in entry   # native field (W1)
    assert "shell" not in entry and "statusMessage" not in entry


def test_version_check_start_wiring_copilot_native_prompt(tmp_path: Path, make_runner):
    _run(
        tmp_path, make_runner(), assistant=AssistantId.COPILOT_CLI,
        backend="azure", with_deps=False,
    )
    wiring = json.loads((tmp_path / _COPILOT_WIRING_REL).read_text(encoding="utf-8"))
    assert "SessionStart" in wiring["hooks"]
    entry = next(
        e for e in wiring["hooks"]["SessionStart"]
        if e.get("type") == "prompt" and "version-check.json" in e.get("prompt", "")
    )
    assert "prompt" in entry and "command" not in entry      # W5: prompt payload, not command
    assert "timeoutSec" in entry


def test_version_check_no_claude_format_on_copilot(tmp_path: Path, make_runner):
    """Parity (FEAT-011/049): no Claude-only fields leak into the Copilot wiring file."""
    _run(
        tmp_path, make_runner(), assistant=AssistantId.COPILOT_CLI,
        backend="azure", with_deps=False,
    )
    wiring = json.loads((tmp_path / _COPILOT_WIRING_REL).read_text(encoding="utf-8"))
    for event_entries in wiring["hooks"].values():
        for entry in event_entries:
            assert "shell" not in entry
            assert "statusMessage" not in entry
            assert "timeout" not in entry   # only timeoutSec


def test_copilot_version_check_sentinels_are_generated(tmp_path: Path):
    """The Copilot version-check wiring uses GENERATED sentinel sources, not static assets."""
    profile = _profile(tmp_path, backend="azure")
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.COPILOT_CLI)
    sources = {a.source for a in plan if a.kind is ArtifactKind.SETTINGS_MERGE}
    assert _COPILOT_VERSION_CHECK_END_WIRING_SENTINEL in sources
    assert _COPILOT_VERSION_CHECK_START_WIRING_SENTINEL in sources


# --- US5/US6: install-time version stamp (D-3/R-4) --------------------------------------------

def test_version_stamp_written_at_install(tmp_path: Path, make_runner):
    """The installer writes `.sertor/.sertor-version` in-process at install time (NOT the hook)."""
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    stamp = tmp_path / _VERSION_STAMP_TARGET
    assert stamp.is_file()
    assert stamp.read_text(encoding="utf-8").strip()   # non-empty version


def test_version_check_runtime_ignores():
    """RUNTIME_IGNORES (kit) carries the 3 new state/stamp entries (FR-018/TASK-F03)."""
    assert ".sertor/.version-check.json" in RUNTIME_IGNORES
    assert ".sertor/.sertor-version" in RUNTIME_IGNORES
    assert ".sertor/.sertor-flow-version" in RUNTIME_IGNORES


# --- lifecycle: owned paths / uninstall / upgrade ---------------------------------------------

def test_version_check_owned_files_claude():
    owned = sertor_owned_paths(AssistantId.CLAUDE)
    covered = owned.covered_targets()
    assert _VERSION_CHECK_HOOK_TARGET in covered
    assert _VERSION_CHECK_START_TARGET in covered


def test_version_check_owned_files_copilot():
    """W5: Copilot owns only the SessionEnd script, never a SessionStart `.ps1`."""
    owned = sertor_owned_paths(AssistantId.COPILOT_CLI)
    covered = owned.covered_targets()
    assert _VC_HOOK_REL_COPILOT in covered
    assert _VC_START_REL_COPILOT not in covered


def test_uninstall_removes_version_check_scripts(tmp_path: Path, make_runner):
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    assert (tmp_path / _VC_HOOK_REL).is_file()
    assert (tmp_path / _VC_START_REL).is_file()

    profile = _profile(tmp_path, backend="azure", with_deps=False)
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
    execute_rag_lifecycle(
        plan, profile, make_runner(), op=LifecycleOp.UNINSTALL, assistant=AssistantId.CLAUDE
    )
    assert not (tmp_path / _VC_HOOK_REL).exists()
    assert not (tmp_path / _VC_START_REL).exists()


def test_upgrade_updates_version_check_script_and_rewrites_stamp(tmp_path: Path, make_runner):
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    hook = tmp_path / _VC_HOOK_REL
    hook.write_text("# stale\n", encoding="utf-8")  # simulate an outdated installed copy
    stamp = tmp_path / _VERSION_STAMP_TARGET
    stamp.write_text("0.0.1\n", encoding="utf-8")   # simulate an outdated stamp

    profile = _profile(tmp_path, backend="azure", with_deps=False)
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
    execute_rag_lifecycle(
        plan, profile, make_runner(), op=LifecycleOp.UPGRADE, assistant=AssistantId.CLAUDE
    )
    refreshed = hook.read_text(encoding="utf-8")
    assert "Invoke-WebRequest" in refreshed         # upgraded to the bundled body
    # the stamp is rewritten with the real installed version (closes the loop, INV-5/FR-013)
    assert stamp.read_text(encoding="utf-8").strip() != "0.0.1"


def test_version_check_install_idempotent(tmp_path: Path, make_runner):
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    before = (tmp_path / _SETTINGS_REL).read_text(encoding="utf-8")
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    settings = json.loads((tmp_path / _SETTINGS_REL).read_text(encoding="utf-8"))
    end_cmds = [h["command"] for e in settings["hooks"]["SessionEnd"] for h in e.get("hooks", [])]
    assert sum("version-check.ps1" in c for c in end_cmds) == 1
    assert (tmp_path / _SETTINGS_REL).read_text(encoding="utf-8") == before


# --- asset form -------------------------------------------------------------------------------

def test_version_check_assets_present():
    end = Path(str(asset_path("rag/hooks/version-check.ps1"))).read_text(encoding="utf-8")
    assert "version.check/1" in end
    start = Path(str(asset_path("rag/hooks/version-check-start.ps1"))).read_text(encoding="utf-8")
    assert ".version-check.json" in start


def test_version_check_script_has_try_catch_and_exit0():
    """R-2/RNF-2: the SessionEnd script has a global try/catch and exits 0 always."""
    text = Path(str(asset_path("rag/hooks/version-check.ps1"))).read_text(encoding="utf-8")
    assert "try {" in text and "} catch" in text
    assert "exit 0" in text
