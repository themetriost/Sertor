# Tasks: Contratto di retrieval verso l'agente

**Feature**: `118-contratto-retrieval-agente` (E5-FEAT-012) · **Data**: 2026-07-24
**Input**: [spec.md](spec.md) · [plan.md](plan.md) · [research.md](research.md) · [data-model.md](data-model.md) · [contracts/](contracts/)

## Convenzioni

- `[P]` = parallelizzabile (file diverso, nessuna dipendenza da task incompiuti)
- `[US1]`/`[US2]`/`[US3]` = user story servita
- 🔌 = **richiede un agente esterno e costa denaro** — NON gira in `uv run pytest`

> **Test-prima.** Il progetto scrive i test insieme all'implementazione, non prima in senso stretto.
> Qui i test delle **invarianti** (T004, T005) precedono deliberatamente il resto: pinnano un
> comportamento **già vero** che il resto della feature non deve rompere.

---

## Phase 1 — Setup

- [ ] T001 Aggiungere `eval_ab/results/` a `.gitignore` (gli esiti delle misure non si versionano; le regole di decisione e i casi sì)
- [ ] T002 [P] Creare `eval_ab/README.md` con l'intestazione «regole di decisione registrate PRIMA delle esecuzioni» e le tre soglie del gate (≤5pp per la consegna, nessun calo per l'attivazione di default)

---

## Phase 2 — Foundational (blocca tutte le user story)

Nessuna: la feature è additiva e ogni story poggia su strutture già esistenti. Le estensioni condivise
(entità, porta) vivono dentro la story che le richiede per prima.

---

## Phase 3 — User Story 2: il contratto dice la verità (Priority: P2, fase F1+F2)

**Goal**: proteggere due comportamenti oggi corretti ma non presidiati, e rendere la descrizione dei
tool coerente con la configurazione attiva.

**Independent test**: `uv run pytest tests/unit/test_eval_routing_invariants.py tests/unit/test_score_contract.py` — verde, e rosso se si rompe una delle invarianti.

> Ordinata per prima nonostante sia P2: è **offline, a basso rischio e senza dipendenze**, e mette in
> sicurezza il terreno su cui le altre story costruiscono.

### F1 — Blindatura delle invarianti della valutazione

