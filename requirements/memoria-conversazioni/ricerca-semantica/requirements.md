# Requisiti — Ricerca semantica opzionale sull'archivio
<!-- Deriva da: FEAT-004 (epica: memoria-conversazioni) -->

## 1. Contesto e problema (perché)

L'MVP della memoria conversazioni è completo e distribuibile: FEAT-001 cattura e archivia le
conversazioni in un archivio locale (`<index_dir>/memory.sqlite`, contenuto già **scrubbed**),
FEAT-002 le rende interrogabili **full-text** (FTS5/BM25 lessicale, parola/frase esatta), FEAT-035 ne
espone la superficie CLI + hook `SessionEnd`, FEAT-003 le aggancia alla distillazione del wiki.

La ricerca full-text ha un limite intrinseco: trova solo ciò che **combacia per parola**. Una domanda
episodica come «com'era finita la discussione sull'astensione del retrieval quando il punteggio è
basso?» non trova nulla se in quella sessione si parlava di «confidence», «soglia», «min-score» —
sinonimi e parafrasi che il match lessicale non collega. Questa è esattamente la lacuna che la
**ricerca per significato** (semantica) colma: recupera la conversazione pertinente *per concetto*,
non per stringa.

La feature **non costruisce un nuovo motore**: riusa l'ingestione/embeddings/store del nucleo RAG
(`sertor-core`) trattando l'archivio episodico come un **corpus/tier dedicato** (Principio I/III — il
prodotto è la libreria di retrieval, non un secondo motore). È perciò una capacità *additiva* sopra
una pipeline già provata.

Il prezzo è la **privacy**: embeddare il contenuto significa darlo in pasto a un provider di
embeddings — che, se cloud, lo manda fuori dalla macchina. Per questo l'epica (REQ-M-E2) impone che
la ricerca semantica sia un **opt-in ulteriore e separato** rispetto alla sola cattura
(`SERTOR_MEMORY`). La mitigazione è strutturale: dopo FEAT-011 il provider di embeddings di **default
è locale** (`glove`/`hash`; in alternativa Ollama), quindi con la configurazione di default il
contenuto **resta sulla macchina** anche con la semantica accesa.

La feature presuppone FEAT-001 (archivio) e convive con FEAT-002 (full-text), che **resta il default**
di ricerca: la semantica è un percorso distinto, attivato esplicitamente.

## 2. Obiettivi e criteri di successo

