"""The MCP server exercised OVER THE PROTOCOL, by a real client (feature 128, FR-007/SC-004).

**Why this file exists, and why the other MCP tests do not replace it.** The unit tests call
the tool functions directly; that answers «does the function work?». A client asks another question
—
«does the server start, announce its tools, and what arrives when one fails?» — and the two answers
have already diverged once: a probe on the SDK's INTERNAL `call_tool` helper concluded the v2 port
had two regressions, while the protocol showed one. The helper changes return type between majors,
so comparing it measures the library, not the contract
(`wiki/concepts/misura-al-confine-pubblico.md`).

The server is launched as a PROCESS (`python -m sertor_mcp.server`) and driven with the SDK's own
client. That is also how Principio XI wants it exercised: through the vehicle, not by importing it.

Contract under test: `specs/128-porting-mcp-sdk-v2/contracts/tool-error-surface.md`.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest

mcp_client = pytest.importorskip("mcp.client.stdio", reason="the `mcp` extra is not installed")
from mcp import ClientSession, StdioServerParameters  # noqa: E402  (after importorskip)

_REPO_ROOT = Path(__file__).resolve().parents[2]

_EXPECTED_TOOLS = {
    "search_code", "search_docs", "search_combined",
    "find_symbol", "who_calls", "related_docs", "get_context",
    "memory_list", "memory_show", "memory_search",
}


def _field(obj, *names):
    """Read a field whose NAME differs between the SDK lines (camelCase → snake_case in 2.x)."""
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    raise AttributeError(f"none of {names} on {type(obj).__name__}")


def _server_params(cwd: Path | None = None, **env_overrides) -> StdioServerParameters:
    """Launch parameters for the server as a subprocess, with a scrubbed-but-working environment.

    `SERTOR_EMBED_PROVIDER=hash` keeps the startup warm-up offline: no GloVe download, no cloud key.

    ⚠️ **`cwd` is how a condition gets planted, and the reason is worth knowing.** `Settings.load`
    reads `.env` with `override=True`, so **the file beats the process environment**: a server
    launched from the repo root ignores `SERTOR_*` variables passed here whenever `.env` also sets
    them. Measured while writing this test — the first attempt «planted» a missing index and got a
    real result back from the repo's own index. To plant anything, run the server from a directory
    that has no `.env` (Principio XIII: the fixture plane must not silently borrow the product's
    configuration).
    """
    env = dict(os.environ)
    env.update({
        "SERTOR_EMBED_PROVIDER": "hash",
        "SERTOR_STORE_BACKEND": "local",
        "PYTHONPATH": str(_REPO_ROOT / "src"),
        "PYTHONIOENCODING": "utf-8",
    })
    env.update(env_overrides)
    return StdioServerParameters(
        command=sys.executable, args=["-m", "sertor_mcp.server"],
        env=env, cwd=str(cwd or _REPO_ROOT),
    )


def _run(coro):
    """Drive a coroutine from a synchronous test — the convention already used in this repo
    (`tests/unit/test_mcp_server.py` does the same with `asyncio.run`), so no async plugin becomes
    a dependency of the suite."""
    return asyncio.run(coro)


def test_handshake_and_the_ten_tools():
    """T009 — the server starts, completes the handshake, and announces its ten tools.

    This is SC-001 measured at the boundary: on a host where the import dies, this test cannot pass,
    whereas `doctor` stays green (E10-FEAT-072) and the CLI keeps working.
    """
    async def _body():
        async with mcp_client.stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                init = await session.initialize()

                info = _field(init, "server_info", "serverInfo")
                assert _field(info, "name") == "sertor-rag"
                assert init.instructions and "Sertor" in init.instructions, (
                    "the instructions travel to the client on both lines"
                )

                listed = await session.list_tools()
                names = {tool.name for tool in listed.tools}
                assert names == _EXPECTED_TOOLS, (
                    f"missing: {_EXPECTED_TOOLS - names} · unexpected: {names - _EXPECTED_TOOLS}"
                )

    _run(_body())

def test_list_returning_tool_delivers_structured_content():
    """T009 — a tool annotated `-> list[dict]` delivers `{"result": [...]}`, measured identical
    on both SDK lines. (The five tools annotated `-> dict` deliver `None` there on BOTH lines —
    our own design limit, tracked as E10-FEAT-076, deliberately not asserted here.)
    """
    async def _body():
        async with mcp_client.stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("search_code", {"query": "retrieval", "k": 2})

                assert _field(result, "is_error", "isError") is False
                structured = _field(result, "structured_content", "structuredContent")
                assert isinstance(structured, dict) and "result" in structured, (
                    f"expected a structured payload keyed by 'result', got {structured!r}"
                )
                assert isinstance(structured["result"], list)

    _run(_body())

def test_anticipated_failure_carries_its_diagnostic_to_the_client(tmp_path):
    """T017 — an ANTICIPATED failure reaches the client WITH its diagnosis (FR-004, SC-002).

    Choosing the condition took two attempts, and the reason belongs here because it is a property
    of the product, not of the test. A **missing index is NOT an error** for this server: the tools
    go through `build_facade()`, i.e. the TOLERANT core, which returns `[]` plus a `no_index`
    warning by deliberate policy — and that holds whatever `SERTOR_ENGINE` says, because the strict
    behaviour lives in the baseline ENGINE, which the server does not use. (Measured: the first
    version of this test planted a missing index under `baseline` and got `results=0`, not a raise.)

    The deterministic anticipated failure is a **missing code-graph**: `find_symbol` says so in its
    own docstring — «explicit error = graph not built» — and raises `GraphNotFoundError`, a
    `SertorError`. No network, no credentials, no fixture to build.

    What must NOT happen is the client receiving only «Error executing tool find_symbol»: true, and
    useless — an agent cannot suggest the remedy, and will fall back to reading files by hand, which
    is what the affected nodes did for 34 and 36 days.

    The server runs from an empty directory on purpose: `.env` is read with `override=True` and
    would otherwise beat the planted variables (see `_server_params`).
    """
    async def _body():
        params = _server_params(
            cwd=tmp_path,                      # no `.env` here: see `_server_params`
            SERTOR_CORPUS="corpus-assente",    # no index and, above all, no code-graph here
        )
        async with mcp_client.stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("find_symbol", {"name": "qualunque"})

                assert _field(result, "is_error", "isError") is True, (
                    "a missing code-graph is an ANTICIPATED failure and must surface as an error"
                )
                text = " ".join(
                    str(getattr(block, "text", "")) for block in (result.content or [])
                )
                assert "graph" in text.lower(), (
                    "the error content must NAME the cause, not just the tool. Got: " f"{text!r}"
                )
                assert "find_symbol" in text, "the failing tool must still be identified"
                assert len(text) > len("Error executing tool find_symbol") + 10, (
                    "the diagnosis was swallowed: the client got only the generic message, "
                    "which is exactly the regression this feature exists to prevent"
                )

    _run(_body())
