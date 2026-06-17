"""Additive merge of an MCP config file (FR-017/018, REQ-231/232).

Same pattern as `settings_merge.py`: absent → create with the `sertor-rag` server only; present →
add the server while preserving the others; already present → skip (never overwrites); malformed →
`ConfigError` (fail-fast, file not touched).

For Claude this is `.mcp.json` in the **host root** with the servers under `mcpServers`; for Copilot
(feature 044) it is `.vscode/mcp.json` with the servers under `servers`. The **root-key** is
parametric (`root_key`, default `mcpServers` → retro-compat); both point to the runtime in
`.sertor/` (`uv run --directory .sertor`).
"""
from __future__ import annotations

import json
from pathlib import Path

from sertor_install_kit.artifacts import Outcome
from sertor_install_kit.errors import ConfigError

_SERVER_NAME = "sertor-rag"


def merge_mcp(
    mcp_path: Path, server_entry: dict, root_key: str = "mcpServers"
) -> tuple[Outcome, str]:
    """Adds the `sertor-rag` server to an MCP config in an additive and idempotent manner.

    `root_key` selects the JSON root that holds the servers map (`mcpServers` for Claude → default
    for retro-compat; `servers` for Copilot's `.vscode/mcp.json`).
    """
    if not mcp_path.exists():
        payload = {root_key: {_SERVER_NAME: server_entry}}
        mcp_path.parent.mkdir(parents=True, exist_ok=True)
        mcp_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        return Outcome.CREATED, f"server {_SERVER_NAME}"

    raw = mcp_path.read_text(encoding="utf-8")
    try:
        existing = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"malformed JSON at line {exc.lineno}: {exc.msg}", key=str(mcp_path)
        ) from exc
    if not isinstance(existing, dict):
        raise ConfigError(f"{mcp_path.name} is not a JSON object", key=str(mcp_path))

    servers = existing.setdefault(root_key, {})
    if not isinstance(servers, dict):
        raise ConfigError(f"{mcp_path.name}: '{root_key}' is not an object", key=str(mcp_path))

    if _SERVER_NAME in servers:
        return Outcome.SKIPPED, f"server {_SERVER_NAME} already present"

    servers[_SERVER_NAME] = server_entry
    mcp_path.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return Outcome.MERGED, f"+server {_SERVER_NAME}"


def remove_mcp_server(
    mcp_path: Path, server_name: str = _SERVER_NAME, root_key: str = "mcpServers"
) -> tuple[Outcome, str]:
    """Removes ONLY the named server from an MCP config — inverse of `merge_mcp`.

    Other servers are preserved. If `server_name` was the only server AND the file holds nothing but
    that servers map, the whole file is removed (`REMOVED`, FR-025). `root_key` is parametric
    (`mcpServers` for Claude, `servers` for Copilot's `.vscode/mcp.json`).

    - file absent / server not present → `(SKIPPED, "...")` (idempotency);
    - server removed, others remain → `(REMOVED, "-server <name>")`, file rewritten;
    - server removed, was the only key/server → file deleted → `(REMOVED, "file removed")`;
    - malformed JSON → `ConfigError` (file not touched), like the merge.
    """
    if not mcp_path.exists():
        return Outcome.SKIPPED, f"no server {server_name}"

    raw = mcp_path.read_text(encoding="utf-8")
    try:
        existing = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"malformed JSON at line {exc.lineno}: {exc.msg}", key=str(mcp_path)
        ) from exc
    if not isinstance(existing, dict):
        raise ConfigError(f"{mcp_path.name} is not a JSON object", key=str(mcp_path))

    servers = existing.get(root_key)
    if not isinstance(servers, dict) or server_name not in servers:
        return Outcome.SKIPPED, f"no server {server_name}"

    del servers[server_name]
    # If the file held only this servers map and it is now empty, the file existed only for the
    # Sertor server → remove it entirely (non-destructive: nothing else lived here).
    if not servers and set(existing.keys()) == {root_key}:
        mcp_path.unlink()
        return Outcome.REMOVED, "file removed"
    mcp_path.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return Outcome.REMOVED, f"-server {server_name}"
