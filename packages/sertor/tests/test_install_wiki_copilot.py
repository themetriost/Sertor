"""Acceptance tests for `install wiki --assistant copilot` (feature 044, US2 + US3).

Host simulated in `tmp_path`. US2: instruction block in `.github/copilot-instructions.md`
(idempotent), prompt-files in `.github/prompts/`. US3: custom-agent in `.github/agents/`, hook
wiring in `.github/hooks/*.json` with SessionStart/Stop, hook script reused identically.
"""
from __future__ import annotations

import json
from pathlib import Path

from sertor_install_kit.assistant import AssistantId
from sertor_installer.config_gen import build_host_profile
from sertor_installer.install_wiki import build_install_plan, execute_plan
from sertor_installer.resources import read_asset_text


def _install(target: Path, **kwargs):
    profile = build_host_profile(target, **kwargs)
    plan = build_install_plan(AssistantId.COPILOT)
    return execute_plan(plan, profile, AssistantId.COPILOT)


# ---------------------------------------------------------------- US2: instruction block + commands

def test_instruction_block_in_copilot_instructions(tmp_path: Path):  # FR-008/009
    report = _install(tmp_path)
    assert report.exit_code() == 0
    instr = tmp_path / ".github" / "copilot-instructions.md"
    assert instr.is_file()
    text = instr.read_text(encoding="utf-8")
    assert "SERTOR:WIKI-RITUAL START" in text
    # no Claude instruction file written for copilot
    assert not (tmp_path / "CLAUDE.md").exists()


def test_instruction_block_idempotent(tmp_path: Path):  # FR-009
    _install(tmp_path)
    instr = tmp_path / ".github" / "copilot-instructions.md"
    before = instr.read_bytes()
    report2 = _install(tmp_path)
    assert report2.exit_code() == 0
    assert instr.read_bytes() == before  # block already present → untouched


def test_prompt_files_present_and_formed(tmp_path: Path):  # FR-010
    _install(tmp_path)
    wiki_prompt = tmp_path / ".github" / "prompts" / "wiki.prompt.md"
    skill_prompt = tmp_path / ".github" / "prompts" / "wiki-author.prompt.md"
    assert wiki_prompt.is_file() and skill_prompt.is_file()
    head = wiki_prompt.read_text(encoding="utf-8")
    assert head.startswith("---")
    assert "mode: agent" in head.splitlines()[1]
    # no Claude commands/skills dirs for copilot
    assert not (tmp_path / ".claude").exists()


# ---------------------------------------------------------------- US3: agent + hooks

def test_custom_agent_present_and_formed(tmp_path: Path):  # FR-011
    _install(tmp_path)
    agent = tmp_path / ".github" / "agents" / "wiki-curator.agent.md"
    assert agent.is_file()
    text = agent.read_text(encoding="utf-8")
    assert text.startswith("---")
    assert "name: wiki-curator" in text


def test_hook_wiring_session_events(tmp_path: Path):  # FR-012
    _install(tmp_path)
    wiring = tmp_path / ".github" / "hooks" / "sertor-hooks.json"
    assert wiring.is_file()
    data = json.loads(wiring.read_text(encoding="utf-8"))
    assert "SessionStart" in data["hooks"]
    assert "Stop" in data["hooks"]


def test_hook_script_reused_identically(tmp_path: Path):  # FR-014 / surface-mapping prop.3
    _install(tmp_path)
    copied = tmp_path / ".github" / "hooks" / "wiki-pending-check.ps1"
    assert copied.is_file()
    canonical = read_asset_text("claude/hooks/wiki-pending-check.ps1")
    assert copied.read_text(encoding="utf-8") == canonical


def test_wiki_scaffold_assistant_agnostic(tmp_path: Path):
    """CONFIG + STRUCTURE land in `wiki/` regardless of assistant."""
    _install(tmp_path)
    assert (tmp_path / "wiki" / "wiki.config.toml").is_file()
    assert (tmp_path / "wiki" / "index.md").is_file()


def test_double_run_idempotent(tmp_path: Path):  # FR-020
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
    assert report.assistant == "copilot"
    payload = json.loads(report.render_json())
    assert payload["assistant"] == "copilot"
