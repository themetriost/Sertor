---
description: "Task list per FEAT-011 — CLI di esecuzione RAG `sertor-rag`"
---

# Tasks: CLI di esecuzione RAG `sertor-rag` (FEAT-011)

**Input**: Design documents da `specs/011-cli-esecuzione-rag/`

**Prerequisites**: plan.md (PASS Constitution Check), spec.md (3 user story P1/P2/P3), research.md
(decisioni D1..D8), data-model.md, contracts/cli-commands.md, contracts/log-events.md, quickstart.md

**Tests**: i task di test sono inclusi per tutte e tre le user story (FR espliciti: NFR-02/SC-007
richiedono verificabilità senza rete con mock; la suite attuale e' 159 passed + 2 xfail con
`-m "not cloud"`).

**Organization**: task organizzati per user story per abilitare implementazione e verifica indipendente
di ciascuna storia. Le estensioni al core (Phase 2) sono prerequisiti blocking per tutte le storie.

## Formato: `[ID] [P?] [Story] Descrizione`

- **[P]**: eseguibile in parallelo (file diversi, nessuna dipendenza su task incompleti)
- **[Story]**: user story di appartenenza (US1, US2, US3)
- Path espliciti in ogni descrizione

## Path Conventions

Single project — `src/`, `tests/` a root. Modulo CLI: `src/sertor_core/cli/`. Test: `tests/unit/`.

---

## Phase 1: Setup (Infrastruttura condivisa)

**Purpose**: scaffolding del package CLI e registrazione del console-script; nessuna logica RAG.
Questa fase NON richiede alcuna dipendenza nuova (argparse e stdlib coprono tutto — D1).

- [ ] T001 Creare il package `src/sertor_core/cli/` con `__init__.py` vuoto (marker di package, install-safe: nessun side-effect a import-time — FR-023)
- [ ] T002 Aggiungere il console-script `sertor-rag = "sertor_core.cli.__main__:main"` in `pyproject.toml` sezione `[project.scripts]`, accanto a `sertor-wiki-tools`
- [ ] T003 [P] Creare `src/sertor_core/cli/output.py` — modulo vuoto con docstring (proiezioni di output; riempito nelle fasi US1/US2)
- [ ] T004 [P] Creare `src/sertor_core/cli/logging_setup.py` — modulo vuoto con docstring (configurazione logging runtime; riempito in US3)

**Checkpoint**: `uv run sertor-rag --help` fallisce "no such module" (normale: `__main__.py` non esiste
ancora); `uv run python -c "import sertor_core.cli"` non produce operazioni RAG (FR-023/SC-003).

---

## Phase 2: Foundational (Estensioni additive al core — prerequisiti blocking)

**Purpose**: le tre estensioni additive al core che tutte le user story richiedono.
Devono essere complete prima di iniziare qualsiasi fase US. Sono modifiche **localizzate**
a file esistenti, senza ristrutturazioni.

**ATTENZIONE CRITICA**: nessuna fase US puo' iniziare prima che questa fase sia completa.

