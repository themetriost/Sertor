# Requisiti — Riduzione altitude blocchi CLAUDE.md + dedup «How to invoke»

<!-- Deriva da: FEAT-021 (epica debito-tecnico) — audit ISSUE-07 del 2026-06-26 -->

## 1. Contesto e problema (perché)

Ogni progetto ospite che installa le tre capability di Sertor (`sertor install wiki`,
`sertor install rag`, `sertor-flow install`) riceve tre blocchi iniettati nel proprio
`CLAUDE.md` (o nel suo equivalente per l'assistente target):

| Blocco | Marker | Asset canonico | Linee |
|--------|--------|----------------|-------|
| Wiki ritual | `SERTOR:WIKI-RITUAL` | `packages/sertor/src/sertor_installer/assets/claude-md-block.md` | 71 |
| SDLC ritual | `SERTOR:SDLC-RITUAL` | `packages/sertor-flow/src/sertor_flow/assets/claude-md-block-sdlc.md` | 65 |
| RAG usage | `SERTOR:RAG-USAGE` | `packages/sertor/src/sertor_installer/assets/rag/claude-md-block-rag-usage.md` | 72 |

**Totale: 208 righe always-on** — caricato integralmente dal client agente a ogni avvio di
sessione, indipendentemente dall'operazione richiesta. Il wiring è confermato in
`install_wiki.py:440`, `install_rag.py:79-80`, `install_governance.py:65-66`.

Questi tre blocchi hanno una struttura disomogenea: alcune sezioni contengono **regole di
comportamento standing** (cosa usare, cosa non fare) che giustificano la presenza always-on;
altre contengono **istruzioni operative di dettaglio** (come invocare i comandi, note di
troubleshooting su Python 3.14/`pywin32`) che sono lookup-on-demand e sprecano budget di
contesto se caricate sempre.

In particolare, la sezione «How to invoke Sertor's commands / How to invoke the runtime CLIs»
con il «Windows note» appare **in tre sedi distinte**:

1. `assets/rag/claude-md-block-rag-usage.md` (righe 12–38, ~27 righe) —
   «How to invoke Sertor's commands», sezione con Windows note; always-on nel CLAUDE.md host.
2. `assets/rag/skills/guided-setup/SKILL.md` (righe 52–78, ~27 righe) —
   sezione identica «How to invoke Sertor's commands», inclusa Windows note.
3. `assets/claude/skills/wiki-author/wiki-playbook.md` (righe 93–112, ~20 righe) —
   «How to invoke the runtime CLIs», stessa sostanza focalizzata su `sertor-wiki-tools`.

Il testo delle tre copie è quasi identico (stessa sequenza `--project` vs `--directory`,
fallback al venv, bare-command spiegazione, Windows note). Una modifica va replicata a mano in
tre posti e rischia di divergere (la divergenza è già parziale: `guided-setup` nomina la CLI
di ritorno in caso di mancata installazione, `wiki-playbook` non lo fa).

**Conseguenze:**
- Ogni sessione carica ~208 righe di dettaglio operativo che l'agente non usa sempre.
- Tre copie della stessa istruzione tecnica = manutenzione triplicata e rischio di deriva
  silenziosa (una copia aggiornata, le altre stantie).

**Valore:** ridurre il budget di contesto always-on (blocchi più corti = più token disponibili
per il lavoro reale) e avere una sola fonte di verità per l'invocazione, che il plan/upgrade
mantiene in un posto solo.

## 2. Obiettivi e criteri di successo

- **CS-1 (altitude ridotta)** La dimensione complessiva dei tre blocchi always-on
  (`claude-md-block.md`, `claude-md-block-sdlc.md`, `claude-md-block-rag-usage.md`) è
  misurabilmente inferiore rispetto alle 208 righe attuali dopo la feature. Il criterio di
  accettazione quantitativo esatto (es. ≤ N righe per blocco) è una decisione da fissare
  in fase di design/plan sulla base del contenuto carico; il requisito funzionale è che
  nessuna sezione lookup-on-demand resti inline — solo le direttive comportamentali standing
  rimangono nel blocco.

- **CS-2 (fonte unica «How to invoke»)** La sezione «How to invoke Sertor's commands /
  runtime CLIs» con la Windows note esiste in **un'unica sede** negli asset distribuiti;
  tutte le altre sedi (blocchi CLAUDE.md, `guided-setup`, `wiki-playbook`) la referenziano
  per nome invece di duplicarla. Verificabile contando le occorrenze della sezione autonoma
  nei file asset.

- **CS-3 (nessun pointer rotto)** Ogni pointer introdotto nei blocchi ridotti verso un asset
  esterno punta a una risorsa che viene effettivamente depositata sul host (closure). La
  guardia di closure della parità (già esistente per i body delle skill, da estendere se
  necessario) resta verde. Verificabile offline.

- **CS-4 (contenuto load-bearing preservato)** Nessuna direttiva comportamentale standing
  (cosa usare, cosa non importare, fail-loud sugli errori MCP, gate di privacy memoria,
  flusso SpecKit, error discipline, git policy) viene rimossa o resa inaccessibile: il
  pointer porta a un asset raggiungibile e completo, non a un vicolo cieco.

- **CS-5 (parità host-agnostica preservata)** I body ridotti restano host-agnostici: nessun
  percorso letterale dell'assistente (`.claude/`), nessun slash-command, nessun nome di
  modello/prodotto Claude. La guardia di parità Copilot (`test_assets_copilot_guard.py`)
  resta verde.

- **CS-6 (sync dogfood preservato)** Le copie dogfood in `.claude/` restano in byte-parità
  con gli asset bundlati. Il guard `tests/unit/test_assets_sync.py` resta verde dopo la
  feature.

## 3. Stakeholder e attori

- **Agente frontier dell'ospite** — usa il CLAUDE.md del suo progetto: beneficia di un
  contesto sempre-attivo più compatto, con le direttive operative di dettaglio disponibili
  on-demand invece di caricate sempre.
- **Operatore/utente ospite** — installa Sertor su un progetto terzo; riceve blocchi che
  non degradano la qualità dell'istruzione ma occupano meno spazio always-on.
- **Manutentore di Sertor** — una sola fonte per «How to invoke» da aggiornare quando
  cambiano i dettagli di invocazione (versione Python, path venv, ecc.).
- **CI e guardie di parità** — le guardie esistenti restano verdi; eventuali guardie nuove
  non richiedono modifiche a `sertor_core`.

## 4. Ambito

### In ambito

- **I tre asset `claude-md-block*.md`** (wiki ritual 71 righe · RAG usage 72 righe · SDLC 65
  righe) e la loro riduzione a «direttiva breve + pointer».
- **La sezione «How to invoke» in `guided-setup/SKILL.md`** (righe 52–78): sostituzione con
  un riferimento per nome all'asset di riferimento, invece della copia inline.
- **La sezione «How to invoke» in `wiki-playbook.md`** (righe 93–112): stessa sostituzione.
- **Il reference unico «How to invoke + Windows note»**: creazione o designazione dell'asset
  canonico che ospita la sezione, distribuito e raggiungibile per nome (decisione
  design/plan, vedi §10).
- **Le copie dogfood** in `.claude/skills/guided-setup/SKILL.md` e
  `.claude/skills/wiki-author/wiki-playbook.md`: re-sincronizzate dagli asset canonici
  ridotti via `python -m sertor_installer.sync`.
- **Guard tests**: closure del pointer (ogni asset citato per nome è depositato) + parità
  host-agnostica + sync dogfood↔bundle.

### Fuori ambito

- **`sertor_core`**: zero modifiche (Principio XI). La feature è igiene pura degli asset
  host-facing; nessun engine, porta, adapter o comando è toccato.
- **CLAUDE.md di radice di Sertor** (il file `CLAUDE.md` a root del repository Sertor):
  è il file di istruzione del dogfood di Sertor, non un asset distribuito agli ospiti. Il
  suo contenuto è di competenza del maintainer; la feature non lo tocca (a eccezione
  dell'eventuale re-sync delle copie `.claude/` che ne derivano, già coperto da CS-6).
- **Pulizia stile generale delle skill** (ALL-CAPS, sezioni «What NOT to do», ToC mancante
  in `wiki-playbook.md`): è **FEAT-022**, fuori ambito qui.
- **Stub `assets/copilot/**`** con solo `.gitkeep`: è **FEAT-023**.
- **Budget di altitude in CI** (test che fallisce se un blocco supera N righe): è
  **FEAT-024** — cross-ref dichiarato. Questa feature paga il debito; FEAT-024 mette il
  freno deterministico che impedisce il re-accumulo.
- **Installer CLI o vehicle** (`sertor install`, `sertor-rag`, ecc.): invariati.
- **Contenuto delle skill al di là della sezione «How to invoke»** (logica di guided-setup,
  operazioni wiki, ecc.): invariato.

## 5. Requisiti funzionali (EARS)

### Gruppo A — Riduzione dei blocchi always-on

- **REQ-001** The system shall reduce each of the three always-on instruction blocks
  (`claude-md-block.md`, `claude-md-block-rag-usage.md`, `claude-md-block-sdlc.md`) to
  contain only standing behavioural directives (rules the agent must follow in every
  session), removing inline lookup-on-demand detail (invocation syntax, troubleshooting
  notes, enumeration of CLI arguments).

- **REQ-002** When a section removed from a block contains information load-bearing for the
  agent (e.g. invocation rules, fallback behaviour), the reduced block shall include a
  pointer to the asset that carries that information, expressed as the name of the asset
  (not a file-system path), so the agent can retrieve it on-demand.

- **REQ-003** If the pointer in a reduced block refers to an asset that is not deployed to
  the host as part of the same capability install, then the install shall not produce that
  pointer (the reference is only valid when the pointed-to asset is present).

- **REQ-004** The reduced instruction blocks shall not contain any assistant-specific path
  (e.g. `.claude/`), slash-command, or product/model name, preserving the host-agnostic
  authoring convention established in FEAT-056/049.

### Gruppo B — Fonte unica «How to invoke + Windows note»

- **REQ-005** The «How to invoke Sertor's commands / runtime CLIs» section, including the
  Windows note on `pywin32`/system Python 3.14, shall exist in exactly one canonical
  distributed asset after this feature; all other locations shall reference that single
  asset by name.

- **REQ-006** The canonical «How to invoke» asset shall itself be a host-agnostic document:
  no assistant-specific paths, no slash-commands, no assistant product/model names.

- **REQ-007** The canonical «How to invoke» asset shall be deployed to the host as part of
  the `sertor install rag` capability (the RAG capability is the primary context in which
  the invocation rules are relevant); where a `wiki`-only or `governance`-only install
  occurs without the RAG capability, the reference in the corresponding block shall not
  produce a dead pointer.

- **REQ-008** Where `guided-setup/SKILL.md` previously contained an inline copy of the
  invocation section, the skill shall instead reference the canonical asset by name,
  instructing the agent to read it when invocation details are needed.

- **REQ-009** Where `wiki-playbook.md` previously contained an inline «How to invoke the
  runtime CLIs» section, the playbook shall instead reference the canonical asset by name
  (or defer to the `guided-setup` skill, if that skill carries the reference — a design
  decision), so the invocation detail lives in one place.

### Gruppo C — Guardie di parità, closure e sync

- **REQ-010** The existing parity guard (`test_assets_copilot_guard.py`) shall remain green
  after the feature; any new asset introduced as the canonical «How to invoke» reference
  shall be covered by the closure assertion (every asset referenced by name in a body is
  deposited on the host for the relevant capability).

- **REQ-011** The existing sync guard (`tests/unit/test_assets_sync.py`) shall remain green
  after the feature; the dogfood copies of the modified assets under `.claude/` shall be
  re-synced to byte-parity with their bundled canonical sources.

- **REQ-012** The feature shall provide, or extend an existing guard to provide, an
  assertion that the three `claude-md-block*.md` assets each contain no inline copy of the
  «How to invoke» section (i.e. the section heading and the invocation patterns are absent
  from the reduced blocks), preventing silent re-introduction.

- **REQ-013** The change shall be additive to the installer lifecycle: the install/upgrade/
  uninstall paths for the three capabilities remain consistent; a reduced block is still
  idempotent on install, updated on upgrade, and removed on uninstall.

### Gruppo D — Coerenza dei blocchi ridotti

- **REQ-014** The reduced `claude-md-block.md` (wiki ritual) shall retain, at minimum: the
  golden rule for wiki documentation, the step-ritual outline with delegation rules, the
  D↔N boundary (mechanical vs judgment), and a reference to the wiki playbook by name.

- **REQ-015** The reduced `claude-md-block-rag-usage.md` (RAG usage) shall retain, at
  minimum: the directive to use vehicles (CLI / MCP tools) and never import `sertor_core`
  directly; the search-first, read-second rule; the MCP error = signal rule; and the
  pointer to invocation details.

- **REQ-016** The reduced `claude-md-block-sdlc.md` (SDLC ritual) shall retain, at minimum:
  the SpecKit flow phases in order; the constitution check gate; the error discipline rule
  (fix, don't suppress); and the version control discipline summary.

## 6. Requisiti non funzionali

- **NFR-1 (Principio XI)** Zero modifiche a `sertor_core`: la feature tocca esclusivamente
  asset host-facing (file `.md`, guardie di test) e nessun codice di runtime del core.
- **NFR-2 (Principio X — host-agnostico)** Ogni asset modificato o introdotto è
  host-agnostico: funziona identico su Claude e su Copilot CLI senza varianti per-assistente
  nel contenuto.
- **NFR-3 (Non-regressione)** Le suite esistenti (`sertor`, `sertor-install-kit`,
  `sertor-flow`, root) restano verdi. In particolare: i guard `test_assets_copilot_guard.py`,
  `test_assets_sync.py` e le guardie di parità in `test_assets_cli_invocation.py`
  (già copre `rag/claude-md-block-rag-usage.md`, `rag/skills/guided-setup/SKILL.md`,
  `claude/skills/wiki-author/wiki-playbook.md`) devono passare.
- **NFR-4 (Non-regressione installabilità)** Un ospite già installato che esegue
  `sertor upgrade` riceve i blocchi ridotti (via `update_marker_block`); gli ospiti non
  ancora installati ricevono i blocchi ridotti al primo install. Nessun ospite rimane con
  il vecchio contenuto verboso dopo l'upgrade.
- **NFR-5 (Closure del pointer)** Ogni riferimento per nome a un asset introdotto come
  «How to invoke reference» punta a un file che esiste nell'insieme degli asset depositati
  per la capability corrispondente: nessun pointer in produzione porta a un asset assente.
  Verificabile offline senza un host reale.
- **NFR-6 (Contenuto minimal load-bearing)** La riduzione non è arbitraria: il criterio è
  conservare *solo* il testo che un agente deve avere in memoria a ogni sessione per
  operare correttamente, e spostare *tutto* il testo che è un lookup (cerchi quando serve).

## 7. Vincoli, assunzioni e dipendenze

- **Vincolo (Principio XI):** nessuna modifica al codice di `sertor_core`; nessun nuovo
  comando, porta, adapter o engine.
- **Vincolo (Principio X):** i body degli asset modificati restano identici tra Claude e
  Copilot (nessuna variante per-assistente nei contenuti); il renderer che genera il
  payload Copilot resta invariato nel suo comportamento: byte-copia i file `.md` agnostici.
- **Vincolo (scope FEAT-022):** la pulizia stilistica (ALL-CAPS, sezioni «What NOT to do»,
  ToC) è *fuori* da questa feature — anche se la riduzione riduce il numero di righe, non
  si rinomina la struttura semantica delle sezioni esistenti per non confondere gli scope.
- **Assunzione:** il «reference unico» per «How to invoke» è un **asset `.md` già
  distribuibile** tramite il meccanismo esistente di byte-copia (`ArtifactKind.FILE` +
  `WriteStrategy.CREATE_IF_ABSENT` o equivalente) nell'installer RAG. Il *come* esatto
  (nome file, cartella, se è un asset nuovo o una sezione di un esistente già distribuito
  come `guided-setup/SKILL.md`) è una decisione di design/plan (vedi §10).
- **Assunzione:** i blocchi ridotti possono referenziare per nome un asset distribuito
  nello stesso install (es. il blocco RAG può referenziare una skill RAG). Per i blocchi
  wiki e SDLC, che non portano la skill RAG, il pointer è condizionale o assente (REQ-007).
- **Dipendenza (parità guard):** `test_assets_copilot_guard.py` verifica la closure
  «ogni asset citato per nome in un body è depositato». Se il reference nuovo è citato
  nei body ridotti, deve essere nel piano di distribuzione corrispondente; la guardia lo
  verifica offline.
- **Dipendenza (sync guard):** `tests/unit/test_assets_sync.py` copre `assets/claude/**`
  (incluse le copie dogfood di `wiki-playbook.md` e `wiki-author/SKILL.md`). Le modifiche
  a quei file richiedono un `python -m sertor_installer.sync` e il guard verde.
- **Dipendenza (test CLI invocation):** `test_assets_cli_invocation.py` già include
  `rag/claude-md-block-rag-usage.md`, `rag/skills/guided-setup/SKILL.md` e
  `claude/skills/wiki-author/wiki-playbook.md` nella lista degli asset che non devono
  contenere `uv run` nudo (footgun check). Dopo la feature i test devono coprire anche
  il nuovo reference asset.
- **Dipendenza cross-feature (FEAT-024):** la guardia di budget altitude (test che fallisce
  se un blocco supera N righe) è FEAT-024 e NON viene scritta qui. Il presente requisito
  (REQ-012) copre solo la clausola specifica «nessuna copia inline di How to invoke nei
  blocchi ridotti»; un budget generale va in FEAT-024.

## 8. Rischi

- **R-1 (Pointer rotto)** Un blocco ridotto cita per nome un asset che non è depositato
  nell'install corrispondente → l'agente cerca il file e non lo trova. Mitigazione:
  REQ-003 + REQ-007 + NFR-5 (closure verificata offline da guardie).
- **R-2 (Over-riduzione)** Si rimuove dal blocco una direttiva che l'agente ha bisogno
  always-on → comportamento degradato in sessione senza il segnale del blocco. Mitigazione:
  REQ-014/015/016 specificano il contenuto minimo load-bearing da preservare per ciascun
  blocco; il plan deve verificare che ogni direttiva rimossa sia accessibile on-demand.
- **R-3 (Drift tra il reference e il blocco ridotto)** Il reference «How to invoke» viene
  aggiornato ma il blocco ridotto che lo cita per nome non viene aggiornato (o viceversa).
  Mitigazione: fonte unica (CS-2); un'unica modifica al reference si propaga senza
  modificare i blocchi ridotti (che citano per nome, non per copia).
- **R-4 (Parità Copilot)** I body ridotti introducono accidentalmente un riferimento
  assistente-specifico (es. `.claude/skills/`) nel pointer. Mitigazione: REQ-004 + REQ-006
  + CS-5; la parity guard lo cattura offline.
- **R-5 (Accumulo futuro)** I blocchi ridotti vengono gonfiati di nuovo nei cicli successivi
  senza un freno automatico. Mitigazione: FEAT-024 introduce il budget altitude CI; questa
  feature riduce il debito, FEAT-024 lo mantiene basso.
- **R-6 (Scope creep)** Durante la riduzione si è tentati di rifattorizzare la struttura
  logica delle skill (FEAT-022) o di allineare gli stili. Mitigazione: §4 (fuori ambito)
  delimita esplicitamente pulizia stile e stub Copilot.

## 9. Prioritizzazione (MoSCoW)

- **Must:** REQ-001, REQ-002, REQ-005, REQ-006, REQ-007, REQ-008, REQ-010, REQ-011,
  REQ-014, REQ-015, REQ-016.
- **Should:** REQ-003, REQ-004, REQ-009, REQ-012, REQ-013.
- **Could:** estendere il guard di closure a tutti gli asset referenziati per nome nei blocchi
  (oggi copre solo i payload della skill `wiki-author`); documentare nella doc utente
  (`docs/install.md`) che i blocchi CLAUDE.md sono compatti e il dettaglio vive nelle skill.
- **Won't (qui):** budget altitude in CI (FEAT-024); pulizia stile (FEAT-022); stub Copilot
  (FEAT-023); modifiche a `sertor_core`.

## 10. Domande aperte

### Scope (da girare all'utente)

- **[DA CHIARIRE — scope]** Il `CLAUDE.md` di radice di Sertor (il file a root del
  repository dogfood, non distribuito agli ospiti) è in ambito? Attualmente contiene le
  istruzioni di sviluppo di Sertor, che sono molto più estese dei tre blocchi. Il brief
  suggerisce che la feature riguarda gli asset distribuiti + le copie dogfood sincronizzate
  da quelli: il CLAUDE.md di radice **non** è una copia sincronizzata, ma un documento
  autonomo. La risposta attesa è **fuori ambito**, ma va confermata.

### Design/plan (non bloccanti per i requisiti)

- **[DA CHIARIRE in design/plan]** Dove vive il reference unico «How to invoke +
  Windows note»? Opzioni principali: (A) un nuovo asset dedicato nel bundle RAG (es.
  `assets/rag/skills/sertor-cli-reference.md` o simile), distribuito via `sertor install rag`;
  (B) la sezione rimane in `guided-setup/SKILL.md` come fonte designata, e `wiki-playbook.md`
  e il blocco RAG la citano per nome; (C) diventa una sezione nel `wiki-playbook.md`
  (già distribuito da `sertor install wiki`) e gli altri la citano lì. La scelta impatta
  il vincolo REQ-007 (disponibilità condizionale su install senza RAG). Il presente
  requisito specifica il *cosa* (fonte unica, host-agnostica, raggiungibile per nome);
  il *dove* è materia del plan.

- **[DA CHIARIRE in design/plan]** Qual è il criterio quantitativo per «direttiva breve» in
  ciascun blocco ridotto? Una soglia in righe (es. ≤ 20 righe per blocco) oppure il
  criterio qualitativo «solo standing directives» di REQ-001 è sufficiente per l'acceptance?
  FEAT-024 introduce un budget gate automatico; per questa feature il criterio è qualitativo
  (REQ-001) + misurabilità ex-post (CS-1). Se si vuole un numero fisso già ora, va deciso
  prima del plan.

- **[DA CHIARIRE in design/plan]** La guardia di «nessuna copia inline di How to invoke»
  (REQ-012) è un assert testuale (cerca l'heading `## How to invoke` nei blocchi ridotti e
  verifica che sia assente) oppure un check più semantico? L'assert testuale è sufficiente
  per il contratto di non-reintroduzione.

- **[DA CHIARIRE in design/plan]** Il blocco SDLC (`claude-md-block-sdlc.md`, pacchetto
  `sertor-flow`) ha la stessa sezione «How to invoke»? Da una lettura diretta (righe 1–65)
  il blocco SDLC non contiene una copia della sezione «How to invoke» — contiene solo le
  fasi SpecKit, la constitution gate, la error discipline e la git policy. La triplicazione
  coinvolge solo il blocco RAG + `guided-setup` + `wiki-playbook`. Il plan deve confermare
  o smentire che il blocco SDLC è già privo della sezione e quindi REQ-008/009 non lo
  riguardano.
