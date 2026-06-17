# Phase 1 — Data Model: Hardening compatibilità GitHub Copilot

**Feature**: `049-compatibilita-copilot` (FEAT-011, epica `sertor-cli`)
**Premessa**: questa feature **non introduce entità di dominio del core** (`sertor-core` invariato, NFR-3
della spec/Principio I). Le «entità» sono **estensioni del seam d'installazione** (`sertor-install-kit`) e
**contratti d'artefatto** (formati di file generati). Tutto stdlib-only, value-object frozen, additivo.

---

## 1. Entità esistenti riusate (invariate o estese)

### `AssistantId` (enum) — invariato
`claude` · `copilot` (VS Code) · `copilot-cli` (CLI). `assistant.py:21-26`. Nessun valore nuovo.

### `Surface` (enum) — invariato
`INSTRUCTION_BLOCK` · `MCP_SERVER` · `COMMAND` · `AGENT` · `HOOK`. `assistant.py:40-50`. Resta il perno
della parità: la novità è **come** `COMMAND` e `HOOK` si materializzano per `copilot-cli`, non un nuovo
membro.

### `AssistantProfile` (value object) — **esteso**
Risolve, per un `AssistantId`, il contenitore di ogni `Surface`. Estensioni:

| Campo / metodo | Oggi | Modifica FEAT-011 |
|---|---|---|
| `_command_dir` / `_command_suffix` (`copilot-cli`) | `.github/prompts` / `.prompt.md` | → `.github/agents` / `.agent.md` **per il veicolo CLI del COMMAND** (Q2=c, nodo #2a) |
| `command_vehicle` (nuovo, opzionale) | — | `PROMPT_FILE` (claude/copilot) · `CUSTOM_AGENT` (copilot-cli); rende esplicito il veicolo invece di dedurlo dal suffisso |
| `render_path(COMMAND, name)` | uguale per copilot/copilot-cli | diverge: copilot-cli → path custom-agent |

Invariante: `claude` **non cambia** (default, non-regressione FR-040). `copilot` (VS Code) mantiene il
prompt-file; può ricevere **anche** il custom-agent (FR-015 lo consente, non lo impone).

---

## 2. Entità/funzioni nuove o modificate nel renderer condiviso (`surfaces.py`, kit)

### `render_prompt_file(canonical_text)` — **modificato**
- **Era**: frontmatter `mode: agent` (`surfaces.py:46`).
- **Diventa**: frontmatter con chiave **`agent:`** (FR-016). Corpo byte-for-byte (FR-019, guard
  `test_assets_copilot_guard.py`). Valore della chiave fissato in §5.

### `render_custom_agent(canonical_text, *, include_model=False)` — **modificato**
- **Era**: itera `("name","description","tools","model")` → copia `model` (`surfaces.py:59`).
- **Diventa**: per i target Copilot **omette `model`** (FR-017, Q6=a). Campi preservati:
  `name`/`description`/`tools` (FR-018). Corpo byte-for-byte (FR-019).
- Parametro esplicito (`include_model` default `False`, oppure `allowed_fields`): rende l'omissione una
  decisione del chiamante, non un effetto collaterale; il target `claude` non usa questo renderer (mantiene
  il layout `.claude/`), quindi nessuna regressione Claude.

### `render_copilot_hooks(events) -> dict` — **nuova** (funzione pura, kit)
Genera il **wiring hook nativo Copilot** dal modello logico di eventi (sostituisce gli asset statici
`copilot/hooks/*.json` in formato Claude). Forma di output: vedi `contracts/copilot-hook-schema.md`.
Proprietà: pura/deterministica, stdlib-only, niente campi Claude-only, `timeoutSec` (non `timeout`).

### Modello logico dell'evento hook — `HookEntrySpec` (nuova, frozen) [interno al builder]
Rappresenta una voce hook **indipendente dall'assistente**, da cui si rende sia la forma Claude sia la forma
Copilot (anti-drift sul wiring, fonte unica):

```
HookEntrySpec:
  event: str            # nome logico: "SessionStart" | "Stop" | "SessionEnd" | "PreToolUse"
  type: str             # "command" | "prompt"  (prompt solo per SessionStart su copilot-cli)
  command: str          # comando/prompt da eseguire
  timeout_sec: int      # secondi
  matcher: str | None   # opzionale (PreToolUse): "Bash|Write|Edit|MultiEdit"
```
La resa Claude usa la struttura annidata + `shell`/`statusMessage`/`timeout`; la resa Copilot usa la forma
piatta + `timeoutSec`. Il modello logico è la fonte unica; le due rese sono funzioni pure.

---

## 3. Script hook condivisi — estensione del contratto d'invocazione

### `wiki-pending-check.ps1` — **modificato** (corpo condiviso, output nativo per assistente)
- **Era**: `param([ValidateSet('Stop','SessionEnd')]$Mode)`, output `{ systemMessage }` per entrambi.
- **Diventa**: `param([ValidateSet('Stop','SessionEnd')]$Mode, [ValidateSet('claude','copilot')]$Assistant='claude')`.
  Il **corpo logico** (delega a `sertor-wiki-tools scan`, contratto `wiki.scan/1`) è una sola fonte; la
  **resa output** diverge:
  - `claude` (default, non-regressione FR-040): `{ systemMessage = … }` su stdout.
  - `copilot` + `Mode=Stop` (→ evento `agentStop`): `{ decision = "allow"; reason = … }` (FR-007).
  - `copilot` + `Mode=SessionEnd` (→ `sessionEnd`): **nessun output su stdout** consumato; messaggio →
    `stderr` (FR-009). Exit 0.
  - Mai dual-field (FR-011/SC-008).

### `<wiki>-session-start.ps1` — **nuovo** (estratto dal comando inline)
Estrae il corpo oggi inline in `wiki.hooks.json:11` (calcolo del nome-partizione-log + direttiva di avvio).
- `param([ValidateSet('claude','copilot')]$Assistant='claude')`.
- `copilot` (VS Code): stdout `{ additionalContext = "<direttiva>" }` (nodo #1, [ASSUNTO-VSC]).
- `copilot-cli`: **non invoca questo script** — usa la voce hook `type:"prompt"` con la direttiva come
  prompt statico (nessun output JSON da emettere).
- `claude`: forma storica (oggi è inline; l'estrazione preserva il comportamento — direttiva su stdout,
  Claude la usa come `additionalContext` dell'evento SessionStart). Non-regressione.

### `sertor-rag-usage-check.ps1` (PreToolUse) — **modificato (minimo)**
Già fail-open su Claude (exit 0). Per Copilot l'evento `preToolUse` è **fail-closed** (audit 🔴): garantire
**exit 0 sempre**, anche su errore di parsing, e **nessun output spurio** che Copilot interpreti come
`deny` (FR-008/041, NFR-3). Aggiunge `-Assistant` solo se serve differenziare l'output; in caso di
violazione rilevata, la forma di warning per Copilot va sul canale che NON blocca (warning non bloccante →
exit 0, nessun `decision:"deny"`).

---

## 4. Wiring hook — strategia di scrittura del file Copilot

Il file `.github/hooks/sertor-hooks.json` è **solo-Sertor** (non è il `settings.json` dell'utente come per
Claude). Due opzioni di scrittura:

- **(P) Generalizzare `settings_merge`** (preferito, DRY): estendere `_inner_commands`
  (`settings_merge.py:18-25`) perché riconosca **anche** la forma piatta Copilot (`entry["command"]` oltre a
  `entry["hooks"][].command`) e operi il dedup-by-command su entrambe. Una sola strategia di merge,
  retrocompatibile col formato Claude. Mantiene `MERGE_DEDUP` e l'idempotenza esistente.
- **(Q) Scrittura idempotente dedicata** del file Copilot via `MERGE_JSON`/write-if-changed: più semplice ma
  introduce un secondo percorso di merge per gli hook.

**Decisione**: (P). Il merge resta unico (Principio III/VII), il formato del file generato è nativo Copilot
(`render_copilot_hooks`), e l'idempotenza/non-distruttività (FR-040, NFR-1) è preservata dal dedup-by-command
già esistente. Il dedup deve essere **schema-aware**: confronta i `command` indipendentemente dalla forma.

---

## 5. Forma degli artefatti generati (riepilogo per-target)

| Artefatto | `claude` | `copilot` (VS Code) | `copilot-cli` |
|---|---|---|---|
| Hook wiring | `.claude/settings.json` (annidato, `timeout`, `shell`, `statusMessage`) — INVARIATO | `.github/hooks/sertor-hooks.json` (`version:1`, piatto, `timeoutSec`) | idem `copilot` |
| SessionStart | inline/script → direttiva (Claude la usa come contesto) | `type:"command"` → `{additionalContext}` | `type:"prompt"` (direttiva come prompt) |
| Stop / agentStop | `{systemMessage}` | `{decision:"allow",reason}` | idem `copilot` |
| SessionEnd / sessionEnd | `{systemMessage}` | nessun stdout consumato; msg→stderr | idem `copilot` |
| PreToolUse | exit 0, fail-open | exit 0, fail-open, nessun output spurio | idem `copilot` |
| COMMAND (`/wiki`, `wiki-author`, `requirements`) | `.claude/commands/*.md`, `.claude/skills/*` | `.github/prompts/*.prompt.md` (`agent:`) [+ opz. custom-agent] | `.github/agents/*.agent.md` (custom-agent) |
| AGENT (`wiki-curator`, …) | `.claude/agents/*.md` | `.github/agents/*.agent.md` (no `model:`) | idem `copilot` |
| Prompt-file frontmatter | n/a | chiave `agent:` (non `mode:`) | n/a (su CLI sono custom-agent) |
| Custom-agent frontmatter | n/a | `name`/`description`/`tools`, **no** `model` | idem `copilot` |
| MCP | `.mcp.json`/`mcpServers` | `.vscode/mcp.json`/`servers` | `.mcp.json`/`mcpServers` (FR-020: evidenza documentata) |

> **Valore chiave `agent:`** — REQ-016/§4 dei requisiti indica `agent: 'agent'`. Il valore esatto (e se i
> comandi-skill richiedano un valore diverso) è un dettaglio d'implementazione fissato in `/speckit-tasks`
> sui file reali; l'**invariante** è: chiave `agent:`, mai `mode:`.

---

## 6. Invarianti del modello

- **Anti-drift sul CONTENUTO** (NFR-2): corpo di comandi/agenti/blocchi e corpo logico degli script = fonte
  unica; solo il contenitore/contratto è tradotto. Guard test (`test_assets_copilot_guard.py`) estesi ai
  nuovi renderer.
- **Non-regressione Claude** (FR-040/SC-010): `claude` è il default di ogni parametro nuovo (`-Assistant
  claude`, `include_model` n/a per Claude, COMMAND prompt/skill `.claude/**`); suite Claude resta verde.
- **Parità governance senza dipendenza dal core** (FR-042/SC-011): le modifiche al renderer condiviso valgono
  per `sertor-flow` riusando il kit; `sertor-flow` continua a NON importare `sertor-core`/`sertor`.
- **Nessuna nuova `ArtifactKind`**: si riusano `FILE` (render per-target), `SETTINGS_MERGE` (dedup
  schema-aware), `MARKER_BLOCK`, `MCP_MERGE`. (Coerente con FEAT-007.)
- **stdlib-only** nel kit (Principio I del kit): `json`, parsing frontmatter già esistente; nessuna nuova
  dipendenza.
