# Requisiti — Refresh incrementale dell'indice
<!-- Deriva da: FEAT-009 (epica sertor-core — «Manutenzione/refresh incrementale dell'indice RAG sui sorgenti») -->

> Base di evidenza: [`corollario-costo.md`](corollario-costo.md) (analisi dei 5 stadi di
> `index(rebuild=True)`). Prior art consultata (2026-06-16): CocoIndex (lineage tracking, change
> detection mtime+fingerprint, cache step pesanti, `behavior_version`), LlamaIndex IngestionPipeline
> (docstore con hash, `upserts_and_delete`), record-manager di LangChain (ledger SQLite, `cleanup`).
> Decisioni di scope prese con l'utente (2026-06-16): **(F1)** vettore incrementale + BM25/code-graph
> ricostruiti dal ledger; **(F2)** incrementale **di default**, full su `--full`.

## 1. Contesto e problema (perché)

Oggi `index()` fa **rebuild-from-scratch**: i cinque stadi — *discover* (legge tutti i file), *chunk*
(ritaglia ogni documento), *embed* (vettorializza), *store* (riscrive tutto il vector store con
`reset`+upsert), *BM25 + code-graph* (sidecar lessicale + grafo AST) — sono **full a ogni invocazione**.
L'unico stadio già incrementale è l'**embed**, grazie alla cache per content-hash (FEAT-019): paga solo
i chunk nuovi. Tutto il resto è wall-clock pieno e CPU/I-O piena.

Sul dogfood (652 doc) il full re-index è di pochi secondi → la regola standing di re-index a fine step
(`CLAUDE.md` p.5) basta. Ma su **ospiti grandi** (centinaia di MB / decine di migliaia di file) il full
a ogni modifica è **minuti**, dominato da I/O (discover) e CPU (chunk + grafo) — stadi che la cache non
copre. Questo contraddice l'essenza di Sertor (*contesto dell'agente sempre reale*): se tenere fresco
l'indice costa minuti, lo si fa meno spesso e il contesto diventa stantio. La feature colma questo
vuoto: **riprocessare solo ciò che è cambiato**.

> Il *come* (formato del manifest, struttura del codice) è materia della fase di design. Qui solo *cosa*
> e *perché*.

## 2. Obiettivi e criteri di successo

- **CS-1 (costo proporzionale al cambiamento):** dato un corpus già indicizzato, modificare **un** file
  e rilanciare aggiorna l'indice in tempo proporzionale al **delta**, non al corpus intero; su un corpus
  grande con poche modifiche, il run incrementale è **molto più veloce** del full rebuild.
- **CS-2 (equivalenza):** dopo un run incrementale, una query produce gli **stessi risultati** che si
  otterrebbero da un full rebuild sulla **stessa** sorgente (vettore, BM25 e code-graph allineati).
- **CS-3 (cancellazioni):** un file **rimosso** dalla sorgente **non compare più** nei risultati dopo il
  run incrementale (le sue tracce sono eliminate da store, BM25 e grafo).
- **CS-4 (correttezza su cambio logica):** se cambia la **versione della logica** di chunking/estrazione,
  il run incrementale **riprocessa** i file interessati; **0** chunk prodotti da logica vecchia
  sopravvivono.
- **CS-5 (fallback sicuro):** con manifest assente o incompatibile, il sistema esegue un **full rebuild**
  automatico; **0** casi in cui produce un indice parziale/silenziosamente incompleto.
- **CS-6 (idempotenza):** un secondo run incrementale su sorgente invariata **non** modifica l'indice
  (nessun lavoro, nessun cambiamento).
- **CS-7 (drift osservabile):** ogni run incrementale **dichiara** quanti file invariati/nuovi/modificati/
  cancellati e quanti chunk aggiunti/rimossi, così una deriva è **visibile**, non silenziosa.

## 3. Stakeholder e attori

- **Owner/operatore di un ospite grande:** principale beneficiario — tiene l'indice fresco senza il costo
  del full a ogni modifica.
