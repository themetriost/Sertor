# Requisiti — Motore RAG a grafo (code-graph strutturale)
<!-- Deriva da: FEAT-005 (backlog epica sertor-core) -->
<!-- Stato: elicitato — 2026-06-12; domande aperte DA-1..DA-5 RISOLTE con l'utente lo stesso giorno -->

## 1. Contesto e problema (perché)

I due motori RAG già consegnati — vettoriale (`BaselineEngine`,
`src/sertor_core/engines/baseline.py`) e ibrido (`HybridEngine`, FEAT-004) — operano per
**similarità**: trasformano la query in un vettore e recuperano i chunk semanticamente o
lessicalmente vicini. Questa strategia è potente per le query in linguaggio naturale, ma ha
un limite strutturale quando si naviga il codice: risponde alla domanda «cosa tratta questo
codice?» ma non risponde alle domande «dove è definito il simbolo X?», «chi chiama Y?» o
«quali doc menzionano Z?».

Queste ultime sono domande di **navigazione strutturale**: richiedono di seguire archi esatti
nel grafo delle dipendenze del codice (definitions, calls, imports, mentions), non di calcolare
prossimità semantica. Il prototipo (`prototype/03-graphrag/`) ha già dimostrato la fattibilità
dell'approccio: `build_graph.py` costruisce un grafo orientato con nodi `module / class /
function / method / doc` e archi `contains / calls / imports / inherits / mentions` via analisi
AST (Python `ast`); `graph_query.py` risponde alle query `def / callers / callees / docs /
context` in modo deterministico, senza embedding, senza cloud.

Il server MCP di produzione (`src/sertor_mcp/server.py:6-7`) ha già riservato esplicitamente
gli slot `find_symbol` / `who_calls` / `related_docs` / `get_context` per il motore GraphRAG,
precisando che «torneranno col motore GraphRAG (FEAT-005)». Fino ad allora, l'agente LLM
non ha accesso alla navigazione strutturale del corpus dal server MCP di produzione.

Il chunking sintattico già presente nel core (`src/sertor_core/services/chunking/code.py`,
10 linguaggi, metadati `qualname / symbol / node_type / start_line / end_line`) costituisce
la base naturale su cui costruire il grafo: i simboli sono già identificati con qualname
completo e coordinate riga. La costruzione del grafo può riusare questi metadati invece di
ri-parsare il codice da zero.

**Ambiguità di terminologia da disambiguare.** Il termine «GraphRAG» copre due famiglie
tecnologicamente molto diverse:

- **(a) Code-graph strutturale**: grafo AST deterministico (definizioni, chiamate, import,
  ereditarietà, menzioni doc↔simbolo). Navigazione per lookup esatti; nessun LLM nella
  costruzione; operazione offline, veloce, riproducibile. Prototipo: `prototype/03-graphrag/`.
- **(b) Microsoft GraphRAG / Knowledge Graph LLM**: knowledge graph estratto da testo via
  LLM + community summaries + retrieval su grafi gerarchici. Costoso (LLM a ogni build),
  dipendenza `graphrag` con ambiente isolato (R-3 epica). Non nel prototipo in questa forma.

L'epica e il prototipo puntano chiaramente a **(a)**; la nota FEAT-005 nell'epica («riporta
`find_symbol`/`who_calls` nel server MCP») conferma che la capacità richiesta è la navigazione
strutturale, non l'extraction LLM. Questa feature elicita i requisiti del **code-graph
strutturale (a)**; il Knowledge Graph LLM è fuori ambito (vedi §4).

---

## 2. Obiettivi e criteri di successo (LSC)

| ID | Criterio (misurabile, tech-agnostico) | Collegamento |
|----|---------------------------------------|--------------|
| LSC-1 | Dato un simbolo presente nel corpus (es. `EmbeddingProvider`), il sistema restituisce la sua **definizione** con path e numero di riga corretti in **≤1 round-trip di lookup** (nessuna iterazione vettoriale). | CS-2 epica |
| LSC-2 | Dato un simbolo, il sistema restituisce i suoi **chiamanti diretti** nel corpus con precisione **≥ 80%** su un ground-truth di almeno 5 simboli noti (misurato senza rete, su fixture versionata). | Principio V |
| LSC-3 | Dato un simbolo, il sistema restituisce le **pagine Markdown** che lo menzionano, con recall **≥ 80%** sullo stesso ground-truth. | Principio V |
| LSC-4 | I quattro tool storici `find_symbol` / `who_calls` / `related_docs` / `get_context` sono **registrati nel server MCP** (`src/sertor_mcp/server.py`) e invocabili dal client MCP senza modifiche alla configurazione. | CS-2 epica |
| LSC-5 | Il motore a grafo funziona **senza vector store e senza embeddings**: il grafo si costruisce e si interroga con nessuna dipendenza da provider cloud. | REQ-E2 epica, Principio II |
| LSC-6 | La costruzione del grafo è **idempotente**: rieseguita sullo stesso corpus, produce lo stesso grafo (stessi nodi, stessi archi). | Principio VI |
| LSC-7 | Il motore a grafo funziona su **qualunque corpus** indicizzato col nucleo sertor (non solo il corpus sertor): host-agnostico, nessuna assunzione sulla struttura del progetto ospite. | Principio X |
| LSC-8 | I test del grafo **passano senza rete** su una fixture versionata (corpus sintetico con simboli, chiamate e menzioni doc noti). | Principio V |

---

## 3. Stakeholder e attori

| Attore | Ruolo |
|--------|-------|
| **Agente LLM (Claude Code / client MCP)** | Principale beneficiario: `find_symbol`/`who_calls`/`related_docs`/`get_context` diventano strumenti di navigazione strutturale del codice, complementari a `search_code`/`search_docs`. |
| **Owner/maintainer** | Costruisce il grafo; verifica il ground-truth; usa i tool per navigare codebase sconosciute. |
| **Server MCP `sertor-rag`** (`src/sertor_mcp/`) | Consumatore diretto: registra i 4 nuovi tool delegando al servizio di grafo del core. |
| **CLI `sertor-rag`** | Consumatore potenziale: può esporre sottocomandi di navigazione del grafo. |
| **`sertor-core` (dipendenza a monte)** | Nucleo su cui il servizio di grafo si appoggia (chunking, ingestion, Settings, composition root). |
| **Codebase target** | Il corpus su cui il grafo viene costruito; non presupposta nella struttura (Principio X). |

---

## 4. Ambito

### In ambito

- **Code-graph strutturale** costruito da analisi AST del corpus: nodi `module`, `class`,
  `function`, `method`, `doc`; archi `contains`, `calls`, `imports`, `inherits`, `mentions`
  (doc↔simbolo per menzione del nome). Riferimento: `prototype/03-graphrag/build_graph.py`.
- **Costruzione del grafo integrata nell'indicizzazione** (DA-2 risolta: `index()` produce
  anche il grafo, come già il sidecar lessicale di FEAT-004): il grafo è un artefatto derivato
  dal corpus, persistito nella directory indici namespaced, mai stantio rispetto all'indice.
- **Persistenza del grafo su disco** nella directory indici namespaced (stessa `index_dir`
  del vector store, stesso namespace corpus+provider o corpus-only dato che il grafo non
  dipende dagli embedding): il grafo deve sopravvivere al riavvio del server MCP.
- **Quattro operazioni di navigazione strutturale** (il catalogo storico dei tool MCP):
  - `find_symbol(name)` — definizioni del simbolo (path, numero di riga, kind);
  - `who_calls(name)` — chiamanti diretti;
  - `related_docs(name)` — documenti Markdown che menzionano il simbolo;
  - `get_context(name)` — fusione multi-hop (definizione + classi base + chiamanti +
    chiamate uscenti + doc collegati): il tool più ricco.
- **Riuso dei metadati sintattico già prodotti dal chunker** (`qualname`, `symbol`,
  `node_type`, `start_line`, `end_line` in `ChunkMetadata`, `src/sertor_core/domain/entities.py`)
  come fonte privilegiata per popolare i nodi del grafo, evitando un secondo passaggio di
  parsing.
- **Tutti i 10 linguaggi del chunker sintattico** (DA-3 risolta, decisione utente — diversa
  dalla raccomandazione Python-only): nodi e archi `contains` sono language-agnostic (dai
  metadati del chunker); gli archi relazionali (`calls`/`imports`/`inherits`) sono best-effort
  per-linguaggio, con copertura del ground-truth stratificata (vedi REQ-003).
- **Porta `CodeGraph`** nel domain (`src/sertor_core/domain/ports.py`): astrazione delle
  operazioni di navigazione strutturale; l'implementazione concreta vive in `adapters/`.
- **Registrazione dei 4 tool nel server MCP** (`src/sertor_mcp/server.py`): superfici sottili
  che delegano al servizio di grafo del core, coerenti con il pattern thin-consumer.
- **Ground-truth set** sul corpus sertor (almeno 5 simboli noti con definizioni/chiamanti/doc
  attesi), verificabile senza rete, come fixture versionata.
- **Log strutturati** per le operazioni di grafo (costruzione e navigazione), coerenti col
  pattern `log_event` esistente (Principio IX).

### Fuori ambito

- **Microsoft GraphRAG / Knowledge Graph LLM** (famiglia b): extraction di grafi da testo
  via LLM, community summaries, dipendenza `graphrag` — fuori ambito per questa feature
  (ambienti isolati, costi LLM, non richiesto dal prototipo né dai tool storici).
- **Modifica della superficie pubblica della `RetrievalFacade`**: i tool di grafo non sono
  retrieval per similarità e non passano dalla facade esistente; convivono come servizio
  distinto.
- **Estrazione di archi da commenti/docstring** (analisi semantica del testo dei commenti):
  l'arco `mentions` è basato su tokenizzazione del testo dei doc, non su analisi semantica.
- **Motore agentico** (FEAT-006) e integrazione RAG-grafo ibrida multi-hop (retrieval
  vettoriale + navigazione grafo in un'unica query): fuori ambito qui.
- **GUI/web**.
- **Distribuzione del pacchetto** (epica sertor-cli).
- **Navigazione multi-repo** (il grafo copre un corpus alla volta).

---

## 5. Requisiti funzionali (EARS)

### Gruppo A — Costruzione del grafo

**REQ-001 (Event-driven)** *When the graph engine builds the graph for a corpus, the system
shall extract at minimum the following node types: `module` (each source file), `class`,
`function`, `method`, and `doc` (each Markdown document); and the following edge types:
`contains` (parent→child in the syntactic hierarchy), `calls` (function/method→called
symbol, best-effort intra-corpus), `imports` (module→module, best-effort intra-corpus),
`inherits` (class→base class, best-effort intra-corpus), and `mentions` (doc→symbol,
by token matching on distinctive names).*

> Ancora: `prototype/03-graphrag/build_graph.py`, funzione `build()`, righe 67–154.
> Il prototipo dimostra la struttura completa; la produzione ne è la riscrittura
> production-grade con riuso dei metadati del chunker.

**REQ-002 (Event-driven)** *When the graph engine builds the graph, the system shall reuse
the syntactic metadata already produced by the code chunker (`qualname`, `symbol`,
`node_type`, `start_line`, `end_line` from `ChunkMetadata`,
`src/sertor_core/domain/entities.py:50-67`) to populate graph nodes, avoiding a second
full re-parse of source files.*

> Principio III (DRY): il chunker sintattico tree-sitter è già nel core e produce esattamente
> i metadati necessari per i nodi. Un secondo parsing sarebbe duplicazione e un rischio di
> inconsistenza.

**REQ-003 (Ubiquitous)** *The system shall build the graph for ALL 10 languages supported
by the code chunker (`src/sertor_core/services/chunking/code.py:21-32`): node extraction and
`contains` edges shall be language-agnostic (derived from the chunker's syntactic metadata);
relational edges (`calls`/`imports`/`inherits`) shall be extracted per-language on a
best-effort basis, and the per-language coverage actually achieved shall be DECLARED
(documented per language), never silently absent.*

> DA-3 risolta (2026-06-12, decisione utente — diversa dalla raccomandazione Python-only):
> tutti i 10 linguaggi in ambito al MVP. **Implicazioni esplicitate:** l'estrazione degli archi
> relazionali ha pattern per-linguaggio (R-1 amplificato); il ground-truth (REQ-040) copre
> Python in profondità + almeno un caso per ciascuno degli altri linguaggi per gli archi
> dichiarati supportati. La mitigazione architetturale: nodi/contains gratis per tutti via
> metadati chunker; gli archi per-linguaggio si stratificano senza nuova infrastruttura.

**REQ-004 (Ubiquitous)** *The system shall resolve `calls` and `imports` edges intra-corpus
only (best-effort by name): if a symbol name is ambiguous (matches more than a configurable
threshold of candidate nodes), the edge shall be omitted rather than generating spurious
connections.*

> Ancora: `prototype/03-graphrag/build_graph.py:122-126` — `if len(tgts) <= 2` filtra i
> simboli troppo ambigui. Il threshold è configurabile (Principio VIII).

**REQ-005 (Event-driven)** *When the graph engine builds the graph, the system shall
persist the graph to the namespaced index directory (same `index_dir` as the vector store,
namespaced by corpus), so that the graph survives server restart and does not need to be
rebuilt on each MCP server start.*

> Principio VI (idempotenza) + impatto pratico: il server MCP gira per sessione, non per
> query; il grafo non deve essere un artefatto in-memory fugace.

**REQ-006 (Event-driven)** *When the corpus is indexed (`build_indexer().index()`), the
system shall build the graph in the same pass, together with the vector index and the
lexical sidecar, so that the graph is never stale with respect to the indexed corpus; a
standalone graph-rebuild path MAY additionally exist (design detail), but the integrated
build is the default behaviour.*

> DA-2 risolta (2026-06-12): **costruzione integrata in `index()`** — stessa scelta del
> sidecar lessicale di FEAT-004, motivata dall'essenza del progetto (contesto dell'agente
> sempre reale: un comando solo tiene freschi RAG e grafo; un passo separato introduce il
> rischio di grafo stantio, R-2). Il build AST è locale e senza cloud: il costo marginale
> è accettabile (misura empirica nel dogfood).

**REQ-007 (Unwanted behaviour)** *If the graph for a collection is absent when a graph
query is issued, then the system shall raise an explicit, actionable error (stating that
the graph must be built before querying), not return a silently empty result.*

> Principio IV: errore esplicito, coerente con la policy strict dei motori (`IndexNotFoundError`
> in `BaselineEngine.ensure_index`, `src/sertor_core/engines/baseline.py:54-62`).

**REQ-008 (Ubiquitous)** *Rebuilding the graph on the same unchanged corpus shall produce
the same set of nodes and edges (idempotence): same node identifiers, same edge types,
same connectivity.*

> Principio VI. L'idempotenza è fondamentale per la riproducibilità dei test e per
> evitare drift tra sessioni di indicizzazione.

### Gruppo B — Porta `CodeGraph` e architettura

**REQ-010 (Ubiquitous)** *The system shall expose a `CodeGraph` port (Protocol) in
`src/sertor_core/domain/ports.py` defining at minimum the following operations:
`build(corpus_root)`, `find_symbol(name)`, `who_calls(name)`, `related_docs(name)`,
`get_context(name)`, and `exists()`.*

> Principio I e II: il domain non dipende dalla libreria di grafi concreta; l'adapter
> implementa la porta. Structural typing (Protocol) già usato per le altre 4 porte
> (`EmbeddingProvider`, `VectorStore`, `LexicalIndex`, `Reranker`).

**REQ-011 (Ubiquitous)** *The concrete graph implementation shall live in a dedicated
adapter under `src/sertor_core/adapters/` and shall be wired exclusively in
`src/sertor_core/composition.py`; no service, facade, or engine shall import the
concrete implementation directly.*

> Principio I: wiring solo nel composition root. Pattern già applicato per tutti gli
> adapter esistenti (`composition.py`).

**REQ-012 (Ubiquitous)** *The graph adapter dependency (e.g. networkx) shall be isolatable
as a separately installable extra, so that the base `sertor-core` package is importable
without the graph extra installed.*

> Principio III: dipendenze pesanti isolabili. Il pattern è già applicato per `rerank`
> (FlashRank, REQ-021 di FEAT-004) e `azure` (lazy import in `composition.py`).

**REQ-013 (Ubiquitous)** *The graph service shall be exposed as an independent service
in the composition root, NOT as a value of `SERTOR_ENGINE`; the graph provides structural
navigation, not similarity retrieval, and is complementary to — not a replacement for —
the baseline and hybrid engines.*

> Decisione di modellazione chiave (vedi §10, DA-1): il grafo non sostituisce il retrieval
> per similarità, lo affianca. `SERTOR_ENGINE` è la manopola dei motori di retrieval;
> il grafo è una capacità di navigazione strutturale distinta, esposta direttamente nel
> composition root come `build_graph_service()`.

### Gruppo C — Navigazione strutturale

**REQ-020 (Event-driven)** *When `find_symbol(name)` is called, the system shall return
all nodes in the graph whose `name` attribute matches exactly, filtered to symbol kinds
(`class`, `function`, `method`), each with at minimum: path (relative to corpus root),
line number, kind (`class`/`function`/`method`), and qualified name.*

> Ancora: `prototype/03-graphrag/graph_query.py:46-48` — `CodeGraph.definitions()`.

**REQ-021 (Event-driven)** *When `who_calls(name)` is called, the system shall return
all nodes that have an outgoing `calls` edge targeting any node whose `name` matches,
each with path, line number, kind, and qualified name.*

> Ancora: `prototype/03-graphrag/graph_query.py:49-53` — `CodeGraph.callers()`.

**REQ-022 (Event-driven)** *When `related_docs(name)` is called, the system shall return
all `doc` nodes that have an outgoing `mentions` edge targeting any node whose `name`
matches, each with path and the matching symbol's qualified name.*

> Ancora: `prototype/03-graphrag/graph_query.py:61-65` — `CodeGraph.related_docs()`.

**REQ-023 (Event-driven)** *When `get_context(name)` is called, the system shall return a
multi-hop context bundle containing: definitions (REQ-020), direct callers (REQ-021),
direct callees (functions/methods called by the symbol), base classes (for class symbols),
and related docs (REQ-022); each section bounded to a configurable maximum of results
(default: 10 for definitions, 8 for callers/callees, 8 for docs) to avoid unbounded
responses.*

> Ancora: `prototype/03-graphrag/graph_query.py:98-108` — modalità `context`. I limiti
> per sezione sono configurabili (Principio VIII); il default coincide con quello del
> prototipo.

**REQ-024 (Unwanted behaviour)** *If a symbol name passed to any navigation operation is
not found in the graph, then the system shall return an explicit empty result (not raise
an exception), and the caller shall be able to distinguish "symbol absent from graph" from
"graph not built" (REQ-007).*

> Policy tollerante per l'assenza del simbolo (non è un errore di stato del sistema, è
> una query senza risultati), policy strict per l'assenza del grafo. Simile alla policy
> tollerante della `RetrievalFacade` (indice mancante → `[]` + warning) vs policy strict
> del `BaselineEngine` (indice mancante → `IndexNotFoundError`).

**REQ-025 (Ubiquitous)** *Each node returned by any navigation operation shall include a
`chunk_id`-compatible reference (in `path#symbol` or `path:lineno` format) so that results
are citeable in the same format used by the MCP server (`path#chunk`).*

