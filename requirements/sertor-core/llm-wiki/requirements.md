# Requisiti — LLM Wiki (end-to-end)

**Epica**: `sertor-core` · **Feature**: `llm-wiki` (consolidamento e2e)
**Status**: ✅ **READY — approvato per il design** (iterazione 13; tutti i temi T0–T7 risolti)
**Creato**: 2026-06-04
**Relazione con il lavoro esistente**: **consolida e supersede FEAT-003 creazione+indicizzazione**
(`requirements/sertor-core/wiki-creazione/requirements.md`): ne **assorbe** struttura/record/distill/
idempotenza (invariati) e ne fa **override** su *ingest/sources* e *indicizzazione*. FEAT-003 resta come
**storico**; `llm-wiki` è la **feature wiki canonica** (T0 risolto → D-10).

> **Come si lavora a questo documento.** È una bozza che cresce per **iterazioni** guidate da domande.
> Le decisioni prese si consolidano in §"Decisioni prese"; i punti ancora aperti vivono in §"Domande
> aperte (per iterazione)". Quando il contenuto è stabile, viene formalizzato con la skill
> `/requirements` (requisiti EARS, MoSCoW, criteri di successo misurabili, rischi).

---

## 1. Visione (perché)

Portare capacità RAG su qualunque repository in modo riproducibile, con **una sola verità
interrogabile**: i sorgenti (il *come*) e la documentazione/wiki (il *perché*) coesistono nello stesso
corpus; la documentazione nuova vive **accanto ai sorgenti** tramite l'**LLM Wiki**. L'LLM Wiki deve
funzionare **end-to-end**: dalla produzione del contenuto (manuale e automatica) alla manutenzione,
all'indicizzazione, fino all'interrogazione. Il **codice è una fonte opzionale**: LLM Wiki + RAG vale
anche per **progetti senza codice** (D-9).

## 2. Modello di riferimento — l'LLM Wiki di Karpathy

> **Fonte primaria**: gist `karpathy/llm-wiki.md` (4 apr 2026,
> <https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f>). Il nostro wiki si ispira a
> questo pattern; lo riportiamo qui come **riferimento normativo** per il design e2e.

**Idea centrale (vs RAG classico).** Invece di ri-scoprire la conoscenza a ogni query (il RAG recupera
chunk grezzi ogni volta, senza accumulo), l'LLM **costruisce e mantiene un wiki persistente** — un
insieme strutturato e interconnesso di file `.md` che sta **tra l'utente e le fonti grezze**. La
conoscenza è **compilata una volta e tenuta aggiornata**, non riderivata a ogni domanda: i
cross-reference ci sono già, le contraddizioni sono già state segnalate.

**Tre livelli.**
1. **Fonti grezze (raw)** — documenti **immutabili** (articoli, paper, immagini). L'LLM le **legge ma
   non le modifica mai**: sono la *source of truth*.
2. **Il wiki** — directory di `.md` **interamente di proprietà dell'LLM** (le scrive e mantiene lui).
3. **Lo schema** — documento di configurazione (es. `CLAUDE.md`) che definisce struttura, convenzioni e
   workflow (ingest / query / maintenance). È volutamente astratto: l'agente lo **co-evolve** con l'utente.

**File chiave.**
- `index.md` — **catalogo** di tutto: ogni pagina con link + sommario di una riga (+ metadati). L'LLM lo
  legge **per primo** per trovare le pagine rilevanti. Aggiornato a ogni ingest.
- `log.md` — registro **append-only** cronologico (ingest/query/lint), formato
  `## [YYYY-MM-DD] ingest | Titolo` (parsabile).
- **Pagine** — `.md` con **wikilink** `[[...]]`, cross-reference, **frontmatter** (tag, date, conteggio
  fonti). Tipi: entità, concetti, fonti, confronti, sintesi.

**Operazioni / workflow.**
- **Ingest** — l'utente mette una fonte nel raw e chiede di processarla; l'LLM legge, discute i
  takeaway, scrive una pagina-sommario, **aggiorna l'indice**, aggiorna le pagine entità/concetti
  collegate, appende al log. *Una sola fonte può toccare 10–15 pagine.* Uno-a-uno guidato o batch.
- **Query** — l'LLM cerca via indice, legge, sintetizza **con citazioni**; le risposte possono prendere
  forme diverse (tabelle, slide, grafici). **Punto chiave:** le buone risposte vanno **rifilate nel wiki
  come nuove pagine** (non disperse nella chat).
- **Lint** — health-check periodico: contraddizioni tra pagine, claim superate, pagine orfane, concetti
  senza pagina, cross-reference mancanti, lacune di dati (anche per web search).

**Principi.**
- **Immutabilità delle fonti grezze** (source of truth, mai modificata).
- **Separazione dei ruoli**: l'umano fa *sourcing, esplorazione e domande giuste*; l'LLM fa **tutto il
  lavoro ingrato** (riassumere, cross-referenziare, archiviare, bookkeeping).
- **Manutenzione a costo ~zero**: il costo non è leggere/pensare ma il *bookkeeping*; l'LLM non si
  annoia, non dimentica un cross-reference, tocca 15 file in un colpo.
- **Niente abbandono**: gli umani mollano i wiki perché la manutenzione cresce più del valore; l'LLM no.
- **Pagine self-contained**: scritte perché un agente *single-shot* le riprenda senza contesto di chat.

**Uso previsto.** È un *idea file* da **copiare nel proprio agente** (Claude Code, Codex, …) e
**co-evolvere lo schema** insieme. Setup tipico: agente da un lato, **Obsidian** dall'altro per navigare
in tempo reale — *"Obsidian è l'IDE, l'LLM è il programmatore, il wiki è la codebase"*. Essendo un repo
git di `.md`, versioning e collaborazione sono gratis. Per wiki grandi: motori di ricerca (BM25/vector +
re-ranking LLM).

**Mappatura su Sertor (allineamenti ✓, parziali ◐, divergenze ⚠️).**
- ✓ **Convenzioni allineate**: `index.md` + `log.md` (stesso formato voce log), frontmatter, wikilink,
  wiki come repo git.
- ◐ **Operazioni**: le primitive `create_wiki`/`record`/`ingest`/`distill`/`index_wiki` **esistono**
  (FEAT-003) ma **non sono ancora orchestrate** da un loop agentico (manca il volante) — è il gap che
  **D-2** colma.
