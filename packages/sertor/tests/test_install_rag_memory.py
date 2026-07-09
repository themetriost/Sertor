"""Tests for feature 071 (FEAT-009): conversation-memory distribution via `sertor install rag`.

`install rag` now also deposits the conversation-capture hook (`memory-capture.py`) plus a
`SessionEnd` wiring entry, routed per-assistant (Claude `.claude/settings.json`, Copilot native
`.github/hooks/sertor-hooks.json`), plus the memory knobs in the `.env` template and a mention in
the RAG-usage instruction block. Additive, idempotent, privacy-by-default; the hook is no-op unless
`SERTOR_MEMORY` is enabled. Mirrors the rag-usage hook pattern (FILE + SETTINGS_MERGE).
"""
from __future__ import annotations

import json
from pathlib import Path

from sertor_install_kit.artifacts import ArtifactKind, LifecycleOp, WriteStrategy
from sertor_install_kit.assistant import AssistantId
from sertor_installer.install_rag import (
    build_rag_plan,
    execute_rag_lifecycle,
    execute_rag_plan,
)
from sertor_installer.rag_profile import RagHostProfile, RagInstallOptions
from sertor_installer.resources import asset_path

_MEMORY_HOOK_REL = ".claude/hooks/memory-capture.py"
_MEMORY_HOOK_REL_COPILOT = ".github/hooks/memory-capture.py"
_SETTINGS_REL = ".claude/settings.json"
_COPILOT_WIRING_REL = ".github/hooks/sertor-hooks.json"


def _run(target: Path, runner, assistant=AssistantId.CLAUDE, **opts):
    options = RagInstallOptions(target_root=target, **opts)
    profile = RagHostProfile.from_options(options)
    plan = build_rag_plan(
        profile, with_deps=options.with_deps, mcp_scope=options.mcp_scope, assistant=assistant
    )
    return execute_rag_plan(plan, profile, runner, assistant=assistant), profile


def _profile(target: Path, **opts) -> RagHostProfile:
    return RagHostProfile.from_options(RagInstallOptions(target_root=target, **opts))


# --- plan composition ------------------------------------------------------------------------

def test_plan_contains_memory_hook_and_wiring_claude(tmp_path: Path):
    profile = _profile(tmp_path, backend="azure")
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)

    files = [a for a in plan if a.kind is ArtifactKind.FILE]
    assert any(a.target_rel.replace("\\", "/") == _MEMORY_HOOK_REL for a in files)
    assert all(a.strategy is WriteStrategy.CREATE_IF_ABSENT for a in files)

    settings = [a for a in plan if a.kind is ArtifactKind.SETTINGS_MERGE]
    # rag-usage + memory both merge into the same settings file.
    targets = {a.target_rel.replace("\\", "/") for a in settings}
    assert targets == {_SETTINGS_REL}
    sources = {a.source for a in settings}
    assert "rag/settings.memory-capture.json" in sources


def test_plan_contains_memory_hook_and_wiring_copilot(tmp_path: Path):
    profile = _profile(tmp_path, backend="azure")
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.COPILOT_CLI)

    files = [a.target_rel.replace("\\", "/") for a in plan if a.kind is ArtifactKind.FILE]
    assert _MEMORY_HOOK_REL_COPILOT in files

    settings = [a for a in plan if a.kind is ArtifactKind.SETTINGS_MERGE]
    # Copilot wiring is generated natively (sentinel source) into the dedicated hooks file.
    mem = [a for a in settings if a.source == "(generated: copilot memory-capture hooks)"]
    assert len(mem) == 1
    assert mem[0].target_rel.replace("\\", "/") == _COPILOT_WIRING_REL


# --- install behaviour -----------------------------------------------------------------------

def test_memory_hook_deposited(tmp_path: Path, make_runner):
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    hook = tmp_path / _MEMORY_HOOK_REL
    assert hook.is_file()
    text = hook.read_text(encoding="utf-8")
    assert '"sertor-rag", "memory", "archive"' in text  # delegates to the CLI vehicle (list argv)
    assert "_hooklib.run" in text                       # non-fatal / non-blocking (always exit 0)
    assert "SERTOR_MEMORY" in text                      # privacy gate


def test_memory_hook_create_if_absent_preserves_user_version(tmp_path: Path, make_runner):
    hook = tmp_path / _MEMORY_HOOK_REL
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text("# user customized hook\n", encoding="utf-8")
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    assert hook.read_text(encoding="utf-8") == "# user customized hook\n"


