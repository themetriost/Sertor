# Tasks — Consolidamento Copilot CLI-only (FEAT-012 epica sertor-cli)

**Branch**: `052-copilot-cli-only` | **Data**: 2026-06-17
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)
**Research**: [research.md](./research.md) | **Contratti**: [contracts/assistant-cli.md](./contracts/assistant-cli.md)
**Pacchetti target**: `packages/sertor-install-kit`, `packages/sertor`, `packages/sertor-flow`, `docs/`

---

## Legenda

- `[P]` task eseguibile in parallelo con altri `[P]` dello stesso gruppo
- Path sempre relativi alla radice del repo
- Ogni task di test ha uno o più success criteria (SC-xxx) di riferimento
- Il refactor è **sottrattivo**: si rimuove codice, si rinominano chiavi, si semplificano rami;
  nessuna nuova entità, nessun nuovo file sorgente (eccezioni esplicitamente indicate)
- Ordine di implementazione: Fase 0 → Fase 1 (fondamenta kit) → Fase 2 (consumatori sertor) →
  Fase 3 (US3 skill requirements) → Fase 4 (US4 mapping upstream + idempotenza) →
  Fase 5 (non-regressione Claude) → Fase 6 (documentazione + migrazione) → Fase 7 (polish)

---

## Fase 0 — Setup & ricognizione (2 task)

Verifica che la baseline sia verde prima di toccare qualsiasi sorgente. Nessun codice prodotto.

- [x] **T-000** Verificare che la suite dei tre pacchetti sia verde sul branch corrente.
  Comando: `uv run pytest packages/sertor-install-kit packages/sertor packages/sertor-flow -m "not cloud" -q`.
  Blocco se fallisce: investigare prima di procedere (baseline di non-regressione).

- [x] **T-001** Eseguire il lint iniziale sui tre pacchetti.
  Comando: `uv run ruff check packages/`.
  Blocco se fallisce: correggere gli errori preesistenti prima del refactor (baseline ruff pulita).

---

## Fase 1 — Fondamenta: rimozione `AssistantId.COPILOT` dal kit condiviso (US1/P1)

Questa fase modifica il **seam condiviso** (`sertor-install-kit`). È il prerequisito di tutte le
fasi successive: la rimozione dell'enum value `COPILOT` propaga ai consumatori per costruzione del
tipo. I task **T-100**, **T-110**, **T-120** sono indipendenti tra loro e parallelizzabili.

**Dipendenza**: Fase 0 completata.

### T-100 Rimozione `AssistantId.COPILOT` dall'enum e dal profilo [P]

File da modificare:
- `packages/sertor-install-kit/src/sertor_install_kit/assistant.py`

Compito:
- [x] Rimuovere il membro `COPILOT = "copilot"` (riga ~25) da `AssistantId`. Dopo la rimozione
  `set(AssistantId) == {CLAUDE, COPILOT_CLI}`. Nessuna altra modifica all'enum (data-model §1).
- [x] Eliminare l'intero ramo `if assistant is AssistantId.COPILOT:` in `for_assistant`
  (righe ~156-176), inclusi: path `.vscode/mcp.json`, root-key `servers`, prefisso `.github/prompts`,
  `command_vehicle=PROMPT_FILE`. Restano i rami `CLAUDE` e `COPILOT_CLI`; il `else` difensivo
  rimane (data-model §2).
- [x] **Non** toccare `CommandVehicle.PROMPT_FILE`, `CommandVehicle.CUSTOM_AGENT`,
  `render_prompt_file` in `surfaces.py`: non sono VS-Code-specifici (research §Nodo 1,
  data-model §3). `surfaces.py` resta invariato.

Effetto: `from_str("copilot")` ora cade nel `except ValueError` esistente (riga ~32-37)
→ `ConfigError` che elenca i validi `claude, copilot-cli` (FR-001). Nessuna logica nuova (research §Nodo 1).

---

### T-110 Test del seam `AssistantId` post-rimozione [P]

File da modificare:
- `packages/sertor-install-kit/tests/unit/test_assistant.py`

Compito (azioni sottrattive + aggiunta di un test):
- [x] Rimuovere `test_assistant_id_known_values`: la parametrizzazione su `COPILOT` non è più valida
  → riscrivere con `(CLAUDE, COPILOT_CLI)` e asserire che `len(list(AssistantId)) == 2`.
