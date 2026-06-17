"""Acceptance tests for `install wiki --assistant copilot-cli` (FEAT-012, US2 + US3).

Host simulated in `tmp_path`. US2: instruction block in `.github/copilot-instructions.md`
(idempotent). US3: COMMANDs (`/wiki`, `wiki-author`) rendered as custom-agents in `.github/agents/`
(the only CLI-invocable form — NOT prompt-files), custom-agent persona in `.github/agents/`, native
hook wiring in `.github/hooks/*.json` (SessionStart as a native prompt, Stop/SessionEnd via the
reused script). The VS Code (`copilot`) target was removed (FEAT-012): no `.github/prompts/**`.
"""
from __future__ import annotations

import json
from pathlib import Path

from sertor_install_kit.assistant import AssistantId
from sertor_installer.config_gen import build_host_profile
from sertor_installer.install_wiki import build_install_plan, execute_plan
from sertor_installer.resources import read_asset_text


def _install(target: Path, assistant: AssistantId = AssistantId.COPILOT_CLI, **kwargs):
    profile = build_host_profile(target, **kwargs)
    plan = build_install_plan(assistant)
    return execute_plan(plan, profile, assistant)


# ---------------------------------------------------------------- US2: instruction block

def test_instruction_block_in_copilot_instructions(tmp_path: Path):  # FR-008/009
    report = _install(tmp_path)
    assert report.exit_code() == 0
    instr = tmp_path / ".github" / "copilot-instructions.md"
    assert instr.is_file()
    text = instr.read_text(encoding="utf-8")
    assert "SERTOR:WIKI-RITUAL START" in text
    # no Claude instruction file written for copilot-cli
    assert not (tmp_path / "CLAUDE.md").exists()


def test_instruction_block_idempotent(tmp_path: Path):  # FR-009
    _install(tmp_path)
    instr = tmp_path / ".github" / "copilot-instructions.md"
    before = instr.read_bytes()
    report2 = _install(tmp_path)
    assert report2.exit_code() == 0
    assert instr.read_bytes() == before  # block already present → untouched


# -------------------------------------------------- US3: COMMANDs are custom-agents (C2.4/C2.5)

def test_cli_command_is_custom_agent_not_prompt_file(tmp_path: Path):  # FR-003 / SC-004
    """CLI: `/wiki` and `wiki-author` COMMANDs are custom-agents (CLI-invocable), never prompt
    files — the VS Code prompt-file vehicle was removed (FEAT-012)."""
    _install(tmp_path)
    assert (tmp_path / ".github/agents/wiki.agent.md").is_file()
    assert (tmp_path / ".github/agents/wiki-author.agent.md").is_file()
    assert not (tmp_path / ".github/prompts/wiki.prompt.md").exists()
    assert not (tmp_path / ".github/prompts").exists()
    # no Claude commands/skills dirs for copilot-cli
    assert not (tmp_path / ".claude").exists()


def test_custom_agent_present_and_formed(tmp_path: Path):  # FR-011
    _install(tmp_path)
    agent = tmp_path / ".github" / "agents" / "wiki-curator.agent.md"
    assert agent.is_file()
    text = agent.read_text(encoding="utf-8")
    assert text.startswith("---")
    assert "name: wiki-curator" in text


def test_custom_agent_omits_model(tmp_path: Path):  # FR-017 / SC-005
    _install(tmp_path)
    from sertor_installer.surfaces import split_frontmatter

    text = (tmp_path / ".github/agents/wiki-curator.agent.md").read_text(encoding="utf-8")
    assert "model:" not in split_frontmatter(text)[0]


# ---------------------------------------------------------------- US3: hook wiring (native schema)

def _wiring(tmp_path: Path) -> dict:
    return json.loads(
        (tmp_path / ".github" / "hooks" / "sertor-hooks.json").read_text(encoding="utf-8")
    )


