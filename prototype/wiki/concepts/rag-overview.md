---
title: Panoramica RAG e approcci
type: concept
tags: [rag, overview]
created: 2026-05-28
updated: 2026-05-28
sources: []
---

# Panoramica RAG e approcci

**RAG** (Retrieval-Augmented Generation) combina un *retriever* (recupera contesto
rilevante da una base di conoscenza) con un *generatore* (un LLM che produce la risposta
condizionata sul contesto recuperato). Riduce allucinazioni e permette di rispondere su
dati privati/aggiornati senza ri-addestrare il modello.

## Pipeline di base

1. **Ingest / indicizzazione**: i documenti vengono divisi in *chunk*, trasformati in
   *embeddings* e salvati in un vector store.
2. **Retrieval**: la query viene embeddata e si recuperano i chunk più simili.
3. **(Opz.) Reranking**: i candidati vengono riordinati con un modello più preciso.
4. **Generazione**: l'LLM risponde usando i chunk recuperati come contesto.

## I 4 approcci che esploriamo

- **Baseline (vector retrieval)** — chunk + embeddings + similarity search. Il punto di partenza.
- **Hybrid + reranking** — keyword/BM25 + dense retrieval, con reranking (cross-encoder o
  semantic ranker). Migliora recall e precision.
- **GraphRAG** — retrieval su knowledge graph: entità e relazioni, utile per domande
  multi-hop e sintesi globali. Vedi pacchetto [Microsoft GraphRAG](../tech/stack.md).
- **Agentic RAG** — retrieval iterativo guidato da agenti (query planning, multi-step,
  multi-agente). Orchestrato con AutoGen / Semantic Kernel.

Ogni approccio avrà la sua pagina in [`../experiments/`](../experiments/) con setup,
risultati e learnings, e userà lo [stack](../tech/stack.md) del workspace.