- [x] Rimuovere `test_copilot_profile_targets` (~riga 58-66) e `test_copilot_render_paths_are_github`
  (~riga 69-74): coprono il profilo VS Code rimosso.
- [x] Rimuovere `test_copilot_vscode_command_stays_prompt_file` (~riga 122-125): profilo rimosso.
- [x] Aggiornare il loop di validità (~riga 137) affinché iteri solo su `(CLAUDE, COPILOT_CLI)`.
- [x] **Aggiungere** `test_copilot_legacy_value_raises`: `from_str("copilot")` solleva `ConfigError`
  e il messaggio nomina `copilot-cli` (FR-001, C1.1, SC-001).
- [x] Conservare `test_command_vehicle_per_target` (~riga 104-106): verificare che per `COPILOT_CLI`
  il `command_vehicle` è `CUSTOM_AGENT` (FR-012, SC-003 parziale).
- [x] **Aggiungere** `test_copilot_cli_profile_mcp_target`: per `COPILOT_CLI`, `for_assistant`
  risolve `target_for(MCP_SERVER)` su `.mcp.json` con root-key `mcpServers` (FR-008, C2.1).
- [x] **Aggiungere** `test_copilot_cli_no_vscode_mcp`: per `COPILOT_CLI`, nessun path `.vscode/**`
  nel profilo (FR-002, SC-004).

Criteri di riferimento: SC-001, SC-004, SC-010.

---

### T-120 Test `mcp_merge` kit — rimozione root-key `servers` VS Code [P]

File da modificare:
- `packages/sertor-install-kit/tests/unit/test_mcp_merge.py`

Compito:
- [x] Rimuovere i test parametrizzati che esercitano la root-key `servers` (VS Code): quella
  root-key non è più raggiungibile da alcun profilo. Restano i test su `mcpServers` (CLI).
- [x] Verificare che i test rimanenti coprano `mcpServers` per `COPILOT_CLI` (invariato da FEAT-011).

Criteri di riferimento: SC-004, SC-010.

---

## Fase 2 — Consumatori `sertor`: semplificazione rami `is_copilot` e help (US1/US2/P1)

Questa fase opera sul pacchetto `packages/sertor`. I task **T-200**, **T-210**, **T-220** sono
parallelizzabili tra loro. Dipendono tutti dalla Fase 1 (il tipo `AssistantId` è già ristretto).

**Dipendenza**: Fase 1 completata (T-100 verde).

### T-200 `install_rag.py` — semplificazione `is_copilot` e rimozione `is_vscode` [P]

File da modificare:
- `packages/sertor/src/sertor_installer/install_rag.py`

Compito:
- [x] Sostituire ogni occorrenza di `assistant in (AssistantId.COPILOT, AssistantId.COPILOT_CLI)`
  (o variante `is_copilot`) con `assistant is AssistantId.COPILOT_CLI` (~righe 138-141, 159,
  191-194): semplificazione della condizione, non cambio logico per `COPILOT_CLI`.
- [x] Rimuovere il sotto-ramo che distingue `COPILOT` (VS Code) da `COPILOT_CLI` ovunque si
  trovasse dentro la condizione `is_copilot` (~righe 249-253): `is_vscode` e la costante `servers`
  sono ora codice irraggiungibile — rimuoverli. Solo `root_key="mcpServers"` resta.
- [x] Rimuovere le costanti `is_vscode` e il ramo `servers` (~righe 459-460): irraggiungibili dopo
  la rimozione del profilo VS Code.
- [x] Rimuovere la nota `[ASSUNTO-VSC]` (~righe 368-374): si riferisce al profilo rimosso.
- [x] **Non** modificare alcun ramo `is COPILOT_CLI` né logica del profilo CLI: questi rami restano
  invariati (FR-017, non-regressione `copilot-cli`).

---

### T-210 `install_wiki.py` — rimozione rami VS Code e semplificazione [P]

File da modificare:
- `packages/sertor/src/sertor_installer/install_wiki.py`

Compito:
- [x] Rimuovere `_build_copilot_wiki_plan` (o il ramo VS Code al suo interno) che produceva il
  `SessionStart` di tipo `command` (VS Code) e referenziava `wiki-session-start.ps1` come script
  da inviare via hook `command` (~righe 108-159): quel percorso era specifico di VS Code.
- [x] Semplificare il branching in `_build_copilot_wiki_plan` (se il nome resta) affinché
  gestisca solo `COPILOT_CLI` (~righe 217-277): nessuna biforcazione per-target dentro la funzione.
