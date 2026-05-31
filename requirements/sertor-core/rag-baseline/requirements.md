# Requisiti — Motore RAG vettoriale (baseline)
<!-- Deriva da: FEAT-002 -->

## 1. Contesto e problema (perché)

### Problema

Il prototipo (`prototype/01-baseline/`) dimostra che un indice vettoriale su codice e documentazione
è la capacità minima necessaria per rendere una codebase interrogabile tramite query in linguaggio
naturale. Tuttavia il prototipo è stato costruito in modo esplorativo: accoppiato a un corpus
specifico (FastAPI), privo di test sistematici, non configurabile senza modificare il codice, e
non riusabile come componente indipendente.

La capacità deve essere **rifatta a qualità di produzione**: testabile, configurabile via config
(senza toccare il codice), repo-agnostica, e progettata per essere **selezionata come una delle
quattro modalità RAG** del core Sertor.

### Perché è il Must della prima release

- È la dimostrazione del **CS-1** dell'epica: dato un progetto, si costruisce un indice vettoriale
  e lo si interroga ottenendo risultati pertinenti su query note.
- È la **modalità di entry-level** del retrieval: la più semplice da configurare (richiede solo
  embeddings + vector store), punto di riferimento per confrontare le modalità più avanzate.
- Le altre modalità (ibrido, grafico, agentico) si costruiscono sopra o a fianco di questa, quindi
  validarla prima riduce il rischio per l'intero stack.

### Ancoraggio al prototipo

Il comportamento di riferimento (non il design) è documentato in:
- `prototype/01-baseline/index.py` — pipeline di indicizzazione: load → chunk → embed → store
- `prototype/01-baseline/search.py` — pipeline di interrogazione: embed query → similarity search → hits
- `prototype/01-baseline/evaluate.py` — valutazione: hit-rate@k e MRR su ground-truth
- `prototype/01-baseline/chunking.py` — chunking code-aware (tree-sitter) + markdown

---

## 2. Obiettivi e criteri di successo

Collegati ai criteri dell'epica (§3 di `epic.md`):

| ID | Criterio | Misura / soglia | CS epica |
|----|----------|-----------------|----------|
| OBJ-1 | Il motore indicizza una codebase qualunque e rende l'indice interrogabile | Indice costruito senza errori su ≥ 2 codebase diverse (es. prototipo Sertor + un secondo repo) | CS-1, CS-5 |
| OBJ-2 | L'interrogazione restituisce risultati pertinenti su query note | Pertinenza (hit-rate@k, MRR) misurata su un corpus campione con ground-truth; **soglia di accettazione fissata in design** con baseline = prototipo (azure-small hit@5 ~0.80, ollama ~0.67), soglia ridotta ammessa per il provider locale | CS-1 |
| OBJ-3 | La re-indicizzazione è idempotente | Due esecuzioni consecutive sull'identica codebase producono un indice con lo stesso numero di chunk e gli stessi risultati alle medesime query | CS-3 (trasversale) |
| OBJ-4 | Il motore funziona con ≥ 2 provider di embeddings distinti (almeno uno locale, almeno uno cloud) | Test green su provider locale (es. Ollama) e su provider cloud (es. Azure) senza modificare il codice | CS-4, CS-7 |
| OBJ-5 | Il motore è selezionabile come modalità "baseline" senza influenzare le altre modalità | L'attivazione/disattivazione della modalità baseline non altera il comportamento delle altre | CS-2 |
| OBJ-6 | Il motore è coperto da test automatici | Suite di test che verifica indicizzazione, interrogazione, idempotenza e gestione degli errori | CS-4 |

---

## 3. Stakeholder e attori

| Attore | Ruolo rispetto a FEAT-002 |
|--------|--------------------------|
| Owner/maintainer (Domenico Saiu) | Costruisce, configura e valida il motore; definisce le soglie di qualità |
| Agente LLM (es. Claude Code via MCP) | Consumatore primario: interroga il motore come strumento di contesto |
| Epica `sertor-cli` (consumatore a valle) | Espone la modalità baseline all'utente finale via comandi `index` / `search` |
| FEAT-001 (nucleo condiviso) | Fornitore delle primitive che FEAT-002 usa: ingestione, chunking, embeddings, vector store |
| FEAT-004 (ibrido + reranking) | Feature sorella: riusa l'indice vettoriale del baseline; i suoi requisiti non devono essere anticipati qui |

