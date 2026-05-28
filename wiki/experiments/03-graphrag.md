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

## Stima costi Tappa 3C (Microsoft GraphRAG)
Dimensione corpus misurata (~4 char/token): **completo ~590K token** (229K codice + 361K doc);
**subset** (`docs/en/docs/tutorial` + `fastapi/security`) **~90K token**.

L'indicizzazione GraphRAG consuma in chiamate LLM **circa 5–10× la dimensione del corpus**
(estrazione entità/relazioni per chunk + gleaning, summary delle descrizioni, community report).
Assunzioni: `chunk_size≈1200`, `max_gleanings=1`, ~80% input / 20% output.

| scenario | corpus | LLM token stimati (I/O) | costo modello *mini* | costo modello *4o* |
|----------|-------:|------------------------:|---------------------:|-------------------:|
| subset | ~90K | **~0.6–1.2M** | ~$0.15–0.30 | ~$2–4 |
| completo | ~590K | **~3.5–7.5M** | ~$1–2 | ~$15–30 |

Embeddings (text-embedding-3): trascurabili (~$0.02–0.1). Costi indicativi su prezzi pubblici
(*mini* ≈ $0.15/$0.60 per 1M in/out; *4o* ≈ $2.5/$10) — su Azure variano col listino del deployment.
**Incertezza ±2×**: dipende molto da `chunk_size` (300 → ~5× chunk e costo maggiore), gleanings,
e da quante entità/community emergono. Il tempo è limitato dal rate limit (TPM) del deployment.
**Approccio consigliato:** partire dal subset con un modello *mini*, leggere il consumo reale
dai log GraphRAG, poi estrapolare al corpus completo.

## Nota setup Tappa 3C — env isolato (non Docker)
Microsoft `graphrag` richiede un **virtualenv dedicato**, separato dal `.venv` principale,
per conflitti di dipendenze: usa `graspologic` (Leiden) → `numba`, che tipicamente vuole
**`numpy < 2.x`**, mentre il nostro `.venv` ha **numpy 2.4** → conflitto diretto. Porta anche
`lancedb`, `pyarrow`, `pandas`, `fnllm`/`tiktoken` con pin stretti.
- Setup: `uv venv 03-graphrag/.venv-grag` + `uv pip install graphrag`, oppure `uv tool install graphrag`.
- Si usa **da CLI** (`graphrag init/index/query`): legge `raw/`, scrive artefatti **parquet**.
- Gli artefatti si **rileggono dal `.venv` principale** (pandas/networkx) per il confronto col grafo AST.
- Isolamento solo dei *pacchetti Python*, non dei dati (condivisi sul filesystem).

## Prossimi passi
- **Tappa 3C:** Microsoft GraphRAG (estrazione entità/relazioni via LLM + community summaries)
  e **confronto** con questo grafo AST.
- Risoluzione re-export/alias nel grafo AST.
- Integrare il grafo nel retrieval (espansione del contesto a partire dai simboli trovati dal vettoriale).
