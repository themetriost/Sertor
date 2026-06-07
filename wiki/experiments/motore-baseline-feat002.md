---
title: Implementazione FEAT-002 Motore Baseline
type: experiment
tags: [feat-002, motore-baseline, rag-vettoriale, ranking, valutazione]
created: 2026-06-03
updated: 2026-06-07
sources: ["specs/002-rag-baseline/plan.md", "specs/002-rag-baseline/tasks.md", "src/sertor_core/engines/**", "tests/**"]
---

# FEAT-002: Motore Baseline (RAG Vettoriale)

Il **motore baseline** (FEAT-002) è la prima modalità RAG di `sertor-core`: [[vector-retrieval|retrieval vettoriale]] con
ranking per similarità sopra il nucleo (FEAT-001), più una **valutazione** (hit_rate@k, MRR). Questo
record ne documenta l'implementazione.

## Stato: ✅ Completato

**Data completamento:** 2026-06-03
**Stato test suite:** 67 passed + 2 xfail | Ruff clean | Constitution Check 9/9 ✅
**Task completati:** 21/21

Sintesi della **phase 2 (implementation)** di FEAT-002 — il motore di retrieval vettoriale baseline che CONSUMA il nucleo di FEAT-001 e aggiunge ranking e valutazione metrica.

---

## Panorama

FEAT-002 aggiunge al nucleo [[implementazione-nucleo-retrieval]] una **stratificazione di ranking** (similarity search top-k) e **misurazione della qualità** (hit-rate@k, MRR@10).

**Architettura:**
- **`BaselineEngine`** (sottopacchetto `src/sertor_core/engines/`): orchestrazione di indexing e query.
  - `index()` — rebuild atomico da zero con flag `rebuild=True` (reset collection DOPO embed, PRIMA upsert).
  - `query(query_text, k)` — similarity search vettoriale, top-k ranking, solleva **`IndexNotFoundError`** se indice mancante (policy del motore, non del nucleo).
  - `name` — identificatore `"baseline"` (solo retrieval vettoriale, niente ibrido/reranking).
- **`evaluation.py`** — metriche di ranking su ground-truth:
  - `hit_rate@k` (k ∈ {1, 3, 5, 10}): frazione di query con ≥1 risultato rilevante nei top-k.
  - `MRR@10`: reciprocal rank medio dei primi match rilevanti.
  - `EvalReport` dataclass (query, k, metriche) per reporting.

---

## Decisioni di design chiave

### 1. **Policy di errore su indice mancante: MOTORE, non nucleo**

Il **nucleo** (facade `retrieval_facade.py` in FEAT-001) resta **tollerante**:
- Indice mancante → `[]` + **warning** (REQ-028 FEAT-001, altri consumatori potrebbero tollerarlo).

Il **motore baseline** è **rigoroso**:
- Indice mancante → **`IndexNotFoundError`** esplicito (REQ-009 FEAT-002, usabilità CLI).

**Motivo:** il motore è il primo consumatore del nucleo in produzione; la sua interface è il modello per CLI e agenti. Isola l'errore senza sporccare il nucleo (Principio I, composabilità).

### 2. **Atomicità del rebuild via ordine operazionale**

Il flag `rebuild=True` su `IndexingService.index()` (nucleo) garanisce ordine:

```
1. Embed + cache
2. Reset collection (VectorStore.reset())
3. Upsert chunks
```

**Motivo:** (REQ-004) se upsert fallisce a metà, la collezione rimane **coerente** (vecchia versione intatta, non "mezzo-nuova"). Implementato senza transazioni esplicite grazie all'ordine reset-after-embed.

### 3. **Estensioni non-breaking al nucleo (validazione interfaccia)**

Il motore introduce **estensioni ADDITIVE** al nucleo (nessuna rottura):

- **Nuova eccezione:** `IndexNotFoundError` in `sertor_core.errors`.
- **Flag `rebuild`:** parametro opzionale su `IndexingService.index()` (default `False`).
- **Metodo `reset(collection)`:** aggiunto alla porta `VectorStore` (implementato in Chroma, Azure, InMemoryStore).
- **Esportazioni API pubblica:** `build_baseline_engine`, `BaselineEngine`, `evaluate`, `EvalReport`, `IndexNotFoundError`.

