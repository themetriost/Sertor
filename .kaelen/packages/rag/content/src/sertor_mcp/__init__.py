"""Sertor MCP server: exposes the core retrieval to an MCP client (e.g. Claude Code).

Thin layer over the core (Principio I): MCP tools call the `sertor_core` facade and reimplement
nothing. Provider/backend/corpus from the centralised configuration (`.env`,
Principio VIII/X). Startup: `python -m sertor_mcp.server` (normally launched by the MCP client).
"""
