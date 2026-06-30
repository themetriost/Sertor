# Feature Specification: Rimuovere lo stub fuorviante `assets/copilot/` (E10-FEAT-023)

**Feature Branch**: `081-stub-copilot` · **Created**: 2026-06-30 · **Status**: Draft

<!-- Deriva da: FEAT-023 (epica debito-tecnico E10) — requirements/debito-tecnico/stub-copilot/requirements.md (audit asset first-party 2026-06-26, ISSUE-09) -->

**Input**: FEAT-023 dell'epica `debito-tecnico` (E10). Il tree
`packages/sertor/src/sertor_installer/assets/copilot/` contiene **solo quattro file `.gitkeep`** —
uno per ciascuna delle quattro directory vuote `agents/`, `hooks/`, `instructions/`, `prompts/`. Le
cartelle furono create in FEAT-044 (`044-distribuzione-copilot`) quando si ipotizzava di depositarvi
asset statici Copilot; in FEAT-049 (`049-compatibilita-copilot`) i file JSON allora presenti
(`wiki.hooks.json`, `rag-usage.hooks.json`) furono **rimossi** e sostituiti dalla generazione a
runtime nativa, perché erano in formato Claude invece che Copilot. Da allora il tree è rimasto vuoto.
Lo stato reale verificato: **i payload Copilot sono generati interamente a runtime** da
`assets/claude/**` e `assets/rag/**` via funzioni pure in `sertor_install_kit.surfaces`
(`render_copilot_hooks` per gli hook JSON, `render_custom_agent` per i custom-agent,
`render_prompt_file` per i prompt-file, byte-copy per i body skill); **nessun file Python legge un
percorso sotto `assets/copilot/`** (grep esaustivo, zero consumatori). Il valore: lo stub vuoto è
**fuorviante** — suggerisce a un manutentore che gli asset Copilot vivano lì come quelli di
`assets/claude/`, mentre l'architettura reale è generativa. Il guard test
`test_no_hand_maintained_copilot_prompt_bodies` già afferma che nessun body deve risiedere sotto
`copilot/`. Rimuovere il tree allinea lo stato del repo alla realtà senza aggiungere file da manutenere.

---

> **Allineamento alla missione (gate Constitution).** La stella polare di Sertor è la **qualità e
> realtà del contesto reso a chi legge il repo** — sia l'agente frontier sia il manutentore umano. Un
> tree di directory vuote sotto `assets/` è contesto **fuorviante**: comunica un'architettura (asset
> Copilot statici) che non esiste (generazione a runtime da sorgente Claude/rag). Rimuoverlo fa sì che
> lo stato del repo **rifletta la realtà**, coerente col principio che il contesto non deve disinformare.
> È puramente **igiene host-facing** sul confine **D↔N**: nessun codice del core, nessun LLM, nessun
> cambiamento di comportamento. Complementa FEAT-022 (pulizia stile delle skill distribuite): quella
> ripulisce i body, questa rimuove un artefatto di struttura ingannevole.

> **Natura del cambiamento: SOTTRATTIVA / igiene host-facing, ZERO codice di core.** La feature **non**
> modifica `sertor_core` né alcun comando/vehicle/porta/adapter/engine (Principio XI). **Non** modifica
> il codice di `surfaces.py`, `install_rag.py`, `install_wiki.py`, né `sertor_install_kit`. Tocca
> **esclusivamente** quattro file statici `.gitkeep` (e le quattro directory vuote che li contengono).
> **Zero cambiamento di comportamento** dell'installer per entrambi gli assistenti: la generazione dei
> payload Copilot resta 100% derivata a runtime da `assets/claude/**` e `assets/rag/**`, identica prima
> e dopo. La rimozione è puramente sottrattiva di file vuoti, non altera alcun piano d'installazione.

