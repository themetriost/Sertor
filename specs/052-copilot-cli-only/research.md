# Phase 0 — Research: consolidamento Copilot CLI-only (FEAT-012)

**Branch**: `052-copilot-cli-only` | **Spec**: [spec.md](./spec.md) | **Data**: 2026-06-17

Le decisioni di *cosa/perché* (Q1–Q4) sono chiuse a monte (requirements §10). Questo documento risolve
i **cinque nodi di *come*** rinviati dalla spec a `/speckit-plan` (spec §Assumptions, ultimo punto). Ogni
nodo: Decision / Rationale / Alternatives, ancorato al codice reale (`path:lineno`).

> **Nota di processo (segnalata, non bloccante):** lo script `.specify/scripts/powershell/setup-plan.ps1`
> e la skill `.claude/skills/speckit-plan/SKILL.md` **sono ASSENTI** nel repo (verificato:
> `ls .specify/scripts/powershell/` → vuoto; `.claude/skills/speckit-plan/` inesistente). Parametri
> ricavati per convenzione dal branch attivo: `FEATURE_SPEC=specs/052-copilot-cli-only/spec.md`,
> `IMPL_PLAN=specs/052-copilot-cli-only/plan.md`, `SPECS_DIR=specs/052-copilot-cli-only/`,
> `BRANCH=052-copilot-cli-only`. Nessun hook SpecKit eseguito (coerente con lo storico FEAT-003/051).
>
> **MCP `sertor-rag`:** non interrogato per questo design — il lavoro è interamente sui pacchetti
> installer (codice locale già letto integralmente con `Read`/`Grep`), non sul corpus dogfood. Nessun
> errore MCP da segnalare perché nessun tool MCP è stato invocato.

---

## Mappa delle superfici toccate (ancoraggio)

Lettura integrale dei file rilevanti. Punti dove vive oggi il target VS Code (`AssistantId.COPILOT`):

| File | Cosa contiene di VS-Code-specifico |
|------|------------------------------------|
| `packages/sertor-install-kit/src/sertor_install_kit/assistant.py:25` | enum value `COPILOT = "copilot"` |
| `…/assistant.py:156-176` | ramo `for_assistant(COPILOT)` → `.vscode/mcp.json` (`servers`), `.github/prompts` (`.prompt.md`), `command_vehicle=PROMPT_FILE` |
| `…/assistant.py:53-64,108,175` | `CommandVehicle.PROMPT_FILE` (resta: lo usa Claude di default) |
| `…/surfaces.py:41-51` | `render_prompt_file` (resta nel kit, ma diventa non più richiamato dai renderer) |
| `packages/sertor/src/sertor_installer/install_rag.py:138-141,159,191-194,249-253,368-374,391-394,459-460,549` | rami `is_copilot` (= COPILOT∪COPILOT_CLI), `is_vscode`/`servers`, nota `[ASSUNTO-VSC]` |
| `packages/sertor/src/sertor_installer/install_wiki.py:108-159,217-277,398-399,429-430` | `_build_copilot_wiki_plan`, SessionStart VS Code (`command`), script `wiki-session-start.ps1`, nota gap, `_command_vehicle` |
| `packages/sertor/src/sertor_installer/__main__.py:84-86,98-101,196-198` | help `… | copilot (VS Code) | copilot-cli` su wiki/rag/lifecycle |
| `packages/sertor-flow/src/sertor_flow/__main__.py:46-49,59-62` | `choices=["claude","copilot"]` su install/upgrade/uninstall |
| `packages/sertor-flow/src/sertor_flow/install_governance.py:83-91,295-302` | `_SERTOR_AUTHORED` (skill `requirements` COMMAND), nota `[ASSUNTO-VSC]` su `assistant=="copilot"` |
| `packages/sertor-flow/src/sertor_flow/speckit_launch.py:55-64,90` | `_EXPECTED_LAYOUT["copilot"]`, `--ai profile.assistant` |
| Test: `test_install_rag_copilot.py`, `test_install_wiki_copilot.py`, `test_install_governance_copilot.py`, `test_assistant.py`, `test_surface_parity.py`, `test_owned_paths.py`, `test_assets_copilot_guard.py`, `test_schema_copilot_*.py` | parametrizzati su `AssistantId.COPILOT` / `assistant="copilot"` |
| Docs: `packages/sertor/docs/install.md`, `docs/install-copilot.md`, `docs/install.md` | tabella target, esempi `--assistant copilot`, righe §9 |

