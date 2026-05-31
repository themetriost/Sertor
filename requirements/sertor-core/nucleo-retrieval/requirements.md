# Requisiti — Nucleo di retrieval condiviso
<!-- Deriva da: FEAT-001 -->

## 1. Contesto e problema (perché)

### Problema

Il prototipo (`prototype/`) dimostra che è possibile costruire quattro modalità di RAG su una
codebase (vettoriale, ibrido, grafico, agentico), ma ogni motore gestisce in modo indipendente
l'ingestione dei documenti, il chunking, gli embeddings e il punto d'accesso al retrieval. Questa
frammentazione produce duplicazione logica, rende difficile il cambio di provider/backend, e
impedisce di riusare le capacità come libreria su un repository qualunque.

Il risultato concreto nel prototipo: `shared/loaders.py:35` (`load_code`),
`shared/loaders.py:59` (`load_docs`), `shared/embeddings.py:71` (`get_embedder`),
`shared/chunking_code.py:67` (`code_chunks`), `shared/retrieval.py:61` (`search_code`) —
cinque capacità esistono ma sono assemblate in modo esplorativo, non production-grade, e
accoppiate al corpus hardcoded `fastapi`/`sertor` (v. `shared/loaders.py` chunk 0 e chunk 3:
lista `_EXCLUDE` gestita a mano).

### Perché serve un nucleo condiviso

Tutti i motori RAG (FEAT-002, FEAT-004, FEAT-005, FEAT-006) e le skill wiki (FEAT-003) devono
poter appoggiarsi a una fondazione unica, production-grade, che:

- **legga qualsiasi repository** (non solo corpus noti a priori) escludendo automaticamente
  artefatti, segreti e virtualenv;
- **chunki il codice ai confini sintattici** e la documentazione ai confini semantici, producendo
  chunk arricchiti di metadati stabili e riproducibili;
- **produca vettori** tramite un'astrazione di provider intercambiabili (locale/cloud) senza
  modificare il codice dei motori;
- **persista e interroghi** i chunk indicizzati tramite un'astrazione di backend di vector store
  intercambiabile;
- **esponga un punto d'accesso unico di retrieval** (facade) su cui i motori si appoggino senza
  dipendere dai dettagli del backend sottostante.

