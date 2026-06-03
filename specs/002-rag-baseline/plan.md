# Implementation Plan: Motore RAG vettoriale (baseline)

**Branch**: `spec/002-rag-baseline` | **Date**: 2026-06-03 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-rag-baseline/spec.md` (deriva da FEAT-002, fonte EARS
`requirements/sertor-core/rag-baseline/requirements.md`). **Dipende da FEAT-001** (nucleo, già in
`master`).

## Summary

Il motore baseline è la **prima modalità RAG** e la dimostrazione di CS-1 ("creare un RAG
interrogabile"): indicizza una codebase in un indice vettoriale e la interroga per similarità,
restituendo i top-k chunk con metadati. È un **motore sottile sopra il nucleo di FEAT-001**: consuma
ingestione, chunking, embeddings e vector store tramite la loro interfaccia pubblica (porte +
composition root) e **non li ridefinisce** (Principio III, D-1). Aggiunge tre cose proprie:
(1) **rebuild-from-scratch idempotente** dell'indice, (2) **policy di errore esplicito** su indice
mancante/provider non disponibile, (3) **valutazione della pertinenza** (hit-rate@k, MRR@10).

L'approccio tecnico è un nuovo componente `engines/baseline.py` che orchestra le primitive del
nucleo. Implementarlo **valida l'interfaccia di FEAT-001** (rischio R-N1 di FEAT-001) e ne richiede
una **estensione additiva minima**: un metodo `reset(collection)` sulla porta `VectorStore` (per il
rebuild-from-scratch) e un flag `rebuild` sull'orchestratore di indicizzazione. Le soglie di
pertinenza/performance restano misurate sul prototipo come baseline (DA-1/DA-3).

## Technical Context

**Language/Version**: Python ≥ 3.11 (eredita da FEAT-001).

**Primary Dependencies**: nessuna nuova dipendenza esterna — il motore usa il nucleo `sertor_core`
(domain/services/adapters/composition) e la stdlib. Embeddings/vector store restano dietro le porte
del nucleo (Ollama/Azure, Chroma/Azure Search).

**Storage**: l'indice vettoriale persistente del nucleo (Chroma locale di default), in una collezione
namespaced per (corpus, provider) — già fornita da FEAT-001 `collection_name`.

**Testing**: `pytest`. Test con `FakeEmbedder` + `InMemoryStore`/`ChromaStore` (NFR-006, no cloud).
Idempotenza (SC-003), errori (indice mancante, provider down), valutazione (hit-rate@k/MRR).

**Target Platform**: Linux + Windows (NFR-008), come il nucleo.

**Project Type**: estensione della libreria `sertor_core` — nuovo sottopacchetto `engines/`. Non CLI.

**Performance Goals**: soglie non fissate a priori (DA-1): misurate in test sul prototipo come
baseline (hit@5 ≈ 0.80 cloud, ≈ 0.67 locale; retrieval orientativo < 2 s locale, NFR-003).

**Constraints**: non duplicare le primitive del nucleo (consumarle); rebuild **atomico** rispetto
agli errori di provider (NFR-004); segreti solo da env (REQ-E5); local-only senza rete cloud.

**Scale/Scope**: ≥ 2 codebase (SC-001), ≥ 2 provider (SC-004); un solo indice attivo per provider
(DA-4, REQ-005 resta Could); no generazione LLM, no multi-tenant (fuori MVP).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** il motore vive in `sertor_core/engines/`,
  importa solo entità/porte/servizi del nucleo e il composition root; non importa SDK di provider né
  la CLI. Esercitabile con `FakeEmbedder`/`InMemoryStore`. → **PASS.**
- [x] **II — Boundary & local-first:** usa le porte `EmbeddingProvider`/`VectorStore` del nucleo;
  provider/backend scelti da config; gira in locale (Ollama+Chroma). → **PASS.**
- [x] **III — YAGNI & unità piccole:** il motore è sottile (orchestrazione); **riusa** il nucleo
  (DRY), niente registry di modalità sovra-progettato (solo un nome stabile). L'estensione del nucleo
  è minima e giustificata (reset per il rebuild). → **PASS.**
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** indice mancante → `IndexNotFoundError`
  esplicito (REQ-009), **non** lista vuota silenziosa; provider down in query → `EmbeddingError`
  propagato (REQ-010); rebuild atomico → nessun indice parziale su errore (REQ-004/NFR-004). → **PASS.**
- [x] **V — Testabilità & misure:** suite F.I.R.S.T. con mock; la **valutazione hit-rate@k/MRR è una
  capacità di prima classe** del motore (REQ-011) — la qualità è misurata per definizione. → **PASS.**
- [x] **VI — Idempotenza & non-distruttività:** rebuild-from-scratch → stesso n. di chunk e stessi
  risultati a input invariato (SC-003); install≠run (indicizza solo su chiamata). → **PASS.**
- [x] **VII — Leggibilità:** naming di dominio (`index`/`query`/`evaluate`/`rebuild`/`hit_rate`/`mrr`). → **PASS.**
- [x] **VIII — Configurabilità centralizzata:** provider, `k`, percorsi da `Settings` del nucleo;
  nessun default hardcoded nel motore. → **PASS.**
- [x] **IX — Osservabilità:** index e query emettono log strutturati (operazione, provider, conteggi,
  tempi, errori) riusando `observability.logging` del nucleo. → **PASS.**

**Esito gate (pre-Phase 0):** ✅ PASS su tutti i 9 principi (inclusi I e IV). Nessuna violazione →
Complexity Tracking vuoto.

> **Nota di evoluzione del nucleo (non una violazione):** FEAT-002 estende FEAT-001 in modo
> **additivo e non-breaking** (metodo `reset` sulla porta `VectorStore`, flag `rebuild`
> sull'orchestratore, eccezione `IndexNotFoundError`). È esattamente la validazione d'interfaccia
> prevista dal rischio R-N1 di FEAT-001. Gli adapter esistenti restano compatibili.

## Project Structure

### Documentation (this feature)

```text
specs/002-rag-baseline/
├── plan.md              # Questo file
├── research.md          # Phase 0 — decisioni (R1..R6)
├── data-model.md        # Phase 1 — entità (EvalReport, GroundTruth, ...)
├── quickstart.md        # Phase 1 — uso del motore baseline come libreria
├── contracts/           # Phase 1 — contratti (baseline-engine, evaluation)
│   ├── baseline-engine.md
│   └── evaluation.md
├── checklists/
│   └── requirements.md  # checklist di qualità della spec (già ✅)
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