- [ ] T003 [US2] Promuovere il letterale `1.0` a costante nominata `_GRAPH_SCORE_SENTINEL` in `src/sertor_core/services/eval/runner.py`, usata da `RoutedEvalEngine.query` — *verifica: `uv run pytest tests/unit -k eval` resta verde*
- [ ] T004 [US2] Test **instradamento esclusivo** in `tests/unit/test_eval_routing_invariants.py`: motore fittizio che fallisce se invocato su un caso `symbol`, grafo fittizio che fallisce se invocato su un caso non-`symbol` — *verifica: entrambe le direzioni asserite; le query di prova DEVONO essere nomi di simbolo (R14: `RoutedEvalEngine` passa l'intera query a `find_symbol`)*
- [ ] T005 [US2] Test **indipendenza dal segnaposto** nello stesso file: eseguire `evaluate(...)` due volte con `_GRAPH_SCORE_SENTINEL` sostituito da due valori diversi e asserire `EvalReport` identici **campo per campo** — *verifica: il test fallisce se una metrica inizia a leggere lo score*

### F2 — Descrizione dei tool derivata dalla configurazione

- [ ] T006 [P] [US2] Helper puro `score_contract(settings) -> str` in `src/sertor_mcp/server.py`: testo differenziato per `settings.engine` (similarità vs fusione per rango) + dichiarazione dell'asimmetria fra la scala dell'astensione e quella esposta — *verifica: funzione pura, nessun I/O*
- [ ] T007 [US2] Comporre le descrizioni dei tre tool di ricerca e la stringa `instructions` del server da testo base + `score_contract(Settings.load())` in `src/sertor_mcp/server.py` — *verifica: `Settings.load()` invocato prima di istanziare il server*
- [ ] T008 [US2] Test in `tests/unit/test_score_contract.py`: con `engine="baseline"` il testo dichiara «similarità, confrontabile solo entro la propria lista»; con `engine="hybrid"` dichiara «fusione per rango, aggiunge poco rispetto all'ordine»; entrambi dichiarano l'asimmetria — *verifica: 3 asserzioni distinte*

**Checkpoint US2**: le due invarianti sono protette e il contratto dichiarato è vero in entrambe le configurazioni.

---

## Phase 4 — User Story 3: il segnale strutturale arriva (Priority: P3, fasi F3–F6)

**Goal**: terzo flusso etichettato in `search_combined`, dietro interruttore spento di default, con
assenza tipizzata e troncamento dichiarato.

**Independent test**: interruttore acceso su una domanda che nomina un simbolo → terzo flusso con
definizioni e relazioni per simbolo; interruttore spento → risposta identica a oggi.

### F3 — Entità di dominio, porta, totali

- [ ] T009 [P] [US3] Creare `src/sertor_core/domain/agent_context.py`: `EntrySource`, `RelationStatus`, `EntryPoint`, `RelationBlock`, `SymbolContext`, `GraphBranch`, `AgentContext` — dataclass **frozen**, campi a tuple, nessun import di SDK — *verifica: `GraphBranch.status` è una **property**, non un campo*
- [ ] T010 [P] [US3] Estendere `ContextBundle` in `src/sertor_core/domain/entities.py` con `totals: tuple[tuple[str, int], ...] = ()` — *verifica: default vuoto, consumatori esistenti invariati*
- [ ] T011 [P] [US3] Aggiungere `list_symbols() -> list[str]` alla porta `CodeGraph` in `src/sertor_core/domain/ports.py` — *verifica: docstring che dichiara la semantica dell'assenza, coerente con gli altri metodi*
- [ ] T012 [US3] Implementare `list_symbols()` in `src/sertor_core/adapters/graph/networkx_graph.py` leggendo i `qualname` già serializzati nell'artefatto — *verifica: nessun ricalcolo, nessuna struttura nuova*
- [ ] T013 [US3] In `networkx_graph.py`, contare i totali **prima** di applicare i limiti `graph_limit_*` e popolare `ContextBundle.totals` — *verifica: `total` corretto anche quando il taglio è attivo*
- [ ] T014 [US3] Estendere i mock della porta `CodeGraph` in `tests/fixtures/mocks.py` con `list_symbols` — *verifica: la suite esistente resta verde*
- [ ] T015 [P] [US3] Test in `tests/unit/test_agent_context_entities.py`: `status` derivato nei 4 casi (`unavailable` / `not_attempted` / `partial` / `ok`); invariante `not_attempted` ⟺ `entry_points` vuoto; `unavailable` ⟹ `reason` non nullo; `shown == len(items)`; `shown <= total` — *verifica: 8+ asserzioni, funzioni pure*

### F4 — Vie d'ingresso deterministiche

- [ ] T016 [P] [US3] Creare `src/sertor_core/services/graph_entry.py` con `extract_identifiers(query)` — riconosce maiuscole interne, underscore, notazione puntata; **non** riconosce parole tutte minuscole senza separatori — *verifica: funzione pura, stdlib-only*
- [ ] T017 [US3] Aggiungere `match_symbol_table(query, qualnames, min_overlap=2)` nello stesso file: spezza i qualname su CamelCase/underscore/punto, match sul nome intero **oppure** su ≥ `min_overlap` parti distinte; ordinamento deterministico (parti coincidenti desc, poi alfabetico)
- [ ] T018 [US3] Aggiungere `resolve_entry_points(...)`: precedenza `caller_supplied` → `extracted_from_query` → `symbol_table_match`, dedup per simbolo conservando la **prima** provenienza, taglio a `max_symbols`
- [ ] T019 [US3] Test in `tests/unit/test_graph_entry.py` — inclusi i casi che **NON devono agganciare**: query italiana senza sovrapposizione → `[]` (lexical gap dichiarato); «cosa fa la cache» con una sola parte in comune → `[]`; tetto rispettato; dedup conserva la provenienza più affidabile; output identico a input identico — *verifica: ≥ 10 casi, tutti puri*

### F5 — Servizio orchestrante, manopole, factory

- [ ] T020 [P] [US3] Aggiungere a `src/sertor_core/config/settings.py` le tre manopole con default **solo qui**: `combined_graph_enabled` (`SERTOR_COMBINED_GRAPH`, `False`), `combined_graph_max_symbols` (`3`), `combined_match_min_overlap` (`2`)
- [ ] T021 [US3] Creare `src/sertor_core/services/agent_context.py` con `AgentContextService.search(query, k)`: chiama `facade.search_combined` (invariato), costruisce il ramo grafo, marca la corroborazione
- [ ] T022 [US3] Nel servizio, mappare le indisponibilità in **3 cause distinte**: `GraphNotFoundError` → `graph_not_built`; `ConfigError` con `key == "graph"` → `navigation_library_missing`; `ConfigError` senza quella chiave → `graph_artifact_unusable` — *verifica: nessuna eccezione collassa in lista vuota (FR-027)*
- [ ] T023 [US3] Funzione pura `mark_corroboration(docs, code, graph)` nello stesso modulo: match **sul solo path**, bilaterale (`corroborated_by` nel `metadata` degli item di somiglianza e sui `SymbolHit` delle definizioni) — *verifica: nessun dedup fra flussi (FR-033)*
- [ ] T024 [US3] Emettere un evento di osservabilità con punti d'ingresso risolti, provenienza, `status` e causa se `unavailable` — *verifica: una risoluzione a vuoto è osservabile, non silenziosa*
- [ ] T025 [US3] Aggiungere `build_agent_context(settings)` a `src/sertor_core/composition.py`, riusando `build_facade` + `build_graph_service` — *verifica: unico punto che conosce le implementazioni concrete*
- [ ] T026 [US3] Test in `tests/unit/test_agent_context_service.py`: le 3 indisponibilità distinte; `not_attempted` senza toccare il grafo; corroborazione bilaterale; troncamento con `shown`/`total`; caso misto (un blocco `ok`, uno `empty`, uno `unavailable`) → `status == "partial"` — *verifica: ≥ 8 casi con porte mockate*
- [ ] T027 [P] [US3] Test che pinna il **discriminante fragile** di R6: un `ConfigError` con `key="graph"` NON deve essere classificato come artefatto corrotto — *verifica: la regressione fallisce invece di degradare in silenzio*

### F6 — Superficie MCP

- [ ] T028 [US3] In `src/sertor_mcp/server.py`, `search_combined` costruisce il servizio e aggiunge la chiave `graph` **solo** se `combined_graph_enabled`; serializzazione JSON annidata, ordine chiavi `docs`, `code`, `graph` (R13)
- [ ] T029 [US3] Test in `tests/unit/test_mcp_combined_graph.py`: a flag **spento** la risposta non contiene `graph` né `corroborated_by` ed è identica a quella odierna (SC-007); a flag **acceso** la forma rispetta `contracts/agent-context.md`; **e i flussi `docs`/`code` NON portano `shown`/`total`** (FR-031: il taglio top-k è costitutivo e non finge esaustività) — *verifica: l'additività è asserita, non assunta; il requisito negativo FR-031 ha un'asserzione propria*

**Checkpoint US3**: il flusso strutturale esiste, è spento di default, e l'additività è dimostrata.

---

## Phase 5 — User Story 1: misurare il comportamento dell'agente (Priority: P1, fase F7)

**Goal**: l'harness che rende misurabile l'effetto di una variante di payload sulla risposta.

**Independent test**: eseguire una misura su un caso di prova e ottenere un confronto ripetibile.

> Ordinata per ultima nell'esecuzione benché sia **P1 per valore**: dipende dalle capacità delle fasi
> precedenti per avere qualcosa da misurare. La priorità della spec resta P1 perché **senza questa
> story il gate di US3 non è applicabile** e la feature non si può consegnare.

- [ ] T030 [P] 🔌 [US1] `eval_ab/cases.toml`: domande + fonti attese estratte dalla suite di valutazione esistente, partizionate in strutturali / non strutturali — *verifica: ≥ 20 casi (SC-001)*
- [ ] T031 [P] 🔌 [US1] `eval_ab/variants.py`: funzioni **pure** `strip_scores(payload)` e `strip_graph(payload)` — *verifica: testabili senza agente; le varianti differiscono per un solo aspetto (FR-004)*
- [ ] T032 🔌 [US1] `eval_ab/capture.py`: cattura i payload eseguendo il **vehicle** (CLI/MCP), mai importando `sertor_core` (Principio XI, R3) — *verifica: nessun `import sertor_core` nel file*
- [ ] T033 🔌 [US1] `eval_ab/drive.py`: esegue gli arm con prompt template identico, **3 ripetizioni** per caso, e calcola i verdetti **deterministici** (`cites_expected` con semantica di **unione**, `invented_path`, `payload_bytes`, `latency_ms`). Persiste in JSONL **il materiale fornito, la risposta ricevuta e il verdetto** — non solo quest'ultimo (SC-010: una decisione di contratto dev'essere riesaminabile risalendo a ciò che l'ha prodotta) — *verifica: nessun giudizio di modello nel calcolo del verdetto; un esito passato è ricostruibile senza rieseguire la misura*
- [ ] T034 🔌 [US1] In `drive.py`, rifiutare l'esecuzione se `eval_ab/README.md` non contiene una regola di decisione registrata (FR-006) — *verifica: un risultato senza regola registrata non è producibile*
- [ ] T035 🔌 [US1] In `drive.py`, dichiarare l'esito **non conclusivo** quando la variazione fra ripetizioni supera l'effetto misurato (FR-008) — *verifica: caso di prova con dati sintetici*

**Checkpoint US1**: si può porre la domanda «questa forma fa rispondere meglio?» e ottenere un numero.

---

## Phase 6 — Le misure e il gate (fase F8)

- [ ] T036 🔌 Registrare in `eval_ab/README.md` le regole di decisione delle tre misure **prima** di eseguirle
- [ ] T037 🔌 Misura **6b** (motore ibrido): payload con e senza `score`, a parità di ordine — *decide se il campo resta sotto il motore di default*
- [ ] T038 🔌 Misura **6a** (motore vettoriale): stessa misura, `SERTOR_ENGINE=baseline` — *decide se il campo resta sotto motore di similarità*
- [ ] T039 🔌 Misura del **gate del fan-out**: beneficio sulle domande strutturali **e** non-regressione su quelle non strutturali, con dimensione del payload e latenza (SC-008)
- [ ] T040 🔌 Applicare il gate: calo > 5pp → non si consegna; ≤ 5pp ma misurabile → si consegna **spenta**; nessun calo + beneficio → attivabile di default (FR-037/038)
- [ ] T041 🔌 Applicare l'esito delle misure 6a/6b a `_fmt` in `src/sertor_mcp/server.py`, rendendo l'esposizione del punteggio **condizionale al motore**; aggiungere `SERTOR_EXPOSE_SCORE` per i consumatori deterministici (FR-018)

---

## Phase 7 — Polish & cross-cutting

- [ ] T042 [P] Riportare gli esiti delle misure in `wiki/concepts/llm-facing-retrieval-contract.md` §8: le righe «non misurato» diventano verdetti; il frontmatter esce da `in-review`
- [ ] T043 [P] Documentare le tre manopole nuove in `docs/reference.md` e nei template `.env` dell'installer (`packages/sertor/src/sertor_installer/assets/rag/env.local.tmpl` e `env.azure.tmpl`) — *regola di progetto: una manopola non documentata è una feature incompleta*
- [ ] T044 Gate pre-merge: `uv run pytest -m "not cloud"` e `uv run ruff check .` entrambi verdi — *vincolante prima di qualunque merge*
- [ ] T045 Aggiornare il blocco EXEC di `wiki/syntheses/roadmap.md` con lo stato risultante di FEAT-012

---

## Dipendenze

```
Setup (T001-T002)
   │
   ├─→ US2 / F1  (T003 → T004, T005)            ── offline, indipendente
   │   US2 / F2  (T006 → T007 → T008)           ── offline, indipendente
   │
   └─→ US3 / F3  (T009,T010,T011 [P] → T012,T013 → T014 → T015)
          │
          F4  (T016 → T017 → T018 → T019)       ── indipendente da F3
          │
          F5  (T020 [P]; T021 → T022,T023,T024 → T025 → T026,T027)
          │      richiede F3 (entità, porta) + F4 (vie d'ingresso)
          │
          F6  (T028 → T029)                     ── richiede F5
                 │
                 └─→ US1 / F7 (T030,T031 [P] → T032 → T033 → T034,T035)
                        │
                        └─→ F8 (T036 → T037,T038,T039 → T040 → T041)
                               │
                               └─→ Polish (T042-T045)
```

**Ordine delle story:** US2 → US3 → US1 nell'**esecuzione**, US1 → US2 → US3 nella **priorità di valore**.
La divergenza è deliberata e spiegata nel piano: US1 misura ciò che US3 costruisce, quindi va scritta
dopo ma resta la ragione per cui US3 può essere consegnata.

## Parallelizzazione

| Gruppo | Task | Nota |
|---|---|---|
| Entità e porta | T009, T010, T011 | file diversi, nessuna dipendenza reciproca |
| Test puri | T015, T027 | file diversi, dopo le rispettive implementazioni |
| Manopole | T020 | indipendente da tutto il resto di F5 |
| Harness | T030, T031 | dati e funzioni pure, nessuna dipendenza |
| Polish | T042, T043 | documentazione, file diversi |

## Strategia di consegna

**MVP consegnabile offline: Phase 1 + Phase 3 + Phase 4** (T001–T029). Produce le invarianti protette,
il contratto dichiarato e il flusso strutturale funzionante ma **spento**. Non richiede né rete né
agente, ed è interamente verificabile con `uv run pytest`.

**Il resto (T030–T041) richiede un agente e costa denaro**: è la parte che *decide* se accendere
l'interruttore. Consegnare l'MVP senza le misure è legittimo — l'interruttore resta spento, il che è
esattamente ciò che FR-019 prescrive finché il gate non è superato.

**Il rischio da non correre** è consegnare la forma e saltare l'esito (R-7 della spec): un flusso
costruito, mai misurato e acceso «perché sembra utile» sarebbe la definizione del difetto che questa
feature esiste per evitare.
