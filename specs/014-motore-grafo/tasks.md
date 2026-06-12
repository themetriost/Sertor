# Tasks: Motore RAG a grafo (code-graph strutturale)

**Input**: Design documents from `/specs/014-motore-grafo/`

**Prerequisites**: plan.md, spec.md, research.md (G1..G10), data-model.md, contracts/

**Tests**: INCLUSI — la costituzione (Principio V) impone test F.I.R.S.T.; le soglie LSC-2/3
(80%) e la copertura dichiarata (FR-003) sono criteri di accettazione misurati dai test.

**Organization**: per user story (spec.md): US1 grafo in `index()` + find_symbol (P1, MVP) ·
US2 navigazione relazioni (P2) · US3 i 4 tool nel server MCP (P3) · US4 ground-truth a due
strati (P4).

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: dipendenze del progetto per la feature

- [x] T001 Aggiorna `pyproject.toml`: nuovo extra `graph = ["networkx>=3"]` (la navigazione lo
      richiede; il build NO — research G1); poi `uv sync --all-packages --extra dev --extra mcp
      --extra azure --extra graph` e baseline verde (`uv run pytest -m "not cloud" -q`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: entità, porta, errore, config e mock condivisi da TUTTE le storie

**⚠️ CRITICAL**: nessun task di storia parte prima della fine di questa fase

- [x] T002 [P] Aggiungi le entità `GraphNode`, `GraphEdge`, `GraphData`, `SymbolHit`,
      `ContextBundle` (dataclass frozen, campi da data-model.md) in
      `src/sertor_core/domain/entities.py` — entità esistenti INVARIATE (FR-029)
- [x] T003 [P] Aggiungi `GraphNotFoundError` (stile `IndexNotFoundError`: messaggio azionabile
      + attributo `corpus`) in `src/sertor_core/domain/errors.py` (FR-007)
- [x] T004 Aggiungi la porta `CodeGraph` (Protocol: build/find_symbol/who_calls/related_docs/
      get_context/exists/reset) in `src/sertor_core/domain/ports.py` secondo
      `contracts/code-graph-port.md` — porte esistenti INVARIATE (FR-009/FR-029)
- [x] T005 Estendi `Settings` in `src/sertor_core/config/settings.py`: `graph_enabled` (True,
      `SERTOR_GRAPH`, parsing bool), `graph_ambiguity_threshold` (2, `SERTOR_GRAPH_AMBIGUITY`),
      `graph_limit_definitions` (10), `graph_limit_relations` (8), `graph_limit_docs` (8) —
      default SOLO qui (Principio VIII)
- [x] T006 [P] Aggiungi il mock `FakeCodeGraph` (dict in memoria, stessa semantica della porta:
      due assenze distinte, bundle limitato) in `tests/fixtures/mocks.py` (NFR-03)
- [x] T007 Test unit dei nuovi campi `Settings` (default, override env, bool) in
      `tests/unit/test_settings.py`

**Checkpoint**: porte+config pronte — le storie possono partire

---

## Phase 3: User Story 1 - Grafo costruito in index() + find_symbol (Priority: P1) 🎯 MVP

**Goal**: `index()` produce anche il grafo (estrazione pura + JSON atomico namespaced per
corpus); `find_symbol` risponde esatto. Il build NON richiede l'extra (G1).

**Independent Test**: su corpus fixture, `index()` (o estrazione+build diretti) produce
`<index_dir>/graph/<corpus>.json` versionato; `find_symbol` di un simbolo noto → path/riga/kind
corretti; stesso corpus → stesso grafo. Senza rete, senza embeddings reali.

### Tests for User Story 1 (prima dell'implementazione)

- [x] T008 [P] [US1] Test unit dell'estrazione in `tests/unit/test_graph_extraction.py`:
      nodi simbolo dai chunk (symbol/qualname/node_type/start_line — FR-002), nodi module/doc
      dai Document, archi `contains` dalla gerarchia dei qualname (language-agnostic),
      `calls`/`imports`/`inherits` per Python (parità prototipo), soglia di ambiguità (FR-004:
      nomi oltre soglia → archi omessi), `mentions` per token distintivi (≥5 char/camel/underscore),
      determinismo (ordinamenti stabili — FR-008), `COVERAGE` esportata e coerente con `_REL`
- [x] T009 [P] [US1] Test unit dell'adapter in `tests/unit/test_networkx_graph.py` (parte
      build+find): `build` scrive JSON `sertor.graph/1` atomico (no leftovers tmp), `exists`/
      `reset` idempotenti, formato sconosciuto/corrotto → `ConfigError`, `find_symbol` (match
      esatto, kinds, ordinamento per ref, vuoto esplicito se assente — FR-013/FR-017), grafo
      assente → `GraphNotFoundError` (FR-007), extra mancante alla query → `ConfigError`
      azionabile (monkeypatch `sys.modules["networkx"]=None`; il BUILD invece funziona senza)

