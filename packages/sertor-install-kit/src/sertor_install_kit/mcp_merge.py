"""Additive merge of an MCP config file (FR-017/018, REQ-231/232).

Same pattern as `settings_merge.py`: absent → create with the `sertor-rag` server only; present →
add the server while preserving the others; already present → skip (never overwrites); malformed →
`ConfigError` (fail-fast, file not touched).

Both supported targets (Claude and the Copilot CLI) use `.mcp.json` in the **host root** with the
servers under `mcpServers`. The **root-key** is left parametric (`root_key`, default `mcpServers`)
so the primitive stays generic for other JSON roots; the server points to the runtime in `.sertor/`
(`uv run --project .sertor` — `--project` selects the environment WITHOUT moving the working
directory, which `--directory` would do, breaking corpus resolution).
"""
from __future__ import annotations

import json
from pathlib import Path

from sertor_install_kit.artifacts import Outcome
from sertor_install_kit.errors import ConfigError

_SERVER_NAME = "sertor-rag"


def reconcile_entry(previous: dict, shipped: dict) -> dict:
    """The entry a host SHOULD have: our invocation, the host's configuration.

    Splits the server entry into what the installer owns and what the host owns, because they fail
    in opposite directions. The **invocation** (`command`/`args`) is an asset: a wrong one makes the
    server read the wrong index, so upgrade must overwrite it. The **environment** (`SERTOR_CORPUS`)
    is the host's own choice, made at install time via `--corpus`: overwriting it points the server
    at a collection that does not exist — the very failure being repaired. Host values therefore
    win per key, exactly like the `.env` merge contract ("additive per-key, never overwrites your
    values"); shipped keys the host lacks are still added. Any extra key the host added survives.

    This distinction is not decoration: reconciling the whole entry wholesale was tried first and
    silently reset `SERTOR_CORPUS` to the directory name on every upgrade.
    """
    merged = dict(previous)
    for key, value in shipped.items():
        if key == "env" and isinstance(previous.get("env"), dict) and isinstance(value, dict):
            env = dict(value)
            env.update(previous["env"])  # the host's configured values win
            merged["env"] = env
        else:
            merged[key] = value
    return merged


def merge_mcp(
    mcp_path: Path, server_entry: dict, root_key: str = "mcpServers"
) -> tuple[Outcome, str]:
    """Adds the `sertor-rag` server to an MCP config in an additive and idempotent manner.

    `root_key` selects the JSON root that holds the servers map (`mcpServers` for both supported
    targets → default; left parametric so the primitive stays generic for other JSON roots).
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
        # E2-FEAT-022: distinguish "present and identical" from "present but DIFFERENT". Reporting
        # both as a bare `already present` is how a broken registration survives forever: on node
        # Kaelen a `.mcp.json` invoking the server with `uv run --directory .sertor` resolved the
        # index INSIDE the runtime directory, so every query returned `[]` — not an error, an
        # absence — for about a month, and each upgrade skipped the file that would have fixed it.
        # Install stays non-destructive (the host's file is NOT touched: it may be a deliberate
        # customization), but the divergence is now NAMED in the report instead of being silent
        # (Principio XII). `upgrade` is the verb that reconciles it → `update_mcp_server`.
        if servers[_SERVER_NAME] == reconcile_entry(servers[_SERVER_NAME], server_entry):
            return Outcome.SKIPPED, f"server {_SERVER_NAME} already present"
        return (
            Outcome.PRESENT_DIVERGENT,
            f"server {_SERVER_NAME} present but differs from the shipped entry — left intact; "
            f"run `sertor upgrade rag` to reconcile it",
        )

    servers[_SERVER_NAME] = server_entry
    mcp_path.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return Outcome.MERGED, f"+server {_SERVER_NAME}"


def update_mcp_server(
    mcp_path: Path, server_entry: dict, root_key: str = "mcpServers"
) -> tuple[Outcome, str]:
    """Reconciles the `sertor-rag` server BY CONTENT — the `upgrade` counterpart of `merge_mcp`.

    Mirrors the asymmetry already established for the instruction block (`write_marker_block` vs
    `update_marker_block`) and for files (`CREATE_IF_ABSENT` vs `update_file_if_changed`):
    install is non-destructive, upgrade replaces in place. Without this, a `.mcp.json` written by an
    older installer — or edited into a broken shape — is skipped by every subsequent upgrade, so the
    one mechanism meant to repair the host becomes the keeper of the broken version (E2-FEAT-022).

    Other servers are always preserved; only the `sertor-rag` entry is rewritten.

    Only the parts the installer owns are rewritten (`command`/`args`); the host's own configuration
    (`SERTOR_CORPUS` and any other `env` value) is preserved — see `reconcile_entry`.

    - file absent → create it (`CREATED`);
    - server absent → add it (`MERGED`);
    - server present and already reconciled → no-op (`SKIPPED`);
    - server present with a different invocation → rewrite in place (`UPDATED`);
    - malformed JSON → `ConfigError` (file not touched), as in the merge.
    """
    if not mcp_path.exists():
        return merge_mcp(mcp_path, server_entry, root_key)

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

    previous = servers.get(_SERVER_NAME)
    if previous is None:
        servers[_SERVER_NAME] = server_entry
        mcp_path.write_text(
            json.dumps(existing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        return Outcome.MERGED, f"+server {_SERVER_NAME}"

    reconciled = reconcile_entry(previous, server_entry)
    if previous == reconciled:
        return Outcome.SKIPPED, f"server {_SERVER_NAME} already current"

    servers[_SERVER_NAME] = reconciled
    mcp_path.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return Outcome.UPDATED, f"server {_SERVER_NAME} re-wired (was a different invocation)"


def remove_mcp_server(
    mcp_path: Path, server_name: str = _SERVER_NAME, root_key: str = "mcpServers"
) -> tuple[Outcome, str]:
    """Removes ONLY the named server from an MCP config — inverse of `merge_mcp`.

    Other servers are preserved. If `server_name` was the only server AND the file holds nothing but
    that servers map, the whole file is removed (`REMOVED`, FR-025). `root_key` is parametric
    (`mcpServers` for both supported targets → default; generic for other JSON roots).

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