Criteri propri di questa feature (ereditano e specializzano CS-2/CS-4 dell'epica):

- **SS-CS-1 (recupero per significato):** data una sessione passata che discuteva un concetto, una
  query semantica che usa **parole diverse ma di significato affine** restituisce quella sessione tra
  i primi risultati, là dove la sola full-text non la troverebbe.
- **SS-CS-2 (opt-in ulteriore e separato):** con la sola cattura attiva (`SERTOR_MEMORY=true`) ma la
  semantica **non** opt-in, nessun contenuto viene embeddato e nessun indice vettoriale viene creato;
  la ricerca semantica è disponibile **solo** dopo l'opt-in esplicito dedicato.
- **SS-CS-3 (contenuto on-machine col provider locale):** con un provider di embeddings locale
  configurato (default dopo FEAT-011), l'intero percorso — indicizzazione e query — avviene **senza
  traffico di rete**; nessun frammento di transcript lascia la macchina.
- **SS-CS-4 (full-text resta il default):** abilitare la semantica **non** sostituisce né disabilita
  la ricerca full-text di FEAT-002; le due coesistono e l'utente sceglie il modo esplicitamente.
- **SS-CS-5 (riuso, non nuovo motore):** la feature non introduce un secondo motore di retrieval;
  l'indicizzazione e la query semantica passano per le capacità di embedding/store del core già usate
  dal RAG (verificabile: nessun nuovo engine; riuso delle factory/porte esistenti).
- **SS-CS-6 (host-agnostico):** indicizzazione e ricerca semantica funzionano su ≥2 ospiti diversi
  senza modifiche al corpo (Principio X, CS-5 dell'epica).
- **SS-CS-7 (freschezza):** una sessione archiviata con la semantica abilitata è recuperabile per
  significato senza un passo manuale dell'utente (l'indicizzazione semantica avviene contestualmente
  all'archiviazione — vedi §4 e la decisione di scope sul trigger).

## 3. Stakeholder e attori

- **Agente LLM (attore primario):** interroga la memoria per significato nei casi speciali, quando la
  parola esatta non basta; è produttore (le sessioni sono le sue conversazioni) e consumatore.
- **Owner/maintainer (utente):** ritrova decisioni e contesto per concetto; sceglie se accendere la
  semantica accettandone il costo/implicazioni di privacy; lancia/abilita l'indicizzazione.
- **Il sistema-wiki (consumatore indiretto):** la distillazione (FEAT-003) può localizzare la
  sessione sorgente per significato, non solo per parola.

## 4. Ambito

### In ambito
- **Indicizzazione semantica** del contenuto dell'archivio episodico: embedding dei transcript
  (riuso della pipeline di embedding/store del core), gated dall'opt-in semantico.
- **Trigger di indicizzazione = automatico a fine sessione** (decisione utente 2026-06-22):
  l'embedding di una sessione avviene **contestualmente alla sua archiviazione** (percorso
  `memory archive` / hook `SessionEnd`), così l'indice semantico è sempre fresco senza un passo
  manuale; il tutto **solo** quando la semantica è opt-in.
- **Ricerca semantica** (query in linguaggio naturale → sessioni/turni pertinenti per significato),
  con citazione (sessione, turno, timestamp, snippet) e ordinamento per similarità.
- **Modo separato opt-in** (decisione utente 2026-06-22): la full-text di FEAT-002 resta il default;
  la semantica è un percorso distinto, attivabile esplicitamente (es. un'opzione `--semantic` sulla
  ricerca, forma esatta = design).
- **Opt-in di privacy a strati:** una manopola dedicata, **distinta** da `SERTOR_MEMORY`, abilita
  l'embedding (default off).
- **Provider locale come default privacy-safe:** riuso del selettore provider del core
  (`SERTOR_EMBED_PROVIDER`, default locale dopo FEAT-011); con provider locale, contenuto on-machine.
- **Degradazione non-fatale:** semantica non opt-in / indice non costruito / provider non disponibile
  → stato vuoto esplicito + warning, mai eccezione propagata.
- **Host-agnostico** (Principio X): il corpo non assume l'assistente ospite.
- **Osservabilità minima** (pattern `log_event` del core): eventi per indicizzazione semantica e per
  query semantica, **metrics-only** (mai testo/transcript/query in chiaro).

### Fuori ambito
- **Cattura e archiviazione** (FEAT-001 — dipendenza a monte, assunta come fornita).
- **Ricerca full-text** (FEAT-002 — questa feature la affianca, non la modifica).
- **Parità MCP** dei comandi di memoria (`search`/`show`/`list` via server MCP): è **FEAT-010**,
  separata. Questa feature consegna la capacità via libreria/CLI; l'esposizione MCP è successiva.
- **Distribuzione via installer** delle nuove manopole (template `.env`, hook, doc): debito di
  completamento da promuovere a FEAT-009/installer quando la feature è pronta (vedi §10), **non**
  risolto qui.
- **Cancellazione/governance/retention** dell'indice semantico: è FEAT-006 (la retention del
  contenuto); qui si fornisce solo il gancio di coerenza con l'archivio.
- **Cattura multi-assistente** (FEAT-008) e **roll-up cross-progetto** (FEAT-007).
- **Scrub dei segreti**: il testo è già scrubbed da FEAT-001; questa feature embedda testo già redatto
  e non applica scrub aggiuntivo.
- **Scelta concreta del *come*** (corpus/`doc_type` del RAG vs store vettoriale dedicato; granularità
  turno/sessione/chunk; nome esatto della manopola e del flag; refresh incrementale dell'indice
  semantico): materia di **design** (`/speckit-plan`) — vedi §10.

## 5. Requisiti funzionali (EARS)

### 5.1 Opt-in di privacy a strati

**REQ-001 (Unwanted behaviour):** *If semantic search over the archive is not explicitly opted in,
then the system shall embed no transcript content and shall create no semantic (vector) index
(layered opt-in beyond `SERTOR_MEMORY`).*