### Implementation for User Story 1

- [x] T010 [US1] Implementa `src/sertor_core/services/graph_extraction.py`:
      `extract_graph(documents, chunks, *, ambiguity_threshold) -> GraphData` (nodi da chunk +
      module/doc; contains da qualname; mappa `_REL` per-linguaggio con python completo
      (calls/imports/inherits via tree-sitter) e node-type di invocazione per gli altri;
      mentions dai doc; `COVERAGE` derivata da `_REL` — FR-001..004, research G2/G3); puro,
      deterministico, NESSUN import di networkx
- [x] T011 [US1] Implementa `NetworkxCodeGraph` in
      `src/sertor_core/adapters/graph/networkx_graph.py` (+ `__init__.py`): `build` = JSON
      atomico in `<index_dir>/graph/<corpus>.json` (tmp+rename, formato `sertor.graph/1`,
      coverage persistita) SENZA networkx; `find_symbol`/`exists`/`reset` con caricamento pigro
      (import networkx nei soli metodi di query → `ImportError` incapsulato in `ConfigError`
      azionabile), cache per corpus, indici per nome (FR-005, contracts/code-graph-port.md).
      **L'evento `graph_build` (FR-026) lo emette `build()` qui** — l'adapter conosce
      `graph_path` e i conteggi; l'orchestratore no (fix analyze I1)
- [x] T012 [US1] Estendi `IndexingService` in `src/sertor_core/services/indexing.py` con
      parametro opzionale `graph: CodeGraph | None = None`: dopo l'upsert (e il sink lessicale)
      estrae dagli STESSI documents/chunks (passando `ambiguity_threshold` da
      `Settings.graph_ambiguity_threshold` — Principio VIII, nessun default nel servizio) e
      chiama `graph.build()` (snapshot intero; corpus vuoto in rebuild → build vuoto — specchio,
      FR-006); l'evento `graph_build` lo emette l'adapter (T011, fix I1)
- [x] T013 [US1] Estendi `src/sertor_core/composition.py`: `build_graph_service(settings)`
      (factory dedicata, ortogonale a `SERTOR_ENGINE` — FR-012/FR-022) + wiring del sink grafo
      in `build_indexer()` quando `graph_enabled` (G6); riesporta `build_graph_service` da
      `src/sertor_core/__init__.py`
- [x] T014 [US1] Esegui i test US1 + `uv run ruff check src tests packages` e sistema fino al
      verde

**Checkpoint**: grafo costruito da `index()`, find_symbol esatto, artefatto persistito

---

## Phase 4: User Story 2 - Navigazione relazioni (Priority: P2)

**Goal**: `who_calls`, `related_docs`, `get_context` (bundle multi-hop limitato) deterministici
e citabili; evento `graph_query` su ogni operazione.

**Independent Test**: su grafo fixture con relazioni note: chiamanti attesi, doc attesi, bundle
con sezioni limitate dai knob; simbolo assente → vuoto; tutto senza rete.

### Tests for User Story 2 (prima dell'implementazione)

- [x] T015 [P] [US2] Estendi `tests/unit/test_networkx_graph.py` (parte navigazione):
      `who_calls` (archi calls entranti — FR-014), `related_docs` (mentions — FR-015),
      `get_context` (definizioni+chiamanti+chiamate+basi+doc, limiti dai knob — FR-016),
      simbolo assente → bundle/liste vuoti (FR-017), `ref` citabile `path#qualname` (FR-018),
      evento `graph_query` con operation/symbol/results/elapsed_ms (FR-027, caplog), nessun
      segreto (FR-028)

### Implementation for User Story 2

- [x] T016 [US2] Completa `NetworkxCodeGraph`: `who_calls`/`related_docs`/`get_context`
      (traversal su indici; limiti da Settings; `SymbolHit`/`ContextBundle`; ordinamenti
      deterministici) + emissione `graph_query` per ogni operazione (FR-014..018, FR-027)