---

## Nodo 1 — Forma della rimozione di `AssistantId.COPILOT` (FR-004, REQ-004; Q1=a)

### Decision

**Rimozione totale e dichiarativa**, in tre cerchi concentrici dal seam verso i consumatori:

1. **Enum** (`assistant.py:25`): eliminare il membro `COPILOT = "copilot"`. `AssistantId` resta
   `{CLAUDE, COPILOT_CLI}`. `from_str("copilot")` ora cade nel `except ValueError` (riga 33) →
   `ConfigError` che elenca i valori validi (`claude, copilot-cli`) — è esattamente l'errore esplicito
   nominante richiesto da FR-001/REQ-001/REQ-008. **Nessuna logica nuova**: il comportamento "solleva su
   `copilot`" emerge per costruzione dalla rimozione del membro.
2. **Profilo** (`assistant.py:156-176`): eliminare l'intero ramo `if assistant is AssistantId.COPILOT:`.
   Restano solo i rami `CLAUDE` e `COPILOT_CLI`. `for_assistant` non può più ricevere `COPILOT` (non
   esiste come valore), quindi nessun ramo morto.
3. **Consumatori** (rami `is_copilot`/`_build_copilot_*`): la condizione
   `assistant in (AssistantId.COPILOT, AssistantId.COPILOT_CLI)` si **semplifica** in
   `assistant is AssistantId.COPILOT_CLI`. Si **eliminano** i sotto-rami `if assistant is
   AssistantId.COPILOT:` (es. `install_wiki.py:254-258` script SessionStart VS Code;
   `install_wiki.py:398-399`, `install_rag.py:368-374` note `[ASSUNTO-VSC]`;
   `install_governance.py:295-302` nota VS Code). Le costanti `is_vscode`/`servers`
   (`install_rag.py:249-253,459-460`) diventano **codice irraggiungibile** perché nessun profilo
   risolve più la superficie MCP su `.vscode/mcp.json` → si rimuovono, lasciando solo
   `root_key="mcpServers"` (la chiave-radice del profilo CLI, già `mcpServers`).

**`CommandVehicle.PROMPT_FILE` e `render_prompt_file` RESTANO nel kit.** Non sono VS-Code-specifici:
`PROMPT_FILE` è il `command_vehicle` di **default** e quello di **Claude** (`assistant.py:108`); per
Claude però il vehicle non innesca mai `render_prompt_file` (Claude tiene il layout byte-copy
`.claude/**` via `_file_prefix`). Dopo la rimozione di COPILOT **nessun plan produce più `.prompt.md`**
come COMMAND nostro → `render_prompt_file` resta esportato (API stabile del kit) ma non più *richiamato*
dai renderer di plan. Conforme a FR-003/REQ-003 ("nessun prompt-file come *veicolo dei comandi* per
`copilot-cli`") e a FR-004 ("prompt-file come veicolo dei comandi" rimosso *dai rami VS Code*): il
veicolo COMMAND prompt-file scompare come *risoluzione per Copilot*, la funzione di rendering resta una
primitiva neutra del kit.

### Rationale

- Q1=a impone *zero codice morto né profilo non testato*. Rimuovere il membro enum è il modo più forte:
  rende **impossibile per costruzione** (non solo improbabile) raggiungere il profilo VS Code, e il
  type-checker/test trova ogni call-site rimasto.
- L'errore esplicito nominante non va scritto a mano: cade dal `from_str` esistente (Principio IV già
  cablato, `assistant.py:32-37`). Meno codice, stessa garanzia.
- Semplificare `is_copilot` in `is COPILOT_CLI` invece di lasciare l'unione a due elementi evita che la
  prossima lettura creda esistano ancora due famiglie Copilot (smell di tupla-di-uno).

### Alternatives rejected

- **(b) nascondere senza rimuovere** (membro interno, escluso dalle `choices`): scartata in Q1 — codice
  raggiungibile-ma-non-testato = rottura silenziosa a valle, esattamente il footgun che la feature
  elimina.
- **Mantenere l'unione `(COPILOT, COPILOT_CLI)` con COPILOT eliminato:** lascerebbe `is COPILOT` come
  ramo irraggiungibile → viola "niente codice morto".

---

## Nodo 2 — Punto e forma del mapping `copilot-cli → --ai copilot` + `_EXPECTED_LAYOUT` (FR-013/014/015)

