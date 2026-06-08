---
title: Implementazione FEAT-002 Motore Baseline
type: experiment
tags: [feat-002, motore-baseline, rag-vettoriale, ranking, valutazione]
created: 2026-06-03
updated: 2026-06-08 (distillato: entità in vector-retrieval/indexing-and-retrieval; record ridotto a evento+esito)
sources: ["specs/002-rag-baseline/plan.md", "specs/002-rag-baseline/tasks.md", "src/sertor_core/engines/**", "tests/**"]
---

# FEAT-002: Motore Baseline (RAG Vettoriale)

**Evento (2026-06-03).** Implementata la prima modalità RAG di `sertor-core`: il **motore baseline**
(`engines/baseline.py`) — [[vector-retrieval|retrieval vettoriale]] con ranking per similarità sopra il
[[retrieval-core|nucleo]] (FEAT-001) — più la **valutazione** (`engines/evaluation.py`: hit-rate@k, MRR@10).

> Record datato: la conoscenza durevole *su cosa è* il motore (e la sua policy d'errore strict, la
> valutazione) è distillata in [[vector-retrieval]]; l'atomicità del rebuild in [[indexing-and-retrieval]].

## Esito (al 2026-06-03)
- **Test:** 67 passed + 2 xfail (`precision@k`/`hit_rate` ground-truth, rinviati a DA-1/DA-3). 21/21 task.
- **Lint:** ruff clean. **Constitution Check:** 9/9 ✅. **`/speckit-analyze`:** 15/15 FR, 0 critical.

## Estensioni non-breaking al nucleo (validazione dell'interfaccia)
La feature è la prova che il motore **estende il nucleo senza modificarlo** (Principio III): aggiunge solo
*additivo* — `IndexNotFoundError`, il flag `rebuild` (default `False`) su `IndexingService.index()`, il metodo
`reset()` sulla porta `VectorStore`, e gli export `build_baseline_engine`/`BaselineEngine`/`evaluate`. Nessun
refactor del nucleo.

## Dove vive ora (conoscenza distillata)
- [[vector-retrieval]] — la modalità, la policy *strict* (`IndexNotFoundError`), la valutazione hit@k/MRR@10.
- [[indexing-and-retrieval]] — l'atomicità del rebuild (reset dopo embed, prima di upsert).

---
**Cross-refs:** [[retrieval-core]] · [[implementazione-nucleo-retrieval]] · [[piano-nucleo-retrieval]] · [[decomposizione-must-core]]
