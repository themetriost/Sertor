# Requisiti — Unificazione degli ambienti (E10-FEAT-002)

> Epica: **`debito-tecnico`** (FEAT-002, Should). Intervento **mirato** (non SpecKit completo, per
> `epic.md:69`): repoint di config + dichiarazione extra + docs + guard test + rimozione del venv di
> troppo. Consegnato il **2026-06-18**.

## 1. Problema (perché)

Il repo aveva **due virtualenv con padroni diversi** che divergevano in silenzio:

- **`.venv`** — venv di default del workspace `uv`, popolato da `uv sync`; usato anche dal prototipo
  congelato (`prototype/tests/conftest.py`).
- **`.venv-core`** — costruito **a mano** con gli extra `mcp`/`graph`/`azure`, puntato dal server MCP
  in `.mcp.json` (`command: .venv-core/Scripts/python.exe`).

Lavorando si sincronizzava `.venv`; il server MCP restava su `.venv-core` che invecchiava → errori
`No module named …` (CLAUDE.md, regola standing MCP). Causa-radice: nessun comando di sync produceva
un venv unico **completo** (test + server + code-graph).

`.venv-grag` (prototipo, GraphRAG, vincolo `numpy<2`) è isolamento **voluto** → **fuori ambito**.

## 2. Requisiti (EARS)

- **REQ-1 (Ubiquitous):** esiste **un solo** venv di sviluppo, `.venv` (default del workspace `uv`).
- **REQ-2 (Ubiquitous):** `uv sync --all-packages --extra dev` produce un venv che fa girare test,
  lint, **server MCP** e **code-graph** — l'extra `dev` include `mcp` e `graph`.
- **REQ-3 (Optional):** dove serve il dogfood-su-Azure, si aggiunge `--extra azure` (extra pesante
  **opt-in**, non forzato su chi lavora local-first). Decisione utente: ibrido (Q1=A).
- **REQ-4 (Ubiquitous):** `.mcp.json` punta al venv canonico `.venv`, **mai** a un secondo venv
  costruito a mano.
- **REQ-5 (Unwanted):** se `.mcp.json` torna a puntare a `.venv-core`/venv non canonico, un **guard
  test** deve fallire (`tests/unit/test_single_venv_guard.py`, criterio **CS-3**).
- **REQ-6 (Ubiquitous):** la documentazione operativa (CLAUDE.md, README, `wiki/tech/mcp-server.md`)
  descrive un solo venv e il comando di sync corretto.

## 3. Fuori ambito

- `.venv-grag` del prototipo (isolamento deliberato).
- Gli **installer** (`sertor install rag`): creano un runtime **per-ospite** isolato in
  `<host>/.sertor/.venv` via `uv init`+`uv add` — **non** referenziano `.venv`/`.venv-core` → nessuna
  modifica necessaria (verificato: `install_rag.py`).
- E10-FEAT-001 (host-agnosticità asset) e E10-FEAT-003 (CI Linux): feature sorelle, separate.

## 4. Esito

Un solo `.venv`; `dev` superset (`+mcp +graph`), `azure` opt-in; `.mcp.json` ripuntato; guard test
verde; `.venv-core` eliminato (gitignored, locale). Verifiche: query dogfood live dal `.venv`, suite
**621 (root) + 282 (sertor) + 120 (sertor-flow) + 131 (kit)** verdi, ruff produzione pulito.
