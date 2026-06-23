# Tasks — guided-setup (E12-FEAT-002)

**Branch**: `075-guided-setup` · **Generato**: 2026-06-23
**Spec**: [`spec.md`](spec.md) · **Piano**: [`plan.md`](plan.md) · **Dati**: [`data-model.md`](data-model.md)
**Contratti**: [`contracts/skill-guided-setup.md`](contracts/skill-guided-setup.md) ·
[`contracts/agent-concierge.md`](contracts/agent-concierge.md) ·
[`contracts/distribution-parity.md`](contracts/distribution-parity.md)
**Requisiti**: `requirements/usabilita/guided-setup/requirements.md`

> **Nota di processo.** I task marcati `[P]` sono parallelizzabili all'interno della stessa fase
> (nessuna dipendenza reciproca). Il suffisso `→ dipende da` lista i task prerequisiti. Git **mai**
> qui: brief di commit al fondo per il `configuration-manager`.
>
> **Natura del cambiamento: ADDITIVO + scope di distribuzione.** Nessun codice runtime del core,
> nessun motore/porta/comando nuovo. La feature vive in: 2 asset (1 skill + 1 agente) + wiring in
> `install_rag.py` (W1-W7) + estensione guardia/test. `sertor-core` e `sertor-install-kit`
> **invariati** (RNF-7). Il comportamento dei comandi deterministici (`install`/`configure`/`doctor`/
> `index`) è identico a oggi: la skill li orchestra, non li altera.
>
> **Rischi noti da coprire (calibra l'ordine):**
> - **R-1 (CRITICO):** `_render_rag` nel test di parità deve diventare render-aware (G1 del
>   contratto `distribution-parity.md`). Va fatto **prima** di ogni verifica (a)(b)(c) sull'agente:
>   altrimenti il `model: sonnet` del frontmatter Claude potrebbe sfuggire ai check anti-leak su
>   Copilot. Primo task della fase guardia.
> - **R-2:** closure mirata «ogni asset citato per nome dalla skill/agente è depositato». L'agente
>   cita `guided-setup` per nome: la closure file-based non la cattura.
> - **R-3:** `test_no_wiki_artifacts_created` va **ristretto** da «nessun agente» a «nessun agente
>   wiki» (il rag plan ora deposita `concierge` in `agents/`); senza questa modifica il test
>   esistente fallisce.
> - **R-4:** prova LIVE su Claude/Copilot reale = task follow-up **non-bloccante** (segnalato,
>   non parte del done automatico offline).
>
> **Strategia MVP/incrementale.**
> - **Setup** (TASK-S01): nuovo albero asset `assets/rag/agents/`. Prerequisito zero.
> - **Fondazionale A — Skill** (TASK-F01): authoring di `guided-setup/SKILL.md`. Testabile in
>   isolamento; bloccante per il wiring skill.
> - **Fondazionale B — Agente** (TASK-F02): authoring di `concierge.md`. Indipendente da F01
>   [P]; bloccante per il wiring agente.
> - **Storia 8 — Distribuzione dual-target** (P1 Must, TASK-US8-01..04): wiring W1-W7 in
>   `install_rag.py`. Dipende da F01+F02. Primo blocco di copertura CS-5.
> - **Storia 8 — Guardia di parità** (TASK-US8-05..07): estensione `test_assets_copilot_parity.py`
>   (R-1 critico per primo). Dipende da US8-01..04.
> - **Storia 9 — Stub concierge instradamento** (P2 Should, TASK-US9-01): test routing e
>   invariante a-un-ramo. Dipende da F02.
> - **Storie 1-7 — Contenuto skill** (TASK-US1-01..US7-01): verifiche testuali/comportamentali sul
>   body della skill. Dipendono da F01. Parallelizzabili tra loro.
> - **Polish/cross-cutting** (TASK-P01..P04): suite verde, lint, additività, tracciamento scope.
>
> L'ordine di priorità segue: distribuzione dual-target (CS-5, US8, P1 Must) → contenuto skill
> (CS-1..4, US1-7) → stub concierge (US9, P2 Should) → polish.

---

## Fase 0 — Setup: albero `assets/rag/agents/` (1 task)

> Prerequisiti: nessuno. Crea il nuovo albero asset per gli agenti RAG (gemello di
> `sertor-flow/assets/claude/agents/`). Bloccante per TASK-F02.

### TASK-S01 — Crea la directory `assets/rag/agents/` nel bundle `sertor`

**File**: `packages/sertor/src/sertor_installer/assets/rag/agents/` (NUOVA)
→ dipende da: nessuno

- [ ] Crea la cartella `packages/sertor/src/sertor_installer/assets/rag/agents/` (vuota inizialmente;
      accoglierà `concierge.md` nel task TASK-F02).
- [ ] Verifica che la struttura sia coerente con `assets/rag/skills/` (gemella per gli agenti) e
      con `sertor-flow/assets/claude/agents/` (il pattern di riferimento D-0.6/D-1).
- [ ] Verifica che il pacchetto `sertor` includa la nuova cartella nei dati distribuiti
      (`package_data` / `include` in `pyproject.toml` del pacchetto `sertor`): l'albero
      `assets/**` deve coprire anche `agents/`. Se `assets/**` è già un glob ricorsivo, nessuna
      modifica richiesta; altrimenti aggiungere la voce.
- [ ] Test di smoke: `importlib.resources.files("sertor_installer").joinpath("assets/rag/agents")`
      è navigabile senza `FileNotFoundError` (da verificare nel task TASK-F02 dopo aver
      aggiunto `concierge.md`).

---

## Fase 1 — Fondazionale: authoring degli asset (2 task paralleli)

> Prerequisiti: TASK-S01 (albero agents/). I due task F01 e F02 sono **parallelizzabili** [P].
> Bloccanti per tutte le fasi successive (distribuzione, guardia, storie).

### TASK-F01 [P] — Crea `assets/rag/skills/guided-setup/SKILL.md`

**File**: `packages/sertor/src/sertor_installer/assets/rag/skills/guided-setup/SKILL.md` (NUOVO)
→ dipende da: nessuno (non necessita di TASK-S01)

- [ ] Crea la cartella `packages/sertor/src/sertor_installer/assets/rag/skills/guided-setup/`
      (gemella di `assets/rag/skills/eval-suite-author/` e `assets/rag/skills/eval-feedback/`).
- [ ] Scrivi il file `SKILL.md` con il **frontmatter nativo agent-skill** conforme al contratto
      (`contracts/skill-guided-setup.md`):
      ```yaml
      ---
      name: guided-setup
      description: "Guide the user from an unconfigured repo to a verified Sertor RAG (a green
        `sertor-rag doctor`), conversing and orchestrating ONLY the deterministic vehicles
        (`sertor install`, `sertor configure --set`, `sertor-rag doctor`/`index`). Detects current state,
        recommends an embedding provider from context (with confirmation), fills `.env` securely (never
        printing secrets), announces the one-time GloVe download, and verifies fail-loud via `doctor`.
        Read-only checks run freely; every host mutation/download runs only after explicit confirmation.
        It never reimplements a command and never imports the core."
      user-invocable: true
      disable-model-invocation: false
      ---
      ```
- [ ] Scrivi il **body in inglese** (host-agnostico byte-identico, single-file, parità con le eval
      skill). Il body DEVE contenere le 10 sezioni prescritte da `research.md` D-2:
      1. **User Input / When to use** — intento «set up Sertor / configure the RAG».
      2. **Hard boundary** — formule del tipo: *no import of `sertor_core`/`build_*`; every access
         to Sertor goes through a vehicle*; la skill orchestra, non reimplementa (FR-001/FR-013,
         RNF-1). Cita esplicitamente i vehicle ammessi.
      3. **Consent gate** — check read-only (`doctor`, rilevazione `.sertor/.env`) liberi; ogni
         passo mutante (`install`, `configure --set`, `index`/download) proposto e condotto **solo
         dopo conferma esplicita** (FR-008, DA-G3).
      4. **Step 1 — Detect state (read-only).** Lancia `sertor-rag doctor --json`, legge le 4
         aree; se tutte verdi → «già configurato e verificato», si ferma (FR-009, idempotenza).
      5. **Step 2 — Choose provider (euristica + confirm).** Legge i 3 segnali via vehicle/file
         (`doctor --json` per creds, segnale conversazionale per airgapped/NL); propone con
         motivazione; l'utente decide (FR-004/FR-005, DA-G2, D-3).
      6. **Step 3 — Install (on confirm).** `sertor install rag [--assistant <host>]` (FR-001).
      7. **Step 4 — Configure (on confirm, secrets via secure path).** Solo via
         `sertor configure --set KEY=VALUE`; segreti via prompt sicuro, mai stampati; se già
         presenti in `.env` non ri-chiesti né esposti (FR-006, RNF-3, US3).
      8. **Step 5 — Index (on confirm, announce GloVe).** Se provider `glove` e non in cache:
         annuncia download una-tantum (~822 MB) prima di `sertor-rag index .` (FR-007, US4).
      9. **Step 6 — Verify (fail-loud).** `sertor-rag doctor`; PASS → «verificato»; non verde →
         area+rimedio dal report, **non** dichiara successo (FR-002/FR-003, RNF-4, Principio XII).
      10. **What NOT to do.** Non stampare segreti; non riempire `.env` a mano; non eseguire
          mutazioni senza conferma; non importare il core; non dichiarare «fatto» senza `doctor`.
- [ ] Verifica che il body **non contenga**:
      - path `.claude/` (no leak contenitore Claude);
      - slash-command (es. `/wiki`, `/install`);
      - nomi-prodotto/modello Claude (`Claude Code`, `Opus`, `Haiku`, `$ARGUMENTS`, `CLAUDE.md`);
      - import di `sertor_core` o chiamate a `build_*`;
      - provider scelto automaticamente senza step di conferma.
- [ ] Verifica che il body citi i vehicle **per nome di comando** (`sertor install`,
      `sertor configure --set`, `sertor-rag doctor`, `sertor-rag index`) — host-agnostici (FR-010,
      RNF-2, lezione FEAT-001/056).

### TASK-F02 [P] — Crea `assets/rag/agents/concierge.md`

**File**: `packages/sertor/src/sertor_installer/assets/rag/agents/concierge.md` (NUOVO)
→ dipende da: TASK-S01

- [ ] Scrivi il file `concierge.md` nella cartella creata in TASK-S01, con il **frontmatter Claude**
      conforme al contratto (`contracts/agent-concierge.md`):
      ```yaml
      ---
      name: concierge
      description: "Entry point for getting Sertor working: when the user asks to set up / configure /
        install Sertor or get the RAG running, route to the `guided-setup` skill and follow its
        install → configure → verify flow over the deterministic vehicles. Minimal stub with a SINGLE
        branch (setup → guided-setup); the full concierge (other dispatches, proactive checks) is a
        separate future capability."
      tools: Read, Bash, Grep, Glob
      model: sonnet
      ---
      ```
- [ ] Scrivi il **body in inglese** host-agnostico: dispatcher sottile a **un solo ramo** — per
      l'intento «set up / configure / install Sertor» / «get the RAG working»: instrada verso la
      skill `guided-setup` (citata **per nome**, US9/FR-012).
- [ ] Verifica che il body **non contenga**:
      - riferimenti a `config-recommender`, `search-diagnose`, `FEAT-004`, `FEAT-007` o capacità
        non ancora esistenti (US9.2, anti scope-creep);
      - path `.claude/` / slash-command / nomi-prodotto Claude (leak contenitore);
      - `model:` nel body (il pin è solo nel **frontmatter**, non nel body — gestito by-target
        dal renderer, lezione FEAT-011/049).
- [ ] Verifica che il body citi `guided-setup` **per nome** (closure D-5.2: la skill dev'essere
      depositata dal plan prima che l'agente possa riferirla — verificato in TASK-US8-06).
- [ ] Verifica che il `model: sonnet` sia nel frontmatter (pin esplicito richiesto — D-1, preservato
      su Claude, omesso su Copilot da `render_custom_agent`).

---

## Fase 2 — Storia 8: Wiring distribuzione dual-target (P1, Must) (7 task)

> Prerequisiti: TASK-F01 (skill), TASK-F02 (agente). Questa fase implementa i punti W1-W7
> in `install_rag.py`. I task W1-W3 [P] sono indipendenti tra loro (costanti e routing);
> W4 dipende da W3; W5 dipende da W1+W2+W3+W4; W6 e W7 dipendono da W5.

### TASK-US8-01 [P] — W1+W2: Costante `_USABILITY_SKILL_NAMES` e factory `_skill_artifacts` generalizzata

**File**: `packages/sertor/src/sertor_installer/install_rag.py`
→ dipende da: TASK-F01

- [ ] Aggiungi la costante `_USABILITY_SKILL_NAMES = ("guided-setup",)` immediatamente dopo
      `_EVAL_SKILL_NAMES` (D-4/W1). Commento: `# Usability skills (E12)`.
- [ ] Generalizza `_eval_skill_artifacts(is_copilot)` → `_skill_artifacts(names, is_copilot)`
      (D-4/W2, DRY, Principio III): il parametro `names` è una tupla di nomi-skill; genera un
      `Artifact(ArtifactKind.FILE, f"rag/skills/{name}/SKILL.md", f"{base}/{name}/SKILL.md",
      WriteStrategy.CREATE_IF_ABSENT)` per ogni nome (invariato rispetto alla forma eval).
- [ ] Aggiorna il sito di chiamata originale per le eval skill: sostituisci
      `_eval_skill_artifacts(is_copilot)` con `_skill_artifacts(_EVAL_SKILL_NAMES, is_copilot)`.
      **Non-regressione**: il comportamento per le eval skill deve restare identico (stessi artefatti,
      stesso ordine — SC-010).
- [ ] Verifica che nessun import nuovo sia necessario (le costanti/tipi sono già importati).

### TASK-US8-02 [P] — W3: Costante `_CONCIERGE_AGENT_SRC` e factory `_concierge_artifact`

**File**: `packages/sertor/src/sertor_installer/install_rag.py`
→ dipende da: TASK-F02

- [ ] Importa (se non già presente) `AssistantId` e `Surface` da `sertor_install_kit.assistant`
      e `render_custom_agent` da `sertor_installer.surfaces` (il pattern `sertor-flow` — D-0.6/D-4).
      Verifica che `install_rag.py:19` importi già `AssistantProfile`/`Surface`; aggiungi solo
      ciò che manca.
- [ ] Aggiungi la costante `_CONCIERGE_AGENT_SRC = "rag/agents/concierge.md"` (D-4/W3).
- [ ] Aggiungi la factory `_concierge_artifact(assistant: AssistantId) -> Artifact` (D-4/W3):
      ```python
      def _concierge_artifact(assistant: AssistantId) -> Artifact:
          aprofile = AssistantProfile.for_assistant(assistant)
          name = "agents/concierge.md" if assistant is AssistantId.CLAUDE else "concierge"
          target_rel = aprofile.render_path(Surface.AGENT, name)
          return Artifact(
              ArtifactKind.FILE,
              _CONCIERGE_AGENT_SRC,
              target_rel,
              WriteStrategy.CREATE_IF_ABSENT,
          )
      ```
      — replica la logica di `install_governance.py:147-157` per la singola superficie AGENT.
- [ ] Verifica (su carta): Claude → `target_rel == ".claude/agents/concierge.md"`;
      Copilot CLI → `target_rel == ".github/agents/concierge.agent.md"` (contratto §Artefatti
      di distribuzione, data-model §2).

### TASK-US8-03 [P] — W4: Helper render-aware `_render_rag_file` (CRITICO — R-1)

**File**: `packages/sertor/src/sertor_installer/install_rag.py`
→ dipende da: TASK-US8-02

- [ ] Aggiungi il helper **locale** `_render_rag_file(art: Artifact) -> str` (D-4/W4):
      ```python
      def _render_rag_file(art: Artifact) -> str:
          text = read_asset_text(art.source)
          if art.target_rel.endswith(".agent.md"):
              return render_custom_agent(text)
          return text
      ```
      Il branch `.agent.md` applica `render_custom_agent` (traduce il frontmatter Claude →
      Copilot, **omette `model:`**); tutti gli altri file (skill `.md`, hook `.ps1`) restano
      byte-copy. Nessun nuovo seam nel kit.
- [ ] Verifica che `read_asset_text` e `render_custom_agent` siano già importati/esportati
      nell'ambito di `install_rag.py`; aggiungi gli import mancanti.
- [ ] Verifica (su carta) che per `art.source = "rag/agents/concierge.md"` con
      `art.target_rel = ".github/agents/concierge.agent.md"`: il testo reso **non** contiene
      `model: sonnet` (omesso da `render_custom_agent` — R-1, contratto `agent-concierge.md`).
- [ ] Verifica (su carta) che per `art.source = "rag/skills/guided-setup/SKILL.md"` con
      `art.target_rel = ".github/skills/guided-setup/SKILL.md"` (non `.agent.md`): il testo reso
      è **byte-identico** al sorgente (skill byte-copy, parità tra target — FR-010).
- [ ] Verifica che gli script hook (`.ps1`) che finiscono in `_apply_rag_hook_file` **non**
      passino per `_render_rag_file` (i loro `target_rel` non terminano in `.agent.md` →
      nessuna regressione sugli hook, data-model §W4 nota).

### TASK-US8-04 — W5+W6+W7: Iniezione nel piano, lifecycle, upgrade render-aware

**File**: `packages/sertor/src/sertor_installer/install_rag.py`
→ dipende da: TASK-US8-01, TASK-US8-02, TASK-US8-03

- [ ] **W5 — Iniezione nel piano** (`build_rag_plan`): accanto a
      `plan.extend(_skill_artifacts(_EVAL_SKILL_NAMES, is_copilot))` aggiungi:
      ```python
      plan.extend(_skill_artifacts(_USABILITY_SKILL_NAMES, is_copilot))
      plan.append(_concierge_artifact(assistant))
      ```
      Ordine consigliato: eval skill → usability skill → agente concierge.
- [ ] **W6 — Lifecycle (`sertor_owned_paths`)** — aggiorna `sertor_owned_paths`:
      - skill `guided-setup` → `owned_dirs`: aggiungi
        `f"{skills_base}/guided-setup"` accanto ai path delle eval skill
        (così uninstall rimuove la dir, upgrade aggiorna il contenuto);
      - agente `concierge` → `owned_files`: aggiungi
        `aprofile.render_path(Surface.AGENT, "agents/concierge.md")` (Claude) o
        `aprofile.render_path(Surface.AGENT, "concierge")` (Copilot) — il file singolo in un
        contenitore condiviso (pattern `sertor-flow` lifecycle, D-4/W6).
      - Verifica: `plan ⊆ owned` — ogni artefatto generato da `_skill_artifacts` e
        `_concierge_artifact` compare in `owned_dirs` o `owned_files` (test di copertura
        esistente deve restare verde).
- [ ] **W7 — Upgrade render-aware** (`_apply_rag_upgrade`): sostituisci ogni occorrenza di
      `read_asset_text(art.source)` nell'apply del `FILE` durante l'upgrade con
      `_render_rag_file(art)`, così l'agente Copilot è aggiornato con il frontmatter tradotto
      (non il sorgente Claude grezzo). La skill resta byte-copy (il branch `.agent.md` non si
      attiva). Verifica non-regressione sugli upgrade degli hook (`.ps1` non terminano in
      `.agent.md`).

---

## Fase 3 — Storia 8 (guardia di parità): estensione `test_assets_copilot_parity.py` (3 task)

> Prerequisiti: TASK-US8-01..04 (il plan deve esistere per poterlo rendere). I task G1 e G2/G3
> sono sequenziali: G1 è il punto critico (R-1) e deve andare per primo.

### TASK-US8-05 — G1 (CRITICO): Allinea `_render_rag` al render reale del plan

**File**: `packages/sertor/tests/test_assets_copilot_parity.py`
→ dipende da: TASK-US8-03

- [ ] Individua la funzione `_render_rag(art)` nel test (oggi fa byte-copy pura:
      `read_asset_text(art.source)`).
- [ ] Allinea `_render_rag` al comportamento reale del plan (D-5.1/G1):
      ```python
      def _render_rag(art: Artifact) -> str:
          text = read_asset_text(art.source)
          if art.target_rel.endswith(".agent.md"):
              return render_custom_agent(text)
          return text
      ```
      Il pattern è **identico** a `_render_rag_file` del plan (non deve divergere — è il punto R-1).
- [ ] Verifica che dopo questa modifica i test esistenti `(a)(b)(c)` su skill e hook esistenti
      restino **verdi** (non-regressione: le skill e gli hook sono byte-copy, non `.agent.md`).
- [ ] Verifica (esecuzione manuale o asserzione): per il corpo Copilot dell'agente `concierge`
      reso da `_render_rag`, il frontmatter risultante **non** contiene `model:` (check
      `_CLAUDE_NAMES`/invariante (c)). Questo è il gate del rischio R-1.

### TASK-US8-06 — G2: Closure mirata asset usabilità (R-2)

**File**: `packages/sertor/tests/test_assets_copilot_parity.py`
→ dipende da: TASK-US8-05

- [ ] Aggiungi il test `test_rag_usability_asset_closure` (o estendi `test_copilot_reference_closure`
      con una sezione RAG) — closure mirata (D-5.2/G3 contratto):
      - Per ogni target (Claude e Copilot): raccogli i body della skill `guided-setup` e
        dell'agente `concierge` (resi da `_render_rag`).
      - Estrai i nomi di asset di usabilità citati per nome (`guided-setup`, `concierge`) con
        una regex mirata (es. `re.findall(r'\bguided-setup\b|\bconcierge\b', body)`).
      - Per ogni nome citato, verifica che il rag plan depositi l'asset corrispondente su quel
        target:
        - `guided-setup` → `{skills_base}/guided-setup/SKILL.md` è un target del plan;
        - `concierge` → il file agente (`concierge.md` o `concierge.agent.md`) è un target del
          plan.
      - Asserzione: tutti i nomi citati hanno un target nel plan (closure completa).
- [ ] Verifica che il test fallisca se si rimuove `guided-setup` dal piano (controllo di sanity
      della guardia).

### TASK-US8-07 — G3 (R-3): Ristringe `test_no_wiki_artifacts_created`

**File**: `packages/sertor/tests/test_install_rag.py`
→ dipende da: TASK-US8-04

- [ ] Individua il test `test_no_wiki_artifacts_created` (riga `:71` circa): oggi asserisce
      `not (.claude/agents)` per il rag plan.
- [ ] **Restringe** l'asserzione: il rag plan **non** deposita l'agente `wiki-curator`, ma **SÌ**
      deposita l'agente `concierge` e le usability/eval skill. Aggiorna l'asserzione a
      «nessun artefatto wiki» (es. path `wiki-curator` assente), non «nessun agente» (R-3).
- [ ] Aggiungi asserzioni specifiche positive accanto alla restrizione:
      - `.claude/agents/concierge.md` è **presente** nel piano Claude (atteso);
      - `.github/agents/concierge.agent.md` è **presente** nel piano Copilot (atteso);
      - le skill di usabilità (`.claude/skills/guided-setup/SKILL.md`) sono **presenti** (attese).
- [ ] Verifica che il test sia verde con il nuovo piano (non fallisce per la presenza di `concierge`).

---

## Fase 4 — Storia 8 (test di deposito): estensione `test_install_rag.py` (2 task)

> Prerequisiti: TASK-US8-04 (wiring). I due task sono **parallelizzabili** [P].

### TASK-US8-08 [P] — Test deposito skill `guided-setup` su entrambi i target

**File**: `packages/sertor/tests/test_install_rag.py`
→ dipende da: TASK-US8-04

- [ ] `test_guided_setup_skill_deposited_claude`: dopo `install rag --assistant claude` via
      `FakeCommandRunner` / plan-builder offline, verifica che `.claude/skills/guided-setup/SKILL.md`
      sia un target del piano (o esista nel fs temporaneo) (D-6, FR-010/US8-AC1).
- [ ] `test_guided_setup_skill_deposited_copilot`: dopo `--assistant copilot-cli`, verifica
      `.github/skills/guided-setup/SKILL.md` (D-6, FR-010/US8-AC1).
- [ ] `test_guided_setup_body_byte_identical`: il contenuto del body della skill reso per Claude
      è **byte-identico** a quello reso per Copilot (skill byte-copy, FR-010/US8-AC2 parità).
- [ ] Tutti `not cloud`, offline (`FakeCommandRunner`, nessun `uv`/ospite reale — RNF-4).

### TASK-US8-09 [P] — Test deposito agente `concierge` su entrambi i target

**File**: `packages/sertor/tests/test_install_rag.py`
→ dipende da: TASK-US8-04

- [ ] `test_concierge_agent_deposited_claude`: `.claude/agents/concierge.md` è un target del piano
      Claude **e** il suo frontmatter contiene `model: sonnet` (pin preservato — D-6/agent-concierge
      contract invarianti, US8-AC1).
- [ ] `test_concierge_agent_deposited_copilot`: `.github/agents/concierge.agent.md` è un target
      del piano Copilot **e** il suo frontmatter **non** contiene `model:` (omesso da
      `render_custom_agent` — lezione FEAT-011/049, D-6, R-1).
- [ ] `test_concierge_copilot_frontmatter_no_claude_names`: il frontmatter del corpo Copilot
      dell'agente non contiene `Claude`, `Opus`, `Haiku`, `claude` (nomi prodotto/modello) —
      invariante (c) della guardia, CS-5/US8-AC3.
- [ ] Test lifecycle — uninstall: dopo `uninstall rag --assistant claude`, `.claude/agents/concierge.md`
      è rimosso dai target di lifecycle (`owned_files`); dopo `--assistant copilot-cli`,
      `.github/agents/concierge.agent.md` è rimosso (W6, idempotenza lifecycle).
- [ ] Test lifecycle — upgrade: dopo `upgrade rag --assistant copilot-cli`, il corpo dell'agente
      Copilot è reso da `_render_rag_file` (frontmatter tradotto, non il sorgente Claude grezzo)
      — W7, non-regressione (upgrade render-aware).
- [ ] Tutti `not cloud`, offline.

---

## Fase 5 — Storia 9: Stub del concierge che instrada (P2, Should) (1 task)

> Prerequisiti: TASK-F02 (body agente). Verifica il routing e l'invariante a-un-ramo. [P]
> rispetto alle storie 1-7 del contenuto skill.

### TASK-US9-01 [P] — Test routing e invariante a-un-ramo dell'agente `concierge`

**File**: `packages/sertor/tests/test_install_rag.py`
→ dipende da: TASK-F02

- [ ] `test_concierge_routes_to_guided_setup`: il body dell'agente `concierge` (letto dal sorgente
      `assets/rag/agents/concierge.md`) cita `guided-setup` almeno una volta (US9-AC1/FR-012).
- [ ] `test_concierge_has_single_branch`: il body **non** cita `config-recommender`,
      `search-diagnose`, `FEAT-004`, `FEAT-007` o capacità non esistenti (US9-AC2, anti
      scope-creep/FR-012).
- [ ] `test_concierge_body_host_agnostic`: il body non contiene path `.claude/`, slash-command,
      nomi-modello Claude (body host-agnostico — RNF-2/lezione 056).
- [ ] Verifica `test_concierge_model_pin_in_frontmatter_only`: `model: sonnet` appare nel
      frontmatter del sorgente; **non** nel body (il pin è gestito by-target dal renderer, non
      nel body — contratto `agent-concierge.md` §Vincoli).
- [ ] Tutti `not cloud`, test sul file sorgente (lettura diretta senza plan-builder).

---

## Fase 6 — Storie 1-7: Contenuto della skill (verifiche comportamentali) (7 task)

> Prerequisiti: TASK-F01 (SKILL.md scritto). Tutti i task di questa fase sono **parallelizzabili**
> tra loro [P]: verificano sezioni indipendenti del body della skill.

### TASK-US1-01 [P] — Verifica flusso install→configure→verify (US1, P1 Must)

**File**: `packages/sertor/tests/test_install_rag.py` (o file di test skill dedicato)
→ dipende da: TASK-F01

- [ ] Leggi il body di `guided-setup/SKILL.md`; verifica che contenga **tutti e sei gli step**
      del flusso (Detect → Provider → Install → Configure → Index → Verify) in ordine
      (FR-001/US1-AC1).
- [ ] Verifica che ogni step citi il **vehicle deterministico** corrispondente per nome di comando
      (`sertor install`, `sertor configure --set`, `sertor-rag doctor`, `sertor-rag index`)
      (FR-001/US1-AC1).
- [ ] Verifica che nessuno step **re-implementi** un comando (nessun blocco di codice Python/shell
      inline che replichi la logica di install/configure/doctor/index — FR-001/FR-013).
- [ ] Verifica che Step 6 (Verify) richiami `sertor-rag doctor` e non dichiari successo senza
      il suo esito (FR-002/US1-AC2).
- [ ] Tutti test: lettura statica del file (nessun `uv`/ospite reale).

### TASK-US2-01 [P] — Verifica scelta provider dal contesto con conferma (US2, P2 Should)

**File**: `packages/sertor/tests/test_install_rag.py`
→ dipende da: TASK-F01

- [ ] Verifica che il body descriva i 3 segnali dell'euristica provider (creds cloud, airgapped,
      semantica NL) come richiesto da D-3/FR-004 (menzione esplicita dei segnali).