**REQ-002 (Optional feature):** *Where semantic search is opted in, the system shall require that
conversation capture (`SERTOR_MEMORY`) is also enabled; if capture is off, then the system shall treat
semantic search as inactive (no embedding, no index) and report the dependency.*

**REQ-003 (Ubiquitous):** *The semantic opt-in shall be a configuration knob distinct from
`SERTOR_MEMORY`, defaulting to off, so that enabling capture never silently enables embedding.*

### 5.2 Indicizzazione semantica (automatica a fine sessione)

**REQ-004 (Event-driven):** *When a session is archived and semantic search is opted in, the system
shall embed that session's transcript content and add it to the semantic index, so the session is
retrievable by meaning on the next search.*

**REQ-005 (Event-driven):** *When a session is archived and semantic search is NOT opted in, the
system shall archive it (FEAT-001 behaviour) without embedding it or touching any semantic index.*

**REQ-006 (Ubiquitous):** *The semantic indexing shall be idempotent on the same session: embedding
an already-indexed session shall not create duplicate entries.*

**REQ-007 (Optional feature):** *Where semantic search is opted in on an archive that already
contains sessions captured before the opt-in, the system shall provide a way to embed the existing
(backlog) sessions into the semantic index (backfill), without requiring re-archival; the backfill is
itself incremental — it shall embed only the units not yet indexed (REQ-030).*

**REQ-008 (Unwanted behaviour):** *If embedding a session at archival time fails (provider error,
oversized content, etc.), then the system shall keep the raw archival of that session intact, log a
warning, and continue; the embedding failure shall not abort the capture/archival run.*

### 5.2.1 Incrementalità dell'indicizzazione

> L'archivio di FEAT-001 è **append-only by design** (`INSERT OR IGNORE`, nessun `DELETE`/`REPLACE`:
> lo storico è conservato e non viene mai mutato). L'incrementalità è quindi **puramente additiva** e
> più semplice del refresh incrementale di FEAT-009: non serve rilevare unità modificate o cancellate
> (non possono cambiare) — basta non ri-processare ciò che è già indicizzato.

**REQ-030 (Ubiquitous):** *The semantic indexing shall be incremental: on any indexing run it shall
embed only the memory units not already present in the semantic index, and shall never re-embed the
entire archive by default — exploiting the append-only nature of the archive (already-indexed units
cannot change).*

**REQ-031 (Ubiquitous):** *The system shall durably record which memory units have already been
embedded (a persisted marker/watermark), so that incremental indexing skips them across process
restarts and across separate indexing runs.*

**REQ-032 (Optional feature):** *Where the embeddings provider or the indexing logic changes so that
existing vectors are incompatible (e.g. a different vector dimension or a changed logic version), the
system shall rebuild the semantic index from the archive; this full rebuild shall be the ONLY
circumstance that re-embeds already-indexed content, and it shall be explicit and observable.*

### 5.3 Ricerca semantica

**REQ-009 (Ubiquitous):** *The semantic search shall accept a natural-language query and return
archived memory units (sessions/turns) ranked by semantic similarity to the query.*

**REQ-010 (Event-driven):** *When a semantic query is submitted, the system shall return, for each
result, at least: the session identifier, the matched unit reference (e.g. turn index), the session
timestamp, a text snippet, and a similarity score.*

**REQ-011 (Ubiquitous):** *The semantic search shall limit the number of returned results to a
configurable maximum (default: a finite, documented value); it shall not return the whole index
unconditionally.*

**REQ-012 (Optional feature):** *Where a time-window constraint is provided, the semantic search
shall restrict results to memory units whose session timestamp falls within the interval (parity with
the full-text time filter of FEAT-002).*

### 5.4 Modo separato dalla full-text

**REQ-013 (Ubiquitous):** *The system shall keep the FEAT-002 full-text search as the default memory
search path; enabling semantic search shall neither disable nor replace it.*

**REQ-014 (Optional feature):** *Where the user explicitly selects the semantic mode, the system shall
route the query through the semantic search; otherwise the system shall use the full-text path.*

**REQ-015 (Unwanted behaviour):** *If the semantic mode is selected but semantic search is not opted
in (or its index is absent), then the system shall return an explicit, actionable message naming the
required opt-in, and shall not silently fall back to full-text.*

### 5.5 Riuso del RAG esistente (no nuovo motore)

