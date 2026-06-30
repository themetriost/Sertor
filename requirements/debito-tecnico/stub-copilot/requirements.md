# Requisiti — Rimozione stub `assets/copilot/` fuorviante

<!-- Deriva da: FEAT-023 (epica debito-tecnico) — audit ISSUE-09 del 2026-06-26 -->

## 1. Contesto e problema (perché)

### 1.1 Stato attuale

Il tree `packages/sertor/src/sertor_installer/assets/copilot/` contiene **quattro
directory vuote**, ciascuna con un solo file `.gitkeep`:

| Path | Scopo storico | Stato attuale |
|---|---|---|
| `assets/copilot/agents/.gitkeep` | Placeholder per agenti Copilot | Vuota |
| `assets/copilot/hooks/.gitkeep` | Placeholder per hook JSON Copilot | Vuota |
| `assets/copilot/instructions/.gitkeep` | Placeholder per blocchi istruzione Copilot | Vuota |
| `assets/copilot/prompts/.gitkeep` | Placeholder per prompt-file Copilot | Vuota |

Le sottocartelle sono state create in FEAT-044 (`044-distribuzione-copilot`, task T001),
quando si ipotizzava di depositare lì asset statici Copilot. In FEAT-049
(`049-compatibilita-copilot`) i file JSON allora presenti in `assets/copilot/hooks/`
(`wiki.hooks.json`, `rag-usage.hooks.json`) sono stati **rimossi** e sostituiti dalla
generazione a runtime via `render_copilot_hooks()`, perché erano in formato Claude
invece che Copilot nativo. Da quel momento il tree `assets/copilot/` è rimasto vuoto.

### 1.2 Come vengono generati i payload Copilot (stato attuale verificato)

I payload Copilot sono generati interamente **da `assets/claude/**` e `assets/rag/**`**
via funzioni pure in `sertor_install_kit.surfaces` (riesportate in
`sertor_installer.surfaces`):

- **Hook JSON** (`sertor-hooks.json`, `.github/hooks/`): generati da
  `render_copilot_hooks(list[HookEntrySpec])` — nessun file statico letto da
  `assets/copilot/` (`install_rag.py:136-244`).
- **Custom agent** (`.github/agents/*.agent.md`): `render_custom_agent(canonical)` su
  sorgente da `assets/claude/agents/` o `assets/rag/agents/` — traduce solo il
  frontmatter, body byte-identico.
- **Prompt file** (`.github/prompts/*.prompt.md`): `render_prompt_file(canonical)` su
  sorgente da `assets/claude/commands/` o `assets/claude/skills/` — stessa meccanica.
- **Skill body** (`.github/skills/<name>/SKILL.md`): byte-copy da `assets/rag/skills/`
  via `iter_asset_dir("rag/skills/...")` — mai da `assets/copilot/`.
- **Blocco istruzione** (`.github/copilot-instructions.md`): sorgente
  `claude-md-block*.md` — mai da `assets/copilot/instructions/`.

**Nessun file Python invoca `iter_asset_dir("copilot/...")` o
`read_asset_text("copilot/...")`.** Verificato con grep esaustivo su tutto il repo.

### 1.3 Problema

Lo stub vuoto è **fuorviante** per due lettori:

1. **Il manutentore** che esplora `assets/` si aspetta che le sottocartelle di
   `assets/copilot/` contengano asset statici analoghi a quelli di `assets/claude/`,
   mentre sono vuote: l'architettura reale (generazione da sorgente Claude) non è
   evidente.
2. **Il test `test_no_hand_maintained_copilot_prompt_bodies`**
   (`packages/sertor/tests/test_assets_copilot_guard.py:85-94`) **già documenta e
   afferma** che nessun body asset deve risiedere sotto `copilot/`; i `.gitkeep` sono
   coerenti con questo vincolo, ma la directory vuota resta un artefatto superfluo.

L'audit ISSUE-09 (2026-06-26) ha identificato questo come debito di igiene: «rimuovere
il tree stub oppure aggiungere un README "generato a runtime"».

### 1.4 Forca di scope: rimozione vs README

**Opzione A — Rimozione del tree stub (RACCOMANDATA)**

Eliminare i quattro file `.gitkeep` e le quattro directory vuote.

- *Pro*: nessun artefatto fuorviante; lo stato del repo riflette la realtà (nulla
  vive sotto `assets/copilot/`); non aggiunge file da manutenere.
