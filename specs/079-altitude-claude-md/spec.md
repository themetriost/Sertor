# Feature Specification: Ridurre l'altitude dei blocchi CLAUDE.md distribuiti + fonte unica «How to invoke» (E10-FEAT-021)

**Feature Branch**: `079-altitude-claude-md` · **Created**: 2026-06-30 · **Status**: Draft

<!-- Deriva da: FEAT-021 (epica debito-tecnico E10) — requirements/debito-tecnico/altitude-claude-md/requirements.md (audit asset first-party 2026-06-26, ISSUE-07) -->

**Input**: FEAT-021 dell'epica `debito-tecnico` (E10). Sertor inietta **tre blocchi a marker** nel
`CLAUDE.md` (o equivalente per-assistente) di ogni ospite che installa le sue capability: wiki-ritual
(`SERTOR:WIKI-RITUAL`, 71 righe), SDLC-ritual (`SERTOR:SDLC-RITUAL`, 65 righe), RAG-usage
(`SERTOR:RAG-USAGE`, 72 righe) — **~208 righe always-on** caricate integralmente dal client agente a
ogni avvio di sessione, indipendentemente dall'operazione richiesta. Questi blocchi mescolano **regole
di comportamento standing** (cosa usare, cosa non importare, fail-loud sugli errori MCP, flusso
SpecKit) — che giustificano la presenza always-on — con **istruzioni operative di dettaglio** (sintassi
di invocazione, note di troubleshooting Python 3.14/`pywin32`, enumerazione di argomenti CLI) che sono
lookup-on-demand e sprecano budget di contesto se caricate sempre. In particolare la sezione «How to
invoke Sertor's commands / runtime CLIs» con la **Windows note** è **triplicata** in tre sedi quasi
identiche (blocco RAG-usage, skill `guided-setup`, `wiki-playbook`): una modifica va replicata a mano in
tre posti e diverge già parzialmente. La feature **riduce ogni blocco a direttiva breve + pointer** ed
**estrae «How to invoke» in una fonte unica** citata per nome, host-agnostica. È debito di **igiene del
contesto always-on** e di **fonte unica di verità** per l'invocazione.

---

> **Allineamento alla missione (gate Constitution).** La stella polare di Sertor è la **qualità e
> realtà del contesto reso all'agente**. Il budget di contesto è una risorsa finita: ~208 righe di
> dettaglio operativo caricate a ogni sessione — gran parte delle quali l'agente non usa nella maggior
> parte delle operazioni — sottraggono token al lavoro reale e diluiscono il segnale delle direttive
> comportamentali che davvero servono always-on. Ridurre ogni blocco a «direttiva standing + pointer»
> e centralizzare l'invocazione in una fonte unica **protegge** la stella polare su due fronti: più
> budget per il contesto che conta e un'unica fonte di verità che il plan/upgrade mantiene aggiornata
> senza deriva tra copie. È coerente col confine **D↔N**: la riduzione e la centralizzazione sono
> **igiene meccanica degli asset** (file `.md`, guardie di test, sync deterministico — **nessun LLM,
> nessun ragionamento**); il giudizio su quale testo sia load-bearing vs. lookup è del design, fissato
> dai requisiti REQ-014/015/016 (contenuto minimo da preservare per blocco). Complementa FEAT-018
> (onestà/portabilità degli hook): quella rende veri i claim sui surface; questa rende compatto e
> non-duplicato il contesto always-on.

> **Natura del cambiamento: ADDITIVO / igiene host-facing, ZERO codice di core.** La feature **non**
> modifica `sertor_core` né alcun comando/vehicle (Principio XI). Tocca esclusivamente **asset
> host-facing** (i tre `claude-md-block*.md`, le due skill `guided-setup`/`wiki-author`, un eventuale
> nuovo asset di riferimento «How to invoke»), le **copie dogfood `.claude/`** ri-sincronizzate da
> quegli asset, e i **test di guardia** (closure del pointer, parità host-agnostica, sync
> dogfood↔bundle, non-reintroduzione di «How to invoke» nei blocchi). Nessun engine, porta, adapter o
> comando è toccato; il lifecycle install/upgrade/uninstall dei blocchi resta invariato salvo il
> contenuto ridotto. A capacità installate il comportamento osservabile è: blocchi più corti, stesso
> wiring a marker, dettaglio di invocazione raggiungibile on-demand per nome.