---

## 4. Ambito

### In ambito

- **Pipeline di indicizzazione vettoriale**: caricamento dei sorgenti (codice + doc) da una
  codebase target, produzione di chunk tramite il nucleo (FEAT-001), calcolo degli embedding con
  un provider configurato, persistenza in un vector store.
- **Idempotenza del re-index**: rieseguire l'indicizzazione sullo stesso progetto deve sovrascrivere
  l'indice esistente producendo un risultato stabile (nessuna duplicazione di chunk).
- **Pipeline di interrogazione vettoriale**: data una query testuale, calcola il suo embedding con
  lo stesso provider usato in fase di indicizzazione, esegue una ricerca per similarità (coseno o
  equivalente) sul vector store, e restituisce i top-k risultati con metadati (path, source, kind,
  chunk index, punteggio di similarità, preview testuale).
- **Configurabilità del provider di embeddings**: il provider (locale o cloud) è selezionabile via
  configurazione senza modificare il codice.
- **Configurabilità del numero di risultati (k)**: il chiamante specifica quanti risultati ottenere.
- **Valutazione della pertinenza**: il motore deve supportare la misurazione di hit-rate@k e MRR su
  un ground-truth, come dimostrato in `prototype/01-baseline/evaluate.py`.
- **Selezione della modalità**: il motore è identificato e selezionabile come modalità `baseline`
  (o equivalente) tra le modalità del core.
- **Repo-agnosticità**: il motore deve funzionare su qualunque codebase target, non solo sul corpus
  del prototipo.
- **Test automatici**: copertura di indicizzazione, interrogazione, idempotenza, e gestione degli
  errori (provider non disponibile, indice assente).

### Fuori ambito

- **Nucleo condiviso** (ingestione, chunking, astrazione del vector store, embeddings multi-provider):
  è FEAT-001; FEAT-002 lo **usa**, non lo ridefinisce.
- **Retrieval ibrido** (BM25 + dense) e **reranking**: sono FEAT-004.
- **Retrieval a grafo** (code-graph / GraphRAG): è FEAT-005.
- **Retrieval agentico** (multi-step / query planning): è FEAT-006.
- **Interfaccia CLI** (`sertor index`, `sertor search`): è l'epica `sertor-cli`.
- **Formato di risposta all'utente finale** (output CLI): è l'epica `sertor-cli`.
- **Generazione di risposta LLM** (RAG completo con step di generation): fuori ambito MVP del motore;
  il motore produce i *chunk pertinenti*, non la risposta finale generata.
- **Ottimizzazione delle dimensioni dell'embedding** o della funzione di similarità: è design a valle.
- **Gestione multi-tenant** o condivisione dell'indice tra più progetti simultanei: post-MVP.

---

## 5. Requisiti funzionali (EARS)

### 5.1 Indicizzazione

**REQ-001 (Ubiquitous)**
*The baseline RAG engine shall accept a target codebase path and a configured embeddings provider, and produce a persistent vector index containing all code and documentation chunks derived from that codebase.*

Ancora: `prototype/01-baseline/index.py` (funzione `main`: `docs = load_code() + load_docs()` → `chunks = chunking.build_chunks(docs)` → `index_provider(p, chunks, client)`).

---

**REQ-002 (Event-driven)**
*When the indexing pipeline is invoked on a codebase that already has an existing index, the system shall discard the previous index and rebuild it from scratch, ensuring no duplicate chunks persist.*

Ancora: `prototype/01-baseline/index.py:31` — `client.delete_collection(name)  # idempotenza: ricrea da zero`.

---

**REQ-003 (Event-driven)**
*When indexing completes successfully, the system shall report the total number of chunks indexed and the embedding dimension used.*

Ancora: `prototype/01-baseline/index.py:64` — `print(f"[{p}] {n} chunk indicizzati (dim={dim}) in {time.time() - t:.1f}s")`.

