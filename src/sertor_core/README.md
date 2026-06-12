# sertor-core

Nucleo di retrieval condiviso di Sertor (FEAT-001): la **fondazione production-grade** su cui
poggiano i motori RAG e le skill wiki. Legge un repository qualunque, ne fa chunking di codice e
documentazione, produce embeddings via provider intercambiabili, persiste/interroga i chunk via
un'astrazione di vector store, ed espone una **facade di retrieval importabile come libreria**.

## Architettura (Clean Architecture)

Le dipendenze puntano verso l'interno: il `domain` (entità + porte + errori) non importa alcun SDK
esterno; gli `adapters` implementano le porte; il `composition root` cabla tutto dalla
configurazione.

```
domain/        entità (Document, Chunk, RetrievalResult, GraphNode, …) + SEI porte Protocol
               (EmbeddingProvider, VectorStore, LexicalIndex, Reranker, CodeGraph,
               RetrieverStrategy) + errori di dominio
services/      ingestion · chunking (code/markdown/fallback) · indexing · retrieval (facade)
               · graph_extraction (code-graph multi-linguaggio)
adapters/      embeddings/{ollama,azure} · vectorstores/{chroma,azure_search}
               · lexical/bm25 · rerank/flashrank (extra) · graph/networkx (extra)
engines/       baseline (vettoriale) · hybrid (BM25+RRF, DEFAULT) · evaluation (hit@k, MRR)
config/        Settings (config centralizzata)
observability/ logging strutturato
composition.py build_facade() / build_indexer() / build_engine() / build_graph_service() / …
```

## Installazione

Il pacchetto **non è (ancora) su PyPI**: la distribuzione interim è via `git+url` (DA-4 dell'epica CLI).

```bash
# base: Chroma (locale) + Ollama (locale), motore ibrido incluso
uv add "sertor-core @ git+https://github.com/themetriost/Sertor"
# extra: cloud, server MCP, reranking cross-encoder, navigazione code-graph
uv add "sertor-core[azure,mcp,rerank,graph] @ git+https://github.com/themetriost/Sertor"
```

Guida completa per installare su un altro repository: [`docs/install.md`](../../docs/install.md).

Il chunking usa `tree-sitter-language-pack` (wheel precompilati, nessuna toolchain C).

## Configurazione

Tutte le scelte passano da `Settings`, lette da env + file `.env` (non versionato). Vedi
`.env.example` alla radice. Modalità `RAG_BACKEND=local` → nessuna chiamata di rete cloud.

## Uso come libreria

```python
from sertor_core import build_indexer, build_facade

# Indicizzare un repository qualunque
report = build_indexer().index("/path/al/repo")
print(report.documents, report.chunks)

# Interrogare (codice / doc / combinata)
facade = build_facade()
for hit in facade.search_code("validazione input", k=5):
    print(hit.path, hit.chunk_id, round(hit.score, 3))
```

Ogni risultato espone `text`, `path`, `chunk_id`, `doc_type`, `score`. Indice vuoto → lista vuota
+ warning (nessuna eccezione).

## Motori RAG e code-graph

Tre capacità (selezione SEMPRE da configurazione, mai da codice):

- **Ibrido (default, FEAT-004)** — `SERTOR_ENGINE=hybrid`: BM25 lessicale + retrieval vettoriale
  fusi con RRF; reranking cross-encoder opzionale (extra `rerank`). I corpora indicizzati prima
  dell'ibrido degradano a vettoriale con warning; un re-index abilita l'ibrido.
- **Baseline (FEAT-002)** — `SERTOR_ENGINE=baseline`: solo similarità vettoriale, identico a
  prima dell'ibrido.
- **Code-graph (FEAT-005, ortogonale ai motori)** — `index()` costruisce anche il grafo
  strutturale del codice; `build_graph_service()` espone `find_symbol` / `who_calls` /
  `related_docs` / `get_context` (navigazione richiede l'extra `graph`).

```python
from sertor_core import build_engine, build_graph_service

engine = build_engine()                    # ibrido di default; baseline via SERTOR_ENGINE
hits = engine.query("EmbeddingProvider", k=5)

graph = build_graph_service()
print(graph.find_symbol("build_facade"))  # definizione esatta: path, riga, qualname
```

### Il motore baseline in dettaglio

Un motore sottile sopra il nucleo che indicizza una codebase e la interroga per similarità
vettoriale.

```python
from sertor_core import build_baseline_engine, evaluate, IndexNotFoundError

engine = build_baseline_engine()           # cablato da Settings; engine.name == "baseline"
engine.index("/path/al/repo")              # rebuild-from-scratch idempotente
hits = engine.query("come si valida un input", k=5)   # top-k per similarità

# Indice non costruito → errore esplicito (non lista vuota):
try:
    build_baseline_engine().query("x")
except IndexNotFoundError as e:
    print("Costruisci prima l'indice:", e)

# Valutazione della pertinenza (hit-rate@k, MRR@10) su un ground-truth:
report = evaluate(engine, [("avvio del server", ["web/server.js"])])
print(report.hit_rate, report.mrr)
```

Differenze rispetto alla facade del nucleo: il motore **ricostruisce l'indice da zero** a ogni
`index()` (nessun chunk obsoleto) e su indice mancante **solleva `IndexNotFoundError`** invece di
restituire una lista vuota. Usa **solo** retrieval vettoriale: è la baseline di confronto nelle
misure (il default di prodotto è l'ibrido).

## Test con mock (senza cloud né rete)

Il core è esercitabile con adapter mock delle porte:

```python
from sertor_core.services.retrieval import RetrievalFacade

facade = RetrievalFacade(embedder=FakeEmbedder(dim=8), store=InMemoryStore(),
                         collection="test", default_k=5)
```

## Linguaggi del chunking code-aware

Sintattici al primo rilascio: Python, JavaScript/TypeScript, Java, C#, Go, C/C++, PHP, Ruby.
PowerShell e i dialetti SQL (T-SQL/PL-SQL) usano il **fallback dimensionale** finché i node-type
non sono validati (estensione incrementale). Qualunque altro linguaggio ricade sul fallback senza
errore.

Vedi `specs/001-nucleo-retrieval/` per spec, piano, contratti e quickstart completi.