> **Decisione di scope — FISSATA con l'utente (non riaprire).** Il `CLAUDE.md` di **radice del
> repository Sertor** (il file a root del dogfood) è **FUORI ambito**: è un documento autonomo di
> istruzione del maintainer, **non un asset sincronizzato** distribuito agli ospiti. La feature riguarda
> SOLO i tre blocchi distribuiti (`claude-md-block*.md`), le copie dogfood `.claude/` sincronizzate da
> quegli asset, le due skill in scope e il reference unico «How to invoke». Codificata in §Out of Scope
> e §Forche RISOLTE (DA-1).

> **Ancoraggio all'esistente (dato di partenza, non da progettare).** Gli asset e i meccanismi in scope
> esistono e sono accertati: i tre asset canonici (`packages/sertor/.../assets/claude-md-block.md`,
> `packages/sertor/.../assets/rag/claude-md-block-rag-usage.md`,
> `packages/sertor-flow/.../assets/claude-md-block-sdlc.md`); le tre copie della sezione «How to invoke»
> (`rag/claude-md-block-rag-usage.md` righe 12–38, `rag/skills/guided-setup/SKILL.md` righe 52–78,
> `claude/skills/wiki-author/wiki-playbook.md` righe 93–112); il wiring a marker
> (`install_wiki.py:440`, `install_rag.py:79-80`, `install_governance.py:65-66`); le guardie
> `test_assets_copilot_guard.py` (parità + closure), `tests/unit/test_assets_sync.py` (sync
> dogfood↔bundle), `test_assets_cli_invocation.py` (footgun `uv run` nudo). **Lettura verificata: il
> blocco SDLC (65 righe) NON contiene la sezione «How to invoke»** — contiene solo le fasi SpecKit, il
> constitution gate, l'error discipline e la git policy; la triplicazione coinvolge solo il blocco RAG +
> `guided-setup` + `wiki-playbook`. I riferimenti **ancorano** i requisiti, non prescrivono il *come*.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — I blocchi always-on caricano meno contesto a ogni sessione (P1, Must)
Un agente frontier apre una sessione su un progetto ospite con le capability Sertor installate. Oggi il
suo `CLAUDE.md` carica ~208 righe sempre, gran parte delle quali è dettaglio operativo (sintassi di
invocazione, troubleshooting) che non serve in quasi tutte le operazioni. Con la feature, ogni blocco
contiene **solo le direttive comportamentali standing** (cosa usare, cosa non importare, fail-loud,
flusso SpecKit) più un **pointer** al dettaglio operativo: l'agente ha più budget per il lavoro reale e
recupera il dettaglio on-demand quando serve.

**Independent Test**: si misura la dimensione (righe/byte) dei tre asset `claude-md-block*.md` prima e
dopo la feature; il totale è misurabilmente inferiore alle 208 righe attuali; nessuna sezione
lookup-on-demand (sintassi di invocazione, note di troubleshooting, enumerazione di argomenti CLI) resta
inline in un blocco.

**Acceptance**:
1. **Given** i tre blocchi ridotti, **When** se ne misura la dimensione, **Then** il totale è
   misurabilmente inferiore alle 208 righe always-on attuali.
2. **Given** un blocco ridotto, **When** lo si ispeziona, **Then** contiene solo direttive
   comportamentali standing e nessuna sezione di dettaglio operativo lookup-on-demand inline.
3. **Given** una direttiva load-bearing rimossa dal corpo del blocco, **When** la si cerca, **Then** il
   blocco include un pointer (per nome dell'asset, non per percorso) all'asset che la porta.

### User Story 2 — «How to invoke» vive in una sola fonte, citata per nome (P1, Must)
Un manutentore di Serto deve aggiornare un dettaglio di invocazione (es. il path del venv o la Windows
note su `pywin32`). Oggi deve modificarlo in tre sedi quasi identiche e rischia che divergano. Con la
feature, la sezione «How to invoke Sertor's commands / runtime CLIs» con la Windows note esiste in
**un'unica sede canonica**; il blocco RAG-usage, `guided-setup` e `wiki-playbook` la **referenziano per
nome** invece di duplicarla. Una sola modifica si propaga.

**Independent Test**: si contano, negli asset distribuiti, le occorrenze della sezione autonoma «How to
invoke» (heading + pattern di invocazione `--project` vs `--directory`, fallback al venv, Windows note);
esiste esattamente in **un** asset; le altre tre sedi storiche (blocco RAG, `guided-setup`,
`wiki-playbook`) contengono un riferimento per nome, non la copia inline.

**Acceptance**:
1. **Given** gli asset distribuiti dopo la feature, **When** si cerca la sezione «How to invoke»
   autonoma, **Then** esiste in esattamente una sede canonica.
2. **Given** il blocco RAG-usage ridotto, `guided-setup/SKILL.md` e `wiki-playbook.md`, **When** li si
   ispeziona, **Then** ciascuno referenzia l'asset canonico per nome e non contiene la copia inline
   della sezione.
3. **Given** l'asset canonico «How to invoke», **When** lo si ispeziona, **Then** è un documento
   host-agnostico (nessun percorso `.claude/`, nessun slash-command, nessun nome di modello/prodotto
   Claude).

### User Story 3 — Nessun pointer rotto: ogni riferimento risolve a un asset reale depositato (P1, Must)
Un ospite installa una capability e l'agente segue un pointer di un blocco ridotto verso un asset
esterno. Il pointer **deve** risolvere a un asset effettivamente depositato sul host per quella
capability: mai un vicolo cieco. Per i blocchi che non portano la skill RAG (wiki, SDLC), il pointer è
condizionale o assente, così non si produce un riferimento morto.

**Independent Test**: per ogni pointer introdotto in un blocco ridotto, l'asset citato per nome è
presente nell'insieme degli asset depositati per la capability corrispondente; la guardia di closure
(parità) verifica offline che ogni asset citato per nome in un body sia depositato.

**Acceptance**:
1. **Given** un blocco ridotto con un pointer a un asset esterno, **When** si esamina il piano di
   distribuzione della stessa capability, **Then** l'asset citato è depositato sul host (closure
   verificata offline).
