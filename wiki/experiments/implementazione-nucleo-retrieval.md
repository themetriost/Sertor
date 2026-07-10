---
title: Implementazione FEAT-001 — Nucleo di Retrieval Condiviso
type: experiment
tags: [FEAT-001, nucleo-retrieval, implementation, completed, python, tree-sitter]
created: 2026-06-03
updated: 2026-06-08
sources: ["src/sertor_core/**", "specs/001-nucleo-retrieval/plan.md", "specs/001-nucleo-retrieval/tasks.md", "tests/**"]
---

# Implementazione FEAT-001 — Nucleo di Retrieval Condiviso

**Evento (2026-06-03).** Completata l'implementazione end-to-end della libreria installabile **`sertor-core`**
(il [[retrieval-core]]) secondo il [[piano-nucleo-retrieval|piano SpecKit FEAT-001]]: ingestione repo-agnostica,
chunking sintattico multilingue, embeddings intercambiabili, vector store astratto, facade di retrieval.

> **Questo è un record datato.** La conoscenza durevole *su cosa il nucleo è* (entità, porte, pipeline,
> chunking) è stata **distillata** nelle pagine-concetto (2026-06-08, vedi *Dove vive ora* sotto); qui resta
> solo l'evento e il suo esito. La versione precedente di questa pagina (≈312 righe) descriveva l'architettura
> inline, con nomi di file ormai stantii rispetto al codice reale.

## Esito (al 2026-06-03)

- **User story US1–US6:** completate (42 task, 0 blockers).
- **Test:** 53 passed + 1 xfail (`precision@k` baseline, rinviato alla misura DA-003).
- **Lint:** `ruff` clean. **Analisi:** `/speckit-analyze` → 100% copertura FR, 0 critical.
- **Constitution Check:** PASS sui 9 principi allora vigenti (Complexity Tracking vuoto).

## Dove vive ora (conoscenza distillata)

L'architettura realizzata — un tempo descritta qui — è ora nelle pagine-entità, ancorate al codice reale:

- [[domain-model]] — le entità (`Document`, `Chunk`/`ChunkMetadata`, `EmbeddedChunk`, `RetrievalResult`,
  `IndexReport`), id stabili e idempotenza.
- [[ports-adapters]] — le porte `EmbeddingProvider`/`VectorStore` (Protocol), gli adapter Ollama/Azure ·
  Chroma/Azure Search, e il composition root che li cabla da `Settings`.
- [[chunking-dispatch]] — il dispatch markdown/sintattico/fallback, i 10 linguaggi sintattici e l'esclusione
  R-N2 di PowerShell/SQL.
- [[indexing-and-retrieval]] — la pipeline ingest→chunk→embed→store (atomicità del rebuild) e la facade
  `search_code/docs/combined`.
- [[tree-sitter-language-pack]] — il binding usato dal chunking sintattico (wrapper `_Node`).

## Linkage a valle
- **FEAT-002:** il motore [[vector-retrieval|baseline]] consuma la facade per la ricerca vettoriale + ranking.
- **FEAT-003:** il wiki (`wiki_tools`) consuma ingestione/indicizzazione per il corpus wiki.

---
**Cross-refs:** [[piano-nucleo-retrieval|piano FEAT-001]] · [[retrieval-core]] · [[decomposizione-must-core]] · [[constitution]]
