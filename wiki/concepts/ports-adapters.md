---
title: Porte e adapter (boundary del retrieval-core)
type: concept
tags: [ports, adapters, protocol, hexagonal, clean-architecture, sertor-core, composition]
created: 2026-06-08
updated: 2026-06-12 (FEAT-004: +LexicalIndex, Reranker, RetrieverStrategy — da due a cinque porte)
sources: ["src/sertor_core/domain/ports.py", "src/sertor_core/composition.py", "src/sertor_core/adapters/**"]
---

# Porte e adapter (boundary del retrieval-core)

Le **porte** del [[retrieval-core]] sono i **boundary astratti** dietro cui vivono i provider concreti: il
nucleo dipende **solo** da esse (Principio I/II della [[constitution|Costituzione]]), gli **adapter** in
`adapters/` le implementano importando gli SDK esterni. Vivono in `domain/ports.py`, definite come
**`Protocol`** (structural typing): un adapter è conforme se ha i metodi giusti, **senza ereditare nulla** —
così è banale da mockare nei test (tutte `@runtime_checkable`). Le porte sono **cinque**: le due
fondative qui sotto, più le tre della FEAT-004 ([[hybrid-retrieval]]).

## Le due porte fondative

- **`EmbeddingProvider`** — trasforma testo in vettori. Metodo `embed(texts) -> list[list[float]]` (a batch,
  ordine preservato, `[]` per input vuoto) + attributi `name`, `dim` (dimensione del vettore, scoperta al
  primo batch se inizialmente `None`), `batch_size`.
- **`VectorStore`** — persiste e cerca. `upsert(collection, records)` (idempotente sugli stessi id),
  `query(collection, vector, k, doc_type) -> list[RetrievalResult]` (top-k per similarità, filtro su
  `DocTypeFilter` = `code|doc|both` **senza** indici separati), più `delete`, `reset` (per il rebuild),
  `exists` e `list_collections()` (elenco delle collezioni — serve alla ricerca combinata multi-collezione
  per distinguere un corpus mai indicizzato, tollerato, da uno indicizzato con un **altro provider** →
  `ProviderMismatchError`, [[spec-010-query-congiunta-e-upsert-index|feature 010]]). Una collezione assente → `query` restituisce `[]` ed
  `exists()==False`; un backend irraggiungibile → `VectorStoreError` (Principio IV).

## Le tre porte della FEAT-004 ([[hybrid-retrieval]])

- **`LexicalIndex`** — indice lessicale del motore ibrido: `build` (snapshot integrale, atomico),
  `query` (ranking di chunk_id, filtro doc_type pre-taglio), `lookup` (materializzazione delle
  voci), `exists`/`reset`. Namespacing per collezione, come il vettoriale.
- **`Reranker`** — secondo stadio opzionale: `model` + `rerank(query, results, k)`; l'adapter è
  dietro l'extra `rerank` (import lazy).
- **`RetrieverStrategy`** — il seam con cui il composition root **inietta** la strategia di
  retrieval nella facade (`retrieve(query, k, doc_type)`): i consumatori non cambiano quando
  cambia il motore.

Le porte parlano in termini di [[domain-model|entità di dominio]] (`EmbeddedChunk`,
`RetrievalResult`, `LexicalEntry`): è ciò che impedisce a uno schema di backend di risalire nel
nucleo.

## Gli adapter (le implementazioni concrete)

| Porta | Adapter locale (default) | Adapter Azure |
|---|---|---|
| `EmbeddingProvider` | `adapters/embeddings/ollama.py` (`OllamaEmbedder`) | `adapters/embeddings/azure.py` (`AzureEmbedder`) |
| `VectorStore` | `adapters/vectorstores/chroma.py` (`ChromaStore`) | `adapters/vectorstores/azure_search.py` (`AzureSearchStore`) |
| `LexicalIndex` | `adapters/lexical/bm25.py` (`Bm25LexicalIndex`, sidecar JSON) | — (delega nativa per-store = Could, Gruppo E) |
| `Reranker` | `adapters/rerank/flashrank.py` (`FlashRankReranker`, extra `rerank`) | — |

## Il composition root sceglie

`composition.py` è l'**unico** componente che conosce gli adapter concreti: le `build_*` (`build_embedder`,
`build_store`, `build_indexer`, `build_facade`, `build_baseline_engine`) leggono `Settings` e cablano
l'implementazione. Provider di **embeddings** e backend del **vector store** sono scelti da **due manopole
distinte** (FEAT-009): `backend` (`RAG_BACKEND`) governa l'embedder (Ollama vs Azure OpenAI),
`store_backend` (`SERTOR_STORE_BACKEND`, default = `backend`) governa lo store (Chroma vs Azure AI Search).
Sono **combinabili** — es. embeddings Azure con store Chroma locale (la combinazione usata per l'indice di
dogfooding `sertor`) — fedeli al local-first del Principio II. Due conseguenze di design:

- **Import lazy.** Gli SDK pesanti sono importati **dentro** le `build_*`, solo sul ramo che li usa: l'extra
  `azure` non serve in locale (isolamento delle dipendenze).
- **Estendere qui, non nei servizi.** Aggiungere un provider/backend significa toccare il composition root e
  scrivere un adapter — **non** modificare i servizi, che vedono solo le porte.

Il composition root calcola anche il nome di **collezione namespaced** per `(corpus, provider)` via
`collection_name()`: poiché il provider determina la dimensione del vettore, includerlo evita di mescolare
embedding di dimensioni diverse (vedi [[corpus-index-naming]]).

## Vedi anche
- L'architettura che le ospita: [[retrieval-core]].
- Cosa scambiano: [[domain-model]].
- Chi le cabla in pipeline: [[indexing-and-retrieval]].
- Perché i consumatori entrano dalle `build_*`: [[thin-consumer]].
