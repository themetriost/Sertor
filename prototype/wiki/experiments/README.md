# Esperimenti

Una pagina per esperimento. Ogni pagina documenta cosa abbiamo costruito, come, i
risultati e le lezioni imparate. Il codice vive nelle cartelle radice corrispondenti
(`01-baseline/`, `02-hybrid-reranking/`, `03-graphrag/`, `04-agentic-rag/`).

## Template di una pagina esperimento

```markdown
---
title: <numero> <nome esperimento>
type: experiment
tags: [<approccio>, ...]
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: pianificato | in-corso | completato
sources: []
---

# <numero> <nome esperimento>

## Obiettivo
Cosa vogliamo verificare/imparare.

## Setup
Backend (local/azure), modelli, vector store, dataset, parametri (chunk size, top-k, ...).

## Procedura
Passi eseguiti / come riprodurre.

## Risultati
Metriche, osservazioni, esempi di query e risposte.

## Learnings
Cosa funziona, cosa no, trade-off. Collega ai [[concept]] e alle [[tech]] rilevanti.
```

## Esperimenti pianificati

| # | Approccio | Stato |
|---|-----------|-------|
| 01 | Baseline (vector retrieval) | pianificato |
| 02 | Hybrid + reranking | pianificato |
| 03 | GraphRAG | pianificato |
| 04 | Agentic RAG | pianificato |