---

**REQ-004 (Unwanted behaviour)**
*If the configured embeddings provider is unavailable or returns an error during indexing, then the system shall abort the indexing operation and report the failure without leaving a partial or corrupted index.*

---

**REQ-005 (Optional feature)**
*Where multiple embeddings providers are configured, the system shall be capable of building one independent index per provider, each identifiable univocamente.*

Ancora: `prototype/01-baseline/index.py` — un'unica collection per provider (`collection_name(provider) = "baseline_" + provider`); `prototype/01-baseline/index.py:53–64` — iterazione su più provider.

---

### 5.2 Interrogazione

**REQ-006 (Event-driven)**
*When a text query is submitted to the baseline engine, the system shall embed the query using the same provider used during indexing, execute a vector similarity search against the corresponding index, and return the top-k most similar chunks.*

Ancora: `prototype/01-baseline/search.py` — funzione `search`: `qv = get_embedder(provider).embed_one(query)` → `coll.query(query_embeddings=[qv], n_results=k)`.

---

**REQ-007 (Ubiquitous)**
*The system shall include, for each returned chunk, at minimum: the source file path, the source type (code / doc), the chunk index within the file, a similarity score, and a text preview.*

Ancora: `prototype/01-baseline/search.py:28–40` — ogni hit contiene `path`, `source`, `kind`, `chunk`, `distance`, `preview`.

---

**REQ-008 (Event-driven)**
*When a query is submitted, the system shall accept a caller-specified value of k (number of results to return); if no value is specified, the system shall use a default value.*

Ancora: `prototype/01-baseline/search.py:22` — `def search(query: str, provider: str = "ollama", k: int = 5)`.

---

**REQ-009 (Unwanted behaviour)**
*If the vector index for the requested provider does not exist, then the system shall return a clear error indicating that the index must be built before querying.*

---

**REQ-010 (Unwanted behaviour)**
*If the configured embeddings provider is unavailable during query execution, then the system shall return an error without returning partial or empty results silently.*

---

### 5.3 Valutazione della pertinenza

**REQ-011 (Optional feature)**
*Where a ground-truth evaluation set is provided (query → expected file paths), the system shall compute hit-rate@k (for k ∈ {1, 3, 5, 10}) and MRR@10 over that set and report the results.*

Ancora: `prototype/01-baseline/evaluate.py` — metriche `hit@1`, `hit@3`, `hit@5`, `hit@10`, `mrr@10` su `eval_queries.json`.

---

### 5.4 Configurabilità e selezione della modalità

**REQ-012 (Ubiquitous)**
*The system shall allow the embeddings provider to be selected via configuration, without requiring code changes.*

Ancora: `prototype/shared/embeddings.py:71–81` — `get_embedder(provider)` parametrizzato; `prototype/shared/config.py` — backend selezionato via `settings.backend`.

---

**REQ-013 (Ubiquitous)**
*The system shall expose the baseline vector RAG as a selectable modality, identifiable by a stable name (e.g. "baseline"), independently of other RAG modalities.*

---

**REQ-014 (While stato)**
*While the baseline modality is active, the system shall use only vector similarity retrieval and shall not invoke hybrid, graph, or agentic retrieval mechanisms.*

---

### 5.5 Repo-agnosticità e test

**REQ-015 (Ubiquitous)**
*The system shall operate on any target codebase provided as a path, without hardcoded assumptions about the project structure, language distribution, or corpus size.*

Ancora: `prototype/shared/loaders.py` — corpus-aware loader parametrizzato via `settings.corpus`; il dogfooding su `SERTOR_CORPUS=sertor` dimostra il funzionamento su un corpus diverso da FastAPI.

---

**REQ-016 (Ubiquitous)**
*The system shall include automated tests covering: (a) successful indexing of a sample codebase, (b) successful querying returning ≥ 1 result, (c) idempotent re-indexing, and (d) error handling for missing index and unavailable provider.*

---

## 6. Requisiti non funzionali