> Coerenza con il formato citabile già stabilito in `src/sertor_mcp/server.py:48-57`
> (`_fmt` → `{path, source, chunk, score, preview}`). Il grafo non ha score di similarità;
> il campo `score` è assente o costante per i risultati strutturali.

### Gruppo D — Integrazione nel server MCP

**REQ-030 (Event-driven)** *When the MCP server starts, the system shall register the
four graph tools (`find_symbol`, `who_calls`, `related_docs`, `get_context`) alongside the
existing three search tools (`search_code`, `search_docs`, `search_combined`), without
modifying the interface or behavior of the existing tools.*

> Non-breaking: i consumatori esistenti continuano a usare i 3 tool attuali invariati.
> Il server MCP è un thin-consumer (Principio I).

**REQ-031 (Ubiquitous)** *Each graph tool in the MCP server shall delegate exclusively to
the graph service of the core; no graph logic shall be reimplemented in the server module.*

> Coerente col pattern thin-consumer già documentato in `src/sertor_mcp/server.py:1-14`.

**REQ-032 (Unwanted behaviour)** *If the graph has not been built for the current corpus
when a graph tool is invoked, then the MCP server shall return a structured error response
(not crash), with a message indicating that the graph must be built.*

> Principio IV: gli errori di stato sono espliciti e azionabili, anche sulla superficie MCP.