- [ ] Verifica che il body menzioni `glove` e `hash` come opzioni locali (FR-004/US2-AC1).
- [ ] Verifica che il body prescriva di **proporre** e **confermare** prima di impostare il
      provider (FR-005/US2-AC3 — «nessuna selezione senza conferma»).
- [ ] Verifica che il body preveda la proposta cloud (`azure`) solo **con creds presenti** e con
      motivazione (US2-AC2).
- [ ] Test: lettura statica del body + asserzioni regex/search.

### TASK-US3-01 [P] — Verifica segreti via percorso sicuro (US3, P1 Must)

**File**: `packages/sertor/tests/test_install_rag.py`
→ dipende da: TASK-F01

- [ ] Verifica che Step 4 del body prescriva **esclusivamente** `sertor configure --set`/prompt
      sicuro per i segreti (FR-006/US3-AC1).
- [ ] Verifica che il body contenga un divieto esplicito di stampare segreti (nella sezione
      «What NOT to do» e/o nello Step 4) (FR-006/RNF-3/US3-AC2).
- [ ] Verifica che il body preveda il controllo «segreto già in `.env` → non ri-richiesto né
      esposto» (US3-AC3/FR-009 idempotenza parziale).
- [ ] Verifica che `model: sonnet` e nomi prodotto Claude **non** compaiano nel body (anti-leak
      guardia — R-1, RNF-2).
