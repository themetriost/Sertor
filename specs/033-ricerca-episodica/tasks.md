---
description: "Task list for feature 033 — Ricerca episodica full-text locale (FEAT-002)"
---

# Tasks: Ricerca episodica full-text locale (FEAT-002, feature 033)

**Input**: Design documents from `specs/033-ricerca-episodica/`

**Prerequisites letti**: plan.md (required), spec.md (required), research.md, data-model.md,
contracts/episodic-search.md, quickstart.md

**Branch**: `033-ricerca-episodica`

**Stack**: Python 3.11+, stdlib-only (`sqlite3` FTS5, `hashlib`, `time`, `logging`). Zero nuove
dipendenze. Additivo su FEAT-001 (INVARIATA). Target: `sertor-core` Clean Architecture.

## Formato: `[ID] [P?] [Story] Descrizione con path file`

- **[P]**: parallelizzabile (file diversi, nessuna dipendenza in sospeso)
- **[Story]**: user story di appartenenza (US1–US4)
- Path file espliciti in ogni task (requisito del formato)

---

## Phase 1: Setup (struttura modulo + manopole Settings)

**Scopo**: Preparare i punti di estensione che i task successivi popoleranno.
Non implementa logica di ricerca — crea solo le "prese" nei file esistenti.

- [x] T001 Aggiungere `InvalidTimeWindowError` in `src/sertor_core/domain/errors.py` (nuova eccezione di dominio, accanto a `ConfigError`; campi: `since: float`, `until: float`; messaggio che descrive l'intervallo non valido; FR-007, Principio IV)
- [x] T002 [P] Aggiungere le manopole `episodic_limit: int = 20` e `episodic_snippet_tokens: int = 12` alla classe `Settings` in `src/sertor_core/config/settings.py` (env `SERTOR_EPISODIC_LIMIT` / `SERTOR_EPISODIC_SNIPPET_TOKENS`; default solo qui, Principio VIII; usare `_int_env` / valore intero diretto analogamente alle manopole esistenti)
- [x] T003 [P] Creare il file `src/sertor_core/services/episodic_search.py` con solo le dataclass di I/O: `SearchQuery(frozen=True)`, `EpisodicHit(frozen=True)`, `EpisodicResults` (con `hits: tuple[EpisodicHit, ...]` e `latency_ms: float`); importa solo `dataclasses`, `typing`, `__future__`; NO logica SQLite ancora (corpo del modulo vuoto oltre le entità)

**Checkpoint Setup**: `errors.py` ha `InvalidTimeWindowError`, `settings.py` ha le due manopole, `episodic_search.py` esiste con le tre dataclass. Verificabile con `uv run python -c "from sertor_core.domain.errors import InvalidTimeWindowError; from sertor_core.services.episodic_search import SearchQuery, EpisodicHit, EpisodicResults; print('ok')"`.

---

## Phase 2: Foundational (prerequisiti bloccanti)

**Scopo**: Componente concreto `EpisodicSearch` completo — schema FTS5, trigger, metodo `search`,
osservabilità, wiring in `composition.py`. Deve essere completo prima di qualunque user story.

**CRITICO**: nessuna user story può iniziare prima che questa fase sia terminata.

- [x] T004 Implementare la classe `EpisodicSearch` in `src/sertor_core/services/episodic_search.py`: costruttore `__init__(self, index_dir: Path)` che salva il path ma NON apre connessioni; metodo privato `_connect() -> sqlite3.Connection` che apre `memory.sqlite` in modalità read-write, crea la tabella virtuale FTS5 `turns_fts` (external-content su `turns`, `content_rowid='rowid'`, `IF NOT EXISTS`), crea i tre trigger di sync (`turns_ai`, `turns_ad`, `turns_au`, `IF NOT EXISTS`), ed esegue il rebuild una-tantum se `turns_fts` è vuota ma `turns` non lo è (pattern I-ONCE da contratto); gestione non-fatale di `sqlite3.OperationalError` su FTS5 non disponibile → log warning + ritorna `None` (P-NOINDEX); usa `logging.getLogger(__name__)`
- [x] T005 Implementare la logica di query in `EpisodicSearch.search(query: SearchQuery) -> EpisodicResults` in `src/sertor_core/services/episodic_search.py`: (1) guard su `query.text` vuoto/whitespace → `EpisodicResults(hits=(), latency_ms=0.0)` (P-EMPTY); (2) validazione finestra: `since > until` → `InvalidTimeWindowError` (C-ERR); (3) costruzione SQL con JOIN `turns_fts` ↔ `turns` ↔ `sessions`, clausola `WHERE` opzionale per `since`/`until` su `sessions.captured_at`, `ORDER BY bm25(turns_fts), sessions.captured_at DESC` per `order="relevance"` oppure `ORDER BY sessions.captured_at DESC` per `order="recency"`, `LIMIT query.limit`; `snippet()` con `query.snippet_tokens`; (4) costruzione `EpisodicHit` per ogni riga con `source_path=None` (edge-case attuale); (5) gestione per-riga di righe malformate → skip + warning (P-BADROW); (6) archivio assente (file non esiste) → `EpisodicResults(hits=(), latency_ms=...)` + warning (P-NOARCH); (7) misura `latency_ms` con `time.monotonic()`
- [x] T006 Implementare l'osservabilità in `EpisodicSearch.search` in `src/sertor_core/services/episodic_search.py`: dopo aver costruito il risultato, emettere `log_event(INFO, "episodic_search", query_hash=sha256_troncato, query_len=len(query.text), since=query.since, until=query.until, order=query.order, limit=query.limit, results=len(hits), latency_ms=...)` via `log_event` da `sertor_core.observability.logging`; il blocco di emissione è avvolto in `try/except Exception` non-fatale (P-OBSFAIL, FR-018); `query_hash` = `hashlib.sha256(query.text.encode()).hexdigest()[:16]`
- [x] T007 [P] Aggiungere `build_episodic_search(settings: Settings | None = None) -> EpisodicSearch | None` in `src/sertor_core/composition.py` (accanto a `build_memory_archive`, circa riga 345): gate `if not settings.memory_enabled: return None`; altrimenti `return EpisodicSearch(settings.index_dir)`; import lazy di `EpisodicSearch` dentro la funzione (come le altre `build_*`); aggiungere `build_episodic_search` alla lista degli export di `src/sertor_core/__init__.py` se il pattern del file lo prevede

**Checkpoint Foundational**: `EpisodicSearch(tmp_path).search(SearchQuery(text="x"))` su un archivio sintetico restituisce un `EpisodicResults` senza eccezioni; `EpisodicSearch(tmp_path / "nope").search(SearchQuery(text="x"))` restituisce `EpisodicResults(hits=())` (P-NOARCH). `build_episodic_search()` con `SERTOR_MEMORY=false` restituisce `None`.

---

## Phase 3: US1 — Ritrovare una conversazione per parola chiave (Priority: P1) — MVP

**Goal**: Data una parola chiave, ottenere la lista dei turni corrispondenti con citazione completa
(session_key, captured_at, role, turn_index, snippet, score). Archivio assente/vuoto → stato vuoto
esplicito, mai errore. Zero rete. Questa storia da sola è l'MVP.

**Test indipendente**: archiviare sessioni sintetiche con contenuto noto, interrogare con parola
presente, verificare che il turno compaia con tutti i campi di citazione e uno snippet con il match.
Testabile interamente offline in `tmp_path`.

### Implementazione US1

- [x] T008 [US1] Scrivere il test `test_finds_turn_by_keyword` in `tests/unit/test_episodic_search.py`: crea archivio sintetico con `MemoryArchive(tmp_path).upsert(...)`, chiama `EpisodicSearch(tmp_path).search(SearchQuery(text="Azure"))`, verifica `hit.session_key`, `hit.turn_index`, `"Azure" in hit.snippet` (C-CITE/C-SNIP, SC-001/SC-002); il test deve passare dopo T004–T006
- [x] T009 [P] [US1] Scrivere il test `test_no_match_returns_empty` in `tests/unit/test_episodic_search.py`: query su archivio con contenuto noto, parola assente → `results.hits == ()`, nessuna eccezione (P-NOMATCH, SC-005, FR-004)
- [x] T010 [P] [US1] Scrivere il test `test_missing_archive_is_empty_not_error` in `tests/unit/test_episodic_search.py`: `EpisodicSearch(tmp_path / "nope").search(SearchQuery(text="x")).hits == ()` (P-NOARCH, FR-004/FR-014, SC-005)
- [x] T011 [P] [US1] Scrivere il test `test_empty_query_returns_empty` in `tests/unit/test_episodic_search.py`: `SearchQuery(text="")` e `SearchQuery(text="   ")` → `hits == ()`, nessun errore (P-EMPTY, edge case spec)
- [x] T012 [P] [US1] Scrivere il test `test_all_citation_fields_present` in `tests/unit/test_episodic_search.py`: verifica che ogni `EpisodicHit` abbia `session_key` non vuoto, `captured_at` float, `role` str, `turn_index` int, `snippet` str non vuoto, `score` float; `source_path` può essere `None` (C-CITE, FR-002/FR-012, SC-002)
- [x] T013 [P] [US1] Scrivere il test `test_zero_network_io` in `tests/unit/test_episodic_search.py`: verifica che la ricerca non apra socket (`socket.socket` patchato o contatore di connessioni a zero) — SC-004/FR-003; alternativa semplificata: verificare che non ci siano import di moduli di rete nel percorso critico e che la chiamata non sollevi `OSError` in un ambiente con rete disabilitata (usare `unittest.mock.patch("socket.getaddrinfo", side_effect=OSError)`)

**Checkpoint US1**: `uv run pytest tests/unit/test_episodic_search.py -k "us1 or keyword or empty or citation or network"` passa. La storia è testabile e dimostrabile come MVP standalone.

---

## Phase 4: US2 — Filtro temporale (Priority: P1)

**Goal**: Aggiungere vincolo opzionale di finestra temporale (since, until, o entrambi) alla query.
Sessioni fuori finestra escluse. Finestra `since > until` → errore esplicito `InvalidTimeWindowError`.

**Test indipendente**: archiviare sessioni con `captured_at` in periodi diversi, interrogare con
finestra che copre solo alcune, verificare che le sessioni fuori finestra non compaiano. Testabile
offline in `tmp_path`.

**Nota**: la logica SQL del filtro temporale è già inclusa in T005 (Foundational). Questi task
aggiungono solo i test di contratto specifici di questa storia.

### Implementazione US2

- [x] T014 [US2] Scrivere il test `test_since_filter_excludes_older` in `tests/unit/test_episodic_search.py`: archivia due sessioni con `captured_at` diversi (es. `1000.0` e `2000.0`), query con `since=1500.0`, verifica che solo la sessione con `captured_at=2000.0` sia nei risultati (C-TIME, SC-003, FR-005/FR-006)
- [x] T015 [P] [US2] Scrivere il test `test_until_filter_excludes_newer` in `tests/unit/test_episodic_search.py`: due sessioni, query con `until=1500.0`, verifica che solo la sessione con `captured_at=1000.0` sia nei risultati (C-TIME, FR-005/FR-006)
- [x] T016 [P] [US2] Scrivere il test `test_since_and_until_combined` in `tests/unit/test_episodic_search.py`: tre sessioni a epoche diverse, query con `since` e `until` che includono solo quella centrale, verifica che solo quella centrale sia nei risultati (SC-003, FR-005)
- [x] T017 [P] [US2] Scrivere il test `test_invalid_window_raises_error` in `tests/unit/test_episodic_search.py`: `SearchQuery(text="x", since=2000.0, until=1000.0)` → `pytest.raises(InvalidTimeWindowError)` con messaggio che descrive l'intervallo (C-ERR, FR-007, Principio IV)
- [x] T018 [P] [US2] Scrivere il test `test_window_with_no_matching_sessions` in `tests/unit/test_episodic_search.py`: finestra che non include nessuna sessione → `hits == ()`, nessuna eccezione (edge case "Finestra temporale che non include alcuna sessione", spec §Edge)

**Checkpoint US2**: `uv run pytest tests/unit/test_episodic_search.py -k "filter or window or since or until or invalid"` passa. US1 e US2 funzionano insieme senza interferenze.

---

## Phase 5: US3 — Ordinamento + citazione utile (Priority: P2)

**Goal**: Risultati ordinati per pertinenza (tie-break recency), modalità recency-first su richiesta,
limite al numero massimo configurabile, snippet di contesto di lunghezza configurabile.

**Test indipendente**: archiviare molti turni corrispondenti, verificare che il numero di risultati
rispetti il limite, che l'ordine rifletta pertinenza+recency e che con `order="recency"` l'ordine
cambi; verificare che lo snippet abbia lunghezza finita e sia coerente ai bordi.

### Implementazione US3

- [x] T019 [US3] Scrivere il test `test_results_limited_by_limit` in `tests/unit/test_episodic_search.py`: archivia N turni (N > limite) tutti corrispondenti, query con `limit=3`, verifica `len(hits) == 3` (C-LIMIT, FR-010, SC US3.3)
- [x] T020 [P] [US3] Scrivere il test `test_default_order_relevance_with_recency_tiebreak` in `tests/unit/test_episodic_search.py`: due turni con stesso testo (uguale pertinenza) in sessioni diverse per `captured_at`, query default → il turno della sessione più recente è primo (C-ORDER-R, FR-008)
- [x] T021 [P] [US3] Scrivere il test `test_recency_order_ignores_relevance` in `tests/unit/test_episodic_search.py`: turni con pertinenza diversa (testo più ricco vs meno ricco), query con `order="recency"` → il turno della sessione più recente è primo indipendentemente dalla pertinenza (C-ORDER-T, FR-009)
- [x] T022 [P] [US3] Scrivere il test `test_snippet_is_non_empty_and_finite` in `tests/unit/test_episodic_search.py`: ogni hit ha `snippet` non vuoto; con `snippet_tokens=5` lo snippet è più corto che con `snippet_tokens=20` (C-SNIP, FR-011); verifica anche il caso edge: match all'inizio e alla fine del testo (edge "Match all'estremità")
- [x] T023 [P] [US3] Scrivere il test `test_multi_turn_same_session_returns_multiple_hits` in `tests/unit/test_episodic_search.py`: sessione con due turni corrispondenti → due hit distinti con stesso `session_key` ma `turn_index` diversi (C-MULTI, edge "Più turni della stessa sessione")

**Checkpoint US3**: `uv run pytest tests/unit/test_episodic_search.py -k "order or limit or snippet or multi"` passa. L'intero stack US1+US2+US3 è funzionante.

---

## Phase 6: US4 — Robustezza e host-agnostico (Priority: P2)

**Goal**: La ricerca non crasha mai su archivio assente/vuoto/corrotto (skip + warning), non assume
nulla sull'assistente ospite (host-agnostico), emette l'evento di osservabilità senza esporre la
query in chiaro, e funziona su zero cloud nel percorso query.

**Test indipendente**: interrogare su archivio inesistente → stato vuoto con warning; introdurre riga
malformata → skip + warning + resto ricercabile; verificare che l'evento di osservabilità non contenga
la query in chiaro; verificare che due archivi di provenienza diversa diano risultati equivalenti.

### Implementazione US4

- [x] T024 [US4] Scrivere il test `test_corrupt_row_is_skipped_not_fatal` in `tests/unit/test_episodic_search.py`: inserire direttamente in SQLite una riga in `turns` con `content` non decodificabile (es. bytes non UTF-8 in campo TEXT) o con schema inatteso, verificare che la ricerca restituisca comunque i turni validi e che nel log ci sia un warning (P-BADROW, FR-013, SC-005); usare `caplog` di pytest
- [x] T025 [P] [US4] Scrivere il test `test_empty_archive_returns_empty` in `tests/unit/test_episodic_search.py`: creare `memory.sqlite` con schema ma zero righe in `sessions`/`turns`, query → `hits == ()`, nessuna eccezione (P-EMPTYARCH, FR-004)
- [x] T026 [P] [US4] Scrivere il test `test_observability_event_emitted_with_hash` in `tests/unit/test_episodic_search.py`: dopo `search(SearchQuery(text="segreto"))`, verificare con `caplog` che sia presente un log con campo `query_hash` (sha256 troncato) e che la stringa `"segreto"` NON compaia nel log (C-OBS, FR-017, DA-FT-004)
- [x] T027 [P] [US4] Scrivere il test `test_observability_failure_is_non_fatal` in `tests/unit/test_episodic_search.py`: patchare `log_event` per sollevare `Exception`, verificare che `search` restituisca comunque `EpisodicResults` valido (P-OBSFAIL, FR-018)
- [x] T028 [P] [US4] Scrivere il test `test_host_agnostic_two_archives` in `tests/unit/test_episodic_search.py`: creare due archivi in `tmp_path` con `adapter_kind` e `project_id` diversi (es. "claude-code" e "cursor") ma stesso contenuto testuale, verificare che la stessa ricerca restituisca risultati equivalenti (C-HOST, FR-015/FR-016, SC-007)
- [x] T029 [P] [US4] Scrivere il test `test_latency_under_budget` in `tests/unit/test_episodic_search.py`: popolare archivio sintetico con almeno 500 turni, misurare `results.latency_ms`, verificare `< 200` (SC-006, DA-FT-003); il test usa `time.monotonic` già incluso nel componente (campo `EpisodicResults.latency_ms`)

**Checkpoint US4**: `uv run pytest tests/unit/test_episodic_search.py -k "corrupt or empty_archive or observability or host or latency"` passa. L'intera suite di robustezza è verde.

---

## Phase 7: Polish & Cross-cutting

**Scopo**: Test end-to-end integrati, verifica quickstart, lint, copertura edge case residui.

- [x] T030 Scrivere il test end-to-end `test_full_cycle_via_composition` in `tests/unit/test_episodic_search.py`: usa `build_episodic_search` di `composition.py` con `Settings(memory_enabled=True, index_dir=tmp_path)`, archivia una sessione via `MemoryArchive`, ricerca via il servizio, verifica il risultato — testa il wiring composition completo (quickstart pattern, FR-020/SC-008)
- [x] T031 [P] Scrivere il test `test_fresh_turn_is_searchable_after_archive` in `tests/unit/test_episodic_search.py`: crea `EpisodicSearch`, poi archivia una sessione con `MemoryArchive`, poi cerca → il turno è ricercabile (I-SYNC/C-FRESH, SC-008, FR-020; verifica che i trigger funzionino end-to-end)
- [x] T032 [P] Scrivere il test `test_schema_creation_is_idempotent` in `tests/unit/test_episodic_search.py`: costruire `EpisodicSearch` due volte sullo stesso `tmp_path` (due `__init__` + due `search`) senza errori, nessun duplicato nei risultati (I-IDEMP, Principio VI)
- [x] T033 [P] Verificare il quickstart manuale: eseguire il codice di `specs/033-ricerca-episodica/quickstart.md` §"Test offline" in un REPL locale con `uv run python`; entrambi gli snippet `test_finds_turn_by_keyword` e `test_missing_archive_is_empty_not_error` devono passare senza errori
- [x] T034 [P] Eseguire lint: `uv run ruff check src/sertor_core/domain/errors.py src/sertor_core/config/settings.py src/sertor_core/services/episodic_search.py src/sertor_core/composition.py` e correggere eventuali errori (regole E,F,I,UP,B; line-length 100)
- [x] T035 [P] Eseguire la suite unit completa per verificare assenza di regressioni: `uv run pytest tests/unit -m "not cloud"` deve passare interamente (additività: nessuna modifica a FEAT-001 o ad altre feature)

**Checkpoint Polish**: suite verde, lint pulito, quickstart verificato.

---

## Grafo delle dipendenze

### Dipendenze tra fasi

- **Phase 1 (Setup)**: nessuna dipendenza — si inizia immediatamente
- **Phase 2 (Foundational)**: dipende dal completamento di Phase 1 (T001–T003) — BLOCCA tutte le user story
- **Phase 3 (US1)**: dipende da Phase 2 completata; i task T008–T013 sono test che esercitano T004–T006
- **Phase 4 (US2)**: dipende da Phase 2 completata; T014–T018 testano il filtro temporale già nel SQL di T005; US2 e US3 possono iniziare in parallelo dopo US1 se il team ha capacità
- **Phase 5 (US3)**: dipende da Phase 2 completata; T019–T023 testano ordinamento/limite/snippet già in T005
- **Phase 6 (US4)**: dipende da Phase 2 completata; T024–T029 testano robustezza e osservabilità di T004–T006; può procedere in parallelo con US2/US3
- **Phase 7 (Polish)**: dipende da tutte le fasi US1–US4 completate

### Dipendenze critiche interne

| Task | Dipende da | Motivo |
|------|------------|--------|
| T002 | T001 | Settings importa `errors.py` indirettamente solo se si vuole il tipo; ma T002 è [P] — indipendente |
| T004 | T001, T002, T003 | Usa `InvalidTimeWindowError`, `Settings`, le dataclass |
| T005 | T004 | Usa `_connect()` e le dataclass |
| T006 | T005 | Usa il risultato di `search` già costruito |
| T007 | T003, T004 | Importa `EpisodicSearch`, usa `Settings` |
| T008–T013 | T004–T006 | Test su implementazione completa |
| T014–T018 | T005 | Testano la logica SQL del filtro temporale |
| T019–T023 | T005 | Testano ordinamento/limite/snippet |
| T024–T029 | T004–T006 | Testano robustezza e osservabilità |
| T030–T032 | T007 + tutti i precedenti | End-to-end con composition |

### Task parallelizzabili per fase

**Phase 1**: T002 e T003 sono [P] — possono procedere in parallelo con T001 (file diversi: `settings.py` e `episodic_search.py` vs `errors.py`).

**Phase 2**: T007 è [P] rispetto a T004–T006 (file diverso: `composition.py`), ma dipende da T003 e T004; in pratica si scrive T007 dopo T004.

**Phase 3 (US1)**: T009, T010, T011, T012, T013 sono tutti [P] tra loro e rispetto a T008 (tutti file di test diversi o sezioni diverse dello stesso file di test — i test non dipendono tra loro).

**Phase 4 (US2)**: T015, T016, T017, T018 sono [P] rispetto a T014 (sezioni indipendenti del file di test).

**Phase 5 (US3)**: T020, T021, T022, T023 sono [P] rispetto a T019.

**Phase 6 (US4)**: T025, T026, T027, T028, T029 sono [P] rispetto a T024.

**Phase 7**: T031, T032, T033, T034, T035 sono [P] rispetto a T030.

---

## Esempio di esecuzione parallela (US1)

```bash
# Dopo aver completato Phase 2 (Foundational), lanciare i test US1 tutti insieme:
uv run pytest tests/unit/test_episodic_search.py::test_finds_turn_by_keyword \
              tests/unit/test_episodic_search.py::test_no_match_returns_empty \
              tests/unit/test_episodic_search.py::test_missing_archive_is_empty_not_error \
              tests/unit/test_episodic_search.py::test_empty_query_returns_empty \
              tests/unit/test_episodic_search.py::test_all_citation_fields_present \
              tests/unit/test_episodic_search.py::test_zero_network_io -v
```

```bash
# Eseguire la suite completa della feature (offline, nessun cloud):
uv run pytest tests/unit/test_episodic_search.py -v -m "not cloud"
```

---

## Strategia di implementazione

### MVP (solo US1 — 3 fasi)

1. Completare **Phase 1** (Setup): T001–T003 — ~30 min
2. Completare **Phase 2** (Foundational): T004–T007 — cuore della feature
3. Completare **Phase 3** (US1): T008–T013 — test della ricerca per parola chiave
4. **STOP e VALIDARE**: `uv run pytest tests/unit/test_episodic_search.py -k "keyword or empty or citation or network"` verde
5. L'archivio episodico è ora interrogabile: MVP dimostrabile

### Consegna incrementale

1. Setup + Foundational (Phase 1+2) → base pronta
2. US1 (Phase 3) → MVP: ricerca per parola chiave; testa e valida
3. US2 (Phase 4) → aggiungi filtro temporale; testa indipendentemente
4. US3 + US4 (Phase 5+6) → possono procedere in parallelo; ordinamento, robustezza e osservabilità
5. Polish (Phase 7) → end-to-end, lint, quickstart

### Strategia parallela (2 persone)

Dopo la Phase 2 completata insieme:

- Persona A: US1 (Phase 3) → US3 (Phase 5)
- Persona B: US2 (Phase 4) → US4 (Phase 6)

US3 e US4 sono logicamente indipendenti; convergono nella Phase 7 (Polish).

---

## Note

- `[P]` = file diversi o sezioni indipendenti, nessuna dipendenza in sospeso
- FEAT-001 (`domain/memory.py`, `adapters/memory/archive.py`) NON viene toccata in nessun task
- I test sono **inclusi** perché il plan esplicita "Principio V — Testabilità & misure" e il
  quickstart mostra i pattern di test offline come parte del design; la spec chiede test F.I.R.S.T.
- `source_path` è `None` in tutti i test (campo facoltativo, edge case noto da research.md)
- FTS5 assente → P-NOINDEX (stato vuoto + warning), testato implicitamente in `test_missing_archive_is_empty_not_error` e documentato in `quickstart.md`
- Nessun task tocca `domain/ports.py` (nessuna porta nuova — componente concreto come `MemoryArchive`)
