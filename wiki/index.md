---
title: Indice del Wiki
type: index
updated: 2026-05-29 (Tappa 04 — adattatore LangGraph + confronto a 4 motori chiusi i 3 framework)
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
| 02 | Hybrid + reranking | [02-hybrid-reranking](experiments/02-hybrid-reranking.md) | **completato** |
| 03 | GraphRAG | [03-graphrag](experiments/03-graphrag.md) | **A+C completato; re-run dominio** |
| 04 | Agentic RAG | [04-agentic-rag](experiments/04-agentic-rag.md) | **vanilla + 3 framework (AutoGen/SK/LangGraph) + eval a 4 motori completati; MCP server prossimo** |

## Fonti

- [fastapi/fastapi (corpus campione)](sources/fastapi.md) — codice + docs Markdown + esempi, in `raw/fastapi/`

## Demo & Test

- [**README.md**](../README.md) — entry-point di root: scopo (toolset RAG riproducibile), pipeline shared
  (ingestion → indici → retrieval), componenti reali (`shared/config`, `loaders`, `embeddings`, Chroma, hybrid, grafo),
  quickstart, test, convenzioni, roadmap. Punto di partenza tecnico.
- [**DEMOS.md**](../DEMOS.md) — runbook eseguibile per ogni configurazione RAG (01, 02, 3A, 3C, 04):
  prerequisiti, comandi, output atteso/osservato. Smoke test pytest in `tests/`.
- [**ESEMPI.md**](../ESEMPI.md) — vetrina divulgativa "ho cercato X → mi ha restituito Y":
  esempi reali su FastAPI per ciascun motore (01–03), testa-a-testa sulla stessa domanda, guida "quale scegliere quando".
- [**ESEMPI-agentic.md**](../04-agentic-rag/ESEMPI-agentic.md) — doc parlante Tappa 04:
  eval comparativa vanilla vs AutoGen su 5 task, generata da `evaluate.py`.

## Sintesi

- [Vetrina di esempi — query → risposta per motore](syntheses/esempi-query-risposta.md) — sintesi pratica dei 4 motori e quando usarli
- [Architettura target — dual-RAG codice + documentazione](syntheses/architettura-target.md) — disegno finale + roadmap incrementale 01→04
