"""Test del merge `.mcp.json` (T015/T019): creazione, preservazione, idempotenza, malformato."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sertor_core.domain.errors import ConfigError
from sertor_installer.artifacts import Outcome
from sertor_installer.mcp_merge import merge_mcp

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
