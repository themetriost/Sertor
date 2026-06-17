"""Tests for `.mcp.json` merge: creation, preservation, idempotence, malformed (kit ConfigError)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sertor_install_kit.artifacts import Outcome
from sertor_install_kit.errors import ConfigError
from sertor_install_kit.mcp_merge import merge_mcp, remove_mcp_server

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


# NB (FEAT-012): the VS Code `servers` root-key is no longer reachable from any profile (the VS
# Code target was removed). The `root_key` parameter of `merge_mcp` remains a generic kit primitive,
# so we keep coverage of its parametricity using a neutral, non-VS-Code root key.
def test_parametric_root_key_create(tmp_path: Path):
    """`merge_mcp` honors an arbitrary `root_key` (parametricity of the kit primitive)."""
    mcp = tmp_path / "custom" / "mcp.json"
    outcome, _ = merge_mcp(mcp, ENTRY, root_key="customRoot")
    assert outcome is Outcome.CREATED
    data = json.loads(mcp.read_text(encoding="utf-8"))
    assert "customRoot" in data and data["customRoot"]["sertor-rag"]["command"] == "uv"
    assert "mcpServers" not in data


def test_parametric_root_key_preserves_others(tmp_path: Path):
    mcp = tmp_path / "custom" / "mcp.json"
    mcp.parent.mkdir(parents=True)
    mcp.write_text(json.dumps({"customRoot": {"altro": {"command": "x"}}}), encoding="utf-8")
    outcome, _ = merge_mcp(mcp, ENTRY, root_key="customRoot")
    assert outcome is Outcome.MERGED
    data = json.loads(mcp.read_text(encoding="utf-8"))
    assert "altro" in data["customRoot"] and "sertor-rag" in data["customRoot"]


def test_parametric_root_key_idempotent(tmp_path: Path):
    mcp = tmp_path / "custom" / "mcp.json"
    merge_mcp(mcp, ENTRY, root_key="customRoot")
    outcome, _ = merge_mcp(mcp, ENTRY, root_key="customRoot")
    assert outcome is Outcome.SKIPPED


def test_parametric_root_key_malformed_raises(tmp_path: Path):
    mcp = tmp_path / "custom" / "mcp.json"
    mcp.parent.mkdir(parents=True)
    mcp.write_text("{nope", encoding="utf-8")
    with pytest.raises(ConfigError):
        merge_mcp(mcp, ENTRY, root_key="customRoot")


# --- feature 048: remove_mcp_server (T018) ------------------------------------------------------


def test_remove_mcp_server_keeps_others(tmp_path: Path):
    mcp = tmp_path / ".mcp.json"
    mcp.write_text(
        json.dumps({"mcpServers": {"altro": {"command": "x"}, "sertor-rag": ENTRY}}),
        encoding="utf-8",
    )
    outcome, _ = remove_mcp_server(mcp)
    assert outcome is Outcome.REMOVED
    data = json.loads(mcp.read_text(encoding="utf-8"))
    assert "altro" in data["mcpServers"]
    assert "sertor-rag" not in data["mcpServers"]


def test_remove_mcp_server_only_server_removes_file(tmp_path: Path):
    mcp = tmp_path / ".mcp.json"
    merge_mcp(mcp, ENTRY)  # file = {mcpServers: {sertor-rag}}
    outcome, detail = remove_mcp_server(mcp)
    assert outcome is Outcome.REMOVED
    assert detail == "file removed"
    assert not mcp.exists()


def test_remove_mcp_server_absent_skips(tmp_path: Path):
    mcp = tmp_path / ".mcp.json"
    mcp.write_text(json.dumps({"mcpServers": {"altro": {"command": "x"}}}), encoding="utf-8")
    outcome, _ = remove_mcp_server(mcp)
    assert outcome is Outcome.SKIPPED


def test_remove_mcp_server_missing_file_skips(tmp_path: Path):
    mcp = tmp_path / ".mcp.json"
    outcome, _ = remove_mcp_server(mcp)
    assert outcome is Outcome.SKIPPED


def test_remove_mcp_server_parametric_root_key(tmp_path: Path):
    mcp = tmp_path / "custom" / "mcp.json"
    mcp.parent.mkdir(parents=True)
    mcp.write_text(
        json.dumps({"customRoot": {"altro": {"command": "x"}, "sertor-rag": ENTRY}}),
        encoding="utf-8",
    )
    outcome, _ = remove_mcp_server(mcp, root_key="customRoot")
    assert outcome is Outcome.REMOVED
    data = json.loads(mcp.read_text(encoding="utf-8"))
    assert "altro" in data["customRoot"] and "sertor-rag" not in data["customRoot"]