**REQ-033 (Ubiquitous)** *The graph service shall be constructed in the composition root
(`src/sertor_core/composition.py`) via a dedicated `build_graph_service()` function, and
its dependency (the graph library extra) shall be imported lazily inside that function.*

> Pattern già consolidato: import lazy in `composition.py` per ogni extra pesante
> (azure, rerank). Principio III.

### Gruppo E — Misura della qualità e ground-truth

**REQ-040 (Ubiquitous)** *The system shall include a ground-truth set for the sertor corpus
containing at least 5 symbol entries, each specifying: symbol name, expected definition
path(s) and line range, expected callers (at least one), and expected related doc paths
(at least one where applicable); this set shall be a versioned fixture in the test suite.*

> Principio V: una feature senza misura non è fatta. Il set minimo di 5 simboli è
> sufficiente per validare le tre operazioni principali; si sceglie un sottoinsieme ovvio
> (es. `EmbeddingProvider`, `build_facade`, `RetrievalFacade`, `BaselineEngine`, `code_chunks`).

**REQ-041 (Event-driven)** *When the graph tests run on the ground-truth set, the system
shall verify for each symbol: (a) `find_symbol` returns the expected path and line range;
(b) `who_calls` includes all expected callers; (c) `related_docs` includes all expected doc
paths where applicable; all assertions shall pass without network access.*

