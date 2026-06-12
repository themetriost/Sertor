---
title: Hybrid retrieval (BM25 + dense con RRF)
type: concept
tags: [hybrid-retrieval, bm25, rrf, reranking, rag, lexical, sertor-core, feat-004]
created: 2026-06-12
updated: 2026-06-12
sources: ["src/sertor_core/engines/hybrid.py", "src/sertor_core/adapters/lexical/bm25.py", "specs/013-motore-ibrido-reranking/**"]
---

# Hybrid retrieval (BM25 + dense con RRF)

L'**hybrid retrieval** è la **seconda modalità RAG** di Sertor (FEAT-004, feature 013, PR #24):
fonde la via **densa** ([[vector-retrieval]]) con una via **lessicale** (BM25) tramite
**Reciprocal Rank Fusion**. Risolve la debolezza nota della sola via densa sulle **query
lessicali** — nomi esatti di simboli, termini rari, acronimi — che il modello di embedding può
«avvicinare» a concetti sbagliati. **Dal 2026-06-12 è il motore di default**
(`SERTOR_ENGINE=hybrid`, decisione D1: «il motore migliore è il default»).

## Le due vie e la fusione

- **Via densa**: invariata — embedding della query → similarity top-pool nel vector store.
- **Via lessicale**: porta `LexicalIndex` con adapter **`Bm25LexicalIndex`** (`rank-bm25`):
  sidecar JSON **atomico e versionato** (`sertor.lexical/1`) in `<index_dir>/lexical/
  <collection>.json` — stesso namespacing `(corpus, provider)` della collezione vettoriale.
  Tokenizer del prototipo 02: lowercase + **sotto-token snake_case** (il differenziatore sulle
  query a simbolo). Costruito nello **stesso passaggio di indicizzazione** (sink opzionale in
  `IndexingService`): i due indici sono sempre uno specchio dell'altro.
- **Fusione RRF**: `score(id) = Σ 1/(c + rank)` sulle due liste (c=60, pool=30 da `Settings`);
  fusione **per ranghi** (coseno e BM25 non sono commensurabili), deterministica (pareggi per
  `chunk_id`). I candidati di sola via lessicale si materializzano dal sidecar (`lookup`).

## Selezione e integrazione (i consumatori non cambiano)

`build_engine()` nel composition root risolve `SERTOR_ENGINE` (`baseline` | `hybrid`; valore
invalido → `ConfigError`); la facade riceve il motore come **strategia iniettata**
(`RetrieverStrategy`, parametro opzionale) → [[mcp-server]] e [[sertor-rag-cli]] beneficiano
dell'ibrido **senza una riga cambiata**. Il fan-out multi-collezione (feature 010) resta
dense-only by design. Il baseline resta selezionabile e identico a prima.

## Degradazione onesta (REQ-034)

Corpus indicizzato **prima** dell'ibrido (sidecar assente) → la query **non fallisce**: retrieval
dense-only + WARNING strutturato `lexical_index_missing` con hint («re-index abilita l'ibrido»).
Corpus **mai** indicizzato → `IndexNotFoundError` strict, come il baseline. È l'unica tensione
gestita col Principio IV (decisione utente DA-1b, tracciata nel plan 013): onestà via log, mai
silenzio.

## Reranking (secondo stadio, opzionale)

Porta `Reranker` + adapter **FlashRank** (cross-encoder ONNX, niente torch) come **extra
`rerank`** a import lazy: default **off** (su embedder forte può non servire, rischio R-3);
`SERTOR_RERANK=true` senza extra → `ConfigError` azionabile, mai fallback muto. Ri-ordina il
pool fuso (`rerank_pool`≈3×k).

## Qualità misurata (chiusi i 2 xfail storici)

Ground-truth versionato (`tests/fixtures/ground_truth.py`, 11 coppie symbol+NL); i 2 test di
pertinenza ex-`xfail` sono **strict e verdi**. Con embedder mock (CI locale, senza rete):

| Modalità | hit@5 | MRR@10 | hit@5 simboli |
|---|---|---|---|
| baseline (dense) | 0.00 | 0.022 | 0.00 |
| **hybrid** | **0.73** | 0.348 | **1.00** |
| hybrid+**rerank** | 1.00 | **0.939** | — |

Replica del prototipo 02 (MRR 0.13→0.94 con embedder debole). Nel dogfood live (Azure, corpus
sertor): qualità densa conservata + robustezza lessicale, ~666ms a query (NFR-04 ok).

## Vedi anche
- La prima modalità: [[vector-retrieval]] · le porte: [[ports-adapters]] · le pipeline:
  [[indexing-and-retrieval]] · il prodotto: [[retrieval-core]].
- Superfici che lo ereditano gratis: [[mcp-server]] · [[sertor-rag-cli]] ([[thin-consumer]]).
- Naming di collezioni e sidecar: [[corpus-index-naming]]. Stato: [[roadmap]].
