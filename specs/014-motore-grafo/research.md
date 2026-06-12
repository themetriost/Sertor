# Research — Motore RAG a grafo / code-graph strutturale (014)

**Input**: `spec.md` (31 FR), fonte EARS `requirements/sertor-core/motore-grafo/requirements.md`
(DA-1..DA-5 risolte), prototipo `prototype/03-graphrag/` (`build_graph.py`, `graph_query.py` —
letti direttamente), chunker sintattico (`services/chunking/code.py`), pattern della 013
(sidecar namespaced, porte, composition, warm-up MCP della PR #23).

Nessun NEEDS CLARIFICATION residuo. Decisioni di design G1..G10.

---

## G1 — Estrazione SEPARATA dalla persistenza: il build del grafo non richiede l'extra

**Decision**: l'estrazione (corpus → nodi/archi) è un **servizio puro** del core
(`services/graph_extraction.py`, usa tree-sitter che è GIÀ dipendenza base del chunking);
la persistenza è un **JSON** scritto dall'adapter senza bisogno della libreria di grafi.
**networkx serve SOLO alla navigazione** (caricamento+traversal) ed è importato pigramente
nei metodi di query dell'adapter.

**Rationale**: scioglie elegantemente la tensione tra «build integrato in `index()`» (DA-2) e
«extra isolato» (REQ-012): `index()` produce SEMPRE l'artefatto grafo (nessun caso di
degradazione al build), e l'errore esplicito DA-5 scatta solo dove serve davvero — alla
**query** senza extra (`ConfigError` azionabile, pattern REQ-022 della 013).

**Alternatives considered**: adapter dict-only senza networkx (le 4 operazioni non richiedono
algoritmi di grafo): scartato — i requirements fissano networkx come riferimento (A-2, DA-5
deciso su quel presupposto) e i traversal futuri (cammini, comunità) ne beneficeranno; il costo
è minimo e isolato nell'extra `graph`.

## G2 — Nodi dai metadati del chunker; archi da un passaggio tree-sitter dedicato

**Decision**: i **nodi** simbolo (`class`/`function`/`method`) derivano dai chunk già prodotti
(`symbol`, `qualname`, `node_type`, `start_line`, `path` — REQ-002); i nodi `module` dai
`Document` di codice, i nodi `doc` dai `Document` Markdown. Gli **archi `contains`** derivano
dalla gerarchia dei `qualname` (language-agnostic: `Classe.metodo` → `Classe` contains
`metodo`; modulo → simboli top-level). Gli **archi relazionali** (`calls`/`imports`/`inherits`)
richiedono un passaggio tree-sitter dedicato sul testo dei `Document` (i chunk sono spezzati e
non bastano — rischio R-3 confermato), guidato da una **mappa di relazione per-linguaggio**.

**Rationale**: REQ-002 (DRY sui nodi) + onestà sul limite dei metadati (il chunker non estrae
chiamate). tree-sitter è già in base: nessuna dipendenza nuova per l'estrazione.

## G3 — Tutti i 10 linguaggi con mappa di copertura DICHIARATA (`COVERAGE`)

**Decision**: la mappa `_REL: lang → {call_nodes, import_nodes, inherit_strategy}` in
`graph_extraction.py` è la **fonte unica della copertura**: i linguaggi vi dichiarano i tipi di
nodo tree-sitter per chiamate/import/ereditarietà. Una costante esportata `COVERAGE`
(lang → set di edge-type supportati) alimenta documentazione e test. Tutti i 10 linguaggi hanno
nodi+`contains` (gratis da G2); al MVP la mappa relazionale dichiara: **python** (calls,
imports, inherits — parità col prototipo), e per gli altri 9 i `calls` via i node-type di
invocazione standard delle grammatiche (`call`, `call_expression`, `method_invocation`,
`invocation_expression`, `function_call_expression`…), con `imports`/`inherits` dichiarati solo
dove il node-type è validato dal ground-truth per-linguaggio (FR-003). Ciò che non è in mappa
NON esiste in modo dichiarato, mai silenzioso.

**Rationale**: attua la decisione utente DA-3 (tutti i 10) con la stratificazione esplicitata
in REQ-003: l'infrastruttura è unica, la profondità per-linguaggio è un dato dichiarato e
testato (un caso di ground-truth per linguaggio/relazione dichiarata), estendibile per
configurazione della mappa senza nuova architettura.

## G4 — Porta `CodeGraph` (settima porta) e adapter `networkx`

**Decision**: porta Protocol in `domain/ports.py` (DA-1):
`build(corpus, data)` · `find_symbol(name)` · `who_calls(name)` · `related_docs(name)` ·
`get_context(name)` · `exists(corpus)` · `reset(corpus)`. Adapter
`adapters/graph/networkx_graph.py` (`NetworkxCodeGraph`): `build` scrive il JSON atomico
(tmp+rename, formato `sertor.graph/1`), le query caricano pigramente il JSON in un
`nx.DiGraph` + indici per nome (cache per corpus, invalidata da build/reset).

**Rationale**: testabilità con `FakeCodeGraph` (NFR-03); stesso stile di `Bm25LexicalIndex`
(013): sidecar atomico versionato, cache, errore esplicito su formato sconosciuto.

