"""Live checks of MCP servers, only when the operator asks (specs/023 D-1, research R-3).

Each server is started as its installed definition says, from the host's root, over stdio; the
check performs the MCP initialisation handshake and asks for the tools, then stops the process,
whatever happened. It runs the producer's code: the outcome says so. It never prints the
environment it passes.
"""

from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import threading
import time
import tomllib
from pathlib import Path

from kaelen.host import jsonspan

PROTOCOL = "2025-06-18"
DEFAULT_TIMEOUT = 10.0


def definition(host: Path, path: str, name: str) -> dict | None:
    """The server's definition as the assistant reads it, from the installed shared file."""
    file = host / path
    if not file.is_file():
        return None
    text = file.read_bytes().decode("utf-8", errors="replace")
    if path.endswith(".toml"):
        try:
            return (tomllib.loads(text).get("mcp_servers") or {}).get(name)
        except tomllib.TOMLDecodeError:
            return None
    try:
        value = jsonspan.value_text(text, ["mcpServers", name])
    except Exception:
        value = None
    if value is None:
        try:
            value = json.dumps((json.loads(text).get("servers") or {}).get(name))
        except ValueError:
            return None
    try:
        out = json.loads(value)
    except (TypeError, ValueError):
        return None
    return out if isinstance(out, dict) else None


def _reader(stream, lines: queue.Queue) -> None:
    for line in iter(stream.readline, ""):
        lines.put(line)
    lines.put(None)


def _send(proc, message: dict) -> None:
    proc.stdin.write(json.dumps(message) + "\n")
    proc.stdin.flush()


def _await(proc, lines: queue.Queue, ident: int, deadline: float) -> dict:
    while True:
        left = deadline - time.monotonic()
        if left <= 0:
            raise TimeoutError
        try:
            line = lines.get(timeout=left)
        except queue.Empty as exc:
            raise TimeoutError from exc
        if line is None:
            raise EOFError
        try:
            message = json.loads(line)
        except ValueError:
            continue  # a server may log on stdout before it answers; only replies count
        if isinstance(message, dict) and message.get("id") == ident:
            return message


def check(host: Path, spec: dict, timeout: float = DEFAULT_TIMEOUT, which=shutil.which) -> dict:
    """{state, server, version, tools, cause}: state is running | failed | not-checked."""
    kind = spec.get("type") or ("http" if spec.get("url") else "stdio")
    if kind != "stdio":
        return {"state": "not-checked", "cause": f"transport {kind!r} is not checked live"}
    command = spec.get("command")
    if not isinstance(command, str) or not command:
        return {"state": "failed", "cause": "the definition has no command"}
    exe = which(command) or (str(host / command) if (host / command).is_file() else None)
    if exe is None:
        return {"state": "failed", "cause": f"command {command!r} not found"}
    args = [str(a) for a in spec.get("args") or []]
    env = dict(os.environ)
    env.update({str(k): str(v) for k, v in (spec.get("env") or {}).items()})
    try:
        proc = subprocess.Popen(
            [exe, *args],
            cwd=host,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        return {"state": "failed", "cause": f"cannot start: {exc.strerror or exc}"}
    lines: queue.Queue = queue.Queue()
    threading.Thread(target=_reader, args=(proc.stdout, lines), daemon=True).start()
    deadline = time.monotonic() + timeout
    try:
        _send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": PROTOCOL,
                    "capabilities": {},
                    "clientInfo": {"name": "kaelen-verify", "version": "1"},
                },
            },
        )
        reply = _await(proc, lines, 1, deadline)
        if "error" in reply:
            return {"state": "failed", "cause": f"initialize error: {reply['error']}"}
        result = reply.get("result") or {}
        info = result.get("serverInfo") or {}
        _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        _send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tools = _await(proc, lines, 2, deadline)
        if "error" in tools:
            return {"state": "failed", "cause": f"tools/list error: {tools['error']}"}
        return {
            "state": "running",
            "server": info.get("name"),
            "version": info.get("version"),
            "protocol": result.get("protocolVersion"),
            "tools": len((tools.get("result") or {}).get("tools") or []),
        }
    except TimeoutError:
        return {"state": "failed", "cause": f"no answer within {timeout:g} s"}
    except (EOFError, BrokenPipeError, OSError):
        return {"state": "failed", "cause": "exited before answering" + _tail(proc)}
    finally:
        _stop(proc)


def _tail(proc) -> str:
    try:
        proc.wait(timeout=1)
        err = (proc.stderr.read() or "").strip().splitlines()
    except Exception:
        return ""
    return f": {err[-1][:200]}" if err else ""


def _stop(proc) -> None:
    """Every process the check started is gone when it returns (REQ-008)."""
    for stream in (proc.stdin,):
        try:
            stream.close()
        except OSError:
            pass
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)
