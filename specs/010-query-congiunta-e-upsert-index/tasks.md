# Tasks: Query congiunta multi-collezione & `upsert-index` in CLI

**Input**: Design documents from `/specs/010-query-congiunta-e-upsert-index/`

**Prerequisites**: plan.md, spec.md (Clarifications 2026-06-10), research.md (R1–R8), data-model.md, contracts/

**Tests**: richiesti dalla spec (SC-007: feature coperta da test deterministici senza rete; suite verde + ruff).

**Organization**: per user story; US1 e US2 sono completamente indipendenti (moduli disgiunti).

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

**Purpose**: baseline verificata prima di toccare il codice.

- [x] T001 Verificare il punto di partenza: `uv run pytest -m "not cloud" -q` verde (135 attesi) e `uv run ruff check .` pulito

---

## Phase 2: Foundational

Nessun prerequisito condiviso tra le due story (moduli disgiunti: `domain/services/adapters/composition` per US1, `wiki_tools` per US2). Si passa direttamente alle story.

---

## Phase 3: User Story 1 — Interrogare codice e wiki in una sola ricerca (Priority: P1) 🎯 MVP

**Goal**: `search_combined()` fa fan-out sulle collezioni del corpus primario + corpora extra dichiarati in `Settings`, fonde i top-k per `(-score, chunk_id)`, degrada su corpus mai indicizzato, fallisce esplicitamente su provider eterogenei. `search_code`/`search_docs` e il caso single-collection restano byte-identici.

**Independent Test**: con `FakeEmbedder` + `InMemoryStore` popolati su due collezioni, `search_combined` restituisce risultati da entrambe, ordinati, ≤ k; tutti i casi del contratto [contracts/combined-search.md](contracts/combined-search.md) passano senza rete.

### Implementation for User Story 1

- [x] T002 [US1] Aggiungere `ProviderMismatchError(SertorError)` (campi `corpus`, `expected`, `found`, messaggio azionabile) in `src/sertor_core/domain/errors.py`
- [x] T003 [US1] Estendere la porta `VectorStore` con `list_collections() -> list[str]` (docstring: rilevamento provider, FR-009) in `src/sertor_core/domain/ports.py`
- [x] T004 [P] [US1] Implementare `list_collections()` in `ChromaStore` (`client.list_collections()`, errori avvolti in `VectorStoreError`) in `src/sertor_core/adapters/vectorstores/chroma.py`
- [x] T005 [P] [US1] Implementare `list_collections()` in `AzureSearchStore` (`SearchIndexClient.list_index_names()`, import lazy, errori avvolti) in `src/sertor_core/adapters/vectorstores/azure_search.py`
- [x] T006 [P] [US1] Implementare `list_collections()` in `InMemoryStore` (chiavi del dict) in `tests/fixtures/mocks.py`
- [x] T007 [US1] Aggiungere `Settings.extra_corpora: tuple[str, ...] = ()` letto da `SERTOR_EXTRA_CORPORA` via `_split_env` in `src/sertor_core/config/settings.py`
- [x] T008 [US1] Implementare fan-out + merge in `RetrievalFacade` (`src/sertor_core/services/retrieval.py`): kwarg keyword-only `extra_collections: Mapping[str, str] | None`; `search_combined` → percorso invariato se mappa vuota, altrimenti 1 embed → query per collezione disponibile → merge `(-score, chunk_id)` → tronca a k; assente+mai-indicizzato → warning `no_index` (FR-004); assente+`{corpus}__*` esistente → `ProviderMismatchError` (FR-009); tutte assenti → `[]`+warning (FR-005); log `retrieve` con `collections`, `k`, `results`, `elapsed_ms` (FR-008); `search_code`/`search_docs` intoccati (FR-006bis)
- [x] T009 [US1] Cablare in `build_facade()` la mappa corpus→collezione per `settings.extra_corpora` via `collection_name(replace(settings, corpus=c), embedder)` in `src/sertor_core/composition.py`
- [x] T010 [P] [US1] Test parsing `SERTOR_EXTRA_CORPORA` (assente→`()`, CSV con spazi, vuoti filtrati) in `tests/unit/test_settings.py`
- [x] T011 [P] [US1] Test del contratto combined-search (i 7 casi: due collezioni popolate; pertinenza concentrata; parità di score → tie-break stabile; degradazione; tutte assenti; `ProviderMismatchError`; regressione single-collection identica) in `tests/unit/test_retrieval_facade.py`
- [x] T012 [P] [US1] Test wiring `build_facade` con `extra_corpora` (mappa derivata correttamente, default vuoto → facade odierna) in `tests/unit/test_composition.py`
- [x] T013 [P] [US1] Test `list_collections` di `ChromaStore` (client finto iniettato) e di `InMemoryStore` in `tests/unit/test_vectorstore.py`
- [x] T014 [US1] Checkpoint US1: `uv run pytest tests/unit -q` verde; `uv run ruff check .` pulito

