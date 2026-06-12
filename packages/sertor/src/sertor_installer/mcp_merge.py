"""Merge additivo del `.mcp.json` in radice host (FR-017/018, REQ-231/232).

Pattern di `settings_merge.py`: assente → crea con il solo server `sertor-rag`; presente → aggiunge
il server preservando gli altri; già presente → skip (mai sovrascrive); malformato → `ConfigError`
(fail-fast, file non toccato). Il `.mcp.json` vive in **radice host** (dove i client MCP lo cercano)
e punta al runtime in `.sertor/` (`uv run --directory .sertor`).
"""
from __future__ import annotations

import json
from pathlib import Path

from sertor_core.domain.errors import ConfigError
from sertor_installer.artifacts import Outcome

_SERVER_NAME = "sertor-rag"


def merge_mcp(mcp_path: Path, server_entry: dict) -> tuple[Outcome, str]:
    """Aggiunge il server `sertor-rag` a `.mcp.json` in modo additivo e idempotente."""
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
            f"JSON malformato alla riga {exc.lineno}: {exc.msg}", key=str(mcp_path)
        ) from exc
    if not isinstance(existing, dict):
        raise ConfigError(".mcp.json non è un oggetto JSON", key=str(mcp_path))

    servers = existing.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        raise ConfigError(".mcp.json: 'mcpServers' non è un oggetto", key=str(mcp_path))

    if _SERVER_NAME in servers:
        return Outcome.SKIPPED, f"server {_SERVER_NAME} già presente"

    servers[_SERVER_NAME] = server_entry
    mcp_path.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return Outcome.MERGED, f"+server {_SERVER_NAME}"
