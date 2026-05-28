---
title: 02 Hybrid + reranking
type: experiment
tags: [hybrid, bm25, rrf, reranking, flashrank, cross-encoder]
created: 2026-05-28
updated: 2026-05-28
status: completato
sources: [https://github.com/fastapi/fastapi]
---

# 02 Hybrid + reranking

## Obiettivo
Verificare se **lessicale (BM25) + fusione + reranking** migliora il [[01-baseline]] solo-denso,
in particolare sulle query a **simboli esatti** del codice. Vedi [[architettura-target]].

## Setup
- Riusa le collection Chroma della Tappa 1 (`01-baseline/.index`), nessuna re-indicizzazione.
- **Sparse:** BM25Okapi (`rank-bm25`) con tokenizer che preserva gli identificatori
  (sotto-token per snake_case).
- **Fusione:** Reciprocal Rank Fusion (RRF, c=60) di dense (pool 30) + sparse (pool 30).
- **Reranking:** FlashRank `ms-marco-MiniLM-L-12-v2` (ONNX, niente torch) sul pool fuso.
- **Eval set esteso:** 18 query (10 NL + 8 a simboli esatti come `OAuth2PasswordBearer`,
  `JSONResponse`, `APIRouter`, `jsonable_encoder`, ...). Metriche: hit@k, MRR@10,
  e MRR sul solo sottoinsieme symbol.
- **Codice:** `02-hybrid-reranking/` (`hybrid.py`, `rerank.py`, `evaluate.py`).

## Risultati

| provider | mode | hit@1 | hit@3 | hit@10 | MRR | MRR(sym) |
|----------|------|------:|------:|-------:|----:|---------:|
| ollama | dense | 0.44 | 0.56 | 0.61 | 0.496 | 0.125 |
| ollama | hybrid | 0.56 | 0.72 | 1.00 | 0.704 | 0.396 |
| ollama | **hybrid+rerank** | **0.83** | **0.94** | 1.00 | **0.897** | **0.938** |
| azure-small | dense | 0.83 | 1.00 | 1.00 | 0.907 | 1.000 |
| azure-small | hybrid | 0.94 | 1.00 | 1.00 | 0.972 | 0.938 |
| azure-small | hybrid+rerank | 0.83 | 0.94 | 1.00 | 0.897 | 0.938 |
| azure-large | dense | 0.94 | 1.00 | 1.00 | 0.972 | 1.000 |
| azure-large | hybrid | 0.83 | 1.00 | 1.00 | 0.907 | 0.854 |
| azure-large | hybrid+rerank | 0.83 | 0.94 | 1.00 | 0.897 | 0.938 |

## Learnings
- **Il valore della tecnica dipende dalla forza del retriever di base.**
- **Embedder locale debole (ollama): vittoria netta.** hybrid+rerank porta MRR 0.50→0.90 e
  sui simboli 0.13→0.94 — quasi a pari con Azure. Il dense locale da solo è pessimo sui
  simboli (es. `OAuth2PasswordBearer` restituiva esempi di streaming); BM25 li recupera e il
  reranker li ordina correttamente (al top finisce `fastapi/security/oauth2.py`).
- **Embedder Azure forti: già vicini al soffitto** su questo eval; il reranker generico
  `ms-marco` (addestrato su passaggi web, non sul codice) **non aiuta e talvolta peggiora**
  leggermente, e la fusione RRF può introdurre rumore. Su `azure-large` il dense puro resta il migliore (MRR 0.972).
- **Implicazione progettuale:** per un deploy **locale/privacy-first** hybrid+rerank è
  essenziale; per embedding cloud large può bastare il denso, oppure serve un **reranker
  tarato sul codice**.
- **Caveat:** eval piccolo (18 query) e saturo per Azure → poco headroom. Serve un set più
  grande e difficile (query ambigue, multi-hop) per misurare davvero il guadagno sui forti.

## Prossimi passi
- Tappa 03 (GraphRAG): grafo del codice + link doc↔codice per query multi-hop.
- Valutare un reranker code-aware e ampliare l'eval set.
- Quando entreranno due corpora distinti (codice vs doc), introdurre la **fusione cross-corpus**.