- [x] T017 [US2] Test di composition in `tests/unit/test_graph_composition.py`:
      `build_graph_service()` ritorna l'adapter configurato; `build_indexer()` cabla il sink
      solo con `graph_enabled=True`; ortogonalità: `SERTOR_ENGINE=baseline|hybrid` non cambia
      nulla del grafo e viceversa (FR-012/FR-031); motori/facade INVARIATI (FR-029)
- [x] T018 [US2] Suite completa (`uv run pytest -m "not cloud" -q`) + ruff e sistema fino al
      verde

**Checkpoint**: navigazione completa dal core, osservabile e deterministica

---

## Phase 5: User Story 3 - I 4 tool nel server MCP (Priority: P3)

**Goal**: `find_symbol`/`who_calls`/`related_docs`/`get_context` registrati accanto ai 3 tool
esistenti (invariati), deleganti al servizio del core, con warm-up eager esteso al grafo.

**Independent Test**: i 7 tool risultano registrati; i 4 di grafo delegano al `FakeCodeGraph`;
errori strutturati (grafo assente / extra mancante); `main()` riscalda facade E grafo prima del
loop stdio.

### Tests for User Story 3 (prima dell'implementazione)

- [x] T019 [P] [US3] Test unit in `tests/unit/test_mcp_graph_tools.py`: 7 tool registrati
      (FR-019), i 4 di grafo delegano al servizio mock e formattano risposte citabili
      (`ref=path#qualname`, contracts/mcp-graph-tools.md), `GraphNotFoundError`/`ConfigError`
      propagati come errori del tool senza crash del server (FR-021/FR-022), i 3 tool di
      ricerca esistenti INVARIATI (stesso formato di prima), `main()` riscalda facade E grafo
      PRIMA di `mcp.run()` e il warm-up NON fallisce se grafo/extra mancano (R-7)

### Implementation for User Story 3

- [x] T020 [US3] Estendi `src/sertor_mcp/server.py`: `_graph()` memoizzato su
      `build_graph_service(Settings.load())`, 4 tool sottili con docstring italiane per
      l'agente, formattazione `{path, line, kind, qualname, ref}` / bundle per sezioni,
      log di superficie `mcp.<tool>`; `main()` con warm-up esteso (tenta il load del grafo,
      tollerante a grafo/extra assenti — contracts/mcp-graph-tools.md)
- [x] T021 [US3] Suite completa + ruff e sistema fino al verde

**Checkpoint**: la promessa dell'epica è mantenuta — i 4 tool storici sono tornati

---

## Phase 6: User Story 4 - Ground-truth a due strati (Priority: P4)

**Goal**: misura senza rete: ≥5 simboli reali del corpus sertor (soglie 80%) + verifica che la
copertura dichiarata `COVERAGE` sia vera per ciascuno dei 10 linguaggi.

**Independent Test**: `uv run pytest tests/integration/test_graph_ground_truth.py
tests/integration/test_graph_languages.py -q` → verde, senza rete.

### Implementation for User Story 4

- [x] T022 [P] [US4] Crea `tests/fixtures/graph_ground_truth.py`: ≥5 simboli reali di
      `src/sertor_core/` scelti per **stabilità dell'insieme dei chiamanti** (fix analyze U1:
      preferire `collection_name`, `discover`, `chunk_document`, `redact` a simboli ad alto
      churn come `log_event`), con definizione attesa (path + intervallo righe), chiamanti
      attesi (lista chiusa enumerata alla scrittura), doc attesi dove applicabile; path
      relativi POSIX (FR-023/FR-025)
- [x] T023 [P] [US4] Crea il mini-corpus `tests/fixtures/graph_corpus/`: un file minimo per
      ciascuno dei 10 linguaggi del chunker (una funzione che ne chiama un'altra + un import
      dove dichiarato), con gli archi attesi documentati nel modulo fixture (FR-003)
- [x] T024 [US4] Test integrazione `tests/integration/test_graph_ground_truth.py`: estrae il
      grafo da `src/sertor_core/` (discover+chunk+extract_graph — niente embeddings) e
      verifica: definizioni esatte per ogni simbolo; **recall** chiamanti attesi ≥80% sul
      corpus reale (robusto al churn: nuovi chiamanti legittimi non rompono il test — fix U1);
      recall doc ≥80% (SC-003/LSC-3); marker `integration`, senza rete (FR-024). La
      **precisione** piena (SC-002/LSC-2) si misura in T025 sul mini-corpus CHIUSO, dove il
      ground-truth è totale