- [x] Rimuovere o semplificare il ramo script `wiki-session-start.ps1` per VS Code
  (~righe 254-258): la versione CLI usa il proprio hook nativo, già FEAT-011.
- [x] Rimuovere la nota `[ASSUNTO-VSC]` e il gap documentato sul SessionStart VS Code (~righe
  398-399): il target VS Code non esiste più.
- [x] Aggiornare `_command_vehicle` e `sertor_owned_paths` per `copilot-cli` (~righe 429-430):
  rimuovere eventuali riferimenti al percorso `.github/prompts` per VS Code; il percorso owned
  ora è solo `.github/agents/` per i COMMAND.

---

### T-220 `__main__.py` sertor — aggiornamento help `--assistant` [P]

File da modificare:
- `packages/sertor/src/sertor_installer/__main__.py`

Compito:
- [x] Aggiornare il testo help del flag `--assistant` per tutti i sottocomandi (install wiki, install
  rag, upgrade, uninstall, ~righe 84-86, 98-101, 196-198): rimuovere la parte `| copilot (VS Code)`
  o similari; il testo deve mostrare esattamente `claude | copilot-cli` (FR-005, FR-007, SC-002).
- [x] Verificare che la validazione rimanga via `from_str` (non `argparse choices`): il comportamento
  su `copilot` legacy è già garantito da T-100 via `ConfigError` con exit 1 (C1.1).
- [x] **Non** aggiungere `choices` argparse per `--assistant` in `sertor`: la validazione è nel seam
  (diversamente da `sertor-flow` che usa `choices`, data-model §6).

---

### T-230 Test `sertor` — aggiornamento suite `install_rag_copilot` e `install_wiki_copilot`

File da modificare:
- `packages/sertor/tests/test_install_rag_copilot.py`
- `packages/sertor/tests/test_install_wiki_copilot.py`
- `packages/sertor/tests/test_install_rag_copilot_cli.py` (già esistente, da completare)

Compito per `test_install_rag_copilot.py`:
- [x] **Eliminare** il file o convertirlo: il file era parametrizzato su `AssistantId.COPILOT`
  (VS Code). Rimuovere i test che assumono `.vscode/mcp.json`, root-key `servers`, profilo VS Code
  (research §Nodo 4 tabella prima riga).
- [x] Verificare che `test_install_rag_copilot_cli.py` (già esistente) copra: `.mcp.json`/`mcpServers`
  presente, `.vscode/mcp.json` assente, hook nativi, anti-bypass, C2.1/C2.2/C2.3.
- [x] **Aggiungere** in `test_install_rag_copilot_cli.py` i casi mancanti rispetto all'ex test VS
  Code, se non già presenti: idempotenza (install 2x → stesso `.mcp.json`), non-distruttività,
  segreti vuoti nel template (porting 1:1 dei test rimossi, SC-008).

Compito per `test_install_wiki_copilot.py`:
- [x] Rimuovere i rami/parametrizzazioni su `COPILOT` VS Code (prompt-file SessionStart VS Code,
  path `.github/prompts`). Lasciare o rinominare a `test_install_wiki_copilot_cli.py`.
- [x] Asserire per `COPILOT_CLI`: i COMMAND (`/wiki`, skill `wiki-author`) risolvono a
  `.github/agents/*.agent.md` (custom-agent), **non** `.github/prompts/*.prompt.md` (C2.4, C2.5,
  FR-003, SC-004).
- [x] Asserire che il SessionStart per `COPILOT_CLI` usa `type:"prompt"` (hook nativo Copilot CLI,
  non `type:"command"` VS Code) — comportamento FEAT-011 già attivo.

Criteri di riferimento: SC-001, SC-002, SC-004, SC-008.

---

### T-240 Test `sertor` — aggiornamento guard e suite trasversale

File da modificare:
- `packages/sertor/tests/test_assets_copilot_guard.py`
- `packages/sertor/tests/test_surface_parity.py`
- `packages/sertor/tests/unit/test_owned_paths.py`
- `packages/sertor/tests/test_mcp_merge.py`
- `packages/sertor/tests/test_schema_copilot_frontmatter.py`
- `packages/sertor/tests/test_schema_copilot_hooks.py`
- `packages/sertor/tests/test_hooks_script_copilot.py`

Compito per `test_assets_copilot_guard.py` (FR-019):
- [x] Restringere lo scope a `copilot-cli` soltanto: rimuovere ogni riferimento al profilo VS Code
  nei test di guardia sugli asset. I test verificano solo gli asset per `COPILOT_CLI` (SC-008).