- [ ] Test: lettura statica del body.

### TASK-US4-01 [P] — Verifica annuncio download GloVe (US4, P2 Should)

**File**: `packages/sertor/tests/test_install_rag.py`
→ dipende da: TASK-F01

- [ ] Verifica che Step 5 del body menzioni esplicitamente il download una-tantum (~822 MB) di
      GloVe quando il provider è `glove` e il modello non è in cache (FR-007/US4-AC1).
- [ ] Verifica che il body prescriva di annunciare **prima** di lanciare `sertor-rag index .`
      (non dopo) (FR-007/US4-AC1).
- [ ] Verifica che il body preveda il caso «cache presente → nessun annuncio» (US4-AC2).
- [ ] Verifica che il body citi (opzionalmente) la disponibilità futura di FEAT-003 (progress)
      senza bloccarsi su di essa (degrado onesto, US4-AC3/FR-007).
- [ ] Test: lettura statica del body.

### TASK-US5-01 [P] — Verifica verify onesto fail-loud (US5, P1 Must)

**File**: `packages/sertor/tests/test_install_rag.py`
→ dipende da: TASK-F01

- [ ] Verifica che Step 6 del body preveda il lancio di `sertor-rag doctor` **come gate
      obbligatorio** prima di dichiarare il setup riuscito (FR-002/US5-AC1).