> **Decisione di scope — FISSATA (era la forca aperta §1.4 / DA-1 dei requirements).** La feature adotta
> l'**Opzione A — RIMOZIONE** del tree `assets/copilot/**` (i quattro `.gitkeep` + le quattro directory
> vuote + `assets/copilot/` stessa). L'**Opzione B (README «generato a runtime»)** è **scartata**:
> aggiungerebbe un file da manutenere che può divergere dalla realtà, e un `README.md` sotto
> `assets/copilot/` sarebbe esso stesso un body asset, **in contraddizione** col commento del guard test
> `test_no_hand_maintained_copilot_prompt_bodies`. La stessa informazione (architettura generativa) è
> già nel codice (`install_rag.py`) e nel test. Quindi **nessun file di rimpiazzo** dopo la rimozione.

> **Ancoraggio all'esistente (dato di partenza, non da progettare).** Lo stato su `master`: il tree
> `packages/sertor/src/sertor_installer/assets/copilot/{agents,hooks,instructions,prompts}/.gitkeep`
> (quattro file vuoti). Generazione Copilot: `render_copilot_hooks`/`render_custom_agent`/
> `render_prompt_file` in `sertor_install_kit.surfaces` (riesportate in `sertor_installer.surfaces`),
> orchestrate da `build_rag_plan` per `AssistantId.COPILOT_CLI`; sorgenti da `assets/claude/**` e
> `assets/rag/**`. Guardie esistenti: `packages/sertor/tests/test_assets_copilot_guard.py`
> (incl. `test_no_hand_maintained_copilot_prompt_bodies`),
> `packages/sertor/tests/test_assets_copilot_parity.py`, `tests/integration/test_packaging.py`.
> Packaging: hatchling include il package per glob ricorsivo (`packages = ["src/sertor_installer"]`,
> `packages/sertor/pyproject.toml`), non per lista esplicita di file → la rimozione di `.gitkeep` non
> richiede modifiche a `pyproject.toml`. I riferimenti **ancorano** i requisiti, non prescrivono il *come*.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Il manutentore non trova più directory vuote fuorvianti (P1, Must)
Un manutentore che esplora `packages/sertor/src/sertor_installer/assets/` non trova più il tree
`copilot/` con quattro sottocartelle vuote: lo stato del repo riflette la realtà (nulla vive sotto
`assets/copilot/`; i payload Copilot sono generati a runtime da `assets/claude/**` e `assets/rag/**`).

**Independent Test**: `git ls-files packages/sertor/src/sertor_installer/assets/copilot/` non produce
output; la directory `assets/copilot/` non esiste più nel tree del repo.

**Acceptance**:
1. **Given** il tree `assets/copilot/` con quattro `.gitkeep`, **When** lo si rimuove, **Then**
   `git ls-files .../assets/copilot/` restituisce zero righe.
2. **Given** la rimozione dei `.gitkeep`, **When** la si applica, **Then** anche le quattro directory
   ora vuote (`agents/`, `hooks/`, `instructions/`, `prompts/`) e `assets/copilot/` stessa scompaiono
   dal tree del repo.
3. **Given** lo stato post-rimozione, **When** si esplora `assets/`, **Then** restano solo `claude/` e
   `rag/` (le sorgenti reali); nessuna directory vuota di Copilot.

### User Story 2 — Nessun file di rimpiazzo viene aggiunto (P2, Should)
Dopo la rimozione non viene introdotto alcun file sostitutivo (README, marker o altro asset) sotto
`assets/copilot/`: lo stato corretto è l'**assenza** della directory, coerente con la meccanica
generativa e col guard test che vieta body asset sotto `copilot/`.

**Independent Test**: dopo la modifica, `git ls-files` non mostra alcun file nuovo sotto un percorso
`assets/copilot/`; nessun `README.md`, marker o asset è stato creato lì.

**Acceptance**:
1. **Given** la rimozione del tree, **When** si verifica il diff, **Then** non compare alcun file
   aggiunto sotto `assets/copilot/`.
2. **Given** la decisione di scope (Opzione A), **When** si chiude la feature, **Then** la directory
   `assets/copilot/` resta inesistente, non sostituita da un README.

### User Story 3 — La generazione Copilot resta invariata (P1, Must)
`build_rag_plan` invocato con `AssistantId.COPILOT_CLI` continua a produrre lo **stesso** insieme di
artefatti host-facing di prima: hook JSON generati, body skill byte-copiati, custom-agent renderizzati,
blocchi istruzione — tutti derivati esclusivamente da `assets/claude/**` e `assets/rag/**`. Il
comportamento dell'installer è byte-identico prima e dopo.