- [ ] T005 Aggiungere `Settings.preview_chars: int = 240` (env `SERTOR_PREVIEW_CHARS`) in `src/sertor_core/config/settings.py` — metodo `load()` legge `int(os.getenv("SERTOR_PREVIEW_CHARS", "240"))` (Principio VIII, D5)
- [ ] T006 Aggiungere `Settings.validate_backend() -> list[str]` in `src/sertor_core/config/settings.py` — metodo puro che ritorna i nomi delle variabili d'ambiente mancanti per il backend selezionato: `azure` embeddings richiede `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_EMBED_DEPLOYMENT`; `azure` store richiede `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_API_KEY`; `local` ritorna sempre `[]` (D3, FR-015)
- [ ] T007 [P] Aggiungere `BaselineEngine.ensure_index(self) -> None` in `src/sertor_core/engines/baseline.py` — estrazione del check `if not self._store.exists(self._collection): raise IndexNotFoundError(...)` gia' presente in `query()` (righe 61-65); `query()` viene refactored per chiamare `ensure_index()` prima di embed (D6, FR-012, Boy Scout Rule)
- [ ] T008 [P] Aggiungere `log_event(logging.ERROR, "embeddings_error", provider=..., reason=..., retriable=...)` nei boundary di `src/sertor_core/adapters/embeddings/ollama.py` (in `_embed_batch`, prima di sollevare `EmbeddingError`) e `src/sertor_core/adapters/embeddings/azure.py` (stesso pattern) — additivo, non cambia il comportamento d'errore (D4, FR-020, contracts/log-events.md)
- [ ] T009 [P] Aggiungere `log_event(logging.ERROR, "store_error", backend=..., reason=...)` nei boundary di `src/sertor_core/adapters/vectorstores/chroma.py` (nei blocchi `except` di `upsert`, `query`, `delete` che avvolgono `VectorStoreError`) e `src/sertor_core/adapters/vectorstores/azure_search.py` (stesso pattern) — additivo (D4, FR-020, contracts/log-events.md)
- [ ] T010 [P] Scrivere i test unitari per le estensioni di Settings in `tests/unit/test_settings_validate_backend.py`: `validate_backend()` locale ritorna `[]`; `azure` embeddings senza endpoint ritorna lista con `AZURE_OPENAI_ENDPOINT`; `azure` store senza chiave ritorna lista con `AZURE_SEARCH_API_KEY`; `preview_chars` default 240, override via env (FR-015, NFR-02)
- [ ] T011 [P] Scrivere i test unitari per `BaselineEngine.ensure_index()` in `tests/unit/test_baseline_engine.py` (file esistente, aggiunte): `ensure_index()` su store vuoto solleva `IndexNotFoundError`; `ensure_index()` su store popolato ritorna `None`; `query()` chiama `ensure_index()` internamente (D6, NFR-02)

**Checkpoint Foundation**: `uv run pytest tests/unit/test_settings_validate_backend.py tests/unit/test_baseline_engine.py -m "not cloud"` passa; il core non e' interrotto.

---

## Phase 3: User Story 1 — Indicizzare un repository dal terminale (Priority: P1) — MVP

**Goal**: `sertor-rag index <path>` indicizza un repository con un solo comando, senza scrivere codice;
emette report con conteggi chunk/embedding_dim; exit code 0/1/2 (FR-001..009, SC-001/003..005).

**Independent Test**: con provider/store mock, `sertor-rag index <tmp_dir>` ritorna exit 0, stdout
contiene `chunks=` e `embedding_dim=`; con path inesistente ritorna exit 1; con backend azure senza
credenziali ritorna exit 1 prima di qualsiasi chiamata al provider.

### Test per User Story 1

> Scrivere i test PRIMA dell'implementazione; assicurarsi che FALLISCANO.

- [ ] T012 [P] [US1] Scrivere `tests/unit/test_cli_index.py` — scenario successo: `main(["index", str(tmp_path)])` con `FakeEmbedder` + `InMemoryStore` ritorna 0 e stdout contiene `chunks=` `embedding_dim=` `documents=` (SC-001); scenario path inesistente: exit 1, stderr contiene "errore:" (FR-006); scenario backend incompleto: exit 1 prima di embedding (`FakeEmbedder.calls == 0`) (FR-015/SC-004); scenario `--json`: stdout e' JSON valido con campi `chunks`, `embedding_dim`, `documents`, `collection` (contracts/cli-commands.md); scenario `install != run`: importare `sertor_core.cli` non chiama build_indexer (FR-023/SC-003); scenario path e' file non directory: exit 1, stderr contiene "errore:" (edge case spec)
- [ ] T013 [P] [US1] Scrivere `tests/unit/test_cli_install_not_run.py` — importare `sertor_core.cli.__main__` e `sertor_core.cli` non deve produrre chiamate a `build_indexer`, `build_facade`, `build_baseline_engine` (FR-023/SC-003); mock dei build_* per asserire zero chiamate

### Implementazione User Story 1