**REQ-016 (Ubiquitous):** *The semantic indexing and querying shall reuse the core's existing
embedding and vector-store capabilities (the same machinery used by the document/code corpus); the
feature shall not introduce a separate retrieval engine.*

**REQ-017 (Ubiquitous):** *The semantic index for the memory archive shall be isolated from the
project's document/code corpus index, so that memory content and corpus content never mix in the same
search results.*

### 5.6 Provider locale e contenuto on-machine

**REQ-018 (Ubiquitous):** *The semantic indexing and querying shall use the embeddings provider
selected by the core's existing provider knob (`SERTOR_EMBED_PROVIDER`), whose default is local
(FEAT-011).*

**REQ-019 (State-driven):** *While a local embeddings provider is configured, the system shall perform
all semantic indexing and querying without any network traffic; no transcript fragment shall leave the
machine.*

**REQ-020 (Optional feature):** *Where a cloud/remote embeddings provider is configured for semantic
search, the system shall make the resulting off-machine transmission of (already-scrubbed) content an
explicit consequence of the opt-in, surfaced to the user (e.g. documented and/or warned), not silent.*

### 5.7 Degradazione non-fatale

**REQ-021 (Unwanted behaviour):** *If the semantic index is absent (never built or deleted) when a
semantic query is submitted, then the system shall return an explicit empty result with a warning, not
an error.*

**REQ-022 (Unwanted behaviour):** *If the embeddings provider is unavailable or misconfigured at query
time, then the system shall return an explicit, actionable error/empty state and shall not crash the
caller.*

**REQ-023 (Unwanted behaviour):** *If a single archived unit is unreadable or its stored embedding is
invalid, then the system shall skip that unit, log a warning, and continue serving the remaining
results.*

### 5.8 Host-agnostico e portabilità

**REQ-024 (Ubiquitous):** *The semantic indexing and search body shall not contain any assumption
about the assistant host that captured the transcripts; it shall operate on the local archive
regardless of provenance.*

**REQ-025 (Ubiquitous):** *The semantic search shall be operable from at least two different host
environments without modifications to its implementation.*

### 5.9 Osservabilità

**REQ-026 (Event-driven):** *When a semantic indexing operation completes, the system shall emit a
structured, metrics-only log event recording at least: the number of units embedded, the provider
name, and the latency; it shall not record transcript text.*

**REQ-027 (Event-driven):** *When a semantic query completes, the system shall emit a structured,
metrics-only log event recording at least: the number of results, the time-window filters applied, and
the latency; the query text shall be recorded only as a hash or omitted, never in clear, consistent
with FEAT-002's strategy.*

**REQ-028 (Unwanted behaviour):** *If emitting an observability event fails, then the indexing/search
result shall still be produced; the observability failure shall be non-fatal.*

### 5.10 Coerenza con l'archivio

**REQ-029 (Ubiquitous):** *The semantic index shall be a derived artifact of the FEAT-001 archive;
deleting/rebuilding it shall not alter the raw archive, and rebuilding it from the archive shall yield
an equivalent index.*

## 6. Requisiti non funzionali

**NFR-001 (Privacy locale di default):** con il provider locale di default, l'intero percorso
(indicizzazione + query) è offline; verificabile con un monitor di rete in test (zero traffico).

**NFR-002 (Costo dell'indicizzazione a fine sessione):** poiché l'indicizzazione è automatica
all'archiviazione (decisione di scope), il costo di embedding per-sessione deve essere contenuto e
non degradare percettibilmente la chiusura di sessione; con provider locale è costo di sola CPU. La
documentazione deve dichiarare l'implicazione di costo (e, per provider cloud, l'implicazione di
privacy) dell'auto-indicizzazione.

**NFR-003 (Latenza di query):** una query semantica su un archivio di dimensione tipica deve
restituire risultati in tempo percettivamente immediato in contesto interattivo (indicativamente
< 2 s su hardware consumer). [DA CHIARIRE: soglia quantitativa dopo la decisione di granularità.]

**NFR-004 (Affidabilità non-fatale):** nessun guasto (indice assente/corrotto, provider giù) si
propaga come eccezione non gestita; sempre stato vuoto/warning/errore azionabile.