- **Agente LLM:** consuma un indice che resta **allineato alla realtà** a basso costo (essenza).
- **Il rituale di step (`CLAUDE.md` p.5):** oggi prescrive il full re-index; con l'incrementale di default
  il re-index a fine step diventa economico anche su ospiti grandi.
- **Il nucleo di indicizzazione** (`services/indexing.py`, i 5 stadi): l'oggetto della feature.
- **La cache embeddings (FEAT-019):** dipendenza a monte — copre già lo stadio embed.

## 4. Ambito

### In ambito
- **Manifest/ledger persistito** dello stato dell'indice (per file: tempo di modifica, content-hash,
  chunk-id derivati, versione della logica) per riconoscere cosa è cambiato e cosa rimuovere.
- **Rilevamento dei cambiamenti** a due livelli: tempo di modifica come pre-filtro + content-hash come
  conferma.
- **Aggiornamento incrementale del vector store**: upsert mirato dei chunk dei file nuovi/modificati,
  **delete mirato** dei chunk dei file modificati/cancellati (no `reset`+full-upsert).
- **Ricostruzione di BM25 e code-graph dal set di chunk del ledger** (senza ri-leggere/ri-chunkare i
  file invariati), così restano corretti dopo ogni run.
- **Incrementale come comportamento di default** quando esiste un manifest valido; **full rebuild su
  richiesta esplicita** (`--full`/equivalente) e come **fallback automatico** quando il manifest manca o
  è incompatibile.
- **Equivalenza col full rebuild** e **invalidazione su cambio della logica** di chunking/estrazione.
- **Osservabilità** del run incrementale (conteggi delta) via il logging esistente.

### Fuori ambito
- **Modalità live/watch** (watcher del filesystem per aggiornamento near-real-time, tipo CocoIndex
  `live=True`): capacità futura.
- **Change-data-capture push** da sorgenti remote (notifiche): fuori ambito (legato a `ingestione-estesa`).
- **BM25 e code-graph *veramente* incrementali** (aggiornamento mirato degli archi cross-file, non
  ricostruzione): ottimizzazione futura (Could) — la ricostruzione-da-ledger è il primo taglio.
- **Parallelizzazione del chunking** e **discover incrementale** spinto: leve di performance ortogonali
  (vedi §9, Could).
- **Rilevamento di rinomini/spostamenti** come tali (nel primo taglio = delete+new): vedi §10.
- **Concorrenza multi-processo** sullo stesso indice (locking): vedi §10.
- Definizione del *come* (formato/sede del manifest, schema): fase di **design**.

## 5. Requisiti funzionali (EARS)

### Manifest e rilevamento
- **REQ-001 (Ubiquitous):** *The system shall maintain a persistent index manifest recording, per source
  file, its last-seen modification time, a content hash, the ids of the chunks derived from it, and the
  version of the chunking/extraction logic that produced them.*
- **REQ-002 (Event-driven):** *When an incremental index run starts, the system shall classify each
  current source file as unchanged, new, modified, or deleted by comparing modification time (fast
  pre-filter) and content hash (confirmation) against the manifest.*
- **REQ-003 (Unwanted):** *If a file's modification time differs but its content hash is unchanged, then
  the system shall treat the file as unchanged and refresh only its recorded modification time (no
  reprocessing).*

### Aggiornamento incrementale (vettore)
- **REQ-004 (Event-driven):** *When a source file is new or modified, the system shall re-chunk only that
  file, embed its chunks (reusing the embedding cache for unchanged chunk content), and upsert the
  resulting records into the vector store.*
- **REQ-005 (Event-driven):** *When a source file is modified or deleted, the system shall remove from the
  vector store the chunks previously derived from that file (as recorded in the manifest) via targeted
  deletion, not a full collection reset.*
- **REQ-006 (Event-driven):** *When a source file is unchanged, the system shall skip reading, chunking,
  embedding and store-writing for that file.*

