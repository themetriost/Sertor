# Tasks: Nucleo wiki deterministico host-agnostico (FEAT-003-D)

**Feature**: `specs/006-nucleo-wiki-deterministico` · **Branch**: `spec/006-nucleo-wiki-deterministico`
**Input**: plan.md, spec.md, data-model.md, contracts/, research.md

**Convenzioni**: `- [x] T### [P?] [US?] descrizione con path`. `[P]` = parallelizzabile (file diversi, nessuna dipendenza
pendente). Stack: Python ≥3.11, `uv`, `pytest -m "not cloud"`, `ruff` (E,F,I,UP,B; ll 100). **Zero LLM/offline.**

---

## Phase 1 — Setup

- [x] T001 Crea il sottopacchetto `src/sertor_core/wiki_tools/__init__.py` (vuoto, riesporterà le operazioni pubbliche)
- [x] T002 Aggiungi il console-script in `pyproject.toml`: `[project.scripts]` → `sertor-wiki-tools = "sertor_core.wiki_tools.__main__:main"`; verifica `uv sync --extra dev`

## Phase 2 — Foundational (prerequisiti bloccanti per tutte le storie)

- [x] T003 [P] Definisci i contratti di risultato in `src/sertor_core/wiki_tools/contracts.py` (dataclass serializzabili: `ScanResult`/`wiki.scan/1`, `LintResult`/`wiki.lint/1`, `CollectResult`/`wiki.collect/1`, `StructureResult`/`wiki.structure/1`, `IndexResult`/`wiki.index/1`, `ErrorResult`/`wiki.error/1`) con helper `to_json()` — vedi `contracts/json-contracts.md`
- [x] T004 [P] Implementa `src/sertor_core/wiki_tools/frontmatter.py`: `parse_frontmatter(text)->dict` (regex, no lib esterne), estrazione wikilink `[[..]]`, helper di validazione campi richiesti — vedi research D2
- [x] T005 Implementa `src/sertor_core/wiki_tools/profile.py`: `WikiProfile` + `load_profile(config_path, root_override=None)` da TOML (`tomllib`); validazione (`root`/`taxonomy`/`language` → `ConfigError` esplicito su assente/malformata; tassonomia-dir assente → warning+skip). Default = profilo Sertor come dato esterno. `ConfigError` in `domain/errors.py` (o sottoclasse locale) — vedi data-model.md, Principio IV
- [x] T006 [P] Crea `wiki.config.toml` alla radice (profilo Sertor `code+doc`, lingua `it`) — vedi quickstart.md
- [x] T007 [P] Crea la fixture ospite finto `tests/fixtures/doc_only_host/` (`wiki.config.toml` con radice `knowledge/`, `source_dirs=["docs"]`, lingua `en`, tassonomia diversa + un mini-albero di pagine) per SC-001

**Checkpoint**: profilo, frontmatter e contratti pronti → le storie possono partire.

## Phase 3 — User Story 1 (P1): Config host-agnostica + scan del lavoro pendente — **MVP**

**Goal**: stesso nucleo su ospiti diversi cambiando solo la config; rilevare lavoro non registrato (mtime).
**Independent test**: `scan` su Sertor e sull'ospite finto `doc-only` con lo stesso codice, solo config diversa.

- [x] T008 [US1] Implementa `src/sertor_core/wiki_tools/scan.py`: `scan(profile)->ScanResult` (mtime delle `source_dirs` con `exclude` vs mtime ultima voce di `log_file`; `message` da `strings` nella lingua del profilo; log strutturato via `observability.logging`) — FR-005, research D3
- [x] T009 [US1] Implementa `src/sertor_core/wiki_tools/__main__.py`: parsing argomenti (`<op>`, `--config`, `--root`, `--json`), dispatch a `scan`, stampa contratto JSON o output umano; exit code esplicito su `ConfigError` — vedi contracts/cli-commands.md
- [x] T010 [US1] Rifattorizza `.claude/hooks/wiki-pending-check.ps1` in **thin wrapper**: invoca `uv run sertor-wiki-tools scan --config <root>/wiki.config.toml --json` e mappa `pending`/`message` al formato hook (Stop/SessionEnd) — vedi quickstart.md
- [x] T011 [P] [US1] Unit `tests/unit/test_wiki_tools_profile.py`: load/validate da TOML, `ConfigError` su config assente/malformata, tassonomia-dir assente → skip
- [x] T012 [P] [US1] Unit `tests/unit/test_wiki_tools_scan.py`: conteggio mtime con repo finto in `tmp_path`; **SC-001** (stessa `scan` su `doc_only_host`, codice immutato); **SC-003** (parità di conteggio con la logica attuale a parità di condizioni)

**Checkpoint**: MVP host-agnostico dimostrato end-to-end (Principio X provato).

## Phase 4 — User Story 2 (P2): Struttura e convenzioni non distruttive

**Independent test**: init su cartella vuota crea la struttura; re-run non cambia nulla; wiki esistente non toccato; validate segnala non conformità.

