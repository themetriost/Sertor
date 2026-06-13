# sertor-core

The shared retrieval core of Sertor (FEAT-001): the **production-grade foundation** on which the
RAG engines and wiki skills are built. It reads any repository, chunks its code and documentation,
produces embeddings via swappable providers, persists/queries the chunks through a vector store
abstraction, and exposes a **retrieval facade importable as a library**.

## Architecture (Clean Architecture)

Dependencies point inward: the `domain` (entities + ports + errors) imports no external SDK;
`adapters` implement the ports; the `composition root` wires everything from configuration.

```
domain/        entities (Document, Chunk, RetrievalResult, GraphNode, …) + SIX Protocol ports
               (EmbeddingProvider, VectorStore, LexicalIndex, Reranker, CodeGraph,
               RetrieverStrategy) + domain errors
services/      ingestion · chunking (code/markdown/fallback) · indexing · retrieval (facade)
               · graph_extraction (multi-language code-graph)
adapters/      embeddings/{ollama,azure} · vectorstores/{chroma,azure_search}
               · lexical/bm25 · rerank/flashrank (extra) · graph/networkx (extra)
engines/       baseline (vector) · hybrid (BM25+RRF, DEFAULT) · evaluation (hit@k, MRR)
config/        Settings (centralised configuration)
observability/ structured logging
composition.py build_facade() / build_indexer() / build_engine() / build_graph_service() / …
```

## Installation

The package is **not (yet) on PyPI**: the interim distribution is via `git+url` (DA-4 of the CLI epic).

```bash
# base: Chroma (local) + Ollama (local), hybrid engine included
uv add "sertor-core @ git+https://github.com/themetriost/Sertor"
# extras: cloud, MCP server, cross-encoder reranking, code-graph navigation
uv add "sertor-core[azure,mcp,rerank,graph] @ git+https://github.com/themetriost/Sertor"
```

Full guide for installing on another repository: [`docs/install.md`](../../docs/install.md).

Chunking uses `tree-sitter-language-pack` (pre-built wheels, no C toolchain required).

## Configuration

All choices flow through `Settings`, read from env + `.env` file (not versioned). See
`.env.example` at the root. `RAG_BACKEND=local` mode → no cloud network calls.

## Usage as a library

```python
from sertor_core import build_indexer, build_facade

# Index any repository
report = build_indexer().index("/path/to/repo")
print(report.documents, report.chunks)

# Query (code / doc / combined)
facade = build_facade()
for hit in facade.search_code("input validation", k=5):
    print(hit.path, hit.chunk_id, round(hit.score, 3))
```

Each result exposes `text`, `path`, `chunk_id`, `doc_type`, `score`. Empty index → empty list
+ warning (no exception).

## RAG engines and code-graph

Three capabilities (selection is ALWAYS from configuration, never from code):

- **Hybrid (default, FEAT-004)** — `SERTOR_ENGINE=hybrid`: lexical BM25 + vector retrieval
  fused with RRF; optional cross-encoder reranking (extra `rerank`). Corpora indexed before
  the hybrid engine degrade to vector-only with a warning; a re-index enables the hybrid engine.
- **Baseline (FEAT-002)** — `SERTOR_ENGINE=baseline`: vector similarity only, identical to
  pre-hybrid behaviour.
- **Code-graph (FEAT-005, orthogonal to engines)** — `index()` also builds the structural code
  graph; `build_graph_service()` exposes `find_symbol` / `who_calls` /
  `related_docs` / `get_context` (navigation requires the `graph` extra).

```python
from sertor_core import build_engine, build_graph_service

engine = build_engine()                    # hybrid by default; baseline via SERTOR_ENGINE
hits = engine.query("EmbeddingProvider", k=5)

graph = build_graph_service()
print(graph.find_symbol("build_facade"))  # exact definition: path, line, qualname
```

### The baseline engine in detail

A thin engine on top of the core that indexes a codebase and queries it by vector similarity.

```python
from sertor_core import build_baseline_engine, evaluate, IndexNotFoundError

engine = build_baseline_engine()           # wired from Settings; engine.name == "baseline"
engine.index("/path/to/repo")              # idempotent rebuild-from-scratch
hits = engine.query("how is an input validated", k=5)   # top-k by similarity

# Index not built → explicit error (not an empty list):
try:
    build_baseline_engine().query("x")
except IndexNotFoundError as e:
    print("Build the index first:", e)

# Relevance evaluation (hit-rate@k, MRR@10) against a ground-truth:
report = evaluate(engine, [("server startup", ["web/server.js"])])
print(report.hit_rate, report.mrr)
```

Differences from the core facade: the engine **rebuilds the index from scratch** on every
`index()` call (no stale chunks) and on a missing index **raises `IndexNotFoundError`** instead of
returning an empty list. It uses **only** vector retrieval: it is the comparison baseline in
measurements (the product default is the hybrid engine).

## Testing with mocks (no cloud or network)

The core is exercisable with mock adapters of the ports:

```python
from sertor_core.services.retrieval import RetrievalFacade

facade = RetrievalFacade(embedder=FakeEmbedder(dim=8), store=InMemoryStore(),
                         collection="test", default_k=5)
```

## Languages supported by code-aware chunking

Syntactic at first release: Python, JavaScript/TypeScript, Java, C#, Go, C/C++, PHP, Ruby.
PowerShell and SQL dialects (T-SQL/PL-SQL) use the **dimensional fallback** until their node types
are validated (incremental extension). Any other language falls back without error.

See `specs/001-nucleo-retrieval/` for the full spec, plan, contracts, and quickstart.