### Decision

**Unico punto, una mappa esplicita commentata in `speckit_launch.py`.** Due interventi co-localizzati:

1. **Mapping upstream** — nuova costante modulo `_SPECKIT_AI_FLAG` accanto a `_SCRIPT_VALUE`
   (`speckit_launch.py:44`):
   ```python
   # Our `--assistant` value → the `--ai` value spec-kit 0.8.18 recognizes. spec-kit has NO
   # `copilot-cli`; our CLI target maps to upstream `copilot` (single documented point, FR-015).
   # If a future pinned spec-kit adds `--ai copilot-cli`, update ONLY this map (VIN-01/A-2).
   _SPECKIT_AI_FLAG = {"claude": "claude", "copilot-cli": "copilot"}
   ```
   In `build_specify_command` (riga 90) si sostituisce `profile.assistant` con
   `_SPECKIT_AI_FLAG.get(profile.assistant, profile.assistant)`. È **l'unico** posto che forma la
   stringa `--ai <x>` (verificato con Grep: nessun altro call-site costruisce `--ai`).

2. **Verifica del layout idempotente** — in `_EXPECTED_LAYOUT` (riga 55-64) **rinominare** la chiave da
   `"copilot"` a `"copilot-cli"` mantenendo i **marker prodotti da spec-kit per il layout Copilot** (lo
   stesso `--ai copilot` deposita `.github/prompts/speckit.specify.prompt.md` + `.specify/…`). La chiave
   del dict è il **nostro** valore di assistente (`profile.assistant == "copilot-cli"`,
   `_expected_layout` riga 67-68); i **path** dentro sono quelli che spec-kit produce per Copilot. Così
   `_layout_present` (riga 71-73) trova davvero il layout al secondo run e non rilancia (idempotenza,
   FR-014/SC-007, mitigazione R-04).

### Rationale

- La spec/requisiti indicano esplicitamente `_SPECKIT_AI_FLAG` come forma preferita (requirements §5
  REQ-015 commento, e Q2 raccomandazione). Una mappa dedicata è più leggibile di un `if` inline e isola
  la policy in un solo posto documentato.
- Il punto chiave dell'idempotency check (R-04, prob. alta): la chiave del dict è il *nostro* nome
  (`copilot-cli`), il valore sono i *marker di spec-kit* (che resta `copilot`). Confondere i due livelli
  è il bug che la spec previene (Edge Cases: "verifica del layout non aggiornata"). La distinzione resta
  esplicita in un commento.
- `_SCRIPT_VALUE` come modello: stesso pattern (mappa nostro→upstream), stessa collocazione → coerenza.

### Alternatives rejected

- **`if profile.assistant == "copilot-cli": ai = "copilot"` inline in build_specify_command:** funziona
  ma sparge la policy; una versione futura di spec-kit con `copilot-cli` richiederebbe di trovarlo a
  mano. La mappa è la "single source" che FR-015 richiede.
- **Aggiungere chiave `_EXPECTED_LAYOUT["copilot-cli"]` SENZA togliere `"copilot"`:** lascerebbe una
  chiave morta (`copilot` non è più un assistente valido). Rinomina diretta (Q4 coerente).

---

## Nodo 3 — Skill `requirements` come custom-agent su `copilot-cli` in `sertor-flow` (FR-009/010/011/012)

### Decision

**Nessuna modifica strutturale a `install_governance.py`: il comportamento corretto emerge dal seam.**
La skill `requirements` è già nel plan come `Surface.COMMAND` (`install_governance.py:89-90`); il
percorso di resa è già delegato al profilo via `aprofile.render_path(surface, name)` (riga 129). Con il
profilo `copilot-cli` (`assistant.py:177-206`, `command_vehicle=CUSTOM_AGENT`, `_command_dir=".github/
agents"`, `_command_suffix=".agent.md"`), `render_path(COMMAND, "requirements")` risolve già
`.github/agents/requirements.agent.md`. Il renderer è scelto per suffisso in `_render_for_target`
(`install_governance.py:186-191`): `.agent.md` → `render_custom_agent` (anti-drift, corpo dal canonico
Claude). **Il meccanismo FEAT-011 del pacchetto `sertor` è già nel kit condiviso e già consumato qui.**

