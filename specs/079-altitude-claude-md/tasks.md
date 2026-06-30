# Tasks — Ridurre l'altitude dei blocchi CLAUDE.md + fonte unica «How to invoke» (E10-FEAT-021)

**Branch**: `079-altitude-claude-md` · **Generato**: 2026-06-30
**Spec**: [`spec.md`](spec.md) · **Piano**: [`plan.md`](plan.md) · **Dati**: [`data-model.md`](data-model.md)
**Contratti**: [`contracts/reduced-blocks.md`](contracts/reduced-blocks.md) · [`contracts/guard.md`](contracts/guard.md)
**Quickstart**: [`quickstart.md`](quickstart.md)

> **Nota di processo.** I task marcati `[P]` sono parallelizzabili all'interno della stessa fase
> (nessuna dipendenza reciproca). Il suffisso `→ dipende da` lista i task prerequisiti. Git **mai**
> qui: brief di commit al fondo per il `configuration-manager`.
>
> **Natura del cambiamento: ADDITIVO / igiene host-facing, ZERO codice di core.**
> La feature tocca esclusivamente:
> - 1 asset Markdown NUOVO (`sertor-cli-reference.md`) — la fonte unica «How to invoke»;
> - 1 modifica di codice (`install_rag.py`) — aggiunta di 1 `Artifact` FILE al `build_rag_plan`;
> - 2 blocchi always-on ridotti (`claude-md-block-rag-usage.md`, `claude-md-block.md`) + pointer;
> - 2 skill deduplicatate (`guided-setup/SKILL.md`, `wiki-playbook.md`) — rimozione sezione inline;
> - 1 re-sync dogfood (`python -m sertor_installer.sync` → `.claude/skills/wiki-author/wiki-playbook.md`);
> - 3 suite di test (rework `test_assets_cli_invocation.py`, estensione `test_assets_copilot_parity.py`,
>   guard SDLC in `test_governance_assets_host_agnostic.py`).
>
> `sertor_core` è **INVARIATO**. Blocco SDLC (`claude-md-block-sdlc.md`) **INVARIATO** (DA-D-r3).
> Nessun nuovo `ArtifactKind`/`WriteStrategy`/`Surface`/seam del kit.
>
> **Vincoli da coprire (calibra l'ordine):**
> - **VR-2 (host-agnostico):** ogni body toccato deve essere privo di `.claude/`, slash-command e
>   nomi modello/prodotto Claude (`Claude`, `Opus`, `Haiku`, `CLAUDE.md`, `$ARGUMENTS`).
> - **C4 footgun `--directory`:** il reference `sertor-cli-reference.md` NON deve contenere
>   `uv run --directory .sertor` (footgun); solo `--project`; verificato da `test_assets_cli_invocation.py`.
> - **VR-4 (fonte unica):** la sezione completa + Windows note (`pywin32_bootstrap`) appare in
>   esattamente un asset; G2 lo verifica offline.
> - **Closure (NFR-5):** il `wiki-playbook.md` non cita `sertor-cli-reference.md` per filename
>   (pointer morto su install solo-wiki); usa frase condizionale senza token `.md` (fuori scope closure).
>
> **Strategia MVP/incrementale.**
> - **Fondazionale** (F01+F02): creare l'asset canonico e registrarlo nel piano RAG. Bloccanti per
>   US1-01 e US2-01 (dipendono dal nome/percorso del reference). F02 dipende da F01.
> - **Riduzione blocchi** (US1-01/02): pure edit di Markdown, parallelizzabili tra loro. US1-02
>   (wiki block) non dipende da F01 (pointer a `wiki-playbook.md`, già esistente). [P]
> - **Dedup skill** (US2-01/02): edit Markdown. US2-02 (wiki-playbook) non dipende da F01
>   (rimuove sezione, frase condizionale senza filename). [P] tra loro, avviabili dopo F01.
> - **Sync dogfood** (US6-01): sequenziale, dopo US2-02 (wiki-playbook modificato).
> - **Guardie** (US7-01/02/03): rework/estensione test, dopo che tutti gli asset sono stabili. [P] tra loro.
> - **Polish** (P01/P02): suite verde totale + CS check.

---

## Fase 0 — Fondazionale: asset reference canonico e wiring nel piano RAG (2 task)

> Prerequisiti: nessuno. F01 [P] (non blocca le task che non citano il reference: US1-02, US2-02).
> F02 dipende da F01 (usa il percorso sorgente del reference). Bloccanti per US1-01, US2-01.

### TASK-F01 [P] — Crea `assets/rag/sertor-cli-reference.md` (asset canonico «How to invoke»)

**File**: `packages/sertor/src/sertor_installer/assets/rag/sertor-cli-reference.md` (NUOVO)
→ dipende da: nessuno

**Mappa FR**: FR-005/006/007 · CS-2 · US2 · data-model §E2 · contracts/reduced-blocks.md C4

- [x] Crea il file `packages/sertor/src/sertor_installer/assets/rag/sertor-cli-reference.md`.
      È l'**unica sede** che ospiterà la sezione «How to invoke Sertor's commands» + Windows note.
- [x] Scrivi il contenuto con heading principale: `# How to invoke Sertor's commands` (o equivalente
      di secondo livello `## How to invoke Sertor's commands` coerente con lo stile delle skill).
- [x] Includi il **livello runtime** (contratto C4):
      - Spiegazione che le CLI non sono su `PATH` dopo install (`not on PATH` ≠ not installed).
      - Forma robusta obbligatoria: `uv run --project .sertor sertor-rag <cmd>` e
        `uv run --project .sertor sertor-wiki-tools <op>`.
      - Chiarimento che `--project` NON è `--directory` (footgun: `--directory` cambia cwd, quindi
        `sertor-rag index .` indicizzerebbe `.sertor` invece del progetto host).
      - Fallback al venv per chi preferisce l'invocazione diretta:
        `.sertor/.venv/Scripts/` (Windows) / `.sertor/.venv/bin/` (macOS/Linux).
- [x] Includi il **livello installer** (contratto C4):
      - `uvx --from "git+https://github.com/themetriost/Sertor` …` per installare/aggiornare.
- [x] Includi la **Windows note** (contratto C4):
      - Sezione che menziona `pywin32_bootstrap`; impatto/azione sulla dipendenza di sistema Python
        3.14+; conclusione che il runtime Sertor è `unaffected`.
- [x] Verifica gli **invarianti host-agnostici** (contratto C4, REQ-006, VR-2):
      - NON contiene `.claude/` (percorso assistente-specifico).
      - NON contiene uno slash-command come invocazione (`/wiki`, `/requirements`).
      - NON contiene nomi modello/prodotto Claude (`Claude Code`, `Opus`, `Haiku`, `CLAUDE.md`,
        `$ARGUMENTS`).
      - NON contiene `uv run --directory .sertor` (footgun — vive solo nel template MCP).
- [x] Verifica che l'heading `How to invoke Sertor's commands` sia presente in forma testuale.
- [x] Verifica che `pywin32_bootstrap` appaia nel corpo (necessario per G2: fonte unica Windows note).
- [x] Verifica che `uvx --from` appaia nel corpo (livello installer — espresso solo qui).
- [x] Verifica che la forma robusta `uv run --project .sertor` appaia almeno una volta
      (necessario per `test_invoking_assets_carry_robust_form` dopo che l'asset entra in `_INVOKING_ASSETS`).

---

### TASK-F02 — Aggiungi `Artifact` FILE al `build_rag_plan` in `install_rag.py`

**File**: `packages/sertor/src/sertor_installer/install_rag.py` (MODIFICA)
→ dipende da: TASK-F01

**Mappa FR**: FR-007/013 · CS-3 · US2/US3 · data-model §E2/VR-3 · plan.md §Sequenza 2

- [x] Apri `packages/sertor/src/sertor_installer/install_rag.py`.
      Individua la funzione `build_rag_plan` (riga ~370). Verifica la struttura attuale.
- [x] Definisci una costante a livello di modulo per il percorso sorgente e il target host:
      ```python
      _CLI_REFERENCE_ASSET = "rag/sertor-cli-reference.md"
      _CLI_REFERENCE_TARGET = ".sertor/sertor-cli-reference.md"
      ```
      (Oppure usa stringhe inline nel `Artifact` se la convenzione del file non usa costanti per ogni
      FILE asset — verifica come sono definite le costanti per hook e skill simili nel file.)
- [x] Aggiungi il seguente `Artifact` FILE nella lista `plan` di `build_rag_plan`, nel punto
      logicamente coerente con gli altri FILE assets (dopo il MARKER_BLOCK del RAG usage block e
      prima o subito dopo i skill artifacts — verifica la convenzione d'ordine):
      ```python
      plan.append(
          Artifact(
              ArtifactKind.FILE,
              _CLI_REFERENCE_ASSET,
              _CLI_REFERENCE_TARGET,
              WriteStrategy.CREATE_IF_ABSENT,
          )
      )
      ```
      Il target `.sertor/sertor-cli-reference.md` è coperto dall'`owned_dir` `.sertor` esistente
      (riga ~835 di `install_rag.py`) → rimosso in blocco su uninstall, aggiornato su upgrade
      come gli altri owned-file di `.sertor/` (VR-3: lifecycle corretto, FR-013).
- [x] Verifica che il target **non sia assistente-specifico** (`.sertor/` è identico su Claude e
      Copilot CLI — il piano viene costruito per entrambi gli assistenti tramite `build_rag_plan`,
      e la FILE di byte-copy è già la strategia degli hook e delle skill, VR-2/Principio X).
- [x] Verifica che non siano stati aggiunti nuovi `ArtifactKind`, `WriteStrategy`, `Surface`
      o seam del kit (riuso puro del meccanismo esistente FILE + CREATE_IF_ABSENT, VR-1).
- [x] Verifica che nessun import di `sertor_core` sia aggiunto (VR-1/Principio XI).
- [x] Spot check: il piano RAG per `AssistantId.CLAUDE` ora include un `Artifact` con
      `target_rel == ".sertor/sertor-cli-reference.md"` e `source == "rag/sertor-cli-reference.md"`.
      Questo sarà verificato offline dalla guardia G4 (TASK-US7-02) tramite
      `{Path(t.target_rel).name for t in plan}`.

---

## Fase 1 — US1/US4 — Riduzione blocchi always-on (2 task, [P])

> Prerequisiti: TASK-F01 (US1-01 cita il reference per nome). US1-02 non dipende da F01.
> I 2 task sono parallelizzabili tra loro [P] (file distinti).
> Bloccanti per TASK-US7-01 (verifica i body modificati).
>
> **Convenzione comune:**
> - **Standing inline:** regole che l'agente deve seguire in OGNI sessione (usa/non-importare, errori).
> - **Spostato a pointer:** sintassi esatta, note di troubleshooting (lookup-on-demand).
> - I pointer citano l'asset per **nome** (non per percorso filesystem), es. ``sertor-cli-reference.md``.
> - Mantenere sempre almeno un'occorrenza della forma robusta `uv run --project .sertor …`
>   (richiesta da `test_invoking_assets_carry_robust_form` e `test_rag_usage_block_uv_run_replaces_bare_search`).

### TASK-US1-01 [P] — Riduci il blocco RAG (`claude-md-block-rag-usage.md`, contratto C1)

**File**: `packages/sertor/src/sertor_installer/assets/rag/claude-md-block-rag-usage.md` (MODIFICA)
→ dipende da: TASK-F01

**Mappa FR**: FR-001/002/004/015 · CS-1/CS-4 · US1/US4 · contracts/reduced-blocks.md C1

- [x] Apri `packages/sertor/src/sertor_installer/assets/rag/claude-md-block-rag-usage.md`.
      Il file ha 72 righe before feature; le righe 12-38 contengono la sezione «How to invoke».
- [x] **Rimuovi** la sezione «How to invoke Sertor's commands» (righe ~12–38, con la Windows note
      `pywin32_bootstrap`): questo è il lookup-on-demand da centralizzare in `sertor-cli-reference.md`.
- [x] **Sostituisci** la sezione rimossa con un **pointer per nome** (REQ-002, C1), es.:
      `For detailed CLI invocation syntax, fallback options, and Windows setup notes, see` `` `sertor-cli-reference.md` `` `(available after` `sertor install rag`).`
      Il pointer deve contenere il token di file ``sertor-cli-reference.md`` (necessario per G3).
      **Non usare un percorso filesystem** (es. `.sertor/sertor-cli-reference.md`): solo il basename.
- [x] Verifica le **presenze obbligatorie** (contratto C1, REQ-015):
      - [x] `sertor_core` + `vehicles` (CLI/MCP) → direttiva vehicle-only / no-import.
      - [x] `Search first` o `search`…`before reading files` → search-first, read-second.
      - [x] `uv run --project .sertor sertor-rag search` → forma robusta conservata (DEVE restare
            inline per `test_rag_usage_block_uv_run_replaces_bare_search`).
      - [x] `error` + `signal` → regola «errore MCP = segnale, non rumore».
      - [x] `SERTOR_MEMORY` → gate privacy memoria conservato.
      - [x] ``sertor-cli-reference.md`` → pointer per nome al reference unico (REQ-002/015).
- [x] Verifica le **assenze obbligatorie** (contratto C1, REQ-001/012):
      - [x] `How to invoke Sertor's commands` **NON** presente (heading rimosso, G1).
      - [x] `pywin32_bootstrap` **NON** presente (Windows note estratta, G1).
      - [x] `uvx --from` **NON** presente (livello installer estratto, G1).
      - [x] `--directory .sertor` **NON** presente nella forma di invocazione (footgun estratto; la
            menzione nella frase cautionary del footgun va gestita con `_is_robust_context` — lascia
            la sola forma `--project`).
- [x] Verifica che il blocco sia **host-agnostico** (VR-2): zero `.claude/`, zero slash-command,
      zero nomi prodotto/modello Claude.
- [x] Misura le righe dopo la modifica (CS-1): il blocco deve essere < 72 righe (~48 atteso).

---

### TASK-US1-02 [P] — Riduci il blocco wiki (`claude-md-block.md`, contratto C2)

**File**: `packages/sertor/src/sertor_installer/assets/claude-md-block.md` (MODIFICA)
→ dipende da: nessuno (pointer a `wiki-playbook.md`, asset già esistente)

**Mappa FR**: FR-001/002/004/014 · CS-1/CS-4 · US1/US4 · contracts/reduced-blocks.md C2

- [x] Apri `packages/sertor/src/sertor_installer/assets/claude-md-block.md`.
      Il file ha 71 righe before feature.
- [x] **Rimuovi** la sezione `### Wiki operations` con l'elenco delle operazioni
      (`ingest`/`query`/`reorg`/`generate`/`rag-sync`/`structure` in forma bullet/elenco): è
      lookup-on-demand già presente nel wiki playbook; non serve always-on.
- [x] **Rimuovi** la sezione `### Conventions` (o equivalente) con i dettagli di frontmatter YAML,
      backlink stile wikilink, naming kebab-case, formato voce di log: anche queste sono
      lookup-on-demand, già nel playbook.
- [x] **Aggiungi** un **riferimento per nome** al wiki playbook (REQ-014, C2), es.:
      `For the full list of wiki operations, conventions, and log format, see` `` `wiki-playbook.md` ``.
      Il token ``wiki-playbook.md`` deve essere presente (necessario per G3).
- [x] Verifica le **presenze obbligatorie** (contratto C2, REQ-014):
      - [x] `Golden rule` → golden rule della documentazione (documentare ogni cosa di rilievo).
      - [x] `Step` + `Record` + `Distill` + `lint` → outline del rituale di step.
      - [x] `wiki-curator` + `main flow` → regole di delega (record→curator; distill/lint→main flow).
      - [x] `judgment` o `D↔N` → confine meccanico vs giudizio.
      - [x] ``wiki-playbook.md`` → riferimento per nome al wiki playbook (REQ-014).
- [x] Verifica le **assenze obbligatorie** (contratto C2):
      - [x] La sezione `### Wiki operations` con l'elenco bullet completo **NON** presente (o ridotta
            a sola menzione senza l'enumerazione estesa di 8 operazioni).
      - [x] La sezione `### Conventions` con YAML frontmatter/kebab-case/formato voce di log
            **NON** presente inline (spostata al playbook).
- [x] Verifica che il blocco sia **host-agnostico** (VR-2): zero `.claude/`, zero slash-command,
      zero nomi prodotto/modello Claude.
- [x] Misura le righe dopo la modifica (CS-1): il blocco deve essere < 71 righe (~53 atteso).

---

## Fase 2 — US2 — Dedup sezione «How to invoke» nelle skill (2 task, [P])

> Prerequisiti: TASK-F01 (US2-01 cita il reference per nome). US2-02 non dipende da F01.
> I 2 task sono parallelizzabili tra loro [P] (file distinti).
> Bloccanti per TASK-US6-01 (US2-02 modifica wiki-playbook sotto `assets/claude/**`) e
> per TASK-US7-01 (verifica le nuove forme dei body).

### TASK-US2-01 [P] — Rimuovi sezione inline da `guided-setup/SKILL.md` (contratto C5)

**File**: `packages/sertor/src/sertor_installer/assets/rag/skills/guided-setup/SKILL.md` (MODIFICA)
→ dipende da: TASK-F01

**Mappa FR**: FR-008 · CS-2 · US2 · contracts/reduced-blocks.md C5

- [x] Apri `packages/sertor/src/sertor_installer/assets/rag/skills/guided-setup/SKILL.md`.
      Le righe 52–78 contengono la sezione «## How to invoke Sertor's commands» (copia inline 2).
- [x] **Rimuovi** la sezione «## How to invoke Sertor's commands» (righe ~52–78) — tutta la
      sottosezione con i dettagli runtime CLI, installer, fallback venv e Windows note.
- [x] **Sostituisci** la sezione rimossa con un **pointer per nome** (C5, REQ-008), es.:
      `For CLI invocation details, see` `` `sertor-cli-reference.md` `` `(the reference ships with this capability).`
      Il token di file ``sertor-cli-reference.md`` deve essere presente (necessario per G3/G4).
- [x] Verifica le **presenze obbligatorie** (contratto C5):
      - [x] ``sertor-cli-reference.md`` → pointer per nome (REQ-008).
      - [x] Il resto della logica della skill (Step 0–6, consent gate, ecc.) è **intatto**.
      - [x] Almeno una forma robusta `uv run --project .sertor` nei passi della skill (il passo
            che invoca `sertor-rag index .` o simile deve usare la forma robusta — necessario
            per `test_invoking_assets_carry_robust_form` che copre `_GUIDED_SETUP`).
- [x] Verifica le **assenze obbligatorie** (contratto C5):
      - [x] `## How to invoke Sertor's commands` **NON** presente (heading rimosso, G1).
- [x] Verifica che l'asset sia **host-agnostico** (VR-2): zero `.claude/`, zero slash-command,
      zero nomi prodotto/modello Claude.

---

### TASK-US2-02 [P] — Riduci `wiki-playbook.md` (contratto C6, closure-safe)

**File**: `packages/sertor/src/sertor_installer/assets/claude/skills/wiki-author/wiki-playbook.md` (MODIFICA)
→ dipende da: nessuno (frase condizionale senza token di file, closure-safe)

**Mappa FR**: FR-009 · CS-2 · US2 · contracts/reduced-blocks.md C6 · research.md §DA-D-r1

- [x] Apri `packages/sertor/src/sertor_installer/assets/claude/skills/wiki-author/wiki-playbook.md`.
      Le righe 93–112 contengono la sottosezione «### How to invoke the runtime CLIs» + Windows note
      (copia inline 3, runtime-only variant — senza livello installer o URL GitHub).
- [x] **Rimuovi** la sottosezione «### How to invoke the runtime CLIs» (righe ~93–112):
      l'heading e il corpo con la Windows note (`pywin32_bootstrap`).
- [x] **Conserva** la forma minima di invocazione al §2 del playbook (righe ~88–91):
      `uv run --project .sertor sertor-wiki-tools <op>` + chiarimento PATH (`not on PATH`).
      Questa forma è l'auto-contenimento wiki-only; NON va rimossa (REQ-014 minimo, C6).
- [x] **Aggiungi** (dopo la forma minima conservata o in punto logico) una **frase condizionale
      senza token di file** sul reference RAG (C6, closure-safe), es.:
      `When the Sertor RAG capability is also installed, a fuller CLI reference document ships with it,
      covering installer-level invocation and platform-specific notes.`
      **IMPORTANTE:** la frase NON deve contenere il token ``sertor-cli-reference.md`` come backtick-
      reference (la regex `_BACKTICK_REF` di closure matcha ``*.md``): se il wiki-playbook lo citasse,
      la guardia G4 richiederebbe che il piano WIKI lo depositi — ma non lo fa (pointer morto su install
      solo-wiki, REQ-007/NFR-5). Usa la frase descrittiva senza il filename.
- [x] Verifica le **presenze obbligatorie** (contratto C6):
      - [x] Forma minima `uv run --project .sertor sertor-wiki-tools` al §2 → presente.
      - [x] Chiarimento PATH (`not on` `PATH` o equivalente) → presente.
      - [x] Frase condizionale senza filename sul reference RAG → presente.
- [x] Verifica le **assenze obbligatorie** (contratto C6):
      - [x] `### How to invoke the runtime CLIs` **NON** presente (heading rimosso, G5).
      - [x] `pywin32_bootstrap` **NON** presente (Windows note estratta, G5).
      - [x] ``sertor-cli-reference.md`` (backtick-reference con estensione `.md`) **NON** presente
            (evita pointer morto su piano wiki, NFR-5/REQ-007).
      - [x] `uvx --from` **NON** presente (livello installer non nel playbook, host-agnostico wiki).
      - [x] `github.com/themetriost/Sertor` **NON** presente (URL non nel playbook).
- [x] Verifica che l'asset sia **host-agnostico** (VR-2): zero `.claude/`, zero slash-command,
      zero nomi prodotto/modello Claude.

---

## Fase 3 — US6 — Sync dogfood↔bundle (1 task)

> Prerequisiti: TASK-US2-02 (wiki-playbook sotto `assets/claude/**`, unico file che richiede re-sync).
> Gli altri asset toccati stanno sotto `assets/` (top-level) o `assets/rag/` → non sincronizzati
> in `.claude/` (research.md §Impatto sul sync dogfood). Bloccante per TASK-P01 (sync guard).

### TASK-US6-01 — Re-sync dogfood: `python -m sertor_installer.sync`

**File**: `.claude/skills/wiki-author/wiki-playbook.md` (RE-SYNC automatico)
→ dipende da: TASK-US2-02

**Mappa FR**: FR-011 · CS-6 · US6 · data-model §E6 · contracts/guard.md G7

- [x] Dopo aver completato TASK-US2-02, esegui il comando di sync:
      ```powershell
      uv run python -m sertor_installer.sync
      ```
      Questo riallinea `.claude/skills/wiki-author/wiki-playbook.md` (copia dogfood) con
      `packages/sertor/src/sertor_installer/assets/claude/skills/wiki-author/wiki-playbook.md`
      (sorgente canonica modificata).
- [x] Verifica byte-parità: le due copie devono essere identiche dopo il sync.
      ```powershell
      # Verifica manuale: se il sync ha prodotto modifiche allo stato git, le diff devono essere
      # solo a .claude/skills/wiki-author/wiki-playbook.md e riflettere esattamente le stesse
      # modifiche applicate alla sorgente canonica.
      ```
- [x] Esegui la guardia di sync (G7) per verifica immediata:
      ```powershell
      uv run pytest tests/unit/test_assets_sync.py -q
      ```
      Deve essere verde. La guardia verifica byte-parità di tutti gli asset sotto `assets/claude/**`
      nelle copie dogfood `.claude/` — quindi copre il wiki-playbook.
- [x] Verifica che gli altri asset toccati (RAG block, wiki block, `guided-setup`, reference)
      NON abbiano generato copie dogfood non volute sotto `.claude/`: questi file stanno sotto
      `assets/` top-level o `assets/rag/`, non sotto `assets/claude/**`, quindi il sync non li tocca.

---

## Fase 4 — US3/US5/US7 — Guardie di test (3 task, [P])

> Prerequisiti: tutte le Fasi 0–3 (i test verificano i body modificati).
> I 3 task sono parallelizzabili tra loro [P] (file distinti, nessuna dipendenza reciproca).
> Bloccanti per TASK-P01.
>
> **Convenzione comune:**
> - Test offline: nessuna rete, nessun `uv run`, nessun processo reale.
> - Usare `read_asset_text(rel)` (sertor package) o `read_asset_text("sertor_flow", rel)` (flow).
> - Marker: nessun `@pytest.mark.cloud`; test standard veloci.

### TASK-US7-01 [P] — Rework `test_assets_cli_invocation.py` (G1/G2/G3/G5)

**File**: `packages/sertor/tests/test_assets_cli_invocation.py` (MODIFICA/REWORK)
→ dipende da: TASK-F01, TASK-US1-01, TASK-US2-01, TASK-US2-02

**Mappa FR**: FR-005/012/015 · CS-1/CS-2/CS-4 · US2/US7 · contracts/guard.md G1/G2/G3/G5

- [x] Apri `packages/sertor/tests/test_assets_cli_invocation.py`.
      Leggi l'intero file per capire le costanti e la struttura corrente.

**1. Aggiorna `_CANONICAL_GUIDE_ASSETS` (G5 rework test_canonical_guide):**
- [x] Cambia `_CANONICAL_GUIDE_ASSETS` da `(_RAG_USAGE, _GUIDED_SETUP)` a una tupla che contiene
      solo il reference canonico:
      ```python
      _CLI_REFERENCE = "rag/sertor-cli-reference.md"
      _CANONICAL_GUIDE_ASSETS = (_CLI_REFERENCE,)
      ```
      (La costante `_CLI_REFERENCE` è usata anche da G2/G3/G4.)

**2. Aggiungi `_CLI_REFERENCE` a `_INVOKING_ASSETS` (footgun check):**
- [x] Aggiungi `_CLI_REFERENCE` alla tupla `_INVOKING_ASSETS` (il reference deve usare la forma
      robusta `uv run --project .sertor` e non avere bare invocations):
      ```python
      _INVOKING_ASSETS = (
          _RAG_USAGE,
          _GUIDED_SETUP,
          _WIKI_PLAYBOOK,
          _CLI_REFERENCE,   # aggiunto: il reference è un asset agent-facing che invoca CLI
          _EVAL_SUITE,
          _EVAL_FEEDBACK,
          _CONCIERGE,
          # ... resto invariato
      )
      ```
      Questo fa sì che `test_invoking_assets_carry_robust_form` e `test_no_bare_invocations_in_invoking_assets`
      coprano automaticamente il nuovo asset (nessuna modifica ai test stessi).

**3. Rework `test_canonical_guide_present_where_first_invoked` (G5):**
- [x] Modifica il test: la guida completa deve essere in `sertor-cli-reference.md` (non più in
      `_RAG_USAGE` e `_GUIDED_SETUP`); queste ultime sedi devono contenere il pointer, non la copia:
      ```python
      def test_canonical_guide_present_where_first_invoked():
          """La guida completa 'How to invoke' vive SOLO in sertor-cli-reference.md (CS-2)."""
          ref_body = read_asset_text(_CLI_REFERENCE)
          assert "How to invoke Sertor's commands" in ref_body, _CLI_REFERENCE
          assert _ROBUST in ref_body, _CLI_REFERENCE
          assert "uvx --from" in ref_body, _CLI_REFERENCE
          assert "not on `PATH`" in ref_body or "not on PATH" in ref_body, _CLI_REFERENCE
          # Le altre sedi contengono il pointer, non la copia:
          for asset in (_RAG_USAGE, _GUIDED_SETUP):
              body = read_asset_text(asset)
              assert "How to invoke Sertor's commands" not in body, (
                  f"{asset}: contiene ancora la sezione inline (deve essere un pointer)"
              )
              assert "`sertor-cli-reference.md`" in body, (
                  f"{asset}: manca il pointer a sertor-cli-reference.md"
              )
      ```

**4. Rework `test_wiki_playbook_ships_runtime_invocation_guide` (G5):**
- [x] Modifica il test: verifica la forma minima §2 + assenza della sottosezione + Windows note:
      ```python
      def test_wiki_playbook_ships_runtime_invocation_guide():
          """Il wiki playbook porta solo la forma minima; la sottosezione completa è rimossa (CS-2)."""
          body = read_asset_text(_WIKI_PLAYBOOK)
          # Forma robusta minima conservata (§2, auto-contenimento wiki-only):
          assert _ROBUST in body
          assert "not on `PATH`" in body or "not on PATH" in body
          # La sottosezione «How to invoke the runtime CLIs» deve essere ASSENTE:
          assert "How to invoke the runtime CLIs" not in body, (
              "wiki-playbook contiene ancora la sottosezione inline: deve essere rimossa"
          )
          # Windows note deve essere ASSENTE:
          assert "pywin32_bootstrap" not in body, (
              "wiki-playbook contiene ancora la Windows note: deve essere rimossa"
          )
          # Invarianti host-agnostici:
          assert "uvx --from" not in body
          assert "github.com/themetriost/Sertor" not in body
      ```

**5. Aggiungi test G1 (non-reintroduzione nei blocchi):**
- [x] Aggiungi un nuovo test che verifica che i blocchi always-on NON contengano la sezione inline:
      ```python
      _WIKI_BLOCK = "claude-md-block.md"

      def test_no_invoke_section_inline_in_blocks():
          """G1: i tre claude-md-block*.md non contengono la sezione 'How to invoke' inline (REQ-012)."""
          for asset in (_RAG_USAGE, _WIKI_BLOCK):
              body = read_asset_text(asset)
              assert "How to invoke Sertor's commands" not in body, (
                  f"{asset}: contiene la sezione inline (deve essere rimossa)"
              )
              assert "pywin32_bootstrap" not in body, (
                  f"{asset}: contiene la Windows note (deve essere rimossa)"
              )
              assert "uvx --from" not in body, (
                  f"{asset}: contiene l'invocazione installer (deve essere rimossa)"
              )
      ```

**6. Aggiungi test G2 (fonte unica):**
- [x] Aggiungi un nuovo test che verifica che la sezione completa esista in esattamente un asset:
      ```python
      def test_invoke_section_exists_in_exactly_one_asset():
          """G2: 'How to invoke Sertor's commands' + Windows note in ESATTAMENTE un asset (CS-2)."""
          from sertor_installer.resources import iter_asset_dir
          all_md = [
              p for p in iter_asset_dir("")   # o la funzione equivalente per enumerare tutti gli asset
              if p.endswith(".md")
          ]
          # Alternativa senza iter_asset_dir: lista esplicita degli asset distribuiti rilevanti
          _CANDIDATE_ASSETS = (
              _RAG_USAGE, _GUIDED_SETUP, _WIKI_PLAYBOOK, _CLI_REFERENCE, _WIKI_BLOCK,
              _EVAL_SUITE, _EVAL_FEEDBACK, _CONCIERGE,
              "claude/skills/wiki-author/SKILL.md",
              "claude/commands/wiki.md",
              "claude/agents/wiki-curator.md",
          )
          heading = "How to invoke Sertor's commands"
          hits_heading = [a for a in _CANDIDATE_ASSETS if heading in read_asset_text(a)]
          assert hits_heading == [_CLI_REFERENCE], (
              f"L'heading '{heading}' deve essere in esattamente 1 asset ({_CLI_REFERENCE}), "
              f"trovato in: {hits_heading}"
          )
          note_hits = [a for a in _CANDIDATE_ASSETS if "pywin32_bootstrap" in read_asset_text(a)]
          assert note_hits == [_CLI_REFERENCE], (
              f"pywin32_bootstrap deve essere in esattamente 1 asset ({_CLI_REFERENCE}), "
              f"trovato in: {note_hits}"
          )
      ```
      Nota: se `iter_asset_dir` non esiste o non elenca tutti i tipi di asset, usa la lista esplicita
      `_CANDIDATE_ASSETS` sopra che copre tutti gli asset agent-facing rilevanti.

**7. Aggiungi test G3 (pointer presenti):**
- [x] Aggiungi un nuovo test che verifica che i pointer siano nei body che ne hanno bisogno:
      ```python
      def test_pointers_present_in_reduced_bodies():
          """G3: i body ridotti contengono i pointer attesi (REQ-014/015)."""
          rag_body = read_asset_text(_RAG_USAGE)
          assert "`sertor-cli-reference.md`" in rag_body, (
              f"{_RAG_USAGE}: manca il pointer a sertor-cli-reference.md"
          )
          wiki_block_body = read_asset_text(_WIKI_BLOCK)
          assert "`wiki-playbook.md`" in wiki_block_body, (
              f"{_WIKI_BLOCK}: manca il riferimento per nome a wiki-playbook.md"
          )
          guided_setup_body = read_asset_text(_GUIDED_SETUP)
          assert "`sertor-cli-reference.md`" in guided_setup_body, (
              f"{_GUIDED_SETUP}: manca il pointer a sertor-cli-reference.md"
          )
      ```

- [x] Verifica che `test_rag_usage_block_uv_run_replaces_bare_search` sia ancora verde
      (la forma `uv run --project .sertor sertor-rag search` è conservata nel RAG block, C1).
- [x] Verifica che `test_invoking_assets_carry_robust_form` sia ancora verde su tutti gli asset
      incluso il nuovo `_CLI_REFERENCE` (necessita che F01 abbia incluso la forma robusta, C4).
- [x] Esegui localmente tutti i test del file per conferma verde:
      ```powershell
      uv run pytest packages/sertor/tests/test_assets_cli_invocation.py -v
      ```

---

### TASK-US7-02 [P] — Estendi `test_assets_copilot_parity.py` (G4/G6)

**File**: `packages/sertor/tests/test_assets_copilot_parity.py` (MODIFICA)
→ dipende da: TASK-F01, TASK-F02

**Mappa FR**: FR-003/004/006/010 · CS-3/CS-5 · US3/US5/US7 · contracts/guard.md G4/G6

- [x] Apri `packages/sertor/tests/test_assets_copilot_parity.py`. Leggi la struttura esistente
      (in particolare le funzioni `_rag_plan`, `_render_rag`, `_rendered_bodies`, e il pattern
      delle closure `_usability_closure_offenders`).
- [x] Aggiungi la costante per il basename del reference (necessaria per la closure check):
      ```python
      _CLI_REFERENCE_BASENAME = "sertor-cli-reference.md"
      ```
- [x] Aggiungi la funzione helper di closure per il reference (G4):
      ```python
      def _reference_closure_offenders(plan: list, render) -> list[str]:
          """G4: ogni body RAG che cita `sertor-cli-reference.md` deve trovarlo depositato nel piano.

          Gemello di `_usability_closure_offenders`: il basename del reference deve essere
          in {Path(t.target_rel).name for t in plan} perché `build_rag_plan` lo deposita
          come FILE in `.sertor/sertor-cli-reference.md` (TASK-F02). Se il piano non lo deposita,
          la closure nomina il body offendente.
          """
          deposited = {Path(t.target_rel).name for t in plan if t.source is not None}
          out = []
          for target_rel, _src, body in _rendered_bodies(plan, render):
              if f"`{_CLI_REFERENCE_BASENAME}`" in body and _CLI_REFERENCE_BASENAME not in deposited:
                  out.append(target_rel)
          return out
      ```
      Nota: `_rendered_bodies` e `_rag_plan` (helper per costruire il piano con `tmp_path`) devono
      essere già presenti nel file — riusali; adatta i nomi alla loro firma reale.
- [x] Aggiungi un test che verifica la closure per entrambi gli assistenti (G4):
      ```python
      def test_cli_reference_closure_in_rag_plan(tmp_path):
          """G4: il reference sertor-cli-reference.md è depositato dal piano RAG
          (sia Claude che Copilot CLI) quando è citato per nome nei body (CS-3/NFR-5)."""
          claude_plan = _rag_plan(AssistantId.CLAUDE, tmp_path)
          copilot_plan = _rag_plan(AssistantId.COPILOT_CLI, tmp_path)
          assert _reference_closure_offenders(claude_plan, _render_rag) == [], (
              "Claude RAG plan: sertor-cli-reference.md citato ma non depositato"
          )
          assert _reference_closure_offenders(copilot_plan, _render_rag) == [], (
              "Copilot RAG plan: sertor-cli-reference.md citato ma non depositato"
          )
      ```
- [x] Aggiungi un test negativo (non-vacuità della guardia G4):
      ```python
      def test_cli_reference_closure_fails_if_not_deposited(tmp_path):
          """G4 negativo: un piano che non deposita il reference fa fallire la closure."""
          # Piano fittizio senza il FILE del reference ma con un body che lo cita:
          from sertor_installer.artifacts import Artifact, ArtifactKind, WriteStrategy
          fake_body_art = Artifact(
              ArtifactKind.MARKER_BLOCK,
              "rag/claude-md-block-rag-usage.md",  # cita sertor-cli-reference.md nel body
              ".claude/CLAUDE.md",
              WriteStrategy.APPEND_BLOCK,
          )
          plan_without_ref = [fake_body_art]  # manca il FILE del reference
          offenders = _reference_closure_offenders(plan_without_ref, _render_rag)
          assert offenders != [], "Il piano senza il reference avrebbe dovuto fallire la closure"
      ```
- [x] Verifica che i test di parità esistenti (G6) coprano il nuovo asset `sertor-cli-reference.md`
      **automaticamente**: le guardie (a) no `.claude/`, (b) no slash-command, (c) no nomi-Claude
      girano su tutti i body renderizzati del piano RAG, incluso il FILE del reference — se il
      reference viola VR-2, le guardie esistenti lo rileveranno senza modifiche. Verifica che
      non sia necessaria una modifica esplicita.
- [x] Esegui i test del file (G4 + non-regressione G6):
      ```powershell
      uv run pytest packages/sertor/tests/test_assets_copilot_parity.py -v
      ```

---

### TASK-US7-03 [P] — Aggiungi guard non-reintroduzione SDLC in `test_governance_assets_host_agnostic.py` (G1 gemello)

**File**: `packages/sertor-flow/tests/unit/test_governance_assets_host_agnostic.py` (MODIFICA)
→ dipende da: nessuno (SDLC block è invariato per costruzione; la guardia previene derive future)

**Mappa FR**: FR-012 · CS-2 · US7 · contracts/guard.md G1 · data-model §E5

- [x] Apri `packages/sertor-flow/tests/unit/test_governance_assets_host_agnostic.py`.
      Verifica il pattern di lettura asset già usato: `read_asset_text("sertor_flow", rel)` tramite
      `from sertor_install_kit import read_asset_text` con il parametro anchor.
      (Alternativa secondo contratto guard.md: `kit_read("sertor_flow", "claude-md-block-sdlc.md")`
      — usa la firma corretta che vedi nel file.)
- [x] Aggiungi un test di non-reintroduzione «How to invoke» nel blocco SDLC (G1 gemello):
      ```python
      def test_sdlc_block_has_no_invoke_section():
          """G1 gemello: il blocco SDLC non contiene 'How to invoke' (invariato, DA-D-r3).

          Il blocco SDLC (claude-md-block-sdlc.md) è a sola direttiva standing (fasi SpecKit,
          constitution gate, error discipline, version control). La sezione 'How to invoke' non è
          mai stata presente; questa guardia previene la ri-introduzione silenziosa.
          """
          sdlc_body = read_asset_text("sertor_flow", "claude-md-block-sdlc.md")
          assert "How to invoke" not in sdlc_body, (
              "claude-md-block-sdlc.md contiene 'How to invoke': non deve essere presente"
          )
          assert "pywin32_bootstrap" not in sdlc_body, (
              "claude-md-block-sdlc.md contiene la Windows note: non deve essere presente"
          )
      ```
      Adatta la chiamata di lettura alla firma effettiva che vedi nel file (potrebbe essere
      `read_asset_text("sertor_flow", "claude-md-block-sdlc.md")` oppure un helper diverso).
- [x] Aggiungi (opzionale ma consigliato) la verifica delle presenze obbligatorie del blocco SDLC
      per pin-regressione (contratto C3):
      ```python
      def test_sdlc_block_preserves_standing_content():
          """C3: il blocco SDLC conserva il contenuto minimo standing (REQ-016)."""
          sdlc_body = read_asset_text("sertor_flow", "claude-md-block-sdlc.md")
          assert "SpecKit" in sdlc_body or "speckit" in sdlc_body.lower(), (
              "Fasi SpecKit assenti dal blocco SDLC"
          )
          assert "Constitution Check" in sdlc_body or "constitution" in sdlc_body.lower(), (
              "Constitution Check assente dal blocco SDLC"
          )
          assert "fix, don't suppress" in sdlc_body or "Error discipline" in sdlc_body, (
              "Error discipline assente dal blocco SDLC"
          )
      ```
- [x] Esegui i test del file:
      ```powershell
      uv run pytest packages/sertor-flow/tests/unit/test_governance_assets_host_agnostic.py -v
      ```

---

## Fase 5 — Polish e cross-cutting (2 task)

> Prerequisiti: tutte le Fasi 0–4 complete. TASK-P01 [P] (non dipende da altri polish).
> TASK-P02 dipende da TASK-P01.

### TASK-P01 [P] — Suite verde totale + lint ruff

→ dipende da: tutte le Fasi 0-4

**Mappa FR**: RNF-1/2/3 · CS-1..6

- [x] **Guardie nuove/rework (CS-2/CS-3/CS-4):**
      ```powershell
      uv run pytest packages/sertor/tests/test_assets_cli_invocation.py -v
      uv run pytest packages/sertor/tests/test_assets_copilot_parity.py -v
      uv run pytest packages/sertor-flow/tests/unit/test_governance_assets_host_agnostic.py -v
      ```
      Tutti devono essere verdi (G1/G2/G3/G4/G5/G6/G7 test).
- [x] **Sync dogfood (CS-6, G7):**
      ```powershell
      uv run pytest tests/unit/test_assets_sync.py -v
      ```
      Deve essere verde dopo il sync di TASK-US6-01 (wiki-playbook dogfood in byte-parità).
- [x] **Quickstart altitude (CS-1):**
      ```powershell
      (Get-Content packages/sertor/src/sertor_installer/assets/claude-md-block.md).Count
      (Get-Content packages/sertor/src/sertor_installer/assets/rag/claude-md-block-rag-usage.md).Count
      (Get-Content packages/sertor-flow/src/sertor_flow/assets/claude-md-block-sdlc.md).Count
      ```
      Totale deve essere misurabilmente < 208 righe (~166 atteso; SDLC invariato a 65).
- [x] **Non-regressione suite completa sertor (RNF-3):**
      ```powershell
      uv run pytest packages/sertor/tests/ -m "not cloud" -q
      ```
      Verifica che `test_assets_copilot_parity.py` e `test_surface_parity.py` restino verdi.
- [x] **Non-regressione suite completa kit (RNF-3):**
      ```powershell
      uv run pytest packages/sertor-install-kit/tests/ -m "not cloud" -q
      ```
- [x] **Non-regressione suite completa sertor-flow (RNF-3):**
      ```powershell
      uv run pytest packages/sertor-flow/tests/ -m "not cloud" -q
      ```
- [x] **Suite root completa (RNF-3):**
      ```powershell
      uv run pytest -m "not cloud" -q
      ```
- [x] **Lint ruff sui file toccati:**
      ```powershell
      uv run ruff check `
          packages/sertor/src/sertor_installer/install_rag.py `
          packages/sertor/tests/test_assets_cli_invocation.py `
          packages/sertor/tests/test_assets_copilot_parity.py `
          packages/sertor-flow/tests/unit/test_governance_assets_host_agnostic.py
      ```
      Zero errori (regole E,F,I,UP,B; line-length 100).
- [x] **Quickstart fonte unica (CS-2, verifica manuale):**
      ```powershell
      Select-String -Path packages/sertor/src/sertor_installer/assets/**/*.md `
          -Pattern "How to invoke Sertor's commands"
      Select-String -Path packages/sertor/src/sertor_installer/assets/**/*.md `
          -Pattern "pywin32_bootstrap"
      ```
      Entrambi SOLO in `rag/sertor-cli-reference.md`.

---

### TASK-P02 — Verifica CS-1..6 e additività trasversale

→ dipende da: TASK-P01

- [x] **CS-1 (altitude ridotta):** totale righe dei 3 blocchi always-on < 208 (stima ~166);
      nessun dettaglio operativo lookup-on-demand inline nei blocchi RAG e wiki. ✓
- [x] **CS-2 (fonte unica «How to invoke»):** `How to invoke Sertor's commands` in esattamente
      1 asset (`sertor-cli-reference.md`); `pywin32_bootstrap` idem; blocco RAG, `guided-setup` e
      `wiki-playbook` contengono pointer/frase condizionale, non la copia inline. Test G2 verde. ✓
- [x] **CS-3 (nessun pointer rotto):** test G4 verde per Claude e Copilot CLI; il reference è
      depositato dal piano RAG (`build_rag_plan`) in `.sertor/sertor-cli-reference.md`; il
      `wiki-playbook` non cita il basename del reference (no pointer morto su install solo-wiki). ✓
- [x] **CS-4 (contenuto load-bearing preservato):**
      - Blocco RAG: vehicle-only + search-first + `uv run --project .sertor sertor-rag search` +
        MCP-error + memory-gate + pointer `sertor-cli-reference.md`. Test G3 verde. ✓
      - Blocco wiki: golden rule + step outline + delegation + D↔N + pointer `wiki-playbook.md`.
        Test G3 verde. ✓
      - Blocco SDLC: fasi SpecKit + constitution gate + error discipline + version-control. Invariato. ✓
- [x] **CS-5 (parità host-agnostica):** test `test_assets_copilot_parity.py` verde su tutti gli
      asset modificati e sul nuovo reference (zero `.claude/`, zero slash-command, zero nomi-Claude).
      Test G6 verde (guardia già esistente, nessuna modifica). ✓
- [x] **CS-6 (sync dogfood):** `tests/unit/test_assets_sync.py` verde dopo il sync; copia
      `.claude/skills/wiki-author/wiki-playbook.md` in byte-parità con la sorgente canonica. ✓
- [x] **Additività core — invarianza `sertor_core`:** verifica che nessun file in `src/sertor_core/`
      sia stato modificato. Zero import di `sertor_core` in `install_rag.py` (unica modifica di codice). ✓
- [x] **Additività installer — nessun nuovo seam:** verifica che non siano stati introdotti nuovi
      `ArtifactKind`, `WriteStrategy`, `Surface`, porte o dipendenze esterne. Solo il nuovo asset
      `.md` e 1 riga di `Artifact(FILE, …)` in `install_rag.py`. ✓
- [x] **Blocco SDLC invariato:** verifica che `packages/sertor-flow/src/sertor_flow/assets/claude-md-block-sdlc.md`
      non sia stato modificato (DA-D-r3). Test G1 gemello (US7-03) verde. ✓
- [x] **Non-regressione installabilità (RNF-4):** verifica che `sertor install rag` (o il
      test di piano equivalente in `test_non_regression_claude.py`) includa il nuovo Artifact del
      reference e che il piano owned-check (`plan ⊆ owned`) resti verde (`.sertor` owned_dir). ✓
- [x] Segnala come **follow-up non-bloccante** (già a casa durevole):
      - Dedup mini-note eval (`eval-suite-author`/`eval-feedback`) → FEAT-022.
      - Budget altitude in CI (freno deterministico) → FEAT-024.
      - Stub `assets/copilot/**` → FEAT-023.
      Il done offline è raggiunto con i task precedenti (quickstart §1-7 verificati).

---

## Grafo delle dipendenze (sintesi)

```
TASK-F01 [P]  (sertor-cli-reference.md NUOVO, asset canonico)  ────────────────────────┐
                                                                                        │
TASK-F02      (install_rag.py: Artifact FILE) ← F01             ──────────────────┐    │
                                                                                   │    │
TASK-US1-01 [P]  (RAG block C1 ridotto + pointer) ← F01        ──────────────┐   │    │
TASK-US1-02 [P]  (wiki block C2 ridotto + pointer) ← —          ──────────┐  │   │    │
                                                                            │  │   │    │
TASK-US2-01 [P]  (guided-setup C5 dedup + pointer) ← F01        ──────┐   │  │   │    │
TASK-US2-02 [P]  (wiki-playbook C6 dedup) ← —                   ──┐   │   │  │   │    │
                                                                   │   │   │  │   │    │
TASK-US6-01      (sync dogfood) ← US2-02                    ──┐   │   │   │  │   │    │
                                                               │   │   │   │  │   │    │
TASK-US7-01 [P]  (test_assets_cli_invocation rework G1/G2/G3/G5)  │   │   │  │   │    │
             ← F01, US1-01, US2-01, US2-02                    ──┤   │   │   │  │   │    │
TASK-US7-02 [P]  (test_assets_copilot_parity G4/G6) ← F01, F02 ──┤   │   │   │  │   │    │
TASK-US7-03 [P]  (test_governance SDLC guard G1) ← —           ──┘   │   │   │  │   │    │
                                                                       │   │   │  │   │    │
TASK-P01 [P]  (suite verde totale + lint) ← US7-01..03, US6-01  ──────┘   │   │  │   │    │
        │                                                                   │   │  │   │    │
TASK-P02      (CS-1..6 + additività) ← P01                         ────────┘   │  │   │    │
                                                                                │  │   │    │
              (sertor_core invariato)                                ────────────┘  │   │    │
              (SDLC block invariato)                                 ───────────────┘   │    │
              (nessun nuovo ArtifactKind/Surface/seam)              ────────────────────┘    │
              (test_assets_sync.py invariata)                       ─────────────────────────┘
```

---

## Criteri di test indipendenti per User Story

| US | Criterio di test indipendente | Task principali | Natura |
|---|---|---|---|
| **US1** (blocchi caricano meno contesto) | Misura righe dei 3 blocchi: totale < 208; nessuna sezione lookup-on-demand inline nei blocchi RAG e wiki. Test G1 verde (assenza sezione nei blocchi). | TASK-US1-01, TASK-US1-02, TASK-US7-01 | MISURA + MECCANICO |
| **US2** («How to invoke» in una sola fonte) | Test G2 verde: heading + `pywin32_bootstrap` in esattamente 1 asset (`sertor-cli-reference.md`). Test G5 rework: `_RAG_USAGE`/`_GUIDED_SETUP` hanno pointer, non copia; `wiki-playbook` ha assenza heading. | TASK-F01, TASK-US1-01, TASK-US2-01, TASK-US2-02, TASK-US7-01 | MECCANICO (asset check) |
| **US3** (nessun pointer rotto) | Test G4 verde per Claude e Copilot CLI: closure `sertor-cli-reference.md` verificata offline. `wiki-playbook` non cita il basename → nessun pointer morto su install solo-wiki. | TASK-F02, TASK-US7-02 | MECCANICO (piano offline) |
| **US4** (nessuna direttiva load-bearing persa) | Test G3 verde: pointer `sertor-cli-reference.md` nel RAG block e in `guided-setup`; pointer `wiki-playbook.md` nel wiki block. Verifica manuale presenze C1/C2/C3 (vehicle-only, search-first, MCP-error, memory-gate, golden rule, step outline, delegation, D↔N, fasi SpecKit). | TASK-US1-01, TASK-US1-02, TASK-US7-01 | MECCANICO + MANUALE |
| **US5** (parità Claude↔Copilot host-agnostica) | Test G6 verde: `test_assets_copilot_parity.py` verde su tutti gli asset modificati e sul reference (zero `.claude/`, zero slash-command, zero nomi-Claude). Test G4 verde su Copilot CLI (reference depositato). | TASK-F01, TASK-F02, TASK-US7-02 | MECCANICO (piano + parità) |
| **US6** (sync dogfood verde) | `tests/unit/test_assets_sync.py` verde dopo `python -m sertor_installer.sync`: copia dogfood `.claude/skills/wiki-author/wiki-playbook.md` in byte-parità con la sorgente canonica. | TASK-US2-02, TASK-US6-01 | MECCANICO (byte-parità) |
| **US7** (guardia non-reintroduzione) | G1 verde: nei blocchi always-on assente `How to invoke Sertor's commands`/`pywin32_bootstrap`/`uvx --from`. G1 gemello SDLC verde. G2 verde: fonte unica. Reintroducendo la sezione inline, almeno un test fallisce (non-vacuità). | TASK-US7-01, TASK-US7-03 | MECCANICO (assert testuale) |

---

## Parallelizzazione consigliata (MVP)

**Sprint 1 — nessun prerequisito (massima parallelizzazione):**
- TASK-F01 [P] (sertor-cli-reference.md — fondazionale, non blocca US1-02/US2-02)
- TASK-US1-02 [P] (wiki block ridotto — non dipende da F01, pointer a wiki-playbook esistente)
- TASK-US2-02 [P] (wiki-playbook dedup — non dipende da F01, frase condizionale senza filename)
- TASK-US7-03 [P] (guard SDLC — non dipende da asset changes, SDLC è invariato)

**Sprint 2 — dopo TASK-F01:**
- TASK-F02 (install_rag.py: Artifact FILE ← F01)
- TASK-US1-01 [P] (RAG block ridotto + pointer ← F01)
- TASK-US2-01 [P] (guided-setup dedup + pointer ← F01)

**Sprint 3 — dopo Sprint 2 completo (F01+F02+US1-01/02+US2-01/02):**
- TASK-US6-01 (sync dogfood ← US2-02)
- TASK-US7-01 [P] (rework test_assets_cli_invocation ← F01+US1-01+US2-01+US2-02)
- TASK-US7-02 [P] (extend test_assets_copilot_parity ← F01+F02)

**Sprint finale — dopo Sprint 3 completo:**
- TASK-P01 [P] (suite verde totale + lint)
- TASK-P02 (CS-check + additività)

---

## Brief di commit (per il `configuration-manager`)

```
docs(tasks): genera tasks.md per E10-FEAT-021 — altitude blocchi CLAUDE.md + fonte unica «How to invoke»

Fase SpecKit "tasks" completata per specs/079-altitude-claude-md.
12 task in 6 fasi:
  Fase 0 Fondazionale (2 task):
    TASK-F01 [P]  assets/rag/sertor-cli-reference.md NUOVO — asset canonico «How to invoke»
                  (heading + runtime `uv run --project` + installer `uvx --from` + Windows note
                  `pywin32_bootstrap`; host-agnostico, invarianti C4)
    TASK-F02      install_rag.py — Artifact(FILE, "rag/sertor-cli-reference.md",
                  ".sertor/sertor-cli-reference.md", CREATE_IF_ABSENT) in build_rag_plan;
                  owned da .sertor owned_dir (lifecycle corretto)
  Fase 1 US1/US4 — Riduzione blocchi always-on (2 task, [P]):
    TASK-US1-01 [P]  rag/claude-md-block-rag-usage.md — rimuove sezione «How to invoke» (righe 12-38)
                     + pointer `sertor-cli-reference.md`; conserva vehicle-only + search-first +
                     `uv run --project .sertor sertor-rag search` + MCP-error + memory-gate (C1)
    TASK-US1-02 [P]  claude-md-block.md — rimuove wiki operations enumeration + Conventions;
                     aggiunge pointer `wiki-playbook.md`; conserva golden rule + step outline +
                     delegation + D↔N (C2)
  Fase 2 US2 — Dedup skill (2 task, [P]):
    TASK-US2-01 [P]  guided-setup/SKILL.md — rimuove sezione inline «How to invoke» (righe 52-78)
                     + pointer `sertor-cli-reference.md`; logica Step 0-6 intatta (C5)
    TASK-US2-02 [P]  claude/skills/wiki-author/wiki-playbook.md — rimuove sottosezione
                     «How to invoke the runtime CLIs» + Windows note; conserva forma minima §2 +
                     frase condizionale senza filename (closure-safe, C6)
  Fase 3 US6 — Sync dogfood (1 task):
    TASK-US6-01      python -m sertor_installer.sync → .claude/skills/wiki-author/wiki-playbook.md
                     in byte-parità; tests/unit/test_assets_sync.py verde (G7)
  Fase 4 US3/US5/US7 — Guardie di test (3 task, [P]):
    TASK-US7-01 [P]  packages/sertor/tests/test_assets_cli_invocation.py — rework:
                     _CANONICAL_GUIDE_ASSETS=(_CLI_REFERENCE,); aggiunge _CLI_REFERENCE a
                     _INVOKING_ASSETS; rework test_canonical_guide + test_wiki_playbook;
                     aggiunge test G1 (non-reintroduzione) + G2 (fonte unica) + G3 (pointer)
    TASK-US7-02 [P]  packages/sertor/tests/test_assets_copilot_parity.py — estende:
                     _reference_closure_offenders() + test_cli_reference_closure_in_rag_plan
                     (Claude + Copilot) + test negativo non-vacuità (G4/G6)
    TASK-US7-03 [P]  packages/sertor-flow/tests/unit/test_governance_assets_host_agnostic.py —
                     aggiunge test_sdlc_block_has_no_invoke_section + test_sdlc_block_preserves_standing_content
                     (G1 gemello SDLC, C3)
  Fase 5 Polish/cross-cutting (2 task):
    TASK-P01 [P]  suite verde totale (sertor/kit/flow/root) + lint ruff; quickstart altitude
                  (righe < 208) + fonte unica (Select-String)
    TASK-P02      CS-1..6 + additività trasversale; segnala follow-up F022/023/024

Natura: ADDITIVO / igiene host-facing. ZERO codice runtime di core. sertor_core INVARIATO.
Blocco SDLC INVARIATO (DA-D-r3). ZERO nuovi ArtifactKind/WriteStrategy/Surface/seam del kit.
Artefatti toccati:
  - 1 asset Markdown NUOVO (sertor-cli-reference.md, bundle RAG)
  - 1 funzione esistente modificata (build_rag_plan in install_rag.py: +1 Artifact FILE)
  - 2 blocchi always-on ridotti (claude-md-block-rag-usage.md, claude-md-block.md)
  - 2 skill deduplicatate (guided-setup/SKILL.md, wiki-playbook.md)
  - 1 copia dogfood re-syncata (.claude/skills/wiki-author/wiki-playbook.md)
  - 3 file di test (rework cli_invocation + extend copilot_parity + extend governance_host_agnostic)
Copertura: FR-001..015, RNF-1..6, CS-1..6, US1..7.
Constitution CHECK: PASS 12/12 + missione (budget di contesto protetto, fonte unica, parità).
Nessun hook SpecKit eseguito (script assenti nel repo); nessuna operazione git.
Template tasks da 078 (setup-plan.ps1/SKILL.md assenti nel repo).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

**File da includere nel commit:**
- `specs/079-altitude-claude-md/tasks.md` (questo file, nuovo)
