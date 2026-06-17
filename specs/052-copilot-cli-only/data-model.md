# Phase 1 — Data Model: consolidamento Copilot CLI-only (FEAT-012)

**Branch**: `052-copilot-cli-only` | **Spec**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

Questa feature è **sottrattiva**: rimuove un valore dal seam e semplifica i rami consumatori. **Non
introduce nuove entità**; modifica per *restrizione* le entità esistenti del seam `AssistantProfile`
(FEAT-044/011). Sotto, lo stato *post-refactor* delle entità interessate.

## §1. `AssistantId` (enum, kit) — RISTRETTO

`packages/sertor-install-kit/src/sertor_install_kit/assistant.py`

| Valore | Stato post-refactor |
|--------|---------------------|
| `CLAUDE = "claude"` | invariato |
| ~~`COPILOT = "copilot"`~~ | **RIMOSSO** (Q1=a, FR-004/REQ-004) |
| `COPILOT_CLI = "copilot-cli"` | invariato — **unico** target Copilot |

- **Invariante:** `set(AssistantId) == {CLAUDE, COPILOT_CLI}`.
- **`from_str("copilot")`** → `ConfigError` (cade nel `except ValueError`, riga 32-37) che elenca i
  validi `claude, copilot-cli` (FR-001/REQ-001/REQ-008, NFR-02). Nessuna logica nuova.
- **Verifica (test):** `from_str("copilot")` solleva; `from_str("copilot-cli") is COPILOT_CLI`.

## §2. `AssistantProfile.for_assistant` — DUE RAMI

| Ramo | Stato |
|------|-------|
| `CLAUDE` (riga 136-155) | invariato (non-regressione, FR-016/SC-005) |
| ~~`COPILOT`~~ (riga 156-176) | **ELIMINATO** (intero blocco) |
| `COPILOT_CLI` (riga 177-206) | invariato — MCP `.mcp.json`/`mcpServers`, COMMAND→`.github/agents/*.agent.md`, `command_vehicle=CUSTOM_AGENT` |
| `else` (riga 207) | irraggiungibile (entrambi i valori coperti); resta `raise ConfigError` difensivo |

- **Invariante (FR-008/REQ-008):** per `COPILOT_CLI`, `target_for(MCP_SERVER).target_rel == ".mcp.json"`
  e `.root_key == "mcpServers"`; le altre superfici su `.github/**`.

## §3. `CommandVehicle` + renderer — INVARIATI (chiarimento di scope)

- `CommandVehicle.PROMPT_FILE` / `CUSTOM_AGENT`: **restano entrambi** nell'enum (`assistant.py:53-64`).
  `PROMPT_FILE` è il default e il vehicle di Claude (`assistant.py:108`); non è VS-Code-specifico.
- `render_prompt_file` (`surfaces.py:41-51`): **resta** come primitiva esportata dal kit, ma **nessun
  plan-builder la richiama più** dopo la rimozione di COPILOT (Claude usa il byte-copy `.claude/**`).
  Conforme FR-003/FR-004 (prompt-file come *veicolo dei comandi* non più risolto per alcun target).
- `render_custom_agent` / `render_copilot_hooks` / `HookEntrySpec`: invariati (usati da `copilot-cli`).

## §4. Mapping upstream `_SPECKIT_AI_FLAG` (nuovo, sertor-flow) — VALUE MAP

`packages/sertor-flow/src/sertor_flow/speckit_launch.py`

| Chiave (nostro `--assistant`) | Valore (`--ai` upstream spec-kit 0.8.18) |
|---|---|
| `claude` | `claude` |
| `copilot-cli` | `copilot` |

- **Unico punto** che traduce verso `--ai` (FR-015/REQ-015, SC-006, R-02). Default difensivo:
  `_SPECKIT_AI_FLAG.get(assistant, assistant)`.

## §5. `_EXPECTED_LAYOUT` (sertor-flow) — CHIAVE RINOMINATA

| Chiave (nostro assistente) | Marker attesi (prodotti da spec-kit) | Stato |
|---|---|---|
| `claude` | `.claude/commands/speckit.specify.md`, `.specify/templates/plan-template.md` | invariato |
| ~~`copilot`~~ → **`copilot-cli`** | `.github/prompts/speckit.specify.prompt.md`, `.specify/templates/plan-template.md` | chiave rinominata; **path invariati** (spec-kit `--ai copilot` produce il layout Copilot) |

- **Invariante (FR-014/REQ-014/SC-007, R-04):** la chiave del dict è il *nostro* nome assistente; i path
  sono i marker che spec-kit produce per Copilot → `_layout_present` riconosce il re-run (idempotenza).

## §6. Superfici CLI (`--assistant` choices) — UNIFICATE

| Comando | choices/validazione post-refactor |
|---|---|
| `sertor install wiki|rag` | `--assistant` senza `choices`, validato da `from_str` → `{claude, copilot-cli}`; help aggiornato (no "(VS Code)") |
| `sertor upgrade|uninstall` | idem (help aggiornato) |
| `sertor configure` | invariato (non ha `--assistant`) |
| `sertor-flow install|upgrade|uninstall` | `choices=["claude","copilot-cli"]` (era `["claude","copilot"]`, Q4=a breaking) |

- **Invariante (FR-005/006/007, SC-001/002):** in 0 pacchetti `copilot` è un valore valido; passarlo →
  errore esplicito (exit 1 `sertor`/`sertor-flow`; argparse exit 2 dove c'è `choices`).

## Transizioni di stato

Non applicabile: nessuna entità con ciclo di vita. Il refactor è una restrizione statica del set di
valori e una semplificazione di branching. Le invarianti di *runtime* (idempotenza, non-distruttività)
sono preservate dai meccanismi esistenti (NFR-01/NFR-06).