2. **Given** un install che non porta la capability RAG (solo wiki o solo governance), **When** il
   blocco corrispondente cita l'invocazione, **Then** il riferimento è condizionale o assente, così non
   si produce un pointer a un asset non depositato.
3. **Given** la guardia di closure della parità, **When** gira, **Then** resta verde anche per
   l'eventuale nuovo asset di riferimento «How to invoke».

### User Story 4 — Nessuna direttiva load-bearing viene persa (P1, Must)
La riduzione non deve cancellare il segnale: ogni direttiva comportamentale standing oggi presente nei
blocchi resta accessibile — o nel corpo ridotto (se è standing) o tramite un pointer raggiungibile (se
era dettaglio). In particolare: il blocco wiki conserva la golden rule, l'outline del rituale di step
con le regole di delega, il confine D↔N e il riferimento per nome al wiki playbook; il blocco RAG
conserva la direttiva vehicle-only / no-import `sertor_core`, la regola search-first read-second, la
regola «errore MCP = segnale» e il pointer ai dettagli di invocazione; il blocco SDLC conserva le fasi
SpecKit in ordine, il constitution gate, l'error discipline e la git policy.

**Independent Test**: per ciascun blocco ridotto si verifica la presenza del contenuto minimo
load-bearing enumerato (REQ-014/015/016); ogni direttiva spostata fuori dal corpo è raggiungibile via un
pointer che risolve a un asset reale.

**Acceptance**:
1. **Given** il blocco wiki ridotto, **When** lo si ispeziona, **Then** contiene golden rule, outline
   del rituale con regole di delega, confine D↔N e riferimento per nome al wiki playbook.
2. **Given** il blocco RAG ridotto, **When** lo si ispeziona, **Then** contiene la direttiva vehicle-only
   / no-import `sertor_core`, la regola search-first read-second, la regola «errore MCP = segnale» e il
   pointer ai dettagli di invocazione.
3. **Given** il blocco SDLC ridotto, **When** lo si ispeziona, **Then** contiene le fasi SpecKit in
   ordine, il constitution gate, l'error discipline e la git policy.

### User Story 5 — Parità Claude↔Copilot host-agnostica preservata (P1, Must)
I body ridotti e l'asset «How to invoke» restano host-agnostici: funzionano identici su Claude e su
Copilot CLI senza varianti per-assistente nel contenuto. Nessun percorso letterale `.claude/`, nessun
slash-command, nessun nome di modello/prodotto Claude (lezione FEAT-056/049). La parità è protetta da
guardia offline.

**Independent Test**: la guardia di parità Copilot (`test_assets_copilot_guard.py`) resta verde dopo la
feature: zero `.claude/`, zero slash-command, zero nomi-modello/prodotto Claude negli asset modificati e
nell'eventuale nuovo asset di riferimento.

**Acceptance**:
1. **Given** i body ridotti e l'asset «How to invoke», **When** la guardia di parità gira, **Then** non
   trova percorsi `.claude/`, slash-command o nomi-modello/prodotto Claude.
2. **Given** il payload generato per Copilot CLI, **When** lo si confronta col canonico, **Then** è
   byte-copia degli stessi asset agnostici (nessuna variante per-assistente del contenuto).

