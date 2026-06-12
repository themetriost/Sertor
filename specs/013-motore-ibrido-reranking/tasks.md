# Tasks: Motore RAG ibrido + reranking

**Input**: Design documents from `/specs/013-motore-ibrido-reranking/`

**Prerequisites**: plan.md, spec.md, research.md (D1..D12), data-model.md, contracts/

**Tests**: INCLUSI — la costituzione (Principio V) impone test F.I.R.S.T. e la feature ha la
misura come criterio di accettazione (REQ-051/052); i test di storia precedono l'implementazione.

**Organization**: per user story (spec.md): US1 ricerca ibrida (P1, MVP) · US2 selezione motore e
retro-compatibilità (P2) · US3 qualità misurata (P3) · US4 reranking opzionale (P4).

**Nota Gruppo E (FR-020..022, Could)**: NESSUN task deliberatamente — il percorso nativo per-store
è solo seam nel composition root (research D12); si implementerà quando uno store nativo sarà in uso.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: dipendenze del progetto per la feature

- [ ] T001 Aggiorna `pyproject.toml`: `rank-bm25` nelle dipendenze base + nuovo extra
      `rerank = ["flashrank>=0.2"]`; poi `uv sync --extra dev --extra mcp --extra azure` e verifica
      che la baseline test resti verde (`uv run pytest -m "not cloud" -q`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: porte, entità, config e mock condivisi da TUTTE le storie

**⚠️ CRITICAL**: nessun task di storia parte prima della fine di questa fase

- [ ] T002 [P] Aggiungi l'entità `LexicalEntry` (dataclass frozen: `chunk_id`, `text`, `doc_type`,
      `path`) in `src/sertor_core/domain/entities.py` — entità esistenti INVARIATE (FR-009)
- [ ] T003 [P] Aggiungi le porte `Protocol` `LexicalIndex` (build/query/exists/reset),
      `Reranker` (model, rerank) e `RetrieverStrategy` (retrieve) in
      `src/sertor_core/domain/ports.py` secondo `contracts/lexical-index-port.md` e
      `data-model.md` — porte esistenti INVARIATE (V-1)
- [ ] T004 Estendi `Settings` in `src/sertor_core/config/settings.py`: campi `engine`
      (default `"hybrid"`), `rrf_c` (60), `rrf_pool` (30), `rerank_enabled` (False),
      `rerank_pool` (15) + lettura env in `load()` (`SERTOR_ENGINE`, `SERTOR_RRF_C`,
      `SERTOR_RRF_POOL`, `SERTOR_RERANK` con parsing bool, `SERTOR_RERANK_POOL`) — default SOLO
      qui (NFR-05/FR-007)
- [ ] T005 [P] Aggiungi il mock `InMemoryLexicalIndex` (stessa semantica della porta, dict in
      memoria) in `tests/fixtures/mocks.py` (NFR-03)
- [ ] T006 Test unit dei nuovi campi `Settings` (default, override env, parsing bool di
      `SERTOR_RERANK`) nel file di test settings esistente in `tests/unit/`

**Checkpoint**: porte+config pronte — le storie possono partire

---

## Phase 3: User Story 1 - Ricerca ibrida: indice lessicale + fusione RRF (Priority: P1) 🎯 MVP

**Goal**: motore ibrido funzionante: indicizzazione congiunta (vettoriale + lessicale) e query che
fonde le due vie con RRF deterministico, restituendo `RetrievalResult` invariati.

**Independent Test**: con mock (FakeEmbedder + InMemoryStore + lessicale reale), indicizzare un
corpus piccolo, cercare un identificatore esatto presente in un solo file e trovarlo in cima;
query NL ancora pertinente; stessa query → stesso ordine (determinismo). Senza rete.

### Tests for User Story 1 (prima dell'implementazione)