### BM25 e code-graph (dal ledger)
- **REQ-007 (Ubiquitous):** *The system shall persist the chunk set in the manifest so that the lexical
  (BM25) index and the code-graph can be regenerated without re-reading or re-chunking unchanged files.*
- **REQ-008 (Event-driven):** *When an incremental run changes the chunk set, the system shall regenerate
  the lexical index and the code-graph from the current chunk set so that both reflect the post-update
  state.*

### Attivazione (default incrementale, full su richiesta/fallback)
- **REQ-009 (State-driven):** *While a valid manifest exists for the target corpus, the system shall
  index incrementally by default.*
- **REQ-010 (Event-driven):** *When the operator explicitly requests a full rebuild, the system shall
  rebuild the entire index from scratch and rewrite the manifest, ignoring the previous one.*
- **REQ-011 (Unwanted):** *If no manifest exists, or it is incompatible or corrupt, then the system shall
  fall back to a full rebuild (writing a fresh manifest) rather than produce a partial index.*

### Correttezza ed equivalenza
- **REQ-012 (Ubiquitous):** *The system shall ensure that an incremental run produces an index equivalent
  to a full rebuild over the same source state (same chunks, same store records, same lexical index, same
  graph).*
- **REQ-013 (Event-driven):** *When the chunking/extraction logic version recorded in the manifest
  differs from the current one, the system shall treat the affected files as modified and reprocess them,
  so that no chunk produced by stale logic survives.*
- **REQ-014 (Unwanted):** *If an incremental run fails partway for a file (read/parse/store error), then
  the system shall surface the failure and shall not leave that file in a silently partial, inconsistent
  state in the index.*

### Osservabilità, idempotenza, vehicles
- **REQ-015 (Event-driven):** *When an incremental run completes, the system shall report the counts of
  unchanged / new / modified / deleted files and of chunks added / removed.*
- **REQ-016 (Event-driven):** *When an incremental run executes, the system shall emit it as an
  observability event through the existing logging, consistently with full index runs.*
- **REQ-017 (Event-driven):** *When the same source state is indexed incrementally more than once, the
  system shall make no further changes (idempotence).*
- **REQ-018 (Ubiquitous):** *The incremental capability shall be reachable through the vehicles (the
  `sertor-rag` CLI / MCP), consistent with Principio XI — no separate library-only entry path.*

## 6. Requisiti non funzionali
- **NFR-1 (correttezza > velocità):** in caso di dubbio sullo stato di un file, il sistema **riprocessa**
  (mai saltare a rischio di stantio). L'essenza «contesto reale» prevale sull'ottimizzazione.
- **NFR-2 (artefatto locale, gitignored):** il manifest è un artefatto rigenerabile, **namespaced per
  `(corpus, provider)`** come le collezioni e l'indice, **non versionato** (sezione Sicurezza della
  costituzione).
- **NFR-3 (nessun segreto):** il manifest non contiene segreti; vale la redazione già in uso.
- **NFR-4 (overhead trascurabile a vuoto):** un run incrementale su corpus invariato deve costare
  ~quanto la sola scansione dei metadati (nessun lavoro inutile).
- **NFR-5 (host-agnostico, Principio X):** funziona su qualunque ospite; ciò che varia sta in config.
- **NFR-6 (non distruttività del full):** il full rebuild su `--full` resta il «reset» sicuro e atomico
  di oggi (rebuild-from-scratch).

## 7. Vincoli, assunzioni e dipendenze
- **Granularità (assunzione):** l'unità di cambiamento è il **file** (un file modificato viene ri-chunkato
  per intero); l'embed-cache evita comunque di ri-pagare i chunk con contenuto identico. Il rilevamento a
  grana di chunk è un'ottimizzazione futura (§10).
- **Dipendenza FEAT-019** (cache embeddings per content-hash): copre lo stadio embed; questa feature la
  riusa, non la ridefinisce.
