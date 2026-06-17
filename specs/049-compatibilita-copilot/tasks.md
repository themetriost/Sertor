# Tasks — Hardening compatibilità GitHub Copilot dell'installer

**Feature**: FEAT-011 — `049-compatibilita-copilot`
**Branch**: `049-compatibilita-copilot`
**Spec**: `specs/049-compatibilita-copilot/spec.md` · **Plan**: `specs/049-compatibilita-copilot/plan.md`
**Data-model**: `specs/049-compatibilita-copilot/data-model.md`
**Contracts**: `specs/049-compatibilita-copilot/contracts/`
**Generato**: 2026-06-17

---

## Panoramica delle fasi e dipendenze

```
Fase 0 — Setup / lettura ground-truth
  └─► Fase 1 — Foundational: seam del kit (assistant.py + surfaces.py + settings_merge.py)
        ├─► Fase 2 — US1/US4: hook JSON nativo Copilot (render_copilot_hooks + HookEntrySpec)
        │     └─► Fase 3 — US2/US4: script .ps1 condivisi (parametro -Assistant, output nativo)
        │           ├─► Fase 4 — US3: SessionStart per-famiglia (script estratto + wiring)
        │           ├─► Fase 5 — US5: piano comandi per-target (CLI custom-agent)
        │           └─► Fase 6 — US6: frontmatter nativo (agent: / no model:)
        │                 └─► Fase 7 — US7: suite validità-schema offline (gruppo G)
        │                       └─► Fase 8 — US8/Polish: gap declaration, surface-mapping, propagazione governance
```

**Regola MVP**: ogni storia (US1–US7) ha un test di non-regressione Claude da eseguire subito dopo
la modifica del codice condiviso (gate duro, SC-010). La US7 (test di schema) DEVE esistere prima
che qualunque asset Copilot sia dichiarato "pronto" (FR-026).

**Parallelismo**: i task marcati `[P]` all'interno della stessa fase possono essere implementati in
parallelo da thread/sessioni diversi purché i task foundational della fase precedente siano già su
branch (`git stash` / worktree o riuso del branch unico con ordine di commit disciplinato).

---

## Fase 0 — Setup: lettura ground-truth e ancoraggio

> Prerequisito: branch `049-compatibilita-copilot` già creato. Nessuna modifica al codice.
> Scopo: leggere i file rilevanti e verificare la corrispondenza tra gli asset reali e gli assunti
> del design, prima di toccare qualsiasi file.

- [x] **T-000** Leggere i file hook statici oggi in formato Claude e annotare i difetti esatti
  - `packages/sertor/src/sertor_installer/assets/copilot/hooks/wiki.hooks.json`
  - `packages/sertor/src/sertor_installer/assets/copilot/hooks/rag-usage.hooks.json`
  - Verificare: mancanza `"version"`, struttura annidata `hooks[].hooks[]`, campi `shell`/`statusMessage`/`timeout` (nome Claude)
  - Confermare con la tabella dell'audit in `specs/049-compatibilita-copilot/research.md` §0

- [x] **T-001** Leggere gli script hook e il seam esistente
  - `packages/sertor/src/sertor_installer/assets/claude/hooks/wiki-pending-check.ps1`
    — `param` attuale, blocco output `{ systemMessage }` per Stop **e** SessionEnd
  - `packages/sertor-install-kit/src/sertor_install_kit/surfaces.py`
    — `render_prompt_file` (riga ~46: `mode: agent`), `render_custom_agent` (riga ~59: copia `model`)
  - `packages/sertor-install-kit/src/sertor_install_kit/assistant.py`
    — `copilot` e `copilot-cli`: stessa `_command_dir=".github/prompts"` / `_command_suffix=".prompt.md"`
  - `packages/sertor-install-kit/src/sertor_install_kit/settings_merge.py`
    — `_inner_commands`: struttura Claude `entry["hooks"][].command`; non riconosce forma piatta Copilot
  - `packages/sertor/src/sertor_installer/install_wiki.py` (righe 158–203: `_build_copilot_wiki_plan`)
  - `packages/sertor-flow/src/sertor_flow/install_governance.py` (righe 83–91: piano Copilot CLI uguale a VS Code)

- [x] **T-002** Leggere i test Copilot esistenti e capire cosa verificano oggi
  - `packages/sertor/tests/test_install_wiki_copilot.py`
  - `packages/sertor/tests/test_assets_copilot_guard.py`
  - `packages/sertor/tests/test_install_rag_copilot.py`
  - `packages/sertor/tests/test_install_rag_copilot_cli.py`
  - `packages/sertor-flow/tests/test_install_governance_copilot.py`
  - Annotare: i test verificano **presenza** dell'asset (es. `mode: agent` atteso), NON la validità-schema Copilot

- [x] **T-003** Eseguire la suite corrente (baseline verde) prima di modificare nulla
  - `uv run pytest packages/sertor/tests/ packages/sertor-flow/tests/ packages/sertor-install-kit/ -q`
  - Salvare l'output: numero di test, eventuali skip. Questo è il baseline di non-regressione.

---

## Fase 1 — Foundational: estensioni del seam nel kit condiviso

> Pacchetto: `packages/sertor-install-kit/src/sertor_install_kit/`
> Principio: queste modifiche sono **additive** (nessun comportamento Claude alterato; `claude` rimane
> il default di ogni nuovo parametro). Completare e far passare i test di non-regressione PRIMA di
> procedere alle fasi successive.
> Dipendenza: nessuna fase precedente (salvo T-000..T-003).

### 1A — `assistant.py`: COMMAND a doppio veicolo per `copilot-cli` (data-model §1, research §2a)