- [ ] T007 [P] [US1] Test unit dell'adapter lessicale in `tests/unit/test_bm25_lexical_index.py`:
      tokenizer (lowercase, `[a-z0-9_]+`, sotto-token snake_case — FR-001), build/query/exists/
      reset, filtro `doc_type` PRIMA del taglio (research D5), namespacing per collezione (FR-005),
      scrittura atomica e sidecar `sertor.lexical/1` (formato sconosciuto → errore esplicito),
      determinismo dei pareggi, `k<=0 → []`
- [ ] T008 [P] [US1] Test unit della fusione RRF in `tests/unit/test_rrf_fusion.py`: formula
      `1/(c+rank)` (FR-006/007), pareggi risolti per `chunk_id` (FR-008), elemento in una sola
      lista incluso col contributo singolo, pool e `c` configurabili
- [ ] T009 [P] [US1] Test unit del motore in `tests/unit/test_hybrid_engine.py`: `index()` scrive
      entrambi gli indici dagli stessi chunk (FR-001/002/003), `query()` fonde dense+lessicale e
      ritorna `RetrievalResult` (FR-009), evento `hybrid_query` con i campi del contratto
      log-events (FR-027), nessun segreto nei log (FR-029), determinismo end-to-end

### Implementation for User Story 1

- [ ] T010 [US1] Implementa `tokenize()` + `Bm25LexicalIndex` in
      `src/sertor_core/adapters/lexical/bm25.py` (+ `__init__.py`): sidecar JSON atomico
      (tmp+rename) in `<Settings.index_dir>/lexical/<collection>.json`, caricamento pigro +
      `BM25Okapi` in memoria, query con filtro doc_type pre-taglio — contratto
      `contracts/lexical-index-port.md` (FR-001/002/005, FR-032)
- [ ] T011 [US1] Estendi `IndexingService` in `src/sertor_core/services/indexing.py` con parametro
      opzionale `lexical: LexicalIndex | None = None`: se presente, dopo l'upsert vettoriale
      costruisce il sidecar dagli stessi chunk (rebuild congiunto, FR-003); default None →
      pipeline byte-per-byte invariata (FR-030)
- [ ] T012 [US1] Implementa `rrf()` (funzione pura) + `HybridEngine` in
      `src/sertor_core/engines/hybrid.py`: `name="hybrid"`, `provider`, `index()` (pipeline con
      sink lessicale), `ensure_index()` strict sulla collezione vettoriale (FR-004),
      `query()`/`retrieve()` con pool denso + pool lessicale → RRF → ordinamento
      `(-score, chunk_id)` → top-k; evento `hybrid_query` (contracts/hybrid-engine.md,
      contracts/log-events.md) — la degradazione REQ-034 arriva in US2 (T018)
- [ ] T013 [US1] Esegui i test US1 (`uv run pytest tests/unit/test_bm25_lexical_index.py
      tests/unit/test_rrf_fusion.py tests/unit/test_hybrid_engine.py -q`) + `uv run ruff check .`
      e sistema fino al verde

**Checkpoint**: motore ibrido costruibile a mano coi mock, funzionante e deterministico

---

## Phase 4: User Story 2 - Selezione del motore e retro-compatibilità (Priority: P2)

**Goal**: `SERTOR_ENGINE` (default `hybrid`) risolto SOLO nel composition root; facade invariata
per i consumatori (strategia iniettata); degradazione onesta sui corpora pre-ibrido (REQ-034);
baseline intatto e selezionabile con risultati identici a oggi.

**Independent Test**: con un indice solo-vettoriale (pre-ibrido), query col default → risultati
dense-only + WARNING `lexical_index_missing`, nessuna eccezione; `SERTOR_ENGINE=baseline` →
risultati identici al sistema attuale; valore invalido → `ConfigError` con i valori ammessi.

### Tests for User Story 2 (prima dell'implementazione)

- [ ] T014 [P] [US2] Test unit della selezione in `tests/unit/test_engine_selection.py`:
      `build_engine()` ritorna baseline/hybrid da `Settings.engine`, default = hybrid (FR-015),
      valore invalido → `ConfigError` coi valori ammessi (edge case), `build_facade()` inietta la
      strategia solo con engine hybrid (FR-017/018), `build_indexer()` cabla il sink lessicale
      solo con hybrid (FR-031: con baseline pipeline identica a oggi), `build_baseline_engine()`
      invariata (FR-030)
