"""Server MCP di Sertor: espone il retrieval del nucleo a un client MCP (es. Claude Code).

Layer sottile sul core (Principio I): i tool MCP chiamano la facade di `sertor_core`, non
reimplementano nulla. Provider/backend/corpus dalla configurazione centralizzata (`.env`,
Principio VIII/X). Avvio: `python -m sertor_mcp.server` (di norma lo lancia il client MCP).
"""
