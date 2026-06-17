# Phase 0 — Research: Hardening compatibilità GitHub Copilot dell'installer

**Feature**: `049-compatibilita-copilot` (FEAT-011, epica `sertor-cli`)
**Input**: `spec.md` (43 FR, 8 user story, 11 SC) · `requirements/sertor-cli/compatibilita-copilot/requirements.md`
**Scopo**: risolvere i 2 nodi di design lasciati aperti dalla spec (§*Nodi di design*) e dichiarare gli
assunti empirici; tutte le altre scelte (Q1–Q6) sono già decise e **non si riaprono**.

> **Ground truth dell'audit** (log `wiki/log/2026-06-17.md`, voce «Audit compatibilità Copilot», ospite
> Copilot CLI 1.0.63 + cross-check doc ufficiale GitHub): è la fonte primaria di questo research. Le
> citazioni «🔴/🟡/⚠️» sotto vengono da lì.

---

## 0. Inventario del codice reale (ancoraggio)

Le difformità della spec sono confermate leggendo gli asset/seam attuali:

| Difetto (audit) | Dove (path:lineno) | Stato corrente |
|---|---|---|
| Hook JSON in formato Claude | `packages/sertor/src/sertor_installer/assets/copilot/hooks/wiki.hooks.json:1-42`, `rag-usage.hooks.json:1-17` | `{"hooks":{<Evento>:[{"hooks":[{type,shell,timeout,statusMessage,command}]}]}}` — manca `version`, struttura annidata, campi Claude-only |
| Output `.ps1` Claude-only | `packages/sertor/src/sertor_installer/assets/claude/hooks/wiki-pending-check.ps1:64,71` | emette `{ systemMessage = … }` per Stop **e** SessionEnd; `param([ValidateSet('Stop','SessionEnd')]$Mode)` — nessun `-Assistant` |
| SessionStart plain-string | `wiki.hooks.json:11` (comando inline) | il comando inline emette stringhe nude (`'AVVIO SESSIONE …'`), nessun wrapper JSON |
| Comandi solo prompt-file | `install_wiki.py:158-203` (`_build_copilot_wiki_plan`), `install_governance.py:83-91` | `copilot` **e** `copilot-cli` ricevono lo STESSO piano (prompt-file); nessuna differenziazione per-target |
| Frontmatter prompt-file `mode:` | `packages/sertor-install-kit/src/sertor_install_kit/surfaces.py:46` | `render_prompt_file` scrive `mode: agent` |
| `model:` Claude copiato | `surfaces.py:59` | `render_custom_agent` itera su `("name","description","tools","model")` → copia `model` |
| Merge dedup struttura annidata | `packages/sertor-install-kit/src/sertor_install_kit/settings_merge.py:18-25` (`_inner_commands`) | `_inner_commands` legge `entry["hooks"][].command` — struttura Claude annidata; il formato piatto Copilot non ha `hooks[]` interno |
| Seam targeting | `assistant.py:138-181` | `copilot` e `copilot-cli` hanno identico `_command_dir=".github/prompts"`, `_command_suffix=".prompt.md"`; nessuna distinzione COMMAND prompt-file vs custom-agent |

Conferma operativa: i test Copilot esistenti (`test_install_wiki_copilot.py:46-55,69-83`) verificano la
**presenza** dell'asset (`mode: agent` atteso, `SessionStart` presente), **non** la sua validità-schema
Copilot — per questo non hanno preso i bug (audit: «Causa di fondo»).

---

## 1. Nodo di design #1 — Meccanismo nativo SessionStart su Copilot VS Code

