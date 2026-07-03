"""Guardia: il server MCP del dogfood gira dal runtime installato `.sertor/` (E15-FEAT-001).

Storia dell'invariante:
- **E10-FEAT-002** (unificazione ambienti): l'MCP doveva girare dal `.venv` canonico del
  workspace, MAI da un secondo venv costruito a mano (il vecchio `.venv-core`), sorgente di
  divergenza silenziosa (uno stantio mentre l'altro veniva sincronizzato).
- **E15-FEAT-001** (fedeltà dogfood, 2026-07-03): il runtime dell'agente è stato spostato dal
  `.venv` *editable* del workspace al **runtime installato** `.sertor/` (progetto `uv` che
  installa `sertor-core` da `git=HEAD`), per eliminare l'ambiguità repo-source ↔ installato.
  Da qui `.mcp.json` invoca `uv run --project .sertor python -m sertor_mcp.server`.

Questo test fallisce se `.mcp.json` regredisce a un venv non canonico (il vecchio `.venv-core`)
o al `.venv` editable del workspace (l'ambiguità che E15 ha chiuso), invece del runtime
installato `.sertor/`.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_mcp_config_points_to_installed_runtime() -> None:
    server = json.loads((REPO_ROOT / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"][
        "sertor-rag"
    ]
    command = server["command"]
    args = [str(a).replace("\\", "/") for a in server.get("args", [])]
    invocation = " ".join([command, *args])

    assert ".venv-core" not in invocation, (
        "il server MCP non deve puntare a `.venv-core` (venv costruito a mano, sorgente di "
        "divergenza silenziosa storica): usa il runtime installato `.sertor/`"
    )
    # Post-E15-FEAT-001: il runtime dell'agente è l'installato `.sertor/`, invocato via
    # `uv run --project .sertor`, NON il `.venv` editable del workspace (ambiguità chiusa da E15).
    assert command == "uv", (
        f"atteso il server MCP invocato via `uv run --project .sertor` (runtime installato), "
        f"trovato command={command!r}"
    )
    assert args[:3] == ["run", "--project", ".sertor"], (
        f"atteso il server MCP sul runtime installato `.sertor/` (`uv run --project .sertor …`), "
        f"trovato args={args!r}"
    )