**Checkpoint**: la query congiunta è completa e testabile in isolamento (MVP).

---

## Phase 4: User Story 2 — Scrivere la riga d'indice del wiki dalla CLI (Priority: P2)

**Goal**: `sertor-wiki-tools upsert-index --page … [--summary …|stdin]` esegue il write idempotente della riga d'indice con esito strutturato `wiki.upsert_index/1`; sommario vuoto/multilinea → `ConfigError`, exit 1, zero scritture.

**Independent Test**: su un wiki fittizio in `tmp_path` con `wiki.config.toml` minimale, i 7 casi del contratto [contracts/cli-upsert-index.md](contracts/cli-upsert-index.md) passano invocando `main(argv)` senza rete.

### Implementation for User Story 2

- [x] T015 [P] [US2] Aggiungere il contratto `UpsertIndexResult` (`written`, `action`, `page`, schema `wiki.upsert_index/1`, `to_dict`/`to_json`) in `src/sertor_core/wiki_tools/contracts.py`
- [x] T016 [US2] Aggiornare `upsert_index` in `src/sertor_core/wiki_tools/registry.py`: ritorno `UpsertIndexResult` (insert/update/noop); validazione FR-018 (trim; vuoto/solo-whitespace o newline interni → `ConfigError`, nessuna scrittura); idempotenza e update-in-place invariati (dipende da T015)
- [x] T017 [US2] Cablare l'op `upsert-index` in `src/sertor_core/wiki_tools/__main__.py`: `_OPS`, parser (`--page`, `--summary`), `_run` (summary da `--summary` o `_read_body`/stdin; `--page` mancante o summary assente → `ConfigError`), `_human` (`written=… action=… page=…`) (dipende da T016)
- [x] T018 [P] [US2] Test registry aggiornati: contratto del risultato (insert/update/noop), validazione (vuoto, whitespace, multilinea → `ConfigError` e file invariato), idempotenza byte-identica in `tests/unit/test_wiki_tools_registry.py`
- [x] T019 [P] [US2] Test CLI end-to-end (nuovo file): insert/update/noop, `--json` conforme allo schema, indice mancante → exit 1, sommario vuoto/multilinea → exit 1, sommario non-ASCII via stdin fedele (UTF-8) in `tests/unit/test_wiki_tools_cli.py`
- [x] T020 [US2] Checkpoint US2: `uv run pytest tests/unit -q` verde; `uv run ruff check .` pulito

**Checkpoint**: entrambe le story funzionano in modo indipendente.

---

## Phase 5: Polish & Cross-Cutting

- [x] T021 Suite completa: `uv run pytest -m "not cloud" -q` verde (zero regressioni, SC-007); `uv run ruff check .` pulito
- [x] T022 Validazione quickstart sul dogfood (richiede credenziali Azure — facoltativa, fuori CI): `SERTOR_EXTRA_CORPORA=wiki` nel `.env`, costruire la collezione wiki (`uv run sertor-wiki-tools index`), verificare `search_combined` fuso via `build_facade()` e un `upsert-index` reale su una pagina del wiki, come da [quickstart.md](quickstart.md)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (P1)**: nessuna.
- **Foundational (P2)**: vuota — le story partono subito dopo il setup.
- **US1 (Phase 3)** e **US2 (Phase 4)**: indipendenti tra loro (moduli disgiunti) — eseguibili anche in parallelo o in qualunque ordine; priorità P1 prima se sequenziali.
- **Polish (Phase 5)**: dopo entrambe le story.

### Within Each Story

- US1: T002→T003 (dominio prima delle implementazioni) → T004/T005/T006 [P] → T007 → T008 (dipende da T002/T003/T006 per i test) → T009 (dipende da T007/T008) → T010–T013 [P] → T014.
- US2: T015 [P] → T016 → T017 → T018/T019 [P] → T020.

### Parallel Opportunities

- T004, T005, T006 (tre adapter/mock, file diversi).
- T010, T011, T012, T13 (quattro file di test diversi).
- T015 con T002–T007 (story diverse, file disgiunti).
- T018, T019 (file di test diversi).

---

## Implementation Strategy

**MVP first**: T001 → US1 completa (T002–T014) → validazione → US2 (T015–T020) → Polish.
US1 da sola è già il valore principale («una sola verità interrogabile»); US2 è piccola e si
aggiunge senza toccare i moduli di US1. Commit per story (delegati al `configuration-manager`).