- [ ] Verifica che il body prescriva: `doctor` non verde → espone **area + rimedio**, **non**
      dichiara «verificato» (FR-003/US5-AC2/Principio XII).
- [ ] Verifica che il body prescriva: `doctor` tutto verde → dichiara «verificato» con esito a
      supporto (US5-AC3/FR-002).
- [ ] Verifica che la sezione «What NOT to do» contenga esplicitamente il divieto di dichiarare
      «fatto» senza `doctor` (RNF-4/Principio XII).
- [ ] Test: lettura statica del body.

### TASK-US6-01 [P] — Verifica consenso prima di ogni mutazione (US6, P2 Should)

**File**: `packages/sertor/tests/test_install_rag.py`
→ dipende da: TASK-F01

- [ ] Verifica che la sezione **Consent gate** del body distingua esplicitamente:
      - check read-only (`doctor`, rilevazione `.sertor/.env`) → liberi, nessuna conferma
        (US6-AC1/FR-008);
      - passi mutanti (`install`, `configure --set`, primo `index`/download) → «proposti ed
        eseguiti solo dopo conferma esplicita» (US6-AC2/FR-008).
- [ ] Verifica che nessun passo mutante nel body sia descritto senza il gate di conferma
      (asserzione: la parola «confirm» o equivalente appare prima di ogni azione mutante)
      (US6-AC2/FR-008).
