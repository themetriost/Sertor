"""Non-regression gate for the Claude target (FEAT-012, US5, FR-016, SC-005, C4.1/C4.2).

The VS Code consolidation must not change anything Claude produces. These tests exercise the real
install plans for `--assistant claude` (offline, `FakeCommandRunner`) and assert the historical
artifact layout: `.claude/**`, `CLAUDE.md`, `.mcp.json` (mcpServers). If any of these change, the
refactor regressed the default target — a hard block.
"""
from __future__ import annotations

import json
from pathlib import Path

from sertor_install_kit.assistant import AssistantId
from sertor_installer.config_gen import build_host_profile
from sertor_installer.install_rag import build_rag_plan, execute_rag_plan
from sertor_installer.install_wiki import build_install_plan, execute_plan
from sertor_installer.rag_profile import RagHostProfile, RagInstallOptions


def test_claude_wiki_artifacts_unchanged(tmp_path: Path):
    profile = build_host_profile(tmp_path)
    plan = build_install_plan(AssistantId.CLAUDE)
    report = execute_plan(plan, profile, AssistantId.CLAUDE)
    assert report.exit_code() == 0
    # historical Claude layout
    assert (tmp_path / "CLAUDE.md").is_file()
    assert (tmp_path / ".claude/commands/wiki.md").is_file()
    assert (tmp_path / ".claude/agents/wiki-curator.md").is_file()
    assert (tmp_path / ".claude/settings.json").is_file()
    # no Copilot containers for the default target
    assert not (tmp_path / ".github").exists()
    assert not (tmp_path / ".vscode").exists()
    assert report.notes == []


def test_claude_rag_artifacts_unchanged(tmp_path: Path, make_runner):
    options = RagInstallOptions(target_root=tmp_path, backend="azure", with_deps=False)
    profile = RagHostProfile.from_options(options)
    plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.CLAUDE)
    report = execute_rag_plan(plan, profile, make_runner(), AssistantId.CLAUDE)
    assert report.exit_code() == 0
    mcp = tmp_path / ".mcp.json"
    assert mcp.is_file()
    data = json.loads(mcp.read_text(encoding="utf-8"))
    assert "mcpServers" in data and "sertor-rag" in data["mcpServers"]
    # Claude routes the instruction block to CLAUDE.md and the hook under `.claude/`
    assert (tmp_path / "CLAUDE.md").is_file()
    assert (tmp_path / ".claude/hooks/sertor-rag-usage-check.ps1").is_file()
    assert not (tmp_path / ".github").exists()
    assert not (tmp_path / ".vscode").exists()
