---
title: Stack del workspace
type: tech
tags: [stack, azure, microsoft, langchain]
created: 2026-05-28
updated: 2026-05-28
sources: []
---

# Stack del workspace

Riepilogo operativo dello stack. La configurazione autorevole è in
[`../../CLAUDE.md`](../../CLAUDE.md); questa pagina è il punto di ingresso del wiki
verso le singole tecnologie (man mano che le approfondiamo, creiamo una pagina dedicata
qui in `tech/` e la colleghiamo).

Due "tracce" intercambiabili via config (`RAG_BACKEND=local|azure`).

## Orchestrazione
- **LangChain** — framework generale, retrieval e chain.
- **Semantic Kernel** — SDK di orchestrazione Microsoft.
- **AutoGen** — orchestrazione multi-agente Microsoft (per [Agentic RAG](../concepts/rag-overview.md)).

## LLM / embeddings
- **Locale**: Ollama (`llama3.x`, `nomic-embed-text`), OpenAI pubblico.
- **Azure**: Azure OpenAI Service (deployment GPT + `text-embedding-3-*`).

## Retrieval / vector store
- **Locale**: Chroma (embedded, default).
- **Azure**: Azure AI Search (hybrid + semantic ranker + vector index), Azure Cosmos DB
  for NoSQL (vector search integrato).
- **GraphRAG**: store a grafo (`networkx` in locale; Neo4j opzionale).

## Reranking
- Azure AI Search semantic ranker (Azure); cross-encoder locale (`sentence-transformers` / FlashRank).

## GraphRAG
- Pacchetto **Microsoft GraphRAG** (`graphrag`).

## Pagine tecnologia da creare su richiesta
`langchain`, `semantic-kernel`, `autogen`, `azure-openai`, `azure-ai-search`,
`cosmos-db-nosql`, `ollama`, `chroma`, `microsoft-graphrag`.
