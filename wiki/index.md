---
title: Indice del Wiki
type: index
updated: 2026-05-30 (Registrate pagine 1–2: requirements-tooling-landscape.md, costituzione-produzione-proposta.md; TODO wiki auto-manutentore aggiunto al backlog di architettura-attuale.md)
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
- [EARS — Easy Approach to Requirements Syntax](concepts/ears-methodology.md) — metodologia pubblica (Alistair Mavin) per requisiti atomici e testabili

## Tecnologie

- [Stack del workspace](tech/stack.md) — panoramica dello stack (locale + Microsoft/Azure)
- [Requirements Engineering — Fase a Monte del Design](tech/requirements-engineering.md) — elicitazione e formalizzazione requisiti via EARS, agnostico rispetto a design a valle
- [SpecKit — Governance e Orchestrazione di Progetto](tech/speckit.md) — framework phase-gate, 9 subagent, transizione prototipo→produzione

## Esperimenti

| # | Approccio | Pagina | Stato |
|---|-----------|--------|-------|
| 01 | Baseline (vector retrieval) | [01-baseline](experiments/01-baseline.md) | **completato** |
| 02 | Hybrid + reranking | [02-hybrid-reranking](experiments/02-hybrid-reranking.md) | **completato** |
| 03 | GraphRAG | [03-graphrag](experiments/03-graphrag.md) | **A+C completato; re-run dominio** |
| 04 | Agentic RAG | [04-agentic-rag](experiments/04-agentic-rag.md) | **completato** (vanilla + AutoGen/SK/LangGraph + eval 4 motori + server MCP) |

## Fonti

- [fastapi/fastapi (corpus campione)](sources/fastapi.md) — codice + docs Markdown + esempi, in `raw/fastapi/`
- [Panorama strumenti Requirements Engineering (mid-2026)](sources/requirements-tooling-landscape.md) — deep-research su BMAD, Kiro, PRD Creator, OpenSpec, gap Spec-Kit, feedback community, EARS overview

## Demo & Test

- [**README.md**](../README.md) — entry-point di root: scopo (toolset RAG riproducibile), pipeline shared
  (ingestion → indici → retrieval), componenti reali (`shared/config`, `loaders`, `embeddings`, Chroma, hybrid, grafo),
  quickstart, test, convenzioni, roadmap. Punto di partenza tecnico.
- [**DEMOS.md**](../DEMOS.md) — runbook eseguibile per ogni configurazione RAG (01, 02, 3A, 3C, 04, 04 MCP):
  prerequisiti, comandi, output atteso/osservato. Smoke test pytest in `tests/` (24 passed, 1 skipped).
  Sezione "04d — Server MCP" per Claude Code (Model Context Protocol, 7 tool di retrieval).
- [**ESEMPI.md**](../ESEMPI.md) — vetrina divulgativa "ho cercato X → mi ha restituito Y":
  esempi reali su FastAPI per ciascun motore (01–03), testa-a-testa sulla stessa domanda, guida "quale scegliere quando".
- [**ESEMPI-agentic.md**](../04-agentic-rag/ESEMPI-agentic.md) — doc parlante Tappa 04:
  eval comparativa vanilla vs AutoGen/SK/LangGraph su 9 task, generata da `evaluate.py`.
- [**FUSIONE.md**](../04-agentic-rag/FUSIONE.md) — confronto quantitativo **fusione dual-RAG (get_context,
  deterministica, 0 token LLM)** vs fusione assemblata dall'agente LLM; misura copertura e costo.

## Sintesi

- [Vetrina di esempi — query → risposta per motore](syntheses/esempi-query-risposta.md) — sintesi pratica dei 4 motori e quando usarli
- [Architettura target — dual-RAG codice + documentazione](syntheses/architettura-target.md) — disegno finale + roadmap incrementale 01→04
- [Architettura attuale (as-built) — tappe 01–04 complete](syntheses/architettura-attuale.md) — diagramma realizzato + strati + backlog di produzione (caching)
- [Flusso end-to-end epica → implementazione](syntheses/flusso-requisiti-implementazione.md) — diagramma e spiegazione dei due strati disaccoppiati (requisiti EARS via skill propria, SpecKit per feature; governance trasversale)
- [Costituzione di Progetto per Fase Produzione — Proposta](syntheses/costituzione-produzione-proposta.md) — 8 principi non-negoziabili (how-agnostici), decisioni aperte su target cloud/rigore test, ratifica in sospeso