- **Idempotenza esistente:** il full rebuild è già idempotente sugli stessi id; l'incrementale deve
  preservare gli **id stabili** dei chunk (`doc_id#index`).
- **Atomicità dello store:** oggi lo store fa `reset`+upsert atomico; l'incrementale introduce
  upsert/delete mirati — la consistenza dello store durante il run è un vincolo di design.
- **Vehicles (Principio XI):** l'incrementale è esposto dalla CLk/MCP, non da un percorso libreria a sé.

## 8. Rischi
- **R-1 — Drift silenzioso (il rischio n.1, acuito dal default-incrementale):** se il rilevamento manca
  un cambiamento o il manifest si disallinea, l'indice diverge dalla realtà **senza accorgersene** —
  esattamente ciò che Sertor vuole evitare. Mitiganti: REQ-012 (equivalenza), REQ-013 (cambio logica),
  REQ-011 (fallback al full), REQ-015 (conteggi osservabili), `--full` facile/documentato, eventuale full
  periodico di riconciliazione (§10).
- **R-2 — Manifest corrotto/incompatibile:** versioni del formato o file danneggiato → REQ-011 (fallback
  al full) come rete.
- **R-3 — Costo residuo di BM25/grafo:** ricostruirli dal ledger a ogni run non è gratis su corpora
  enormi (sono comunque strutture full) — il guadagno principale resta su discover/chunk/embed/store; la
  vera incrementalità di BM25/grafo è una dote futura.
- **R-4 — Rinomini trattati come delete+new:** un file spostato/rinominato ri-embedda i suoi chunk
  (costo) finché non si aggiunge la rename-detection (§10).
- **R-5 — Concorrenza:** due processi che indicizzano lo stesso indice insieme possono corrompere il
  manifest/store (§10).

## 9. Prioritizzazione (MoSCoW)
- **Must:** REQ-001..006 (manifest + rilevamento + incrementale vettore + cancellazioni), REQ-007/008
  (BM25/grafo dal ledger — scelta F1), REQ-009/010/011 (default incrementale + full + fallback — scelta
  F2), REQ-012/013/014 (correttezza/equivalenza/logica/integrità), REQ-015 (conteggi), REQ-017
  (idempotenza), REQ-018 (vehicles); NFR-1..6.
- **Should:** REQ-016 (evento di osservabilità dedicato, oltre ai conteggi); **rename-detection**
  (delete+new → move riconosciuto); **full periodico di riconciliazione** opzionale (anti-drift).
- **Could:** **BM25/code-graph veramente incrementali** (archi cross-file mirati); **parallelizzazione
  del chunking** + **discover incrementale** spinto (leve di performance); **rilevamento a grana di
  chunk**.
- **Won't (ora):** modalità **live/watch**; **CDC push** da sorgenti remote; **locking multi-processo**.

## 10. Domande aperte
- **DA-1 — Sede/formato del manifest:** SQLite locale accanto a `embed_cache.sqlite`/`observability.sqlite`
  o file dedicato? (design; vincola NFR-2). [proposto: SQLite locale namespaced]
- **DA-2 — Full periodico di riconciliazione:** col default-incrementale conviene forzare un full ogni N
  run / a un trigger (anti-drift di lungo periodo)? Should o Won't? [DA CHIARIRE]
- **DA-3 — Rename-detection:** vale la pena riconoscere i rinomini (stesso hash, path diverso) per
  evitare il re-embed, o delete+new è accettabile nel primo taglio? [proposto: delete+new ora, rename Should]
- **DA-4 — Concorrenza:** serve un lock sul manifest/indice per più processi/utenti che indicizzano
  insieme (cross-ref epica `multiutente`)? [DA CHIARIRE — probabile Won't finché mono-utente]
- **DA-5 — Soglia di convenienza:** sotto quale numero di file cambiati l'incrementale conviene davvero
  vs un full (per corpora piccoli il full è già pochi secondi)? [misura in design]