Senza questa fondazione ogni nuovo motore reimplementerebbe le stesse primitive, moltiplicando il
debito tecnico e rendendo impossibile la garanzia di qualità uniforme su repo-agnosticità,
configurabilità e testabilità (CS-4, CS-5 dell'epica).

---

## 2. Obiettivi e criteri di successo

I criteri sono misurabili e collegati ai criteri di successo dell'epica primaria.

| ID  | Criterio di successo locale | Collegamento epica |
|-----|-----------------------------|--------------------|
| LSC-1 | Dato un repository arbitrario (senza configurazione hardcoded), il nucleo lo ingesta, lo chunka e lo indicizza senza errori; verificabile su almeno due codebase distinte (es. il prototipo stesso + un secondo repo). | CS-5 (repo-agnostico) |
| LSC-2 | Il provider di embeddings è selezionabile via configurazione (senza modificare codice); il sistema produce vettori con almeno un provider locale e almeno un provider cloud, producendo risultati semanticamente equivalenti. | CS-4 (configurabile), CS-7 (LLM configurabile) |
| LSC-3 | Il backend di vector store è selezionabile via configurazione; il nucleo si comporta in modo equivalente con almeno due backend distinti (es. locale embedded e cloud). | CS-4 (configurabile) |
| LSC-4 | La facade di retrieval restituisce risultati pertinenti (precision@5 ≥ misura di riferimento definita durante il design) su query note rispetto a un corpus campione. | CS-1 (creare RAG, baseline) |
| LSC-5 | Ogni capacità del nucleo è coperta da test automatici; una re-indicizzazione sullo stesso corpus produce lo stesso insieme di chunk (idempotenza). | CS-4 (production-grade) |
| LSC-6 | Il nucleo non richiede alcun provider cloud per operare in modalità locale; in locale-only non si effettua nessuna chiamata di rete verso servizi cloud. | CS-4 (non dipende da singolo cloud) |

---

## 3. Stakeholder e attori

| Attore | Ruolo rispetto a FEAT-001 |
|--------|--------------------------|
| **Owner/maintainer** | Definisce i requisiti, valuta la qualità del nucleo, usa il dogfooding sul prototipo come acceptance test. |
| **Motori RAG (FEAT-002, 004, 005, 006)** | Consumatori diretti del nucleo: si appoggiano all'ingestione, al chunking, agli embeddings e alla facade senza reimplementarli. |
| **Skill wiki (FEAT-003, 007, 008)** | Consumano il nucleo per indicizzare e recuperare contenuti del wiki. |
| **Epica `sertor-cli` (consumatore a valle)** | Installa e configura il nucleo; non fa parte di questa feature. |
| **Agente LLM (es. Claude Code)** | Attore non umano: usa la facade di retrieval come strumento; beneficia della qualità e della stabilità dei metadati restituiti. |
| **Codebase target** | Il repository su cui il nucleo opera; qualunque progetto **multi-linguaggio** (set MVP: Python, JS/TS, Java, C#, Go, C/C++, PHP, Ruby, PowerShell, Bash, T-SQL, PL/SQL) + Markdown, con fallback testuale per gli altri linguaggi. |

---

## 4. Ambito

### In ambito

- **Ingestione repo-agnostica:** scoperta e lettura di file sorgente (codice e documentazione
  Markdown) di un repository qualunque, con meccanismo di esclusione configurabile di artefatti,
  virtualenv, file di segreti e cartelle ignorate dal version control.
- **Chunking code-aware:** suddivisione del codice ai confini sintattici (funzioni, classi,
  metodi) con produzione di metadati strutturali stabili (path, qualname, tipo di nodo); per la
  documentazione Markdown, chunking ai confini di heading con metadati di sezione.
- **Fallback al chunking dimensionale:** quando la lingua sorgente non è supportata dal chunker
  sintattico, il sistema ricade su chunking dimensionale (per dimensione/overlap) senza errore.
- **Astrazione del provider di embeddings:** interfaccia unica per produrre vettori, con almeno
  un provider locale e almeno un provider cloud supportati e selezionabili via configurazione.
- **Astrazione del vector store:** interfaccia unica per persistere, aggiornare e interrogare
  chunk indicizzati; backend locale embedded e backend cloud selezionabili via configurazione;
  gestione dei namespace per corpus multipli sullo stesso store.
- **Facade di retrieval:** punto d'accesso unico con almeno le operazioni: ricerca semantica su
  codice, ricerca semantica su documentazione, ricerca combinata; ogni risultato riporta metadati
  stabili (path, sorgente, chunk id, testo).
- **Configurazione centralizzata:** tutte le scelte di provider, backend, percorsi e parametri
  di chunking sono governate da un unico punto di configurazione, leggibile da file/variabili
  d'ambiente, senza toccare il codice.
- **Testabilità:** ogni capacità è esercitabile da test automatici in isolamento.

### Fuori ambito

- **Motori RAG completi** (baseline, ibrido, grafico, agentico): sono FEAT-002, 004, 005, 006;
  si appoggiano al nucleo ma non fanno parte di esso.
- **Skill LLM Wiki** (creare, mantenere, arricchire): FEAT-003, 007, 008.
- **UX/CLI** (comando `sertor`, pacchetto installabile, configurazione interattiva): epica
  `sertor-cli`.
- **Reranking** (cross-encoder, reranker semantico cloud): è una capacità dei motori ibridi
  (FEAT-004), non del nucleo condiviso.
- **Costruzione del code-graph AST/GraphRAG**: è la fondazione specifica di FEAT-005.
- **Gestione LLM per generazione/ragionamento**: il nucleo non richiede un LLM; lo richiedono
  i motori agentico (FEAT-006) e alcune skill wiki.
- **Valutazione della qualità del retrieval** (metriche end-to-end, benchmark): necessaria ma
  definita a livello di motore/epica; il nucleo espone solo i dati necessari per calcolarle.
- **Interfacce web o GUI.**

---

## 5. Requisiti funzionali (EARS)

### Capacità A — Ingestione repo-agnostica

**REQ-001** *(Ubiquitous)*
The ingestion component shall accept any file-system path as the root of a target repository and
discover all indexable files (source code and Markdown documentation) under that root without
requiring prior knowledge of the repository's structure or content.

*Ancora al prototipo:* `shared/loaders.py:35` (`load_code`) e `shared/loaders.py:59` (`load_docs`)
gestiscono la scoperta dei file; nel prototipo il percorso è hardcoded per corpus noti — il
requisito richiede di generalizzarlo.

**REQ-002** *(Ubiquitous)*
The ingestion component shall exclude from indexing any file or directory that matches a
configurable exclusion list (covering at minimum: virtual environments, build artefacts, binary
files, hidden VCS directories, and files matching patterns typically used for secrets).

*Ancora al prototipo:* `shared/loaders.py` chunk 3 — `_EXCLUDE` gestita manualmente; il requisito
richiede che sia configurabile, non hardcoded.

**REQ-003** *(Event-driven)*
When a file cannot be read (e.g. encoding error, permission denied), then the ingestion component
shall skip that file, record a warning with the file path and the failure reason, and continue
processing the remaining files.

**REQ-004** *(Ubiquitous)*
The ingestion component shall assign each ingested document a stable, unique identifier derived
from its relative path within the repository root, such that re-ingesting the same repository
produces the same identifiers for unchanged files.

*Ancora al prototipo:* `shared/loaders.py` chunk 1 — `Doc.id` è già il path relativo.

**REQ-005** *(Ubiquitous)*
The ingestion component shall attach to each document a set of metadata including at minimum: the
relative file path, the document type (code or documentation), and the detected programming
language or markup language.

---

### Capacità B — Chunking code-aware

**REQ-006** *(Ubiquitous)*
The chunking component shall split source code files at syntactic boundaries (functions, classes,
methods) producing chunks that correspond to complete, self-contained syntactic units.

*Ancora al prototipo:* `shared/chunking_code.py:67` (`code_chunks`) — chunking tree-sitter sui
confini sintattici; `01-baseline/chunking.py:49` (`chunk_doc`) — dispatcher code/doc.

**REQ-007** *(Ubiquitous)*
The chunking component shall attach to each code chunk a set of structural metadata including at
minimum: source file path, qualified name of the syntactic unit (e.g. class.method), node type
(function / class / method), and character/line offsets within the source file.

*Ancora al prototipo:* `01-baseline/chunking.py` chunk 2 (`_treesitter_code`) e chunk 3
(`chunk_doc`) — metadati strutturali già prodotti nel prototipo.

**REQ-008** *(Ubiquitous)*
The chunking component shall split Markdown documentation files at heading boundaries, producing
chunks that correspond to coherent sections, and attach to each chunk the document path and the
heading hierarchy.

**REQ-009** *(If <condizione>, then)*
If the source language of a file is not supported by the syntactic chunker, then the chunking
component shall fall back to size-based chunking with configurable chunk size and overlap, without
raising an error.

*Ancora al prototipo:* `01-baseline/chunking.py` chunk 1 (`_recursive_code`) — già presente come
fallback nel prototipo.

**REQ-010** *(Ubiquitous)*
The chunking component shall assign each chunk a stable, unique identifier derived from the
document identifier and the chunk's position, such that re-chunking the same unchanged document
produces the same chunk identifiers.

**REQ-011** *(Ubiquitous)*
The chunking component shall provide syntactic (code-aware) chunking for the MVP set of supported
languages — Python, JavaScript/TypeScript, Java, C#, Go, C/C++, PHP, Ruby, PowerShell, Bash, T-SQL,
PL/SQL — and shall allow this set to be extended with additional languages as an increment, not a
redesign. The chunking parameters (chunk size, overlap, supported-language set) shall be governable
via the centralised configuration without modifying the chunking component's code.

*Nota:* per i linguaggi del set non ancora coperti da un parser sintattico maturo al primo rilascio,
REQ-009 (fallback dimensionale) ne garantisce comunque la copertura senza errore.

---

### Capacità C — Astrazione del provider di embeddings

**REQ-012** *(Ubiquitous)*
The embeddings component shall expose a single interface for producing vector representations of
text, regardless of the underlying embedding provider.

*Ancora al prototipo:* `shared/embeddings.py:71` (`get_embedder`) — factory che restituisce un
`Embedder` uniforme; `shared/embeddings.py` chunk 2 (`Embedder._embed_batch`) — interfaccia
astratta già definita.

**REQ-013** *(Ubiquitous)*
The embeddings component shall support at least one local provider (operating without any cloud
service) and at least one cloud provider, selectable via the centralised configuration.

**REQ-014** *(Ubiquitous)*
The embeddings component shall process lists of texts in batches, with the batch size governable
via configuration, to accommodate provider rate limits and memory constraints.

*Ancora al prototipo:* `shared/embeddings.py` chunk 3 (`Embedder.embed`) — batching già
implementato nel prototipo.

**REQ-015** *(If <condizione>, then)*
If the configured embeddings provider is unavailable or returns an error, then the embeddings
component shall raise a structured error that identifies the provider, the failure reason, and
whether the operation can be retried.

**REQ-016** *(Where <feature>)*
Where a local-only configuration is selected, the embeddings component shall operate without
initiating any network connection to cloud services.

---

### Capacità D — Astrazione del vector store

**REQ-017** *(Ubiquitous)*
The vector store component shall expose a single interface for the operations: store chunks with
their vectors and metadata, update an existing collection (add, replace, or delete chunks),
and query by vector similarity.

**REQ-018** *(Ubiquitous)*
The vector store component shall support at least one local embedded backend and at least one
cloud backend, selectable via the centralised configuration without changing the caller's code.

*Ancora al prototipo:* `shared/retrieval.py` chunk 7 (sezione vector/hybrid) e
`02-hybrid-reranking/hybrid.py:50` (`HybridIndex.__init__`) — Chroma come backend locale;
`shared/config.py` chunk 2 — indici namespaced per corpus.

**REQ-019** *(Ubiquitous)*
The vector store component shall support namespaced collections, so that indices for different
repositories or corpora coexist in the same store without interference.

*Ancora al prototipo:* `shared/config.py` chunk 2 — `.index` vs `.index-<corpus>` già separati.

**REQ-020** *(Event-driven)*
When an indexing operation is performed on an already-indexed collection, the vector store
component shall support an incremental update mode that adds or replaces only the changed chunks,
without requiring a full re-index of the entire corpus.

**REQ-021** *(If <condizione>, then)*
If the configured vector store backend is unavailable, then the vector store component shall raise
a structured error that identifies the backend and the failure reason, without silently returning
empty results.

**REQ-022** *(Where <feature>)*
Where a local-only configuration is selected, the vector store component shall persist data to
the local file system only and shall not require any cloud credentials or network access.

---

### Capacità E — Facade di retrieval

**REQ-023** *(Ubiquitous)*
The retrieval facade shall expose a single, stable interface for querying the indexed corpus,
independent of the underlying vector store backend and embedding provider.

*Ancora al prototipo:* `shared/retrieval.py:61` (`search_code`) e `shared/retrieval.py:68`
(`search_docs`) — le funzioni di retrieval centralizzate che tutti i motori (agentico incluso,
v. `04-agentic-rag/mcp_server.py`) usano come punto di accesso comune.

**REQ-024** *(Ubiquitous)*
The retrieval facade shall support at minimum the following query operations: semantic search on
code, semantic search on documentation, and combined search across both.

**REQ-025** *(Ubiquitous)*
The retrieval facade shall return, for each result, at minimum: the chunk text, the source file
path, the chunk identifier, the document type (code/documentation), and a relevance score.

**REQ-026** *(Ubiquitous)*
The retrieval facade shall accept a configurable maximum number of results (`k`) per query.

**REQ-027** *(Ubiquitous)*
The retrieval facade shall support filtering results by document type (code only, documentation
only, or both) without requiring separate index structures.

**REQ-028** *(Event-driven)*
When a query is issued against an empty or uninitialised index, then the retrieval facade shall
return an empty result set and signal the absence of an index via a structured warning, without
raising an unhandled exception.

**REQ-029** *(Ubiquitous)*
The retrieval facade shall be usable as an importable component (library/skill) by any consuming
module (RAG engine, wiki skill, CLI layer) without requiring direct access to the underlying
store or embeddings implementation details.

*Collegamento:* REQ-E1 dell'epica — *"The system shall expose its RAG-creation and wiki
capabilities as reusable components, independent of any installation/CLI layer."*

---

### Configurazione e osservabilità trasversali

**REQ-030** *(Ubiquitous)*
The nucleus shall read all configuration values (provider, backend, paths, chunking parameters,
exclusion patterns) from a single centralised configuration, loadable from environment variables
and/or a configuration file, without hardcoded defaults in individual components.

*Ancora al prototipo:* `shared/config.py` chunk 1 (`Settings`) — già usa `RAG_BACKEND`,
`SERTOR_CORPUS` e variabili d'ambiente; il requisito richiede di generalizzare e rendere
repo-agnostiche le parti ancora hardcoded.

**REQ-031** *(Ubiquitous)*
The nucleus shall emit structured log events (at minimum: indexing start/end with document count,
embedding errors, store errors, query timing) to enable observability without requiring a
specific logging framework to the caller.

**REQ-032** *(If <condizione>, then)*
If a secret value (API key, credential) is required by a component, then the nucleus shall read
it exclusively from environment variables or a local non-version-controlled file, and shall not
write it to any version-controlled path.

*Collegamento:* REQ-E5 dell'epica — *"If a configuration value is a secret, then the system
shall not persist it in a version-controlled file."*

---

## 6. Requisiti non funzionali

| ID     | Categoria | Requisito |
|--------|-----------|-----------|
| NFR-01 | **Testabilità** | Ogni componente del nucleo (ingestione, chunking, embeddings, vector store, facade) deve essere testabile in isolamento tramite test automatici, senza dipendere da servizi esterni o da un corpus reale. |
| NFR-02 | **Idempotenza** | L'operazione di indicizzazione completa su un corpus invariato deve produrre lo stesso insieme di chunk identifier e lo stesso contenuto dei vettori (a parità di provider). |
| NFR-03 | **Portabilità** | Il nucleo deve operare su almeno due sistemi operativi (es. Linux e Windows) senza modifiche al codice. |
| NFR-04 | **Isolamento dipendenze pesanti** | Le dipendenze specifiche di un singolo backend/provider devono essere installabili in modo opzionale (es. extra di pacchetto), così da non bloccare l'uso del nucleo con gli altri backend. |
| NFR-05 | **Performance di indicizzazione** | L'indicizzazione di un repository di medie dimensioni (≤ 50 000 righe di codice sorgente) deve completarsi entro un tempo ragionevole definito durante il design; il valore di riferimento è stabilito a partire dai tempi misurati sul prototipo. |
| NFR-06 | **Performance di retrieval** | Una singola query di retrieval deve restituire risultati entro una latenza massima definita durante il design (valore orientativo: < 2 secondi su hardware standard con backend locale). |
| NFR-07 | **Sicurezza / privacy** | Nessun dato del repository target (testi, chunk, vettori) deve essere trasmesso a servizi non configurati esplicitamente; in modalità locale, nessun dato lascia la macchina. |
| NFR-08 | **Manutenibilità** | Il codice del nucleo deve essere strutturato in componenti chiaramente separati (ingestione, chunking, embeddings, store, facade) con interfacce stabili, per permettere la sostituzione di un componente senza impattare gli altri. |

---

## 7. Vincoli, assunzioni e dipendenze

### Vincoli

- **V-1:** Il nucleo non può dipendere dall'epica `sertor-cli` per funzionare (REQ-E1 dell'epica);
  deve essere usabile come libreria indipendente.
- **V-2:** Nessun segreto (chiavi API, credenziali) può essere scritto in file versionati (REQ-E5).
- **V-3:** Il nucleo deve supportare la modalità local-only senza alcuna chiamata di rete cloud
  (REQ-E4, LSC-6).
- **V-4:** Il progetto è Python >= 3.11 (vincolo d'epica).

### Assunzioni

- **A-1:** Il repository target è accessibile in lettura dal file system locale (o da un path
  montato); non è richiesto il supporto a repository remoti (es. clone da URL) in questa feature.
- **A-2:** Il corpus principale da indicizzare è composto da file di testo (codice sorgente e
  Markdown); file binari, immagini e formati non-testo (PDF/DOCX/notebook) sono **esclusi dall'MVP**
  di FEAT-001 (DA-001 risolta — vedi §10).
- **A-3:** Il chunker sintattico copre **dal primo rilascio** un set multi-linguaggio (Python,
  JS/TS, Java, C#, Go, C/C++, PHP, Ruby, PowerShell, Bash, T-SQL, PL/SQL; REQ-011), estendibile come
  incremento; REQ-009 (fallback dimensionale) garantisce la copertura dei linguaggi fuori dal set
  senza errore (DA-002 risolta — vedi §10).
- **A-4:** La facade di retrieval nel nucleo copre le operazioni di recupero (read); le operazioni
  di scrittura/indicizzazione sono gestite separatamente dai componenti di ingestione e store.
- **A-5:** Un solo indice attivo per volta per corpus/repository è il caso d'uso principale; la
  gestione di indici multipli concorrenti sullo stesso store è fuori ambito per questa feature.

### Dipendenze

- **D-1:** FEAT-002 (motore RAG vettoriale) è il primo consumatore diretto del nucleo; la sua
  implementazione convalida la correttezza e la completezza dell'interfaccia esposta dal nucleo.
- **D-2:** FEAT-003 (skill wiki) è consumatore del nucleo per l'indicizzazione dei contenuti wiki.
- **D-3:** La configurazione del provider LLM/embeddings e del backend di retrieval è descritta
  nell'epica `sertor-cli`; il nucleo la legge ma non la definisce.

---

## 8. Rischi

| ID   | Rischio | Probabilità | Impatto | Mitigazione |
|------|---------|-------------|---------|-------------|
| R-N1 | **Interfaccia facade insufficiente:** la facade definita per FEAT-001 non copre i bisogni dei motori ibrido/agentico (FEAT-004, 006) e deve essere estesa con breaking change. | Media | Alto | Coinvolgere la decomposizione di FEAT-004 e FEAT-006 come input di validazione dell'interfaccia prima di finalizzarla; progettare la facade con punti di estensione espliciti. |
| R-N2 | **Maturità disomogenea del chunking sintattico nel set multi-linguaggio:** per alcuni linguaggi del set MVP (es. shell, dialetti SQL) un parser sintattico maturo può non essere disponibile al primo rilascio; il fallback dimensionale (REQ-009) compensa ma produce chunk di qualità inferiore. | Alta | Medio | Prioritizzare i parser per i linguaggi più usati nel repo target; misurare la qualità del retrieval per linguaggio durante il design; il set è estensibile incrementalmente. |
| R-N3 | **Idempotenza dell'indicizzazione difficile da garantire:** l'ordine di scoperta dei file e i timestamp possono variare tra esecuzioni, producendo chunk identifier diversi. | Media | Medio | Il requisito REQ-004 (ID da path relativo) e REQ-010 (ID chunk da posizione) devono essere verificati esplicitamente nei test di idempotenza (NFR-02). |
| R-N4 | **Conflitti di dipendenze tra backend:** installare tutti i backend nel medesimo ambiente può causare conflitti irrisolvibili. | Media | Medio | Vincolo V-4 (isolamento dipendenze pesanti, NFR-04): definire gli extra del pacchetto durante la fase di design. |
| R-N5 | **Scope creep verso il motore baseline:** la tentazione di includere logica specifica di FEAT-002 nel nucleo condiviso (es. pipeline di indicizzazione end-to-end) può gonfiare FEAT-001 e ritardare la delivery. | Media | Medio | Il confine "fuori ambito" (§4) è esplicito; verificarlo durante la revisione dei requisiti di FEAT-002. |

---

## 9. Prioritizzazione (MoSCoW)

### Must (blocca il completamento di FEAT-001 e di tutti i consumatori)

- REQ-001, REQ-002, REQ-003, REQ-004, REQ-005 — ingestione repo-agnostica completa
- REQ-006, REQ-007, REQ-008, REQ-009, REQ-010, REQ-011 — chunking code-aware + fallback
- REQ-012, REQ-013, REQ-014, REQ-015 — astrazione embeddings con locale + cloud
- REQ-017, REQ-018, REQ-019, REQ-021 — astrazione vector store con backend locali/cloud e namespace
- REQ-023, REQ-024, REQ-025, REQ-026, REQ-027, REQ-028, REQ-029 — facade di retrieval completa
- REQ-030, REQ-032 — configurazione centralizzata + protezione segreti

### Should (raccomandati per la qualità production-grade, ma non bloccanti per il primo rilascio)

- REQ-020 — aggiornamento incrementale dell'indice (senza full re-index)
- REQ-022 — garanzia locale-only senza accesso di rete
- REQ-016 — garanzia locale-only per gli embeddings
- REQ-031 — log strutturati per osservabilità

### Could (desiderabili, posticipabili)

- Supporto a linguaggi **oltre il set MVP** nel chunker sintattico (estensione incrementale; il set
  MVP di 14 linguaggi è Must via REQ-011, DA-002 risolta)
- Supporto a formati documentali **non-testo** (PDF/DOCX/notebook) — post-MVP (DA-001 risolta: fuori MVP)

### Won't (fuori ambito per questa feature, da rivedere nelle feature successive)

- Reranking semantico (FEAT-004)
- Costruzione del code-graph AST (FEAT-005)
- Generazione/ragionamento LLM (FEAT-006)
- Valutazione automatica della qualità del retrieval (metrica end-to-end)

---

## 10. Domande aperte (risolte)

Chiuse in elicitazione il 2026-05-31 (decisioni di ambito MVP del core).

**DA-001 — File non-testo (PDF/DOCX/notebook).** *Risolta:* **fuori MVP**. L'MVP ingesta codice
(set multi-linguaggio) + Markdown/testo; PDF/DOCX/`.ipynb` sono post-MVP. (Aggiorna A-2.)

**DA-002 — Linguaggi del chunking sintattico.** *Risolta:* **multilinguaggio da subito**. Set MVP:
Python, JavaScript/TypeScript, Java, C#, Go, C/C++, PHP, Ruby, PowerShell, Bash, T-SQL, PL/SQL
(REQ-011), con **fallback testuale** per gli altri (REQ-009) ed **estensibilità** del set come
incremento, non riprogettazione. (Aggiorna A-3; LSC-1 verificabile su un 2° repo non-Python.)

**DA-003 — Baseline di performance.** *Risolta:* **non si fissano numeri assoluti ora**; le soglie
(NFR-05/06) si fissano in **fase di design** dopo misura reale, con **baseline = il prototipo stesso**
(corpus di dogfooding) come riferimento minimo.

**DA-004 — Aggiornamento incrementale.** *Risolta:* l'MVP usa **full re-index** (naturalmente
idempotente); l'aggiornamento incrementale (REQ-020) resta **Should/post-MVP**, collocato nella
**manutenzione** (nuova FEAT-009 dell'epica, per l'indice sorgenti).

**DA-005 — Extra opzionali del pacchetto.** *Rinviata* all'epica `sertor-cli` (struttura del
pacchetto/installazione). La direzione (NFR-04) resta: dipendenze pesanti installabili come extra.