### User Story 6 — Sync dogfood↔bundle resta verde e le copie `.claude/` sono riallineate (P1, Must)
Le copie dogfood in `.claude/` (`wiki-author/wiki-playbook.md`, e ogni altra copia delle skill toccate)
restano in byte-parità con gli asset bundlati canonici dopo la riduzione, via
`python -m sertor_installer.sync`. La guardia di sync (`tests/unit/test_assets_sync.py`) resta verde.

**Independent Test**: dopo la riduzione degli asset canonici e il re-sync, le copie dogfood `.claude/`
sono byte-identiche alle sorgenti bundlate; la guardia di sync passa.

**Acceptance**:
1. **Given** gli asset canonici ridotti, **When** si esegue il sync verso `.claude/`, **Then** le copie
   dogfood sono byte-identiche alle sorgenti bundlate.
2. **Given** la guardia di sync dogfood↔bundle, **When** gira dopo i cambiamenti di asset, **Then**
   resta verde.

### User Story 7 — Una guardia impedisce la silenziosa re-introduzione di «How to invoke» nei blocchi (P1, Must)
La fonte unica è protetta in CI: un test fallisce se la sezione «How to invoke» riappare inline in uno
dei tre `claude-md-block*.md` (heading + pattern di invocazione assenti dai blocchi ridotti), o se un
pointer introdotto cita un asset inesistente. Così il debito pagato non si ri-accumula per deriva.

**Independent Test**: si esegue la guardia: (a) ciascuno dei tre `claude-md-block*.md` non contiene la
sezione «How to invoke» inline; (b) ogni pointer per nome in un blocco ridotto risolve a un asset reale
depositato; reintroducendo la sezione inline o un pointer rotto, almeno un test fallisce.

**Acceptance**:
1. **Given** la guardia di non-reintroduzione, **When** gira, **Then** verifica che i tre
   `claude-md-block*.md` non contengano l'heading «How to invoke» né i pattern di invocazione inline.
2. **Given** la guardia di closure dei pointer, **When** gira, **Then** verifica che ogni asset citato
   per nome in un blocco ridotto sia depositato per la capability corrispondente; un pointer a un asset
   inesistente fa fallire il test.
3. **Given** le guardie esistenti (`test_assets_cli_invocation.py`, footgun `uv run` nudo), **When**
   girano sul nuovo asset di riferimento e sui blocchi ridotti, **Then** restano verdi.

## Edge Cases
- **Install solo-wiki o solo-governance (senza RAG)**: il blocco corrispondente non deve produrre un
  pointer verso un asset che vive solo nel bundle RAG → pointer condizionale o assente (US3 — FR-003/007;
  il *dove* del reference impatta REQ-007, è forca di plan).
- **Blocco SDLC privo di «How to invoke»**: verificato in lettura — il blocco SDLC non contiene la
  sezione; REQ-008/009 (sostituzione della copia inline) non lo riguardano. Il plan conferma formalmente
  (forca di *come* DA-D-r3).
- **Divergenza già esistente tra le tre copie** (`guided-setup` nomina la CLI di ritorno se non
  installata, `wiki-playbook` no): la centralizzazione in fonte unica risolve la deriva eleggendo una
  versione canonica (US2 — FR-005).
- **Pointer per nome vs percorso**: i pointer citano l'asset **per nome** (non per percorso
  filesystem), per restare host-agnostici su Claude e Copilot (US5 — FR-002/004/006).
- **Footgun `uv run` nudo**: l'asset di riferimento «How to invoke» eredita il vincolo già verificato da
  `test_assets_cli_invocation.py` (mai `uv run` senza `--project`); il nuovo asset entra nella copertura
  (US7 — FR-012, NFR-3).
- **CLAUDE.md di radice di Sertor**: fuori ambito — documento autonomo, non sincronizzato; la feature
  non lo tocca (eventuale re-sync delle copie `.claude/` derivate dagli asset bundlati è già coperto da
  US6) (DA-1, §Out of Scope).
- **Riduzione che cancella una direttiva standing**: rischio di over-riduzione → mitigato da
  REQ-014/015/016 (contenuto minimo per blocco) e dalla verifica US4 (ogni direttiva rimossa resta
  raggiungibile via pointer).

## Requirements *(mandatory)*

### Requisiti funzionali

**Gruppo A — Riduzione dei blocchi always-on**
- **FR-001 (blocchi a sola direttiva standing).** Ciascuno dei tre blocchi always-on
  (`claude-md-block.md`, `claude-md-block-rag-usage.md`, `claude-md-block-sdlc.md`) è ridotto a contenere
  **solo direttive comportamentali standing**; il dettaglio operativo lookup-on-demand (sintassi di
  invocazione, note di troubleshooting, enumerazione di argomenti CLI) è rimosso dal corpo inline.
  *(REQ-001; CS-1)*