> Test senza rete, Principio V. La suite di test è l'acceptance gate: LSC-2 e LSC-3
> (≥ 80% precisione/recall) si esprimono concretamente su questo set.

**REQ-042 (Ubiquitous)** *The ground-truth set shall use relative paths (not absolute)
and shall not encode assumptions about the internal structure of the sertor project beyond
what is directly verifiable in the corpus.*

> Principio X: l'host-agnosticità vale anche per le fixture di test.

### Gruppo F — Osservabilità

**REQ-050 (Event-driven)** *When the graph is built, the system shall emit a structured
log event recording at minimum: corpus, graph_path, node_count (by kind), edge_count (by
type), elapsed_ms.*

**REQ-051 (Event-driven)** *When a graph navigation operation is executed, the system
shall emit a structured log event recording at minimum: operation name, symbol queried,
result_count, elapsed_ms.*

**REQ-052 (Ubiquitous)** *Log records shall never contain secret values; redaction follows
the existing `log_event` pattern (`src/sertor_core/observability/logging.py`).*

### Gruppo G — Retro-compatibilità e non-distruttività

**REQ-060 (Ubiquitous)** *The introduction of the graph service shall not modify the
interfaces of `BaselineEngine`, `HybridEngine`, `RetrievalFacade`, or any existing port;
the graph port (`CodeGraph`) is additive.*