## G5 — Namespacing per SOLO corpus (non per provider)

**Decision**: il grafo vive in `<index_dir>/graph/<corpus>.json` — namespace per **corpus**,
senza provider.

**Rationale**: il grafo non dipende dagli embeddings (LSC-5): legarlo al provider costringerebbe
a ricostruirlo per ogni provider senza alcuna differenza di contenuto. Differenza deliberata
rispetto a collezioni vettoriali e sidecar lessicale (che dipendono dal provider).

## G6 — Build integrato: sink opzionale in `IndexingService` (pattern 013)

**Decision**: `IndexingService` acquisisce il parametro opzionale `graph: CodeGraph | None` e
una dipendenza dal servizio di estrazione: dopo l'upsert vettoriale (e il sidecar lessicale),
estrae nodi/archi dagli stessi `documents`/`chunks` e chiama `graph.build()` (snapshot intero,
idempotente). `build_indexer()` lo cabla quando `Settings.graph_enabled` (default True).
Con corpus vuoto in rebuild: `graph.build(corpus, vuoto)` (specchio).

**Rationale**: DA-2 (mai grafo stantio), REQ-006; identico al sink lessicale (semantica
specchio, niente flussi parziali). L'estrazione è pura e locale: costo marginale accettabile,
misurato dal log `graph_build` (elapsed_ms) nel dogfood.

## G7 — Servizio esposto: `build_graph_service()` ortogonale a `SERTOR_ENGINE`

**Decision**: factory dedicata nel composition root che restituisce l'adapter configurato
(corpus da Settings); NESSUN coinvolgimento di `SERTOR_ENGINE` (REQ-013/FR-012). Il server MCP
la consuma memoizzata. `Settings` nuovi: `graph_enabled` (`SERTOR_GRAPH`, default True),
`graph_ambiguity_threshold` (`SERTOR_GRAPH_AMBIGUITY`, default 2 — il filtro del prototipo
`len(tgts) <= 2`), `graph_limit_definitions` (10), `graph_limit_relations` (8),
`graph_limit_docs` (8) per `get_context` (REQ-023, Principio VIII).

## G8 — Le due semantiche di assenza (FR-007/FR-017) e l'errore DA-5

**Decision**:
- grafo assente (`exists()` False) → `GraphNotFoundError` (nuova eccezione di dominio, stile
  `IndexNotFoundError`): «costruisci il grafo (index) prima di interrogare»;
- simbolo assente → risultato vuoto esplicito (liste vuote nel bundle), MAI eccezione;
- extra `graph` mancante alla query → `ConfigError` azionabile («uv add "sertor-core[graph]"»)
  sollevata dall'import pigro nei metodi di query (DA-5);
- nel server MCP gli errori diventano risposte strutturate (FastMCP propaga l'eccezione come
  tool error — pattern esistente: gli errori reali NON vengono inghiottiti).

## G9 — Server MCP: 4 tool sottili + warm-up esteso (lezione PR #23)

**Decision**: i 4 tool delegano al servizio memoizzato (`_graph()`), formato risultati citabile
coerente con `_fmt` (`{path, line, kind, qualname, ref}` con `ref = path#qualname`); `main()`
estende il warm-up eager: oltre alla facade, **carica il grafo** (se esiste e l'extra c'è) prima
di `mcp.run()` — l'init pigro dentro la prima tool call parcheggia su Windows (diagnosi
2026-06-12, R-7). Se extra o grafo mancano, il warm-up NON fallisce (il server parte; l'errore
esplicito arriva alla chiamata del tool, DA-5).

## G10 — Ground-truth strutturale a due strati

**Decision**:
1. **Strato corpus reale (Python)**: fixture `tests/fixtures/graph_ground_truth.py` con ≥5
   simboli di `src/sertor_core/` (es. `build_facade` ← chiamato da `_facade` del server MCP e
   dalla CLI; `RetrievalFacade`; `log_event` ← chiamanti multipli; `IndexingService`;
   `collection_name`), ciascuno con definizione attesa (path+righe), chiamanti attesi, doc
   attesi; misura precisione ≥80% / recall ≥80% (LSC-2/3), senza rete.
2. **Strato per-linguaggio (sintetico)**: mini-corpus versionato
   `tests/fixtures/graph_corpus/` (un file minimo per ciascuno dei 10 linguaggi con una
   chiamata/import noti) che verifica ESATTAMENTE ciò che `COVERAGE` dichiara (FR-003): se la
   mappa dichiara `calls` per `go`, il test del file Go DEVE trovare quell'arco.

**Rationale**: REQ-040..042 + l'onestà della scelta DA-3: la copertura dichiarata è verificata,
non promessa.

## Note minori

- **Token distintivi per `mentions`**: euristica del prototipo (nome ≥5 char, o camelCase, o
  underscore) — costante nel servizio di estrazione, documentata; non configurabile al MVP
  (YAGNI; diventa knob se emergono falsi positivi).
- **Formato JSON `sertor.graph/1`**: `{format, corpus, coverage, nodes[], edges[]}` — schema in
  data-model.md; scrittura atomica; formato sconosciuto → `ConfigError`.
- **`get_context` su nome di classe**: include `inherits` uscenti (basi) come il prototipo;
  per i non-class la sezione è vuota.