- [x] **T-010** Aggiungere il campo `command_vehicle` (o modificare `_command_dir` / `_command_suffix`)
  nell'`AssistantProfile` di `copilot-cli`
  - File: `packages/sertor-install-kit/src/sertor_install_kit/assistant.py`
  - Modifica: `copilot-cli` → `_command_dir = ".github/agents"`, `_command_suffix = ".agent.md"`
    (VS Code = `copilot` → invariato: `.github/prompts` / `.prompt.md`)
  - Aggiungere attributo booleano o enum `command_vehicle: PROMPT_FILE | CUSTOM_AGENT` al profile
    (opzionale se il suffisso è già discriminante, ma rende l'intenzione esplicita per i plan-builder)
  - Invariante: `claude` non cambia; `copilot` (VS Code) non cambia

- [x] **T-011** Test di non-regressione `AssistantProfile` — aggiornare/estendere i test esistenti
  - File: `packages/sertor-install-kit/tests/` (o nel test suite corrispondente)
  - Verificare che `AssistantProfile.for_assistant(AssistantId.CLAUDE).render_path(Surface.COMMAND, "x")`
    resti invariato
  - Verificare che `copilot-cli` ora risolva `.github/agents/x.agent.md`
  - Verificare che `copilot` (VS Code) risolva ancora `.github/prompts/x.prompt.md`

### 1B — `surfaces.py`: `render_prompt_file` con chiave `agent:` e `render_custom_agent` senza `model:` (data-model §2)

- [x] **T-020** Correggere `render_prompt_file` per usare `agent:` invece di `mode:`
  - File: `packages/sertor-install-kit/src/sertor_install_kit/surfaces.py` (riga ~46)
  - Da: `mode: agent`
  - A: `agent: agent` (valore secondo requirements §4; invariante = chiave `agent:`, mai `mode:`)
  - FR-016 / SC-006 / contratto `copilot-frontmatter.md` F1
  - **Non-regressione**: il target `claude` NON usa `render_prompt_file` (usa `.claude/**` byte-copy)
    → nessun impatto su Claude

- [x] **T-021** Correggere `render_custom_agent` per omettere `model:` sui target Copilot
  - File: `packages/sertor-install-kit/src/sertor_install_kit/surfaces.py` (riga ~59)
  - Aggiungere parametro `include_model: bool = False` (default `False` = Copilot-safe)
  - Rimuovere `"model"` dall'iterazione default; il chiamante Claude non usa questo renderer (nessuna
    regressione Claude)
  - Preservare `name` / `description` / `tools` (FR-018)
  - Preservare corpo byte-for-byte (FR-019)
  - FR-017 / SC-005 / contratto `copilot-frontmatter.md` A1

- [x] **T-022** [P] Test `render_prompt_file` — aggiornare i test esistenti e aggiungere asserzioni
  - File: `packages/sertor/tests/test_assets_copilot_guard.py` (e/o test di kit)
  - Assert: frontmatter prodotto contiene `agent:` NON `mode:`
  - Assert: corpo sotto il frontmatter è identico alla fonte (guard anti-drift)

- [x] **T-023** [P] Test `render_custom_agent` — aggiornare i test esistenti e aggiungere asserzioni
  - File: `packages/sertor/tests/test_assets_copilot_guard.py` (e/o test di kit)
  - Assert: nessun campo `model:` nel frontmatter generato
  - Assert: `name` / `description` / `tools` preservati
  - Assert: corpo identico alla fonte (guard anti-drift)
  - Test di regressione (inverso): chiamata con asset che contiene `model: haiku` → `model` NON presente nell'output

### 1C — `settings_merge.py`: dedup schema-aware per entrambe le forme hook (data-model §4)

- [x] **T-030** Generalizzare `_inner_commands` per riconoscere anche la forma piatta Copilot
  - File: `packages/sertor-install-kit/src/sertor_install_kit/settings_merge.py` (riga ~18)
  - Attuale: `_inner_commands` legge `entry["hooks"][].command` (struttura Claude annidata)
  - Modifica: se `"command"` è direttamente in `entry` (forma piatta Copilot), estrarlo anche da lì
  - Retrocompatibilità GARANTITA: la forma Claude annidata deve continuare a funzionare
  - Nota di rischio R-3 del plan: testare entrambe le forme

- [x] **T-031** Test retrocompatibilità merge — file esistente nel formato Claude annidato resta gestito
  - File: `packages/sertor/tests/test_settings_merge.py` (oppure test del kit)
  - Aggiungere test: merge su file con struttura Claude annidata → dedup corretto (comando già presente
    → non duplicato)
  - Aggiungere test: merge su file con struttura piatta Copilot → dedup corretto
  - Aggiungere test: merge misto (Claude annidato + Copilot piatto nello stesso file) → entrambi
    riconosciuti

- [x] **T-032** [P] Eseguire la suite completa del kit per confermare non-regressione
  - `uv run pytest packages/sertor-install-kit/ -q`
  - Deve restare verde; 0 regressioni

---

## Fase 2 — US1/US4: hook JSON nativo Copilot (`render_copilot_hooks` + `HookEntrySpec`)

> Dipende da: Fase 1 (T-020..T-032 completati)
> Pacchetti: `packages/sertor-install-kit/` (renderer puro) + `packages/sertor/` (plan-builder +
> rimozione asset statici)
> User Story: US1 (hook conformi allo schema) + US4 parziale (fonte unica per il wiring)

### 2A — Kit: funzione pura `render_copilot_hooks` + modello `HookEntrySpec`

- [x] **T-040** Aggiungere `HookEntrySpec` (dataclass frozen) nel kit
  - File: `packages/sertor-install-kit/src/sertor_install_kit/surfaces.py` (o nuovo
    `hook_schema.py`)
  - Campi: `event: str`, `type: str`, `command: str`, `timeout_sec: int`, `matcher: str | None`
  - (vedi data-model §2, contratto `copilot-hook-schema.md`)
  - stdlib-only; frozen; nessun import esterno

- [x] **T-041** Implementare `render_copilot_hooks(events: list[HookEntrySpec]) -> dict`
  - File: stesso di T-040
  - Output struttura: `{"version": 1, "hooks": {<evento>: [{type, command, timeoutSec, [matcher]}]}}`
  - Regole MUST (contratto §1): R1 `version:1`; R2 lista piatta; R3 nessun campo Claude-only;
    R4 `timeoutSec` non `timeout`; R5 alias PascalCase/camelCase accettati
  - Funzione PURA: stdlib-only, deterministica, nessun I/O
  - Riesportare da `__init__.py` del kit

