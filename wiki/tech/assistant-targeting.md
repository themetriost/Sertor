---
title: Targeting per-assistente (AssistantProfile / Surface)
type: tech
tags: [installer, sertor-install-kit, copilot, claude, host-agnostico, principio-x, feat-007]
created: 2026-06-15
updated: 2026-06-15
sources: ["packages/sertor-install-kit/src/sertor_install_kit/assistant.py", "packages/sertor/src/sertor_installer/install_wiki.py", "packages/sertor/src/sertor_installer/install_rag.py", "specs/044-distribuzione-copilot/plan.md", "requirements/sertor-cli/distribuzione-copilot/requirements.md"]
---

# Targeting per-assistente — `AssistantProfile` / `Surface`

Il **seam** che rende l'installer di Sertor capace di depositare le proprie superfici **per più
assistenti** (Claude Code, GitHub Copilot) mantenendo la **parità funzionale**. Introdotto da
**FEAT-007** (feature 044, [[sertor-installer]]) e collocato nel **`sertor-install-kit`** così da essere
**riusato da `sertor-flow`/FEAT-009**. È l'estensione operativa del **Principio X** ([[constitution]])
all'**assistente ospite**: l'assistente si **configura**, non si presume nel corpo dei plan-builder.

## Le tre entità

- **`AssistantId`** (enum): l'assistente target — `claude` (default documentato), `copilot`. Valore
  ignoto → `ConfigError` esplicito (Principio IV). `codex` = futuro (Could).
- **`Surface`** (enum): la **categoria logica** di artefatto distribuibile, indipendente
  dall'assistente — `INSTRUCTION_BLOCK`, `MCP_SERVER`, `COMMAND`, `AGENT`, `HOOK`. È il **perno della
  parità**: ogni Surface ha una resa per ciascun assistente.
- **`AssistantProfile`** (value object frozen): per un `AssistantId`, risolve **dove/come** ogni
  `Surface` si materializza — contenitore (path relativo validato), `WriteStrategy`, e `root_key` per
  l'MCP. È l'**unico** posto che conosce le convenzioni per-assistente.

## La mappa (data-model §3)

| Surface | `claude` | `copilot` |
|---|---|---|
| `INSTRUCTION_BLOCK` | `CLAUDE.md` (marker) | `.github/copilot-instructions.md` (marker) |
| `MCP_SERVER` | `.mcp.json` (`mcpServers`) | `.vscode/mcp.json` (`servers`) |
| `COMMAND` | `.claude/commands/*.md`, `.claude/skills/*` | `.github/prompts/*.prompt.md` |
| `AGENT` | `.claude/agents/*.md` | `.github/agents/*.agent.md` |
| `HOOK` | `.claude/settings.json` | `.github/hooks/sertor-hooks.json` |

I plan-builder `build_install_plan`/`build_rag_plan` ([[sertor-installer]]) sono **parametrici**:
chiedono i target al profilo invece di cablare `.claude/...`. `--assistant claude` resta byte-identico
al comportamento storico (non-regressione).

## Decisione di design — DA-2 «ibrido»

**Riuso del CONTENUTO + traduzione del CONTENITORE**, da **fonte unica**. Non si punta Copilot agli
asset `.claude` (riuso puro: fragile su Preview e incapace di coprire prompt-file/agent/MCP), né si
mantiene una doppia copia a mano (traduzione pura: deriva). Invece:
- il **contenuto** (testo del blocco, entry MCP, corpo comando, persona agente, **script hook**) ha una
  sola fonte;
- la forma Copilot è **resa** a install-time (`surfaces.py`: prompt-file e custom-agent generati dal
  contenuto Claude) con una **guardia anti-drift** che fallisce sulla divergenza (REQ-021);
- gli **script** degli hook (`.ps1`) sono **riusati identici** tra assistenti; varia solo il wiring.

Si riusano le `ArtifactKind` esistenti ([[sertor-install-kit]]): `MARKER_BLOCK` su
`copilot-instructions.md`, `SETTINGS_MERGE` sul JSON `.github/hooks/*`, `MCP_MERGE` con **`root_key`
parametrico** (`mcpServers`↔`servers`, retro-compatibile). Nessuna nuova `ArtifactKind`.

## Invarianti

install ≠ run · non distruttivo · idempotente · **CLI di esecuzione assistant-agnostic** (`sertor-rag`/
`sertor-wiki-tools` non hanno varianti per-assistente) · segreti mai versionati · **gap dichiarati** nel
report (mai omissione silenziosa, FR-016).

## Grounding Copilot (giugno 2026)

Copilot (VS Code agent mode) ha gli **stessi 8 eventi hook** di Claude (`SessionStart`/`Stop`/
`PreToolUse`/…), custom-agent `.agent.md`, prompt-file, MCP `.vscode/mcp.json`, e legge nativamente
`.claude/settings.json`/`CLAUDE.md` — il che rende la parità realizzabile (e ha smentito l'assunzione
obsoleta «Copilot niente hook»).

## Relazioni

Vive nel [[sertor-install-kit]], consumato da [[sertor-installer]] (FEAT-007) e — prossimamente — dalla
governance `sertor-flow` (FEAT-009, dove SpecKit sarà ottenuto **lanciando l'installer di spec-kit**,
non vendorato). Embodiment del Principio X ([[constitution]]). Explainer: [[sertor-con-copilot]].