- **FR-002 (pointer per nome al contenuto load-bearing rimosso).** Quando una sezione rimossa da un
  blocco contiene informazione load-bearing per l'agente (es. regole di invocazione, comportamento di
  fallback), il blocco ridotto include un **pointer** all'asset che la porta, espresso come **nome
  dell'asset** (non un percorso filesystem), così l'agente lo recupera on-demand. *(REQ-002; CS-1/CS-4)*
- **FR-003 (nessun pointer a un asset non depositato).** Se il pointer di un blocco ridotto riferisce un
  asset che non è depositato sul host come parte dello stesso install di capability, allora l'install
  **non** produce quel pointer (il riferimento è valido solo quando l'asset puntato è presente).
  *(REQ-003; CS-3)*
- **FR-004 (blocchi host-agnostici).** I blocchi ridotti non contengono alcun percorso
  assistente-specifico (es. `.claude/`), slash-command o nome di prodotto/modello, preservando la
  convenzione di authoring host-agnostico (FEAT-056/049). *(REQ-004; CS-5)*

**Gruppo B — Fonte unica «How to invoke + Windows note»**
- **FR-005 (fonte unica «How to invoke»).** La sezione «How to invoke Sertor's commands / runtime CLIs»,
  inclusa la Windows note su `pywin32`/Python 3.14 di sistema, esiste in **esattamente un** asset
  canonico distribuito dopo la feature; tutte le altre sedi la referenziano per nome. *(REQ-005; CS-2)*
- **FR-006 (asset canonico host-agnostico).** L'asset canonico «How to invoke» è esso stesso un
  documento host-agnostico: nessun percorso assistente-specifico, nessuno slash-command, nessun nome di
  prodotto/modello dell'assistente. *(REQ-006; CS-2/CS-5)*
- **FR-007 (raggiungibilità del reference per la capability rilevante).** L'asset canonico «How to
  invoke» è depositato sul host come parte dell'install in cui le regole di invocazione sono rilevanti
  (la capability RAG è il contesto primario); dove avviene un install solo-wiki o solo-governance senza
  la capability che porta il reference, il riferimento nel blocco corrispondente non produce un pointer
  morto. *(REQ-007; CS-3)*
- **FR-008 (`guided-setup` referenzia, non duplica).** Dove `guided-setup/SKILL.md` conteneva la copia
  inline della sezione di invocazione, la skill referenzia l'asset canonico per nome, istruendo l'agente
  a leggerlo quando servono i dettagli di invocazione. *(REQ-008; CS-2)*
- **FR-009 (`wiki-playbook` referenzia, non duplica).** Dove `wiki-playbook.md` conteneva la sezione
  inline «How to invoke the runtime CLIs», il playbook referenzia l'asset canonico per nome (o rinvia
  alla skill che porta il reference — decisione di plan), così il dettaglio di invocazione vive in un
  solo posto. *(REQ-009; CS-2)*

**Gruppo C — Guardie di parità, closure e sync**
- **FR-010 (parità + closure verde).** La guardia di parità esistente
  (`test_assets_copilot_guard.py`) resta verde dopo la feature; ogni nuovo asset introdotto come
  reference canonico «How to invoke» è coperto dall'assert di closure (ogni asset citato per nome in un
  body è depositato per la capability rilevante). *(REQ-010; CS-5/CS-6)*
- **FR-011 (sync dogfood↔bundle verde).** La guardia di sync (`tests/unit/test_assets_sync.py`) resta
  verde dopo la feature; le copie dogfood degli asset modificati sotto `.claude/` sono ri-sincronizzate
  in byte-parità con le sorgenti canoniche bundlate. *(REQ-011; CS-6)*
- **FR-012 (guardia di non-reintroduzione «How to invoke»).** La feature fornisce, o estende una guardia
  esistente, un assert che i tre `claude-md-block*.md` non contengano una copia inline della sezione
  «How to invoke» (heading e pattern di invocazione assenti dai blocchi ridotti), prevenendo la
  re-introduzione silenziosa. *(REQ-012; CS-2/CS-6)*
- **FR-013 (additività lifecycle).** Il cambiamento è additivo al lifecycle dell'installer: i percorsi
  install/upgrade/uninstall delle tre capability restano coerenti; un blocco ridotto è ancora idempotente
  su install, aggiornato su upgrade e rimosso su uninstall. *(REQ-013; CS-1)*