- [x] T025 [US4] Test integrazione `tests/integration/test_graph_languages.py`: estrazione sul
      mini-corpus e verifica che OGNI relazione dichiarata in `COVERAGE` per ogni linguaggio
      produca l'arco atteso (la dichiarazione è vera — FR-003) e che la **precisione** sul
      corpus chiuso sia ≥80% (SC-002/LSC-2: qui il ground-truth è totale); nodi+contains
      presenti per tutti i 10. Il mini-corpus È anche la verifica SC-007 (secondo corpus,
      zero adattamenti — fix C1)
- [x] T026 [US4] Suite completa + ruff e sistema fino al verde

**Checkpoint**: copertura dichiarata = copertura dimostrata; soglie LSC misurate

---

## Phase 7: Polish & Dogfood

**Purpose**: documentazione, validazione live, chiusura

- [x] T027 [P] Aggiorna `docs/install.md` (sezione grafo: extra `graph`, build automatico nel
      re-index, i 4 tool MCP, manopole `SERTOR_GRAPH*`) e la sezione env del `CLAUDE.md` di
      radice (aggiungi `SERTOR_GRAPH`)
- [x] T028 Dogfood live sul corpus `sertor`: `uv run sertor-rag index .` (costruisce anche il
      grafo — osserva `graph_build` nei log con conteggi per kind/type), poi da Python o via
      server MCP riavviato: `find_symbol("build_facade")`, `who_calls("log_event")`,
      `get_context("RetrievalFacade")` — risposte citabili e pertinenti; osserva
      `graph_query.elapsed_ms` (NFR-04: <100ms navigazione, <500ms context); annota l'esito in
      `specs/014-motore-grafo/quickstart.md`
- [x] T029 Suite completa finale (`uv run pytest -m "not cloud" -q` root + `uv run pytest
      packages/sertor/tests -q`) + `uv run ruff check src tests packages` + validazione del
      quickstart

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** → **Foundational (Phase 2)** → blocca tutte le storie
- **US1 (Phase 3)**: dopo Foundational — MVP
- **US2 (Phase 4)**: dipende da US1 (estende l'adapter)
- **US3 (Phase 5)**: dipende da US2 (i tool espongono la navigazione completa)
- **US4 (Phase 6)**: dipende da US1 per l'estrazione; indipendente da US3 — può girare in
  parallelo a US3
- **Polish (Phase 7)**: T027 in parallelo; T028 dopo US3; T029 ultima

### Critical Path

T001 → T004 → T005 → (T008/T009) → T010 → T011 → T012 → T013 → T014 → T015 → T016 → T018 → T019 → T020 → T021 → T028 → T029 (~17 passi)

### Parallel Opportunities

- Phase 2: T002 ∥ T003 ∥ T006; T004/T005/T007 a seguire
- US1: T008 ∥ T009 prima di T010..T013
- Dopo US2: US3 (T019..T021) ∥ US4 (T022..T026)
- Phase 7: T027 ∥ T028

## Parallel Example: User Story 1

```bash
# I due file di test di US1 insieme (falliscono prima dell'implementazione):
Task: "Test estrazione in tests/unit/test_graph_extraction.py"
Task: "Test adapter build+find in tests/unit/test_networkx_graph.py"
```

## Implementation Strategy

### MVP First (US1)

1. Phase 1 + 2 (extra graph + entità/porta/errore/config/mock)
2. Phase 3 (US1): estrazione pura → adapter (build JSON + find_symbol) → sink in indexing →
   composition
3. **STOP & VALIDATE**: `index()` su fixture produce il grafo; find_symbol esatto; idempotente

### Incremental Delivery

1. US1 → MVP (grafo + lookup fondamentale)
2. US2 → navigazione completa dal core
3. US3 → i 4 tool tornano nel server MCP (promessa dell'epica)
4. US4 → copertura dichiarata dimostrata + soglie LSC misurate
5. Phase 7 → docs + dogfood live

## Notes

- FR coverage: US1 = FR-001..013 (con FR-007/FR-017 ripresi in US2), FR-026 · US2 =
  FR-014..018, FR-027/FR-028, FR-012/FR-029/FR-031 (test composition) · US3 = FR-019..022 ·
  US4 = FR-003 (verifica), FR-023..025 · Polish = FR-030 (non-distruttività verificata nel
  dogfood) — 31/31 FR coperti
- Zero deroghe costituzionali (plan, Complexity Tracking vuoto)
- Commit a fine di ogni fase o gruppo logico (delega al configuration-manager)