- *Pro*: il test `test_no_hand_maintained_copilot_prompt_bodies` già documenta la
  meccanica generativa e continua a passare (non verifica l'esistenza dei `.gitkeep`).
- *Pro*: hatchling include il package directory per glob ricorsivo (`packages =
  ["src/sertor_installer"]`), non per lista esplicita di file: la rimozione di file
  `.gitkeep` non rompe la build del wheel.
- *Nessun rischio tecnico verificato*: zero consumatori Python della directory.

**Opzione B — README «generato a runtime»**

Aggiungere un `README.md` in `assets/copilot/` che spiega la meccanica generativa.

- *Pro*: visibilità esplicita per chi apre quella cartella da un file explorer.
- *Contro*: aggiunge un file da manutenere; può divergere dalla realtà nel tempo;
  la stessa informazione è già nel codice (`install_rag.py`, commenti) e nel test
  (`test_no_hand_maintained_copilot_prompt_bodies`). Un README dentro `assets/`
  potrebbe confondere hatchling o `iter_asset_dir` se invocato su quella
  sottodirectory in futuro.
- *Rischio*: il README stesso diventa body asset sotto `assets/copilot/`,
  tecnicamente in contraddizione con il commento del test.

**Raccomandazione netta: Opzione A (rimozione).** Nessun codice legge la directory,
nessun test ne verifica l'esistenza, il test di guardia documenta già la meccanica.
La rimozione è sicura e rimuove la fonte di ambiguità senza aggiungere maintenance.

Se l'utente preferisce l'Opzione B, si veda la domanda aperta DA-1 in §10.

## 2. Obiettivi e criteri di successo

- **CS-1 (zero stub fuorvianti)** Il tree
  `packages/sertor/src/sertor_installer/assets/copilot/` non esiste più nel repo
  (rimozione totale). Verificabile: `find packages/sertor/src/sertor_installer/assets/copilot`
  o `git ls-files packages/sertor/src/sertor_installer/assets/copilot/` non produce
  output.

- **CS-2 (nessuna regressione build/wheel)** La build del pacchetto `sertor`
  (`uv build -p sertor`) completa senza errori; il wheel prodotto non richiede la
  presenza di file in `assets/copilot/`. Verificabile: il test di packaging
  (`tests/integration/test_packaging.py`) resta verde.

- **CS-3 (nessuna regressione suite)** Tutte le suite esistenti rimangono verdi:
  `packages/sertor/tests/test_assets_copilot_guard.py`,
  `packages/sertor/tests/test_assets_copilot_parity.py`, root (`uv run pytest`).
  Verificabile: zero test falliti dopo la modifica.

- **CS-4 (comportamento installer invariato)** `build_rag_plan` per `copilot-cli`
  genera gli stessi artefatti di prima: hook JSON, skill body, agent, blocchi istruzione
  — tutti derivati da `assets/claude/**` e `assets/rag/**` come prima.
  Verificabile: i test `test_install_rag_copilot_cli.py` (o equivalenti) restano verdi.

## 3. Stakeholder e attori

- **Manutentore di Sertor** — esplora `assets/` e non trova più directory vuote fuori
  posto; l'architettura generativa è l'unica documentata nel codice e nei test.
- **CI e guardie di parità** — le guardie esistenti restano verdi; nessuna nuova
  guardia è introdotta da questa feature.
- **Il sistema di build (hatchling)** — non è influenzato dalla rimozione (glob ricorsivo
  su package dir, nessun file esplicito elencato per `assets/copilot/`).

## 4. Ambito

### In ambito

- **Rimozione dei quattro file `.gitkeep`** e delle quattro directory vuote:
  `assets/copilot/agents/`, `assets/copilot/hooks/`, `assets/copilot/instructions/`,
  `assets/copilot/prompts/`, e `assets/copilot/` stessa.
- **Verifica di non-regressione** delle suite esistenti (`sertor`, `sertor-install-kit`,
  `sertor-flow`, root) prima di dichiarare la feature completa.
- **Zero modifica semantica all'installer**: build plan, comportamento di `install rag`,
  superfici generate — tutti invariati.

### Fuori ambito

- **`sertor_core`**: zero modifiche (Principio XI); la feature tocca esclusivamente
  file statici nel package `sertor_installer`.
- **`assets/claude/**` e `assets/rag/**`**: non toccati.
- **Il codice di `surfaces.py`, `install_rag.py`, `install_wiki.py`**: invariati.
- **Il codice di `sertor_install_kit`**: invariato.
- **Budget altitude in CI** → FEAT-024.
- **Parity guard esteso a `.ps1`/`.json`** → FEAT-024.
- **Riconciliazione fork IT eval-skill** → FEAT-025.
- **Portabilità OS degli hook** → FEAT-018 (già completata).
- **Aggiunta di documentazione esplicita** sull'architettura generativa Copilot (oltre
  la rimozione stub): sarebbe un intervento editoriale a `docs/` o `wiki/`, fuori
  scope per questa feature di igiene.