| ID | Categoria | Requisito | Soglia / misura |
|----|-----------|-----------|-----------------|
| NFR-001 | Pertinenza | Pertinenza (hit-rate@k, MRR) misurata su corpus campione con ground-truth; **soglia fissata in design**, baseline = prototipo, soglia ridotta ammessa per il locale (DA-1/DA-3 risolte) | Verificabile con REQ-011; riferimento prototipo `azure-small`: hit@5 ~0.80, MRR ~0.83; `ollama` hit@5 ~0.67 |
| NFR-002 | Performance (indicizzazione) | L'indicizzazione di una codebase di dimensioni tipiche deve completare in tempo ragionevole; **soglia numerica fissata in design** dopo profiling, baseline = prototipo (nessun numero assoluto vincolante ora) | DA-1 risolta (§10) |
| NFR-003 | Performance (interrogazione) | Il tempo di risposta a una singola query deve restare interattivo; **soglia (orientativa < 2 s locale) confermata in design** dopo misura (DA-1 risolta) | Riferimento prototipo |
| NFR-004 | Affidabilità | In caso di errore del provider durante l'indicizzazione, l'indice preesistente non viene corrotto (atomicità dell'operazione di rebuild) | Verificabile con REQ-004 |
| NFR-005 | Configurabilità | Il provider di embeddings è selezionabile via file di configurazione senza modificare il codice | Verificabile con REQ-012 |
| NFR-006 | Testabilità | Ogni requisito funzionale di §5 deve essere coperto da almeno un test automatico eseguibile in locale (con provider locale o mock) | Verificabile con REQ-016 |
| NFR-007 | Osservabilità minima | Il motore registra, a ogni run di indicizzazione e interrogazione: numero di chunk processati, provider usato, tempo di esecuzione, eventuali errori | Verificabile con REQ-003 |
| NFR-008 | Portabilità | Il motore funziona su almeno due sistemi operativi (es. Linux e Windows) senza modifiche al codice | Test su Linux nativo rinviato a CI/design (DA-2, §10) |

---

## 7. Vincoli, assunzioni e dipendenze

### Dipendenze

- **DIPENDE da FEAT-001 (Nucleo di retrieval condiviso):** FEAT-002 usa le primitive del nucleo
  per l'ingestione dei sorgenti, il chunking code-aware, il layer di embeddings multi-provider e
  l'astrazione del vector store. FEAT-001 deve essere decomposta e progettata prima o in parallelo
  con FEAT-002; i requisiti REQ-E2 dell'epica si applicano direttamente (embeddings + vector store
  sono obbligatori per questa modalità).
- **REQ-E2 dell'epica:** *Where a RAG modality requires text embeddings, the system shall require a
  configured embeddings provider and a vector store.* Questo motore ricade in questa categoria.
- **REQ-E5 dell'epica:** i segreti (API key del provider di embeddings) non devono essere
  persistiti in file versionati.

### Vincoli

- Il motore non deve ridefinire o duplicare le primitive del nucleo (FEAT-001); deve consumarle
  tramite la loro interfaccia pubblica.
- Il motore deve essere riusabile come componente (non è una CLI standalone): l'epica `sertor-cli`
  lo invoca a valle.
- Il motore deve supportare almeno un provider di embeddings locale (es. Ollama) e almeno uno
  cloud, come richiesto da CS-7 e REQ-E4.
- Le dipendenze del motore baseline devono essere **isolabili** rispetto a quelle delle modalità
  più pesanti (es. GraphRAG), per evitare conflitti (vincolo epica §5, rischio R-3).

### Assunzioni

- **A-1:** il nucleo FEAT-001 espone un'interfaccia stabile per il chunking e il layer di embeddings;
  se l'interfaccia cambia, FEAT-002 deve essere aggiornata di conseguenza.
- **A-2:** il vector store del nucleo supporta la ricerca per similarità coseno (o equivalente) e
  la persistenza su disco; la scelta del vector store specifico è materia del design di FEAT-001.
- **A-3:** il corpus target contiene file di codice sorgente e/o documentazione Markdown; corpora
  privi di entrambe le tipologie sono fuori dal caso d'uso primario (ma non bloccano il motore).