- [ ] T015 [P] [US2] Test della degradazione in `tests/unit/test_hybrid_engine.py` (estensione):
      collezione vettoriale presente + sidecar assente → risultati dense-only equivalenti al
      baseline + WARNING `lexical_index_missing` con `collection` e `hint` (FR-016, SC-008);
      collezione assente → `IndexNotFoundError` (FR-004); via facade: collezione assente →
      `[]` + warning `no_index` (policy tollerante INVARIATA)

### Implementation for User Story 2

- [ ] T016 [US2] Estendi `RetrievalFacade` in `src/sertor_core/services/retrieval.py` con
      parametro keyword opzionale `retriever: RetrieverStrategy | None = None`: se presente, il
      percorso single-collection di `_search` delega a `retriever.retrieve(query, k, doc_type)`
      DOPO il check `exists()` (policy tollerante intatta); il fan-out multi-collezione
      (`_search_multi`) resta dense-only invariato (research D6); default None → comportamento
      byte-per-byte attuale (FR-018/030)
- [ ] T017 [US2] Estendi `src/sertor_core/composition.py`: `build_engine(settings)` (selezione
      baseline/hybrid + `ConfigError` su valore invalido — FR-015/017), wiring del sink lessicale
      in `build_indexer()` quando hybrid, iniezione del motore come `retriever` in
      `build_facade()` quando hybrid (FR-031); import lazy; `build_baseline_engine()` NON toccata
- [ ] T018 [US2] Implementa la degradazione REQ-034 in `HybridEngine.retrieve`
      (`src/sertor_core/engines/hybrid.py`): `lexical.exists()` false → retrieval dense-only +
      evento WARNING `lexical_index_missing` (`collection`, `hint` re-index) — mai eccezione
      (FR-016, contracts/log-events.md)
- [ ] T019 [US2] Test integrazione end-to-end in `tests/integration/test_hybrid_end_to_end.py`:
      corpus fixture su tmp_path → `build_indexer`-style index → query via facade con strategia
      (stesso formato risultati dei consumatori); confronto `SERTOR_ENGINE=baseline` ≡
      comportamento attuale (FR-031); marker `integration`, senza rete
- [ ] T020 [US2] Esegui l'intera suite (`uv run pytest -m "not cloud" -q`) + ruff e sistema fino
      al verde — il baseline e i suoi test DEVONO essere intatti (FR-030)

**Checkpoint**: default hybrid attivo, consumatori invariati, degradazione onesta verificata

---

## Phase 5: User Story 3 - Qualità misurata: ground-truth e xfail→strict (Priority: P3)

**Goal**: ground-truth versionato (≥10 coppie miste symbol/NL), valutazione comparativa
baseline vs ibrido (vs ibrido+rerank quando disponibile) con hit@1/3/5/10 e MRR@10; i 2 test
`xfail` diventano strict e passano senza rete.

**Independent Test**: `uv run pytest tests/integration/test_baseline_quality.py
tests/integration/test_precision_at_k.py -q` → 2 passed (non più xfail), con soglie
hit@5 ibrido ≥ baseline, MRR ibrido ≥ baseline e +10 pp sul sottoinsieme symbol (LSC-1).

### Implementation for User Story 3

- [ ] T021 [P] [US3] Crea il ground-truth versionato in `tests/fixtures/ground_truth.py`:
      `GROUND_TRUTH: list[tuple[str, list[str], str]]` (query, path POSIX relativi attesi,
      kind ∈ {"symbol","nl"}) — le 6 coppie symbol di research D10 + ≥4 NL fino a ≥10 totali
      (FR-023/026)
- [ ] T022 [US3] Generalizza `evaluate()` in `src/sertor_core/engines/evaluation.py`: type hint
      da `BaselineEngine` a un Protocol con `query`/`provider` (solo annotazione, zero
      comportamento) così accetta entrambi i motori (FR-024)