## 5. Requisiti funzionali (EARS)

### Gruppo A — Rimozione del tree stub

- **REQ-001** The system shall remove the four placeholder `.gitkeep` files located at
  `packages/sertor/src/sertor_installer/assets/copilot/agents/.gitkeep`,
  `packages/sertor/src/sertor_installer/assets/copilot/hooks/.gitkeep`,
  `packages/sertor/src/sertor_installer/assets/copilot/instructions/.gitkeep`, and
  `packages/sertor/src/sertor_installer/assets/copilot/prompts/.gitkeep`.

- **REQ-002** When the `.gitkeep` files are removed, the system shall also remove the
  now-empty directories `agents/`, `hooks/`, `instructions/`, `prompts/`, and
  `assets/copilot/` itself from the repository tree.

- **REQ-003** The system shall not add any replacement file (README, marker, or other
  asset) under `assets/copilot/` after the removal.

### Gruppo B — Non-regressione

- **REQ-004** The `build_rag_plan` function, when invoked with `AssistantId.COPILOT_CLI`,
  shall continue to produce the same set of host-facing artefacts as before the change:
  generated hook JSON, byte-copied skill bodies, rendered custom agents, and instruction
  blocks — all sourced exclusively from `assets/claude/**` and `assets/rag/**`.

- **REQ-005** If any Python module were found to call `iter_asset_dir` or
  `read_asset_text` with a path rooted at `copilot/`, then the system shall fix or
  remove that call before deleting the directory; otherwise (no such call found,
  as verified in §1.2), the removal proceeds without code changes.

- **REQ-006** The existing test
  `packages/sertor/tests/test_assets_copilot_guard.py::test_no_hand_maintained_copilot_prompt_bodies`
  shall remain green after the removal; this test does not assert the existence of
  `.gitkeep` files, so no change to the test is required.

- **REQ-007** The existing parity guard
  (`packages/sertor/tests/test_assets_copilot_parity.py`) shall remain green after
  the removal; it does not read from `assets/copilot/`, only from generated plans.

- **REQ-008** The integration packaging test (`tests/integration/test_packaging.py`)
  shall remain green after the removal; hatchling's glob-based inclusion of the package
  directory (`packages = ["src/sertor_installer"]`) does not require specific files
  under `assets/copilot/`.

## 6. Requisiti non funzionali

- **NFR-1 (Principio XI)** Zero modifiche a `sertor_core`: la feature tocca
  esclusivamente file statici (`.gitkeep`) nel package `sertor_installer`. Nessun
  engine, porta, adapter, comando o servizio del core è coinvolto.

- **NFR-2 (Non-regressione comportamentale)** Il comportamento dell'installer per
  entrambi gli assistenti (`claude`, `copilot-cli`) è byte-identico prima e dopo la
  rimozione: la rimozione è puramente sottrattiva di file vuoti, non cambia alcun
  piano d'installazione.

- **NFR-3 (Non-regressione suite)** Le suite di test `sertor`, `sertor-install-kit`,
  `sertor-flow` e root rimangono verdi (zero nuovi fallimenti).

- **NFR-4 (Impatto minimale)** La feature richiede al massimo quattro comandi `git rm`
  e un commit; nessuna modifica al codice Python, ai test o agli altri asset.

## 7. Vincoli, assunzioni e dipendenze

