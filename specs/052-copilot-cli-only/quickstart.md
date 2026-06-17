# Quickstart — Verifica del consolidamento Copilot CLI-only (FEAT-012)

**Branch**: `052-copilot-cli-only`. Verifiche offline (nessun client Copilot reale, NFR-05). Comandi in
**PowerShell** dalla root del repo. `uv run pytest` gira con `RAG_BACKEND=local`, marker `not cloud`.

## 0. Suite di test (gate)

```powershell
uv run pytest packages/sertor-install-kit packages/sertor packages/sertor-flow -m "not cloud"
uv run ruff check packages/
```

Atteso: verde. Nessun test cita più `AssistantId.COPILOT` (VS Code).

## 1. US1 — un solo valore Copilot, errore esplicito sul legacy

```powershell
# legacy `copilot` rifiutato, nomina copilot-cli (exit 1 sertor; exit 2 sertor-flow/argparse)
uv run sertor install rag --assistant copilot --target .            # -> error: ... copilot-cli ...
uv run sertor-flow install --assistant copilot --target .           # -> argparse: invalid choice
# valore corretto accettato
uv run sertor install rag --assistant copilot-cli --no-deps --target <tmp>
```

Verifica (in `<tmp>`): esiste `.mcp.json` (root `mcpServers`), **non** esiste `.vscode/mcp.json`,
**nessun** `.github/prompts/*.prompt.md` nostro.

## 2. US2 — naming uniforme

```powershell
uv run sertor install rag --help        | Select-String "assistant"   # claude | copilot-cli
uv run sertor-flow install --help       | Select-String "assistant"   # {claude,copilot-cli}
uv run sertor upgrade --help            | Select-String "assistant"
uv run sertor-flow uninstall --help     | Select-String "assistant"
```

Atteso: ovunque `claude|copilot-cli`, mai `copilot` (VS Code).

## 3. US3 — skill `requirements` come custom-agent su CLI

```powershell
# (con specify mockato nei test; manualmente serve uvx+spec-kit)
uv run pytest packages/sertor-flow/tests/test_install_governance_copilot.py -k copilot_cli
```

Verifica: `.github/agents/requirements.agent.md` presente; `.github/prompts/requirements.prompt.md`
assente; body == canonico Claude (anti-drift).

## 4. US4 — mapping upstream `--ai copilot`

```powershell
uv run pytest packages/sertor-flow/tests/ -k "specify_command or expected_layout or copilot_cli"
```

Verifica: `build_specify_command` con `copilot-cli` contiene `--ai copilot`; secondo run di
`launch_speckit` ritorna `SKIPPED` (idempotenza preservata, chiave `_EXPECTED_LAYOUT["copilot-cli"]`).

## 5. US5 — non-regressione Claude

```powershell
uv run sertor install rag --assistant claude --no-deps --target <tmpA>
# confronto con un albero di riferimento pre-refactor (stessi path/contenuti)
uv run pytest packages/sertor packages/sertor-flow -k claude
```

Atteso: artefatti Claude identici; test Claude verdi senza modifiche di logica.

## 6. US6/US7 — documentazione

Ispeziona `docs/install-copilot.md` (un solo percorso `copilot-cli` + nota di migrazione),
`docs/install.md` e `packages/sertor/docs/install.md` (valori `claude|copilot-cli`, nessuna riga VS Code).

## Criteri di accettazione coperti

SC-001..SC-010 (vedi `contracts/assistant-cli.md` per le clausole verificabili 1:1).
