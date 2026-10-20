# Tasks: Memoria semantica che regge i turni grandi e i rifiuti del provider

**Input**: Design documents from `specs/145-memoria-semantica-turni-grandi/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/memory-semantic-index.md

**Tests**: richiesti — è un BUG dal campo: ogni storia ha un test che **fallisce prima** della correzione
(riproduzione) e passa dopo (SC-001..006).

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

- [x] T001 Verificare la base verde prima di toccare: `uv run pytest tests/unit/test_memory_semantic.py tests/unit/test_cli_memory_semantic.py tests/unit/test_memory_archive_semantic.py -q` e annotare il numero di test passati (riferimento per SC-006)

## Phase 2: Foundational

- [x] T002 Aggiungere a `tests/unit/test_memory_semantic.py` un `LimitedEmbedder(FakeEmbedder)` che solleva `EmbeddingError(reason="http 400", retriable=False)` per l'intero batch se un testo supera un budget in caratteri (riproduce la regola del servizio reale), con contatore delle chiamate e dei testi ricevuti
- [x] T003 Aggiungere `RejectedTurn` (frozen dataclass: `session_key`, `turn_index`, `reason`) e il campo `rejected: tuple[RejectedTurn, ...] = ()` a `SemanticIndexReport` in `src/sertor_core/services/memory_semantic.py`; aggiornare l'aggregazione in `index_all` per concatenare `rejected`

**Checkpoint**: la suite esistente resta verde (campo con default, costruttori invariati).

## Phase 3: User Story 1 — Un turno grande non fa più sparire la sessione (P1) 🎯 MVP

**Goal**: i turni oltre `max_chunk_tokens` sono spezzati e indicizzati; un risultato per turno in ricerca.

**Independent Test**: sessione di 181 turni con un turno da ~290.000 caratteri + `LimitedEmbedder` →
`embedded=181 errors=0`.

- [x] T004 [US1] Test di riproduzione in `tests/unit/test_memory_semantic.py`: caso Kaelen (181 turni, turno 37 da ~290.000 caratteri, `Settings(max_chunk_tokens=…)` coerente col budget del `LimitedEmbedder`) → atteso `embedded=181, errors=0` (fallisce prima della correzione)
- [x] T005 [P] [US1] Test in `tests/unit/test_memory_semantic.py`: un turno entro il budget conserva `chunk_id = "<key>#<i>"` e payload senza `part`/`parts`; un turno spezzato produce `"<key>#<i>/<p>"` con `part`/`parts`, e ogni pezzo rientra nel budget
- [x] T006 [P] [US1] Test in `tests/unit/test_memory_semantic.py`: incrementalità — secondo run sulla stessa sessione (con turno spezzato) → `embedded=0, skipped=181` e **zero** chiamate all'embedder; un indice costruito con la granularità vecchia (solo id `#i`) non viene ri-embeddato
- [x] T007 [P] [US1] Test in `tests/unit/test_memory_semantic.py`: ricerca su un termine presente solo nella coda del turno spezzato → il turno compare **una volta**, con `session_key`/`turn_index` corretti
- [x] T008 [US1] Implementare in `src/sertor_core/services/memory_semantic.py` la scomposizione in unità (`_turn_units(session, turn)` via `cap_to_tokens(text, settings.max_chunk_tokens, settings.chunk_overlap)`), il probe di incrementalità sugli id di tutte le unità (turno già indicizzato ⇔ tutte presenti) e la costruzione dei record con payload esteso solo per i pezzi; `embedded` conta i turni
- [x] T009 [US1] Implementare in `_run_search`/`_results_to_hits` (`src/sertor_core/services/memory_semantic.py`) l'over-fetch `2 × max(limit, 1)` e la deduplicazione per `(session_key, turn_index)` prima del taglio a `limit`

**Checkpoint**: T004–T007 verdi; suite della 072 verde.

## Phase 4: User Story 2 — Un rifiuto colpisce solo il turno rifiutato (P1)

**Goal**: su `http 400/413/422` il ripiego per pezzo confina l'errore; gli altri errori restano come oggi.

**Independent Test**: embedder che rifiuta solo il testo del turno 4 su 10 → `embedded=9, errors=1`.