**REQ-061 (Ubiquitous)** *The graph service shall be non-destructive on the target
repository: it shall not modify user source files; the persisted graph shall be stored
in the namespaced index directory (e.g. `.index/`), consistent with the vector and lexical
indexes.*

**REQ-062 (Ubiquitous)** *Setting `SERTOR_ENGINE=baseline` or `SERTOR_ENGINE=hybrid` shall
produce behavior identical to the current system for all existing consumers; the graph
service is orthogonal to the engine selection.*

---

## 6. Requisiti non funzionali

| ID | Categoria | Requisito |
|----|-----------|-----------|
| NFR-01 | **Dipendenze verso l'interno** (Principio I) | Il servizio di grafo dipende solo dalle porte del dominio e dalle entità (`ChunkMetadata`, `Document`); non importa SDK di librerie di grafi direttamente nei servizi. |
| NFR-02 | **Isolamento dipendenze pesanti** (Principio III) | La libreria di grafi (es. networkx) è installabile separatamente come extra `graph`; la sua assenza non impedisce l'installazione o l'uso del pacchetto base né l'uso dei motori vettoriale/ibrido. |
| NFR-03 | **Testabilità senza rete** (Principio V) | Il servizio di grafo è testabile con un corpus sintetico in-memory (fixture versionata), senza cloud, senza embeddings, senza vector store. I test passano con `pytest -m "not cloud"`. |
| NFR-04 | **Latenza di navigazione** | Una query `find_symbol` / `who_calls` / `related_docs` su un grafo in-memory di dimensioni tipiche di una codebase media (< 50.000 nodi) deve completarsi in tempo trascurabile per uso interattivo da un agente LLM (< 100 ms); `get_context` (multi-hop) può richiedere fino a 500 ms. |
| NFR-05 | **Configurabilità centralizzata** (Principio VIII) | Il threshold di ambiguità per la risoluzione degli archi `calls` (REQ-004), i limiti per sezione di `get_context` (REQ-023), e il path del grafo nella `index_dir` sono configurabili da `Settings`; nessun default hardcodato nei componenti. |
| NFR-06 | **Idempotenza e determinismo** (Principio VI) | La costruzione del grafo è idempotente (REQ-008); le operazioni di navigazione sono deterministiche (stesso input → stesso output ordinato). |
| NFR-07 | **Osservabilità** (Principio IX) | Ogni operazione di grafo (build e query) emette log strutturati sufficienti a diagnosticare un fallimento (REQ-050/051/052). |
| NFR-08 | **Host-agnosticità** (Principio X) | Il servizio di grafo non presuppone la struttura interna del progetto ospite (nessun path fisso, nessun nome di dominio hardcodato); funziona su qualsiasi corpus indicizzato col nucleo sertor. |
| NFR-09 | **Nessun cloud per le operazioni strutturali** | La costruzione e la navigazione del grafo non richiedono un provider LLM, embeddings o vector store attivi; operano interamente in locale (Principio II, REQ-E2 epica). |
| NFR-10 | **Retro-compatibilità** | Nessun consumatore esistente (facade, MCP, CLI) richiede modifiche di codice o di configurazione per continuare a funzionare dopo l'introduzione del grafo. |

---

## 7. Vincoli, assunzioni e dipendenze

### Vincoli

- **V-1**: Il servizio di grafo è **ortogonale** a `SERTOR_ENGINE`; non viene selezionato
  tramite quella manopola (Principio I, REQ-013).
- **V-2**: Il wiring del servizio di grafo avviene **solo nel composition root**
  (`src/sertor_core/composition.py`, Principio I, REQ-011).