- [ ] T023 [US3] Riscrivi `tests/integration/test_baseline_quality.py` strict (niente xfail):
      indicizza `src/sertor_core/` con FakeEmbedder + InMemoryStore + `Bm25LexicalIndex` su
      tmp_path; `evaluate()` su baseline e ibrido dallo stesso ground-truth; asserzioni:
      hit@5 ibrido ≥ hit@5 baseline, MRR ibrido ≥ MRR baseline (FR-025) e — sul sottoinsieme
      `kind=="symbol"` — hit@5 ibrido ≥ baseline + 10 pp (SC-001/LSC-1); riporta nel log del test
      hit@1/3/5/10 + MRR@10 per modalità (FR-024)
- [ ] T024 [US3] Riscrivi `tests/integration/test_precision_at_k.py` strict sullo stesso
      ground-truth/fixture (precision@5 via facade con strategia ibrida ≥ baseline) (FR-025)
- [ ] T025 [US3] Esegui la suite integrazione (`uv run pytest tests/integration -q`) — i 2 ex
      xfail passano strict; aggiorna eventuali marker/`addopts` se necessario

**Checkpoint**: qualità DIMOSTRATA dal confronto; debito xfail chiuso

---

## Phase 6: User Story 4 - Reranking opzionale come secondo stadio (Priority: P4)

**Goal**: secondo stadio cross-encoder dietro l'extra `rerank` (FlashRank, import lazy):
disabilitato di default, errore esplicito se configurato senza extra, eventi di log dedicati.

**Independent Test**: senza extra e `SERTOR_RERANK=false` → risultati identici all'ibrido
RRF-only; `SERTOR_RERANK=true` senza extra → `ConfigError` azionabile; con reranker (fake nei
test) → top-k ri-ordinati dal punteggio del cross-encoder + evento `rerank`.

### Tests for User Story 4 (prima dell'implementazione)

- [ ] T026 [P] [US4] Test unit in `tests/unit/test_rerank.py`: con un `FakeReranker` (conforme
      alla porta) il pool fuso troncato a `rerank_pool` viene ri-ordinato e tornano top-k con
      score del reranker (FR-010/014); reranking disabilitato → risultati RRF identici, nessun
      evento `rerank` (FR-013); evento `rerank` con `reranker_model`, `pool_size`, `top_k`,
      `elapsed_ms` (FR-028); composition con `rerank_enabled=True` ed extra assente →
      `ConfigError` azionabile (FR-012)

### Implementation for User Story 4

- [ ] T027 [US4] Implementa `FlashRankReranker` in `src/sertor_core/adapters/rerank/flashrank.py`
      (+ `__init__.py`): import lazy di `flashrank`, attributo `model`, `rerank()` che mappa i
      punteggi del cross-encoder in `RetrievalResult` ri-ordinati (FR-010/011, pattern
      `prototype/02-hybrid-reranking/rerank.py`)
- [ ] T028 [US4] Cabla il reranker: in `src/sertor_core/composition.py` costruzione lazy quando
      `Settings.rerank_enabled` (extra assente → `ConfigError` con istruzione d'installazione,
      FR-012); in `src/sertor_core/engines/hybrid.py` stadio rerank sul pool fuso
      (`rerank_pool`) + evento `rerank` (FR-010/014/028)
- [ ] T029 [US4] Validazione opzionale con l'extra reale: `uv sync --extra dev --extra rerank`,
      esegui la valutazione comparativa includendo ibrido+rerank (FR-024) e annota l'esito in
      `specs/013-motore-ibrido-reranking/quickstart.md` (nota: su embedder forte può peggiorare —
      rischio R-3 atteso e documentato); poi suite completa + ruff

**Checkpoint**: tutte le storie indipendentemente funzionanti

---

## Phase 7: Polish & Dogfood

**Purpose**: documentazione, validazione live sul corpus reale, chiusura