- ⚠️ **Una sola verità interrogabile**: Karpathy tiene il wiki **separato** dalle fonti grezze; Sertor
  punta a interrogare wiki **+ codice insieme** — ma **solo nel momento di retrieval (b)**, con
  **collezioni separate** interrogate congiuntamente (vedi **D-3**). Un'**estensione** del pattern.
- ⚠️ **Source of truth (stratificata)**: per Karpathy è il *raw* esterno unico; per Sertor è **stratificata**
  (vedi **D-4**) — **codice/test** per il *comportamento*, **discussioni/SpecKit/`manual_edited`** per il
  *perché*. La convenzione **`manual_edited/`** (D-1) è l'analogo del *raw* immutabile (l'LLM non lo
  modifica ma ne **compila** pagine derivate).
- ⚠️ **Superficie**: Karpathy usa Obsidian (navigazione/IDE umano); Sertor espone il wiki via
  **RAG / CLI / MCP** (superficie programmatica) → tema T6.
- ⚠️ **Esecuzione**: in Karpathy l'agente *è* l'LLM che scrive a mano i `.md`; in Sertor il **layer
  agentico orchestra e riusa FEAT-003** (D-2), come **skill client-agnostica invocata al commit** dal
  configuration-manager / equivalente del client (D-8).

---

## 3. Glossario (due livelli oggi distinti)

- **Layer A — Governance (Claude Code)**: hook `SessionStart` (lettura stato), comando `/wiki`
  (manuale), agente `wiki-keeper` (su delega). Oggi **scrive i Markdown a mano**.
- **Layer B — Prodotto Sertor (FEAT-003)**: libreria `sertor_core.wiki`
  (`create_wiki`/`record`/`ingest`/`distill`/`index_wiki`) + CLI `sertor wiki index`. Oggi le
  operazioni di *authoring* (`record`/`ingest`/`distill`) **non sono invocate da nessuno** (solo test):
  manca il "volante" (CLI/MCP/agente).

> Tema centrale di questo requisito: definire **come i due layer si uniscono** in un flusso e2e.

---

## 4. Decisioni prese

### D-1 — Convenzione "manuale vs automatico" (cartella `manual_edited/`)
- I file Markdown **scritti a mano dall'umano** vivono in **`wiki/manual_edited/`** e sono trattati
  come **documentazione esterna / fonte autorevole**.
- L'automazione (agente `wiki-keeper` e skill wiki FEAT-003) **non modifica né cancella mai** i file in
  `manual_edited/`: li può solo **leggere** (come contesto/fonte) e **indicizzare**.
- **Il wiki generato** (`concepts/ tech/ experiments/ syntheses/` + `index.md`, `log.md`) è
  **automatico**: generato/mantenuto dai tool, rigenerabile e modificabile.
- *(Aggiornato in D-6: `sources/` → `ingested_sources/` è una cartella di **input** non versionato, non
  fa parte del wiki generato. Modello a due classi input/generato in D-6.)*
- Implicazioni: (a) il `wiki-keeper` non scrive in `manual_edited/`; (b) un eventuale auto-fix tratta
  `manual_edited/` come "curated" (intoccabile); (c) `manual_edited/` **NON è indicizzata nel RAG**
  (vedi **D-7**): è *input*, si interroga via i concetti compilati; le pagine generate possono linkarla
  (provenienza non indicizzata); (d) il suo **contenuto è compilato** in pagine wiki derivate, ma il
  **file sorgente resta immutato** (vedi **D-4**) — è l'analogo del *raw* immutabile di Karpathy.
- *(Da rifinire in EARS; nome cartella e posizione confermati: dentro `wiki/`.)*

### D-2 — Il wiki è popolato/mantenuto da un layer AGENTICO (skill + hook) che riusa FEAT-003
- Il popolamento e la manutenzione del wiki seguono il **pattern Karpathy** (§2): il lavoro di
  bookkeeping (riassumere, cross-referenziare, archiviare, aggiornare `index.md`/`log.md`, segnalare
  contraddizioni) è svolto da un **layer agentico** fatto di **skill** e **hook**, non dall'editing
  manuale come processo primario.
- Queste skill/hook **riusano le operazioni di FEAT-003** (`create_wiki`/`record`/`ingest`/`distill`/
  `index_wiki`) come **primitive di libreria** dove la funzionalità è già coperta (DRY, Principio III),
  aggiungendovi sopra l'**orchestrazione agentica** (leggere le fonti, decidere cosa scrivere, toccare
  più pagine in un colpo). Dove FEAT-003 non copre, la skill può fare di più.
- **Risolve T2**: i due livelli del Glossario (§3) si **uniscono** — il layer agentico è l'orchestratore,
  FEAT-003 è il motore. L'editing manuale resta possibile ma **confinato a `manual_edited/`** (D-1).
- *(Dettagli aperti: quali skill esatte, quali hook/trigger — vedi §5 e T1/T3.)*

### D-3 — Due momenti distinti: generazione (Karpathy) e indicizzazione/retrieval (RAG paritario)
Il ciclo di vita del wiki si separa in **due momenti** con modelli diversi; così la divergenza "una
sola verità interrogabile" e il "peso paritario" (FEAT-003 FR-009) **non sono in conflitto**.

**(a) Generazione del contenuto wiki — modello Karpathy (§2).**
- Contenuto in **linguaggio naturale**, organizzato in **concetti linkati** (formato wiki), generato e
  **aggiornato incrementalmente**.
- Da un **insieme di fonti-input configurabile e modificabile durante il ciclo di vita** del progetto.
  **Set iniziale** — *versionate* (refresh al commit, D-5): log discussioni · `manual_edited/` ·
  sorgenti · test · SpecKit (`specs/`); *non versionata* (trigger manuale, D-6): `ingested_sources/`.
- Qui il wiki è il **livello compilato** (il *perché*); le fonti-input ne sono il "raw".

**(b) Indicizzazione + interrogazione (RAG).**
- Il wiki generato è un **corpus del RAG paritario** ai sorgenti — il principio di **peso paritario**
  (FEAT-003 FR-009) vale **solo qui**.
- **Packaging: collezioni separate** (wiki ≠ codice), **interrogate insieme** → "una sola verità
  interrogabile" **a livello di query**, ma ogni collezione si **rigenera in modo indipendente** (risolve
  il rebuild distruttivo trovato col dogfood).

**Conseguenze.**
- La divergenza "una sola verità interrogabile" (§2) vale **solo nel momento (b)**.
- Nel momento (a) il **codice è un input** alla generazione → collega al Punto 2 (source of truth) e dà
  casa alla **verifica di freschezza wiki-vs-codice** come preoccupazione di (a).