- [ ] T014 [US1] Implementare `src/sertor_core/cli/__main__.py` — `main(argv)`: riconfigura stdout/stderr UTF-8 (come `wiki_tools/__main__.py:174-179`); costruisce il parser argparse con sub-parser `index` e `search`; flags globali `-v/--verbose`, `--log-json`, `--log-config`; sub-parser `index` con `path` (posizionale), `--corpus`, `--json`; cattura `SertorError` → stderr `"errore: {exc}"` exit 1; `argparse` gestisce exit 2 per uso errato; entry-point `if __name__ == "__main__": raise SystemExit(main())` (D8, FR-001..004, contracts/cli-commands.md)
- [ ] T015 [US1] Implementare il handler `_cmd_index(args, settings)` in `src/sertor_core/cli/__main__.py` — sequenza: (1) `setup_logging(args)` (stub per ora); (2) `Settings.load()`; (3) se `--corpus`: `settings = dataclasses.replace(settings, corpus=args.corpus)` (D7, FR-009); (4) `missing = settings.validate_backend()` → se non vuota: `raise ConfigError(f"configurazione backend incompleta: mancano {', '.join(missing)}")` (FR-015); (5) `build_indexer(settings).index(Path(args.path), rebuild=True)` → `IndexReport`; (6) stampa output via `output.format_index_report(report, json=args.json)` (FR-005/007/008)
- [ ] T016 [US1] Implementare `format_index_report(report: IndexReport, *, json: bool) -> str` in `src/sertor_core/cli/output.py` — formato umano: `"collection={r.collection} documents={r.documents} chunks={r.chunks} embedding_dim={r.embedding_dim} elapsed_ms={r.elapsed_ms}"` (contracts/cli-commands.md); formato `--json`: `json_module.dumps({"collection":..., "documents":..., "chunks":..., "embedding_dim":..., "elapsed_ms":...})` (FR-005, SC-001)
- [ ] T017 [US1] Validare path in `_cmd_index`: prima di chiamare `build_indexer`, verificare che `Path(args.path).exists()` e `Path(args.path).is_dir()`; se falso sollevare `IngestionError(f"path non valido o non e' una directory: {args.path}")` (FR-006, edge case spec); questo e' un check pre-volo della CLI (non duplica logica del core)

**Checkpoint US1**: `uv run pytest tests/unit/test_cli_index.py tests/unit/test_cli_install_not_run.py -m "not cloud"` passa; `uv run sertor-rag index . --help` stampa usage; dogfood locale: `uv run sertor-rag index .` completa con provider configurato.

---

## Phase 4: User Story 2 — Interrogare l'indice dal terminale (Priority: P2)

**Goal**: `sertor-rag search <query>` interroga l'indice e ritorna top-k risultati con path, tipo,
chunk_id, score, anteprima troncata; rispetta `-k`, `--type`, `--full`, `--json`; errore esplicito su
indice assente per qualunque `--type` (FR-010..013, SC-002).

**Independent Test**: con un indice mock precostruito, `sertor-rag search "query"` ritorna exit 0,
ogni hit contiene i 5 campi minimi (path, doc_type, chunk_id, score, preview); con indice vuoto ritorna
exit 1 con messaggio "indice inesistente"; `-k 2` ritorna al piu' 2 risultati; `--json` ritorna array
JSON valido con stessi campi; `--full` rimuove troncatura.

### Test per User Story 2

> Scrivere i test PRIMA dell'implementazione; assicurarsi che FALLISCANO.

- [ ] T018 [P] [US2] Scrivere `tests/unit/test_cli_search.py` — scenario successo `both`: `main(["search", "query"])` con indice popolato ritorna exit 0, stdout contiene `score=`, `path=`, `doc_type=`, `chunk_id=` e preview troncata (FR-010); scenario indice assente: exit 1 per `both`, `code`, `doc` (FR-012/D6); scenario `-k 2`: al piu' 2 hit (FR-011); scenario `--type code`: solo hit `doc_type=code` (FR-011); scenario `--type doc`: solo hit `doc_type=doc`; scenario `--json`: JSON array valido con campi `path`, `doc_type`, `chunk_id`, `score`, `preview` (FR-013); scenario `--full`: campo `text` integrale, nessuna ellissi (FR-010/013); scenario query vuota: exit non-zero (edge case); scenario `--corpus altro`: `settings.corpus == "altro"` nel composition (FR-009/D7); equivalenza informativa umano/JSON: stessi campi (SC-002)