- [ ] Verifica che il body preveda «l'utente non conferma → la skill non esegue» (US6-AC3/FR-008).
- [ ] Test: lettura statica + asserzioni sulle sezioni identificate.

### TASK-US7-01 [P] — Verifica ri-esecuzione idempotente (US7, P2 Should)

**File**: `packages/sertor/tests/test_install_rag.py`
→ dipende da: TASK-F01

- [ ] Verifica che Step 1 del body prescriva il rilevamento dello stato esistente tramite
      `sertor-rag doctor --json` prima di procedere (FR-009/US7-AC1, D-2 Step 4).
- [ ] Verifica che il body preveda: tutte le aree `doctor` verdi → «già configurato e verificato»,
      stop (non ri-scaffolda) (FR-009/US7-AC1).
- [ ] Verifica che il body preveda: config parziale → conduce **solo** i passi mancanti, non
      quelli già completi (US7-AC2/FR-009).
- [ ] Verifica che il body menzioni il divieto di duplicare artefatti già presenti (US7-AC3/
      idempotenza percepita, RNF-5).
- [ ] Test: lettura statica del body.

---

## Fase 7 — Polish e cross-cutting (4 task)

> Prerequisiti: tutte le Fasi 0–6. TASK-P01 e TASK-P02 [P]; TASK-P03 dipende da P01+P02;
> TASK-P04 è indipendente e può partire prima.

