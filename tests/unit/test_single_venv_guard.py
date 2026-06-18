"""Guardia: un solo venv coerente (E10-FEAT-002, unificazione degli ambienti).

Il server MCP del dogfood deve girare dal venv canonico del workspace (`.venv`, il default di
`uv sync`), MAI da un secondo ambiente costruito a mano come il vecchio `.venv-core` — che era la
sorgente della divergenza silenziosa (uno stantio mentre l'altro veniva sincronizzato). Questo test
fallisce se `.mcp.json` torna a puntare a un venv non canonico.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_mcp_config_points_to_canonical_venv() -> None:
    mcp = json.loads((REPO_ROOT / ".mcp.json").read_text(encoding="utf-8"))
    command = mcp["mcpServers"]["sertor-rag"]["command"].replace("\\", "/")

    assert ".venv-core" not in command, (
        "il server MCP non deve puntare a `.venv-core` (venv costruito a mano, sorgente di "
        "divergenza silenziosa): usa il `.venv` unico del workspace"
    )
    assert command.startswith(".venv/"), (
        f"atteso il server MCP sul venv canonico `.venv/`, trovato: {command!r}"
    )