### Implementazione User Story 2

- [ ] T019 [US2] Implementare il handler `_cmd_search(args, settings)` in `src/sertor_core/cli/__main__.py` — sequenza: (1) `setup_logging(args)` (stub); (2) validate query non vuota: `if not args.query.strip(): raise ConfigError("query vuota o solo spazi")`; (3) `Settings.load()` + `--corpus` override (D7); (4) `validate_backend()` → `ConfigError` se mancanti (FR-015); (5) `engine = build_baseline_engine(settings)`; `engine.ensure_index()` — strict per qualunque `--type` (D6, FR-012); (6) se `--type both`: `results = engine.query(args.query, k=args.k)`; se `code`/`doc`: `facade = build_facade(settings)`, `results = facade.search_code/search_docs(args.query, k=args.k)` (D2/D6); (7) stampa via `output.format_search_results(results, settings, json=args.json, full=args.full)` (FR-010/011/013)
- [ ] T020 [US2] Aggiungere al sub-parser `search` in `__main__.py`: `query` posizionale, `-k` int (default da `settings.default_k` — letto dopo Settings.load, oppure `None` con fallback a `settings.default_k` in `_cmd_search`), `--type` con `choices=["code","doc","both"]` default `"both"`, `--full` bool, `--json` bool, `--corpus` str (FR-011/013, contracts/cli-commands.md)
- [ ] T021 [US2] Implementare `format_search_results(results, settings, *, json, full) -> str` in `src/sertor_core/cli/output.py` — formato umano: blocco per hit numerato `[N] score={score:.3f}  doc={doc_type}  path={path}  chunk={chunk_id}\n    {preview_or_text}` (contracts/cli-commands.md); troncatura: `text[:settings.preview_chars] + "…"` se `not full and len(text) > settings.preview_chars` (D5, FR-010/013); formato `--json`: `json.dumps([{"path":..., "doc_type":..., "chunk_id":..., "score":..., "preview"|"text":...}])` (FR-013, SC-002)

**Checkpoint US2**: `uv run pytest tests/unit/test_cli_search.py -m "not cloud"` passa; `uv run sertor-rag search --help` stampa usage; dogfood: `uv run sertor-rag search "composition root"` (richiede indice precostruito).

---

## Phase 5: User Story 3 — Rendere osservabili le operazioni (Priority: P3)

