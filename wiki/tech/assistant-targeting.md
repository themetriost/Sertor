---
title: Targeting per-assistente (AssistantProfile / Surface)
type: tech
tags: [installer, sertor-install-kit, copilot, copilot-cli, claude, host-agnostico, principio-x, feat-007]
created: 2026-06-15
updated: 2026-07-11
sources: ["packages/sertor-install-kit/src/sertor_install_kit/assistant.py", "packages/sertor/src/sertor_installer/install_wiki.py", "packages/sertor/src/sertor_installer/install_rag.py", "specs/044-distribuzione-copilot/plan.md", "requirements/sertor-cli/distribuzione-copilot/requirements.md"]
---

# Targeting per-assistente — `AssistantProfile` / `Surface`

Il **seam** che rende l'installer di Sertor capace di depositare le proprie superfici **per più
assistenti** (Claude Code, GitHub Copilot) mantenendo la **parità funzionale**. Introdotto da
**FEAT-007** (feature 044, [[sertor-installer]]) e collocato nel **`sertor-install-kit`** così da essere
**riusato da `sertor-flow`/FEAT-009**. È l'estensione operativa del **Principio X** ([[constitution]])
all'**assistente ospite**: l'assistente si **configura**, non si presume nel corpo dei plan-builder.

## Le tre entità

- **`AssistantId`** (enum): l'assistente target — oggi **due valori**: `claude` (default documentato) e
  `copilot-cli` (Copilot CLI). Valore ignoto → `ConfigError` esplicito (Principio IV). *(Il target
  `copilot` VS Code, presente nella storia sotto, è stato **consolidato in `copilot-cli`** — FEAT-012;
  `codex` = futuro, Could.)*
- **`Surface`** (enum): la **categoria logica** di artefatto distribuibile, indipendente
  dall'assistente — `INSTRUCTION_BLOCK`, `MCP_SERVER`, `COMMAND`, `AGENT`, `HOOK`. È il **perno della
  parità**: ogni Surface ha una resa per ciascun assistente.
- **`AssistantProfile`** (value object frozen): per un `AssistantId`, risolve **dove/come** ogni
  `Surface` si materializza — contenitore (path relativo validato), `WriteStrategy`, e `root_key` per
  l'MCP. È l'**unico** posto che conosce le convenzioni per-assistente.

## La mappa (data-model §3)

| Surface | `claude` | `copilot` (VS Code) | `copilot-cli` |
|---|---|---|---|
| `INSTRUCTION_BLOCK` | `CLAUDE.md` (marker) | `.github/copilot-instructions.md` | `.github/copilot-instructions.md` |
| `MCP_SERVER` | `.mcp.json` (`mcpServers`) | `.vscode/mcp.json` (`servers`) | `.mcp.json` (`mcpServers`) |
| `COMMAND` | `.claude/commands/*.md`, `.claude/skills/*` | `.github/prompts/*.prompt.md` | `.github/prompts/*.prompt.md` |
| `AGENT` | `.claude/agents/*.md` | `.github/agents/*.agent.md` | `.github/agents/*.agent.md` |
| `HOOK` | `.claude/settings.json` | `.github/hooks/sertor-hooks.json` | `.github/hooks/sertor-hooks.json` |

