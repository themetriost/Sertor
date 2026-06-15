"""Tests for `.mcp.json` merge: creation, preservation, idempotence, malformed (kit ConfigError)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sertor_install_kit.artifacts import Outcome
from sertor_install_kit.errors import ConfigError
from sertor_install_kit.mcp_merge import merge_mcp

ENTRY = {
    "command": "uv",
    "args": ["run", "--directory", ".sertor", "python", "-m", "sertor_mcp.server"],
    "env": {"SERTOR_CORPUS": "myapp"},
}


def test_create(tmp_path: Path):
    mcp = tmp_path / ".mcp.json"
    outcome, _ = merge_mcp(mcp, ENTRY)
    assert outcome is Outcome.CREATED
    data = json.loads(mcp.read_text(encoding="utf-8"))
    assert data["mcpServers"]["sertor-rag"]["command"] == "uv"


def test_preserve_other_servers(tmp_path: Path):
    mcp = tmp_path / ".mcp.json"
    mcp.write_text(json.dumps({"mcpServers": {"altro": {"command": "x"}}}), encoding="utf-8")
    outcome, _ = merge_mcp(mcp, ENTRY)
    assert outcome is Outcome.MERGED
    data = json.loads(mcp.read_text(encoding="utf-8"))
    assert "altro" in data["mcpServers"] and "sertor-rag" in data["mcpServers"]


def test_idempotent_skip(tmp_path: Path):
    mcp = tmp_path / ".mcp.json"
    merge_mcp(mcp, ENTRY)
    outcome, _ = merge_mcp(mcp, ENTRY)
    assert outcome is Outcome.SKIPPED


def test_malformed_raises(tmp_path: Path):
    mcp = tmp_path / ".mcp.json"
    mcp.write_text("{not json", encoding="utf-8")
    with pytest.raises(ConfigError):
        merge_mcp(mcp, ENTRY)


# ---------------------------------------------------------------- feature 044: parametric root_key

def test_default_root_key_is_mcpservers(tmp_path: Path):
    """Retro-compat: absent `root_key` keeps the historical `mcpServers` root."""
    mcp = tmp_path / ".mcp.json"
    merge_mcp(mcp, ENTRY)
    data = json.loads(mcp.read_text(encoding="utf-8"))
    assert "mcpServers" in data and "sertor-rag" in data["mcpServers"]


def test_copilot_servers_root_key_create(tmp_path: Path):
    """Copilot uses `servers` on `.vscode/mcp.json`."""
    mcp = tmp_path / ".vscode" / "mcp.json"
    outcome, _ = merge_mcp(mcp, ENTRY, root_key="servers")
    assert outcome is Outcome.CREATED
    data = json.loads(mcp.read_text(encoding="utf-8"))
    assert "servers" in data and data["servers"]["sertor-rag"]["command"] == "uv"
    assert "mcpServers" not in data


def test_servers_root_key_preserves_others(tmp_path: Path):
    mcp = tmp_path / ".vscode" / "mcp.json"
    mcp.parent.mkdir(parents=True)
    mcp.write_text(json.dumps({"servers": {"altro": {"command": "x"}}}), encoding="utf-8")
    outcome, _ = merge_mcp(mcp, ENTRY, root_key="servers")
    assert outcome is Outcome.MERGED
    data = json.loads(mcp.read_text(encoding="utf-8"))
    assert "altro" in data["servers"] and "sertor-rag" in data["servers"]


def test_servers_root_key_idempotent(tmp_path: Path):
    mcp = tmp_path / ".vscode" / "mcp.json"
    merge_mcp(mcp, ENTRY, root_key="servers")
    outcome, _ = merge_mcp(mcp, ENTRY, root_key="servers")
    assert outcome is Outcome.SKIPPED


def test_servers_root_key_malformed_raises(tmp_path: Path):
    mcp = tmp_path / ".vscode" / "mcp.json"
    mcp.parent.mkdir(parents=True)
    mcp.write_text("{nope", encoding="utf-8")
    with pytest.raises(ConfigError):
        merge_mcp(mcp, ENTRY, root_key="servers")
