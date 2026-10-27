"""Compatibility layer over the two supported MCP SDK lines.

**Why this exists.** The MCP SDK published **2.0.0 on 2026-07-28**, a major rework that REMOVED
`mcp.server.fastmcp` — the module this server was built on. A host that resolved its dependencies
after that date got the new major, and the server died at import: not «some tools missing», but
**no tools at all**, while `sertor-rag doctor` stayed green. Reported from the field by three
federation nodes; two of them ran without MCP for over a month.

Both lines are supported on purpose. A ceiling alone (`mcp<2`, shipped 2026-08-07) only protects
installations that resolve AFTER it: a host whose lock already froze the new major stays broken
until it re-resolves, and a host pinned to a published version cannot re-resolve at all. Supporting
both lines heals every population by updating `sertor-core` alone.

**This module is the ONLY place that knows two lines exist.** `server.py` must not name either of
them — `tests/unit/test_sdk_compat.py` asserts that, because a layer that gets bypassed is worse
than no layer: it looks like protection and is not.

**When the next major arrives.** The dependency ceiling is deliberately narrow — pinned to the
minor we actually measured — so raising it is a decision, not a default. E10-FEAT-071 is the guard
meant to notice a release above the ceiling; until it exists, the ceiling is watched by human
memory alone, and *a ceiling without a reminder is a deadline nobody reads*.

**When the 1.x line is dropped.** Delete this module and import from the SDK directly in
`server.py`. Nothing else has to change: no caller inspects `SDK_LINE`, and the two imported
objects are used through the SDK's own interface.
"""
from __future__ import annotations

# Kept private: the contract of this layer is three public names, and a fourth would invite
# consumers to reason about versions — which is exactly what `server.py` must not do.
_SUPPORTED_RANGE = ">=1.2,<2.3"

try:
    # Line 2.x: `FastMCP` became `MCPServer` and `mcp.server.fastmcp` was removed.
    from mcp.server import MCPServer as ServerClass
    from mcp.server.mcpserver.exceptions import ToolError

    SDK_LINE = "v2"
except ImportError:
    try:
        # Line 1.x: the line most existing hosts still have in their lock.
        from mcp.server.fastmcp import FastMCP as ServerClass
        from mcp.server.fastmcp.exceptions import ToolError

        SDK_LINE = "v1"
    except ImportError as exc:
        # Neither line. Say WHICH version is installed and WHAT is supported: the original
        # failure reached hosts as `No module named 'mcp.server.fastmcp'`, which names an
        # internal submodule and leaves the reader with no action to take.
        from importlib.metadata import PackageNotFoundError, version

        try:
            _installed = version("mcp")
        except PackageNotFoundError:  # pragma: no cover - the extra is declared, so this is rare
            _installed = "not installed"
        raise ImportError(
            "the installed MCP SDK exposes neither `mcp.server.MCPServer` (line 2.x) nor "
            f"`mcp.server.fastmcp.FastMCP` (line 1.x). Installed mcp: {_installed}; "
            f"supported: mcp{_SUPPORTED_RANGE}. Install a supported version, for example "
            f"`uv pip install 'mcp{_SUPPORTED_RANGE}'`."
        ) from exc

__all__ = ["SDK_LINE", "ServerClass", "ToolError"]