- Il "peso paritario" (FEAT-003 FR-009) **non si ribalta**.

### D-4 — Verità stratificata, gerarchia di autorità e obsolescenza
- **Verità stratificata** (non esiste un'unica *source of truth*):
  - **codice + test** = autorità sul **comportamento** (il *come/cosa fa*);
  - **discussioni / SpecKit / `manual_edited`** = autorità sul **perché** (decisioni, razionale).
- **Gerarchia di default per i conflitti**: comportamento → **codice/test**; "perché" → **decisione
  registrata** (SpecKit/`manual_edited`).
- **Gerarchia configurabile (SHOULD)**: deve essere possibile **configurare una gerarchia di autorità
  esplicita** che sovrascrive il default.
- **Conflitti che coinvolgono `manual_edited` → human-in-the-loop**: se la generazione/verifica rileva
  un'incongruenza che tocca `manual_edited`, la skill **non decide da sola**: **segnala e chiede
  all'utente** come procedere (non modifica né scarta autonomamente la fonte autorevole).
- **`manual_edited` compilato (raffina D-1)**: il contenuto di `manual_edited/` **viene compilato** in
  pagine wiki derivate (sintesi/integrazione) ed **eventualmente linkato** alla fonte; il **file sorgente
  resta immutato** (l'LLM non lo modifica). È l'analogo del *raw* immutabile di Karpathy.
- **Definizione di "wiki obsoleto"**: una pagina è obsoleta se contraddice **il codice/test**
  (comportamento) **oppure** una **decisione registrata** (SpecKit/`manual_edited`). Definisce cosa
  controlla la verifica di freschezza del momento (a) (→ T5).

### D-5 — Refresh git-driven al commit (fonti versionate) + git come prerequisito
- Le fonti-input **versionate** (codice, test, SpecKit, log discussioni, `manual_edited/`) vivono in git;
  il wiki si aggiorna **al commit**, elaborando il **changeset dall'ultimo commit** → **generazione
  incrementale guidata da git** ("ultimo commit elaborato" = *watermark*).
- **Git è un prerequisito documentato** del meccanismo (versioning + tracciabilità della provenienza).
- `manual_edited/` accetta **qualunque contenuto leggibile**; i **binari non leggibili** sono esclusi;
  struttura libera.

### D-6 — `ingested_sources/` (ex `sources/`): input esterno NON versionabile, a trigger manuale
- La cartella `sources/` è **rinominata `ingested_sources/`** e **cambia ruolo**: da *output di riassunti
  generati* a **punto d'ingresso delle sorgenti che NON possiamo versionare** (materiale esterno: paper,
  contenuti web, ecc., fuori da git).
- **Popolamento/aggiornamento a trigger MANUALE dell'utente** (tipicamente in creazione, ma anche in
  aggiornamento) — non essendo versionato, manca il segnale "commit" di D-5.
- Il wiki la **usa come input** per **generare e arricchire i concetti** → è a tutti gli effetti **un
  input dell'LLM Wiki** (non un output di pagine-riassunto).