- **V-3**: Nessun segreto su file versionati (REQ-E5 epica).
- **V-4**: Python ≥ 3.11 (vincolo d'epica).
- **V-5**: Il ground-truth set (REQ-040) è scritto come fixture nel repo con path relativi;
  non dipende da file esterni non versionati.
- **V-6**: I motori baseline e ibrido restano pienamente funzionanti (REQ-060/062).
- **V-7**: La libreria di grafi (es. networkx) è richiesta solo per il build e la lettura
  del grafo; deve essere importata in modo lazy (REQ-012/033).

### Assunzioni

- **A-1**: Il grafo in-memory ricostruito a ogni avvio del servizio (o caricato da disco se
  persistito) è sufficiente per corpus di dimensioni tipiche (< 50.000 nodi); per corpus
  molto grandi la persistenza su disco (REQ-005) è il meccanismo di ottimizzazione.
- **A-2**: La libreria di grafi di riferimento è `networkx` (leggera, usata nel prototipo,
  nessun conflitto noto con le dipendenze attuali del core); la scelta concreta è di design,
  ma il requisito di isolamento (extra lazy) vale per qualsiasi libreria scelta.
- **A-3**: La risoluzione degli archi `calls` e `imports` è **best-effort intra-corpus**:
  le chiamate a librerie esterne non generano archi nel grafo, e i simboli ambigui sono
  omessi (REQ-004). Questa approssimazione è intenzionale e coerente col prototipo.
- **A-4**: I metadati `qualname`, `symbol`, `node_type`, `start_line`, `end_line` prodotti
  dal chunker sintattico (`ChunkMetadata`) sono la fonte privilegiata per i nodi del grafo
  Python (REQ-002); per i nodi `module` (livello file) si usa il path del `Document`.
- **A-5**: Il formato di serializzazione del grafo è **JSON** (DA-4 risolta: indipendente
  dalla libreria di grafi, leggibile nei test); il requisito resta la persistenza namespaced
  e idempotente — i dettagli dello schema sono di design.
- **A-6**: Il server MCP registra i 4 tool con la stessa interfaccia del prototipo
  (`find_symbol(name)`, `who_calls(name)`, `related_docs(name)`, `get_context(name)`,
  tutti con parametro `name: str`); parametri addizionali opzionali sono di design.

### Dipendenze

- **D-1**: `sertor-core` in `master` — nucleo retrieval (FEAT-001), chunking sintattico
  (`src/sertor_core/services/chunking/code.py`), entità (`domain/entities.py` con
  `ChunkMetadata`), porte (`domain/ports.py`), `Settings` (`config/settings.py`),
  composition root (`composition.py`), `log_event` (`observability/logging.py`).
- **D-2**: Motore ibrido (FEAT-004, branch 013, appena mergiato) — in particolare la porta
  `LexicalIndex` e il pattern di sidecar nella `index_dir` come modello per il grafo.
- **D-3**: `prototype/03-graphrag/build_graph.py` e `graph_query.py` — riferimento
  funzionale per le operazioni di costruzione e navigazione; la produzione ne è la
  riscrittura production-grade.
- **D-4** (opzionale, extra): libreria di grafi (networkx o equivalente); isolabile come
  extra `graph`, import lazy nel composition root.
- **D-5**: `src/sertor_mcp/server.py` — consumatore dei 4 tool di grafo; i nuovi tool
  saranno aggiunti qui senza modificare i 3 esistenti.

---

## 8. Rischi

| ID | Rischio | Prob. | Impatto | Mitigazione |
|----|---------|-------|---------|-------------|
| R-1 | **Risoluzione archi imprecisa**: la risoluzione best-effort per nome dei `calls` produce falsi positivi (archi errati) o falsi negativi (archi mancanti) su simboli con nomi comuni. | Alta | Medio | REQ-004: threshold di ambiguità configurabile; omettere gli archi ambigui piuttosto che aggiungerne di sbagliati (conservative). Il ground-truth verifica la recall su simboli distinti (meno esposti al problema). |
| R-2 | **Grafo stale**: se il corpus viene modificato ma il grafo non viene ricostruito, la navigazione restituisce risultati non più corretti. | Media | Alto | REQ-006: rebuild congiunto con il vettoriale; REQ-007: errore esplicito se grafo assente. La policy di re-index del rituale di step (CLAUDE.md, punto 5) mitiga il rischio operativo. |
| R-3 | **Metadati chunker insufficienti per ricostruire gli archi**: il chunker produce `qualname`/`symbol` ma non estrae esplicitamente le chiamate (solo il prototipo lo faceva via `ast`). Il riuso dei metadati (REQ-002) può richiedere un secondo passaggio di analisi AST solo per gli archi `calls`/`imports`. | Media | Medio | Il requisito ammette un passaggio AST dedicato solo per gli archi relazionali; il riuso dei metadati è per i nodi. La scelta di design (riuso completo vs passaggio parziale) è di competenza della fase a valle. |
| R-4 | **Conflitti di dipendenze del grafo**: networkx (o alternativa) potrebbe avere conflitti con le dipendenze esistenti del core in alcuni ambienti. | Bassa | Medio | NFR-02: extra isolato, import lazy (REQ-012); la CI base non installa l'extra. Networkx è leggera e senza dipendenze C/Rust. |
| R-5 | **Grafo troppo grande per in-memory su corpus grandi**: per codebase con decine di migliaia di file, il grafo in-memory diventa pesante. | Bassa | Basso | NFR-04 scoping (< 50.000 nodi per MVP); la persistenza su disco (REQ-005) è il meccanismo principale. Per corpus molto grandi sarà FEAT successiva. |
| R-6 | **Violazione Principio I**: logica di costruzione o navigazione del grafo fuori dal composition root o con import concreti nel domain. | Bassa | Alto | REQ-010/011/013: vincoli espliciti; Constitution Check al momento del design. |
| R-7 | **Tool MCP di grafo appesi su Windows**: il pattern eager warm-up risolto per la facade (`src/sertor_mcp/server.py:99`) potrebbe non coprire il graph service se questo ha init bloccante. | Media | Medio | REQ-033: import lazy nel composition root; il graph service va incluso nel warm-up eager di `main()` se ha init bloccante. |

---

## 9. Prioritizzazione (MoSCoW)

| Priorità | Requisiti | Motivazione |
|----------|-----------|-------------|
| **Must** | REQ-001 (build grafo), REQ-003 (tutti i 10 linguaggi — DA-3, decisione utente), REQ-005 (persistenza), REQ-006 (build integrato in index() — DA-2), REQ-007/008 (errore esplicito + idempotenza), REQ-010/011/013 (porta + composition root + ortogonalità engine), REQ-020..024 (4 operazioni navigazione), REQ-025 (formato citabile), REQ-030..033 (MCP 4 tool), REQ-040..041 (ground-truth + test), REQ-060..062 (retro-compatibilità), NFR-01..03, NFR-06, NFR-08..10 | Il ciclo minimo dimostrabile: grafo multi-linguaggio + 4 operazioni + 4 tool MCP + test su ground-truth = la feature è "fatta" (Principio V). |
| **Should** | REQ-002 (riuso metadati chunker), REQ-004 (threshold ambiguità configurabile), REQ-012 (extra isolato), REQ-042 (robustezza ground-truth), REQ-050..052 (osservabilità), NFR-04 (latenza), NFR-05 (configurabilità threshold), NFR-07 (osservabilità) | Completano la qualità, la configurabilità e l'osservabilità; essenziali per robustezza ma non bloccanti per la dimostrazione minima. |
| **Could** | Profondità degli archi `calls`/`imports` per i linguaggi non-Python oltre la copertura best-effort dichiarata; NFR-04 misurazione empirica formalizzata | Valore incrementale; richiedono solo estensione del mapping, non nuova infrastruttura. |
| **Won't (questa feature)** | Microsoft GraphRAG / Knowledge Graph LLM, navigazione multi-repo, integrazione RAG-grafo ibrida multi-hop (FEAT-006), GUI/web, distribuzione pacchetto (epica CLI). | Fuori ambito dichiarato. |

---

## 10. Domande aperte (RISOLTE il 2026-06-12)

Tutte risolte con l'utente lo stesso giorno dell'elicitazione e codificate nei requisiti:

| # | Tema | Decisione | Codificata in |
|---|------|-----------|---------------|
| DA-1 | Modellazione del grafo | **Porta `CodeGraph` Protocol nel domain** (come raccomandato: testabilità con mock senza extra) | REQ-010 |
| DA-2 | Quando si costruisce | **Integrata in `index()`** (raccomandazione del flusso principale, DIVERSA da quella dell'analista «passo separato»: un solo comando tiene freschi RAG e grafo — mai grafo stantio, essenza «contesto agente sempre reale»; stesso pattern del sidecar lessicale 013) | REQ-006, §4 |
| DA-3 | Linguaggi al MVP | **Tutti i 10 linguaggi del chunker** (decisione utente, DIVERSA dalla raccomandazione Python-only; implicazioni esplicitate: archi relazionali per-linguaggio best-effort con copertura DICHIARATA, ground-truth stratificato, R-1 amplificato) | REQ-003, §4, MoSCoW |
| DA-4 | Formato serializzazione | **JSON** (delegata al design dal flusso principale, come raccomandato: indipendente dalla libreria, leggibile nei test) | A-5 |
| DA-5 | Tool MCP senza extra | **Errore esplicito e azionabile alla chiamata** (come raccomandato: Principio IV, pattern REQ-022 di FEAT-004) | REQ-032 |

Il dettaglio originale delle opzioni valutate resta sotto, per tracciabilità.

---

### DA-1 — Modellazione del servizio di grafo: porta del domain o servizio standalone?

**Contesto.** Attualmente il domain (`src/sertor_core/domain/ports.py`) espone 5 porte
(Protocol) che definiscono i boundary verso i provider concreti: `EmbeddingProvider`,
`VectorStore`, `LexicalIndex`, `Reranker`, `RetrieverStrategy`. REQ-010 propone di
aggiungere una porta `CodeGraph`. Tuttavia il grafo è diverso dalle porte esistenti:
non è un provider intercambiabile con diverse implementazioni in uso contemporaneo
(locale/cloud), ma un servizio con un'unica implementazione ragionevole (una libreria
di grafi leggera). Due opzioni:

- **Opzione A — Porta `CodeGraph` nel domain (come REQ-010)**: il grafo è un'astrazione
  di dominio; l'implementazione concreta (networkx, igraph, …) vive nell'adapter. Il
  consumatore (server MCP, composition root) dipende dalla porta, non dall'implementazione.
  - Pro: coerente con il pattern del domain; facilità di mocking nei test unitari senza
    libreria di grafi installata; apre la porta a implementazioni alternative (Neo4j in
    futuro) senza cambiare il domain.
  - Contro: aggiunge un'astrazione che potrebbe non avere mai una seconda implementazione
    (YAGNI, Principio III).
- **Opzione B — Classe concreta nel servizio di grafo, senza porta Protocol**: il grafo
  è un servizio leaf (una sola implementazione ragionevole); si mette direttamente in
  `src/sertor_core/adapters/graph/` e si usa direttamente nel composition root.
  - Pro: meno astrazione; Principio III (nessuna astrazione senza evidenza di necessità).
  - Contro: il test unitario richiede networkx installato; nessuna intercambiabilità futura
    senza refactor.

**Raccomandazione**: **Opzione A (porta Protocol)**. Il beneficio principale non è
l'intercambiabilità futura ma la **testabilità unitaria** senza dipendenze (il pattern già
stabilito per `LexicalIndex` e `Reranker`): i test unitari delle operazioni MCP possono
usare un `FakeCodeGraph` in-memory senza installare l'extra `graph`. Il costo è minimo
(un Protocol di 6 metodi). Principio III è soddisfatto perché la evidenza è quella stessa
testabilità, che è esplicitamente richiesta da NFR-03.