**NFR-005 (Additività a leva spenta):** con la semantica non opt-in (default), il comportamento e il
costo del sistema sono identici a oggi: nessun embedding, nessun file/indice nuovo, nessun import del
percorso semantico (coerente col gate `build_*` esistente che ritorna `None` a memoria spenta).

**NFR-006 (Riuso, dipendenze minimali):** preferire il riuso delle capacità di embedding/store già
nel core; nessuna nuova dipendenza di terze parti se evitabile (coerente con il local-first del core).

**NFR-007 (Testabilità offline):** la logica di indicizzazione e ricerca deve essere testabile come
componente isolato con embedder/store mock (pattern delle fixture del core), senza rete né corpus
reale.

**NFR-008 (Osservabilità strutturata):** gli eventi seguono il pattern `log_event` del core, fields
già redatti, metrics-only; nessuna nuova dipendenza di logging.

**NFR-009 (Costo di indicizzazione a regime = O(nuovo)):** grazie all'incrementalità (REQ-030/031),
il costo di embedding a regime è proporzionale alle **sole** unità nuove, non all'intero archivio; il
ri-embedding dell'intero storico avviene solo nel caso eccezionale di REQ-032 (cambio
provider/dimensione del vettore). Verificabile: una seconda indicizzazione senza nuove sessioni non
produce nuove chiamate di embedding.

## 7. Vincoli, assunzioni e dipendenze

### Vincoli (ereditati dall'epica)
- **Privacy-by-default a strati (REQ-M-E1/E2):** cattura = opt-in; embedding (semantica) = opt-in
  **ulteriore e separato**; full-text locale resta il default privacy-safe.
- **Host-agnostico (REQ-M-E3):** il corpo non assume l'host; gli adattamenti host-specifici stanno in
  FEAT-001/config.
- **Contenuto già scrubbed:** FEAT-001 ha applicato lo scrub; questa feature embedda testo già redatto.
- **Riuso del RAG (Principio I/III):** nessun secondo motore; si riusa la pipeline esistente.
- **Accesso solo via vehicles (Principio XI):** la capacità è esercitata via CLI/MCP, non importando
  `sertor_core` a runtime (eccezione: i test).

### Assunzioni documentate
- **A-001 — Archivio fornito da FEAT-001:** sessioni+turni scrubbati in `memory.sqlite`
  (`adapters/memory/archive.py`), con id sessione, timestamp, contenuto, indice di turno.
- **A-002 — Full-text fornita da FEAT-002:** `EpisodicSearch` (`services/episodic_search.py`) resta il
  percorso di default; la semantica le si affianca.
- **A-003 — Gate privacy come gli altri `build_*`:** la factory del percorso semantico ritorna `None`
  (no-op) quando la semantica non è opt-in, come `build_episodic_search`/`build_memory_archiver`
  ritornano `None` a `SERTOR_MEMORY` off (`composition.py`).
- **A-004 — Manopola dedicata:** si assume una nuova manopola booleana dedicata (nome proposto, non
  vincolante: `SERTOR_MEMORY_SEMANTIC`), default off, accanto alle manopole memoria esistenti
  (`SERTOR_MEMORY`, `SERTOR_EPISODIC_LIMIT`, `SERTOR_EPISODIC_SNIPPET_TOKENS`, `SERTOR_MEMORY_*`). Il
  nome esatto è design.
- **A-005 — Provider dal selettore esistente:** l'embedding usa `SERTOR_EMBED_PROVIDER` (default
  locale dopo FEAT-011); nessun selettore di provider nuovo solo per la memoria.
- **A-006 — Indicizzazione contestuale all'archiviazione:** coerente con la decisione di scope
  (auto a fine sessione), si assume che il percorso di archiviazione (FEAT-001/035, hook `SessionEnd`)
  sia il punto in cui scatta anche l'embedding, quando opt-in. L'archivio grezzo e l'indice semantico
  non divergono (REQ-029).

### Dipendenze
- **FEAT-001 (Must, a monte):** archivio dei transcript — sorgente dei dati da embeddare.
- **FEAT-002 (Must, affiancata):** full-text — resta il default; la semantica è il modo alternativo.
- **FEAT-011 (✅ fatto):** embedder locale di default — è ciò che rende l'auto-indicizzazione
  privacy-safe by default (contenuto on-machine senza configurazione extra).