**Independent Test**: i test di installazione Copilot (`test_install_rag_copilot_cli.py` o equivalenti)
restano verdi; il piano generato per `copilot-cli` contiene gli stessi artefatti di prima.

**Acceptance**:
1. **Given** la rimozione dello stub, **When** si genera il piano `build_rag_plan(copilot-cli)`,
   **Then** l'insieme degli artefatti (hook JSON, skill body, agent, blocchi istruzione) è identico a
   prima della modifica.
2. **Given** che la generazione Copilot non legge mai `assets/copilot/`, **When** si rimuove la
   directory, **Then** nessun artefatto cambia e nessun percorso sorgente si rompe.
3. **Given** la verifica zero-consumatori (§1.2 requirements), **When** si applica la rimozione,
   **Then** non è richiesta alcuna modifica al codice Python (`surfaces.py`/`install_rag.py`).

### User Story 4 — Build e packaging non si rompono (P1, Must)
La build del pacchetto `sertor` (`uv build`) completa senza errori e il wheel prodotto non richiede la
presenza di file sotto `assets/copilot/`: hatchling include il package per glob ricorsivo, non per lista
esplicita.

**Independent Test**: `uv build` (pacchetto `sertor`) completa senza errori; il test di packaging
(`tests/integration/test_packaging.py`) resta verde; nessuna modifica a `pyproject.toml` è necessaria.

**Acceptance**:
1. **Given** la rimozione dei `.gitkeep`, **When** si esegue `uv build` per `sertor`, **Then** la build
   completa senza errori e il wheel è prodotto correttamente.
2. **Given** l'inclusione hatchling per glob ricorsivo, **When** si rimuove `assets/copilot/`, **Then**
   il `pyproject.toml` non richiede aggiornamenti.
3. **Given** il test di packaging, **When** gira dopo la modifica, **Then** resta verde (il wheel non
   dipende da file sotto `assets/copilot/`).

### User Story 5 — Le suite e le guardie esistenti restano verdi (P1, Must)
Tutte le suite di test esistenti (`sertor`, `sertor-install-kit`, `sertor-flow`, root) restano verdi
dopo la rimozione: in particolare `test_assets_copilot_guard.py` (incl.
`test_no_hand_maintained_copilot_prompt_bodies`) e `test_assets_copilot_parity.py`, che non leggono da
`assets/copilot/` né verificano l'esistenza dei `.gitkeep`.

**Independent Test**: `uv run pytest` sull'intero workspace non produce nuovi fallimenti rispetto allo
stato pre-modifica; le guardie Copilot restano verdi.