### TASK-P01 [P] — Suite `sertor` e kit verde + lint ruff pulito

→ dipende da: tutti i task delle Fasi 0–6

- [ ] Esegui `uv run pytest packages/sertor/tests/ -m "not cloud" -v` → verde (tutti i nuovi e
      modificati test: `test_install_rag.py`, `test_assets_copilot_parity.py`).
- [ ] Verifica non-regressione: i test **pre-esistenti** di `test_install_rag.py` (eval skill,
      wiki, hook, idempotenza, uninstall) restano verdi — la generalizzazione di
      `_eval_skill_artifacts` → `_skill_artifacts` non deve rompere alcun comportamento
      precedente (W2/US8-AC1 non-regressione).
- [ ] Esegui `uv run pytest packages/sertor-install-kit/tests/ -m "not cloud" -v` → verde
      (kit invariato: nessun test del kit deve cambiare).
- [ ] Esegui `uv run ruff check packages/sertor/` → zero errori sui file nuovi/modificati
      (`install_rag.py`, `test_install_rag.py`, `test_assets_copilot_parity.py`).
      Regole E,F,I,UP,B; line-length 100.
- [ ] Esegui `uv run ruff check packages/sertor-install-kit/` → zero errori (invariato).

### TASK-P02 [P] — Verifica additività residua: core, kit e comandi runtime invariati

→ dipende da: tutti i task delle Fasi 0–6

- [ ] Verifica che **nessuno** dei seguenti file sia stato modificato (RNF-7):
      - `src/sertor_core/` (tutto il core: porte/adapter/composition/engine/services invariati);
      - `packages/sertor-install-kit/src/` (kit invariato: `assistant.py`/`surfaces.py`/
        `artifacts.py` — riuso, no estensione);
      - `packages/sertor/src/sertor_installer/install_wiki.py` (wiki install invariato);
      - `packages/sertor/src/sertor_installer/install_governance.py` (governance install invariato).