- **Pipeline RAG del core (✅):** embedding/vector-store/factory esistenti — riusate, non riscritte.
- **FEAT-010 (a valle, separata):** parità MCP — esporrà anche la ricerca semantica via MCP.
- **Installer / FEAT-009 (a valle):** distribuzione delle nuove manopole/asset agli ospiti (debito di
  completamento, §10).

## 8. Rischi

- **R-001 — Auto-indicizzazione e privacy con provider cloud:** la decisione di scope (embedding a
  fine sessione) implica che, *se* fosse configurato un provider cloud, ogni sessione manderebbe
  contenuto (già scrubbed) fuori macchina a ogni chiusura. Mitigazione: opt-in separato esplicito +
  default provider locale (FEAT-011) + dichiarazione/segnalazione esplicita (REQ-020); documentare
  chiaramente l'implicazione.
- **R-002 — Costo dell'embedding a ogni sessione:** l'auto-indicizzazione paga l'embedding a ogni
  archiviazione. Mitigazione: con provider locale è solo CPU; NFR-002 impone di contenere e
  documentare il costo; idempotenza (REQ-006) evita ri-embedding.
- **R-003 — Staleness/divergenza indice↔archivio:** se l'embedding a fine sessione fallisce in
  silenzio, la sessione esiste nel grezzo ma non nella semantica. Mitigazione: REQ-008 (warning,
  non-fatale) + REQ-029 (indice ricostruibile dal grezzo) + REQ-007 (backfill).