### Problema
`type: "prompt"` (decisione Q1=b per CLI) è documentato **solo per Copilot CLI** sull'evento
`sessionStart`. Su Copilot VS Code (agent mode) il meccanismo nativo esatto di iniezione di contesto
all'avvio sessione **non è stato verificato sul campo** dall'utente (l'audit è stato condotto su CLI 1.0.63).
La spec lo marca esplicitamente come nodo da fissare «con verifica empirica» (US3 scenario 2, FR-006).

### Opzioni considerate
- **(O1) `additionalContext` via hook `command`** — la voce hook `sessionStart` invoca uno script che
  stampa `{"additionalContext": "<testo>"}` su stdout; Copilot lo parsa e lo inietta nel prompt. È la
  forma che la doc ufficiale Copilot cita per iniettare contesto da uno script di hook su `sessionStart`,
  e — secondo l'audit — è ciò che Copilot tenta di fare (`JSON.parse` sull'output, oggi fallisce sulle
  stringhe nude). Funziona per costruzione anche su CLI (l'output dello script è consumato uguale).
- **(O2) `type: "prompt"` anche su VS Code** — più pulito (nessuno script), ma l'audit lo dà come
  **CLI-only**; usarlo su VS Code è un comportamento **non documentato/non verificato** → vietato dal
  principio guida («NON inventare un comportamento non documentato»).

### Decisione
**Wiring SessionStart per-famiglia, entrambi nativi:**
- **Copilot CLI** → voce hook nativa **`type: "prompt"`** (Q1=b, già deciso, CLI-documentato).
- **Copilot VS Code** → voce hook nativa **`type: "command"`** che invoca uno script il cui output è
  **`{"additionalContext": "<testo>"}`** (O1).

Razionale: ogni target riceve la sua forma nativa (zero stringhe nude, zero campo «tollerato»), e si evita
il comportamento non documentato (O2). Il messaggio di avvio-sessione è lo **stesso contenuto** delle due
forme (anti-drift sul contenuto): è la direttiva «carica roadmap/index/log + mostra l'EXEC» che oggi vive
inline in `wiki.hooks.json:11`. Per non duplicare la logica di calcolo del nome-partizione-log, il corpo
inline viene estratto in uno **script SessionStart condiviso** parametrico (`-Assistant`), coerente con la
Story 4 (vedi §3).

### Assunto empirico dichiarato (NON ancora verificato dall'utente)
> **[ASSUNTO-VSC]** Copilot VS Code (agent mode) inietta contesto a `sessionStart` consumando lo **stdout
> JSON** `{"additionalContext": "..."}` dell'hook `command` (stessa semantica documentata per CLI). Questo
> assunto **deve essere confermato empiricamente** su un VS Code reale prima di dichiarare parità piena su
> quella superficie (FR-027). Finché non confermato, la superficie SessionStart-VS-Code è **dichiarata come
> gap non-verificato** nella surface-mapping e nell'output d'installazione (FR-028 / Story 8).
>
> **Fallback nativo più sicuro** se [ASSUNTO-VSC] fosse smentito: per VS Code, degradare l'avvio-sessione a
> una **direttiva statica nel blocco istruzioni** (`copilot-instructions.md`, già installato) che chiede
> all'agente di caricare il contesto di propria iniziativa — è nativo, non emette nulla da parsare, e non
> reintroduce stringhe nude. NON si ripiega mai su un campo tollerato/dual-field.

Conseguenza sull'ambito: la **verifica runtime su VS Code reale è validazione operativa, fuori ambito di
prodotto** (Assumptions della spec); ciò che è in ambito è (a) produrre la forma nativa, (b) testarla
offline contro lo schema atteso, (c) dichiararla come non-verificata finché lo è.

---

## 2. Nodo di design #2 — Revisione del seam `AssistantProfile`/`Surface`

### Problema
Oggi il seam (`assistant.py`, `surfaces.py`) (a) rende prompt-file per **entrambi** i target Copilot
(COMMAND identico), (b) copia `model:` in `render_custom_agent`, (c) non distingue il contratto di output
hook per assistente, (d) il renderer hook non esiste (il wiring Copilot è un asset statico in formato
Claude). Domanda: basta **estendere** il seam o serve una **revisione profonda** (autorizzata)?

### Analisi
Il seam ha già le fondamenta giuste: `AssistantId` distingue `copilot` da `copilot-cli`
(`assistant.py:21-26`), `Surface` è il perno della parità, `render_path` instrada i per-file surface, e
`SurfaceTarget` porta `strategy`/`root_key`. La divergenza CLI↔VS-Code è **già modellata** (target MCP
diverso). Quindi le quattro lacune sono **assenze di parametri/funzioni**, non un difetto strutturale.

### Decisione: **estensione mirata del seam, NON revisione profonda**

Quattro interventi additivi, tutti dentro il seam/renderer condiviso del kit (NFR-2/NFR-7, FR-043):

**(a) Piano comandi per-target — COMMAND a doppio veicolo (Q2=c).**
Il veicolo del COMMAND dipende dall'`AssistantId`: VS Code → prompt-file (`.github/prompts/*.prompt.md`);
CLI → custom-agent (`.github/agents/*.agent.md`). Realizzazione: il `AssistantProfile` di `copilot-cli`
espone il COMMAND con `_command_dir=".github/agents"` + `_command_suffix=".agent.md"` (oppure un campo
`command_vehicle: PROMPT_FILE|CUSTOM_AGENT`), e il plan-builder sceglie il renderer (`render_prompt_file`
vs `render_custom_agent`) in base al suffisso del target — pattern già usato in `_render_for_target`
(`install_wiki.py:211-223`, `install_governance.py:179-191`). VS Code (FR-015, Should) mantiene il
prompt-file; può ricevere **anche** il custom-agent (la spec lo consente: «su VS Code restano disponibili
anche come prompt-file»). Il piano `copilot-cli` smette di condividere `_build_copilot_wiki_plan` con
`copilot`: i due divergono nel veicolo COMMAND.

**(b) Omissione `model:` (Q6=a).**
`render_custom_agent` smette di includere `model` per i target Copilot. Forma scelta: parametro esplicito
`render_custom_agent(canonical_text, *, allowed_fields=…)` (o `drop_model: bool`) — il default per Copilot
**non** include `model`. Mantiene `name`/`description`/`tools` (FR-018) e corpo byte-for-byte (FR-019). È
una modifica al renderer condiviso → vale per `sertor` **e** `sertor-flow` (FR-042) da una fonte unica.

**(c) Output hook nativo per assistente (Q4=b).**
Lo script `.ps1` condiviso acquisisce `-Assistant claude|copilot` (default `claude` → non-regressione,
FR-040). Il corpo logico (delega alla CLI `sertor-wiki-tools scan`, mappatura del contratto `wiki.scan/1`)
resta **una fonte**; la **resa dell'output** diverge per assistente: Claude → `{ systemMessage }`; Copilot
→ per-evento (vedi `contracts/hook-output-contract.md`). Mai dual-field (FR-011). Se un evento non si
riesce a rendere pulito da uno script parametrico (FR-012), si ammette una **variante per-assistente**; in
questa feature il parametro basta.

**(d) Renderer hook JSON nativo Copilot.**
Il wiring Copilot smette di essere un **asset statico** in formato Claude e diventa **generato** dal seam
nel formato nativo Copilot (`{"version":1,"hooks":{<evento>:[entry piatta]}}`,
`type/command/timeoutSec/[matcher]`, niente `shell`/`statusMessage`). Realizzazione: una funzione pura nel
kit `render_copilot_hooks(events) -> dict` (o un `HookContract` per-assistente) che il plan-builder usa
quando l'`AssistantId` è Copilot. Il merge dedup (`settings_merge.py`) va **generalizzato** per riconoscere
sia la forma annidata Claude (`entry["hooks"][].command`) sia la forma piatta Copilot (`entry["command"]`)
— estensione di `_inner_commands`, retrocompatibile. In alternativa, dato che il wiring Copilot è un file
**solo-Sertor** (non un `settings.json` utente condiviso come Claude), si può usare `MERGE_JSON`/scrittura
idempotente del file `sertor-hooks.json`; la scelta finale è in `data-model.md` §4 (preferito: generalizzare
il dedup per non introdurre una seconda strategia di merge — DRY, Principio III).

### Perché NON la revisione profonda
Una riprogettazione del seam (es. introdurre un `SurfaceContract` polimorfico per ogni superficie)
violerebbe YAGNI (Principio III): le quattro lacune si chiudono con parametri additivi su funzioni
esistenti, senza nuove `ArtifactKind` e senza toccare il target `claude` (default invariato). Il seam ha già
la granularità giusta (per-`AssistantId`). La revisione profonda resta **autorizzata ma non necessaria**;
si segnala come opzione solo se, in `/speckit-tasks`, l'estensione (a)+(d) risultasse intrattabile sul
veicolo COMMAND — eventualità che il pattern `_render_for_target` esistente rende improbabile.

---

## 3. Decisioni derivate (per-superficie)

| Superficie | Decisione | Fonte |
|---|---|---|
| Hook JSON Copilot | Generato nativo: `version:1`, `hooks.{evento}:[piatto]`, `timeoutSec`, no `shell`/`statusMessage` | FR-001..005; audit 🔴 |
| Alias evento | Accettare PascalCase + alias documentati (`SessionStart`↔`sessionStart`, `PreToolUse`↔`preToolUse`, `Stop`↔`agentStop`) | FR-005; A-3 |
| SessionStart CLI | `type:"prompt"` | Q1=b |
| SessionStart VS Code | `type:"command"` → `{additionalContext}` | Nodo #1, [ASSUNTO-VSC] |
| agentStop | `{decision:"allow", reason:"<msg>"}` (non-bloccante) | Q3=b, FR-007 |
| preToolUse | exit 0, nessun output spurio (fail-open) anche su errore | FR-008/041, NFR-3; audit 🔴 |
| sessionEnd | nessun output consumato; eventuale messaggio → stderr | FR-009 |
| Script `.ps1` | corpo condiviso + `-Assistant`; output nativo; mai dual-field | Q4=b, FR-011/012 |
| COMMAND CLI | custom-agent | Q2=c, FR-013/014 |
| COMMAND VS Code | prompt-file (+ eventuale custom-agent) | FR-015 (Should) |
| Frontmatter prompt-file | chiave `agent:` (non `mode:`) | FR-016; audit |
| Frontmatter custom-agent | `model:` omesso; persona preservata; corpo byte-for-byte | FR-017/018/019, Q6=a |
| MCP CLI | documentare prova empirica `.mcp.json`/`mcpServers` vs `~/.copilot/mcp-config.json`; correggere solo se smentita | FR-020, Q5 |
| Test schema | suite offline (stdlib `json`/`tomllib`/parsing frontmatter), reintroduzione difetti → fail | FR-021..026, NFR-5 |
| Claim/gap | nessuna parità non verificata; gap espliciti nel report + surface-mapping | FR-027/028 |

> **Nota frontmatter prompt-file `agent:`** — il requisito REQ-016 prescrive `agent:` come chiave
> documentata. Il **valore** (es. `agent: 'agent'`, da requirements §4) e l'eventuale necessità di un valore
> diverso da `agent` per i comandi-skill vanno fissati in `data-model.md`; l'invariante è: chiave `agent:`,
> non `mode:`.

---

## 4. Verifica MCP CLI (FR-020 / Q5) — stato dell'evidenza

L'audit segna l'MCP CLI come **⚠️ da riconfermare**: PR #66 ha validato empiricamente che Copilot CLI legge
`.mcp.json` (cwd→git root) con root `mcpServers` (cfr. `wiki/tech/assistant-targeting.md:40-47` e
`test_install_rag_copilot_cli.py:30-40`), **ma** la doc ufficiale indica `~/.copilot/mcp-config.json`
(user-level). FR-020 è **non-bloccante**: richiede di **documentare** l'evidenza (la PR #66 è la prova
corrente, valida per CLI 1.0.63) e di correggere la surface **solo se** una versione successiva la smentisce.

