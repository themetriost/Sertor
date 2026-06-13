"""Additive merge of `.mcp.json` in the host root (FR-017/018, REQ-231/232).

Same pattern as `settings_merge.py`: absent → create with the `sertor-rag` server only; present →
add the server while preserving the others; already present → skip (never overwrites); malformed →
`ConfigError` (fail-fast, file not touched). `.mcp.json` lives in the **host root** (where MCP
clients look for it) and points to the runtime in `.sertor/` (`uv run --directory .sertor`).
"""
from __future__ import annotations

import json
from pathlib import Path

from sertor_core.domain.errors import ConfigError
from sertor_installer.artifacts import Outcome

_SERVER_NAME = "sertor-rag"


def merge_mcp(mcp_path: Path, server_entry: dict) -> tuple[Outcome, str]:
    """Adds the `sertor-rag` server to `.mcp.json` in an additive and idempotent manner."""
    if not mcp_path.exists():
        payload = {"mcpServers": {_SERVER_NAME: server_entry}}
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
        raise ConfigError(".mcp.json is not a JSON object", key=str(mcp_path))

    servers = existing.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        raise ConfigError(".mcp.json: 'mcpServers' is not an object", key=str(mcp_path))

    if _SERVER_NAME in servers:
        return Outcome.SKIPPED, f"server {_SERVER_NAME} already present"

    servers[_SERVER_NAME] = server_entry
    mcp_path.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return Outcome.MERGED, f"+server {_SERVER_NAME}"