- **Modello a due classi** risultante:
  - **Input** (l'LLM legge, non scrive): codice · test · SpecKit · log discussioni · `manual_edited/`
    (versionato) · `ingested_sources/` (non versionato).
  - **Wiki generato** (l'LLM scrive): `concepts/` · `tech/` · `experiments/` · `syntheses/` · `index.md`
    · `log.md`.
- **Impatto su FEAT-003 (istanza di T0)**: cambia la semantica di `sources/` e dell'operazione `ingest`
  (oggi produce riassunti *in* `sources/`) → da rivedere.

### D-7 — Retrieval "puro Karpathy": indicizzato solo il wiki generato + il codice
- Nel momento (b) il **RAG contiene SOLO**: il **wiki generato** + il **codice** (collezioni separate,
  query congiunta, D-3).
- Le cartelle di **input** (`manual_edited/`, `ingested_sources/`) **non sono indicizzate** né inserite
  nel RAG: si interrogano **solo attraverso** i concetti compilati del wiki (interroghi il *compilato*,
  non il *raw* — fedeltà al pattern Karpathy).
- Le pagine del wiki generato **possono contenere riferimenti/link** alle fonti di input (provenienza),
  ma **tali riferimenti non sono indicizzati né inseriti nel RAG**.
- **Override esplicito di D-1**: la precedente implicazione "`manual_edited/` entra nel RAG come doc
  paritaria" è **annullata** — `manual_edited/` è input, non corpus interrogabile.

### D-8 — Skill client-agnostica invocata al commit; trigger contract portabile; setup rilascia il trigger
- La generazione/manutenzione del wiki è una **skill a sé**, **distinta** dal componente di versioning
  (configuration-manager): SRP (Principio VII). Il config-manager **non** assorbe la logica di
  generazione.
- È **invocata al commit** dal configuration-manager (o dall'equivalente del client): il config-manager
  decide il **QUANDO** (commit + changeset), la skill fa il **COSA** (riusa FEAT-003).
- Esecuzione **sincrona quando possibile** → gli output entrano nello **stesso commit** (FR-018);
  **fallback asincrono** (commit di follow-up) se la sincrona non è praticabile (costo/latenza LLM).
- **Contratto di trigger portabile**: definito in modo **client-agnostico** ("al commit, col changeset");
  il configuration-manager è solo il **binding** per Claude Code. Altri client (Copilot/Codex) forniscono
  il proprio binding → il prodotto è **(i)** uno strumento di un client LLM, non legato a un client solo.
- **Setup rilascia il binding del trigger (Aggiunta A)**: poiché la skill dipende dal suo trigger, il
  **setup del prodotto deve installare anche il binding** (per Claude Code: il configuration-manager /
  hook di commit). Altrimenti il trigger **si perde** e la generazione non scatta.

### D-9 — LLM Wiki + RAG come asset anche per progetti SENZA codice (Aggiunta B)
- L'insieme **LLM Wiki + RAG** ha valore **anche per progetti che non contengono codice** (knowledge base
  pure, ricerca, documentazione, raccolte di fonti). Il **codice è UNA delle fonti-input** (D-3), **non un
  prerequisito**.
- Per i progetti senza codice manca la "verità sul comportamento" (codice/test) di D-4, ma restano:
  `manual_edited/`, `ingested_sources/`, log discussioni, e il **wiki compilato interrogabile**.
- Implicazione di scope: il prodotto *shall not* assumere la presenza di codice (vedi §1, da rivisitare;
  il git-prerequisito di D-5 resta, il "codice come fonte" è opzionale).

### D-10 — Questo documento è l'autorità e2e (consolidante); FEAT-003 assorbito come storico (chiude T0)
- Questo requisito è il **nuovo riferimento canonico** dell'LLM Wiki e2e.
- **Assorbe** da FEAT-003 (invariati): struttura/convenzioni (REQ-001..006), record (REQ-010..013),
  distill (REQ-030..033), idempotenza (REQ-050/051).
- **Override esplicito** su: ingest/`sources/` (→ D-6/D-11) e indicizzazione (→ D-3/D-5/D-7).
- **Espande** lo scope oltre l'MVP di FEAT-003: manutenzione (T5), superficie nativa (T6), refresh
  incrementale (D-5), orchestrazione agentica (D-2/D-8), no-code (D-9).
- FEAT-003 (`wiki-creazione`) resta come **storico**; `llm-wiki` è **la** feature wiki di riferimento.

### D-11 — Funzionalità di "ingest": importa documentazione esterna in `ingested_sources/`
- Esiste una funzionalità di **ingest** che **importa documentazione esterna** in `ingested_sources/`
  (l'area di input non versionata, D-6).
- **Quando**: alla **creazione del wiki** (popolazione iniziale), **on-demand** (importare nuova
  documentazione), e a seguito di **update** di doc esterni da riflettere in `ingested_sources/`.
- **Import ≠ compile**: l'ingest popola l'**input** (`ingested_sources/`); la **compilazione** in
  pagine-concetto avviene nella **generazione** (momento a, D-3). *(Override di FEAT-003 REQ-020, dove
  `ingest` scriveva un riassunto in `sources/`.)*

### D-12 — Superfici di invocazione: skill (primaria) + CLI + MCP per le operazioni on-demand
- Le operazioni **non-automatiche** (ingest on-demand, query, rigenerazione, manutenzione, setup) sono
  esposte su **tutte e tre** le superfici:
  - **Skill** del client LLM (Claude Code/Copilot/Codex) — **primaria** (D-8: il prodotto è uno strumento
    di un client LLM);
  - **CLI** (`sertor …`) — per umano/script;
  - **MCP** — per uso cross-client da un agente esterno.
- La superficie **automatica** (generazione al commit) resta quella di D-8 (skill invocata dal binding del
  configuration-manager).

### D-13 — Query via RAG; navigazione umana via Obsidian/editor; nessuna superficie nativa (chiude T6)
- L'**interrogazione** del wiki avviene tramite il **RAG esistente** (`sertor search` + MCP `search_*`),
  che restituisce wiki generato + codice (D-7).
- Il wiki, essendo `.md` interconnessi, resta **consultabile direttamente** con **Obsidian o altri
  editor** (navigazione umana, graph view, backlink) — gratis, come nel pattern Karpathy.
- **Nessuna superficie wiki-nativa dedicata** in scope (es. query "cosa abbiamo deciso su X" a pagina
  intera); eventuali skill aggiuntive sono **opzionali/future**.
- → chiude **T6**.

### D-14 — Manutenzione in scope: lint strutturale + verifica di freschezza; trigger incrementale/on-demand/periodico
- **In scope** due controlli:
  - **Lint strutturale**: link rotti, pagine orfane, copertura/cross-reference mancanti, contraddizioni.
  - **Verifica di freschezza** (FR-017): pagina obsoleta vs codice/test (comportamento) **o** vs decisione.
- **Trigger (stesso modello per entrambi)**:
  - **Al commit — incrementale**: insieme alla generazione (D-5/D-8), limitato alle **pagine collegate
    alle entità modificate dal commit** (changeset).
  - **On-demand — full**: su **tutto il wiki**.
  - **Periodico — full**: su tutto il wiki, schedulato.
- **Gate al commit**: blocca, avvisa e propone soluzioni (incluso "ignora e committa") — vedi **D-17**.

### D-15 — distill-da-artifact = modalità mirata della generazione (no operazione separata)
- Gli artefatti del progetto (spec SpecKit, `plan`, ADR/decision record, `requirements`, design doc) sono
  **già fonti-input** della generazione (D-3): la generazione li **compila** in concetti.
- **Non** esiste un'operazione "distill-da-artifact" separata; al più una **modalità mirata** della
  generazione (rigenera limitandoti a un artefatto), esposta come operazione on-demand (D-12). Chiude T5-Q3.

### D-16 — Comando/skill di setup (`sertor wiki init`)
- Esiste un comando/skill di **setup** (es. `sertor wiki init`), eseguito **una volta per repo**, che:
  ① crea la struttura wiki (`create_wiki`); ② installa il **binding del trigger** al commit (D-8/FR-028)
  — per Claude Code: configuration-manager / hook; ③ esegue un **ingest iniziale** di `ingested_sources/`
  (D-11) se fornito. *(Default adottato; correggibile.)*

### D-17 — Gate al commit: blocca, avvisa, propone soluzioni (incl. "ignora e committa")
- Al commit, se lint/freschezza (D-14) rilevano problemi **sopra soglia configurabile**, il gate
  **blocca** il commit, **avvisa** l'utente coi problemi rilevati e **propone una o più soluzioni**
  (rimedi: correggi link, aggiorna pagina obsoleta, rigenera…); tra le opzioni c'è **sempre "ignora e
  committa lo stesso"** (override esplicito, **tracciato**).
- È **human-in-the-loop** (coerente con D-4): l'utente decide; **nessun auto-fix silenzioso** né blocco
  senza via d'uscita.

---

## 5. Requisiti funzionali (EARS)

> Bozza (iterazione 1). Notazione EARS; `[NC]` = NEEDS CLARIFICATION da chiudere in iterazioni successive.

### 5.1 — Popolamento e manutenzione agentici (deriva da D-2, pattern Karpathy §2)

- **FR-001 (Ubiquitous)** — Il sistema *shall* popolare e mantenere il wiki tramite un **layer agentico**
  (skill + hook) che esegue il bookkeeping del pattern Karpathy (pagine, `index.md`, `log.md`,
  cross-reference), riducendo l'editing manuale a eccezione confinata in `manual_edited/`.
- **FR-002 (Optional — riuso DRY)** — Le skill/hook *may* costruire sulle operazioni di FEAT-003
  (`create_wiki`/`record`/`ingest`/`distill`/`index_wiki`); **dove** si appoggiano a una capacità già
  coperta, *should* **riusarla** anziché reimplementarla (DRY, Principio III).
- **FR-003 (Event-driven — ingest/record)** — *When* viene segnalata una nuova fonte o un'attività/
  decisione rilevante, il sistema *shall* eseguire ingest/record secondo Karpathy: leggere la fonte,
  scrivere/aggiornare la pagina tematica, **aggiornare le pagine collegate** (potenzialmente più pagine),
  aggiornare `index.md`, appendere **una** voce a `log.md`.
- **FR-004 (Event-driven — distillazione di sessione)** — *When* una sessione/attività si conclude, il
  sistema *shall* distillare il lavoro svolto (decisioni/concetti/esiti) in pagine wiki conformi e
  registrarlo nel log. `[NC: trigger esatto — hook Stop/SessionEnd, comando /wiki, o entrambi?]`
- **FR-005 (Event-driven — query→file-back)** — *When* una query/esplorazione produce conoscenza
  riutilizzabile, il sistema *shall* poterla **archiviare nel wiki come nuova pagina** (no dispersione in
  chat), aggiornando indice e log.
- **FR-006 (Optional — lint periodico)** — *Where* abilitato, il sistema *shall* eseguire un **lint** del
  wiki (contraddizioni, pagine orfane, claim superate, cross-reference/copertura mancanti) e segnalarne
  gli esiti. `[NC: cadenza/trigger del lint — vedi T5]`
- **FR-007 (Unwanted — protezione manual_edited)** — *If* una pagina è in `manual_edited/`, then il layer
  agentico *shall* **non** modificarla né cancellarla, leggendola solo come fonte (D-1).

### 5.2 — Generazione (a) e indicizzazione/retrieval (b) (deriva da D-3)

- **FR-008 (Ubiquitous — formato generazione)** — La generazione del wiki *shall* produrre contenuto in
  **linguaggio naturale** a **concetti linkati** (formato wiki), aggiornabile **incrementalmente**.
- **FR-009 (Ubiquitous — fonti-input configurabili)** — L'insieme delle **fonti-input** della generazione
  *shall* essere **configurabile** e **modificabile** durante il ciclo di vita del progetto; **set
  iniziale**: log discussioni, `manual_edited/`, sorgenti, test, SpecKit (`specs/`).
- **FR-010 (Ubiquitous — collezioni separate, query congiunta)** — Il wiki *shall* essere indicizzato in
  una **collezione separata** dai sorgenti e *shall* essere **interrogabile insieme** ad essi (join a
  query-time), con **peso paritario** (FEAT-003 FR-009) nel momento (b).
- **FR-011 (Ubiquitous — refresh indipendente)** — Ogni collezione (wiki, sorgenti) *shall* essere
  **rigenerabile indipendentemente**: il rebuild di una *shall not* intaccare l'altra.

### 5.3 — Verità, autorità e obsolescenza (deriva da D-4)

- **FR-012 (Ubiquitous — verità stratificata)** — Il sistema *shall* trattare **codice+test** come
  autorità sul *comportamento* e **discussioni/SpecKit/`manual_edited`** come autorità sul *perché*;
  non esiste un'unica source of truth.
- **FR-013 (Ubiquitous — gerarchia di default)** — In caso di conflitto, il sistema *shall* applicare la
  gerarchia di default (comportamento → codice/test; perché → decisione registrata).
- **FR-014 (Optional — gerarchia configurabile)** — *Where* configurata, il sistema *should* applicare
  una **gerarchia di autorità esplicita** in luogo del default.
- **FR-015 (Event-driven — conflitto su manual_edited)** — *When* viene rilevata un'incongruenza che
  coinvolge `manual_edited/`, il sistema *shall* **segnalarla e chiedere all'utente** come procedere,
  senza modificare né scartare autonomamente la fonte.
- **FR-016 (Ubiquitous — manual_edited compilato)** — Il contenuto di `manual_edited/` *shall* essere
  **compilato** in pagine wiki derivate (sintesi/integrazione) ed **eventualmente linkato** alla fonte;
  il **file sorgente in `manual_edited/` resta immutato** (D-1).
- **FR-017 (Ubiquitous — obsolescenza)** — Una pagina wiki *shall* essere considerata **obsoleta** se
  contraddice **il codice/test** (comportamento) **oppure** una **decisione registrata**
  (SpecKit/`manual_edited`).

### 5.4 — Fonti-input, trigger e versionamento (deriva da D-5/D-6)

- **FR-018 (Event-driven — refresh al commit)** — *When* avviene un commit, il sistema *shall*
  aggiornare il wiki elaborando il **changeset dall'ultimo commit** (fonti versionate). *(Trigger
  principale.)*
- **FR-019 (Ubiquitous — git prerequisito + watermark)** — Il sistema *shall* richiedere **git** come
  prerequisito; lo stato **"ultimo commit elaborato"** funge da watermark per l'incrementale.
- **FR-020 (Ubiquitous — ingested_sources come input)** — La cartella **`ingested_sources/`** *shall*
  essere il punto d'ingresso per sorgenti **non versionabili**, usate dal wiki come **input** per
  generare/arricchire i concetti (non è un output di pagine-riassunto).
- **FR-021 (Event-driven — trigger manuale)** — *When* l'utente lo richiede (creazione o aggiornamento),
  il sistema *shall* (ri)elaborare `ingested_sources/` come input.
- **FR-022 (Unwanted — binari non leggibili)** — *If* un file in `manual_edited/` o `ingested_sources/`
  è un **binario non leggibile**, then il sistema *shall not* ingerirlo.

### 5.5 — Perimetro del retrieval (deriva da D-7)

- **FR-023 (Ubiquitous — scope del RAG)** — Il RAG (momento b) *shall* indicizzare **solo** il **wiki
  generato** e il **codice** (collezioni separate, query congiunta); `manual_edited/` e
  `ingested_sources/` *shall not* essere indicizzate.
- **FR-024 (Ubiquitous — riferimenti non indicizzati)** — Le pagine del wiki generato *may* contenere
  riferimenti/link alle fonti di input; tali riferimenti *shall not* essere indicizzati né inseriti nel
  RAG.

### 5.6 — Esecuzione: skill, trigger, setup, no-code (deriva da D-8/D-9)

- **FR-025 (Ubiquitous — skill separata)** — La generazione/manutenzione del wiki *shall* essere una
  **skill distinta** dal componente di versioning; quest'ultimo *shall* limitarsi a **invocarla**.
- **FR-026 (Event-driven — invocazione sincrona al commit)** — *When* il configuration-manager (o
  equivalente) sta per committare, il sistema *shall* invocare la skill di generazione e **includerne gli
  output nello stesso commit**; *if* la sincrona non è praticabile, then *shall* ripiegare su un **commit
  di follow-up**.
- **FR-027 (Ubiquitous — contratto di trigger portabile)** — Il trigger *shall* essere definito da un
  **contratto client-agnostico** ("al commit, col changeset"); il configuration-manager ne è un *binding*.
- **FR-028 (Ubiquitous — setup rilascia il binding)** — Il **setup del prodotto** *shall* installare anche
  il **binding del trigger** (per Claude Code: configuration-manager / hook di commit), così che il
  trigger non si perda.
- **FR-029 (Ubiquitous — niente assunzione di codice)** — Il sistema *shall not* assumere la presenza di
  **codice sorgente**: il codice è una fonte-input **opzionale**; LLM Wiki + RAG *shall* funzionare anche
  per progetti **senza codice**.

### 5.7 — Ingest: import in ingested_sources (deriva da D-11)

- **FR-030 (Event-driven — ingest popola ingested_sources)** — *When* la funzionalità di **ingest** è
  invocata — alla **creazione** del wiki, **on-demand** (importare nuova documentazione), o a seguito di
  **update** di doc esterni — il sistema *shall* (ri)popolare `ingested_sources/` con la documentazione
  esterna importata.
- **FR-031 (Ubiquitous — import ≠ compile)** — L'ingest (import in `ingested_sources/`) *shall* essere
  **distinto** dalla **compilazione** in pagine-concetto (generazione, momento a): l'ingest fornisce
  l'**input**, la generazione lo **compila**.

### 5.8 — Superfici di invocazione (deriva da D-12)

- **FR-032 (Ubiquitous — tre superfici)** — Le operazioni on-demand del wiki (ingest, query,
  rigenerazione, manutenzione, setup) *shall* essere esposte via **skill** del client LLM (primaria),
  **CLI** e **MCP**.

### 5.9 — Interrogazione e navigazione (deriva da D-13)

- **FR-033 (Ubiquitous — query via RAG)** — L'interrogazione del wiki *shall* avvenire tramite il **RAG**
  (search esistente); **non** è prevista una superficie di query wiki-nativa dedicata in scope.
- **FR-034 (Ubiquitous — formato aperto navigabile)** — Il wiki *shall* restare **Markdown interconnesso**
  (wikilink), così da essere navigabile con strumenti esterni (Obsidian/editor) senza una UI dedicata.

### 5.10 — Manutenzione: lint + freschezza (deriva da D-14)

- **FR-035 (Ubiquitous — lint strutturale)** — Il sistema *shall* fornire un **lint strutturale** del
  wiki (link rotti, pagine orfane, copertura/cross-reference mancanti, contraddizioni).
- **FR-036 (Ubiquitous — verifica di freschezza)** — Il sistema *shall* fornire la **verifica di
  freschezza** delle pagine (obsolescenza, FR-017).
- **FR-037 (Event-driven — incrementale al commit)** — *When* avviene un commit, il sistema *shall*
  eseguire lint + freschezza in modo **incrementale**, sulle **pagine collegate alle entità del
  changeset** (insieme alla generazione).
- **FR-038 (Event-driven — full on-demand/periodico)** — *When* richiesto **on-demand** o secondo una
  **schedulazione periodica**, il sistema *shall* eseguire lint + freschezza su **tutto il wiki**.

### 5.11 — Distillazione artefatti e setup (deriva da D-15/D-16)

- **FR-039 (Ubiquitous — distill come modalità di generazione)** — Il sistema *shall not* prevedere
  un'operazione "distill-da-artifact" separata: gli artefatti sono **fonti-input** della generazione
  (D-3), che li compila; è ammessa una **modalità mirata** on-demand (rigenera da un singolo artefatto).
- **FR-040 (Event-driven — setup per repo)** — *When* si inizializza il wiki su un repo
  (`sertor wiki init` o equivalente), il sistema *shall* creare la struttura, **installare il binding del
  trigger** al commit, ed eseguire un **ingest iniziale opzionale**.

### 5.12 — Gate al commit (deriva da D-17)

- **FR-041 (Event-driven — gate bloccante)** — *When* lint/freschezza al commit rilevano problemi sopra
  soglia, il sistema *shall* **bloccare** il commit, **avvisare** l'utente e **proporre una o più
  soluzioni**.
- **FR-042 (Optional — override tracciato)** — *Where* l'utente sceglie **"ignora e committa"**, il
  sistema *shall* procedere col commit **registrando l'override** in modo tracciabile.

## 6. Criteri di successo (misurabili)

- **SC-001** Su un repo inizializzato, un commit che tocca N file produce un aggiornamento del wiki
  **limitato alle pagine collegate alle entità del changeset** (non un full rebuild). (D-5/FR-018/FR-037)
- **SC-002** Le cartelle di input (`manual_edited/`, `ingested_sources/`) **non compaiono mai nel RAG**:
  una query non restituisce quei file, ma i **concetti compilati** che ne derivano. (D-7/FR-023)
- **SC-003** Una query di retrieval restituisce risultati dal **wiki generato** e dal **codice**
  (collezioni separate interrogate insieme). (D-3/D-7/FR-010)
- **SC-004** Al commit, se lint/freschezza rilevano problemi sopra soglia, l'operazione è **bloccata**,
  l'utente è **avvisato** e riceve **≥1 soluzione** tra cui "ignora e committa"; con l'override il commit
  procede e l'override è **registrato**. (D-17/FR-041/FR-042)
- **SC-005** Il prodotto funziona su un progetto **senza codice**: generazione, retrieval e manutenzione
  operano con le sole fonti documentali. (D-9/FR-029)
- **SC-006** Rieseguendo un'operazione strutturale su input invariato, l'esito è **identico** (idempotenza:
  nessun duplicato di pagina/voce log; id chunk = path relativo). (assorbe FEAT-003 REQ-050/051)
- **SC-007** La stessa operazione è invocabile e raggiungibile da **skill, CLI e MCP**. (D-12/FR-032)
- **SC-008** Dopo `sertor wiki init`, un commit **innesca effettivamente** la generazione (binding del
  trigger installato). (D-16/FR-028/FR-040)
- **SC-009** Una pagina che afferma un comportamento **contraddetto dal codice/test**, o una **decisione**
  contraddetta, è segnalata come **obsoleta**. (D-4/FR-017/FR-036)
- **SC-010** L'ingest popola `ingested_sources/` alla creazione, on-demand e su update, **senza** scrivere
  pagine-riassunto (separazione import/compile). (D-11/FR-030/FR-031)

## 7. Ambito e confini

### In ambito
- Generazione/manutenzione **agentica** del wiki (skill che riusa FEAT-003), invocata **al commit**
  (incrementale sul changeset), **on-demand** e **periodica**.
- **Ingest** di documentazione esterna in `ingested_sources/` (creazione/on-demand/update).
- **Manutenzione**: lint strutturale (link rotti, orfani, copertura/cross-ref) + verifica di freschezza.
- **Gate al commit** human-in-the-loop (blocca/avvisa/propone/override tracciato).
- **Retrieval** via RAG su **collezioni separate** wiki/codice (query congiunta); input non indicizzati.
- **Superfici**: skill (primaria) + CLI + MCP; comando di **setup** `sertor wiki init`.
- Convenzione **`manual_edited`** (input umano versionato, immutabile, compilato).
- Funzionamento anche su **progetti senza codice**.

### Fuori ambito
- **Superficie wiki-nativa dedicata** (query a pagina intera, navigazione UI): si usa RAG + Obsidian/editor
  (D-13).
- **Arricchimento bidirezionale Wiki↔RAG** (loop wiki→query→wiki): futura **FEAT-008**.
- **Re-index FULL del corpus** da zero: capacità del nucleo/CLI; qui si usa l'incrementale.
- **GUI/interfaccia web** del wiki.
- **Traduzione automatica** dei contenuti.
- **Chunking di trascrizioni grezze**: la distillazione riceve input già condensato (assorbito da FEAT-003).

---

## 8. Assunzioni
- **Git è prerequisito** (D-5): versioning e trigger al commit richiedono un repo git.
- Le fonti versionate vivono nel repo; `ingested_sources/` è gestita a mano (non versionata).
- Il wiki è **Markdown interconnesso** (wikilink), navigabile da editor esterni (FR-034).
- `manual_edited/` contiene **solo contenuti leggibili** (no binari, FR-022).
- È presente un **client LLM** (Claude Code/Copilot/Codex) con un **binding del trigger** installato dal
  setup (D-8/D-16).
- Provider LLM configurato per generazione e verifica di freschezza; le operazioni strutturali (struttura,
  ingest-import) sono **LLM-free**.

## 9. Dipendenze
- **FEAT-001** (nucleo retrieval condiviso) per l'indicizzazione (collezioni, embeddings, vector store).
- **Provider LLM** per generazione e verifica di freschezza.
- **configuration-manager** (o equivalente del client) come **binding del trigger** al commit.
- **Refresh incrementale dell'indice** (capacità tipo FEAT-009) come abilitatore della
  generazione/manutenzione incrementale al commit; in assenza, fallback (rigenerazione più ampia).
- **FEAT-003** assorbito come substrato (struttura/record/distill/idempotenza).

## 10. Rischi
| ID | Rischio | Prob | Impatto | Mitigazione |
|----|---------|------|---------|-------------|
| R-01 | Rumore del giudizio LLM nella verifica di freschezza (falsi positivi) | Media | Medio | Gate **human-in-the-loop** (D-17) + verità **stratificata** (D-4); soglia configurabile |
| R-02 | Costo/latenza della generazione **sincrona** al commit | Media | Medio | **Incrementale** sul solo changeset (D-5); fallback **asincrono** (D-8/FR-026) |
| R-03 | Il **trigger si perde** se il setup non installa il binding | Media | Alto | Il setup **installa** il binding (D-16/FR-028/FR-040) e lo verifica |
| R-04 | Generazione su **progetti grandi** lenta | Bassa | Medio | Incrementale di default; full solo on-demand/periodico; scalabilità lineare |
| R-05 | Divergenza tra le **tre superfici** (skill/CLI/MCP) | Bassa | Medio | Superfici = **binding** sullo stesso core/contratto (D-8/D-12) |
| R-06 | Conflitti su `manual_edited` risolti male | Bassa | Alto | **Human-in-the-loop** obbligatorio (D-4/FR-015); l'LLM non modifica la fonte |

## 11. Prioritizzazione (MoSCoW)
| Gruppo di requisiti | MoSCoW | Motivazione |
|---------------------|--------|-------------|
| Generazione al commit (D-2/D-3/D-5/D-8) + collezioni separate + retrieval (D-7) + idempotenza + setup (D-16) | **Must** | Cuore e2e: senza, non c'è LLM Wiki vivo né "una sola verità interrogabile" |
| Convenzione input (`manual_edited` D-1 / `ingested_sources` D-6) + ingest (D-11) | **Must** | Definiscono cosa alimenta la generazione |
| Superfici skill+CLI+MCP (D-12) | **Should** | La skill@commit basta per il flusso primario; CLI/MCP ampliano l'uso |
| Manutenzione (lint + freschezza D-14) + gate al commit (D-17) | **Should** | Alza la qualità; il valore base esiste anche senza |
| Trigger **periodico** (D-14) | **Could** | Utile ma non essenziale rispetto a commit + on-demand |
| **No-code-first** (D-9) | **Could** | Generalizza il prodotto; non blocca il caso con codice |
| Gerarchia di autorità **configurabile** (D-4/FR-014) | **Could** | Il default copre la maggior parte dei casi |

---

## 12. Domande aperte (per iterazione)

Organizzate per tema; le affrontiamo un blocco per volta.

- **T0 — Confine del documento**: ✅ **risolto** (D-10) — **consolidante**: autorità e2e; assorbe
  FEAT-003 (struttura/record/distill/idempotenza), override su ingest/sources e indexing, espande lo
  scope; FEAT-003 = storico, `llm-wiki` = feature canonica.
- **T1 — Attori e modello di invocazione e2e**: ✅ **risolto** — è **prodotto (i)**, strumento di un
  **client LLM** (Claude Code/Copilot/Codex), realizzato come **skill client-agnostica invocata al
  commit** dal configuration-manager / equivalente (D-8); il setup ne rilascia il binding del trigger.
- **T2 — Unificazione dei due layer**: ✅ **risolta da D-2** — il layer agentico orchestra e **riusa
  FEAT-003** come libreria; manuale solo in `manual_edited/`.
- **T3 — Superfici di invocazione**: ✅ **risolto** (D-12) — operazioni on-demand su **skill (primaria) +
  CLI + MCP**; generazione automatica via skill@commit (D-8). *(Residui minori: dettaglio query → T6;
  comando di setup → Q3 in corso.)*
- **T4 — Indicizzazione**: ✅ **risolta da D-3** — **collezioni separate** interrogate insieme; ogni
  corpus si rigenera indipendentemente (niente rebuild distruttivo). *(Resta da vedere: refresh
  incrementale di ciascun corpus → sinergia FEAT-009.)*
- **T5 — Manutenzione**: ✅ **risolto** (D-14/D-15) — lint strutturale + verifica di freschezza **in
  scope** (trigger incrementale@commit/on-demand/periodico); distill-da-artifact **sussunto** dalla
  generazione; **gate al commit** = blocca/avvisa/propone soluzioni incl. override (D-17).
- **T3-Q3 — Setup**: ✅ **risolto** (D-16) — comando/skill `sertor wiki init` (struttura + binding trigger
  + ingest iniziale), una volta per repo.
- **T6 — Superficie wiki-nativa**: ✅ **risolto** (D-13) — **fuori scope**: query via RAG, navigazione
  umana via Obsidian/editor (Markdown aperto); skill aggiuntive opzionali/future.
- **T7 — manual_edited / ingested_sources**: ✅ **risolto** da D-4/D-5/D-6/**D-7** (compilato + immutabile
  + human-in-the-loop; refresh al commit; `ingested_sources/` input manuale; **input NON indicizzati** nel
  RAG — solo wiki generato + codice).

---

## Changelog iterazioni
- **Iter 0 (2026-06-04)**: scheletro creato; D-1 (convenzione `manual_edited`) registrata; temi T0–T7 aperti.
- **Iter 0.1 (2026-06-04)**: aggiunto §2 *Modello di riferimento — l'LLM Wiki di Karpathy* (fonte primaria:
  gist Karpathy) con caratteristiche, operazioni, principi e mappatura allineamenti/divergenze su Sertor.
- **Iter 1 (2026-06-04)**: D-2 (popolamento agentico via skill+hook che riusano FEAT-003) → risolve T2;
  primo blocco EARS §5.1 (FR-001..007); T1 raffinato.
- **Iter 2 (2026-06-04)**: Punto 1 chiuso → D-3 (due momenti: generazione Karpathy da fonti-input
  configurabili · retrieval con collezioni separate interrogate insieme, peso paritario solo in (b));
  EARS §5.2 (FR-008..011); T4 risolta; §2 raffinato; status → iter 2.
- **Iter 3 (2026-06-04)**: Punto 2 chiuso → D-4 (verità stratificata; gerarchia default + configurabile;
  human-in-the-loop sui conflitti manual_edited; manual_edited compilato; definizione obsolescenza);
  EARS §5.3 (FR-012..017); D-1/§2/T5/T7 raffinati.
- **Iter 4 (2026-06-04)**: Punto 3 (quasi chiuso) → D-5 (refresh git-driven al commit + git prerequisito)
  e D-6 (rinomina `sources/`→`ingested_sources/`, input non versionato a trigger manuale; modello a due
  classi input/generato; impatto su FEAT-003 `ingest`); EARS §5.4 (FR-018..022); D-1/D-3/T7 aggiornati.
  Residuo Punto 3: Q4b (interrogabilità delle cartelle di input nel retrieval).
- **Iter 5 (2026-06-04)**: Punto 3 chiuso → D-7 (retrieval "puro Karpathy": RAG indicizza solo wiki
  generato + codice; input non indicizzati; riferimenti non indicizzati); fix D-1 (override); EARS §5.5
  (FR-023/024); T7 risolto.
- **Iter 6 (2026-06-04)**: Punto 4 chiuso → D-8 (skill client-agnostica invocata al commit dal
  config-manager; sincrona; contratto di trigger portabile; setup rilascia il binding) e D-9 (LLM Wiki +
  RAG asset anche senza codice); EARS §5.6 (FR-025..029); §1/§2/T1 aggiornati. **T1 risolto.**
- **Cleanup (2026-06-04)**: rimosse TUTTE le tracce del branch morto FEAT-007 (header, FR-006, T0, T5, §2)
  — funzionalità ridefinite ex-novo; FR-002 ammorbidito (may/should, DRY); §2 "operazioni" riclassificate
  ◐ (esistono ma non orchestrate).
- **Iter 7 (2026-06-04)**: T0 chiuso → D-10 (consolidante: autorità e2e, assorbe FEAT-003, override su
  ingest/indexing, espande scope; FEAT-003 storico) e D-11 (ingest ridefinita: importa in
  `ingested_sources/` alla creazione/on-demand/update; import≠compile); EARS §5.7 (FR-030/031); header/T0
  aggiornati.
- **Iter 8 (2026-06-04)**: T3 (Q1) → D-12 (operazioni on-demand su skill+CLI+MCP); EARS §5.8 (FR-032).
  Residui T3: Q2 (query → T6), Q3 (comando di setup).
- **Iter 9 (2026-06-04)**: T6 chiuso → D-13 (query via RAG; navigazione Obsidian/editor; nessuna superficie
  nativa); EARS §5.9 (FR-033/034). Resta solo T3-Q3 (comando di setup) e T5 (manutenzione).
- **Iter 10 (2026-06-04)**: T5 (Q1/Q2) → D-14 (lint strutturale + verifica di freschezza in scope; trigger
  incrementale@commit/on-demand/periodico); EARS §5.10 (FR-035..038). Residui: T5-Q3 (distill-da-artifact),
  T3-Q3 (setup), gating `[NC]`.
- **Iter 11 (2026-06-04)**: T5 e T3-Q3 chiusi → D-15 (distill-da-artifact sussunto dalla generazione) e
  D-16 (comando di setup `sertor wiki init`); EARS §5.11 (FR-039/040). **Tutti i temi T0–T7 risolti**;
  unico residuo: gating bloccante al commit `[NC]`.
- **Iter 12 (2026-06-04)**: ultimo `[NC]` chiuso → D-17 (gate al commit: blocca/avvisa/propone soluzioni
  incl. "ignora e committa", override tracciato, human-in-the-loop); EARS §5.12 (FR-041/042).
  **Tutte le decisioni prese; nessun residuo aperto.** Pronto per formalizzazione `/requirements`.
- **Iter 13 (2026-06-04)**: formalizzazione `/requirements` — completati §6 Criteri di successo
  (SC-001..010), §7 Ambito (in/fuori scope), §8 Assunzioni, §9 Dipendenze, §10 Rischi (R-01..06),
  §11 MoSCoW; status → **READY** (approvato per il design). Decisioni ed EARS preservati invariati.