Quindi l'azione concreta del nodo 3 è **solo abilitare il target**: aggiungere `copilot-cli` alle
`choices` di `sertor-flow` (vedi Nodo dipendente §Naming) e **estendere la copertura di test** (Nodo 4).
La verifica che `requirements` su `copilot-cli` produca un custom-agent e non un prompt-file **esiste
già** (`test_install_governance_copilot.py:114-139`, fixture `installed_copilot_cli`). Va **conservata**;
il pezzo da rimuovere è solo il ramo VS Code (`installed_copilot` + `test_requirements_skill_is_prompt_file`).

### Rationale

- Principio X / VIN-05: il seam `AssistantProfile` è l'unico punto che conosce le convenzioni; i
  plan-builder non devono ramificare per-assistente. Il design FEAT-011 ha già reso `copilot-cli` un
  custom-agent producer; FEAT-012 deve solo **renderlo raggiungibile** da `sertor-flow` (oggi
  `choices=["claude","copilot"]` non lo espone).
- Anti-drift (FR-011/NFR-04): `render_custom_agent` riusa il corpo canonico Claude byte-for-byte; il
  test `test_cli_command_body_reused_from_canonical` (già presente, riga 131-139) lo garantisce.

### Alternatives rejected

- **Aggiungere un ramo dedicato `requirements` per copilot-cli in install_governance:** violerebbe
  Principio X (assunzione per-assistente nel corpo del plan-builder) e DRY — il seam fa già il lavoro.

---

## Nodo 4 — Strategia di sostituzione dei test del vecchio target VS Code (FR-017/018/019, SC-008)

### Decision

**Per ciascun file/test parametrizzato su `COPILOT` (VS Code), eliminare il ramo VS Code e garantire un
equivalente `copilot-cli`**, secondo questa tabella di copertura (la "matrice" che chiude R-03/SC-008):