**Acceptance**:
1. **Given** la rimozione, **When** gira `test_no_hand_maintained_copilot_prompt_bodies`, **Then** resta
   verde (non asserisce l'esistenza dei `.gitkeep`).
2. **Given** la rimozione, **When** gira `test_assets_copilot_parity.py`, **Then** resta verde (legge
   dai piani generati, non da `assets/copilot/`).
3. **Given** l'intera suite, **When** gira dopo la modifica, **Then** zero nuovi fallimenti rispetto al
   baseline.

### User Story 6 — Lo stub non riappare (P2, Should)
Una guardia anti-regressione fallisce se il tree stub `assets/copilot/` (o un suo `.gitkeep`) viene
ricreato in futuro «per tenere il posto» di asset Copilot statici, re-introducendo l'ambiguità che
questa feature elimina.

**Independent Test**: ricreando una directory `assets/copilot/` con un `.gitkeep`, almeno un test di
guardia fallisce; allo stato corretto (directory assente) la guardia passa. *(In alternativa: estendere
il guard Copilot esistente per asserire l'assenza della directory `assets/copilot/`.)*

**Acceptance**:
1. **Given** lo stato corretto (directory assente), **When** la guardia gira, **Then** passa.
2. **Given** un futuro contributor che ricrea `assets/copilot/agents/.gitkeep` (o simile), **When** la
   guardia gira, **Then** fallisce, segnalando la ricomparsa dello stub.
3. **Given** la decisione (nessuna guardia CI-enforced obbligatoria per i requirements — R-2 «non
   necessaria»), **When** si valuta in plan, **Then** la guardia è additiva e leggera (asserzione di
   assenza directory), senza vincoli di stack.

## Edge Cases
- **Codice introdotto dopo la verifica zero-consumatori ma prima del merge** che leggesse
  `assets/copilot/` (`iter_asset_dir`/`read_asset_text` con root `copilot/`): la verifica grep va
  ripetuta al momento dell'implementazione; se un tale consumatore esistesse, va **prima corretto/rimosso**,
  poi si rimuove la directory (US3, FR-005). La suite verde (US5) lo rileverebbe comunque.
- **Ricomparsa dello stub** da un futuro contributor: la guardia anti-regressione fallisce (US6, FR-008).
- **Wheel pre-esistente con `.gitkeep`** vs wheel fresco senza: differenza di comportamento a runtime =
  zero (i `.gitkeep` non sono mai letti); il test di packaging lo verifica (US4, FR-006).
- **Directory vuota residua dopo `git rm` dei file**: git non traccia directory vuote → rimosso l'ultimo
  file, la directory scompare dal tree; nessun residuo (US1, FR-002).

## Requirements *(mandatory)*

### Requisiti funzionali

**Rimozione del tree stub**
- **FR-001 (rimozione `.gitkeep`).** I quattro file placeholder `.gitkeep` sotto
  `packages/sertor/src/sertor_installer/assets/copilot/{agents,hooks,instructions,prompts}/` sono
  rimossi dal repo. *(REQ-001; CS-1)*
- **FR-002 (rimozione directory vuote).** Rimossi i `.gitkeep`, le quattro directory ora vuote
  (`agents/`, `hooks/`, `instructions/`, `prompts/`) e `assets/copilot/` stessa non esistono più nel
  tree del repo. *(REQ-002; CS-1)*
- **FR-003 (nessun file di rimpiazzo).** Dopo la rimozione non viene aggiunto alcun file sostitutivo
  (README, marker o altro asset) sotto `assets/copilot/`: lo stato corretto è l'assenza della directory.
  *(REQ-003; decisione scope Opzione A)*

**Non-regressione**
- **FR-004 (generazione Copilot invariata).** `build_rag_plan` invocato con `AssistantId.COPILOT_CLI`
  continua a produrre lo stesso insieme di artefatti host-facing di prima (hook JSON generati, body
  skill byte-copiati, custom-agent renderizzati, blocchi istruzione), tutti derivati esclusivamente da
  `assets/claude/**` e `assets/rag/**`. *(REQ-004; CS-4)*
- **FR-005 (verifica zero-consumatori).** Se al momento dell'implementazione un modulo Python risultasse
  leggere un percorso rooted a `copilot/` (`iter_asset_dir`/`read_asset_text`), quel consumatore è prima
  corretto o rimosso; altrimenti (nessun consumatore, come verificato in §1.2 requirements) la rimozione
  procede senza modifiche al codice. *(REQ-005)*
- **FR-006 (build e packaging invariati).** La build del pacchetto `sertor` (`uv build`) completa senza
  errori; il wheel non richiede file sotto `assets/copilot/`; il `pyproject.toml` non è modificato
  (hatchling include il package per glob ricorsivo); il test di packaging
  (`tests/integration/test_packaging.py`) resta verde. *(REQ-008; CS-2)*
- **FR-007 (guardie e suite verdi).** Le guardie esistenti
  (`test_assets_copilot_guard.py` incl. `test_no_hand_maintained_copilot_prompt_bodies`,
  `test_assets_copilot_parity.py`) e l'intera suite (`sertor`, `sertor-install-kit`, `sertor-flow`,
  root) restano verdi dopo la rimozione, senza modifiche ai test esistenti. *(REQ-006/007; CS-3)*

**Anti-regressione**
- **FR-008 (guardia anti-ricomparsa).** La feature fornisce una guardia che fallisce se il tree
  `assets/copilot/` (o un `.gitkeep` al suo interno) viene ricreato, oppure estende il guard Copilot
  esistente per asserire l'assenza della directory `assets/copilot/`; allo stato corretto la guardia
  passa. *(R-2 requirements; CS-3)*

### Requisiti non funzionali
- **RNF-1 (Principio XI):** zero modifiche a `sertor_core` — la feature tocca esclusivamente file
  statici (`.gitkeep`) nel package `sertor_installer`; nessun engine/porta/adapter/comando/servizio del
  core è coinvolto. *(NFR-1)*
- **RNF-2 (non-regressione comportamentale):** il comportamento dell'installer per entrambi gli
  assistenti (`claude`, `copilot-cli`) è byte-identico prima e dopo la rimozione; la rimozione è
  puramente sottrattiva di file vuoti, non cambia alcun piano d'installazione. *(NFR-2)*
- **RNF-3 (non-regressione suite):** le suite `sertor`, `sertor-install-kit`, `sertor-flow` e root
  restano verdi (zero nuovi fallimenti). *(NFR-3)*
- **RNF-4 (impatto minimale):** la feature richiede al massimo la rimozione di quattro file `.gitkeep`
  (più, opzionalmente, una guardia anti-regressione leggera); nessuna modifica al codice Python di
  runtime, ai test esistenti o agli altri asset. *(NFR-4)*

### Key Entities
- **Tree stub `assets/copilot/`** — la directory
  `packages/sertor/src/sertor_installer/assets/copilot/` con le quattro sottocartelle vuote
  (`agents/`, `hooks/`, `instructions/`, `prompts/`), ciascuna contenente un solo `.gitkeep`: l'oggetto
  che la feature rimuove.
- **Pipeline di generazione Copilot** — `render_copilot_hooks`/`render_custom_agent`/`render_prompt_file`
  in `sertor_install_kit.surfaces`, orchestrate da `build_rag_plan` per `COPILOT_CLI`; sorgenti da
  `assets/claude/**` e `assets/rag/**`. Non modificata; resta l'unica fonte dei payload Copilot.
- **Guardie esistenti** — `test_assets_copilot_guard.py` (incl.
  `test_no_hand_maintained_copilot_prompt_bodies`), `test_assets_copilot_parity.py`,
  `tests/integration/test_packaging.py`: restano verdi, non modificate.
- **Guardia anti-regressione** — il test (nuovo o estensione del guard Copilot esistente) che fallisce
  se lo stub `assets/copilot/` riappare.

## Success Criteria *(mandatory)*
- **CS-1 (zero stub fuorvianti):** il tree
  `packages/sertor/src/sertor_installer/assets/copilot/` non esiste più nel repo — verificabile con
  `git ls-files packages/sertor/src/sertor_installer/assets/copilot/` che non produce output.
  *(FR-001/002/003, US1/US2)*
- **CS-2 (nessuna regressione build/wheel):** `uv build` (pacchetto `sertor`) completa senza errori e il
  test di packaging (`tests/integration/test_packaging.py`) resta verde — il wheel non dipende da file
  sotto `assets/copilot/`. *(FR-006, US4)*
- **CS-3 (nessuna regressione suite):** tutte le suite esistenti rimangono verdi (zero nuovi fallimenti)
  — in particolare `test_assets_copilot_guard.py` e `test_assets_copilot_parity.py`; la guardia
  anti-regressione passa allo stato corretto. *(FR-007/008, US5/US6)*
- **CS-4 (comportamento installer invariato):** `build_rag_plan` per `copilot-cli` genera gli stessi
  artefatti di prima (hook JSON, skill body, agent, blocchi istruzione), tutti derivati da
  `assets/claude/**` e `assets/rag/**`; i test `test_install_rag_copilot_cli.py` (o equivalenti) restano
  verdi. *(FR-004/005, US3)*

## Assumptions
- **A-001 — Zero consumatori della directory:** verificato per grep esaustivo (§1.2 requirements):
  nessun file Python, test o config legge un percorso sotto `assets/copilot/`. Se questa assunzione
  fosse falsificata da codice introdotto prima del merge, FR-005 obbliga a correggere prima di rimuovere.
  *(FR-005)*
- **A-002 — Hatchling glob ricorsivo:** hatchling include i file sotto `src/sertor_installer/` per
  ricorsione (`packages = ["src/sertor_installer"]`), non per lista esplicita; la rimozione di `.gitkeep`
  e delle directory vuote non richiede aggiornamenti al `pyproject.toml`. *(FR-006)*
- **A-003 — FEAT-049 completata:** la rimozione dei file JSON hook da `assets/copilot/hooks/` era già
  avvenuta in FEAT-049; questa feature rimuove solo i `.gitkeep` rimasti come artefatto. *(contesto)*
- **A-004 — Guard test non asserisce i `.gitkeep`:** `test_no_hand_maintained_copilot_prompt_bodies` non
  verifica l'esistenza dei `.gitkeep` (afferma solo che nessun body deve risiedere sotto `copilot/`) →
  resta verde dopo la rimozione, senza modifiche al test. *(FR-007)*
- **A-005 — `.gitkeep` non letti a runtime:** i file `.gitkeep` non sono mai letti dall'installer; la
  differenza tra wheel vecchio (con `.gitkeep`) e nuovo (senza) è zero a livello di comportamento.
  *(RNF-2, FR-006)*

### Fuori ambito (dichiarato)
- **Modifiche a `sertor_core`** o a qualunque comando/vehicle/porta/adapter/engine — la feature è
  sottrattiva e host-facing, zero codice di runtime del core (Principio XI).
- **Codice di `surfaces.py`, `install_rag.py`, `install_wiki.py`, `sertor_install_kit`**: invariato.
- **`assets/claude/**` e `assets/rag/**`**: non toccati.
- **Modifica ai test esistenti** `test_assets_copilot_guard.py` / `test_assets_copilot_parity.py`: non
  modificati (restano verdi così come sono).
- **Aggiunta di un README** «generato a runtime» sotto `assets/copilot/` (Opzione B): **scartata** (è
  un file da manutenere, in contraddizione col guard test).
- **Documentazione editoriale** sull'architettura generativa Copilot in `docs/`/`wiki/` (oltre la
  rimozione stub): intervento autonomo, fuori scope per questa feature di igiene.