**Gruppo D — Coerenza dei blocchi ridotti (contenuto minimo load-bearing)**
- **FR-014 (blocco wiki — minimo).** Il `claude-md-block.md` (wiki ritual) ridotto conserva almeno: la
  golden rule per la documentazione wiki, l'outline del rituale di step con le regole di delega, il
  confine D↔N (meccanico vs giudizio) e un riferimento per nome al wiki playbook. *(REQ-014; CS-4)*
- **FR-015 (blocco RAG — minimo).** Il `claude-md-block-rag-usage.md` (RAG usage) ridotto conserva
  almeno: la direttiva di usare i vehicle (CLI / MCP) e mai importare `sertor_core` direttamente; la
  regola search-first read-second; la regola «errore MCP = segnale»; e il pointer ai dettagli di
  invocazione. *(REQ-015; CS-4)*
- **FR-016 (blocco SDLC — minimo).** Il `claude-md-block-sdlc.md` (SDLC ritual) ridotto conserva almeno:
  le fasi del flusso SpecKit in ordine; il constitution check gate; l'error discipline (fix, don't
  suppress); e il riassunto della version control discipline. *(REQ-016; CS-4)*

### Requisiti non funzionali
- **RNF-1 (Principio XI):** zero modifiche a `sertor_core`; la feature tocca esclusivamente asset
  host-facing (file `.md`, guardie di test) e nessun codice di runtime del core; nessun LLM coinvolto.
  *(NFR-1)*
- **RNF-2 (Principio X — host-agnostico):** ogni asset modificato o introdotto è host-agnostico:
  funziona identico su Claude e Copilot CLI senza varianti per-assistente nel contenuto; il renderer del
  payload Copilot resta invariato (byte-copia degli `.md` agnostici). *(NFR-2)*
- **RNF-3 (Non-regressione):** le suite esistenti (`sertor`, `sertor-install-kit`, `sertor-flow`, root)
  restano verdi; in particolare `test_assets_copilot_guard.py`, `test_assets_sync.py` e
  `test_assets_cli_invocation.py` (già copre `rag/claude-md-block-rag-usage.md`,
  `rag/skills/guided-setup/SKILL.md`, `claude/skills/wiki-author/wiki-playbook.md`) passano. *(NFR-3)*
- **RNF-4 (Non-regressione installabilità):** un ospite già installato che esegue `sertor upgrade`
  riceve i blocchi ridotti (via il meccanismo di aggiornamento del blocco a marker); gli ospiti non
  ancora installati ricevono i blocchi ridotti al primo install. Nessun ospite resta col vecchio
  contenuto verboso dopo l'upgrade. *(NFR-4)*
- **RNF-5 (Closure del pointer):** ogni riferimento per nome a un asset introdotto come reference «How
  to invoke» punta a un file presente nell'insieme degli asset depositati per la capability
  corrispondente: nessun pointer in produzione porta a un asset assente; verificabile offline senza un
  host reale. *(NFR-5; FR-003/007)*
- **RNF-6 (Riduzione non arbitraria):** la riduzione conserva *solo* il testo che un agente deve avere
  in memoria a ogni sessione per operare correttamente e sposta *tutto* il testo che è un lookup; il
  criterio è qualitativo (REQ-001) con misurabilità ex-post (CS-1) — **nessuna soglia numerica fissata
  qui** (il budget di altitude deterministico in CI è FEAT-024, cross-ref). *(NFR-6)*

### Key Entities
- **Blocco a marker ridotto (`claude-md-block*.md`)** — uno dei tre asset always-on iniettati nel
  `CLAUDE.md` host, ridotto a sole direttive comportamentali standing + pointer; mantiene il proprio
  marker e il lifecycle install/upgrade/uninstall; il dettaglio operativo è spostato fuori.
- **Asset canonico «How to invoke»** — l'unica sede distribuita che ospita la sezione «How to invoke
  Sertor's commands / runtime CLIs» con la Windows note; host-agnostico, citabile per nome dagli altri
  asset; la sua collocazione (nuovo asset dedicato vs sezione di un asset esistente) è di plan.
- **Pointer per nome** — il riferimento, in un blocco ridotto o in una skill, all'asset che porta il
  dettaglio rimosso, espresso come nome dell'asset (non percorso filesystem), valido solo se l'asset è
  depositato per la capability corrispondente.
- **Copia inline di «How to invoke» (da eliminare/centralizzare)** — le tre occorrenze storiche
  (blocco RAG-usage, `guided-setup/SKILL.md`, `wiki-playbook.md`); dopo la feature restano riferimenti
  per nome, non copie.