- [ ] T030 [P] Aggiorna `docs/install.md` (sezione configurazione: `SERTOR_ENGINE` e manopole
      ibrido/rerank, extra `rerank`, nota migrazione: re-index abilita l'ibrido) e la sezione env
      del `CLAUDE.md` di radice se elenca le variabili
- [ ] T031 Dogfood live sul corpus `sertor` (provider reale Azure): re-index con
      `uv run sertor-rag index .` (costruisce il sidecar lessicale), query a simbolo
      (`EmbeddingProvider`, `IndexNotFoundError`) via `sertor-rag search` confrontando default
      hybrid vs `SERTOR_ENGINE=baseline`; verifica degradazione (query PRIMA del re-index →
      warning `lexical_index_missing`); osserva `elapsed_ms` degli eventi `hybrid_query` per la
      misura empirica di latenza (NFR-04/D3); verifica server MCP invariato (stessi tool, SC-003)
- [ ] T032 Suite completa finale (`uv run pytest -m "not cloud" -q` + `uv run ruff check .`) e
      validazione del quickstart (`specs/013-motore-ibrido-reranking/quickstart.md` eseguibile
      com'è scritto)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: nessuna dipendenza
- **Foundational (Phase 2)**: dipende da Setup — BLOCCA tutte le storie
- **US1 (Phase 3)**: dipende da Foundational — è l'MVP
- **US2 (Phase 4)**: dipende da US1 (cabla il motore di T012 nel composition root)
- **US3 (Phase 5)**: dipende da US1 (misura il motore); indipendente da US2 (i test costruiscono
  il motore direttamente coi mock) — può girare in parallelo a US2
- **US4 (Phase 6)**: dipende da US1 (stadio sul pool fuso); indipendente da US2/US3
- **Polish (Phase 7)**: T030 dopo US2; T031 dopo US2 (richiede composition cablata); T032 ultima

### Critical Path

T001 → T004 → (T007..T009) → T010 → T011 → T012 → T013 → (T014/T015) → T016 → T017 → T018 → T019 → T020 → T031 → T032 (~15 passi)

### Parallel Opportunities

- Phase 2: T002 ∥ T003 ∥ T005 (file diversi); T004 e T006 dopo T002/T003
- US1: T007 ∥ T008 ∥ T009 (test, file diversi) prima di T010..T012
- US2: T014 ∥ T015 prima di T016..T018
- Dopo US1: US2, US3 (T021..T025) e US4 (T026..T028) possono procedere in parallelo
- T030 ∥ T031 in Phase 7

## Parallel Example: User Story 1

```bash
# I tre file di test di US1 insieme (falliscono prima dell'implementazione):
Task: "Test adapter lessicale in tests/unit/test_bm25_lexical_index.py"
Task: "Test fusione RRF in tests/unit/test_rrf_fusion.py"
Task: "Test HybridEngine in tests/unit/test_hybrid_engine.py"
```

## Implementation Strategy

### MVP First (US1)

1. Phase 1 + 2 (setup + porte/config/mock)
2. Phase 3 (US1): adapter lessicale → sink in indexing → HybridEngine + RRF
3. **STOP & VALIDATE**: motore ibrido funzionante coi mock, deterministico, senza rete

### Incremental Delivery

1. US1 → MVP dimostrabile (motore costruito a mano)
2. US2 → il default `hybrid` va in produzione per tutti i consumatori, retro-compat verificata
3. US3 → la qualità è misurata e i 2 xfail chiusi (criterio di accettazione, FR-024/025)
4. US4 → reranking opzionale (Should; il valore core è già dimostrato)
5. Phase 7 → dogfood live + docs

## Notes

- FR coverage: US1 = FR-001..009, FR-027/029, FR-032 · US2 = FR-004/015..019, FR-030/031 ·
  US3 = FR-023..026 · US4 = FR-010..014, FR-028 · Gruppo E (FR-020..022) deliberatamente senza
  task (Could, research D12)
- La deroga REQ-034 (degradazione vs Principio IV) è tracciata nel plan (Complexity Tracking):
  T015/T018 ne sono l'implementazione fedele — warning strutturato, mai silenzioso
- Commit a fine di ogni fase o gruppo logico (delega al configuration-manager)
