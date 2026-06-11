# Implementation Plan: CLI di esecuzione RAG `sertor-rag`

**Branch**: `011-cli-esecuzione-rag` | **Date**: 2026-06-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/011-cli-esecuzione-rag/spec.md`

## Summary

Aggiungere la terza superficie d'uso del nucleo `sertor-core` — il **terminale** — tramite un
console-script `sertor-rag` (accanto a `sertor-wiki-tools`) con i sottocomandi `index <path>` e
`search <query>`. La CLI è un **layer sottile** (Principio I/NFR-01): fa parsing degli argomenti,
carica la configurazione centralizzata (`Settings`), valida staticamente i parametri del backend,
caba i punti d'ingresso del composition root (`build_indexer`, `build_facade`,
`build_baseline_engine`) e formatta l'output (umano/`--json`). Completa l'osservabilità a runtime
(`-v`, `--log-json`, `--log-config` dictConfig) e aggiunge in modo **additivo** al core un evento di
log strutturato sui fallimenti ai boundary (embeddings/store/indexing). Nessuna logica RAG nuova:
le capacità restano nel core, la CLI le orchestra.

Approccio tecnico (da `research.md`): modulo `src/sertor_core/cli/` (argparse, nessuna dipendenza
nuova); via **strict** per `search` su indice assente via `BaselineEngine`; validazione statica
backend come metodo puro su `Settings` (niente default duplicati); anteprima troncata governata da
un nuovo default centralizzato `Settings.preview_chars`; `--corpus` via `replace(settings, corpus=)`.

## Technical Context

**Language/Version**: Python ≥ 3.11 (vincolo V-4 / costituzione).

**Primary Dependencies**: solo `sertor-core` (stesso pacchetto) + `argparse` (stdlib). Nessuna
dipendenza obbligatoria nuova. `pyyaml` resta **opzionale** (solo per `--log-config` in YAML; JSON
dictConfig funziona con la sola stdlib — degradazione esplicita se YAML richiesto senza `pyyaml`).

**Storage**: nessuno proprio. La persistenza (vector store Chroma/Azure AI Search) è interamente del
core; la CLI scrive solo nello store dell'indice via `build_indexer`. Non distruttiva sui file
target (FR-008).

**Testing**: `pytest` con mock structural-typing (`tests/fixtures/mocks.py`); marker `cloud`
escluso dalla CI locale. Tutta la superficie CLI testabile senza rete (NFR-02/SC-007).

**Target Platform**: Linux e Windows (NFR-03); I/O UTF-8 stabile come in `wiki_tools/__main__.py`.

**Project Type**: CLI sottile (console-script) sopra una libreria — single project.

**Performance Goals**: N/A (la CLI è I/O e orchestrazione; il costo è nel core: embeddings/store).

**Constraints**: `install ≠ run` (FR-023/Principio VI); repo-agnostica (FR-024/Principio X); exit
code per scripting (FR-004); errori leggibili non stack trace (NFR-04); nessun segreto su file
versionati né nei log (FR-016/022).

**Scale/Scope**: 2 sottocomandi, ~6 opzioni; un package CLI (`cli/__main__.py`, `output.py`,
`logging_setup.py`); estensioni additive minime al core (un metodo su `Settings`, un default
centralizzato, un metodo su `BaselineEngine`, `log_event(ERROR)` ai boundary).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Gate derivati dalla costituzione (`.specify/memory/constitution.md`, v1.1.0).

### Check iniziale (pre-Phase 0)

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** la CLI vive in `sertor_core/cli/` ma è un
  **consumatore** del core (importa `build_*`, `Settings`, eccezioni); il core NON importa `cli/`.
  Nessun SDK di provider nel CLI: l'unico posto che conosce gli adapter resta `composition.py`. La
  CLI non tocca lo store concreto (D2/D6). **PASS**.
- [x] **II — Boundary & local-first:** la CLI non introduce dipendenze esterne; la scelta
  locale↔cloud resta guidata da `Settings` (`RAG_BACKEND`/`SERTOR_STORE_BACKEND`). **PASS**.
- [x] **III — YAGNI & unità piccole:** `argparse` (stdlib), nessun framework CLI; estensioni al core
  minime e motivate da requisiti presenti (FR-015/020/012). `pyyaml` solo opzionale. **PASS**.
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** via strict per `search` (`IndexNotFoundError`,
  D2/D6); validazione statica blocca prima dei servizi (D3); nessun risultato vuoto silenzioso;
  eccezioni di dominio mappate in messaggi leggibili + exit non-zero. **PASS**.
- [x] **V — Testabilità & misure:** ogni comando testabile con mock senza rete (NFR-02/SC-007). La
  feature non introduce un nuovo motore RAG → nessuna nuova soglia hit@k/MRR da fissare (le misure
  restano quelle del baseline FEAT-002; SC-008 verifica solo coerenza CLI↔facade). **PASS**.
- [x] **VI — Idempotenza & non-distruttività:** `index` delega a `build_indexer().index(rebuild=True)`
  (rebuild idempotente, ID stabili); `install ≠ run` (FR-023, test dedicato); non distruttiva sui
  file target (FR-008). **PASS**.
- [x] **VII — Leggibilità:** naming di dominio (`index`/`search`, `ensure_index`, `validate_backend`,
  `preview`); messaggi d'errore azionabili. **PASS**.
- [x] **VIII — Configurabilità centralizzata:** tutte le scelte (provider/backend/`default_k`/
  troncatura) vengono da `Settings`; nessun default hardcoded nel CLI — la troncatura aggiunge
  `Settings.preview_chars` (default centralizzato), la validazione backend vive su `Settings`. **PASS**.
- [x] **IX — Osservabilità:** la CLI rende configurabili livello/formato/appender del logger
  `sertor_core` senza toccare il core; estensione additiva FR-020 (evento ERROR ai boundary); campi
  documentati in `contracts/log-events.md` (FR-021); redazione segreti già nel core. **PASS**.
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** la CLI opera su un `<path>` arbitrario, nessuna
  assunzione su struttura/linguaggio/dimensione (FR-024); ciò che varia per ospite sta in
  `Settings`/`--corpus`, non nel corpo. Il dogfooding (SC-008) è strumentale, non giustifica
  hardcoding. **PASS**.

**Esito pre-Phase 0: PASS** (nessuna violazione, nessuna voce in Complexity Tracking).

### Re-check (post-Phase 1 design)

Dopo la stesura di `research.md`, `data-model.md` e `contracts/`, i gate restano soddisfatti:

- **I:** confermato — `data-model.md` esclude entità di dominio nuove; le viste CLI sono pure
  proiezioni; nessun accesso allo store concreto dal CLI (`ensure_index` incapsula il check nel core).
- **IV/VIII:** confermati e rafforzati — `validate_backend()` su `Settings` (D3) evita di duplicare
  i campi di backend; `preview_chars` colloca la troncatura nella config centralizzata (D5).
- **IX:** confermato — `contracts/log-events.md` fissa lo schema dei campi per operazione, inclusi i
  nuovi eventi ERROR additivi, con garanzia di redazione.
- Nessun nuovo design ha introdotto SDK nel core o nel CLI, né default hardcoded.

**Esito post-Phase 1: PASS** (Complexity Tracking vuoto).

## Project Structure

### Documentation (this feature)

```text
specs/011-cli-esecuzione-rag/
├── plan.md              # questo file
├── research.md          # Phase 0 — decisioni D1..D8
├── data-model.md        # Phase 1 — entità riusate + viste CLI + input model
├── quickstart.md        # Phase 1 — guida d'uso
├── contracts/
│   ├── cli-commands.md  # sinossi comandi, output, exit code
│   └── log-events.md    # schema campi di log per operazione (FR-021)
└── tasks.md             # Phase 2 (/speckit-tasks — NON creato qui)
```

### Source Code (repository root)

```text
src/sertor_core/
├── cli/                      # NUOVO — layer CLI sottile (consumatore del core)
│   ├── __init__.py
│   ├── __main__.py           # entry-point: parse → composition → formatta; exit code
│   ├── output.py             # proiezioni/viste: report index, risultati search (umano/JSON, troncatura)
│   └── logging_setup.py      # -v / --log-json / --log-config (dictConfig)
├── config/
│   └── settings.py           # + Settings.validate_backend(); + preview_chars / SERTOR_PREVIEW_CHARS
├── engines/
│   └── baseline.py           # + BaselineEngine.ensure_index() (estrazione del check esistente)
├── adapters/
│   ├── embeddings/{ollama,azure}.py   # + log_event(ERROR, "embeddings_error", ...) al boundary
│   └── vectorstores/{chroma,azure_search}.py  # + log_event(ERROR, "store_error", ...) al boundary
└── observability/
    └── logging.py            # invariato (riusa log_event/redact)

pyproject.toml                # + [project.scripts] sertor-rag = "sertor_core.cli.__main__:main"

tests/
└── unit/
    ├── test_cli_index.py     # NUOVO — US1 con mock
    ├── test_cli_search.py    # NUOVO — US2 con mock (k/type/full/json, indice assente strict)
    ├── test_cli_logging.py   # NUOVO — US3 (-v/--log-json/--log-config; no segreti)
    ├── test_cli_install_not_run.py  # NUOVO — FR-023 (import non avvia operazioni)
    └── test_settings_validate_backend.py  # NUOVO — FR-015
```

**Structure Decision**: single project, CLI **dentro** `sertor_core` (package `cli/`), coerente col
precedente `wiki_tools` e con D1 (nessuna dipendenza extra → nessun package separato come
`sertor_mcp`). Le modifiche al core sono additive e localizzate (config/engine/adapters), nessuna
ristrutturazione.

## Complexity Tracking

> Nessuna violazione del Constitution Check. Tabella non necessaria.
