---
title: 03 GraphRAG (A — code graph leggero)
type: experiment
tags: [graphrag, code-graph, ast, networkx, multi-hop]
created: 2026-05-28
updated: 2026-05-28
status: parziale (A fatto; C — Microsoft GraphRAG — pianificato)
sources: [https://github.com/fastapi/fastapi]
---

# 03 GraphRAG (A — code graph leggero)

## Obiettivo
Costruire un **code knowledge graph** dal codice (AST) per query **strutturali** e
**multi-hop** (chi-chiama, dove-definito, doc collegati) complementari al retrieval
vettoriale di [[01-baseline]] / [[02-hybrid-reranking]]. Vedi [[architettura-target]].
Scelta concordata: **A ora** (grafo custom leggero), **C in seguito** (Microsoft GraphRAG) per confronto.

## Setup
- **Sorgente:** [[fastapi]] (`fastapi/` + `docs_src/` via AST; `docs/en/` per i link doc).
- **Grafo (`networkx`):** nodi module/class/function/method/doc; archi
  `contains` (struttura), `imports` (modulo→modulo), `calls` (func→func),
  `inherits` (classe→base), `mentions` (doc→simbolo, per menzione del nome).
  Risoluzione per nome **intra-progetto** (best-effort).
- **Codice:** `03-graphrag/` (`build_graph.py`, `graph_query.py`, `evaluate.py`).

## Risultati
- **Grafo:** 1917 nodi (502 module, 732 function, 312 class, 218 method, 153 doc) /
  4868 archi (1256 contains, 1166 calls, 1651 mentions, 579 imports, 216 inherits).
- **Definizione@1 sulle query a simbolo: 6/8 (0.75).**

| simbolo | def@1 | #callers | #docs |
|---------|:-----:|---------:|------:|
| OAuth2PasswordBearer | OK | 0 | 4 |
| OAuth2PasswordRequestForm | OK | 0 | 4 |
| APIRouter | OK | 1 | 10 |
| BackgroundTasks | OK | 1 | 3 |
| HTTPException | OK | 69 | 9 |
| jsonable_encoder | OK | 15 | 9 |
| JSONResponse | — | 0 | 0 |
| WebSocketDisconnect | — | 0 | 0 |

## Learnings
- **Forza del grafo:** risposte **precise e strutturali** che il vettoriale non dà —
  definizione con `path:lineno`, call-graph (es. `HTTPException` → 69 chiamanti) e
  collegamento doc↔codice (es. `APIRouter` → 10 doc).
- **Limite onesto (re-export):** `JSONResponse` e `WebSocketDisconnect` non risultano
  "definiti" perché sono **re-esportati da Starlette** (`from starlette... import ...`):
  l'AST li vede come import, non come `ClassDef`. Servirebbe risoluzione di alias/re-export
  (o un grafo arricchito via LLM come Microsoft GraphRAG).
- **Nessuna ricerca semantica:** il grafo **non** gestisce le query in linguaggio naturale.
  È **complementare**, non sostitutivo, del retrieval vettoriale/ibrido (che infatti aveva
  trovato `JSONResponse` via testo).
- **Implicazione → fusione:** vettoriale/ibrido per fuzzy/NL e re-export; grafo per
  struttura/navigazione precisa. La combinazione è il cuore del dual-RAG target.

## Prossimi passi
- **Tappa 3C:** Microsoft GraphRAG (estrazione entità/relazioni via LLM + community summaries)
  e **confronto** con questo grafo AST.
- Risoluzione re-export/alias nel grafo AST.
- Integrare il grafo nel retrieval (espansione del contesto a partire dai simboli trovati dal vettoriale).
