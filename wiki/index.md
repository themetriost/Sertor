---
title: Indice del Wiki
type: index
updated: 2026-05-28
---

# Indice del Wiki RAG

Catalogo globale del wiki. Questo è il primo file da leggere per orientarsi.
Il wiki è mantenuto secondo lo schema descritto in [`../CLAUDE.md`](../CLAUDE.md)
(sezione *Wiki & documentazione*), ispirato al pattern "LLM Wiki" di Karpathy.

## Come è organizzato

| Cartella | Contenuto |
|----------|-----------|
| [`concepts/`](concepts/) | Concetti RAG (chunking, embeddings, hybrid search, reranking, GraphRAG, agentic, ...) |
| [`tech/`](tech/) | Tecnologie e strumenti (LangChain, Semantic Kernel, AutoGen, Azure AI Search, Cosmos DB, Ollama, ...) |
| [`experiments/`](experiments/) | Una pagina per esperimento: obiettivo, setup, risultati, learnings |
| `sources/` | Riassunti di fonti esterne (paper, articoli, doc) — create su richiesta |
| `syntheses/` | Confronti e sintesi trasversali — create su richiesta |
| [`../raw/`](../raw/) | Fonti esterne immutabili (mai modificate): articoli, paper, asset |
| [`log.md`](log.md) | Registro append-only di tutto ciò che facciamo |

## Concetti

- [Panoramica RAG e approcci](concepts/rag-overview.md) — cos'è il RAG e i 4 approcci che esploriamo

## Tecnologie

- [Stack del workspace](tech/stack.md) — panoramica dello stack (locale + Microsoft/Azure)

## Esperimenti

| # | Approccio | Pagina | Stato |
|---|-----------|--------|-------|
| 01 | Baseline (vector retrieval) | [01-baseline](experiments/01-baseline.md) | **completato** |
| 02 | Hybrid + reranking | _da creare_ | pianificato |
| 03 | GraphRAG | _da creare_ | pianificato |
| 04 | Agentic RAG | _da creare_ | pianificato |

## Fonti

- [fastapi/fastapi (corpus campione)](sources/fastapi.md) — codice + docs Markdown + esempi, in `raw/fastapi/`

## Sintesi

- [Architettura target — dual-RAG codice + documentazione](syntheses/architettura-target.md) — disegno finale + roadmap incrementale 01→04
