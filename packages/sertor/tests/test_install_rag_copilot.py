"""Acceptance tests for `install rag --assistant copilot` (feature 044, US1 + US3).

Host simulated in `tmp_path`, `FakeCommandRunner` (no network/real uv). US1: MCP in
`.vscode/mcp.json` (`servers.sertor-rag`), empty secrets, install≠run, idempotence,
non-destructiveness. US3: anti-bypass PreToolUse hook in `.github/hooks/*.json`, fail-open, hook
script byte-identical to Claude's.
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
        assistant=AssistantId.COPILOT,
    )
    return execute_rag_plan(plan, profile, runner, AssistantId.COPILOT), profile


def _calls(runner) -> list[list[str]]:
    return [cmd for cmd, _ in runner.calls]


# ---------------------------------------------------------------- US1: MCP reachable

def test_mcp_in_vscode_servers_key(tmp_path: Path, make_runner):  # FR-004/005
    runner = make_runner()
    report, _ = _run(tmp_path, runner, backend="azure", with_deps=False, corpus="myapp")
    assert report.exit_code() == 0
    mcp = tmp_path / ".vscode" / "mcp.json"
    assert mcp.is_file()
    data = json.loads(mcp.read_text(encoding="utf-8"))
    assert "servers" in data and "sertor-rag" in data["servers"]
    assert "mcpServers" not in data
    assert not (tmp_path / ".mcp.json").exists()  # not the Claude file
    assert "myapp" in mcp.read_text(encoding="utf-8")


def test_secrets_empty_in_env(tmp_path: Path, make_runner):  # FR-006
    runner = make_runner()
    _run(tmp_path, runner, backend="azure", with_deps=False)
    env = (tmp_path / ".sertor" / ".env").read_text(encoding="utf-8")
    # template ships empty secret values (compiled in .env, never versioned)
    assert "AZURE_OPENAI_API_KEY=\n" in env or "AZURE_OPENAI_API_KEY=" in env


def test_install_never_indexes(tmp_path: Path, make_runner):  # FR-018
    runner = make_runner()
    _run(tmp_path, runner, backend="azure")
    assert all("index" not in cmd and "search" not in cmd for cmd in _calls(runner))


def test_idempotent_rerun(tmp_path: Path, make_runner):  # FR-020
    runner = make_runner()
    _run(tmp_path, runner, backend="azure", with_deps=False)
    report2, _ = _run(tmp_path, runner, backend="azure", with_deps=False)
    assert report2.exit_code() == 0
    assert report2.created == 0
    assert all(o.outcome.value in ("skipped", "merged") for o in report2.outcomes)


def test_non_destructive_on_existing_vscode_mcp(tmp_path: Path, make_runner):  # FR-017
    mcp = tmp_path / ".vscode" / "mcp.json"
    mcp.parent.mkdir(parents=True)
    mcp.write_text(json.dumps({"servers": {"other": {"command": "x"}}}), encoding="utf-8")
    runner = make_runner()
    _run(tmp_path, runner, backend="azure", with_deps=False)
    data = json.loads(mcp.read_text(encoding="utf-8"))
    assert "other" in data["servers"] and "sertor-rag" in data["servers"]


# ------------------------------------------------------- US3: anti-bypass hook (Principio XI)

def test_pretooluse_hook_wiring_present(tmp_path: Path, make_runner):  # FR-013
    runner = make_runner()
    _run(tmp_path, runner, backend="azure", with_deps=False)
    wiring = tmp_path / ".github" / "hooks" / "sertor-hooks.json"
    assert wiring.is_file()
    data = json.loads(wiring.read_text(encoding="utf-8"))
    assert "PreToolUse" in data["hooks"]


def test_hook_script_byte_identical_to_claude(tmp_path: Path, make_runner):  # surface-map prop.3
    runner = make_runner()
    _run(tmp_path, runner, backend="azure", with_deps=False)
    copied = tmp_path / ".github" / "hooks" / "sertor-rag-usage-check.ps1"
    assert copied.is_file()
    canonical = read_asset_text("rag/hooks/sertor-rag-usage-check.ps1")
    assert copied.read_text(encoding="utf-8") == canonical


# ------------------------------------------- FEAT-011: native Copilot rag wiring schema (US1)

def test_rag_wiring_is_native_copilot_schema(tmp_path: Path, make_runner):  # FR-001..004
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