- [x] **T-042** Test unitari di `render_copilot_hooks` (offline, stdlib `json`)
  - File: `packages/sertor-install-kit/tests/` (nuovo `test_render_copilot_hooks.py` o nel kit)
  - Test R1: output contiene `"version": 1`
  - Test R2: ogni voce è piatta (no `"hooks"` annidato dentro la voce)
  - Test R3a: nessun campo `"shell"` nelle voci
  - Test R3b: nessun campo `"statusMessage"` nelle voci
  - Test R4: timeout usa `"timeoutSec"`, mai `"timeout"`
  - Test R5: alias `agentStop` / `Stop` entrambi accettati come equivalenti
  - Test: `matcher` presente solo se non `None`
  - Test anti-pattern (SC-007 — reintroduzione difetti): rimuovere `version` dall'output → fallisce

### 2B — `install_wiki.py`: sostituire l'asset statico con il wiring generato

- [x] **T-050** Modificare `_build_copilot_wiki_plan` per usare `render_copilot_hooks` al posto
  dell'asset statico `copilot/hooks/wiki.hooks.json`
  - File: `packages/sertor/src/sertor_installer/install_wiki.py` (riga ~158, `_build_copilot_wiki_plan`)
  - Rimuovere la riga che usa `_COPILOT_HOOK_FRAGMENT = "copilot/hooks/wiki.hooks.json"` come asset statico
  - Generare il `dict` wiring con `render_copilot_hooks([...])` e scriverlo come `ArtifactKind.SETTINGS_MERGE`
    (o `ArtifactKind.FILE` con contenuto inline, a seconda della strategia scelta in data-model §4)
  - Separare il piano per target: `copilot` (VS Code) e `copilot-cli` iniziano a divergere qui
    (T-050 gestisce il wiring; la divisione COMMAND è in Fase 5)
  - Le voci `SessionStart`, `Stop`, `SessionEnd` usano i comandi con `-Assistant copilot` (i comandi
    esatti dipendono dallo script estratto in Fase 4; usare placeholder per ora se Fase 4 è parallela)
  - FR-001..FR-005

- [x] **T-051** Modificare `install_rag.py` per usare `render_copilot_hooks` al posto dell'asset
  statico `copilot/hooks/rag-usage.hooks.json`
  - File: `packages/sertor/src/sertor_installer/install_rag.py`
  - Stessa logica di T-050 per il PreToolUse: `render_copilot_hooks([HookEntrySpec(event="PreToolUse",
    type="command", ..., matcher="Bash|Write|Edit|MultiEdit")])`
  - FR-001..FR-005, FR-008 (exit 0 garantito — vedi Fase 3 per lo script)

- [x] **T-052** Eliminare gli asset statici in formato Claude
  - File da rimuovere (o svuotare come `.gitkeep`):
    - `packages/sertor/src/sertor_installer/assets/copilot/hooks/wiki.hooks.json`
    - `packages/sertor/src/sertor_installer/assets/copilot/hooks/rag-usage.hooks.json`
  - Aggiornare `resources.py` / `iter_asset_dir` se questi file erano inclusi esplicitamente
  - Confermare che nessun altro punto del codice li referenzia (grep su `wiki.hooks.json`,
    `rag-usage.hooks.json`)

- [x] **T-053** Test di integrazione: plan wiki Copilot produce hook JSON nativo (non il vecchio formato)
  - File: `packages/sertor/tests/test_install_wiki_copilot.py`
  - Aggiornare/estendere: ispezionare il contenuto del file `.github/hooks/sertor-hooks.json` prodotto
    nel tmp_path
  - Assert R1..R4 sul file generato (vedi contratto `copilot-hook-schema.md`)
  - Assert: nessun campo `"shell"`, `"statusMessage"`, `"timeout"` (nome Claude)

- [x] **T-054** [P] Test non-regressione target Claude (gate duro SC-010)
  - `uv run pytest packages/sertor/tests/test_install_wiki.py packages/sertor/tests/test_install_rag.py -q`
  - DEVE restare verde prima di procedere. Se fallisce: bloccare e correggere.

---

## Fase 3 — US2/US4: script `.ps1` condivisi con parametro `-Assistant` e output nativo per evento

> Dipende da: Fase 1 completata (T-020..T-032)
> Pacchetto: `packages/sertor/src/sertor_installer/assets/claude/hooks/`
> Può essere sviluppata in PARALLELO con Fase 2 (non condividono file, salvo la chiamata allo script
> nel wiring, che può essere aggiornata dopo)

### 3A — `wiki-pending-check.ps1`: aggiungere `-Assistant` e output nativo per evento

- [x] **T-060** Aggiungere parametro `-Assistant` con default `claude` (non-regressione FR-040)
  - File: `packages/sertor/src/sertor_installer/assets/claude/hooks/wiki-pending-check.ps1`
  - Modificare `param(...)`: aggiungere `[ValidateSet('claude','copilot')][string]$Assistant = 'claude'`
  - Il `$Mode` esistente (`Stop`/`SessionEnd`) rimane invariato
  - Default `claude` → comportamento storico byte-for-byte (non-regressione SC-010)

- [x] **T-061** Implementare la resa output nativa per evento e assistente (no dual-field FR-011)
  - File: stesso di T-060
  - Ramo `claude` (default): invariato — `{ systemMessage = $msg }` per Stop **e** SessionEnd
  - Ramo `copilot` + `Mode=Stop` (→ `agentStop`): `{ decision = "allow"; reason = $msg }` (FR-007,
    contratto `hook-output-contract.md` O3)
  - Ramo `copilot` + `Mode=SessionEnd` (→ `sessionEnd`): nessun stdout; eventuale msg → stderr
    (FR-009, contratto O5)
  - Exit 0 in tutti i casi
  - Mai dual-field: nessun ramo che scriva sia `systemMessage` sia `decision`/`reason`

