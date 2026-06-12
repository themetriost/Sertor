---
title: Vector retrieval
type: concept
tags: [vector-retrieval, dense-retrieval, rag, baseline, embeddings, valutazione, sertor-core]
created: 2026-06-07
updated: 2026-06-12 (non è più l'unica modalità né il default: arriva [[hybrid-retrieval]], FEAT-004)
sources: ["src/sertor_core/engines/baseline.py", "src/sertor_core/engines/evaluation.py", "CLAUDE.md"]
---

# Vector retrieval

Il **vector retrieval** (retrieval vettoriale, o *dense* retrieval) è la **modalità RAG di riferimento** di
Sertor: la query viene trasformata in **embedding** e confrontata per **similarità** coi vettori dei chunk nel
vector store, restituendo i **top-k** più vicini. Nel [[retrieval-core]] è realizzato dal **motore baseline**
(`engines/baseline.py`); è la modalità più semplice, la baseline da cui si diramano le modalità successive
(ibrida, reranking, grafo).

## Come funziona

Il motore baseline (`BaselineEngine`) ha due operazioni:

- `index(root)` — ingerisce e indicizza un repository (rebuild-from-scratch, idempotente): chunking →
  embedding → upsert nel vector store.
- `query(query, k=None)` — calcola l'embedding della query e fa **similarity search** sui top-k (se `k` è
  omesso usa il default da `Settings`), restituendo `list[RetrievalResult]` (chunk + `score` di similarità).

## Policy d'errore *strict* (non come il nucleo)

A differenza del nucleo, che è **tollerante** (indice mancante → `[]` + warning, per composabilità), il
motore baseline è **strict**: se l'indice non esiste solleva `IndexNotFoundError` invece di restituire una
lista vuota — perché per il **consumatore finale** un indice assente è un errore d'uso, non un risultato
valido. È la differenza voluta descritta in [[retrieval-core]].

## Valutazione

«Una feature senza misura non esiste»: il modulo `engines/evaluation.py` misura la qualità del retrieval su
un **ground-truth esterno** (query → file attesi) e produce un `EvalReport` con **hit-rate@k** (per ogni k)
e **MRR@10**. Serve a confrontare modalità/provider su numeri, non impressioni.

## Cosa NON è

Non è retrieval **ibrido** (BM25 + dense), né **reranking**, né **GraphRAG**, né **agentic**. Dal
2026-06-12 la modalità ibrida **esiste** ([[hybrid-retrieval]], FEAT-004) ed è il **default**
(`SERTOR_ENGINE=hybrid`): il vector retrieval resta la via densa che l'ibrido ingloba, la baseline
di confronto nelle misure (`evaluate()`), e la modalità selezionabile con `SERTOR_ENGINE=baseline`
(risultati identici a prima). Il [[code-graph]] (FEAT-005, dal 2026-06-12) NON è una modalità di
retrieval ma navigazione strutturale ortogonale; il motore agentico resta futuro (FEAT-006).

## Vedi anche
- La modalità che lo estende (e oggi default): [[hybrid-retrieval]].
- Realizzazione e record datato: [[motore-baseline-feat002]]. Fondazione: [[retrieval-core]]. Collezioni e
  isolamento per corpus: [[corpus-index-naming]].
