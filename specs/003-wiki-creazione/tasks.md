---
description: "Task list — Skill LLM Wiki: creare/indicizzare (FEAT-003)"
---

# Tasks: Skill LLM Wiki (creare/indicizzare)

**Input**: Design documents from `specs/003-wiki-creazione/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅;
**FEAT-001/002 in `master`** (nucleo + baseline; il Gruppo E li consuma).

**Tests**: INCLUSI (Principio V; RNF-002; SC-002/004). Tutti su **wiki sandbox in temp** (R-W5).

**Organization**: per user story. La skill vive in `src/sertor_core/wiki/`. Foundational = convenzioni
+ estensioni additive al nucleo (porta LLMProvider, LLMNotConfiguredError) per la distillazione.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [x] T001 Create `src/sertor_core/wiki/__init__.py` e `src/sertor_core/adapters/llm/__init__.py` (docstring)

---

## Phase 2: Foundational (convenzioni + estensioni additive — BLOCCANTI)

- [x] T002 Implement `src/sertor_core/wiki/conventions.py`: enum aree tematiche→cartelle, `Brief`, `SourceBrief`, render frontmatter YAML (title/type/tags/created/updated/sources), kebab-case da titolo, formato voce log `## [YYYY-MM-DD] <op> | <title>` (REQ-003/004/005)
- [x] T003 [P] Add `LLMProvider` Protocol (`name`, `generate(prompt, system=None)->str`) in `src/sertor_core/domain/ports.py` [additivo]
- [x] T004 [P] Add `LLMNotConfiguredError(SertorError)` in `src/sertor_core/domain/errors.py` + export in `src/sertor_core/__init__.py` (REQ-031)
- [x] T005 [P] Implement Ollama LLM adapter in `src/sertor_core/adapters/llm/ollama.py` (chat `/api/chat` via httpx; errori → SertorError)
- [x] T006 [P] Implement Azure LLM adapter in `src/sertor_core/adapters/llm/azure.py` (`/chat/completions`; import/segreti lazy)
- [x] T007 Add `build_llm(settings)` in `src/sertor_core/composition.py` (provider chat da config) + chiavi chat in `Settings` (modello/deployment)
- [x] T008 [P] Add `FakeLLM` (deterministico) in `tests/fixtures/mocks.py`

**Checkpoint**: convenzioni + porta LLM pronte → le operazioni possono essere implementate

---

## Phase 3: User Story 1 - Inizializzare la struttura (Priority: P1) 🎯 MVP

**Goal**: creare la struttura standard del wiki in un'invocazione, senza sovrascrivere un wiki esistente.

**Independent Test**: create su repo senza wiki → cartelle + index/log conformi; re-invoke su wiki esistente → nessuna sovrascrittura.

### Tests for US1 ⚠️
- [x] T009 [P] [US1] Test in `tests/unit/test_wiki_structure.py`: create produce cartelle tematiche + `index.md`/`log.md` conformi (REQ-001); re-invoke non sovrascrive index/log (REQ-002); pagina con frontmatter/kebab-case/wikilink (REQ-003/004/005)

### Implementation for US1
- [x] T010 [US1] Implement `create_wiki(root, today=None)` in `src/sertor_core/wiki/structure.py`: crea cartelle se assenti, `index.md`/`log.md` minimi solo se assenti (non-distruttivo), log strutturato (REQ-001/002/006)

**Checkpoint**: US1 testabile (init non-distruttivo)

---

## Phase 4: User Story 2 - Documentare in continuo (record) (Priority: P1)

**Goal**: da un brief, creare/aggiornare la pagina, aggiornare index e appendere una voce log, senza duplicati.

**Independent Test**: record con un brief → pagina corretta + link in index + 1 voce log; re-run identico → nessun duplicato.

### Tests for US2 ⚠️
- [x] T011 [P] [US2] Test in `tests/unit/test_wiki_operations.py` (parte record): record crea pagina nel tema (no duplicati), `index.md` con link+sommario, **1** voce `log.md` (REQ-010/011/012)

### Implementation for US2
- [x] T012 [US2] Implement `record(root, brief, today=None)` in `src/sertor_core/wiki/operations.py`: path tema da kind+titolo (kebab-case), scrivi solo se il contenuto cambia, aggiorna index, append 1 voce log; log strutturato (REQ-010/011/012/013)

**Checkpoint**: US2 testabile (record con dedup)

---

## Phase 5: User Story 4 - Idempotenza delle operazioni (Priority: P1)

**Goal**: re-run su input invariato → output identico (no file/voci/timestamp nuovi).

**Independent Test**: eseguire due volte create e record su input invariato → hash file invariato, nessun duplicato.

### Tests for US4 ⚠️
- [x] T013 [P] [US4] Test in `tests/integration/test_wiki_idempotence.py`: doppio create → file identici (hash) (SC-002); doppio record stesso brief → `changed=False`, nessuna 2ª voce log (REQ-013/050); `updated` non cambia su file invariati

> Impl: coperta da T010/T012 (scrivi-solo-se-cambia); questa fase **verifica** l'idempotenza.

**Checkpoint**: US4 verificata (idempotenza strutturale)

---