- **Vincolo (Principio XI):** nessuna modifica al codice di `sertor_core`.
- **Vincolo (non-distruttività dell'installer):** rimuovere i `.gitkeep` non altera
  alcun piano d'installazione sugli ospiti; le directory `assets/copilot/` non sono
  referenziate da nessun `ArtifactKind.FILE` né da `iter_asset_dir`.
- **Assunzione (hatchling glob ricorsivo):** hatchling include i file sotto
  `src/sertor_installer/` per ricorsione; la rimozione di file `.gitkeep` (e delle
  relative directory vuote) non richiede aggiornamenti al `pyproject.toml`
  (`packages/sertor/pyproject.toml:46`).
- **Assunzione (zero consumatori):** verificato per grep esaustivo (§1.2): nessun
  file Python, test o config legge un percorso sotto `assets/copilot/`. Se questa
  assunzione fosse falsificata da codice introdotto prima del merge, REQ-005 obbliga
  a correggere prima di rimuovere.
- **Dipendenza (FEAT-049 completata):** la rimozione dei file JSON hook da
  `assets/copilot/hooks/` era già avvenuta in FEAT-049 (`049-compatibilita-copilot`);
  questa feature rimuove solo i file `.gitkeep` rimasti come artefatto.
- **Dipendenza (suite pre-esistenti):** le guardie `test_assets_copilot_guard.py` e
  `test_assets_copilot_parity.py` non devono essere modificate (CS-3).

## 8. Rischi

- **R-1 (Assunzione zero-consumatori falsificata)** Un file Python aggiunto dopo la
  verifica (§1.2) ma prima del merge potrebbe leggere `assets/copilot/`, rompendo
  la feature su quel codice. Mitigazione: REQ-005 richiede di ripetere la verifica
  grep al momento dell'implementazione; la suite verde (CS-3) la rileva comunque.

- **R-2 (Ricomparsa dello stub)** Un futuro contributor ricrea la directory con un
  `.gitkeep` per «tenere il posto» di asset Copilot statici, re-introducendo
  l'ambiguità. Mitigazione: il test `test_no_hand_maintained_copilot_prompt_bodies`
  già documenta (nel commento) che nessun body asset deve risiedere lì; il codice
  generativo è l'unica fonte. Non è necessaria una guardia aggiuntiva (fuori scope;
  FEAT-024 se dovesse diventare CI-enforced).

- **R-3 (Impatto wheel in ambienti che installano da git+url)** Un ambiente che
  aveva già il wheel con i `.gitkeep` potrebbe avere comportamenti diversi da uno
  fresco. Mitigazione: i file `.gitkeep` non sono letti a runtime, quindi la
  differenza tra vecchio e nuovo wheel è zero a livello di comportamento; il test di
  packaging (CS-2) lo verifica.

## 9. Prioritizzazione (MoSCoW)

- **Must:** REQ-004, REQ-005, REQ-006, REQ-007, REQ-008 (non-regressione — le
  guardie esistenti devono restare verdi).
- **Must:** REQ-001, REQ-002 (rimozione effettiva — è il corpo della feature).
- **Should:** REQ-003 (nessun file di rimpiazzo — rafforza l'intenzione di pulizia;
  l'assenza di file è l'unico stato corretto secondo la meccanica generativa).
- **Won't (qui):** guardia CI che vieti la ricreazione di `assets/copilot/` → FEAT-024;
  documentazione esplicita dell'architettura generativa in `docs/` → intervento
  editoriale autonomo; qualunque modifica a `sertor_core`.

## 10. Domande aperte

### Scope (da girare all'utente se la raccomandazione non è accettata)

- **[DA CHIARIRE — DA-1]** La feature adotta l'**Opzione A (rimozione)**. Se l'utente
  preferisce l'**Opzione B (README «generato a runtime»)**: quale file aggiungere
  esattamente? Un `README.md` in `assets/copilot/` (un singolo file) o singoli
  `README.md` in ciascuna sottodirectory? Il contenuto minimale sarebbe:
  «I Copilot payloads are generated at runtime from `assets/claude/**` and `assets/rag/**`
  via `render_copilot_hooks`, `render_custom_agent`, `render_prompt_file` in
  `sertor_install_kit.surfaces`. No static asset files should be added here.»
  Se si sceglie l'Opzione B, i requisiti REQ-001/002/003 vanno sostituiti con un
  requisito di creazione del README e REQ-005/006/007 restano invariati.
  La **raccomandazione resta A** perché B aggiunge maintenance e la stessa informazione
  è già nel codice e nel test.

### Design/plan (non bloccanti per i requisiti)

- **[DA CHIARIRE in design/plan]** Dopo la rimozione: conviene aggiungere un commento
  in `install_rag.py` che espliciti «There is no static Copilot asset directory: all
  Copilot-facing artefacts are generated from claude/** and rag/** sources»? Non è
  un requisito di questa feature (nessun codice cambia), ma potrebbe prevenire R-2.
  Decisione al momento del plan/implement.