- **A-4:** il ground-truth per la valutazione (REQ-011) è un artefatto esterno che il chiamante
  fornisce; il motore non genera ground-truth automaticamente.
- **A-5:** le prestazioni di hit-rate dipendono dal provider di embeddings scelto; il motore non
  garantisce soglie identiche su tutti i provider (il riferimento è il provider di default
  configurato per l'ambiente: cloud in Azure, locale altrimenti).

---

## 8. Rischi

| ID | Rischio | Probabilità | Impatto | Mitigazione |
|----|---------|-------------|---------|-------------|
| R-B1 | Qualità del retrieval insufficiente (hit-rate < soglia OBJ-2) con il provider locale (Ollama) | Media | Alto (CS-1 non soddisfatto) | Definire soglie separate per provider locale e cloud; REQ-011 consente la misurazione sistematica |
| R-B2 | Idempotenza del re-index non garantita per grandi corpus (race condition o interruzione parziale) | Bassa | Alto (indice corrotto → risultati imprevedibili) | REQ-002 + REQ-004 + NFR-004 coprono il requisito; il design deve garantire atomicità (delete→rebuild) |
| R-B3 | Interfaccia FEAT-001 non stabile al momento della decomposizione di FEAT-002 | Media | Medio (blocco del design) | Decomporre FEAT-001 in parallelo; i requisiti di FEAT-002 sono espressi in termini di capacità, non di API |
| R-B4 | Tempi di indicizzazione inaccettabili su corpus molto grandi con provider locale | Media | Medio (UX degradata) | NFR-002 fissa soglie da validare; batching già presente nel prototipo (`prototype/01-baseline/index.py:38–46`) |
| R-B5 | Dipendenze del baseline in conflitto con quelle di altre modalità RAG | Bassa | Medio (ambienti non risolvibili, rischio R-3 dell'epica) | Mantenere le dipendenze del baseline minimali; isolare quelle pesanti nelle rispettive feature |
| R-B6 | Riscrittura introduce regressioni rispetto al prototipo senza accorgersene | Media | Alto | OBJ-2 con soglie esplicite + REQ-016 (test automatici) rendono il confronto misurabile |

---

## 9. Prioritizzazione (MoSCoW)

| Priorità | Requisiti | Motivazione |
|----------|-----------|-------------|
| **Must** | REQ-001, REQ-002, REQ-006, REQ-007, REQ-008, REQ-009, REQ-010, REQ-012, REQ-013, REQ-015, REQ-016 | Capacità minima di "creare un RAG" interrogabile (CS-1); idempotenza; configurabilità; test automatici |
| **Should** | REQ-003, REQ-004, REQ-011, REQ-014 | Osservabilità dell'indicizzazione; gestione robusta degli errori; valutazione della pertinenza; isolamento della modalità |
| **Could** | REQ-005 | Indici multi-provider in parallelo; utile per il confronto sperimentale, non necessario per la funzione primaria |
| **Won't (MVP)** | Generazione LLM integrata, multi-tenant, ottimizzazione avanzata della similarità | Fuori ambito dichiarato |

---

## 10. Domande aperte (risolte)

Chiuse in elicitazione il 2026-05-31.

| ID | Disposizione |
|----|--------------|
| DA-1 — Soglie di performance | **Risolta:** non si fissano numeri assoluti ora; le soglie (NFR-002/003) si fissano in **design** dopo profiling, con baseline = prototipo. |
| DA-2 — Test Linux nativo | **Rinviata** a CI/design; la portabilità multi-OS (NFR-008) resta obiettivo di test, non blocca l'MVP. |
| DA-3 — Soglia hit-rate locale | **Risolta:** si accetta una **soglia ridotta per il provider locale** (coerente col prototipo, ollama hit@5 ~0.67); le soglie esatte si fissano in design. |
| DA-4 — Indici multi-provider in parallelo | **Risolta:** l'MVP espone **un solo indice attivo** (provider configurato); REQ-005 resta **Could**. |
| DA-5 — Ground-truth condiviso o per-codebase | **Rinviata** al setup test/design; direzione: corpus campione condiviso (prototipo) come baseline + ground-truth per-codebase ammesso. |
