# Data Model — Motore RAG a grafo (014)

Entità e contratti dati. Le entità e porte esistenti **non cambiano** (FR-029): tutto è additivo.

## Entità di dominio nuove (`domain/entities.py`)

| Entità | Campi | Note |
|---|---|---|
| `GraphNode` (frozen) | `id: str`, `kind: str` (module/class/function/method/doc), `name: str`, `path: str`, `line: int \| None`, `qualname: str \| None` | `id` stabile: `path` per module/doc, `path::qualname` per i simboli (pattern del prototipo) → idempotenza (FR-008). |
| `GraphEdge` (frozen) | `source: str`, `target: str`, `type: str` (contains/calls/imports/inherits/mentions) | Riferimenti per `id` di nodo. |
| `GraphData` (frozen) | `nodes: tuple[GraphNode, ...]`, `edges: tuple[GraphEdge, ...]`, `coverage: dict[str, tuple[str, ...]]` | Output dell'estrazione, input di `CodeGraph.build`; `coverage` = la dichiarazione per-linguaggio (FR-003). |
| `SymbolHit` (frozen) | `path: str`, `line: int \| None`, `kind: str`, `qualname: str`, `ref: str` | Risultato di navigazione citabile (`ref = path#qualname`, FR-018). |
| `ContextBundle` (frozen) | `definitions`, `callers`, `callees`, `bases`, `docs` (tuple di `SymbolHit`/path doc) | Risposta di `get_context` (FR-016), sezioni limitate. |

Eccezione di dominio nuova (`domain/errors.py`): **`GraphNotFoundError`** (stile
`IndexNotFoundError`): grafo non costruito → errore esplicito azionabile (FR-007).

## Porta nuova (`domain/ports.py`)

### `CodeGraph` (Protocol) — settima porta

| Metodo | Contratto |
|---|---|
| `build(corpus: str, data: GraphData) -> None` | Sostituzione integrale, scrittura atomica (tmp+rename), idempotente. NON richiede la libreria di grafi (solo serializzazione JSON). |
| `find_symbol(name: str) -> list[SymbolHit]` | Match esatto sul nome, kinds class/function/method; vuoto se assente (FR-017). |
| `who_calls(name: str) -> list[SymbolHit]` | Nodi con arco `calls` verso il simbolo. |
| `related_docs(name: str) -> list[str]` | Path dei doc con arco `mentions` verso il simbolo. |
| `get_context(name: str) -> ContextBundle` | Bundle multi-hop, sezioni limitate dai knob di Settings (FR-016). |
| `exists(corpus: str) -> bool` | True se l'artefatto grafo è presente e leggibile. |
| `reset(corpus: str) -> None` | Elimina l'artefatto (assente = no-op). |

Semantica errori: query con grafo assente → `GraphNotFoundError`; extra `graph` mancante
all'atto della query → `ConfigError` azionabile (import pigro, G8/DA-5); formato sconosciuto
→ `ConfigError`.

Mock di test: `FakeCodeGraph` in `tests/fixtures/mocks.py` (dict in memoria, stessa semantica).

## Artefatto persistito (`sertor.graph/1`)

Percorso: `<Settings.index_dir>/graph/<corpus>.json` — namespace per **solo corpus** (G5: il
grafo non dipende dal provider di embeddings).

```json
{
  "format": "sertor.graph/1",
  "corpus": "sertor",
  "coverage": {"python": ["calls", "imports", "inherits"], "go": ["calls"], "...": []},
  "nodes": [
    {"id": "src/sertor_core/composition.py", "kind": "module", "name": "composition.py",
     "path": "src/sertor_core/composition.py", "line": null, "qualname": null},
    {"id": "src/sertor_core/composition.py::build_facade", "kind": "function",
     "name": "build_facade", "path": "src/sertor_core/composition.py", "line": 82,
     "qualname": "build_facade"}
  ],
  "edges": [
    {"source": "src/sertor_core/composition.py",
     "target": "src/sertor_core/composition.py::build_facade", "type": "contains"}
  ]
}
```

- Scrittura atomica; formato sconosciuto/corrotto → `ConfigError` (mai parsing parziale).
- `coverage` persistita = ciò che il build ha dichiarato (verificabile a posteriori).

## Servizio di estrazione (`services/graph_extraction.py`, puro)

| Funzione | Contratto |
|---|---|
| `extract_graph(documents, chunks) -> GraphData` | Nodi simbolo dai chunk (`symbol`/`qualname`/`node_type`/`start_line` — REQ-002); nodi module/doc dai Document; `contains` dalla gerarchia dei qualname; archi relazionali da un passaggio tree-sitter per i linguaggi nella mappa `_REL`; `mentions` per token distintivi (nome ≥5 char o camelCase o underscore) dai doc. |
| `COVERAGE: dict[str, tuple[str, ...]]` | Derivata da `_REL`: la dichiarazione unica per-linguaggio (FR-003), consumata da build, doc e test. |

Regole: ambiguità — un nome che risolve a più di `Settings.graph_ambiguity_threshold` candidati
non genera archi `calls` (FR-004, prototipo `len(tgts) <= 2`); deterministico (ordinamenti
stabili per id, FR-008); tree-sitter è già dipendenza base (nessun import nuovo).

## `Settings` — campi nuovi (env → default)

| Campo | Env | Default | Nota |
|---|---|---|---|
| `graph_enabled` | `SERTOR_GRAPH` | `True` | Cabla il sink grafo in `build_indexer()` (G6). |
| `graph_ambiguity_threshold` | `SERTOR_GRAPH_AMBIGUITY` | `2` | FR-004. |
| `graph_limit_definitions` | `SERTOR_GRAPH_LIMIT_DEFS` | `10` | FR-016. |
| `graph_limit_relations` | `SERTOR_GRAPH_LIMIT_RELS` | `8` | callers/callees/bases (FR-016). |
| `graph_limit_docs` | `SERTOR_GRAPH_LIMIT_DOCS` | `8` | FR-016. |

## Eventi di log (FR-026..028)

| Evento | Livello | Campi |
|---|---|---|
| `graph_build` | INFO | `corpus, graph_path, nodes_by_kind, edges_by_type, elapsed_ms` |
| `graph_query` | INFO | `operation, symbol, results, elapsed_ms` |

Redazione segreti: meccanismo esistente.

## Flusso del build (in `IndexingService.index()`, G6)

```
discover → chunk → embed → (reset) → upsert vettoriale
  → [lexical sink, 013]
  → [graph sink, 014]: extract_graph(documents, chunks) → graph.build(corpus, data)
       (estrazione pura + JSON: nessun extra richiesto al build — G1)
```
Corpus vuoto in rebuild → `graph.build(corpus, GraphData(vuoto))` (specchio).