Compito per `test_surface_parity.py`:
- [x] Aggiornare il pivot di parità a `{CLAUDE, COPILOT_CLI}`: rimuovere la riga/colonna `COPILOT`
  (VS Code) dalla matrice; la parità è ora verificata sui due target rimasti (SC-002, SC-010).

Compito per `test_owned_paths.py`:
- [x] Aggiornare i casi parametrizzati su `COPILOT` → `COPILOT_CLI`: l'invariante `plan ⊆ owned`
  si verifica per `COPILOT_CLI`, non più per `COPILOT` (research §Nodo 4 tabella).

Compito per `test_mcp_merge.py` (sertor):
- [x] Rimuovere i test su root-key `servers` (VS Code). Restano solo i test su `mcpServers`.

Compito per `test_schema_copilot_frontmatter.py`, `test_schema_copilot_hooks.py`,
`test_hooks_script_copilot.py`, `test_render_copilot_hooks.py` (kit):
- [x] Verificare che non contengano parametrizzazioni sul profilo VS Code. Rimuovere eventuali
  rami VS Code. I test di schema offline sono validi per `copilot-cli`; nessun'altra modifica
  necessaria se già parametrizzati su `COPILOT_CLI` (research §Nodo 4, ultime righe).

Criteri di riferimento: SC-002, SC-004, SC-008, SC-010.

---

## Fase 3 — US3: Skill `requirements` come custom-agent su `copilot-cli` (P1)

La skill `requirements` in `sertor-flow` è già resa come `Surface.COMMAND` e il seam `copilot-cli`
risolve già `COMMAND → .github/agents/*.agent.md` (research §Nodo 3). L'azione concreta è
**abilitare il target** in `sertor-flow` + copertura test. Dipende da Fase 1.

**Dipendenza**: Fase 1 completata (T-100 verde); Fase 2 in corso o completata (non bloccante per
questa fase, il seam è già disponibile).

### T-300 `sertor-flow __main__.py` — aggiornamento `choices` a `copilot-cli` (breaking)

File da modificare:
- `packages/sertor-flow/src/sertor_flow/__main__.py`

Compito:
- [x] Aggiornare `choices=["claude","copilot"]` → `choices=["claude","copilot-cli"]` per tutti i
  sottocomandi che accettano `--assistant`: `install`, `upgrade`, `uninstall` (~righe 46-49, 59-62).
  Questa è la **breaking change voluta** (Q4=a): `copilot` non è più un valore valido (FR-006,
  SC-002). Con argparse `choices`, passare `copilot` produce exit 2 con messaggio che elenca
  `{claude, copilot-cli}` (C1.1 per sertor-flow).
- [x] Verificare che il default rimanga `claude` per tutti i verbi (data-model §6).

---

### T-310 `install_governance.py` — rimozione nota VS Code e aggiornamento assistant check

File da modificare:
- `packages/sertor-flow/src/sertor_flow/install_governance.py`

Compito:
- [x] Rimuovere o aggiornare il check `if assistant == "copilot"` / nota `[ASSUNTO-VSC]`
  (~righe 295-302): con il target VS Code rimosso, quella condizione è irraggiungibile. Rimuovere
  il ramo morto. Se esiste logica per `copilot-cli` (FEAT-011), mantenerla invariata.
- [x] Verificare che `_SERTOR_AUTHORED` (~righe 83-91) includa la skill `requirements` come
  `Surface.COMMAND` e che non produca prompt-file per `copilot-cli` (il meccanismo del seam già
  garantisce `CUSTOM_AGENT` → `.github/agents/requirements.agent.md`).
- [x] **Non** aggiungere rami per-assistente: il comportamento corretto emerge dal profilo (Nodo 3,
  Principio X).

---

### T-320 Test governance `copilot-cli` — verifica skill `requirements` come custom-agent

File da modificare:
- `packages/sertor-flow/tests/test_install_governance_copilot.py`

Compito (azioni sottrattive + conservazione dei test CLI esistenti):
- [x] Rimuovere la fixture `installed_copilot` (VS Code) e tutti i test che la usano:
  `test_requirements_skill_is_prompt_file` e `test_specify_launched_with_copilot` (versione VS Code).
  (research §Nodo 4 terza riga tabella)