def test_hook_wiring_session_events(tmp_path: Path):  # FR-012
    _install(tmp_path)
    wiring = tmp_path / ".github" / "hooks" / "sertor-hooks.json"
    assert wiring.is_file()
    data = json.loads(wiring.read_text(encoding="utf-8"))
    assert "SessionStart" in data["hooks"]
    assert "Stop" in data["hooks"]


def test_wiki_wiring_is_native_copilot_schema(tmp_path: Path):  # FR-001..004 / R1..R4
    _install(tmp_path)
    data = _wiring(tmp_path)
    assert data["version"] == 1                                  # R1
    for entries in data["hooks"].values():
        for entry in entries:
            assert "hooks" not in entry                          # R2 (flat, no nesting)
            assert "shell" not in entry                          # R3
            assert "statusMessage" not in entry                  # R3
            assert "timeout" not in entry                        # R4 (timeoutSec only)


def test_wiki_stop_command_passes_assistant_copilot(tmp_path: Path):
    _install(tmp_path)
    stop = _wiring(tmp_path)["hooks"]["Stop"][0]
    assert "-Assistant copilot" in stop["command"]
    assert "-Mode Stop" in stop["command"]
    assert stop["timeoutSec"] == 10


def test_cli_session_start_is_prompt_not_command(tmp_path: Path):  # FR-006 / SC-003
    """CLI: SessionStart is `type:"prompt"` (a static directive), never a bare command-string —
    the native Copilot CLI hook form (FEAT-011, invariant under FEAT-012)."""
    _install(tmp_path)
    ss = _wiring(tmp_path)["hooks"]["SessionStart"][0]
    assert ss["type"] == "prompt"
    # a prompt-hook carries its text in `prompt`, NOT `command` (Copilot ignores `command` here)
    assert isinstance(ss["prompt"], str) and ss["prompt"].strip()
    assert "command" not in ss
    # the VS Code session-start script is NOT installed (FEAT-012: no VS Code target)
    assert not (tmp_path / ".github/hooks/wiki-session-start.ps1").exists()


def test_hook_script_reused_identically(tmp_path: Path):  # FR-014 / surface-mapping prop.3
    _install(tmp_path)
    copied = tmp_path / ".github" / "hooks" / "wiki-pending-check.ps1"
    assert copied.is_file()
    canonical = read_asset_text("claude/hooks/wiki-pending-check.ps1")
    assert copied.read_text(encoding="utf-8") == canonical


# ---------------------------------------------------------------- scaffold + idempotence + report

def test_wiki_scaffold_assistant_agnostic(tmp_path: Path):
    """CONFIG + STRUCTURE land in `wiki/` regardless of assistant."""
    _install(tmp_path)
    assert (tmp_path / "wiki" / "wiki.config.toml").is_file()
    assert (tmp_path / "wiki" / "index.md").is_file()


def test_cli_double_run_idempotent(tmp_path: Path):  # FR-040 / NFR-1
    """The CLI plan re-run leaves the filesystem stable (idempotence)."""
    _install(tmp_path)
    snapshot = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    report2 = _install(tmp_path)
    assert report2.exit_code() == 0
    assert report2.created == 0
    assert report2.block == 0
    after = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert snapshot.keys() == after.keys()
    for p, content in snapshot.items():
        assert after[p] == content, f"{p} changed on re-run"


def test_report_declares_assistant(tmp_path: Path):  # Principio IX
    report = _install(tmp_path)
    assert report.assistant == "copilot-cli"
    payload = json.loads(report.render_json())
    assert payload["assistant"] == "copilot-cli"


def test_cli_report_has_no_vscode_gap(tmp_path: Path):
    """The CLI does not use any VS Code mechanism → no [ASSUNTO-VSC] gap note (FEAT-012)."""
    report = _install(tmp_path)
    assert not any("[ASSUNTO-VSC]" in n for n in report.notes)


def test_claude_report_has_no_gap_note(tmp_path: Path):  # non-regression
    profile = build_host_profile(tmp_path)
    plan = build_install_plan(AssistantId.CLAUDE)
    report = execute_plan(plan, profile, AssistantId.CLAUDE)
    assert report.notes == []