> **Perché due target Copilot (feature 046, PR #66).** La **Copilot CLI** ha **rimosso** il supporto a
> `.vscode/mcp.json` (root `servers`) e legge l'MCP da `.mcp.json` (cwd→git root) con root `mcpServers`
> — il **formato Claude**. Da qui un terzo `AssistantId` `copilot-cli`: **unica differenza** dal target
> `copilot` è il contenitore `MCP_SERVER` (`.mcp.json`/`mcpServers` invece di `.vscode/mcp.json`/
> `servers`); tutte le altre Surface riusano i contenitori `.github/**` (che la CLI legge). Nel codice
> `install_rag`/`install_wiki` instradano la **famiglia Copilot** (VS Code + CLI) sulle superfici
> `.github/**`; `_apply_mcp` deriva il `root_key` dal target. **Ambito:** solo pacchetto `sertor`;
> `sertor-flow` resta `claude|copilot` (supporto SpecKit alla CLI = follow-up).

I plan-builder `build_install_plan`/`build_rag_plan` ([[sertor-installer]]) sono **parametrici**:
chiedono i target al profilo invece di cablare `.claude/...`. `--assistant claude` resta byte-identico
al comportamento storico (non-regressione).

## De-binarizzazione del seam — `select_for` (A-19, 2026-07-11)

Il profilo era l'unico posto che *conosce* le convenzioni, ma alcuni **plan-builder** sceglievano ancora
un valore/nome per-assistente con **ternari binari** `X if CLAUDE else Y` — che assumono *esattamente
due* assistenti e, con un terzo (Codex), cadrebbero in silenzio nel ramo `else`. A-19 li sostituisce con
un helper **n-ario e fail-loud** nel kit:

- **`select_for(assistant, {AssistantId: valore})`** (+ metodo `AssistantProfile.select(mapping)`):
  ogni scelta per-assistente è una **mappa totale** sugli assistenti supportati; una chiave mancante →
  **`ConfigError`** che nomina l'assistente (Principio IV/XII), mai un default silenzioso. Aggiungere un
  assistente = **aggiungere una chiave** (fail-loud se dimenticata).
- Siti convertiti: `_SERTOR_AUTHORED` (governance) da colonne `(claude_name, copilot_name)` →
  `dict[AssistantId, str]`; il concierge (`install_rag`); i target `.ps1` legacy e `owned_dirs`
  (`install_wiki`); l'enumerazione `(CLAUDE, COPILOT_CLI)` → `iter(AssistantId)` (`__main__`).
- **Parità by construction:** `select({CLAUDE:X, COPILOT_CLI:Y})[claude] = X`, identico al ternario →
  output installato byte-identico per i due assistenti (suite + test seam verdi).

> **Confine onesto (Principio III/YAGNI).** A-19 de-binarizza la **selezione di valori/nomi**, non i
> pochi guard *a singolo ramo* `if COPILOT_CLI:` che codificano un **comportamento strutturale**
> dell'assistente (generazione hook nativa, render custom-agent): astrarli senza conoscere le convenzioni
> di Codex sarebbe speculativo. Un terzo assistente sarà «un'aggiunta di dati» per nomi/target, ma dovrà
> comunque *decidere* il proprio comportamento a quei punti.

## Decisione di design — DA-2 «ibrido»

**Riuso del CONTENUTO + traduzione del CONTENITORE**, da **fonte unica**. Non si punta Copilot agli
asset `.claude` (riuso puro: fragile su Preview e incapace di coprire prompt-file/agent/MCP), né si
mantiene una doppia copia a mano (traduzione pura: deriva). Invece:
- il **contenuto** (testo del blocco, entry MCP, corpo comando, persona agente, **script hook**) ha una
  sola fonte;
- la forma Copilot è **resa** a install-time (`surfaces.py`: prompt-file e custom-agent generati dal
  contenuto Claude) con una **guardia anti-drift** che fallisce sulla divergenza (REQ-021);
- gli **script** degli hook (`.py` portabili, invocati via `uv run --no-project python` — A-09) sono **riusati identici** tra assistenti; varia solo il wiring.

Si riusano le `ArtifactKind` esistenti ([[sertor-install-kit]]): `MARKER_BLOCK` su
`copilot-instructions.md`, `SETTINGS_MERGE` sul JSON `.github/hooks/*`, `MCP_MERGE` con **`root_key`
parametrico** (`mcpServers`↔`servers`, retro-compatibile). Nessuna nuova `ArtifactKind`.

## Invarianti

install ≠ run · non distruttivo · idempotente · **CLI di esecuzione assistant-agnostic** (`sertor-rag`/
`sertor-wiki-tools` non hanno varianti per-assistente) · segreti mai versionati · **gap dichiarati** nel
report (mai omissione silenziosa, FR-016).

## Grounding Copilot (giugno 2026)

Copilot (VS Code agent mode) ha gli **stessi 8 eventi hook** di Claude (`SessionStart`/`Stop`/
`PreToolUse`/…), custom-agent `.agent.md`, prompt-file, MCP `.vscode/mcp.json` — il che rende la parità
realizzabile (e ha smentito l'assunzione obsoleta «Copilot niente hook»).

## Hardening compatibilità (FEAT-011, giugno 2026)

Un audit di dogfooding (Copilot CLI 1.0.63) ha mostrato che la «parità piena» dichiarata era **falsa**: i
primi installer FEAT-007/009 depositavano artefatti in **formato Claude** non conformi allo schema Copilot
(hook JSON senza `version:1` → **scartati in silenzio**; output `.ps1` con `systemMessage` Claude-only;
SessionStart con stringhe nude; comandi solo-prompt-file non invocabili da CLI; frontmatter `mode:` invece
di `agent:`; `model:` Claude nei custom-agent). FEAT-011 corregge **tradicendo nativamente il contenitore**:

- gli hook Copilot sono **generati nativamente** da `render_copilot_hooks`/`HookEntrySpec` nel kit
  (`version:1`, voci piatte, `timeoutSec`, nessun campo Claude-only); gli asset statici sono rimossi;
- gli script (oggi `.py`) rendono l'output **nativo per assistente** via `--assistant copilot` (agentStop
  `{decision:"allow",reason}`, sessionEnd su stderr, **mai dual-field**); preToolUse resta **fail-open**;
- il **COMMAND** su `copilot-cli` è un **custom-agent** (`.github/agents/*.agent.md`, l'unica forma
  invocabile da CLI) via il nuovo `command_vehicle` del profilo; su VS Code resta prompt-file (`agent:`);
- SessionStart è **per-famiglia**: VS Code `type:"command"`→`{additionalContext}` (**[ASSUNTO-VSC]**, gap
  dichiarato nelle `InstallReport.notes`, mai «parità piena»); CLI `type:"prompt"` statico;
- una **suite di validità-schema offline** (gruppo G) avrebbe preso ognuno dei bug dell'audit.

Le superfici sono **validate dallo schema (offline)**; la conferma runtime su client reale resta fuori
ambito di prodotto → i claim di parità VS Code sono **gap dichiarati**, non «pieni».

## Parità by construction (FEAT-001, feature 056)

Il seam traduce il **contenitore**, ma **riusa il body verbatim** (anti-drift). Questo riuso è
un'arma a doppio taglio: un path `.claude/...` o un comando `/wiki` lasciati **dentro il body**
**trapelano** sull'host Copilot, dove non risolvono. Un audit di dogfooding (Copilot CLI 1.0.63) ha
mostrato che la capacità wiki era **rotta** lì: (1) il **payload multi-file** della skill
`wiki-author` (`wiki-playbook.md`, `ops/*.md`, `*-craft.md`) **non veniva depositato**; (2) i body
citavano `.claude/...` e `/wiki`, inesistenti su quell'host. La guardia byte-identica non lo vedeva:
verifica che il body **non forki**, non i suoi riferimenti interni.

> **Revisione (meccanismo NATIVO).** Una prima correzione depositava la skill come custom-agent + un
> container dedicato `.github/sertor/wiki-author/` + placeholder `{SKILL_DIR}`. Letta la doc ufficiale
> Copilot (agent skills native, auto-discovery **per-cartella-skill**), questa era una reinvenzione: la
> via corretta è il **meccanismo nativo**.

La regola che chiude il buco è **host-agnosticità alla sorgente** + **deposito nativo per host**:

- **Body host-agnostici.** Niente path d'assistente letterali, niente slash-command come
  invocazione, niente nomi di assistente né `$ARGUMENTS` nei body LLM-facing; il payload si
  referenzia con **path relativi co-locati** (`wiki-playbook.md`, `ops/<x>.md`, `../wiki-craft.md`).
  Poiché i container sono **paralleli** (`.claude/skills/wiki-author/` ↔ `.github/skills/wiki-author/`),
  gli stessi riferimenti relativi risolvono identici su entrambi gli host.
- **Skill nativa per host.** La capacità wiki è una **agent-skill nativa** depositata dove ciascun host
  la cerca — `.claude/skills/wiki-author/**` su Claude, `.github/skills/wiki-author/**` su Copilot — e
  auto-scoperta dal client (tutti i file della cartella, incl. `ops/`). Su Copilot la skill **assorbe il
  ruolo del command `/wiki`** (la CLI non ha slash-command custom): il suo `SKILL.md` è il **dispatcher**
  delle 8 operazioni, reso dalla fonte unica `commands/wiki.md`; il payload (playbook/ops/craft) è
  byte-copiato via `iter_asset_dir` — **nessun nuovo `ArtifactKind`**, nessun render skill→custom-agent.
  `wiki-curator` resta un custom-agent (`.github/agents/wiki-curator.agent.md`). Tutto dichiarato in
  `sertor_owned_paths` come owned_dir (uninstall/upgrade in blocco).

**Enforcement = guardia di parità** (`packages/sertor/tests/test_assets_copilot_parity.py`): rende i
piani Copilot (wiki + governance + rag) — e quello Claude per la closure — e fallisce su un body che
reintroduce `.claude/`, uno slash-command, un nome di assistente, **oppure** che cita un file del
payload **non depositato** (*closure dei riferimenti*). Un riferimento dangling fa fallisce nominando
il file: un agente «rotto in silenzio» (playbook mancante) diventa un **fallimento esplicito** del
test (Principio IV). La regola è codificata in tre sedi: questa pagina, la sezione *Host-agnostic
authoring* del [[wiki-playbook]], e la **Definition of Done** del blocco rituale distribuito.

## Default model-policy per-agente (Copilot CLI, FEAT-015)

**Meccanismo:** i 5 agenti Sertor-authored (concierge, configuration-manager, requirements-analyst,
requirements, wiki-curator) ricevono un campo `model:` nel frontmatter del custom-agent `.agent.md`,
**centralizzato e versionato** nel kit (`model_policy.py`). Risolve la richiesta del 2026-06-30
([[copilot-default-models]], elaborata in PR #135).

**Fonte unica versionata** (`packages/sertor-install-kit/src/sertor_install_kit/model_policy.py`):
- Costante `MODEL_POLICY_VERSION = "1.0.0"` (indipendente dalla versione Sertor)
- Mappa agente→modello: concierge/configuration-manager → `claude-haiku-4.5` (dispatcher, basso carico);
  requirements-analyst/requirements/wiki-curator → `claude-sonnet-4.6` (reasoning + sintesi)
- Funzione `resolve_model(agent_name, policy_version)` fail-loud su agente fuori ambito → zero
  deposito parziale (Principio IV), niente silent config-mismatch
- Importata da **entrambi** i pacchetti (`sertor` + `sertor-flow`) → niente drift, niente dipendenza
  cross-pacchetto

**Integrazione plan-builder:** `render_custom_agent(…, model: str | None)` riceve il modello dal
profilo/policy e lo scrive nel frontmatter YAML di Copilot CLI. Path Claude byte-identico (niente
echo dell'alias). Fail-loud install-time se il profilo Copilot CLI non copre un agente atteso.

**Guardie riconciliate:** le guardie di test distinguono alias Claude **nudo** (`haiku`/`sonnet`/`opus`,
**assente**, cattivo) dal campo `model:` **di policy** (`claude-haiku-4.5`, **presente**, buono). Parsing
YAML-aware (chiave `model:`, non substring, poiché `claude-haiku-4.5` contiene `haiku`).

**Finding di verifica:** il meccanismo config `subagents.agents.<name>.model` di Copilot CLI è
runtime settings, NON un meccanismo di repository. La doc ufficiale GitHub stabilisce che il modello
di un custom-agent Copilot CLI si configura mediante il campo `model:` nel frontmatter `.agent.md`
e (secondariamente) via user settings machine-global `~/.copilot/settings.json`. Il default nel
frontmatter è **al sicuro dagli upgrade per costruzione** perché il file `settings.json` dell'utente
può sempre sovrascrittere a runtime.

**Scope out dichiarato:** gli agenti vendorati di spec-kit (`speckit.*`: specify/clarify/plan/…)
rimangono fuori ambito → follow-up FEAT-016 (Could), post-verifica supporto `model:` sui prompt-file.

Record completo: [[feat-083-default-model-policy-copilot]].

## Relazioni

Vive nel [[sertor-install-kit]], consumato da [[sertor-installer]] (FEAT-007) **e da** [[sertor-flow]]
(FEAT-009, PR #65: il renderer è stato spostato qui nel kit per condividerlo; lì SpecKit è ottenuto
**lanciando l'installer di spec-kit**, non vendorato). Embodiment del Principio X ([[constitution]]).
Explainer: [[sertor-con-copilot]].
