---
title: Retrieval core
type: concept
tags: [retrieval-core, sertor-core, clean-architecture, porte-adapter, retrieval, architettura]
created: 2026-06-07
updated: 2026-06-09
sources: ["src/sertor_core/composition.py", "src/sertor_core/**", "CLAUDE.md", "specs/001-nucleo-retrieval/**"]
---

# Retrieval core

Il **retrieval core** (`sertor-core`, pacchetto `src/sertor_core/`) è la **libreria di retrieval
importabile** che costituisce *il prodotto* Sertor: ingerisce un repository qualunque (codice + doc), lo
**chunka**, ne calcola gli **embedding**, li persiste in un **vector store** ed espone una **facade di
retrieval unica**. CLI, server MCP e wiki-tools sono **[[thin-consumer|consumatori sottili]]** che la
importano — non è il core a dipendere da loro.

È costruito in **Clean Architecture** sotto la [[constitution|Costituzione]] (Principio I, non
negoziabile): **le dipendenze puntano verso l'interno**.

## Architettura a strati

```
src/sertor_core/
├─ domain/         entità (Document, Chunk, RetrievalResult), porte (Protocol), errori — NESSUN import di SDK
├─ services/       ingestion · chunking (code/markdown/fallback + dispatch) · indexing · retrieval (facade)
├─ adapters/       embeddings/{ollama, azure} · vectorstores/{chroma, azure_search}
├─ engines/        baseline (1ª modalità RAG) + evaluation (hit_rate@k, MRR)
├─ config/         Settings — unica fonte di default (legge env + .env)
├─ observability/  logging strutturato
└─ composition.py  composition root: l'UNICO posto che conosce gli adapter concreti
```

- **`domain/` è puro.** Entità (`entities.py`), errori (`errors.py`, gerarchia `SertorError`) e le **porte**
  come `Protocol` in `ports.py` (`EmbeddingProvider`, `VectorStore`). Lo *structural typing* le rende
  mockabili senza ereditarietà: nessun SDK esterno entra nel dominio.
- **`adapters/` implementa le porte.** I provider concreti — Ollama/Azure per gli embedding, Chroma/Azure
  AI Search per il vector store — vivono qui dietro le porte. Gli SDK pesanti sono importati **lazy** nelle
  factory, così l'extra `azure` non serve in locale.
- **`composition.py` è l'unico cablaggio.** Sceglie le implementazioni da **due manopole distinte** di
  `Settings`: l'**embedder** da `embed_provider` (`azure` → Azure OpenAI · altrimenti Ollama) e lo **store**
  da `store_backend` (`azure` → Azure AI Search · altrimenti Chroma). Le due sono **combinabili** — es.
  embeddings Azure + store Chroma locale, la combinazione del dogfood `sertor`. Per aggiungere un provider si
  estendono composition root e adapters, **non** i servizi. Vedi [[ports-adapters]].

## Principi che lo governano

- **Default solo in `Settings`** (config centralizzata, env + `.env`), mai hardcodati nei componenti. I
  consumatori entrano dalle factory `build_facade()` / `build_indexer()` / `build_baseline_engine()`.
- **Policy errori non uniforme e voluta.** Il nucleo è *tollerante* (indice mancante → `[]` + warning, per
  composabilità); il motore [[motore-baseline-feat002|baseline]] è *strict* (solleva `IndexNotFoundError`,
  per usabilità del consumatore). La differenza non va uniformata.
- **Idempotenza.** `engine.index()` fa rebuild-from-scratch; l'`upsert` è idempotente sugli stessi `id`
  (`doc_id` = path relativo POSIX, `chunk_id` = `{doc_id}#{ordinale}`).
- **Collezioni namespaced per `(corpus, provider)`** via `collection_name()`: provider con dimensioni-vettore
  diverse non si mescolano. Vedi [[corpus-index-naming]].

## Capacità

- **Ingestione repo-agnostica** — layout arbitrario, estensioni note, fallback testuale (Principio X,
  [[mission-vision]]).
- **Chunking code-aware** — sintattico multi-linguaggio via [[tree-sitter-language-pack]], più fallback
  dimensionale e splitter Markdown, smistati da un dispatcher.
- **Embeddings multi-provider** e **vector store astratto** — dietro le rispettive porte, scelti da config.
- **Facade di retrieval unificata** + motore [[motore-baseline-feat002|baseline]] (retrieval vettoriale con
  [[vector-retrieval|retrieval vettoriale]]) e valutazione (hit_rate@k, MRR).

## Le pagine-entità (dettaglio)
Il nucleo, scomposto nelle sue entità durevoli (distillate dal codice reale):
- [[domain-model]] — le entità dati (`Document`, `Chunk`, `RetrievalResult`, …) e l'idempotenza degli id.
- [[ports-adapters]] — le porte `EmbeddingProvider`/`VectorStore` e gli adapter cablati dal composition root.
- [[chunking-dispatch]] — il dispatch markdown/sintattico/fallback e i 10 linguaggi sintattici.
- [[indexing-and-retrieval]] — le due pipeline (ingest→chunk→embed→store) e la facade `search_code/docs/combined`.

## Vedi anche
- Design e implementazione (record datati): [[piano-nucleo-retrieval]] · [[implementazione-nucleo-retrieval]].
- Decomposizione dei requisiti: [[decomposizione-must-core]].
