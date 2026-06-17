"""Acceptance tests for `install rag --assistant copilot-cli`.

The GitHub Copilot CLI does NOT read VS Code's `.vscode/mcp.json` (`servers` root key); it reads
`.mcp.json` (cwd → git root) with the `mcpServers` root. This target writes the MCP config where the
CLI looks, while reusing the `.github/**` host-facing surfaces (instruction block + anti-bypass
hook), which the CLI also reads. Host simulated in `tmp_path`, `FakeCommandRunner` (no network/uv).
"""
from __future__ import annotations

import json
from pathlib import Path

from sertor_install_kit.assistant import AssistantId
from sertor_installer.install_rag import build_rag_plan, execute_rag_plan
from sertor_installer.rag_profile import RagHostProfile, RagInstallOptions
from sertor_installer.resources import read_asset_text


def _run(target: Path, runner, **opts):
    options = RagInstallOptions(target_root=target, **opts)
    profile = RagHostProfile.from_options(options)
    plan = build_rag_plan(
        profile, with_deps=options.with_deps, mcp_scope=options.mcp_scope,
        assistant=AssistantId.COPILOT_CLI,
    )
    return execute_rag_plan(plan, profile, runner, AssistantId.COPILOT_CLI), profile


# ---------------------------------------------------------------- MCP in the CLI-readable file

def test_mcp_in_dot_mcp_json_mcpservers_key(tmp_path: Path, make_runner):
    runner = make_runner()
    report, _ = _run(tmp_path, runner, backend="azure", with_deps=False, corpus="myapp")
    assert report.exit_code() == 0
    mcp = tmp_path / ".mcp.json"
    assert mcp.is_file()
    data = json.loads(mcp.read_text(encoding="utf-8"))
    assert "mcpServers" in data and "sertor-rag" in data["mcpServers"]
    assert "servers" not in data  # NOT the VS Code root key the CLI rejects
    assert not (tmp_path / ".vscode" / "mcp.json").exists()  # not the VS Code file
    assert "myapp" in mcp.read_text(encoding="utf-8")


def test_secrets_empty_in_env(tmp_path: Path, make_runner):  # FR-006 (ported from VS Code suite)
    runner = make_runner()
    _run(tmp_path, runner, backend="azure", with_deps=False)
    env = (tmp_path / ".sertor" / ".env").read_text(encoding="utf-8")
    # template ships empty secret values (compiled in .env, never versioned)
    assert "AZURE_OPENAI_API_KEY=\n" in env or "AZURE_OPENAI_API_KEY=" in env


def test_install_never_indexes(tmp_path: Path, make_runner):
    runner = make_runner()
    _run(tmp_path, runner, backend="azure")
    calls = [cmd for cmd, _ in runner.calls]
    assert all("index" not in cmd and "search" not in cmd for cmd in calls)


def test_idempotent_rerun(tmp_path: Path, make_runner):
    runner = make_runner()
    _run(tmp_path, runner, backend="azure", with_deps=False)
    report2, _ = _run(tmp_path, runner, backend="azure", with_deps=False)
    assert report2.exit_code() == 0
    assert report2.created == 0
    assert all(o.outcome.value in ("skipped", "merged") for o in report2.outcomes)


def test_non_destructive_on_existing_dot_mcp(tmp_path: Path, make_runner):
    mcp = tmp_path / ".mcp.json"
    mcp.write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}}), encoding="utf-8")
    runner = make_runner()
    _run(tmp_path, runner, backend="azure", with_deps=False)
    data = json.loads(mcp.read_text(encoding="utf-8"))
    assert "other" in data["mcpServers"] and "sertor-rag" in data["mcpServers"]


# ---------------------------------------------------------------- reused .github/** surfaces

def test_hook_wiring_in_github(tmp_path: Path, make_runner):
    runner = make_runner()
    _run(tmp_path, runner, backend="azure", with_deps=False)
    wiring = tmp_path / ".github" / "hooks" / "sertor-hooks.json"
    assert wiring.is_file()
    data = json.loads(wiring.read_text(encoding="utf-8"))
    assert "PreToolUse" in data["hooks"]


def test_instruction_block_in_copilot_instructions(tmp_path: Path, make_runner):
    runner = make_runner()
    _run(tmp_path, runner, backend="azure", with_deps=False)
    instr = tmp_path / ".github" / "copilot-instructions.md"
    assert instr.is_file()
    assert "SERTOR:RAG-USAGE" in instr.read_text(encoding="utf-8")


def test_hook_script_byte_identical_to_claude(tmp_path: Path, make_runner):
    """The anti-bypass hook script is reused byte-for-byte from the canonical Claude asset
    (surface-map property 3, ported from the removed VS Code suite)."""
    runner = make_runner()
    _run(tmp_path, runner, backend="azure", with_deps=False)
    copied = tmp_path / ".github" / "hooks" / "sertor-rag-usage-check.ps1"
    assert copied.is_file()
    canonical = read_asset_text("rag/hooks/sertor-rag-usage-check.ps1")
    assert copied.read_text(encoding="utf-8") == canonical


def test_rag_wiring_is_native_copilot_schema(tmp_path: Path, make_runner):  # FR-017 (FEAT-011)
    """The PreToolUse wiring is native Copilot schema (version:1, flat entry, timeoutSec) —
    ported from the removed VS Code suite; the CLI target preserves the native schema."""
    runner = make_runner()
    _run(tmp_path, runner, backend="azure", with_deps=False)
    data = json.loads(
        (tmp_path / ".github/hooks/sertor-hooks.json").read_text(encoding="utf-8")
    )
    assert data["version"] == 1                                       # R1
    entry = data["hooks"]["PreToolUse"][0]
    assert "hooks" not in entry                                       # R2 flat
    assert "shell" not in entry and "statusMessage" not in entry      # R3
    assert "timeout" not in entry and entry["timeoutSec"] == 10       # R4
    assert entry["matcher"] == "Bash|Write|Edit|MultiEdit"            # PreToolUse matcher
    assert "-Assistant copilot" in entry["command"]                   # native output selector