- [x] T013 [US2] Implementa `src/sertor_core/wiki_tools/structure.py`: `init_structure(profile)->StructureResult` (crea cartelle tassonomia + `index_file`/`log_file` con contenuto minimo; **non sovrascrive** esistenti; idempotente) — FR-003, SC-006
- [x] T014 [US2] Estendi `__main__.py` con `structure init` e `validate` (validazione convenzioni: frontmatter richiesto, wikilink, kebab-case, area) → `wiki.lint/1` (sezioni frontmatter+naming) — FR-004
- [x] T015 [P] [US2] Unit `tests/unit/test_wiki_tools_structure.py`: creazione, idempotenza, non-distruttività (indice/registro preesistenti intatti)
- [x] T016 [P] [US2] Unit `tests/unit/test_wiki_tools_frontmatter.py`: parse frontmatter, estrazione wikilink, rilevazione campi mancanti e naming non conforme

## Phase 5 — User Story 3 (P2): Lint strutturale meccanico

**Independent test**: su wiki-fixture con difetti iniettati, rileva tutti e solo quelli.

- [x] T017 [US3] Implementa `src/sertor_core/wiki_tools/lint.py`: `lint(profile)->LintResult` (link interni rotti, pagine orfane, frontmatter mancante; **nessun** giudizio semantico) — FR-006
- [x] T018 [US3] Estendi `__main__.py` con il comando `lint` → `wiki.lint/1`
- [x] T019 [P] [US3] Unit `tests/unit/test_wiki_tools_lint.py`: **SC-004** (100% dei difetti iniettati — link rotto, orfano, frontmatter mancante — e 0 falsi positivi su wiki pulito)

## Phase 6 — User Story 4 (P3): Mappa pagine + registri idempotenti

**Independent test**: enumerazione restituisce la mappa attesa; append-registro/aggiorna-indice idempotenti.

- [x] T020 [US4] Implementa `src/sertor_core/wiki_tools/collect.py`: `collect(profile)->CollectResult` (enumera pagine + metadati, senza corpo; `rel_path` POSIX) — FR-007
- [x] T021 [US4] Implementa `src/sertor_core/wiki_tools/registry.py`: `append_log(profile, op, title)` e `upsert_index(profile, page, summary)` idempotenti; id stabile = path relativo — FR-008/009, SC-002
- [x] T022 [US4] Estendi `__main__.py` con il comando `collect` → `wiki.collect/1`
- [x] T023 [P] [US4] Unit `tests/unit/test_wiki_tools_collect.py`: mappa pagine attesa su wiki noto
- [x] T024 [P] [US4] Unit `tests/unit/test_wiki_tools_registry.py`: **SC-002** (re-run identico: nessun duplicato, nessun timestamp modificato)

## Phase 7 — User Story 5 (P3): Orchestrazione indicizzazione a collezioni separate

**Independent test**: rigenerando il solo wiki, la collezione delle sorgenti resta invariata.

- [x] T025 [US5] Implementa `src/sertor_core/wiki_tools/indexing.py`: `index_wiki(profile)->IndexResult` riusando il facade/indexer di `sertor_core` (import **lazy**); collezione separata via `collection_name((corpus, provider))`; **no-op pulito** se `rag.enabled=false` — FR-010, research D5
- [x] T026 [US5] Estendi `__main__.py` con il comando `index` → `wiki.index/1`
- [x] T027 [P] [US5] Test `tests/unit/test_wiki_tools_indexing.py`: no-op con `rag.enabled=false`; con mock/indexer fittizio, collezione separata e rigenerazione indipendente (marker `not cloud`; mock degli embeddings)

## Phase 8 — Polish & cross-cutting

- [x] T028 [P] Riesporta le operazioni pubbliche in `src/sertor_core/wiki_tools/__init__.py`; verifica log strutturati (Principio IX) in ogni operazione; docstring di dominio (Principio VII)
- [x] T029 [P] `uv run ruff check --fix .` e correzione warning residui (E,F,I,UP,B; ll 100)
- [x] T030 Verifica end-to-end: `uv run pytest -m "not cloud" tests/unit/test_wiki_tools_*.py` verde; controlla SC-001/002/004/005/006; smoke `uv run sertor-wiki-tools scan --config wiki.config.toml --json` su Sertor

---

## Dipendenze e ordine

- **Setup (T001-T002)** → **Foundational (T003-T007)** → storie.
- **Foundational** blocca tutte le storie: `profile.py`(T005), `frontmatter.py`(T004), `contracts.py`(T003) sono prerequisiti.
- **US1 (T008-T012)** = MVP, indipendente dopo Foundational.
- **US2/US3/US4** dipendono solo da Foundational (e US3/US4 usano `collect`/`frontmatter`); largamente indipendenti tra loro.
- **US5 (T025-T027)** dipende da `profile`+`collect` e dal facade esistente di `sertor_core`.
- **Polish (T028-T030)** dopo le storie volute.

## Esecuzione parallela (esempi)
- Foundational: `T003`, `T004`, `T006`, `T007` in parallelo (file diversi); `T005` dopo (usa errori).
- Dentro una storia: i test `[P]` in parallelo all'implementazione una volta pronte le firme.

## MVP
**US1 (Phase 1+2+3, T001-T012)**: config host-agnostica + `scan` + hook wrapper. Dimostra il Principio X end-to-end
(SC-001) con rischio minimo. Le storie P2/P3 sono incrementi indipendenti.