- [ ] Spot check comandi runtime invariati:
      - `sertor install rag --assistant claude` produce gli stessi artefatti pre-esistenti **più**
        i nuovi (additivo — nessun artefatto pre-esistente rimosso o modificato);
      - `sertor-rag doctor`, `sertor-rag index`, `sertor configure` invariati (non toccati).
- [ ] Verifica che `test_assets_copilot_guard.py` (anti-corpo-a-mano) sia verde — nessun secondo
      corpo Copilot a mano per skill/agente (D-5.3, contratto §Anti-corpo-a-mano).

### TASK-P03 — Verifica CS-1..5 e criteri di accettazione trasversali

→ dipende da: TASK-P01, TASK-P02

- [ ] **CS-1 (dal nulla a verificato):** verifica che il flusso della skill copra install →
      configure → verify senza richiedere conoscenza interna (US1). Confermato da TASK-US1-01.
- [ ] **CS-2 (scelta provider motivata):** verifica che l'euristica e la proposta con conferma
      siano presenti (US2). Confermato da TASK-US2-01.
- [ ] **CS-3 (segreti mai esposti):** verifica che il body prescriva segreti via percorso sicuro
      e nessuna stampa (US3). Confermato da TASK-US3-01.
- [ ] **CS-4 (verify fail-loud):** verifica che `doctor` verde → «verificato» e rosso → area+rimedio
      senza dichiarazione di successo (US5). Confermato da TASK-US5-01.
- [ ] **CS-5 (host-agnostico & installabile):** verifica che skill e agente siano depositati su
      entrambi i target, corpo byte-identico, closure dei riferimenti, zero leak di contenitore
      (US8). Confermato da TASK-US8-05..09.
- [ ] Verifica che `contracts/skill-guided-setup.md`, `contracts/agent-concierge.md`,
      `contracts/distribution-parity.md` siano tutti rispettati (nessun gap aperto).
- [ ] Segnala eventuale prova LIVE residua come **follow-up non-bloccante** (R-4): done
      automatico offline; la verifica su un ospite Claude/Copilot reale va tracciata come
      task di integrazione post-merge (non blocca il done di questa feature).

### TASK-P04 [P] — Tracciamento scope nel backlog d'epica (D-7)

**File**: `requirements/usabilita/epic.md`
→ dipende da: nessuno (può partire in qualsiasi fase)

- [ ] Aggiorna la riga **FEAT-002** (`:172`) da «decomposta → requirements» a
      **«in progress → spec/plan 075»** (D-7/data-model §5).
- [ ] Aggiorna la riga **FEAT-009** (`:180`) da «da decomporre» a
      **«parzialmente avviata (stub agente `concierge` a un ramo) — gli altri rami
      (config-recommender FEAT-004 / search-diagnose FEAT-007) + check proattivi restano FEAT-009»**
      (D-7/plan §Tracciamento dello scope durevole). Non marcare done, non duplicare.
- [ ] Verifica che FEAT-003 (`:174`) e FEAT-004 (`:175`) restino voci esistenti nel backlog
      senza modifica (consumo opzionale «quando disponibili» — nessun rinvio orfano in `specs/`).
- [ ] Verifica che nessuna voce out-of-scope rimanga orfana solo in `specs/075-guided-setup/`
      (profilazione ricca → FEAT-004; progress GloVe → FEAT-003; compiti pieni concierge → FEAT-009).

---

## Grafo delle dipendenze (sintesi)

```
TASK-S01 (albero assets/rag/agents/) ──────────────────────────────────────────┐
                                                                                │
TASK-F01 [P] (SKILL.md) ──────────────────────────────────────────────────┐   │
TASK-F02 [P] (concierge.md) ← S01 ────────────────────────────────────────┼───┘
                                                                           │
         TASK-US8-01 [P] (W1+W2: _USABILITY_SKILL_NAMES + _skill_artifacts) ← F01
         TASK-US8-02 [P] (W3: _CONCIERGE_AGENT_SRC + _concierge_artifact) ← F02
         TASK-US8-03 [P] (W4: _render_rag_file render-aware) ← US8-02
                  │
         TASK-US8-04 (W5+W6+W7: build_rag_plan + lifecycle + upgrade) ← US8-01, US8-02, US8-03
                  │
         ┌────────┼─────────────────────────────────────────┐
         │        │                                         │
 TASK-US8-05   TASK-US8-07 (R-3: test ristretto)       TASK-US9-01 [P] ← F02
 (G1 critico)  ← US8-04                                (routing + a-un-ramo)
 ← US8-03
         │
 TASK-US8-06 (G2: closure mirata) ← US8-05
         │
 TASK-US8-08 [P] (deposito skill) ← US8-04
 TASK-US8-09 [P] (deposito agente + lifecycle) ← US8-04

TASK-US1-01 [P] ← F01   TASK-US2-01 [P] ← F01   TASK-US3-01 [P] ← F01
TASK-US4-01 [P] ← F01   TASK-US5-01 [P] ← F01
TASK-US6-01 [P] ← F01   TASK-US7-01 [P] ← F01

TASK-P01 [P] (suite verde + lint) ← tutti i task Fasi 0–6
TASK-P02 [P] (additività residua) ← tutti i task Fasi 0–6
TASK-P03 (CS-1..5) ← P01, P02
TASK-P04 [P] (epic.md tracciamento scope) ← nessuno
```

---

## Criteri di test indipendenti per User Story