- [x] **Conservare** la fixture `installed_copilot_cli` e i 3 test FEAT-011 (~righe 114-139):
  `test_requirements_custom_agent_present`, `test_requirements_prompt_file_absent`,
  `test_cli_command_body_reused_from_canonical` (anti-drift). Questi test soddisfano FR-009,
  FR-010, FR-011, SC-003.
- [x] **Aggiungere** `test_specify_launched_with_copilot_cli`: verifica che con `assistant="copilot-cli"`
  il lancio dello specify upstream usi `--ai copilot` (non `copilot-cli`) — questa asserzione si
  sposta qui da T-410 (research §Nodo 4 terza riga: "aggiungere un test che `--ai copilot` è passato
  per `copilot-cli`"). Usa `FakeSpecifyRunner` offline.
- [x] **Aggiungere** `test_legacy_copilot_rejected_by_sertor_flow`: chiamare
  `sertor-flow install --assistant copilot --target <tmp>` → exit 2, messaggio nomina `copilot-cli`
  (FR-001, SC-001). Test CLI con `capsys`.

Criteri di riferimento: SC-001, SC-002, SC-003, SC-004, SC-008.

---

## Fase 4 — US4: Mapping upstream `copilot-cli → --ai copilot` e idempotenza (P1)

Questa fase modifica `speckit_launch.py` in `sertor-flow`: aggiunge la mappa `_SPECKIT_AI_FLAG`
e rinomina la chiave `_EXPECTED_LAYOUT`. Dipende dalla Fase 3 (il target `copilot-cli` deve essere
accettato da `sertor-flow` prima di testare il lancio).

**Dipendenza**: Fase 3 completata (T-300 verde).

### T-400 `speckit_launch.py` — mappa `_SPECKIT_AI_FLAG` e `_EXPECTED_LAYOUT` rinominata

File da modificare:
- `packages/sertor-flow/src/sertor_flow/speckit_launch.py`

Compito:
- [x] Aggiungere la costante `_SPECKIT_AI_FLAG` a livello di modulo (~riga 44, accanto a
  `_SCRIPT_VALUE`):
  ```python
  # Our --assistant value → the --ai value spec-kit 0.8.18 recognizes.
  # spec-kit has NO `copilot-cli`; our CLI target maps to upstream `copilot`
  # (single documented point, FR-015). Update ONLY this map if a future pinned
  # spec-kit adds --ai copilot-cli (VIN-01/A-2).
  _SPECKIT_AI_FLAG = {"claude": "claude", "copilot-cli": "copilot"}
  ```
  (data-model §4, research §Nodo 2, FR-013/FR-015, SC-006)
- [x] In `build_specify_command` (~riga 90): sostituire `profile.assistant` con
  `_SPECKIT_AI_FLAG.get(profile.assistant, profile.assistant)` nell'argomento `--ai`.
  Questo è l'**unico** punto che costruisce `--ai <x>` (verificato da Grep; FR-015, SC-006).
- [x] In `_EXPECTED_LAYOUT` (~righe 55-64): rinominare la chiave `"copilot"` → `"copilot-cli"`,
  mantenendo i **path invariati** (i marker che spec-kit produce per Copilot: `.github/prompts/
  speckit.specify.prompt.md`, `.specify/templates/plan-template.md`). La chiave è il *nostro*
  nome assistente; i path sono quelli *spec-kit* per Copilot (data-model §5, FR-014, SC-007).
- [x] Verificare che la chiave `"copilot"` non compaia più in `_EXPECTED_LAYOUT` (nessuna chiave
  morta).

---

### T-410 Test `speckit_launch.py` — mapping e idempotenza

File da modificare:
- `packages/sertor-flow/tests/test_speckit_launch.py`

Compito:
- [x] **Aggiungere** `test_build_specify_command_copilot_cli_uses_ai_copilot`:
  `build_specify_command` con `profile.assistant == "copilot-cli"` → la lista comando contiene
  `"--ai"` seguito da `"copilot"` (non `"copilot-cli"`). Usa solo oggetti Python, nessun processo
  (C3.1, FR-013, SC-006).
- [x] **Aggiungere** `test_build_specify_command_claude_uses_ai_claude`:
  con `profile.assistant == "claude"` → contiene `"--ai", "claude"` (C3.2, non-regressione).
- [x] **Aggiungere** `test_speckit_ai_flag_single_symbol`:
  verifica che `_SPECKIT_AI_FLAG` sia un `dict` con esattamente le chiavi `{"claude", "copilot-cli"}`
  (C3.3, FR-015, SC-006 — unico punto documentato).
- [x] **Aggiungere** `test_expected_layout_has_copilot_cli_key`:
  `_EXPECTED_LAYOUT` contiene la chiave `"copilot-cli"` e **non** la chiave `"copilot"` (data-model
  §5, FR-014).
- [x] **Aggiungere** `test_launch_speckit_idempotent_copilot_cli`:
  `launch_speckit` eseguito due volte sullo stesso ospite con `copilot-cli` (ospite già
  inizializzato, layout presente): la seconda chiamata ritorna `Outcome.SKIPPED` senza lanciare
  di nuovo `specify init` (C3.4, FR-014, SC-007). Usa `FakeSpecifyRunner` offline.
- [x] Rimuovere eventuali test parametrizzati sulla chiave `"copilot"` di `_EXPECTED_LAYOUT`
  (chiave rinominata, non più valida).

Criteri di riferimento: SC-006, SC-007.

---

## Fase 5 — US5: Non-regressione Claude (gate duro, P1)

Questa fase aggiunge i test espliciti di non-regressione Claude. La logica del target `claude` non
viene toccata dal refactor; questa fase verifica formalmente l'invariante. È parallelizzabile con
le Fasi 3 e 4 dopo la Fase 1.

**Dipendenza**: Fase 1 completata (T-100 verde).

### T-500 Test non-regressione Claude — suite esistente + gate esplicito [P]

File da modificare/consultare:
- `packages/sertor/tests/` (suite esistente)
- `packages/sertor-flow/tests/` (suite esistente)
- `packages/sertor-install-kit/tests/unit/test_assistant.py`

Compito:
- [x] Eseguire la suite esistente filtrata sul target `claude`:
  `uv run pytest packages/sertor packages/sertor-flow -k claude -q`.
  Atteso: verde senza modifiche alla logica di test (FR-016, SC-005, C4.2). Se fallisce,
  il refactor ha introdotto una regressione: blocco assoluto.
- [x] **Aggiungere** in `packages/sertor-install-kit/tests/unit/test_assistant.py`:
  `test_claude_profile_invariant_after_refactor` — `for_assistant(CLAUDE)` produce lo stesso
  profilo di prima: `_command_dir=".claude/commands"`, `command_vehicle=PROMPT_FILE`,
  `_mcp_target=".mcp.json"` con `root_key="mcpServers"` (C4.1, FR-016, SC-005).
- [x] **Aggiungere** in `packages/sertor/tests/test_surface_parity.py` (o nuovo file
  `test_non_regression_claude.py`): `test_claude_artifacts_unchanged` — eseguire
  `sertor install rag --assistant claude` e `sertor install wiki --assistant claude` su un
  `tmp_path`; verificare che gli artefatti prodotti siano identici a quelli del target `claude`
  documentati nei test esistenti (path e contenuto). Usa `FakeCommandRunner` offline.
- [x] Verificare che `packages/sertor-flow/tests/integration/test_install_governance.py`
  (claude) rimanga verde senza modifiche (non toccare la logica di test).

Criteri di riferimento: SC-005, SC-010.

---

## Fase 6 — US6/US7: Documentazione e nota di migrazione (P2)

Questa fase modifica esclusivamente la documentazione utente. Non dipende da fasi specifiche di
codice (può partire in parallelo con le Fasi 2-5 non appena la Fase 1 è chiusa), ma per coerenza
si posiziona dopo il completamento del codice. I task **T-600** e **T-610** sono parallelizzabili.

**Dipendenza**: Fase 1 completata; idealmente Fase 2-5 verdi (documentazione allineata al codice finale).

### T-600 `docs/install-copilot.md` — unico percorso CLI + nota di migrazione [P]

File da modificare:
- `docs/install-copilot.md`

Compito:
- [x] Rimuovere la sezione "Pick your Copilot target" (tabella a due righe `copilot | copilot-cli`):
  rimane un solo percorso con `--assistant copilot-cli` ovunque (FR-020, SC-009).
- [x] Aggiornare tutti gli esempi di comando: `--assistant copilot` → `--assistant copilot-cli`
  (FR-020).
- [x] Aggiungere una sezione "Migrating from the VS Code target" (in coda o dopo l'intro, FR-022):
  - Spiega che il target VS Code (`copilot`) è stato consolidato in `copilot-cli`.
  - Indica come percorso di aggiornamento: ri-eseguire `sertor install ... --assistant copilot-cli`
    sullo stesso ospite.
  - Chiarisce che la rimozione di eventuali artefatti VS Code residui (`.vscode/mcp.json`) è
    manuale — nessuna logica automatica (Q3=a, SC-009).

Criteri di riferimento: SC-009.

---

### T-610 `docs/install.md` e `packages/sertor/docs/install.md` — valori allineati [P]

File da modificare:
- `docs/install.md`
- `packages/sertor/docs/install.md`

Compito:
- [x] Aggiornare la tabella §9 (o equivalente) dei target supportati: rimuovere la riga per
  `--assistant copilot` (VS Code); l'insieme valori diventa esattamente `claude|copilot-cli`
  (FR-021, SC-009).
- [x] Aggiornare tutti gli esempi con `--assistant copilot` → `--assistant copilot-cli`.
- [x] Rimuovere la nota di scope "sertor-flow supports claude|copilot" (ora `claude|copilot-cli`).
- [x] Aggiungere un rimando alla nota di migrazione in `docs/install-copilot.md` (T-600)
  (research §Nodo 5, SC-009).
- [x] Verificare la coerenza tra i due file (`docs/install.md` e il mirror
  `packages/sertor/docs/install.md`): devono essere allineati (research §Nodo 5 terzo intervento).

Criteri di riferimento: SC-009.

---

## Fase 7 — Polish: cross-cutting e gate finali (P2)

I task di questa fase sono **indipendenti tra loro** e parallelizzabili. Dipendono dal completamento
delle Fasi 1-6.

**Dipendenza**: Fasi 0-6 completate.

### T-700 Gate non-regressione finale — suite completa dei tre pacchetti [P]

Compito:
- [x] Eseguire la suite completa: `uv run pytest packages/sertor-install-kit packages/sertor packages/sertor-flow -m "not cloud" -q`.
  Atteso: verde. Nessun test cita più `AssistantId.COPILOT` (VS Code) — verificabile con
  `uv run grep -r "AssistantId.COPILOT[^_]" packages/` (deve tornare vuoto).
- [x] Verificare che il numero di test non sia diminuito rispetto alla baseline (Fase 0) senza
  sostituzione equivalente: ogni test rimosso ha un equivalente `copilot-cli` (SC-008).

Criteri di riferimento: SC-005, SC-008, SC-010.

---

### T-710 Verifica assenza residui VS Code nel codice sorgente [P]

Compito:
- [x] Verificare con Grep che nessun file sorgente (esclusi i file di test rimossi e `tasks.md`)
  contenga riferimenti al profilo VS Code rimosso:
  - `AssistantId.COPILOT` (non seguito da `_CLI`) → 0 occorrenze in sorgenti
  - `.vscode/mcp.json` → 0 occorrenze in sorgenti (solo doc migrazione ammessa)
  - `servers` come root-key MCP → 0 occorrenze (solo `mcpServers`)
  - `CommandVehicle.PROMPT_FILE` in rami Copilot → 0 occorrenze (può restare per Claude/default)
  File da escludere dalla verifica: `specs/`, `wiki/`, `docs/install-copilot.md` (nota migrazione),
  `.git/`.

Criteri di riferimento: SC-001, SC-004, SC-010.

---

### T-720 Verifica `sertor-core` invariato [P]

Compito:
- [x] Verificare che nessuna modifica sia stata apportata a `src/sertor_core/` durante il refactor
  (C5.1, NFR-03, SC-010):
  - `git diff HEAD -- src/sertor_core/` deve essere vuoto.
  - Il toolkit `sertor-install-kit` non importa da `sertor_core` (già garantito da VIN-04;
    verificare con `uv run python -c "import sertor_install_kit"` senza il pacchetto `sertor-core`
    installato, o tramite `test_no_core_dependency.py` già esistente).

Criteri di riferimento: SC-010.

---

### T-730 Lint finale [P]

Compito:
- [x] Eseguire `uv run ruff check packages/` — zero errori (line-length 100, regole E/F/I/UP/B).
  Correggere eventuali warning introdotti dalla rimozione di simboli importati ma non più usati
  (es. `COPILOT` importato da un consumatore) o da import orfani dopo la semplificazione dei rami.

---

### T-740 Verifica help CLI — naming uniforme `claude|copilot-cli` [P]

Compito:
- [x] **Aggiungere** `test_sertor_help_assistant_choices`:
  in `packages/sertor/tests/test_cli.py` (o file dedicato): per tutti i sottocomandi che accettano
  `--assistant` (`install rag`, `install wiki`, `upgrade`, `uninstall`), `main([<cmd>, "--help"])`
  produce output che contiene `copilot-cli` e **non** contiene `copilot (VS Code)` (FR-005, FR-007,
  SC-002).
- [x] **Aggiungere** `test_sertor_flow_help_assistant_choices`:
  per tutti i sottocomandi di `sertor-flow` (`install`, `upgrade`, `uninstall`), `main(["<cmd>",
  "--help"])` produce output che contiene `{claude,copilot-cli}` o `claude | copilot-cli` e **non**
  contiene `copilot` come valore a sé stante (FR-006, SC-002).

Criteri di riferimento: SC-002.

---

## Grafo delle dipendenze (sintesi)

```
Fase 0 (T-000, T-001)
    └─▶ Fase 1 [P]: T-100 → T-110, T-120
           │
           ├─▶ Fase 2 [P]: T-200, T-210, T-220 → T-230, T-240
           │
           ├─▶ Fase 3: T-300 → T-310 → T-320
           │        └─▶ Fase 4: T-400 → T-410
           │
           └─▶ Fase 5 [P]: T-500 (gate Claude, parallelizzabile con Fasi 2-4)
                    │
                    └─▶ (tutte convergono) ─▶ Fase 6 [P]: T-600, T-610
                                                      └─▶ Fase 7 [P]: T-700, T-710, T-720, T-730, T-740
```

**Parallelismi sfruttabili:**
- Fase 1: T-110 e T-120 parallelizzabili dopo T-100 (enum rimosso).
- Fase 2: T-200, T-210, T-220 parallelizzabili; T-230, T-240 dopo i rispettivi sorgenti.
- Fase 5 (non-regressione Claude): parallelizzabile con Fasi 2-4 dopo la Fase 1.
- Fase 6: T-600 e T-610 parallelizzabili tra loro.
- Fase 7: tutti i task `[P]` indipendenti tra loro.

---

## Strategia MVP / incrementale

**MVP verificabile dopo Fasi 0+1+2** (US1 + US2 parziale):
- `AssistantId.COPILOT` rimosso: `from_str("copilot")` → `ConfigError` esplicito con exit 1.
- `sertor install rag|wiki --assistant copilot` rifiutato con errore nominante.
- Nessun artefatto VS Code prodotto da nessun target.
- Help `sertor` mostra `claude | copilot-cli`.

**Valore P1 completo dopo Fasi 0+1+2+3+4+5**:
- US1: target VS Code rimosso, errore esplicito sul legacy.
- US2: naming uniforme `claude|copilot-cli` su `sertor` e `sertor-flow`.
- US3: skill `requirements` è custom-agent su `copilot-cli`.
- US4: mapping `_SPECKIT_AI_FLAG` + idempotenza `_EXPECTED_LAYOUT` preservata.
- US5: non-regressione Claude — gate verde.
- Suite dei tre pacchetti verde, lint pulito.

**Valore P2 completo dopo Fase 6**:
- US6: nota di migrazione inline in `docs/install-copilot.md`.
- US7: documentazione allineata a `claude|copilot-cli` ovunque.

**Fase 7** non blocca il P1/P2 ma è richiesta per chiudere la feature (gate finale).

---

## Riepilogo task per fase

| Fase | Descrizione | Task | US/Priority |
|------|-------------|-----:|:-----------:|
| 0 | Setup & verifica baseline | 2 | — |
| 1 | Fondamenta kit: rimozione `COPILOT` (seam + test kit) | 5 | US1/P1 |
| 2 | Consumatori `sertor`: semplificazione rami + test | 6 | US1/US2/P1 |
| 3 | US3 skill `requirements` come custom-agent su CLI | 3 | US3/P1 |
| 4 | US4 mapping upstream + idempotenza `_EXPECTED_LAYOUT` | 2 | US4/P1 |
| 5 | US5 non-regressione Claude (gate duro) | 1 | US5/P1 |
| 6 | US6/US7 documentazione + nota migrazione | 2 | US6/US7/P2 |
| 7 | Polish: gate finali, lint, verifica residui, help | 5 | cross-cutting |
| **Tot.** | | **26** | |

> Nessun task bloccato da dipendenze esterne. L'intero P1 (Fasi 0-5) è autocontenuto.
> Il P2 (Fase 6) richiede solo la documentazione. La Fase 7 chiude i gate finali.