Estende il pacchetto `sertor_core` con il sottopacchetto `engines/`. Le frecce di dipendenza
restano verso l'interno: `engines/` → `services`/`domain`/`composition` del nucleo.

```text
src/sertor_core/
├── engines/                    # NUOVO — motori RAG (modalità)
│   ├── __init__.py
│   ├── baseline.py             # BaselineEngine: index(rebuild) / query / name (REQ-001..014)
│   └── evaluation.py           # hit_rate@k + MRR@10 su ground-truth (REQ-011)
├── domain/errors.py            # + IndexNotFoundError (REQ-009) [estensione additiva]
├── domain/ports.py             # + VectorStore.reset(collection) [estensione additiva]
├── services/indexing.py        # + flag rebuild in index() (reset prima dell'upsert) [additivo]
├── adapters/vectorstores/
│   ├── chroma.py               # + reset() (delete_collection) [additivo]
│   └── azure_search.py         # + reset() [additivo]
└── composition.py              # + build_baseline_engine(settings) [additivo]

tests/
├── unit/
│   ├── test_baseline_engine.py     # index/query/k/errori/mode (US1,US2,US5)
│   └── test_evaluation.py          # hit-rate@k + MRR (US4)
├── integration/
│   └── test_baseline_idempotence.py# rebuild-from-scratch stabile (US3, SC-003)
└── fixtures/                       # riuso mocks + sample_repo di FEAT-001
```

**Structure Decision**: nuovo sottopacchetto `engines/` dentro `sertor_core` (i motori RAG fanno
parte del *core* per la costituzione). Il motore è un **consumatore** del nucleo: tutta la logica di
ingestione/chunking/embeddings/store resta in FEAT-001 (DRY). Le uniche modifiche al nucleo sono
estensioni additive necessarie e riusabili (reset, rebuild, IndexNotFoundError), non duplicazioni.

## Complexity Tracking

> Nessuna violazione del Constitution Check.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