- [x] **T-062** Aggiornare i comandi nel wiring Copilot per passare `-Assistant copilot`
  - File: `packages/sertor/src/sertor_installer/install_wiki.py`
  - Le voci hook `Stop` e `SessionEnd` nel piano Copilot devono chiamare lo script con
    `-Mode Stop -Assistant copilot` e `-Mode SessionEnd -Assistant copilot`
  - (Coordinare con T-050 se le fasi procedono in parallelo)

### 3B — `sertor-rag-usage-check.ps1`: garantire exit 0 fail-open su Copilot (FR-008/041)

- [x] **T-070** Aggiungere `-Assistant` e garantire exit 0 sempre su Copilot
  - File: `packages/sertor/src/sertor_installer/assets/claude/hooks/sertor-rag-usage-check.ps1`
    (o percorso equivalente — verificare con T-001 il path esatto)
  - Aggiungere `[ValidateSet('claude','copilot')][string]$Assistant = 'claude'` nel `param(...)`
  - Avvolgere l'intero corpo in un `try { ... } catch { if ($Assistant -eq 'copilot') { exit 0 } }`
    (nota di rischio R-2: fail-closed su Copilot → exit 0 SEMPRE, anche su errore parsing)
  - Su Copilot: nessun output spurio che Copilot possa interpretare come `decision:"deny"` (contratto O2)
  - Default `claude` → comportamento storico invariato

- [x] **T-071** Aggiornare i comandi nel wiring Copilot (PreToolUse) per passare `-Assistant copilot`
  - File: `packages/sertor/src/sertor_installer/install_rag.py`
  - La voce `PreToolUse` nel piano Copilot deve chiamare lo script con `-Assistant copilot`
  - (Coordinare con T-051 se le fasi procedono in parallelo)

### 3C — Test script `.ps1` (invocazione con mock / FakeCommandRunner)

- [x] **T-075** Test `wiki-pending-check.ps1` con `-Assistant copilot` per evento Stop
  - File: `packages/sertor/tests/test_install_wiki_copilot.py` (o nuovo
    `test_hooks_script_copilot.py`)
  - Invocare lo script in modalità Copilot (se l'ambiente PowerShell è disponibile in CI) O
    verificare la struttura del file con parsing (approccio offline-safe)
  - Assert: output contiene `decision` = `"allow"` e `reason` (non `systemMessage`) — contratto O3
  - Assert: nessun campo dual-field (non presente contemporaneamente `systemMessage` e `decision`)

- [x] **T-076** [P] Test `wiki-pending-check.ps1` con `-Assistant copilot` per evento SessionEnd
  - Assert: nessun output su stdout (o output non contiene payload consumato da Copilot) — O5
  - Assert: exit 0

- [x] **T-077** [P] Test `wiki-pending-check.ps1` con `-Assistant claude` (default) — non-regressione
  - Assert: output contiene `systemMessage` (invariato rispetto al comportamento storico) — O6
  - GATE: questo test DEVE essere verde prima di ogni merge

- [x] **T-078** [P] Test `sertor-rag-usage-check.ps1` con stdin malformato su Copilot → exit 0 fail-open
  - Assert: exit 0 anche con stdin invalido (nota di rischio R-2)
  - Assert: nessun output spurio su stdout

---

## Fase 4 — US3: SessionStart per-famiglia (script estratto + wiring nativo)

> Dipende da: Fase 3 (T-060..T-071 completati — il nuovo script SessionStart condivide la struttura
> `-Assistant`)
> Pacchetti: `packages/sertor/`

### 4A — Estrarre il corpo inline di SessionStart in uno script dedicato

- [x] **T-080** Creare `wiki-session-start.ps1` (estratto dall'inline in `wiki.hooks.json`)
  - File nuovo: `packages/sertor/src/sertor_installer/assets/claude/hooks/wiki-session-start.ps1`
  - Parametro: `[ValidateSet('claude','copilot')][string]$Assistant = 'claude'`
  - Corpo: calcolo del nome-partizione-log + direttiva «carica roadmap/index/log + mostra EXEC»
    (stesso contenuto oggi inline in `wiki.hooks.json:11`) — fonte unica, anti-drift
  - Ramo `claude` (default): emettere la direttiva su stdout (forma storica — non-regressione)
  - Ramo `copilot` (VS Code → `type:"command"`): stdout `{"additionalContext": "<direttiva>"}` (JSON
    valido, mai stringa nuda — contratto `hook-output-contract.md` O4; [ASSUNTO-VSC] dichiarato)
  - Ramo `copilot-cli`: NON viene invocato (usa `type:"prompt"` statico nel wiring — nessun output)
  - Exit 0; stdlib PS — nessuna dipendenza esterna

- [x] **T-081** Aggiornare `install_wiki.py`: piano Claude usa lo script estratto invece dell'inline
  - File: `packages/sertor/src/sertor_installer/install_wiki.py`
  - Il piano Claude ora installa `wiki-session-start.ps1` in `.claude/hooks/` e lo referenzia nel
    wiring `settings.hooks.json` (al posto del comando inline)
  - Non-regressione: il comportamento dell'utente Claude è identico (lo script emette la stessa
    direttiva)

### 4B — Wiring SessionStart per-famiglia nel piano Copilot

- [x] **T-082** Aggiornare `_build_copilot_wiki_plan` per SessionStart per-famiglia
  - File: `packages/sertor/src/sertor_installer/install_wiki.py`
  - `copilot` (VS Code): voce hook `SessionStart` = `type:"command"` → chiama
    `wiki-session-start.ps1 -Assistant copilot` (emette `{additionalContext}`) — `[ASSUNTO-VSC]`
  - `copilot-cli`: voce hook `SessionStart` = `type:"prompt"` con `command` = direttiva statica
    (nessuno script da invocare — la direttiva è il prompt) — FR-006 / Q1=b
  - Installiamo `wiki-session-start.ps1` anche in `.github/hooks/` (riuso dello script già nel piano)
  - Separare `_build_copilot_wiki_plan` in `_build_copilot_vscode_wiki_plan` e
    `_build_copilot_cli_wiki_plan` se la divergenza è significativa, altrimenti parametrizzare

- [x] **T-083** Test SessionStart CLI: voce hook è `type:"prompt"`, nessuna stringa nuda — SC-003 / FR-006
  - File: `packages/sertor/tests/test_install_wiki_copilot.py` (aggiornare)
  - Assert: piano `copilot-cli` contiene una voce `SessionStart` con `type: "prompt"` nel JSON
    generato (non una stringa non-JSON)
  - Assert: nessuna voce `SessionStart` ha `type: "command"` + output plain-string

- [x] **T-084** [P] Test SessionStart VS Code: voce hook è `type:"command"`, output JSON parsabile
  - Assert: piano `copilot` (VS Code) ha `SessionStart` `type:"command"`
  - Assert: invocando lo script in modalità `copilot`, l'output è `{"additionalContext": "..."}` (JSON
    valido — O4)
  - Dichiarare `[ASSUNTO-VSC]` nel commento del test: «non confermato runtime su VS Code reale»