**Decisione**: nessuna modifica alla surface MCP in questa feature (l'assunto A-4 resta valido); si produce
solo la **documentazione di evidenza** (surface-mapping) e si lascia il test esistente
(`test_install_rag_copilot_cli.py`) come guardia. Se l'utente esegue una verifica empirica che smentisce
PR #66, la correzione è un follow-up tracciato (non si indovina).

---

## 5. Constitution Check (Phase 0) — esito sintetico

Eseguito in `plan.md` §Constitution Check (pre-design): **PASS 11/11**, nessuna deroga. I principi più
sollecitati: III (estensione mirata vs revisione profonda → si sceglie il minimo), X (tutto passa per il
seam, niente assunzioni d'ospite nel corpo), VI (install≠run, idempotenza, non-distruttività preservate),
XI (i comandi di esecuzione restano via vehicles; la feature è tutta install-time, non runtime di core).

---

## 6. Conclusioni / output per Phase 1

- Nodo #1 risolto: SessionStart per-famiglia (CLI `prompt` / VS Code `command`→`additionalContext`), con
  [ASSUNTO-VSC] dichiarato e fallback nativo.
- Nodo #2 risolto: **estensione mirata** del seam (4 interventi additivi), revisione profonda non necessaria.
- Nessun `NEEDS CLARIFICATION` residuo (Q1–Q6 chiuse; nodi di design risolti; [ASSUNTO-VSC] è validazione
  operativa, non ambiguità di prodotto).
- Pronto per `data-model.md` + `contracts/`.