| US | Criterio di test indipendente | Task principali | Natura |
|---|---|---|---|
| **US1** (dal nulla a verificato) | Il body della skill contiene tutti e sei gli step del flusso (Detect→Provider→Install→Configure→Index→Verify) con i vehicle deterministici corretti per nome di comando; nessun comando re-implementato. | TASK-F01, TASK-US1-01 | TESTUALE/STATICO |
| **US2** (scelta provider dal contesto) | Body descrive i 3 segnali euristica; proposta con motivazione; nessuna selezione senza conferma; locale (glove/hash) per creds assenti/airgapped; cloud proponibile con creds presenti. | TASK-F01, TASK-US2-01 | TESTUALE/STATICO |
| **US3** (segreti via percorso sicuro) | Body prescrive solo `configure --set`/prompt sicuro per segreti; divieto esplicito di stampa; segreto già presente → non ri-richiesto né esposto. | TASK-F01, TASK-US3-01 | TESTUALE/STATICO |
| **US4** (annuncio download GloVe) | Body prescrive annuncio una-tantum (~822 MB) prima del primo `index` con `glove` non in cache; silenzioso con cache presente. | TASK-F01, TASK-US4-01 | TESTUALE/STATICO |
| **US5** (verify onesto fail-loud) | Body prescrive `doctor` come gate obbligatorio; rosso → area+rimedio, nessun «verificato»; verde → dichiara verificato con esito a supporto. | TASK-F01, TASK-US5-01 | TESTUALE/STATICO |
| **US6** (consenso prima di mutazioni) | Body distingue check read-only (liberi) da passi mutanti (proposta + conferma); nessuna azione mutante senza gate; stop se l'utente non conferma. | TASK-F01, TASK-US6-01 | TESTUALE/STATICO |
| **US7** (ri-esecuzione idempotente) | Step 1 rileva stato via `doctor --json`; tutte le aree verdi → stop; config parziale → solo passi mancanti; nessuna duplicazione artefatti. | TASK-F01, TASK-US7-01 | TESTUALE/STATICO |
| **US8** (installabile dual-target con parità) | Skill e agente depositati nei contenitori nativi di entrambi i target via `sertor install`; body skill byte-identico; agente Claude con `model: sonnet`, agente Copilot senza `model:`; closure «guided-setup» citata per nome → skill depositata; zero leak contenitore. | TASK-US8-01..09, TASK-US8-05 (R-1 critico) | MECCANICO |
| **US9** (stub concierge che instrada) | Body cita `guided-setup` per nome; nessun riferimento a `config-recommender`/`search-diagnose`/FEAT-004/007; `model: sonnet` solo nel frontmatter (non nel body); body host-agnostico. | TASK-F02, TASK-US9-01 | TESTUALE/STATICO |

---

## Parallelizzazione consigliata (MVP)

**Sprint 1 (nessun prerequisito — in parallelo):**
- TASK-S01 (albero `assets/rag/agents/`)
- TASK-F01 [P] (skill `guided-setup/SKILL.md`)
- TASK-P04 [P] (epic.md tracciamento scope — indipendente, può partire subito)

**Sprint 2 (dopo S01 — in parallelo):**
- TASK-F02 [P] (agente `concierge.md` — dipende da S01)
- TASK-US8-01 [P] (W1+W2 — dipende da F01, parallelizzabile con F02)
- TASK-US9-01 [P] (test routing — dipende da F02 per lettura sorgente, ma può partire
  subito con F02 in progress)

**Sprint 3 (dopo F01+F02 — massima parallelizzazione verifiche contenuto):**
- TASK-US8-02 [P] (W3: factory agente)
- TASK-US1-01..US7-01 [P] (verifiche statiche skill — tutte dipendono da F01, tutte parallelizzabili)

**Sprint 4 (dopo US8-02 — render-aware e piano completo):**
- TASK-US8-03 (W4: `_render_rag_file` — R-1, CRITICO, sblocca G1)
- TASK-US8-04 (W5+W6+W7 — dopo US8-01+02+03)

**Sprint 5 (dopo US8-04 — guardia e test di deposito):**
- TASK-US8-05 (G1 critico — prima degli invarianti sull'agente)
- TASK-US8-07 [P] (R-3: test ristretto)
- TASK-US8-08 [P] (deposito skill)
- TASK-US8-09 [P] (deposito agente + lifecycle)

**Sprint 6 (dopo US8-05 — closure):**
- TASK-US8-06 (G2: closure mirata — dipende da US8-05)

**Sprint finale (Polish — dopo tutto):**
- TASK-P01 [P] (suite verde + lint)
- TASK-P02 [P] (additività residua)
- TASK-P03 (CS-1..5 trasversali)

---

## Brief di commit (per il `configuration-manager`)

```
docs(tasks): genera tasks.md per E12-FEAT-002 — guided-setup (skill + agente concierge)

Fase SpecKit "tasks" completata per specs/075-guided-setup.
29 task in 8 fasi:
  Fase 0 Setup                     : 1 task  (TASK-S01 — albero assets/rag/agents/)
  Fase 1 Fondazionale              : 2 task  [P] (TASK-F01 skill SKILL.md · TASK-F02 agente concierge.md)
  Fase 2 Storia 8 — Wiring         : 4 task  (TASK-US8-01..04 — W1-W7 in install_rag.py)
  Fase 3 Storia 8 — Guardia parità : 3 task  (TASK-US8-05 G1 critico · 06 closure · 07 R-3)
  Fase 4 Storia 8 — Test deposito  : 2 task  [P] (TASK-US8-08 skill · 09 agente lifecycle)
  Fase 5 Storia 9 (P2 Should)      : 1 task  (TASK-US9-01 — routing + a-un-ramo)
  Fase 6 Storie 1-7 (contenuto)    : 7 task  [P] (TASK-US1-01..US7-01 — verifiche statiche skill)
  Fase 7 Polish/cross-cutting       : 4 task  (TASK-P01..P04 — suite, lint, CS-1..5, epic.md)

Natura: ADDITIVO + scope di distribuzione. Nessun codice runtime del core.
sertor-core e sertor-install-kit invariati (RNF-7).
Rischi coperti: R-1 (TASK-US8-03+05 — _render_rag render-aware, modello sonnet non leaka su
  Copilot), R-2 (TASK-US8-06 — closure mirata nome-asset), R-3 (TASK-US8-07 — test ristretto
  wiki/rag), R-4 (follow-up non-bloccante — segnalato in TASK-P03).
Copertura: FR-001..013, RNF-1..7, CS-1..5, US1..9.
Test natura: MECCANICO (US8) + TESTUALE/STATICO (US1-7, US9).
Default eval skill invariati: TASK-US8-01 (generalizzazione _skill_artifacts non-regressione).
Parità dual-target: TASK-US8-05 G1 critico (guardia render-aware) + TASK-US8-08/09 deposito.
Tracciamento scope: TASK-P04 (FEAT-002 in progress; FEAT-009 parzialmente avviata — stub).

Nessun hook SpecKit eseguito (script assenti nel repo); nessuna operazione git.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

**File da includere nel commit:**
- `specs/075-guided-setup/tasks.md` (questo file, nuovo)
