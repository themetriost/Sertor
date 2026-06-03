---
description: "Task list — Nucleo di retrieval condiviso (FEAT-001)"
---

# Tasks: Nucleo di retrieval condiviso

**Input**: Design documents from `specs/001-nucleo-retrieval/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: INCLUSI. La costituzione (Principio V — testabilità & misure) e i requisiti (NFR-01,
SC-004, SC-005) richiedono test automatici; ogni contratto in `contracts/` definisce contract test.

**Organization**: task raggruppati per user story (P1×5, P2×1), su base Clean Architecture
(`src/sertor_core/`: domain ← services / adapters; composition root). Le dipendenze puntano verso
l'interno (Principio I).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: eseguibile in parallelo (file diverso, nessuna dipendenza da task incompleti)
- **[Story]**: user story di appartenenza (US1..US6)
- Ogni task indica il path esatto

## Path Conventions

Single project a libreria: `src/sertor_core/`, `tests/` alla radice del repo (da `plan.md`).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: inizializzazione del pacchetto e struttura

- [x] T001 Create package structure per plan.md: `src/sertor_core/{domain,services,services/chunking,adapters/embeddings,adapters/vectorstores,config,observability}/__init__.py` e `tests/{unit,integration,fixtures}/`
- [x] T002 Initialize Python project in `pyproject.toml` (Python ≥3.11, build backend, package `sertor_core` in `src/`); dipendenze base: `httpx`, `chromadb`, `python-dotenv`, `tree-sitter`, `tree-sitter-language-pack`; extra opzionali `[azure]`; dev: `pytest`
- [x] T003 [P] Configure linting/formatting (`ruff` + config) e `pytest` (`[tool.pytest.ini_options]`, `testpaths=tests`) in `pyproject.toml`
- [x] T004 [P] Create `.env.example` con le chiavi di `Settings` (RAG_BACKEND, SERTOR_CORPUS, OLLAMA_*, AZURE_*, CHUNK_*, EMBED_BATCH_SIZE) e verifica che `.env`/`.index*` siano in `.gitignore`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: cuore di dominio + config/logging base + fixtures, condivisi da TUTTE le story

**⚠️ CRITICAL**: nessuna user story può iniziare prima del completamento di questa fase

- [x] T005 [P] Create domain entities in `src/sertor_core/domain/entities.py`: `DocType` (enum code/doc), `Document`, `ChunkMetadata` (code + markdown), `Chunk`, `RetrievalResult`, `IndexReport` (conteggi) — dataclass, nessun import di SDK esterni (data-model.md)
- [x] T006 [P] Create domain error hierarchy in `src/sertor_core/domain/errors.py`: `SertorError` → `ConfigError`, `IngestionError`, `EmbeddingError(provider, reason, retriable)`, `VectorStoreError(backend, reason)` (data-model.md §Errori; Principio IV)
- [x] T007 Create ports in `src/sertor_core/domain/ports.py`: `EmbeddingProvider` (`name`, `dim`, `batch_size`, `embed(texts)->list[list[float]]`) e `VectorStore` (`upsert`, `query`, `delete`, `exists`) come `Protocol` (contracts/embedding-provider.md, contracts/vector-store.md)
- [x] T008 [P] Implement centralized `Settings` in `src/sertor_core/config/settings.py`: legge env+file via `python-dotenv`, espone backend/corpus/embeddings/store/chunking/esclusioni/`default_k`/`batch_size`; default SOLO qui (REQ-030); nessun segreto su path versionati (REQ-032)
- [x] T009 [P] Implement structured logging in `src/sertor_core/observability/logging.py`: helper `get_logger` + emissione record con campi (operation, provider/backend, conteggi, dim, elapsed_ms, error) + `redact()` per segreti (REQ-031/032)
- [x] T010 [P] Create test fixtures in `tests/fixtures/`: mini-repo multi-linguaggio (≥ Python, JS, Go, Markdown, 1 file di linguaggio fuori-set, 1 file binario, 1 dir tipo `.venv`), `FakeEmbedder`(dim piccola, deterministico) e `InMemoryStore` (mock delle porte) in `tests/fixtures/mocks.py`

**Checkpoint**: dominio, config, logging e mock pronti → le user story possono partire

---

## Phase 3: User Story 1 - Ingestione repo-agnostica (Priority: P1) 🎯 MVP

**Goal**: scoprire e leggere codice + Markdown di un repo qualunque, escludendo artefatti/segreti, con id stabili.

**Independent Test**: puntare il nucleo su due repo e ottenere l'elenco dei documenti indicizzabili con id stabili, senza config hardcoded, senza artefatti/segreti.

### Tests for User Story 1 ⚠️

- [x] T011 [P] [US1] Test ingestione in `tests/unit/test_ingestion.py`: scoperta file indicizzabili + id = path relativo (REQ-001/004); esclusione configurabile (REQ-002); skip file illeggibile con warning (REQ-003); repo senza file → lista vuota senza errore (edge case)

### Implementation for User Story 1

- [x] T012 [US1] Implement ingestion service in `src/sertor_core/services/ingestion.py`: `discover(root, settings)` scoperta **ordinata** (sort path), lettura UTF-8 `errors=ignore`, rilevamento linguaggio da estensione, esclusione via `settings.exclude_patterns`, skip illeggibili (warning + continua), `Document.id` = path relativo POSIX (REQ-001..005)
- [x] T013 [US1] Add structured logging all'ingestione (operation=ingest, doc_count, skipped) usando `observability.logging` (REQ-031)

**Checkpoint**: US1 indipendentemente testabile (scoperta repo-agnostica)

---

## Phase 4: User Story 2 - Chunking code-aware multilinguaggio (Priority: P1)

**Goal**: chunk ai confini sintattici per il set MVP, fallback dimensionale per gli altri, Markdown per heading, id stabili.

**Independent Test**: file in più linguaggi del set → chunk = unità sintattiche con metadati; linguaggio fuori-set → fallback senza errore; Markdown → chunk per heading; re-chunk → stessi id.

### Tests for User Story 2 ⚠️

- [x] T014 [P] [US2] Test code chunking in `tests/unit/test_chunking_code.py`: chunk sintattici Python/JS/Go con metadati (qualname, node_type, righe) (REQ-006/007/011); idempotenza chunk_id (REQ-010)
- [x] T015 [P] [US2] Test fallback + markdown in `tests/unit/test_chunking_fallback_md.py`: linguaggio fuori-set → size_fallback senza errore (REQ-009); Markdown → confini heading + heading_path (REQ-008)

### Implementation for User Story 2

- [x] T016 [P] [US2] Implement code chunker in `src/sertor_core/services/chunking/code.py`: tree-sitter via `tree-sitter-language-pack`; mappa `language -> {def_types, class_types, name_field}` per i linguaggi del set; emit class/method/function/module con contesto classe in testa ai metodi; split oversize (riuso logica `prototype/shared/chunking_code.py`, generalizzata) (REQ-006/007/011)
- [x] T017 [P] [US2] Implement markdown chunker in `src/sertor_core/services/chunking/markdown.py`: split ai confini heading, `heading_path` gerarchico (REQ-008)
- [x] T018 [P] [US2] Implement size fallback in `src/sertor_core/services/chunking/fallback.py`: chunking dimensionale (size/overlap da config), nessun errore (REQ-009)
- [x] T019 [US2] Implement dispatcher in `src/sertor_core/services/chunking/dispatch.py`: `chunk_document(doc, settings)` seleziona code/markdown/fallback per doc_type+linguaggio; assegna `chunk_id = f"{doc.id}#{index}"` ordinale (REQ-010); `chunker` nei metadati (depends on T016, T017, T018)

**Checkpoint**: US2 testabile (chunking multilinguaggio + fallback + idempotenza)

---

## Phase 5: User Story 3 - Embeddings via provider intercambiabili (Priority: P1)

**Goal**: produrre vettori con un provider locale e uno cloud, scelti via config, a batch; local-only senza rete.

**Independent Test**: vettori con provider locale e cloud cambiando solo la config; in local-only nessuna chiamata cloud.

### Tests for User Story 3 ⚠️

- [x] T020 [P] [US3] Contract test in `tests/unit/test_embeddings.py`: output len/ordine preservati a batch (REQ-014); `texts` vuota → `[]`; provider down → `EmbeddingError(provider, reason, retriable)` (REQ-015); local-only nessuna connessione cloud via spia su client HTTP (REQ-016)

### Implementation for User Story 3

- [x] T021 [P] [US3] Implement Ollama adapter in `src/sertor_core/adapters/embeddings/ollama.py`: `EmbeddingProvider` via `httpx` `POST /api/embed`, batching, `dim` al primo batch, errori→`EmbeddingError` (REQ-012/013/016)
- [x] T022 [P] [US3] Implement Azure adapter in `src/sertor_core/adapters/embeddings/azure.py`: `httpx` `POST /embeddings` header `api-key`, riordino `data` per index, errori→`EmbeddingError`; import SDK/segreti lazy (REQ-013)
- [x] T023 [US3] Add embeddings factory in `src/sertor_core/composition.py` (`build_embedder(settings)`): seleziona provider da config; default ollama in local, azure in cloud (REQ-030)

**Checkpoint**: US3 testabile (embeddings intercambiabili, local-only)

---

## Phase 6: User Story 4 - Persistenza e interrogazione via vector store (Priority: P1)

**Goal**: persistere e interrogare chunk via un'unica astrazione, backend locale/cloud da config, collezioni namespaced.

**Independent Test**: due corpora in collezioni namespaced sullo stesso store → query di uno non ritorna l'altro; ripetere con un 2° backend cambiando solo la config.

### Tests for User Story 4 ⚠️

- [x] T024 [P] [US4] Contract test in `tests/unit/test_vectorstore.py` (su Chroma temp dir): upsert+query per similarità (REQ-017); isolamento namespace tra 2 corpora (REQ-019); filtro doc_type senza indici separati (REQ-027); k>disponibili → tutti; collezione assente → `query`=[] / `exists`=False (REQ-028); upsert idempotente (no duplicati)
- [x] T025 [P] [US4] Test errore backend in `tests/unit/test_vectorstore_errors.py`: backend non disponibile → `VectorStoreError(backend, reason)`, non vuoto silenzioso (REQ-021)

### Implementation for User Story 4

- [x] T026 [P] [US4] Implement Chroma adapter in `src/sertor_core/adapters/vectorstores/chroma.py`: `VectorStore` con persistenza locale, collezioni namespaced `{corpus}-{provider}-{dim}`, filtro su metadato `doc_type`, `exists`, errori→`VectorStoreError` (REQ-017/018/019/021/022)
- [x] T027 [P] [US4] Implement Azure AI Search adapter in `src/sertor_core/adapters/vectorstores/azure_search.py`: `VectorStore` su vector index, import SDK lazy (extra `[azure]`), filtro su `doc_type` (REQ-018)
- [x] T028 [US4] Add vector store factory in `src/sertor_core/composition.py` (`build_store(settings)`): seleziona backend da config; calcolo nome collezione namespaced (REQ-018/019/030)

**Checkpoint**: US4 testabile (persistenza/interrogazione, namespace, 2 backend)

---

## Phase 7: User Story 5 - Facade di retrieval riusabile come libreria (Priority: P1)

**Goal**: unico punto d'accesso (code/doc/combined) importabile come libreria, indipendente dal backend.

**Independent Test**: da un modulo consumatore importare la facade e ottenere risultati pertinenti con metadati stabili, senza accedere a store/embeddings; gestione indice vuoto.

### Tests for User Story 5 ⚠️

- [x] T029 [P] [US5] Contract test in `tests/unit/test_retrieval_facade.py` (mock embedder+store): risultati con text/path/chunk_id/doc_type/score (REQ-025); filtro tipo (REQ-027); k/default e oversize (REQ-026); indice vuoto → [] + warning, no eccezione (REQ-028); errori propagati (REQ-012/021); uso come libreria importata (REQ-029)
- [x] T030 [P] [US5] Quality test in `tests/integration/test_precision_at_k.py`: `precision@5` su corpus ground-truth (fixture) con baseline = prototipo; soglia registrata quando misurata (SC-004, DA-003) — marcato skip/xfail finché il baseline non è disponibile

### Implementation for User Story 5

- [x] T031 [US5] Implement `RetrievalFacade` in `src/sertor_core/services/retrieval.py`: `search_code/search_docs/search_combined`, embed query → `store.query` con filtro doc_type, mapping a `RetrievalResult`, indice vuoto → []+warning (REQ-023..028); logging per query (REQ-031)
- [x] T031b [US5] Implement indexing orchestrator in `src/sertor_core/services/indexing.py`: `IndexingService.index(root) -> IndexReport` che concatena ingestion.discover → chunking.dispatch → embedder.embed → store.upsert (full re-index idempotente, namespace da config); logging strutturato (operation=index, doc/chunk count, dim, tempi) (REQ-015/031, SC-005) — chiude il gap C1 (depends on T012, T019, T023, T028)
- [x] T032 [US5] Implement composition root in `src/sertor_core/composition.py`: `build_facade()`, `build_indexer()` e `build_embedder/build_store` che cablano Settings→adapter→service; export pubblico in `src/sertor_core/__init__.py` (REQ-029) (depends on T023, T028, T031, T031b)

**Checkpoint**: US5 testabile (facade riusabile, indipendente dal backend) — **nucleo end-to-end funzionante**

---

## Phase 8: User Story 6 - Configurazione centralizzata e osservabilità (Priority: P2)

**Goal**: tutte le scelte da un'unica config senza default hardcoded; log strutturati completi per index e query.

**Independent Test**: cambiare provider/parametri solo via config e verificare il comportamento; ispezionare i log di un'indicizzazione e di una query e trovare tutti i campi richiesti.

### Tests for User Story 6 ⚠️

- [ ] T033 [P] [US6] Test config in `tests/unit/test_settings.py`: tutte le scelte (provider/backend/percorsi/chunking/k/batch/esclusioni) lette da env+file; assenza di default hardcoded nei componenti (REQ-030); segreti mai su path versionato (REQ-032)
- [ ] T034 [P] [US6] Test osservabilità in `tests/unit/test_logging.py`: index e query emettono log con campi (operation, provider/backend, conteggi, embedding_dim, elapsed_ms, error); `redact()` rimuove segreti (REQ-031/032, SC-007)

### Implementation for User Story 6

- [ ] T035 [US6] Harden `Settings` (config/settings.py): coprire TUTTI i parametri usati dai componenti, rimuovere ogni default hardcoded residuo nei servizi/adapter (REQ-030)
- [ ] T036 [US6] Ensure structured logs su tutte le operazioni di index e retrieval con i campi completi + redazione segreti (services/ingestion.py, services/retrieval.py, adapters) (REQ-031/032)

**Checkpoint**: US6 verificata (config unica + osservabilità completa)

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: criteri di accettazione trasversali e validazione end-to-end

- [ ] T037 Integration test idempotenza in `tests/integration/test_idempotence.py`: full re-index su corpus invariato → stesso insieme di chunk_id, nessun duplicato (SC-005, NFR-02)
- [ ] T038 Integration test repo-agnosticità in `tests/integration/test_two_corpora.py`: indicizza 2 codebase distinte (fixture + prototype) senza modifiche al codice; collezioni isolate (SC-001)
- [ ] T039 [P] Integration test local-only in `tests/integration/test_local_only.py`: con `RAG_BACKEND=local`, 0 chiamate di rete cloud (spia su httpx) lungo index+query (SC-006)
- [ ] T040 [P] Run quickstart.md validation: eseguire i flussi di `quickstart.md` (index → search_code/docs/combined) sulla fixture e verificare gli output
- [ ] T041 [P] Documentation: aggiungere `README.md` del pacchetto `src/sertor_core/` con uso come libreria (allineato a quickstart.md) e note extra opzionali (NFR-04)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: nessuna dipendenza
- **Foundational (Phase 2)**: dipende da Setup — BLOCCA tutte le user story
- **US1/US2 (Phase 3,4)**: dopo Foundational — indipendenti tra loro
- **US3/US4 (Phase 5,6)**: dopo Foundational — indipendenti tra loro e da US1/US2
- **US5 (Phase 7)**: dipende da US3 (embedder) + US4 (store) per il wiring end-to-end del composition root; la facade è testabile con mock anche prima
- **US6 (Phase 8)**: trasversale; indurisce config/log usati da tutte; verificabile dopo US5
- **Polish (Phase 9)**: dopo le user story desiderate

### Within Each User Story

- I test si scrivono PRIMA e devono FALLIRE prima dell'implementazione (TDD, Principio V)
- domain → services/adapters → composition (dipendenze verso l'interno)

### Parallel Opportunities

- Setup: T003, T004 in parallelo
- Foundational: T005, T006, T008, T009, T010 in parallelo (T007 dopo T005/T006)
- Story P1 (US1–US4) parallelizzabili tra loro dopo Foundational
- Dentro US2: T016, T017, T018 in parallelo (T019 dopo); dentro US3/US4 gli adapter [P] in parallelo

---

## Parallel Example: Foundational

```bash
Task: "Domain entities in src/sertor_core/domain/entities.py"        # T005
Task: "Domain errors in src/sertor_core/domain/errors.py"            # T006
Task: "Settings in src/sertor_core/config/settings.py"              # T008
Task: "Structured logging in src/sertor_core/observability/logging.py" # T009
Task: "Test fixtures + mocks in tests/fixtures/"                     # T010
```

---

## Implementation Strategy

### MVP First

1. Phase 1 Setup → 2. Phase 2 Foundational (CRITICO) → 3. US1 (ingestione) → **STOP & VALIDATE**.
   US1 da sola dimostra la repo-agnosticità (CS-5). Poi US2→US3→US4→US5 per il nucleo end-to-end,
   US6 per l'hardening trasversale, Phase 9 per i criteri di accettazione (SC-001/005/006/007).

### Incremental Delivery

- Foundational → US1 (scoperta) → US2 (chunk) → US3 (vettori) → US4 (store) → US5 (facade: nucleo
  completo, primo consumatore FEAT-002 può partire) → US6 (config/osservabilità) → Polish.

---

## Notes

- [P] = file diversi, nessuna dipendenza
- Test prima dell'implementazione; verificare il fallimento iniziale
- Commit dopo ogni task o gruppo logico (delega al `configuration-manager`)
- Stop ai checkpoint per validare la story in isolamento
- Evitare: task vaghi, conflitti sullo stesso file, dipendenze cross-story che rompono l'indipendenza
- **Mapping requisiti→story**: US1=REQ-001..005; US2=REQ-006..011; US3=REQ-012..016; US4=REQ-017..022;
  US5=REQ-023..029; US6=REQ-030..032 (+ trasversali su tutte)
