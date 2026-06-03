---
description: "Task list — Motore RAG vettoriale baseline (FEAT-002)"
---

# Tasks: Motore RAG vettoriale (baseline)

**Input**: Design documents from `specs/002-rag-baseline/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅;
**FEAT-001 in `master`** (nucleo consumato da questa feature).

**Tests**: INCLUSI (Principio V; REQ-016/NFR-006; SC-002/003).

**Organization**: per user story (P1×2, P2×3). Il motore vive in `src/sertor_core/engines/` e
**consuma** il nucleo. Una fase Foundational applica le **estensioni additive** al nucleo
(reset/rebuild/IndexNotFoundError) che sbloccano le user story.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [x] T001 Create engine subpackage `src/sertor_core/engines/__init__.py` (docstring: motori RAG/modalità)

---

## Phase 2: Foundational (estensioni additive al nucleo — BLOCCANTI)

**⚠️ CRITICAL**: necessarie a tutte le user story; additive e non-breaking verso FEAT-001.

- [x] T002 [P] Add `IndexNotFoundError(SertorError)` (campo `collection`, messaggio azionabile) in `src/sertor_core/domain/errors.py` (REQ-009, data-model)
- [x] T003 Add `reset(collection: str) -> None` alla porta `VectorStore` in `src/sertor_core/domain/ports.py` (REQ-002)
- [x] T004 [P] Implement `reset()` in `src/sertor_core/adapters/vectorstores/chroma.py` (delete_collection idempotente; errori → `VectorStoreError`) (REQ-002)
- [x] T005 [P] Implement `reset()` in `src/sertor_core/adapters/vectorstores/azure_search.py` (delete index/documents; errori → `VectorStoreError`) (REQ-002)
- [x] T006 [P] Implement `reset()` in `InMemoryStore` mock in `tests/fixtures/mocks.py` (svuota la collezione)
- [x] T007 Add `rebuild: bool = False` a `IndexingService.index()` in `src/sertor_core/services/indexing.py`: quando True esegue `store.reset(collection)` **dopo** l'embed e **prima** dell'upsert (atomicità su errore provider, REQ-002/004)
- [x] T008 Export `IndexNotFoundError` in `src/sertor_core/__init__.py` (API pubblica)

**Checkpoint**: nucleo esteso (reset/rebuild/errore) → il motore può essere costruito

---

## Phase 3: User Story 1 - Creare un indice vettoriale (Priority: P1) 🎯 MVP

**Goal**: indicizzare una codebase producendo un indice vettoriale persistente, con report e rebuild atomico.

**Independent Test**: dato un repo + provider, `index()` produce un indice con tutti i chunk e un report (chunks+dim); provider down → nessun indice parziale.

### Tests for User Story 1 ⚠️

- [x] T009 [P] [US1] Test in `tests/unit/test_baseline_engine.py` (parte index): `index()` produce `IndexReport` con chunks≥documents e `embedding_dim` (REQ-001/003); provider down in index → `EmbeddingError`, indice preesistente intatto (REQ-004) usando un embedder che fallisce

### Implementation for User Story 1

- [x] T010 [US1] Implement `BaselineEngine.__init__` + `index(root)` in `src/sertor_core/engines/baseline.py`: delega a `IndexingService(...).index(root, rebuild=True)`; log strutturato (operation=index, provider, chunks, dim, tempi) (REQ-001/003/015)
- [x] T011 [US1] Add `build_baseline_engine(settings)` in `src/sertor_core/composition.py` (cabla embedder+store+collection_name+default_k+settings) (REQ-012)

**Checkpoint**: US1 testabile (indicizzazione + rebuild atomico)

---

## Phase 4: User Story 2 - Interrogare per similarità (Priority: P1)

**Goal**: query testuale → top-k chunk con metadati; errore esplicito se l'indice manca.

**Independent Test**: con indice esistente, una query nota restituisce top-k con (path, doc_type, chunk_id, score, text); k configurabile; indice mancante → errore.

### Tests for User Story 2 ⚠️

- [x] T012 [P] [US2] Test in `tests/unit/test_baseline_engine.py` (parte query): top-k con campi richiesti (REQ-006/007); `k` dato/override/oversize (REQ-008); indice mancante → `IndexNotFoundError` (REQ-009); provider down → `EmbeddingError` (REQ-010)

### Implementation for User Story 2

- [x] T013 [US2] Implement `BaselineEngine.query(query, k=None)` in `src/sertor_core/engines/baseline.py`: se `not store.exists(collection)` → `IndexNotFoundError` (REQ-009); altrimenti embed query (stesso provider) → `store.query(k, doc_type="both")` → `list[RetrievalResult]`; `k` da Settings se assente; log strutturato (REQ-005/006/007/008/010/015)

**Checkpoint**: US2 testabile (query + errore esplicito su indice mancante)

---

## Phase 5: User Story 3 - Idempotenza del re-index (Priority: P2)

**Goal**: re-index sulla stessa codebase invariata → indice stabile, nessun duplicato.

**Independent Test**: indicizzare due volte e verificare stesso n. di chunk e stessi risultati alle stesse query.

### Tests for User Story 3 ⚠️

- [x] T014 [P] [US3] Integration test in `tests/integration/test_baseline_idempotence.py`: due `index()` consecutivi su `sample_repo` → stesso n. chunk e stessi top-k alla stessa query (SC-003); rebuild rimuove chunk di file non più presenti (REQ-002)

> Impl: coperta da T007 (rebuild) + T010; questa fase **verifica** l'idempotenza end-to-end.

**Checkpoint**: US3 verificata (rebuild idempotente)

---

## Phase 6: User Story 4 - Valutare la pertinenza (Priority: P2)

**Goal**: hit-rate@k (k∈{1,3,5,10}) e MRR@10 su un ground-truth fornito.

**Independent Test**: dato un ground-truth su un indice popolato, `evaluate` riporta hit-rate@k e MRR coerenti.

### Tests for User Story 4 ⚠️

- [x] T015 [P] [US4] Test in `tests/unit/test_evaluation.py`: hit@k coerente con risultati attesi (REQ-011); MRR su ranghi noti; ground-truth vuoto → metriche 0 senza errore
- [x] T016 [P] [US4] Quality test (xfail) in `tests/integration/test_baseline_quality.py`: soglia hit@5 vs baseline prototipo, `xfail` finché ground-truth reale assente (SC-002, DA-1/DA-3)

### Implementation for User Story 4

- [x] T017 [US4] Implement `evaluate(engine, ground_truth, ks=(1,3,5,10)) -> EvalReport` + `EvalReport` in `src/sertor_core/engines/evaluation.py`: hit-rate@k e MRR@10; pertinente se `RetrievalResult.path ∈ expected_paths` (REQ-011)

**Checkpoint**: US4 testabile (metriche di qualità)

---

## Phase 7: User Story 5 - Configurabilità provider e selezione modalità (Priority: P2)

**Goal**: provider via config; baseline come modalità con nome stabile, solo retrieval vettoriale.

**Independent Test**: cambiare provider via config senza modifiche al codice; la baseline usa solo il vettoriale.

### Tests for User Story 5 ⚠️

- [x] T018 [P] [US5] Test in `tests/unit/test_baseline_engine.py` (parte mode/config): `engine.name == "baseline"` (REQ-013); `build_baseline_engine` con backend local → embedder Ollama + store Chroma (REQ-012); con backend azure → componenti azure (no modifiche al codice)

### Implementation for User Story 5

- [x] T019 [US5] Set `BaselineEngine.name = "baseline"` (attributo di classe) e documentare in docstring che usa solo retrieval vettoriale (no ibrido/grafo/agentico) (REQ-013/014); export `BaselineEngine` + `build_baseline_engine` in `src/sertor_core/__init__.py`

**Checkpoint**: US5 verificata (config provider + identità modalità)

---

## Phase 8: Polish & Cross-Cutting

- [x] T020 Integration test repo-agnosticità in `tests/integration/test_baseline_two_corpora.py`: indicizza 2 repo distinti (sample_repo + repo tmp) e interroga ciascuno isolatamente (SC-001/SC-005-isolamento)
- [x] T021 [P] Run full suite + ruff; aggiorna `src/sertor_core/README.md` con la sezione "Motore baseline" (uso index/query/evaluate)

---

## Dependencies & Execution Order

- **Setup (P1)** → **Foundational (P2)**: T002–T008 sbloccano tutto. T003 prima di T004/T005/T006; T007 dopo T003.
- **US1 (P3)**: dopo Foundational. T010 dopo T007; T011 dopo T010.
- **US2 (P4)**: dopo Foundational + T002. T013 dopo T011.
- **US3 (P5)**: dopo US1 (usa index). Verifica.
- **US4 (P6)**: dopo US2 (usa query). T017 prima di T015/T016 esecuzione, ma test scritti prima (TDD).
- **US5 (P7)**: dopo US1/US2 (usa build + engine).
- **Polish (P8)**: dopo le user story.

### Parallel Opportunities
- Foundational: T002, T004, T005, T006 in parallelo (T003 prima di T004/05/06; T007 dopo T003).
- Test [P] di story diverse parallelizzabili.

---

## Implementation Strategy

MVP = Setup + Foundational + US1 + US2 (ciclo index↔query completo). Poi US3 (idempotenza), US4
(misura qualità), US5 (config/modalità), Polish. Ogni fase è un incremento testabile.

## Notes

- Il motore **consuma** il nucleo: niente duplicazione di ingestione/chunking/embeddings/store (DRY).
- Estensioni al nucleo (reset/rebuild/IndexNotFoundError) sono additive e non-breaking (R-N1).
- Commit per checkpoint (delega al `configuration-manager`).
- **Mapping requisiti→story**: US1=REQ-001..004; US2=REQ-005..010; US3=REQ-002(idemp.); US4=REQ-011;
  US5=REQ-012..015; trasversali REQ-015/016 su tutte.