def test_sessionend_entry_added(tmp_path: Path, make_runner):
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    settings = json.loads((tmp_path / _SETTINGS_REL).read_text(encoding="utf-8"))
    assert "SessionEnd" in settings["hooks"]
    cmds = [h["command"] for e in settings["hooks"]["SessionEnd"] for h in e.get("hooks", [])]
    assert any("memory-capture.py" in c for c in cmds)


def test_memory_coexists_with_rag_usage(tmp_path: Path, make_runner):
    # The same settings file carries the rag-usage PreToolUse AND the memory SessionEnd entry.
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    settings = json.loads((tmp_path / _SETTINGS_REL).read_text(encoding="utf-8"))
    assert "PreToolUse" in settings["hooks"]
    assert "SessionEnd" in settings["hooks"]


def test_sessionend_preserves_existing_hooks(tmp_path: Path, make_runner):
    settings_path = tmp_path / _SETTINGS_REL
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps(
            {
                "hooks": {
                    "SessionEnd": [{"hooks": [{"type": "command", "command": "echo mine"}]}]
                }
            }
        ),
        encoding="utf-8",
    )
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    cmds = [h["command"] for e in settings["hooks"]["SessionEnd"] for h in e["hooks"]]
    assert "echo mine" in cmds                                   # user hook preserved
    assert any("memory-capture.py" in c for c in cmds)          # ours added


def test_memory_install_idempotent(tmp_path: Path, make_runner):
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    before = (tmp_path / _SETTINGS_REL).read_text(encoding="utf-8")
    hook_before = (tmp_path / _MEMORY_HOOK_REL).read_text(encoding="utf-8")
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    settings = json.loads((tmp_path / _SETTINGS_REL).read_text(encoding="utf-8"))
    sessionend_cmds = [
        h["command"] for e in settings["hooks"]["SessionEnd"] for h in e.get("hooks", [])
    ]
    # no duplicate memory entry
    assert sum("memory-capture.py" in c for c in sessionend_cmds) == 1
    assert (tmp_path / _SETTINGS_REL).read_text(encoding="utf-8") == before
    assert (tmp_path / _MEMORY_HOOK_REL).read_text(encoding="utf-8") == hook_before


# --- copilot native wiring -------------------------------------------------------------------

def test_copilot_memory_wiring_generated_native(tmp_path: Path, make_runner):
    _run(
        tmp_path, make_runner(), assistant=AssistantId.COPILOT_CLI,
        backend="azure", with_deps=False,
    )
    wiring = json.loads((tmp_path / _COPILOT_WIRING_REL).read_text(encoding="utf-8"))
    assert wiring["version"] == 1                       # native schema (R1)
    assert "SessionEnd" in wiring["hooks"]
    entry = wiring["hooks"]["SessionEnd"][0]
    assert "memory-capture.py" in entry["command"]
    assert "timeoutSec" in entry and "timeout" not in entry   # native field (R4)
    # coexists with the rag-usage PreToolUse wiring in the same dedicated file
    assert "PreToolUse" in wiring["hooks"]


# --- instruction block mention ---------------------------------------------------------------

def test_claude_md_block_mentions_memory(tmp_path: Path, make_runner):
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    md = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert "sertor-rag memory" in md
    assert "SERTOR_MEMORY=true" in md


# --- lifecycle: uninstall --------------------------------------------------------------------

def test_uninstall_removes_memory_preserving_user_hook(tmp_path: Path, make_runner):
    settings_path = tmp_path / _SETTINGS_REL
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps(
            {"hooks": {"SessionEnd": [{"hooks": [{"type": "command", "command": "echo mine"}]}]}}
        ),
        encoding="utf-8",
    )
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    assert (tmp_path / _MEMORY_HOOK_REL).is_file()

    profile = _profile(tmp_path, backend="azure", with_deps=False)
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
    execute_rag_lifecycle(
        plan, profile, make_runner(), op=LifecycleOp.UNINSTALL, assistant=AssistantId.CLAUDE
    )

    assert not (tmp_path / _MEMORY_HOOK_REL).exists()            # hook removed
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    cmds = [h["command"] for e in settings["hooks"].get("SessionEnd", []) for h in e["hooks"]]
    assert "echo mine" in cmds                                   # user hook preserved
    assert not any("memory-capture.py" in c for c in cmds)      # ours removed


# --- asset form ------------------------------------------------------------------------------

def test_memory_hook_asset_form():
    text = Path(str(asset_path("rag/hooks/memory-capture.py"))).read_text(encoding="utf-8")
    assert '"sertor-rag", "memory", "archive"' in text  # delegates to the CLI vehicle (list argv)
    assert "_hooklib.run" in text                       # non-fatal fail-safe runner (always exit 0)