- **R-004 — Qualità del recupero col provider locale:** gli embedding locali (`glove`/`hash`) hanno
  qualità semantica inferiore ai modelli cloud; il recupero per significato potrebbe essere debole.
  Mitigazione: la qualità è misurabile (l'epica retrieval-qualita/eval esiste); documentare il
  trade-off qualità↔privacy e lasciare all'utente la scelta del provider.
- **R-005 — Contaminazione col corpus principale:** se l'indice semantico della memoria non è isolato,
  i transcript potrebbero inquinare i risultati del RAG di codice/doc. Mitigazione: REQ-017
  (isolamento esplicito, collezioni separate).
- **R-006 — Crescita dell'indice:** l'indice vettoriale cresce con l'archivio. Mitigazione: la
  retention è FEAT-006; qui REQ-029 garantisce ricostruibilità.

## 9. Prioritizzazione (MoSCoW) interna

| ID | Requisito / gruppo | Priorità |
|----|-------------------|----------|
| REQ-001..003 | Opt-in di privacy a strati (distinto da `SERTOR_MEMORY`) | **Must** |
| REQ-004..006, REQ-008 | Indicizzazione automatica a fine sessione, idempotente, non-fatale | **Must** |
| REQ-030..031 | Incrementalità: embedda solo il nuovo + marker durevole di «già indicizzato» | **Must** |
| REQ-032 | Rebuild totale solo su cambio provider/dimensione vettore (esplicito) | **Should** |
| REQ-009..011 | Ricerca semantica di base (query, risultati, citazione, limite) | **Must** |
| REQ-013..015 | Modo separato opt-in; full-text resta default; no fallback silenzioso | **Must** |
| REQ-016..017 | Riuso del RAG, indice isolato dal corpus | **Must** |
| REQ-018..019 | Provider dal selettore esistente; on-machine col locale | **Must** |
| REQ-021..023 | Degradazione non-fatale | **Must** |
| REQ-024..025 | Host-agnostico | **Must** |
| REQ-026..028 | Osservabilità metrics-only non-fatale | **Must** |
| REQ-029 | Coerenza/ricostruibilità indice↔archivio | **Must** |
| REQ-012 | Filtro temporale sulla semantica (parità FEAT-002) | **Should** |
| REQ-007 | Backfill delle sessioni pre-opt-in | **Should** |
| REQ-020 | Segnalazione esplicita dell'invio off-machine con provider cloud | **Should** |
| NFR-001, NFR-004..008 | Privacy locale, affidabilità, additività, riuso, testabilità, osservabilità | **Must** |
| NFR-009 | Costo a regime = O(nuovo) grazie all'incrementalità | **Must** |
| NFR-002..003 | Costo di indicizzazione documentato; soglia di latenza | **Should** |

## 10. Domande aperte

**DA-SS-1 — Dove vive l'indice semantico: corpus/`doc_type` del RAG vs store dedicato (DA-M-d) [priorità: ALTA]**
È la forca di design centrale dell'epica (DA-M-d). Opzioni da valutare al design:
- **Opzione A — corpus/`doc_type` del RAG:** trattare l'archivio come un nuovo corpus indicizzato dalla
  pipeline esistente (riuso massimo di `build_indexer`/`build_facade`, collezioni namespaced per
  `(corpus, provider)`). Pro: riuso totale, isolamento naturale via corpus distinto. Contro: la
  pipeline è pensata per file su disco, non per righe di `memory.sqlite` → serve un adattamento della
  sorgente di ingestione.
- **Opzione B — store vettoriale dedicato affiancato all'archivio:** una collezione vettoriale propria
  della memoria, popolata direttamente dai turni. Pro: aderente alla forma dei dati (turni in SQLite).
  Contro: più codice di wiring proprio, meno riuso.
- **Opzione C — porta/seam con due implementazioni:** decidere a config. (Probabile over-engineering
  per uno Should.)
[Impatta REQ-016/017, NFR-006 e la granularità. Segnalare al design.]

**DA-SS-2 — Granularità dell'unità indicizzata/restituita [priorità: ALTA]**
Turno (coerente con FEAT-002), sessione intera, o chunk (come il RAG)? FEAT-002 ha scelto **turno**
(ricerca) su archivio **sessione**. La semantica potrebbe voler chunkare turni lunghi. [Design,
coerente con DA-SS-1 e con la granularità di FEAT-002.]

**DA-SS-3 — Superficie utente del modo semantico [priorità: MEDIA]**
Estendere `sertor-rag memory search` con un'opzione `--semantic` (un solo comando, due modi) **oppure**
un sotto-comando dedicato `memory search-semantic`? Raccomandazione preliminare: opzione su comando
esistente (coerenza, meno superficie). [Design; la parità MCP è FEAT-010, fuori da qui.]

**DA-SS-4 — Meccanismo di incrementalità (marker/watermark) dell'indice semantico [priorità: ALTA]**
L'incrementalità è ora un **requisito** (REQ-030/031/032), non un'opzione: l'auto-indicizzazione a
fine sessione embedda solo il nuovo, mai l'intero archivio. Poiché l'archivio è **append-only**, il
problema è più semplice di FEAT-009 (niente change/delete detection — solo additività). Resta da
decidere al design **come** si materializza il marker di «già indicizzato» (REQ-031):
- **Opzione 1 — colonna/flag nell'archivio** `memory.sqlite` (es. un timestamp/booleano per turno):
  vicino ai dati, una sola sorgente di verità; ma scrive su una tabella di FEAT-001.
- **Opzione 2 — manifest/watermark separato** (riuso del pattern manifest SQLite di FEAT-009,
  namespaced per `(corpus-memoria, provider)`): non tocca lo schema di FEAT-001; coerente col
  precedente del core.
- **Opzione 3 — derivare il marker dallo stato del vector store** (chiedere allo store quali id
  esistono già): nessun marker proprio, ma dipende dalle capacità dello store.
Inoltre: il trigger del **rebuild totale eccezionale** (REQ-032) si lega al namespacing per provider
(`collection_name` già namespaced per `(corpus, provider)` → cambiare provider cambia collezione, il
che potrebbe rendere il rebuild *implicito*). [Design; coerente con DA-SS-1 e con il pattern FEAT-009.]

**DA-SS-5 — Nome esatto della manopola di opt-in [priorità: BASSA]**
Proposta non vincolante `SERTOR_MEMORY_SEMANTIC` (booleana, default off), accanto alle manopole
memoria esistenti. [Design.]

**DA-SS-6 — Distribuzione via installer (debito di completamento) [priorità: MEDIA]**
Per la regola «feature completa = installabile» (CLAUDE.md, Principio X), la nuova manopola di opt-in
e l'eventuale comando vanno cablati nei template `.env`/asset dell'installer (come ha fatto FEAT-009
per le manopole memoria). **Da promuovere** a item durevole (riga nel backlog epica / cross-ref
FEAT-009) prima che la feature conti come *done*; **non** risolto qui. [Tracciamento, non design.]