- [x] T010 [P] [US2] Test in `tests/unit/test_memory_semantic.py`: `PickyEmbedder` che rifiuta (`http 400`, batch intero) se contiene un marcatore presente solo nel turno 4 → `embedded=9, errors=1`, `rejected == (RejectedTurn("s1", 4, "http 400"),)`, nessun record del turno 4 nello store; secondo run → i 9 non tornano all'embedder, il turno 4 viene ritentato
- [x] T011 [P] [US2] Test in `tests/unit/test_memory_semantic.py`: tutto o niente — turno spezzato con un solo pezzo rifiutato → nessun pezzo di quel turno nello store, turno in `rejected`
- [x] T012 [P] [US2] Test in `tests/unit/test_memory_semantic.py`: errore `retriable=True` (rete) e `http 401` non ritentabile → nessun ripiego (una sola chiamata all'embedder), `errors = turni nuovi`, `rejected == ()`; errore ritentabile durante il ripiego → ripiego interrotto, turni restanti in `errors` ma non in `rejected`
- [x] T013 [US2] Implementare in `src/sertor_core/services/memory_semantic.py` la costante `_INPUT_REJECTION_REASONS = frozenset({"http 400", "http 413", "http 422"})` e il ripiego `_index_turn_by_turn(...)`: un `embed([pezzo])` per pezzo, turno per turno, record scritti con un solo `upsert` finale, interruzione su errore non di rifiuto

**Checkpoint**: T010–T012 verdi; il test esistente `test_index_session_embedding_failure_is_counted_not_fatal` invariato e verde.

## Phase 5: User Story 3 — L'esito dice cosa è successo e dove (P2)

**Goal**: esito CLI con sessione/turno/motivo dei rifiuti; eventi `input_rejected` metrics-only.

**Independent Test**: report con un `RejectedTurn` → riga umana e campo JSON; report senza → output identico a oggi.

- [x] T014 [P] [US3] Test in `tests/unit/test_cli_memory_semantic.py`: `format_semantic_index_report` con `rejected` → riga `rejected session=<k> turn=<i> reason=http 400` e JSON con `"rejected": [{"session", "turn", "reason"}]`; il test esistente senza rifiuti resta invariato (output byte per byte uguale)
- [x] T015 [P] [US3] Test in `tests/unit/test_memory_semantic.py`: con un rifiuto, l'evento `memory_semantic_index_failed` ha `reason=input_rejected`, `detail=http 400`, `rejected=1` e non contiene né il testo del turno né la `session_key`; l'evento `memory_semantic_index` di `index_all` porta `rejected`; con il provider giù il motivo resta `provider_unavailable`
- [x] T016 [US3] Implementare in `src/sertor_core/cli/output.py` la resa di `rejected` (solo se non vuoto) in `format_semantic_index_report`
- [x] T017 [US3] Implementare in `src/sertor_core/services/memory_semantic.py` l'evento `input_rejected` nel ripiego e il campo `rejected` in `_emit_index_event`

**Checkpoint**: T014–T015 verdi.

## Phase 6: Polish & Cross-Cutting

- [x] T018 [P] Aggiornare la documentazione utente `docs/retrieval.md` (sezione memoria semantica): turni oltre `SERTOR_MAX_CHUNK_TOKENS` spezzati, esito che elenca i turni rifiutati, nessun rebuild necessario (un run di `memory index-semantic` recupera le sessioni perse)
- [x] T019 [P] Aggiungere la voce in `CHANGELOG.md` §Unreleased (Fixed), con il riferimento alla segnalazione di Kaelen
- [x] T020 [P] Aggiornare il contratto e il data-model della feature d'origine (`specs/072-ricerca-semantica-memoria/contracts/memory-semantic.md` §index_session/§index_all, `data-model.md` §chunk_id) con un rimando alla 145, perché non descrivano più la granularità «un id per turno» come unica
- [x] T021 Gate pre-merge: `uv run pytest -m "not cloud"` e `uv run ruff check .` verdi; confronto col conteggio di T001 (nessun test esistente rimosso o modificato oltre T014)
- [x] T022a Verificare che `tests/unit/test_memory_archive_semantic.py` resti verde: l'indicizzazione automatica a fine sessione chiama lo stesso `index_session`, quindi eredita la correzione senza codice proprio
- [x] T022 Verifica sul dogfood (2026-10-20, runtime `68ec358`: `embedded=237 skipped=13548 errors=0`, secondo run `embedded=0` — 62 ri-embedding imprevisti → seguito Phase 7) via vehicle: `uv run --project .sertor sertor-rag memory index-semantic` (se la memoria semantica è accesa) — dopo il merge, a runtime ri-lockato

## Phase 7: Seguito dalla verifica sul dogfood (branch 146)

- [x] T023 Test in `tests/unit/test_memory_semantic_large_turns.py`: turno indicizzato intero con un budget largo, reindicizzato con un budget stretto → `skipped`, zero chiamate, nessun pezzo creato (fallisce su `master` dopo la 145)
- [x] T024 In `src/sertor_core/services/memory_semantic.py`: `_existing_ids` interroga anche gli id interi dei turni; un turno con l'id intero presente è «già indicizzato»
- [ ] T025 Dopo il merge: re-lock del runtime e `memory index-semantic` → `embedded=0` sul dogfood (nessun nuovo ri-embedding)

## Dependencies & Execution Order

- T001 → T002, T003 → US1 (T004–T009) → US2 (T010–T013, usa le unità di T008) → US3 (T014–T017, usa
  `rejected` popolato da T013) → Polish.
- US2 dipende da US1 solo per la funzione delle unità; i test [P] di ogni fase sono indipendenti fra loro
  (stesso file ma funzioni distinte: scriverli in sequenza, eseguirli insieme).

## Parallel Example: User Story 1

```text
T005, T006, T007 → test indipendenti, poi T008 + T009
```

## Implementation Strategy

MVP = US1 (risolve da sola il caso segnalato: 181/181). US2 rende il fix strutturale per ogni rifiuto
futuro; US3 rende diagnosticabile il residuo. Consegna unica (una PR), perché le tre storie toccano la
stessa funzione.
