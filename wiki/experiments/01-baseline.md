---
title: 01 Baseline (vector retrieval)
type: experiment
tags: [baseline, vector-retrieval, embeddings, chroma]
created: 2026-05-28
updated: 2026-05-28
status: completato
sources: [https://github.com/fastapi/fastapi]
---

# 01 Baseline (vector retrieval)

## Obiettivo
Validare end-to-end un RAG baseline su un singolo corpus (codice + doc insieme) e
**confrontare i 3 provider di embedding** su uno stesso eval set. Vedi [[architettura-target]].

## Setup
- **Backend:** local (Chroma persistente, distanza coseno).
- **Corpus:** [[fastapi]] — `fastapi/` + `docs_src/` (codice/esempi) e `docs/en/` (doc Markdown).
  655 documenti → **3500 chunk**.
- **Chunking:** language-aware (Python `900/120`, Markdown `1200/150`) — baseline; tree-sitter più avanti.
- **Embedding** (vedi [[stack]]): `nomic-embed-text` (Ollama, 768) · `text-embedding-3-small`
  (Azure, 1536) · `text-embedding-3-large` (Azure, 3072). Una collection Chroma per provider.
- **Codice:** `01-baseline/` (`chunking.py`, `index.py`, `search.py`, `evaluate.py`).

## Procedura
```bash
python 01-baseline/index.py --provider all     # indicizza i 3 provider
python 01-baseline/evaluate.py                 # hit-rate@k + MRR su 10 query
```
Eval set: 10 query con ground-truth a sottostringhe di path (`eval_queries.json`); una hit
conta se un risultato top-k ha il path atteso.

## Risultati

Tempi di indicizzazione (3500 chunk): ollama **27.5s**, azure-small **105s**, azure-large **113s**.

| provider | hit@1 | hit@3 | hit@5 | hit@10 | MRR@10 |
|----------|------:|------:|------:|-------:|-------:|
| ollama (locale) | 0.60 | 0.80 | 0.80 | 0.90 | 0.693 |
| azure-small | 0.70 | 1.00 | 1.00 | 1.00 | 0.833 |
| azure-large | **0.90** | **1.00** | 1.00 | 1.00 | **0.950** |

Esempio (query "how to declare a dependency with Depends", ollama): recupera sia
`fastapi/applications.py` sia `docs/en/docs/tutorial/dependencies/index.md` → la
**dual-corpus** (codice+doc nello stesso indice) funziona già nel baseline.

## Learnings
- **Ranking provider:** `azure-large` > `azure-small` > `ollama`. Large è il migliore ai
  primi rank (hit@1 0.90); small recupera comunque tutto entro i primi 3.
- **Ollama locale** è una baseline credibile (hit@10 0.90) ma più debole in cima → per il
  caso d'uso agentico, dove contano i primi risultati, il gap conta.
- **Trade-off:** large costa di più e invia il testo al cloud (privacy); ollama è gratis e
  locale. La scelta dipenderà da sensibilità del codice vs qualità richiesta.
- **Limite del baseline:** solo retrieval denso. Query con **identificatori/simboli esatti**
  dovrebbero migliorare con il lessicale (BM25) + reranking → motivazione della Tappa 02
  ([[architettura-target]]).
- L'eval set è piccolo (10 query): indicativo, non statisticamente robusto. Da ampliare.

## Prossimi passi
- Tappa 02: hybrid (BM25 + dense) + reranking, e **fusione** quando entreranno due corpora distinti.
- Rifinitura chunking con tree-sitter (AST per funzione/classe).