| Test/file VS Code attuale | Azione | Copertura equivalente `copilot-cli` |
|---|---|---|
| `test_install_rag_copilot.py` (intero, helper `_run` su `AssistantId.COPILOT`) | **Eliminare** | `test_install_rag_copilot_cli.py` (già esiste): verifica `.mcp.json`/`mcpServers`, hook nativi, anti-bypass — copre US1/US3 su CLI. **Aggiungere** se mancano: idempotenza, non-distruttività, segreti vuoti (porting 1:1 dei test 62/71/48 cambiando il file MCP atteso) |
| `test_install_wiki_copilot.py` (rami COPILOT) | **Ridurre a `copilot-cli`** | rinominare/riparametrare su `AssistantId.COPILOT_CLI`; asserire `.github/agents/*.agent.md` (non `.prompt.md`) e SessionStart `type:"prompt"` |
| `test_install_governance_copilot.py` | **Togliere** fixture `installed_copilot` + `test_requirements_skill_is_prompt_file` + `test_specify_launched_with_copilot` (riparametrare su `copilot-cli`) | conservare `installed_copilot_cli` + i 3 test FEAT-011 (114-139); **aggiungere** un test che `--ai copilot` è passato per `copilot-cli` (sposta l'asserzione di `test_specify_launched_with_copilot`) |
| `test_assistant.py` (`test_assistant_id_known_values` riga 23; `test_copilot_profile_targets` 58-66; `test_copilot_render_paths_are_github` 69-74; `test_command_vehicle_per_target` 104-106; `test_copilot_vscode_command_stays_prompt_file` 122-125; loop 137) | **Rimuovere le asserzioni su `COPILOT`** | **aggiungere** `test_copilot_legacy_value_raises` (`from_str("copilot")` → `ConfigError` nominante `copilot-cli`); il loop di validità itera `(CLAUDE, COPILOT_CLI)` |
| `test_surface_parity.py` | **Aggiornare** il pivot di parità a `{CLAUDE, COPILOT_CLI}` | parità verificata sui due target rimasti |
| `test_owned_paths.py` | **Aggiornare** i casi parametrizzati su COPILOT → COPILOT_CLI | `plan ⊆ owned` per `copilot-cli` |
| `test_assets_copilot_guard.py` (FR-019/REQ-019) | **Restringere** lo scope a `copilot-cli` | rimuovere ogni riferimento al profilo VS Code |
| `test_schema_copilot_frontmatter.py` / `test_schema_copilot_hooks.py` / `test_render_copilot_hooks.py` / `test_hooks_script_copilot.py` | **Verificare** che non dipendano dal profilo VS Code | sono test di schema offline (FEAT-011 gruppo G): restano validi per `copilot-cli`; rimuovere eventuali parametrizzazioni VS Code |
| `test_mcp_merge.py` (kit + sertor) | **Verificare** | i test su root-key `servers` (VS Code) si rimuovono; restano `mcpServers` |

**Regola operativa (chiude SC-008):** nessun file di test viene cancellato senza che la superficie che
copriva (MCP, hook, COMMAND, INSTRUCTION_BLOCK, anti-bypass) abbia un test equivalente su `copilot-cli`.
La tabella sopra è il manifesto di copertura; `tasks.md` la trasformerà in task 1:1.

### Rationale

- FR-018/SC-008 vietano superfici scoperte. La tabella mappa **superficie → test sopravvissuto/nuovo**,
  non "test → cancellazione". È la mitigazione diretta di R-03 (prob. media: facile dimenticare).
- I test `copilot-cli` esistono già in larga parte (FEAT-011): il lavoro è **sottrattivo** (togliere VS
  Code) + **completivo** (portare i pochi casi unici dei test VS Code, es. non-distruttività MCP).
- NFR-05: tutti offline con `FakeCommandRunner`/`FakeSpecifyRunner` — i test esistenti già lo sono.

### Alternatives rejected

- **Cancellare i test VS Code senza tabella:** rischio R-03 (superficie scoperta). Rifiutato.
- **Lasciare i test VS Code come `xfail`:** mantiene riferimenti a un profilo rimosso (codice morto nei
  test) → contraddice Q1=a.

---

## Nodo 5 — Collocazione della nota di migrazione (FR-020/021/022, SC-009)

### Decision

Tre interventi documentali, con la **nota di migrazione** in `docs/install-copilot.md`:

1. **`docs/install-copilot.md`** — rimuovere la sezione "Pick your Copilot target" (la tabella a due
   righe `copilot | copilot-cli`) e ridurla a un **unico percorso** con `--assistant copilot-cli`; tutti
   gli esempi usano `copilot-cli` (FR-020). In coda (o subito dopo l'intro) una **sezione "Migrating from
   the VS Code target"** (FR-022): spiega il consolidamento, indica come upgrade ri-eseguire
   `--assistant copilot-cli` sullo stesso ospite, e chiarisce che `.vscode/mcp.json` residuo va rimosso
   **a mano** (nessun rilevamento automatico).
2. **`docs/install.md`** (reference, righe 17-19, 425-426, 463-466 ecc.) — l'insieme valori diventa
   esattamente `claude|copilot-cli` (FR-021); rimuovere la riga `--assistant copilot` (VS Code) dalla
   tabella §9, gli esempi `copilot` → `copilot-cli`, e la nota di scope "sertor-flow supports
   claude|copilot" (ora `claude|copilot-cli`).
3. **`packages/sertor/docs/install.md`** — stesso allineamento (è la copia versionata nel pacchetto).

La nota di migrazione vive **inline in `docs/install-copilot.md`** (la doc dedicata a Copilot), perché è
lì che un ex-utente VS Code la cerca; `docs/install.md` la **richiama** con un link.

### Rationale

- FR-022 ammette "inline nella documentazione d'installazione o sezione separata": `install-copilot.md`
  è la sede più scopribile per il pubblico interessato (chi installa per Copilot).
- SC-009 richiede un *unico percorso* + insieme valori esatto + nota presente: i tre interventi lo
  coprono. Coerente con la convenzione del workspace "documentazione utente = `docs/`+README" (memoria).

### Alternatives rejected

- **CHANGELOG/release-note separata:** meno scopribile per chi rilegge la guida d'installazione; la spec
  vuole la nota *nella documentazione d'installazione*.

---

## Tecnologie / vincoli confermati (Technical Context grounding)

- **Linguaggio:** Python ≥ 3.11; pacchetti `sertor`, `sertor-flow`, `sertor-install-kit` (stdlib-only il
  kit, VIN-04). Build hatchling, `uv` workspace.
- **Test:** pytest, offline (`FakeCommandRunner`/`FakeSpecifyRunner`), marker `not cloud` per la CI.
- **`sertor-core` INVARIATO** (NFR-03/SC-010): nessun import né modifica a porte/adapter/composition.
- **Anti-drift:** sorgente canonica `assets/claude/**` + renderer condivisi nel kit (NFR-04/VIN-03).