## Phase 6: User Story 3 - Indicizzare il wiki nel RAG (Priority: P1)

**Goal**: ingerire le pagine del wiki nel corpus RAG (full rebuild), interrogabili come corpus paritario.

**Independent Test**: con wiki + RAG configurato, index_wiki → query documentale trova pagine wiki.

### Tests for US3 ⚠️
- [x] T014 [P] [US3] Integration test in `tests/integration/test_wiki_indexing.py` (FakeEmbedder+ChromaStore temp): index_wiki ingerisce i `.md` (REQ-040/042); query doc trova una pagina wiki (SC-004); re-index senza duplicati, id=path (REQ-041/051); radice vuota → warning + indice immutato (REQ-045)

### Implementation for US3
- [x] T015 [US3] Implement `index_wiki(wiki_root, settings=None)` in `src/sertor_core/wiki/indexing.py`: costruisce embedder+store dal nucleo e delega a `IndexingService(...).index(wiki_root, rebuild=True)`; radice vuota → warning senza modificare l'indice; errori store → propagati (REQ-040..045)

**Checkpoint**: US3 testabile (indicizzazione via nucleo)

---

## Phase 7: User Story 5 - Ingest di fonti esterne (Priority: P2)

**Goal**: incorporare una fonte in `sources/`, propagare i riferimenti, marcare le contraddizioni.

### Tests for US5 ⚠️
- [x] T016 [P] [US5] Test in `tests/unit/test_wiki_operations.py` (parte ingest): pagina `sources/` con reference nel frontmatter (REQ-020); propagazione del riferimento nelle pagine correlate esistenti (REQ-021); index+log `ingest` (REQ-022); contraddizione marcata (REQ-023)

### Implementation for US5
- [x] T017 [US5] Implement `ingest(root, source, today=None)` in `src/sertor_core/wiki/operations.py`: crea/aggiorna pagina `sources/`, propaga ref nelle pagine `related` esistenti, marca `contradicts`, append voce log `ingest` (REQ-020..023)

**Checkpoint**: US5 testabile (ingest + contraddizioni)

---

## Phase 8: User Story 6 - Distillare conversazioni (Priority: P2)

**Goal**: da un brief condensato + LLM, produrre una pagina distillata conforme; errore se manca l'LLM.

### Tests for US6 ⚠️
- [x] T018 [P] [US6] Test in `tests/unit/test_wiki_distill.py` (FakeLLM): distill produce pagina conforme nel tema + voce log `record` (REQ-030/032/033); senza LLM → `LLMNotConfiguredError` (REQ-031)

### Implementation for US6
- [x] T019 [US6] Implement `distill(root, brief, llm, today=None)` in `src/sertor_core/wiki/distill.py`: se `llm is None` → `LLMNotConfiguredError`; altrimenti `llm.generate(...)` → corpo pagina, scrivi pagina conforme + 1 voce log; idempotenza strutturale (REQ-030..033)

**Checkpoint**: US6 testabile (distill con LLM)

---

## Phase 9: Polish & Cross-Cutting

- [x] T020 Integration test repo-agnosticità in `tests/integration/test_wiki_two_repos.py`: create+record+index_wiki su 2 radici wiki temp distinte senza modifiche al codice (SC-005)
- [x] T021 [P] Run full suite + ruff; aggiorna `src/sertor_core/README.md` con sezione "Skill LLM Wiki" (create/record/ingest/distill/index_wiki)

---

## Dependencies & Execution Order

- **Setup → Foundational**: T002–T008 sbloccano tutto. T003 prima di T005/T006; T004 con T003.
- **US1 (P3)**: dopo Foundational (conventions). T010 dopo T002.
- **US2 (P4)**: dopo US1 (struttura). T012 dopo T010.
- **US4 (P5)**: dopo US1/US2 (verifica idempotenza).
- **US3 (P6)**: dopo Foundational; consuma il nucleo (in master).
- **US5 (P7)**: dopo US2 (riusa primitive di pagina).
- **US6 (P8)**: dopo Foundational (LLM) + US2.
- **Polish (P9)**: dopo le user story.

### Parallel Opportunities
- Foundational: T003/T004/T005/T006/T008 in parallelo (T002 e T007 sequenziali rispetto agli adapter).
- Test [P] di story diverse parallelizzabili.

---

## Implementation Strategy

MVP = Setup + Foundational + US1 (create) + US2 (record) + US4 (idempotenza) + US3 (index). Poi US5
(ingest) e US6 (distill) come secondo incremento. Sequenza A→B→F→E→C/D (da §9 requirements).

## Notes

- La skill **consuma** il nucleo per l'indicizzazione (DRY); niente reimplementazione del RAG.
- Estensioni al nucleo (LLMProvider, LLMNotConfiguredError) additive e usate solo da distill.
- Tutti i test su wiki sandbox in temp (mai sul wiki di produzione).
- Commit per checkpoint (delega al `configuration-manager`).
- **Mapping requisiti→story**: US1=REQ-001..006; US2=REQ-010..013; US3=REQ-040..045/051; US4=REQ-050;
  US5=REQ-020..023; US6=REQ-030..033; trasversali REQ-013/RNF-004 su tutte.