**Goal**: `-v` abilita INFO strutturati sul logger `sertor_core`; `--log-json` emette record JSON;
`--log-config <file>` carica un dictConfig (YAML/JSON) per agganciare appender arbitrari; i fallimenti
ai boundary emettono un evento strutturato prima della propagazione (gia' implementato in T008/T009);
nessun segreto nei log (FR-017..022, SC-006, LSC-7).

**Independent Test**: `main(["index", str(tmp_path), "-v"])` con mock — stderr contiene almeno un record
INFO del logger `sertor_core`; `--log-json` — ogni record e' JSON parseable con campo `operation`;
`--log-config` valido — appender configurato riceve gli eventi; `--log-config` inesistente — exit 1
prima dell'operazione; un fallimento a boundary di embeddings mock produce un evento `embeddings_error`
in `caplog`; nessun campo contenente "key"/"api_key"/"token" ha valore non-`***`.

### Test per User Story 3

> Scrivere i test PRIMA dell'implementazione; assicurarsi che FALLISCANO.

- [ ] T022 [P] [US3] Scrivere `tests/unit/test_cli_logging.py` — scenario `-v`: `caplog` (livello INFO su `sertor_core`) o cattura stderr contiene evento INFO dopo operazione mock (FR-017); scenario `--log-json`: ogni linea emessa e' JSON valido, campo `operation` presente (FR-018); scenario `--log-config` JSON valido: il dictConfig e' caricato senza errori e l'appender configurato riceve eventi (FR-019); scenario `--log-config` file inesistente: exit 1, stderr "errore:", nessuna operazione eseguita (edge case spec/FR-019); scenario `--log-config` YAML senza pyyaml: exit 1 con messaggio di degradazione esplicita (D4); scenario no segreti: con settings azure mock i campi `api_key`, `token` nei log hanno valore `***` (FR-022/REQ-055); scenario fallimento boundary embeddings: `FakeEmbedder` che solleva `EmbeddingError` produce evento `embeddings_error` in `caplog` (FR-020/T008 — test di integrazione con il core)

### Implementazione User Story 3

- [ ] T023 [US3] Implementare `setup_logging(args) -> None` in `src/sertor_core/cli/logging_setup.py` — logica: (1) se `--log-config`: legge il file (autodetect JSON/YAML per estensione); JSON via `json.loads` (stdlib); YAML via `import yaml; yaml.safe_load` se `pyyaml` installato, altrimenti `raise ConfigError("--log-config YAML richiede pyyaml: installa sertor-core[yaml]")` (degradazione esplicita, D4); applica `logging.config.dictConfig(cfg)` e ritorna (ha precedenza sulle altre leve, D4); se il file non esiste: `raise ConfigError(f"--log-config: file non trovato: {args.log_config}")`; (2) se `--log-json`: costruisce `StreamHandler(stderr)` con formatter JSON che serializza `%(message)s` + `extra` del record (D4, FR-018); (3) se `-v`: imposta `logging.getLogger("sertor_core").setLevel(logging.INFO)` con `StreamHandler(stderr)` umano; (4) default (nessuna flag): livello `WARNING`, nessun handler aggiunto (FR-017)
- [ ] T024 [US3] Integrare `setup_logging(args)` nei handler `_cmd_index` e `_cmd_search` in `src/sertor_core/cli/__main__.py` — sostituisce gli stub; chiamata come prima operazione, prima di `Settings.load()`, cosi' anche gli errori di config sono loggati con la configurazione corretta (D4, FR-017..019)
- [ ] T025 [US3] Implementare il formatter JSON in `src/sertor_core/cli/logging_setup.py` — classe `JsonLogFormatter(logging.Formatter)`: `format(record)` ritorna `json.dumps({"ts": record.created, "level": record.levelname, "operation": getattr(record, "operation", None), "msg": record.getMessage(), **{k: v for k, v in record.__dict__.items() if k in _EXTRA_FIELDS}})` dove `_EXTRA_FIELDS` sono i campi di `contracts/log-events.md` (FR-018/REQ-054); i segreti sono gia' redatti da `log_event` prima che arrivino al formatter (FR-022)

**Checkpoint US3**: `uv run pytest tests/unit/test_cli_logging.py -m "not cloud"` passa; `uv run sertor-rag index . -v` emette record INFO; `uv run sertor-rag search "query" --log-json` emette JSON per linea.

---

## Phase 6: Polish e Concern Trasversali

**Purpose**: integrazione finale, validazione dogfood, documentazione schema log, copertura edge case
rimasti e revisione complessiva della suite.

- [ ] T026 [P] Aggiungere il test di repo-agnosticita' in `tests/unit/test_cli_index.py` — indicizzare due `tmp_path` distinti nello stesso test (con FakeEmbedder + InMemoryStore), verificare che le collezioni siano namespace-separate e che i file dei due repository non siano stati alterati (SC-005/FR-024)
- [ ] T027 [P] Aggiungere il test di `--corpus` override in `tests/unit/test_cli_index.py` e `tests/unit/test_cli_search.py` — `main(["index", path, "--corpus", "myns"])` → collezione inizia con `myns__`; `main(["search", "query", "--corpus", "myns"])` → `settings.corpus == "myns"` (FR-009/D7)
- [ ] T028 [P] Verificare exit code 2 per errore d'uso argparse in `tests/unit/test_cli_index.py` — `main(["unknown-cmd"])` ritorna 2 o lancia `SystemExit(2)` (FR-003); `main(["index"])` senza path ritorna 2; `main(["search"])` senza query ritorna 2; `main(["search", "q", "--type", "invalid"])` ritorna 2
- [ ] T029 Eseguire la suite completa `-m "not cloud"` e verificare che i 159 test precedenti restino verdi e che i nuovi test aggiungano copertura senza regressioni: `uv run pytest -m "not cloud" --tb=short`
- [ ] T030 [P] Aggiungere `src/sertor_core/observability/README.md` (o docstring in `logging.py`) che referenzia `specs/011-cli-esecuzione-rag/contracts/log-events.md` come schema autoritativo dei campi di log (FR-021/REQ-054)
- [ ] T031 Validare il quickstart end-to-end con provider reale: seguire `specs/011-cli-esecuzione-rag/quickstart.md` §4 (dogfood SC-008): `SERTOR_CORPUS=sertor uv run sertor-rag index .` poi `uv run sertor-rag search "composition root"` — risultati coerenti con facade/MCP (SC-008); questo e' l'unico task che richiede un provider configurato
- [ ] T032 [P] Revisione lint e type-check del codice CLI: `uv run ruff check src/sertor_core/cli/ tests/unit/test_cli_*.py --fix`; verificare assenza di import SDK di provider in `cli/` (Principio I)

---

## Dependencies & Execution Order

### Dipendenze tra fasi

```
Phase 1 (Setup)
  |
  v
Phase 2 (Foundational — BLOCCA tutte le US)
  |-- T005, T006 (Settings) → richiesti da T015, T019
  |-- T007 (ensure_index) → richiesto da T019
  |-- T008, T009 (log_event boundary) → richiesti da T022/T024
  |-- T010, T011 (test estensioni core) → prerequisito di qualita' prima delle US
  |
  +--- Phase 3 (US1 — MVP)     ← inizia dopo Phase 2
  |       |
  |       v
  |    Phase 4 (US2)           ← puo' iniziare dopo Phase 2 in parallelo con US1
  |       |                       (dipende da ensure_index T007 ma non da US1)
  |       v
  |    Phase 5 (US3)           ← puo' iniziare dopo Phase 2; T024 dipende da T014/T019
  |
  v
Phase 6 (Polish)               ← dipende da tutte le US completate
```

### Dipendenze tra user story

- **US1 (P1)**: dipende solo da Phase 2. Non dipende da US2 o US3.
- **US2 (P2)**: dipende solo da Phase 2. Non dipende da US1 (usa indice mock precostruito per i test).
  In produzione l'indice deve esistere, ma per l'implementazione/test e' indipendente.
- **US3 (P3)**: dipende da Phase 2 (T008/T009 per gli eventi di boundary). `T024` (integrazione
  `setup_logging` in `__main__.py`) dipende da T014 (US1) e T019 (US2) — la shell `__main__.py` deve
  esistere. Per minimizzare il blocco: i moduli `logging_setup.py` (T023/T025) sono sviluppabili in
  parallelo con US1/US2; solo T024 e' sequenziale.

### Dipendenze intra-story

**US1**: T012/T013 (test, [P]) → T014 (`__main__.py`) → T015 (`_cmd_index`) → T016 (`output`) → T017 (validazione path)

**US2**: T018 (test, [P]) → T019 (`_cmd_search`) → T020 (argparse search) → T021 (`format_search_results`)

**US3**: T022 (test, [P]) → T023 (`setup_logging`) → T024 (integrazione) → T025 (JsonFormatter)

---

## Esempi di esecuzione parallela

### Parallelo Phase 2 (dopo Phase 1)

```
# Track A — estensioni Settings (T005, T006, T010)
T005: Settings.preview_chars in src/sertor_core/config/settings.py
T006: Settings.validate_backend() in src/sertor_core/config/settings.py
T010: tests/unit/test_settings_validate_backend.py

# Track B — motore baseline (T007, T011)
T007: BaselineEngine.ensure_index() in src/sertor_core/engines/baseline.py
T011: tests/unit/test_baseline_engine.py (addizioni)

# Track C — log_event boundary (T008, T009)
T008: adapters/embeddings/{ollama,azure}.py
T009: adapters/vectorstores/{chroma,azure_search}.py
```

T005+T006 sullo stesso file → eseguiti sequenzialmente (o stesso developer). T007, T008, T009 su file diversi → paralleli.

### Parallelo tra User Story (dopo Phase 2)

```
# Developer A: US1 (index)
T012, T013 → T014 → T015 → T016 → T017

# Developer B: US2 (search) — file diversi da US1 (test_cli_search.py, nessun conflitto su __main__.py
# salvo _cmd_search e sub-parser search: coordinarsi su __main__.py o sviluppare su branch separati)
T018 → T019 → T020 → T021

# Developer C: US3 (logging) — logging_setup.py e' un file dedicato, nessun conflitto
T022 → T023 → T025  (T024 attende T014+T019)
```

Nota: `__main__.py` e' condiviso tra US1 e US2 (contiene sia `_cmd_index` che `_cmd_search`). Per
evitare conflitti con un singolo developer, US1 implementa il file + `_cmd_index`; US2 aggiunge
`_cmd_search` e il sub-parser search. Se parallelo con due developer: usare stub per il sottocomando
dell'altro e fare merge ordinato.

---

## Implementation Strategy

### MVP: Solo User Story 1 (index)

1. Completare Phase 1: Setup (T001..T004) — pochi minuti
2. Completare Phase 2: Foundational (T005..T011) — prerequisiti blocking
3. Completare Phase 3: US1 (T012..T017) — il valore minimo: CLI funzionante per l'indicizzazione
4. **STOP e VALIDA**: `uv run pytest tests/unit -k "cli" -m "not cloud"` + dogfood `sertor-rag index .`
5. Deploy/demo MVP — il repo Sertor e' indicizzabile via CLI

### Incrementale

1. Setup + Foundational → foundation pronta
2. US1 (index) → test indipendente → demo MVP
3. US2 (search) → test indipendente → `sertor-rag search` operativo
4. US3 (logging) → test indipendente → osservabilita' completa
5. Polish (Phase 6) → qualita', dogfood, lint
6. Ogni storia aggiunge valore senza rompere le precedenti

### Strategia parallela (singolo developer con TDD)

Il pattern TDD suggerito dagli artefatti (quickstart §5, NFR-02):
1. Scrivi i test della storia (tag [P]: vanno scritti prima dell'implementazione)
2. Verifica che FALLISCANO (`pytest ... -m "not cloud"`)
3. Implementa fino al verde
4. Checkpoint storia → procedi alla successiva

---

## Note

- `[P]` = file diversi, nessuna dipendenza su task incompleti della stessa fase
- `[USn]` = traceabilita' verso la user story della spec
- Ogni user story e' completamente verificabile con `FakeEmbedder` + `InMemoryStore` (`tests/fixtures/mocks.py`)
- Il pattern di riferimento per lo stile CLI e' `src/sertor_core/wiki_tools/__main__.py` (stesso pattern argparse, stessa mappatura `SertorError → exit 1`, stessa riconfigurazione UTF-8)
- `T031` (dogfood) e' l'unico task che richiede un provider reale (Ollama/Azure) — separato appositamente
- Exit code `2` e' gestito nativamente da argparse: non richede codice aggiuntivo (D8)
- `pyyaml` rimane opzionale: non aggiungere a `[project.dependencies]`; valutare `[project.optional-dependencies]` sezione `yaml` se richiesto, ma NON e' necessario per l'MVP
- La redazione segreti e' gia' garantita da `redact()` in `observability/logging.py`: il formatter JSON (T025) non deve reimplementarla