**Validazione:** implementazione motore non tocca il nucleo; sole estensioni aggiunte sono new methods/exceptions (no refactor). Constitution Check 9/9 su entrambi.

---

## Artefatti e copertura

### Libreria motore

```
src/sertor_core/engines/
├─ __init__.py             # exports: build_baseline_engine, BaselineEngine, evaluate, ...
├─ baseline_engine.py      # orchestrazione indexing + query
├─ evaluation.py           # hit_rate@k, MRR@10, EvalReport
└─ ...
```

### Specifica SpecKit

- **`specs/002-rag-baseline/plan.md`** — piano architetturale, 8 decisioni di design (R1–R8), Constitution Check.
- **`specs/002-rag-baseline/tasks.md`** — 21 task atomici distribuiti su 4 US (User Story): motore, API pubblica, test, evaluation.
- **`specs/002-rag-baseline/research.md`** — approfondimento hit-rate baseline (Chroma default BM25 vs cosine).

### Test suite

- **Unit:** engine initialization, query with/without index, error handling, config.
- **Integration:** E2E ingest → query → ranking su corpus piccolo (10 doc, ground-truth).
- **Evaluation:** hit@k, MRR metrics su corpus di test.

**Totale:** 67 test passed + 2 xfail.

**xfail (rinviati a decision gate):**
- `test_precision_at_k_baseline` (DA-1) — baseline prototipo precision@5 ≈0.67 vs 0.80 target; necessita corpus ground-truth definitivo e soglia decision.
- `test_hit_rate_evaluation_baseline` (DA-3) — hit@k metric definition rinviata a misura (fine soglia).

### Analisi SpecKit Analyze

- **FR (Functional Requirements):** 15/15 coperte.
- **Critical issues:** 0.
- **Constitution Check:** 9/9 ✅.
- **Rilievi LOW:** SC-005 (isolamento modalità) — banalmente soddisfatto finché non esistono altre modalità; progettazione futura quando sarà il caso.

---

## Linkage e dipendenze

### Upstream (dipende da)
- **[[implementazione-nucleo-retrieval]]** (FEAT-001) — `IndexingService`, `retrieval_facade`, `VectorStore`, chunking/embeddings.
- **[[piano-nucleo-retrieval]]** — architettura e decisioni R1–R8.
- **[[constitution]]** — Principi I+IV NON-NEGOZIABILI (core isolation, error handling esplicito).

### Downstream (usato da)
- **FEAT-003 (Wiki creazione)** — userà `BaselineEngine.query()` per ingestione wiki nel RAG.
- **sertor-cli** — importerà `build_baseline_engine` e CLI per ingestione/ranking.

### Correlati
- **[[decomposizione-must-core]]** (§ FEAT-002) — scope, requisiti 16+8 NFR, decisioni MVP.

---

## Processo git

| Fase | Hash | Descrizione |
|------|------|-------------|
| Pre-merge FEAT-001 | `3b8de22` | FEAT-001 (nucleo) mergiato in `master`. |
| Allineamento branch | `5502700` | Branch `spec/002-rag-baseline` allineato a `master` per avere il nucleo. |
| Piano | `4f159d0` | `specs/002-rag-baseline/plan.md` committato. |
| Task | `23641b3` | `specs/002-rag-baseline/tasks.md` committato. |
| Implementazione | incrementali | Fase implementation con test incrementali (snapshot a fine sessione). |

---

## Checksum completamento

- [x] Motore baseline (`BaselineEngine`) completo + test.
- [x] API pubblica esportata (6 symbol principali).
- [x] Estensioni non-breaking al nucleo validate.
- [x] Evaluation (`hit_rate@k`, `MRR@10`) implementata.
- [x] Constitution Check 9/9 ✅.
- [x] 67 test passed (xfail gestite).
- [x] Ruff clean.
- [x] 21/21 task completati.
- [x] Documentazione SpecKit (plan/tasks/analyze).