---

### DA-2 — Costruzione del grafo: integrata nell'indicizzazione o comando separato?

**Contesto.** Il grafo è un artefatto derivato dal corpus, come l'indice lessicale (FEAT-004).
Il sidecar BM25 viene ricostruito automaticamente quando `build_indexer().index()` gira
(REQ-003 di FEAT-004). Due opzioni analoghe per il grafo:

- **Opzione A — Costruzione integrata**: `build_indexer().index(root)` costruisce anche
  il grafo (come il sidecar BM25). Il grafo è sempre coerente con l'indice.
  - Pro: zero attrito per l'utente; nessun comando separato da ricordare; il grafo è
    sempre disponibile dopo un `index`.
  - Contro: aggiunge latenza all'operazione di indicizzazione (analisi AST del corpus);
    accoppia due artefatti con cicli di vita potenzialmente diversi.
- **Opzione B — Passo separato** (es. `sertor-rag graph-build .` o API dedicata): la
  costruzione del grafo è un'operazione distinta, da lanciare esplicitamente.
  - Pro: separazione dei concern; l'utente che non usa i tool di grafo non paga il costo;
    il ciclo di vita del grafo è indipendente dall'indice vettoriale.
  - Contro: attrito: l'utente deve ricordarsi di lanciare il build del grafo; il grafo
    può andare stale rispetto all'indice.

