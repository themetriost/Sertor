# Research — Distribuzione su GitHub Copilot (FEAT-007)

Phase 0. Risolve l'unica vera incognita di design (DA-2) e le scelte per-superficie. Ground: superfici
Copilot verificate il 2026-06-15 (doc VS Code / GitHub) + lettura del codice installer reale
(`install_wiki.py`, `install_rag.py`, `sertor_install_kit/artifacts.py`).

## Superfici Copilot (fatti verificati)

| Logica | Claude (oggi) | Copilot (nativo) | Note |
|---|---|---|---|
| Server MCP | `.mcp.json` (`mcpServers`) / `claude mcp add-json` | `.vscode/mcp.json` (chiave `servers`), workspace | committabile |
| Istruzioni sempre-attive | blocco a marker in `CLAUDE.md` | `.github/copilot-instructions.md` (+ `.github/instructions/*.instructions.md`) | Copilot legge **anche** `CLAUDE.md`/`AGENTS.md` |
| Comando/slash | `.claude/commands/*.md`, `.claude/skills/*/SKILL.md` | `.github/prompts/*.prompt.md` | nessun bridge auto da `.claude` |
| Agente / persona | `.claude/agents/*.md` | `.github/agents/*.agent.md` (frontmatter `tools`/`model`/`hooks`) | subagent ⇒ eventi `SubagentStart/Stop` |
| Hook | `.claude/settings.json` (`hooks`) | `.github/hooks/*.json`, **stessi 8 eventi** | Copilot carica **anche** `.claude/settings.json` |

## Decisione DA-2 — "riuso vs traduzione"

**Decisione: IBRIDO = riuso del CONTENUTO + traduzione del CONTENITORE/wiring, da fonte unica.**

- **Rationale.** Il puro **riuso** (puntare Copilot agli asset `.claude`) è respinto come strategia
  primaria: (1) dipende dalla compatibilità *Preview* "Copilot legge `.claude`", fragile da basarci la
  parità; (2) **non è idiomatico**; (3) soprattutto **non raggiunge la parità** — slash command (prompt
  file), custom agent e MCP **non** hanno un bridge automatico da `.claude`, quindi il riuso da solo li
  lascerebbe fuori. La pura **traduzione** è la base corretta, ma per gli **hook** il file
  `.github/hooks/*.json` referenzia *script shell* → si **riusa lo script** (`.ps1`/`.sh`, nessuna
  riscrittura) e si traduce solo il **wiring JSON**; per **MCP** si riusa l'**entry del server** e
  cambia solo contenitore/chiave. Quindi l'ottimo è: **tradurre il contenitore, riusare il contenuto**,
  da un'**unica fonte di verità** → idiomatico, indipendente dalla Preview, e a parità piena.

- **Alternative considerate.**
  - *(a) Riuso puro* — costo minimo ma parità impossibile (vedi sopra) e dipendente da Preview. ❌
  - *(b) Traduzione pura con doppia copia a mano* — raggiunge la parità ma viola l'anti-drift (due
    sorgenti divergenti). ❌ come forma; ✅ come esito se la copia è **generata/guardata** (vedi sotto).
  - *(c) Ibrido (scelto)* — fonte unica + reso per-assistente. ✅

## Sotto-decisioni per superficie (come si rende Copilot)

1. **MCP** → `.vscode/mcp.json`. **Estendere `mcp_merge`** con root-key parametrico (`mcpServers` →
   `servers`) e target parametrico. Riusa l'entry `rag/mcp.server.json.tmpl`. Idempotente/additivo come
   oggi. (FR-004/005; segreti vuoti, FR-006.)
2. **Istruzioni/rituale** → blocco a marker in `.github/copilot-instructions.md` via il **già esistente**
   `write_marker_block` (target+markers parametrici): stessi marker, stesso contenuto. Per il target
   Copilot si scrive **lì**, NON in `CLAUDE.md`, per evitare doppio-trigger col fatto che Copilot legge
   anche `CLAUDE.md` (edge case coesistenza). (FR-008/009.)
3. **Hook** → `.github/hooks/sertor-*.json` (eventi `SessionStart`/`Stop`/`PreToolUse` ⇒ identici).
   **Riuso degli script** `wiki-pending-check.ps1` / `sertor-rag-usage-check.ps1` (FILE, invariati);
   **traduzione del solo wiring** via `merge_settings` puntato sul file `.github/hooks/*.json` (è già un
   merge additivo di frammenti JSON su file arbitrario). Comportamento non bloccante/fail-open preservato
   (FR-013/014).
4. **Comandi/skill wiki** (`/wiki`, `wiki-author`) → `.github/prompts/*.prompt.md`. Reso da contenuto
   condiviso (corpo prosa riusato; frontmatter prompt-file generato). (FR-010.)
5. **Agente** `wiki-curator` → `.github/agents/wiki-curator.agent.md` (frontmatter `tools`/`model`).
   (FR-011.)

## Dove vive il targeting (architettura)

- **`AssistantProfile` nel `sertor-install-kit`** (stdlib): mappa ogni **Surface** logica →
  `(target_rel, contenitore/strategy)` per l'assistente scelto. I plan-builder `build_install_plan` /
  `build_rag_plan` chiedono i target al profilo invece di cablare `.claude/...`. **Condiviso con
  `sertor-flow`/FEAT-009** (REQ-017) → un solo meccanismo `--assistant`, niente divergenza.
- **CLI** `sertor install <cap> --assistant claude|copilot` (FR-001/002). **Default `claude`**
  (documentato): è l'assistente di prima classe storico; cambiarlo è una decisione di prodotto a parte.

## Anti-drift (REQ-021/FR-021)

Gli asset Copilot che non sono identici al contenuto Claude (frontmatter di prompt-file/custom-agent)
seguono il pattern già adottato per `.claude/` nel repo: **fonte canonica + test di guardia** che fa
fallire la build se le due forme divergono sul contenuto condiviso. Niente seconda copia "libera".

## Decisioni confermate (non più aperte per FEAT-007)

- **Client target = VS Code Copilot agent mode.** Copilot coding agent cloud = fuori taglio (Won't).
- **Selettore = `--assistant`**, default `claude`. Multi-target in un'unica esecuzione = non MVP.
- **Codex = fuori taglio** (Could d'epica).
- **DA-2 = ibrido** (sopra).