- [x] **T-085** [P] Test non-regressione SessionStart Claude (gate duro)
  - Assert: il piano Claude usa lo script estratto; comportamento identico a prima
  - `uv run pytest packages/sertor/tests/test_install_wiki.py -q` verde

---

## Fase 5 — US5: piano comandi per-target (CLI custom-agent)

> Dipende da: T-010/T-011 (Fase 1A, `copilot-cli` risolve `.github/agents/`)
> Può essere sviluppata in PARALLELO con Fase 4 (non condividono logica)
> Pacchetti: `packages/sertor/` + `packages/sertor-flow/`

### 5A — `install_wiki.py`: COMMAND CLI come custom-agent

- [x] **T-090** Separare il piano COMMAND per `copilot` e `copilot-cli` nel wiki
  - File: `packages/sertor/src/sertor_installer/install_wiki.py`
  - `copilot` (VS Code): COMMAND = `.github/prompts/wiki.prompt.md` + `.github/prompts/wiki-author.prompt.md`
    (prompt-file, FR-015 Should)
  - `copilot-cli`: COMMAND = `.github/agents/wiki.agent.md` + `.github/agents/wiki-author.agent.md`
    (custom-agent, FR-013)
  - Usare `render_custom_agent` per le destinazioni `.agent.md` e `render_prompt_file` per le
    destinazioni `.prompt.md` (già in `_render_for_target`)
  - Aggiornare le costanti `_WIKI_COMMAND_DST` / `_WIKI_SKILL_DST` in base al target

- [x] **T-091** Test piano wiki `copilot-cli`: nessun COMMAND solo-prompt-file — SC-004 / FR-013
  - File: `packages/sertor/tests/test_install_wiki_copilot.py` (aggiornare)
  - Assert: il piano `copilot-cli` contiene artefatti con target `.agent.md` per `/wiki` e `wiki-author`
  - Assert: il piano `copilot-cli` NON ha artefatti con target `.prompt.md` per i COMMAND (o se li ha,
    ha ANCHE il `.agent.md`)
  - Test anti-pattern (SC-007): forzare solo prompt-file sul piano CLI → il test fallisce

### 5B — `install_governance.py` (`sertor-flow`): COMMAND CLI come custom-agent

- [x] **T-095** Separare il piano COMMAND per `copilot` e `copilot-cli` nella governance
  - File: `packages/sertor-flow/src/sertor_flow/install_governance.py` (righe 83–91)
  - Stesso schema di T-090: CLI → custom-agent `.github/agents/requirements.agent.md`; VS Code →
    prompt-file `.github/prompts/requirements.prompt.md`
  - Riusare i renderer del kit (`render_custom_agent` / `render_prompt_file`) — FR-042 / SC-011
  - Vincolo ASSOLUTO: `sertor-flow` NON importa `sertor-core` / `sertor` (guard esistente in
    `packages/sertor-flow/tests/unit/test_no_core_dependency.py`)

- [x] **T-096** Test piano governance `copilot-cli`: nessun COMMAND solo-prompt-file — FR-014 / SC-004
  - File: `packages/sertor-flow/tests/test_install_governance_copilot.py` (aggiornare)
  - Assert: il piano `copilot-cli` ha `requirements.agent.md` come COMMAND
  - Assert: nessuna dipendenza da `sertor-core` / `sertor` introdotta (eseguire guard
    `test_no_core_dependency.py`)

- [x] **T-097** [P] Eseguire guard dipendenza `sertor-flow` dopo T-095
  - `uv run pytest packages/sertor-flow/tests/unit/test_no_core_dependency.py
    packages/sertor-flow/tests/integration/test_install_without_core.py -q`
  - GATE: DEVE restare verde (SC-011)

---

## Fase 6 — US6: frontmatter nativo per prompt-file e custom-agent

> Dipende da: T-020..T-023 (Fase 1B — renderer già corretti)
> Dipende da: T-090/T-095 (Fase 5 — i piani ora generano le destinazioni corrette)
> Questa fase verifica che il renderer aggiornato (Fase 1B) sia effettivamente usato nei piani reali

- [x] **T-100** Verifica end-to-end: prompt-file installato su `copilot` ha frontmatter `agent:`
  - File: `packages/sertor/tests/test_install_wiki_copilot.py` (aggiornare)
  - Eseguire `build_install_plan(AssistantId.COPILOT)` su un `tmp_path`, leggere
    `.github/prompts/wiki.prompt.md`, verificare che il frontmatter contenga `agent:` NON `mode:`
  - Assert: corpo identico alla fonte canonica Claude (guard anti-drift FR-019)
  - FR-016 / SC-006

