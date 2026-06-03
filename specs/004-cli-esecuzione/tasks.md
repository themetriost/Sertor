---
description: "Task list — CLI esecuzione (FEAT-CLI-004)"
---

# Tasks: CLI — esecuzione delle capacità del core

**Input**: Design documents from `specs/004-cli-esecuzione/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅;
**sertor-core (FEAT-001/002/003) in `master`**.

**Tests**: INCLUSI (Principio V; NFR-02). Comandi via `cli.main([...])` con `build_*` del core
monkeypatchati a mock; nessun cloud/rete.

**Organization**: per user story. La CLI vive in `src/sertor_cli/` (sottile sul core). Foundational =
parser+dispatch+osservabilità+output+estensione log errori del core.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [ ] T001 Aggiorna `pyproject.toml`: aggiungi il pacchetto `sertor_cli` ai target wheel, `[project.scripts] sertor = "sertor_cli.cli:main"`, e la dipendenza `pyyaml` (per `--log-config` YAML)
- [ ] T002 Crea lo scheletro del pacchetto: `src/sertor_cli/{__init__.py, __main__.py}` e `src/sertor_cli/commands/__init__.py` (docstring)

---

## Phase 2: Foundational (parser + osservabilità + output + estensione core — BLOCCANTI)

- [ ] T003 Implement `src/sertor_cli/observability.py`: setup logging — `-v/--verbose` (INFO), `--log-json` (formatter JSON minimale interno), `--log-config <file>` (dictConfig da YAML/JSON, precedenza); mira al logger `sertor_core` (REQ-050/051/052)
- [ ] T004 [P] Implement `src/sertor_cli/output.py`: formattazione risultati `search` (testo / JSON), **anteprima troncata** (lunghezza limite) con `--full` per il testo completo; formattazione `IndexReport` (REQ-020/023)
- [ ] T005 Implement `src/sertor_cli/cli.py`: parser argparse con sottocomandi `index`/`search`/`wiki index`, opzioni globali (`-v/--verbose`, `--log-json`, `--log-config`), dispatch ai comandi, **mapping eccezioni di dominio → messaggio leggibile + exit code** (REQ-001/002/003/004); `__main__.py` chiama `cli.main()`
- [ ] T006 [P] Estendi il core (additivo): `log_error(operation, exc, **fields)` in `src/sertor_core/observability/logging.py` e chiamala sui boundary (adapter embeddings/store; `services/indexing.py`) **prima** del raise (REQ-053)

**Checkpoint**: entry-point, osservabilità, output e log-errori pronti → i comandi possono essere implementati

---

## Phase 3: User Story 1 - `sertor index` (Priority: P1) 🎯 MVP

**Goal**: indicizzare un repo da CLI con report; non distruttivo; errori espliciti; install≠run.

**Independent Test**: `main(["index", repo])` con `build_*` mockati → exit 0 + report; path inesistente → exit≠0; provider assente → bloccato.

### Tests for US1 ⚠️
- [ ] T007 [P] [US1] Test in `tests/unit/test_cli_index.py`: `index <repo>` (mock) → exit 0 + report (chunks/dim) (REQ-010); `--corpus` → collezione namespaced (REQ-014); path inesistente → exit≠0 + messaggio (REQ-011); provider assente → bloccato con errore (REQ-041); import del modulo non indicizza nulla (install≠run, REQ-060)

### Implementation for US1
- [ ] T008 [US1] Implement `src/sertor_cli/commands/index_cmd.py`: legge `Settings`, costruisce `build_indexer(settings)` (corpus da `--corpus`/config), esegue `index(path, rebuild=True)`, stampa il report; errori di dominio propagati a `cli.main` (REQ-010..014/041)

**Checkpoint**: US1 testabile

---

## Phase 4: User Story 2 - `sertor search` (Priority: P1)

**Goal**: interrogare l'indice da CLI con metadati; default dal core; testo/JSON; errore su indice mancante.

**Independent Test**: `main(["search","q"])` (mock, indice popolato) → risultati; `-k`/`--type`/`--json`/`--full`; indice mancante → exit≠0.

### Tests for US2 ⚠️
- [ ] T009 [P] [US2] Test in `tests/unit/test_cli_search.py`: risultati con path/tipo/chunk_id/score/anteprima (REQ-020); default da core (`default_k`, `both`) (REQ-021); `--json` → array JSON, `--full` → testo intero (REQ-023); indice inesistente → exit≠0 + "costruisci prima l'indice" (REQ-022)

### Implementation for US2
- [ ] T010 [US2] Implement `src/sertor_cli/commands/search_cmd.py`: costruisce `build_baseline_engine`/`build_facade` da config, esegue la query (k/type dai default del core se omessi), passa i risultati a `output.py` (testo/JSON/full); `IndexNotFoundError` → propagata (REQ-020..023)

**Checkpoint**: US2 testabile

---

## Phase 5: User Story 3 - `sertor wiki index` (Priority: P2)

**Goal**: indicizzare il wiki nel corpus (riusa `index_wiki`).

**Independent Test**: `main(["wiki","index",wiki])` (mock) → n. documenti; radice vuota → warning, indice immutato.

### Tests for US3 ⚠️
- [ ] T011 [P] [US3] Test in `tests/unit/test_cli_wiki.py`: `wiki index <wiki>` (mock) → exit 0 + n. documenti (REQ-030); radice vuota/senza .md → warning, exit 0, indice immutato (REQ-031)

### Implementation for US3
- [ ] T012 [US3] Implement `src/sertor_cli/commands/wiki_cmd.py`: sottocomando `wiki index <wiki>` che chiama `index_wiki(wiki_path, settings)` e stampa il report (REQ-030/031)

**Checkpoint**: US3 testabile

---

## Phase 6: User Story 4 - Osservabilità configurabile (Priority: P2)

**Goal**: log visibili e collegabili ad appender esterni; errori loggati; nessun segreto.

**Independent Test**: con `-v` eventi INFO; con `--log-json` record JSON; con `--log-config` un handler riceve gli eventi; errore di boundary → evento di log.

### Tests for US4 ⚠️
- [ ] T013 [P] [US4] Test in `tests/unit/test_cli_observability.py`: `-v` → log INFO del core visibili (caplog) (REQ-050); `--log-json` → record JSON (REQ-051); `--log-config <tmp.yaml>` → handler configurato riceve eventi (REQ-052); errore su boundary → evento di log emesso (REQ-053); nessun segreto nei log (REQ-055)

### Implementation for US4
- [ ] T014 [US4] Rifinire `observability.py` e l'integrazione in `cli.main` (applicare il setup logging in base alle opzioni globali prima di eseguire il comando); verificare la precedenza `--log-config` > `-v`/`--log-json` (REQ-050..052)

**Checkpoint**: US4 verificata

---

## Phase 7: Polish & Cross-Cutting

- [ ] T015 Documentazione: tabella dei **campi di log per operazione** (REQ-054) in `src/sertor_core/observability/README.md` (o sezione del README) — utile per configurare appender esterni
- [ ] T016 [P] Aggiorna `src/sertor_core/README.md` (o un nuovo `src/sertor_cli/README.md`) con la sezione "CLI `sertor`" (index/search/wiki + osservabilità) allineata a quickstart.md
- [ ] T017 [P] Run full suite + ruff; verifica install≠run (nessun side-effect su import) e che `python -m sertor_cli --help` / `sertor --help` funzionino

---

## Dependencies & Execution Order

- **Setup (T001/T002)** → **Foundational (T003–T006)**: sbloccano tutto. T005 (cli) dopo T003/T004.
- **US1 (T007/T008)**: dopo Foundational.
- **US2 (T009/T010)**: dopo Foundational (output).
- **US3 (T011/T012)**: dopo Foundational.
- **US4 (T013/T014)**: l'impianto è in T003; qui si verifica e si rifinisce l'integrazione + T006 (log errori).
- **Polish (T015–T017)**: dopo le user story.

### Parallel Opportunities
- Foundational: T004 e T006 in parallelo (T003/T005 sequenziali sul parser).
- Test [P] di story diverse parallelizzabili.

---

## Implementation Strategy

MVP = Setup + Foundational + US1 (`index`) + US2 (`search`): il ciclo eseguibile minimo (e l'entry
point per il dogfooding di produzione). Poi US3 (`wiki index`), US4 (osservabilità), Polish.

## Notes

- La CLI **consuma** il composition root del core; niente logica RAG nella CLI (Principio I, NFR-01).
- Estensione del core (log errori) additiva e non-breaking.
- Test con mock (`build_*` monkeypatchati); nessun provider reale necessario per i test.
- Commit per checkpoint (delega al `configuration-manager`).
- **Mapping requisiti→story**: US1=REQ-001..004,010..014,040,041,060,061; US2=REQ-020..023;
  US3=REQ-030,031; US4=REQ-050..055; trasversali su tutte.
