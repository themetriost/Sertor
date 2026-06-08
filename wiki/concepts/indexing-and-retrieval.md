---
title: Indicizzazione e retrieval (le due pipeline)
type: concept
tags: [indexing, retrieval, facade, pipeline, idempotenza, sertor-core, thin-consumer]
created: 2026-06-08
updated: 2026-06-08
sources: [
  "src/sertor_core/services/indexing.py",
  "src/sertor_core/services/retrieval.py",
  "src/sertor_core/services/ingestion.py"
]
---

# Indicizzazione e retrieval (le due pipeline)

Il [[retrieval-core]] ha due flussi simmetrici che si incontrano sulla **collezione namespaced**:
**indicizzazione** (scrive l'indice) e **retrieval** (lo legge). Entrambi cablano [[domain-model|entità di
dominio]] dietro le [[ports-adapters|porte]] — non conoscono né lo store né il provider concreti.

## Pipeline di indicizzazione

`IndexingService.index(root, rebuild)` esegue la catena completa **ingest → chunk → embed → store**:

1. **`discover(root)`** (`ingestion.py`) — scoperta repo-agnostica e **ordinata** per path (determinismo):
   estensione → linguaggio, esclusione configurabile di artefatti/segreti, skip dei file illeggibili con
   warning, `Document.id` = path relativo POSIX.
2. **`chunk_document`** per ogni documento → [[chunking-dispatch|i Chunk]].
3. **`embed`** dei testi via [[ports-adapters|`EmbeddingProvider`]] → `EmbeddedChunk`.
4. **`upsert`** nello [[ports-adapters|`VectorStore`]]; ritorna un `IndexReport` (conteggi, dimensione,
   `elapsed_ms`) e un log strutturato.

**Atomicità del rebuild (decisione).** Con `rebuild=True` il `reset` della collezione avviene **dopo**
l'embedding e **prima** dell'upsert: così se il provider fallisce durante l'embed (rete, rate-limit) l'indice
preesistente **resta intatto**. Il rebuild è idempotente (gli id stabili del [[domain-model]] fanno coincidere
i chunk a corpus invariato). `installazione ≠ esecuzione`: l'indice si costruisce **solo** quando `index()` è
chiamato (Principio VI).

## La facade di retrieval

`RetrievalFacade` è il **punto d'accesso unico e stabile** al corpus indicizzato, ed è ciò che i
[[thin-consumer|consumatori sottili]] (server MCP, motori, CLI) importano via `build_facade()` **senza**
conoscere store/embeddings. Espone tre ricerche, distinte solo dal filtro `DocTypeFilter`:

- `search_code(query, k)` → solo codice
- `search_docs(query, k)` → sola documentazione
- `search_combined(query, k)` → entrambi

Ogni ricerca embedda la query, interroga lo store per il top-k, emette un log e ritorna
`list[RetrievalResult]`.

**Tolleranza sull'indice assente (policy voluta).** Se la collezione non esiste, la facade ritorna **`[]` con
un warning**, senza eccezioni (REQ-028): è la faccia *tollerante* del nucleo, pensata per la composabilità —
da non confondere con la policy *strict* del motore [[vector-retrieval|baseline]] (che invece solleva), scelta
per l'usabilità del consumatore. La differenza è [[deterministic-vs-judgment|deliberata e non va uniformata]].

## Vedi anche
- Le entità in transito: [[domain-model]].
- Le astrazioni cablate: [[ports-adapters]].
- Come nascono i chunk: [[chunking-dispatch]].
- Chi consuma la facade: [[thin-consumer]] · prima modalità RAG: [[vector-retrieval]].