- **Budget altitude in CI** (gate file-skill > N righe) → **FEAT-024**.
- **Parity guard esteso a `.ps1`/`.json`** → **FEAT-024**.
- **Riconciliazione fork IT eval-skill** → **FEAT-025**.
- **Portabilità OS degli hook** → **FEAT-018** (già completata).
- **Il *come* di dettaglio** (forma esatta della guardia anti-ricomparsa: test nuovo vs estensione del
  guard Copilot; commento esplicativo in `install_rag.py`): fase di **design/plan**.

> **Tracciamento dello scope.** I rinvii reali sono già **promossi a casa durevole** nel backlog
> d'epica: budget altitude / parity guard esteso → **FEAT-024**; riconciliazione fork IT eval-skill →
> **FEAT-025**; documentazione editoriale dell'architettura generativa → intervento autonomo separato.
> Nessun rinvio reale resta sepolto in `specs/`. La feature è *done* quando:
> `git ls-files .../assets/copilot/` è vuoto; nessun file di rimpiazzo aggiunto; `uv build` + test di
> packaging verdi; zero nuovi fallimenti di suite; `build_rag_plan(copilot-cli)` produce gli stessi
> artefatti di prima; guardia anti-ricomparsa verde.

### Forche di design — per `/speckit-plan` (sono *come*, non scope)
- **DA-D-1 — Forma della guardia anti-ricomparsa:** test nuovo dedicato che asserisce l'assenza della
  directory `assets/copilot/` vs estensione del guard Copilot esistente
  (`test_assets_copilot_guard.py`). La direzione (assenza directory) è fissata; la collocazione è plan.
  *(come di plan; FR-008)*
- **DA-D-2 — Commento esplicativo in `install_rag.py`:** dopo la rimozione, conviene aggiungere un
  commento «There is no static Copilot asset directory: all Copilot-facing artefacts are generated from
  claude/** and rag/** sources» per prevenire la ricomparsa (R-2)? Non è un requisito (nessun codice
  cambia); decisione al plan/implement. *(come di plan)*
