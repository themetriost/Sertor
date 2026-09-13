"""The compatibility layer over the two MCP SDK lines (E10-FEAT-070, feature 128).

Contract under test: `specs/128-porting-mcp-sdk-v2/contracts/sdk-compat.md` — three exported names
and one invariant on `server.py`. These tests run on WHICHEVER line the environment resolved, which
is the point: CI runs them twice (once per line, R-5/D-3), and `test_sdk_line_matches_the_class`
is what makes the second run a measure instead of a green no-op.
"""
from __future__ import annotations

import builtins
import importlib
from pathlib import Path

import pytest

from sertor_mcp import _sdk

_SERVER_SOURCE = Path(__file__).resolve().parents[2] / "src" / "sertor_mcp" / "server.py"


def test_the_three_contract_names_are_usable():
    """T006 — the layer exports a constructible server class, a raisable error, and a line."""
    server = _sdk.ServerClass("probe", instructions="x")
    assert hasattr(server, "tool") and hasattr(server, "run")

    with pytest.raises(_sdk.ToolError, match="anticipated"):
        raise _sdk.ToolError("an anticipated failure")

    assert _sdk.SDK_LINE in {"v1", "v2"}


def test_sdk_line_matches_the_class():
    """T006a — `SDK_LINE` is DERIVED from the import that won, not declared beside it.

    Read the truth from the class actually obtained (its module) and compare. This is the test that
    keeps the CI step which installs the OTHER line from being green and vacuous: if the step did
    not really change line, this fails instead of quietly agreeing.
    """
    module = _sdk.ServerClass.__module__
    expected = "v2" if "mcpserver" in module else "v1"
    assert _sdk.SDK_LINE == expected, (
        f"SDK_LINE says {_sdk.SDK_LINE!r} but the server class comes from {module!r} — "
        "the value is declared somewhere instead of derived (Principio XIV)"
    )
    # The error class must come from the SAME line: mixing them would compile and then misbehave.
    assert ("mcpserver" in _sdk.ToolError.__module__) == (expected == "v2")


def test_import_failure_names_the_version_and_the_range(monkeypatch):
    """T006b — with neither line importable, the message is ACTIONABLE (FR-003).

    The original defect reached hosts as `No module named 'mcp.server.fastmcp'`: true, and useless.
    """
    real_import = builtins.__import__

    def _no_mcp_server(name, *args, **kwargs):
        if name.startswith("mcp.server"):
            raise ImportError(f"simulated: no {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _no_mcp_server)
    with pytest.raises(ImportError) as excinfo:
        importlib.reload(_sdk)

    message = str(excinfo.value)
    assert "mcp.server.MCPServer" in message and "fastmcp" in message, (
        "the message must name BOTH lines it looked for"
    )
    assert ">=1.2,<2.3" in message, "the message must name the supported range"
    assert "Installed mcp:" in message, "the message must name what IS installed"

    # Leave the module in its real state for the rest of the session.
    monkeypatch.undo()
    importlib.reload(_sdk)


def test_server_module_never_names_a_specific_line():
    """T006c — the invariant that says whether the layer is doing its job, or was bypassed.

    A compatibility layer that the consumer walks around is worse than none: it looks like
    protection. Checked on the source text, because that is where a future edit would reintroduce
    the coupling.
    """
    source = _SERVER_SOURCE.read_text(encoding="utf-8")
    offenders = [
        line.strip()
        for line in source.splitlines()
        if ("fastmcp" in line or "mcpserver" in line) and not line.lstrip().startswith("#")
    ]
    assert not offenders, (
        "server.py names a specific SDK line; it must go through `._sdk` instead: " f"{offenders}"
    )