- **Guardie di asset** — `test_assets_copilot_guard.py` (parità host-agnostica + closure dei pointer),
  `tests/unit/test_assets_sync.py` (byte-parità dogfood↔bundle), `test_assets_cli_invocation.py`
  (footgun `uv run` nudo), più la guardia di non-reintroduzione di «How to invoke» nei blocchi.
- **Copie dogfood `.claude/`** — le copie sincronizzate degli asset modificati (es.
  `.claude/skills/wiki-author/wiki-playbook.md`) re-sincronizzate via `sertor_installer.sync`.

## Success Criteria *(mandatory)*
- **CS-1 (altitude ridotta):** la dimensione complessiva dei tre blocchi always-on
  (`claude-md-block.md`, `claude-md-block-sdlc.md`, `claude-md-block-rag-usage.md`) è misurabilmente
  inferiore alle 208 righe attuali dopo la feature; nessuna sezione lookup-on-demand resta inline (solo
  direttive standing). Verificabile misurando righe/byte degli asset e ispezionando l'assenza delle
  sezioni di dettaglio. *(FR-001/013, US1)*
- **CS-2 (fonte unica «How to invoke»):** la sezione «How to invoke» con la Windows note esiste in
  **un'unica** sede negli asset distribuiti; le altre sedi (blocco RAG, `guided-setup`, `wiki-playbook`)
  la referenziano per nome. Verificabile contando le occorrenze della sezione autonoma nei file asset.
  *(FR-005/008/009/012, US2)*
- **CS-3 (nessun pointer rotto):** ogni pointer introdotto nei blocchi ridotti verso un asset esterno
  punta a una risorsa effettivamente depositata sul host (closure); su install senza la capability che
  porta il reference, il pointer è condizionale o assente. Verificabile offline tramite la guardia di
  closure. *(FR-002/003/007/010, US3)*
- **CS-4 (contenuto load-bearing preservato):** nessuna direttiva comportamentale standing (cosa usare,
  cosa non importare, fail-loud sugli errori MCP, gate di privacy memoria, flusso SpecKit, error
  discipline, git policy) viene rimossa o resa inaccessibile; il pointer porta a un asset raggiungibile e
  completo. Verificabile controllando il contenuto minimo di REQ-014/015/016 e la raggiungibilità dei
  pointer. *(FR-014/015/016, US4)*
- **CS-5 (parità host-agnostica preservata):** i body ridotti e l'asset «How to invoke» restano
  host-agnostici (zero `.claude/`, zero slash-command, zero nomi-modello/prodotto Claude); la guardia di
  parità Copilot resta verde. Verificabile eseguendo `test_assets_copilot_guard.py`. *(FR-004/006/010,
  US5)*
- **CS-6 (sync dogfood preservato):** le copie dogfood in `.claude/` restano in byte-parità con gli
  asset bundlati; la guardia `tests/unit/test_assets_sync.py` resta verde dopo la feature. Verificabile
  eseguendo la guardia di sync. *(FR-011/012, US6/US7)*

## Assumptions
- **A-001 — Il reference «How to invoke» è un asset `.md` già distribuibile** tramite il meccanismo
  esistente di byte-copia dell'installer (FILE create-if-absent o equivalente): la feature **usa**
  l'infrastruttura esistente; il *come* esatto (nome file, cartella, asset nuovo vs sezione di uno
  esistente) è di plan. *(FR-005/007)*
- **A-002 — I blocchi ridotti possono referenziare per nome un asset distribuito nello stesso install**
  (es. il blocco RAG referenzia un asset RAG). Per i blocchi wiki e SDLC, che non portano la capability
  RAG, il pointer è condizionale o assente (FR-003/007). *(FR-002/003)*
- **A-003 — Il meccanismo del blocco a marker** (idempotente su install, aggiornato su upgrade, rimosso
  su uninstall) è invariato; la feature cambia solo il **contenuto** dei blocchi, non il loro wiring.
  *(FR-013, NFR-4)*
- **A-004 — Le guardie di asset esistono e sono testate** (`test_assets_copilot_guard.py`,
  `tests/unit/test_assets_sync.py`, `test_assets_cli_invocation.py`): la feature le usa/estende, senza
  modifiche al kit oltre alla copertura del nuovo asset. *(FR-010/011/012)*
- **A-005 — Il blocco SDLC non contiene «How to invoke»** (lettura verificata, righe 1–65): FR-008/009
  non lo riguardano; il plan conferma formalmente. *(DA-D-r3)*