- [x] **T-101** [P] Verifica end-to-end: custom-agent installato su `copilot` / `copilot-cli` non ha `model:`
  - File: `packages/sertor/tests/test_install_wiki_copilot.py` (aggiornare)
  - Leggere `.github/agents/wiki-curator.agent.md` prodotto nel `tmp_path`
  - Assert: frontmatter NON contiene `model:` (con qualsiasi valore)
  - Assert: `name` / `description` / `tools` presenti (se nell'originale)
  - Assert: corpo identico alla fonte canonica
  - FR-017 / SC-005

- [x] **T-102** [P] Verifica end-to-end governance: prompt-file e custom-agent con frontmatter corretto
  - File: `packages/sertor-flow/tests/test_install_governance_copilot.py` (aggiornare)
  - Stesse asserzioni di T-100/T-101 per la skill `requirements`
  - Conferma che le correzioni del renderer del kit si propagano a `sertor-flow` (FR-042 / SC-011)

---

## Fase 7 — US7: suite di validità-schema offline (gruppo G)

> Dipende da: Fasi 2–6 completate (gli asset corretti esistono prima di testarli)
> Questa è la fase di TEST FONDAMENTALI (FR-021..026, SC-007)
> Tutti i test DEVONO girare OFFLINE (stdlib `json`, frontmatter parsing, no Copilot client)
> Principio: per OGNI difetto dell'audit, un test che fallirebbe se reintrodotto

### 7A — Test validità-schema hook JSON (FR-021 / SC-007 scenario 1)

- [x] **T-110** Creare o estendere la suite di validità-schema hook Copilot in `packages/sertor/tests/`
  - File: `packages/sertor/tests/test_schema_copilot_hooks.py` (nuovo)
  - Helper: funzione `assert_valid_copilot_hook_file(data: dict)` che verifica R1..R4
    (contratto `copilot-hook-schema.md`)
  - Test T-110a: campo `"version"` presente e `== 1` — R1
  - Test T-110b: ogni voce nell'evento è piatta (no `"hooks"` annidato dentro la voce) — R2
  - Test T-110c: nessuna voce contiene `"shell"` — R3
  - Test T-110d: nessuna voce contiene `"statusMessage"` — R3
  - Test T-110e: nessuna voce usa `"timeout"` (il nome Claude); usa `"timeoutSec"` — R4
  - Eseguire la suite su entrambi i piani: wiki Copilot + rag-usage Copilot (prodotti su tmp_path)

- [x] **T-111** Test anti-pattern: reintrodurre ogni difetto → fallisce (SC-007 scenario 1)
  - Test T-111a: rimuovere `"version"` dall'output di `render_copilot_hooks` → `assert_valid_*` fallisce
  - Test T-111b: aggiungere `"hooks": [...]` annidato in una voce → R2 fallisce
  - Test T-111c: aggiungere `"shell": "powershell"` in una voce → R3 fallisce
  - Test T-111d: usare `"timeout"` invece di `"timeoutSec"` → R4 fallisce
  - Approccio: usare `HookEntrySpec` e `render_copilot_hooks` costruendo casi difettosi

### 7B — Test validità-schema frontmatter prompt-file (FR-022 / SC-007 scenario 2)

- [x] **T-115** Creare suite di validità-schema frontmatter Copilot in `packages/sertor/tests/`
  - File: `packages/sertor/tests/test_schema_copilot_frontmatter.py` (nuovo, o aggiungere a
    `test_assets_copilot_guard.py`)
  - Test T-115a: ogni `.prompt.md` installato su `copilot` contiene frontmatter con chiave `agent:`
    NON `mode:` — F1 (contratto `copilot-frontmatter.md`)
  - Test T-115b (anti-pattern SC-007): produrre un prompt-file con `mode:` → test fallisce
  - Test T-115c: corpo identico alla fonte canonica Claude (guard FR-019)

- [x] **T-116** [P] Test validità-schema custom-agent (FR-023 / SC-007 scenario 3)
  - File: stesso di T-115 o `test_assets_copilot_guard.py`
  - Test T-116a: nessun custom-agent generato per `copilot` / `copilot-cli` contiene `model:` con
    valore Claude
  - Test T-116b (anti-pattern SC-007): passare un asset con `model: haiku` a `render_custom_agent`
    → campo `model:` ASSENTE nell'output
  - Test T-116c: `name` / `description` / `tools` presenti quando nella fonte — A2

### 7C — Test validità output script per evento (FR-024 / SC-007 scenario 4)

- [x] **T-120** [P] Test che gli script hook per `copilot` emettono output conforme per evento (SC-002)
  - File: `packages/sertor/tests/test_schema_copilot_hooks.py` (aggiungere sezione) o
    `test_hooks_script_copilot.py`
  - Test T-120a: `wiki-pending-check.ps1 -Mode Stop -Assistant copilot` → output ha `decision`
    non `systemMessage`; `decision == "allow"` — O3
  - Test T-120b: `wiki-pending-check.ps1 -Mode SessionEnd -Assistant copilot` → stdout vuoto
    (o nessun payload consumabile da Copilot) — O5
  - Test T-120c (anti-pattern SC-007 / SC-008): script che emette sia `systemMessage` sia `decision`
    → test fallisce (dual-field)
  - Test T-120d: `sertor-rag-usage-check.ps1 -Assistant copilot` con stdin malformato → exit 0 — O2
  - Approccio preferito: test offline che leggono il contenuto del file `.ps1` e verificano le
    costanti di output (se l'esecuzione PowerShell non è garantita in CI); in alternativa, invocare
    lo script se `pwsh` è disponibile

### 7D — Test validità COMMAND non solo-prompt-file su CLI (FR-025 / SC-007 scenario 5)

- [x] **T-125** Test che il piano `copilot-cli` non ha COMMAND solo-prompt-file (SC-004)
  - File: aggiungere a `test_schema_copilot_frontmatter.py` o ai test di piano esistenti
  - Test T-125a: piano wiki `copilot-cli` contiene almeno un artefatto con target `.agent.md` per
    ogni COMMAND (wiki, wiki-author)
  - Test T-125b (anti-pattern SC-007 scenario 5): rimuovere il custom-agent dal piano CLI e lasciare
    solo il prompt-file → questo test fallisce
  - Test T-125c: piano governance `copilot-cli` ha custom-agent per `requirements`

### 7E — Test che la suite gira offline (FR-026 / SC-007 scenario 6)

- [x] **T-130** Documentare e applicare marker `@pytest.mark.no_network` (o simile) ai nuovi test
  - I test di schema usano solo: `json` stdlib, parsing frontmatter in-memory, costruzione piani
    su `tmp_path`, invocazione script locale
  - Nessun test chiama API esterne, non richiede Copilot client, non richiede credenziali
  - Verificare esecuzione con `uv run pytest packages/sertor/tests/test_schema_copilot_hooks.py
    packages/sertor/tests/test_schema_copilot_frontmatter.py -q`

---

## Fase 8 — US8 / Polish: gap declaration, surface-mapping, propagazione governance

> Dipende da: tutte le fasi P1 (1–7) completate
> Questa fase è P2 ma è necessaria per il "done" corretto (nessun false-positive)

### 8A — Dichiarazione gap nell'output d'installazione (FR-027/028 / SC-009)

- [x] **T-140** Aggiornare `install_wiki.py` per dichiarare `[ASSUNTO-VSC]` nell'`InstallReport`
  - File: `packages/sertor/src/sertor_installer/install_wiki.py`
  - Nell'`InstallReport` prodotto per target `copilot` (VS Code), aggiungere un avviso/nota esplicita:
    «SessionStart VS Code: meccanismo `additionalContext` non verificato su client reale — gap
    dichiarato (non parità piena)»
  - Non dichiarare "parità funzionale piena" per questa superficie (FR-027)

- [x] **T-141** [P] Aggiornare `install_rag.py` e `install_governance.py` per dichiarare gap analoghi
  - File: `packages/sertor/src/sertor_installer/install_rag.py`
  - File: `packages/sertor-flow/src/sertor_flow/install_governance.py`
  - Nessuna superficie Copilot dichiarata come «parità piena» se non validata + confermata runtime
  - SC-009

### 8B — Documentazione: `surface-mapping-and-gaps.md` e verifica MCP CLI (FR-020)

- [x] **T-145** Aggiornare `specs/049-compatibilita-copilot/contracts/surface-mapping-and-gaps.md`
  - File: `specs/049-compatibilita-copilot/contracts/surface-mapping-and-gaps.md`
  - Aggiornare la tabella §2 con lo stato finale per-superficie: «schema validato (offline) ✓» per
    le superfici corrette; «[ASSUNTO-VSC]» dichiarato su SessionStart VS Code
  - FR-020: documentare l'evidenza MCP CLI (PR #66, CLI 1.0.63, chiave `mcpServers` in `.mcp.json`)
    con il caveat della doc ufficiale (`~/.copilot/mcp-config.json`) — nessuna modifica alla surface

- [x] **T-146** [P] Aggiornare `wiki/tech/assistant-targeting.md` (o equivalente) con i gap dichiarati
  - File: `wiki/tech/assistant-targeting.md`
  - Riflettere la tabella `surface-mapping-and-gaps.md` §2 aggiornata
  - Nessuna voce deve dichiarare "parità piena" non verificata (SC-009)

### 8C — Gate finale: suite completa verde

- [x] **T-150** Eseguire la suite completa di tutti e tre i pacchetti
  - `uv run pytest packages/sertor/tests/ packages/sertor-flow/tests/ packages/sertor-install-kit/
    -q --tb=short`
  - GATE DURO: 0 fallimenti (inclusa non-regressione Claude SC-010 e guard dipendenza SC-011)

- [x] **T-151** [P] Verificare che non esistano import di `sertor-core` / `sertor` in `sertor-flow`
  - `uv run pytest packages/sertor-flow/tests/unit/test_no_core_dependency.py
    packages/sertor-flow/tests/integration/test_install_without_core.py -q`
  - GATE DURO: SC-011

- [x] **T-152** [P] Ruff lint sui file modificati
  - `uv run ruff check packages/sertor-install-kit/src/ packages/sertor/src/ packages/sertor-flow/src/ --select E,F,I,UP,B`
  - 0 errori

- [x] **T-153** [P] Verifica idempotenza: eseguire due volte il piano Copilot sullo stesso `tmp_path`
  - Assert: secondo install → outcome `SKIPPED` / `no new entries` per tutti gli artefatti già presenti
  - FR-040 / NFR-1

---

## Grafo delle dipendenze (sintesi)

```
T-000..T-003 (Fase 0 — lettura)
    │
    ├─► T-010..T-032 (Fase 1 — seam kit)
    │       │
    │       ├─► T-040..T-054 (Fase 2 — render_copilot_hooks) ─────────────┐
    │       │                                                                │
    │       ├─► T-060..T-078 (Fase 3 — script .ps1 -Assistant) ─────────┐  │
    │       │       │                                                     │  │
    │       │       └─► T-080..T-085 (Fase 4 — SessionStart) ────────┐   │  │
    │       │                                                          │   │  │
    │       └─► T-090..T-097 (Fase 5 — COMMAND per-target) ───────┐   │   │  │
    │               │                                               │   │   │  │
    │               └─► T-100..T-102 (Fase 6 — frontmatter E2E)   │   │   │  │
    │                       │                                       │   │   │  │
    └──────────────────────────────────────────────────────────────┼───┼───┼──┘
                                                                    │   │   │
                                                    T-110..T-130 (Fase 7 — suite schema)
                                                                    │
                                                    T-140..T-153 (Fase 8 — polish + gate)
```

**Gate duri (bloccanti)**:
1. T-054 (non-regressione Claude dopo Fase 2) — DEVE essere verde prima di merge
2. T-097 (guard dipendenza `sertor-flow`) — DEVE essere verde dopo ogni modifica a `sertor-flow`
3. T-150 (suite completa) — DEVE essere verde per il "done"

---

## Conteggio task per fase / storia

| Fase | Descrizione | Task totali | [P] paralleli |
|------|-------------|-------------|---------------|
| Fase 0 | Setup / lettura ground-truth | 4 (T-000..T-003) | 0 |
| Fase 1 | Foundational: seam del kit | 8 (T-010..T-032) | 2 (T-022, T-023) |
| Fase 2 | US1/US4: hook JSON nativo | 6 (T-040..T-054) | 2 (T-054) |
| Fase 3 | US2/US4: script .ps1 / output nativo | 8 (T-060..T-078) | 4 (T-076..T-078) |
| Fase 4 | US3: SessionStart per-famiglia | 6 (T-080..T-085) | 2 (T-084, T-085) |
| Fase 5 | US5: COMMAND per-target | 5 (T-090..T-097) | 2 (T-097) |
| Fase 6 | US6: frontmatter nativo E2E | 3 (T-100..T-102) | 2 (T-101, T-102) |
| Fase 7 | US7: suite validità-schema offline | 10 (T-110..T-130) | 5 (T-116, T-120..T-130) |
| Fase 8 | US8 + Polish + gate finale | 9 (T-140..T-153) | 6 (T-141, T-146..T-153) |
| **Totale** | | **59 task** | **25 parallelizzabili** |

Distribuzione per user story:
- US1 (hook conformi): T-040..T-054, T-110..T-111
- US2 (output script nativi): T-060..T-078, T-120
- US3 (SessionStart nativa): T-080..T-085, T-083, T-084
- US4 (fonte unica / -Assistant): T-060..T-062, T-070..T-071 (trasversale a US1/2/3)
- US5 (COMMAND CLI): T-090..T-097, T-125
- US6 (frontmatter nativo): T-020..T-023, T-100..T-102, T-115..T-116
- US7 (suite di schema): T-110..T-130 (Fase 7 intera)
- US8 (gap declaration): T-140..T-146

---

## Note implementative

### Rischi da piano (R-1..R-3 + [ASSUNTO-VSC])

- **R-1 non-regressione Claude**: ogni modifica a uno script `.ps1` o al seam richiede che
  `uv run pytest packages/sertor/tests/test_install_wiki.py packages/sertor/tests/test_install_rag.py`
  resti verde. Eseguire PRIMA e DOPO ogni intervento sugli script condivisi.
- **R-2 fail-closed preToolUse**: `sertor-rag-usage-check.ps1` deve avere un `try/catch` globale
  che forza `exit 0` su Copilot (T-070). Testare con stdin `$null` / JSON malformato (T-078).
- **R-3 dedup merge schema-aware**: `_inner_commands` esteso (T-030) deve restare retrocompatibile
  (T-031). Testare entrambe le forme (Claude annidata + Copilot piatta) nello stesso test.
- **[ASSUNTO-VSC]**: SessionStart VS Code non è verificato su client reale. I test offline (T-084)
  verificano la forma dello script ma dichiarano l'assunto. Non rimuovere il warning nel report
  (T-140) finché non c'è conferma empirica.

### FR-020 (MCP CLI)

Nessuna modifica al codice della surface MCP. Solo documentazione: T-145 aggiorna
`surface-mapping-and-gaps.md` con l'evidenza di PR #66 e il caveat della doc ufficiale. Correggere
solo su smentita empirica futura.

### Strategia MVP incrementale

Il blocco critico è **Fase 1 + Fase 2 + Fase 3**: queste tre fasi insieme chiudono i due bug più
gravi (hook scartati in silenzio + output sbagliato). Con Fase 7 (test di schema) si ottiene la rete
di sicurezza. Fasi 4–6 completano le superfici mancanti. Fase 8 chiude la documentazione e i claim.

Ordine di consegna suggerito per commit granulari:
1. Fase 0 (no commit — solo lettura)
2. Fase 1 (commit: `fix(kit): seam copilot-cli COMMAND + agent: + no model: + dedup schema-aware`)
3. Fase 2 (commit: `feat(sertor): render_copilot_hooks nativo, rimuovi asset statici Claude`)
4. Fase 3 (commit: `fix(hooks): script wiki/rag-usage -Assistant copilot, output nativo per evento`)
5. Fase 4 (commit: `feat(hooks): wiki-session-start estratto, SessionStart per-famiglia`)
6. Fase 5 (commit: `fix(sertor,flow): COMMAND CLI come custom-agent`)
7. Fase 6 (commit: `test: verifica E2E frontmatter nativo`)
8. Fase 7 (commit: `test: suite validità-schema Copilot offline (gruppo G)`)
9. Fase 8 (commit: `docs: gap declaration, surface-mapping aggiornato`)

---

## Stato finale (implement)

**59/59 task completati.** Suite per-pacchetto tutte verdi:

| Pacchetto | Esito |
|-----------|-------|
| `sertor-install-kit` | 126 passed |
| `sertor` | 219 passed |
| `sertor-flow` | 108 passed |

Gate:
- **SC-010** (non-regressione Claude): `test_install_wiki.py` + `test_install_rag.py` → 29 passed.
- **SC-011** (nessuna dipendenza `sertor-flow` → `sertor-core`/`sertor`): `test_no_core_dependency.py`
  + `test_install_without_core.py` → 17 passed.
- **ruff** (E,F,I,UP,B): pulito su `src/` e `tests/` dei tre pacchetti.
- **Idempotenza (T-153/FR-040)**: coperta da `test_double_run_idempotent` (VS Code) e
  `test_cli_double_run_idempotent` (CLI) in `test_install_wiki_copilot.py`.

**Nota su T-150 (suite congiunta in un solo comando pytest):** il lancio
`pytest packages/sertor/tests/ packages/sertor-flow/tests/ packages/sertor-install-kit/` in un'unica
sessione fallisce con `ImportPathMismatchError` perché `packages/sertor/tests/` e
`packages/sertor-flow/tests/` espongono entrambi un package `tests` con `conftest.py` omonimo (collisione
di nome del plugin pytest). È un **limite preesistente** (i due `conftest.py` provengono dal commit
`8f9a77f`, antecedente a FEAT-011), **non una regressione** introdotta da questa feature. Il gate si
soddisfa eseguendo le suite **per-pacchetto** (come fa la CI di Sertor, ogni pacchetto col proprio
`pythonpath`): tutte verdi. Eventuale unificazione del comando = debito di tooling separato (rinominare i
package di test o usare `--import-mode=importlib` con package distinti).