**Raccomandazione**: **Opzione B (passo separato)** con una chiara linea guida operativa.
Il prototipo usava un comando separato (`python 03-graphrag/build_graph.py`) e il pattern
è già noto. Principio VI (install ≠ run): il build del grafo è un'operazione esplicita,
non un side-effect dell'indicizzazione. La latenza dell'analisi AST può essere significativa
su corpus grandi. Si può introdurre un flag opt-in per la costruzione integrata in futuro.

[DA CHIARIRE: la separazione (Opzione B) è preferita, ma se l'utente preferisce il costo
zero di configurazione dell'Opzione A (sempre coerente senza passi extra), si può scegliere
A. La decisione impatta il piano di implementazione.]

---

### DA-3 — Multi-linguaggio al MVP: Python only o subset dei 10 linguaggi?

**Contesto.** Il chunker sintattico supporta 10 linguaggi (`src/sertor_core/services/chunking/
code.py:21-32`). Il prototipo usava `ast` di Python (solo Python). REQ-003 propone Python
come Must e gli altri come Could. Tre alternative:

- **Opzione A — Python only (Must, altri Could)**: come REQ-003. Semplice, testabile,
  sufficiente per il dogfooding (Sertor stesso è Python).
  - Pro: nessuna dipendenza su grammatiche aggiuntive; ground-truth più semplice.
  - Contro: limita il valore per repo multi-linguaggio.
- **Opzione B — Python + JavaScript/TypeScript (Must)**: i due linguaggi più diffusi
  nei repo open source.
  - Pro: copre la grande maggioranza dei casi d'uso reali.
  - Contro: richiede validazione delle grammatiche tree-sitter per l'estrazione degli archi
    `calls` in JS/TS (più complessa di Python per callback/arrow functions).
- **Opzione C — Tutti i 10 linguaggi del chunker (Must)**: massima copertura.
  - Pro: parità con il chunker.
  - Contro: alto rischio di archi `calls` imprecisi su linguaggi non testati; ground-truth
    richiesto per ogni linguaggio.

**Raccomandazione**: **Opzione A (Python only al MVP)**. Il valore del grafo per il
dogfooding è immediato; l'estensione agli altri linguaggi è incrementale (stessa
infrastruttura, nuovo mapping). Il rischio R-1 (archi imprecisi) è già presente per Python:
estendere prima di validare Python aumenterebbe la superficie di errore.

---

### DA-4 — Formato di serializzazione del grafo su disco: GraphML, JSON-lines, o altro?

**Contesto.** REQ-005 richiede la persistenza del grafo nella `index_dir` namespaced.
Il prototipo usava GraphML (`nx.write_graphml`). Tre opzioni:

- **Opzione A — GraphML** (prototipo): formato standard, leggibile, supportato da networkx.
  - Pro: interoperabile con altri strumenti di visualizzazione (Gephi, yEd).
  - Contro: verboso (XML); lettura più lenta di formati binari su grafi grandi.
- **Opzione B — JSON-lines o JSON** (nodi + archi separati): leggibile, indipendente da
  networkx per la lettura (facilitie il mock dei test).
  - Pro: nessuna dipendenza da networkx per caricare il grafo in test; più leggero di XML.
  - Contro: non interoperabile con strumenti di visualizzazione di grafi.
- **Opzione C — Formato binario pickle/msgpack**: veloce, compatto.
  - Pro: latenza di load minima su grafi grandi.
  - Contro: non leggibile; dipendente dalla versione Python/networkx; non raccomandato per
    artefatti persistiti (sicurezza del pickle).

**Raccomandazione**: **Opzione B (JSON)** per indipendenza dalla libreria e leggibilità dei
test. Il formato è un dettaglio di design; l'importante è che sia namespaced, idempotente
e non dipenda da un formato binario fragile. La scelta definitiva è di competenza del design.

[DA CHIARIRE: nessuna preferenza forte; la decisione può essere delegata alla fase di
design.]

---

### DA-5 — Comportamento del server MCP se l'extra `graph` non è installato

**Contesto.** REQ-012 richiede che la libreria di grafi sia un extra isolato. Se l'extra
non è installato e il client MCP chiama `find_symbol`, il server deve rispondere. Due opzioni:

- **Opzione A — Errore esplicito e azionabile**: il tool risponde con un messaggio di
  errore che indica l'extra mancante e il comando per installarlo.
  - Pro: coerente con Principio IV e il pattern del reranker (REQ-022 di FEAT-004).
  - Contro: il client MCP deve gestire un errore di tool; potenziale confusione se il
    client non si aspettava un errore di configurazione.
- **Opzione B — Tool non registrati se extra assente**: se l'extra non è installato, i
  4 tool di grafo non vengono registrati nel server MCP (il server parte con soli 3 tool).
  - Pro: nessun errore a runtime; il client sa che i tool non esistono (non li vede nel
    catalogo).
  - Contro: il comportamento del server cambia a seconda dell'extra; possibile confusione
    per l'agente LLM.

**Raccomandazione**: **Opzione A (errore esplicito)**. Coerente con il pattern della
costituzione (Principio IV) e con REQ-022 di FEAT-004. L'errore è azionabile: il messaggio
dice all'agente/utente cosa fare. L'Opzione B richiede una logica di registrazione
condizionale nel server che complicherebbe il bootstrap.