### Out of Scope (dichiarato)
- **CLAUDE.md di radice del repository Sertor** — documento autonomo di istruzione del maintainer, non
  un asset sincronizzato distribuito agli ospiti: **fuori ambito** per decisione utente (DA-1). La
  feature non lo tocca; l'eventuale re-sync delle copie `.claude/` derivate dagli asset bundlati è già
  coperto da CS-6.
- **Pulizia stile generale delle skill** (ALL-CAPS, sezioni «What NOT to do», ToC mancante in
  `wiki-playbook.md`) → **FEAT-022** (cross-ref).
- **Stub `assets/copilot/**`** con solo `.gitkeep` → **FEAT-023** (cross-ref).
- **Budget di altitude in CI** (test che fallisce se un blocco supera N righe) → **FEAT-024** (cross-ref).
  Questa feature paga il debito (criterio qualitativo «direttiva + pointer» + misurabilità ex-post);
  FEAT-024 mette il freno deterministico che impedisce il re-accumulo. **Nessuna soglia numerica è
  fissata qui.**
- **Installer CLI o vehicle** (`sertor install`, `sertor-rag`, ecc.) — invariati.
- **Contenuto delle skill al di là della sezione «How to invoke»** (logica di `guided-setup`, operazioni
  wiki) — invariato.
- **Codice di `sertor_core`** o qualunque comando/vehicle — zero modifiche (Principio XI).

> **Tracciamento dello scope.** I rinvii reali sono già **promossi a casa durevole** nel backlog
> d'epica: pulizia stile/struttura skill → **FEAT-022**; stub `assets/copilot/` → **FEAT-023**; budget
> di altitude in CI → **FEAT-024**. Nessun rinvio reale resta sepolto in `specs/`. La feature è *done*
> quando i tre blocchi sono ridotti a direttiva + pointer (altitude misurabilmente inferiore), «How to
> invoke» vive in una sola fonte host-agnostica citata per nome, nessun pointer è rotto, il contenuto
> load-bearing è preservato e raggiungibile, e le guardie (parità + closure + sync dogfood↔bundle +
> non-reintroduzione) sono verdi (additive all'installer).

### Forche di design — RISOLTE con l'utente (per `/speckit-plan`)
- **DA-1 — Scope CLAUDE.md di radice: RISOLTA.** Il `CLAUDE.md` a root del repository Sertor è **fuori
  ambito** (documento autonomo, non sincronizzato). La feature riguarda SOLO i tre blocchi distribuiti +
  copie dogfood `.claude/` + reference unico. *(decisione utente; §Out of Scope.)*
- **DA-2 — Strategia: RISOLTA.** Ridurre ogni blocco a «direttiva breve + pointer» ed estrarre «How to
  invoke» in una fonte unica citata per nome, host-agnostica. *(decisione utente; FR-001/005.)*

### Forche di design — RESIDUE (questioni di *come*, per `/speckit-plan`)
- **DA-D-r1 — Dove vive il reference unico «How to invoke + Windows note»:** (A) nuovo asset dedicato nel
  bundle RAG (es. `assets/rag/skills/sertor-cli-reference.md` o simile), distribuito da
  `sertor install rag`; (B) la sezione resta in `guided-setup/SKILL.md` come fonte designata e gli altri
  la citano per nome; (C) diventa una sezione del `wiki-playbook.md` (distribuito da `sertor install
  wiki`) e gli altri la citano lì. La scelta impatta REQ-007 (disponibilità condizionale su install
  senza RAG). Il *cosa* (fonte unica, host-agnostica, per nome) è fissato; il *dove* è di plan.
- **DA-D-r2 — Criterio qualitativo per «direttiva breve»:** il criterio è qualitativo («solo standing
  directives», REQ-001) con misurabilità ex-post (CS-1). **Nessuna soglia numerica in righe** è fissata
  qui — il budget gate deterministico è FEAT-024. Se in plan si vuole un numero indicativo, va deciso
  esplicitamente come obiettivo non vincolante.
- **DA-D-r3 — Conferma formale che il blocco SDLC non contiene «How to invoke»:** lettura verificata
  (righe 1–65: nessuna sezione di invocazione). Il plan conferma formalmente che REQ-008/009 non
  toccano il blocco SDLC.
- **DA-D-r4 — Forma della guardia di non-reintroduzione (REQ-012):** assert testuale (cerca l'heading
  «How to invoke» e i pattern di invocazione nei blocchi ridotti e verifica che siano assenti) vs check
  più semantico; l'assert testuale è sufficiente per il contratto di non-reintroduzione. *Come* di plan.
