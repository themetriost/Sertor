# Implementation Plan: Ground-truth & valutazione della pertinenza (FEAT-001)

**Branch**: `065-ground-truth-valutazione` | **Date**: 2026-06-20 | **Spec**:
[`spec.md`](spec.md)

**Input**: `specs/065-ground-truth-valutazione/spec.md` ·
`requirements/retrieval-qualita/ground-truth-valutazione/requirements.md` (REQ-001..062, RNF-1..6) ·
`requirements/retrieval-qualita/epic.md` (CS-1..5).

> **Nota di processo.** `.specify/scripts/.../setup-plan.ps1` e `.claude/skills/speckit-plan/SKILL.md`
> **assenti** nel repo → parametri per convenzione dal branch; nessun hook SpecKit eseguito. Git
> **delegato** al flusso principale / `configuration-manager` (mai eseguito qui). MCP `sertor-rag`
> interrogato per l'ancoraggio al codice; **nessun errore tool** da riportare.

## Summary

Promuovere l'harness di valutazione del retrieval da **fixture di test** a **capacità host-side di prima
classe**: una **suite-dato versionata** del progetto (`eval/suite.toml`, TOML), un **run deterministico
via vehicle** (`sertor-rag eval run` → `hit-rate@k`/`MRR`, report umano + JSON con dettaglio per-query),
un **gate di non-regressione** (`eval/baseline.toml` + tolleranza, exit non-zero sotto baseline), e i
**seam** per la genesi assistita (FEAT-008, skill) e il feedback (FEAT-009, skill) **senza** che il run
dipenda mai da un LLM. Approccio cardine: **riusare** `evaluate`/`EvalReport`/`QueryableEngine`
(`engines/evaluation.py`) e la forma `(query, expected, kind)` del fixture, **estendendoli** in modo
**additivo non-breaking** (solo `EvalReport.per_query` + `QueryOutcome` nuovi nel core); tutto il resto
in un servizio nuovo `services/eval/` + sottocomando CLI thin (Principio I/XI). Il `kind` resta metadato
dell'artefatto/report (la firma di `evaluate` non cambia). 5 forche di design decise dall'utente
(TOML · baseline-su-file+tolleranza · skill-pattern · `sertor-rag eval` · validazione write-time contro
l'indice) progettate in [`research.md`](research.md).

## Technical Context

**Language/Version**: Python ≥ 3.11 (`tomllib` stdlib = floor del progetto).
**Primary Dependencies**: solo **stdlib** (`tomllib`/`tomllib`-read, serializzatore TOML a mano,
`sqlite3` via `IndexManifest` esistente). **Nessuna nuova dipendenza** (`tomli-w` valutato e **scartato**
— research DA-a; adottabile come extra solo se il round-trip fallisce su casi reali).
**Storage**: artefatti **versionati** `eval/suite.toml` + `eval/baseline.toml` (root ospite,
`SERTOR_EVAL_DIR`); elenco documenti indicizzati letto da `IndexManifest` (SQLite gitignored).
**Testing**: `pytest` (unit, `not cloud`, mock/Chroma locale — RNF-1); funzioni pure (IO suite/baseline,
`compare_to_baseline`, `validate_paths`) testabili senza rete; CLI con core mockato (stile
`test_cli_search`).
**Target Platform**: CLI host-agnostica (qualunque progetto ospite, Principio X).
**Project Type**: libreria + CLI (single project — core `src/sertor_core`, pacchetto installer
`packages/sertor`).
**Performance Goals**: suite di poche decine di casi in tempi interattivi/CI; costo dominato dalle query
di retrieval, non dall'harness (RNF-5).
**Constraints**: determinismo (REQ-035); additività a leve spente (costo identico, SC-009); local-first
(no cloud — confronto cloud = FEAT-002 fuori ambito); confine D↔N (il core/CLI non chiama mai un LLM).
**Scale/Scope**: ~1 servizio nuovo (`services/eval/`), ~1 sottocomando CLI (`eval` + 3 azioni), 4 errori
di dominio, 2 manopole `Settings`, 2 voci nei template `.env`, 1 estensione additiva di `EvalReport`.

## Constitution Check (PRE-design)

*GATE prima di Phase 0. Gate derivati da `.specify/memory/constitution.md` v1.2.0.*

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** la misura deterministica vive nel core
  (`evaluate` riusato; servizio `services/eval/` puro), il CLI è **thin** (parsing → composition →
  format). Nessun import di SDK provider o della CLI nel core; esercitabile con engine mock (i 2 test
  strict già lo fanno). **PASS**
- [x] **II — Boundary & local-first:** nessun nuovo boundary verso provider esterni (suite/baseline sono
  **dati**, non adapter); valutazione in locale (mock/Chroma); confronto cloud fuori ambito (FEAT-002).
  **PASS**
- [x] **III — YAGNI & unità piccole:** **nessuna nuova porta Protocol** (suite/baseline = dati, single
  consumer, come `IndexManifest`); **nessuna nuova dipendenza** (`tomli-w` scartato, serializzatore a
  mano per schema piatto); funzioni pure piccole (IO/compare/validate). **PASS**
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** `SuiteNotFoundError`/`SuiteValidationError`
  (nomina il caso)/`SuiteWriteError`/`RegressionDetected`, tutti `SertorError` → exit 1; manifest assente
  → `None` **gestito esplicitamente** (degrado onesto, mai «tutto ok» silenzioso); suite vuota → fallisce
  azionabile, mai zero ingannevole (REQ-032). **PASS**
- [x] **V — Testabilità & misure:** **è** la feature della misura (hit@k/MRR su ground-truth, Principio V
  reso operativo); funzioni pure F.I.R.S.T., core con mock; baseline = livello accettato del progetto.
  **PASS**
- [x] **VI — Idempotenza & non-distruttività:** `add-case`/`write_suite` preservano i casi esistenti,
  ordine stabile, re-run senza duplicati (REQ-011); baseline aggiornata **solo** su flag esplicito
  (REQ-044). **PASS**
- [x] **VII — Leggibilità:** vocabolario di dominio (evaluate/hit-rate/mrr/baseline/regression);
  funzioni piccole, guard clause. **PASS**
- [x] **VIII — Configurabilità centralizzata:** `eval_dir`/`eval_tolerance` default **solo** in
  `Settings` (env `SERTOR_EVAL_DIR`/`SERTOR_EVAL_TOLERANCE`), mai hardcodati. **PASS**
- [x] **IX — Osservabilità:** il run emette evento `eval` (provider, metriche, regressed, tolerance) via
  `log_event`; **metrics-only, nessun testo libero/segreto** (RNF-3, contract `event-eval.md`). **PASS**
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** suite/baseline = dato dell'**ospite** in `eval/`
  (override config), niente assunzioni Sertor nel corpo; il fixture Sertor è **esempio dogfood**, non
  spedito; rebase path (REQ-005). Manopole/skill via installer (REQ-061). **PASS**
- [x] **XI — Consumo via vehicles:** il run accede al retrieval/manifest **solo** via factory `build_*`
  della composition (il CLI è il vehicle); la skill esterna (FEAT-008/009) invoca i **sottocomandi**
  (`eval validate-path`/`add-case`), **mai** importa `sertor_core`; eccezione test invariata. **PASS**

**Esito PRE-design: 11/11 PASS, nessuna deroga.**

## Project Structure

### Documentation (this feature)
```text
specs/065-ground-truth-valutazione/
├── plan.md              # questo file
├── research.md          # Phase 0: 5 forche + 3 nodi
├── data-model.md        # Phase 1: entità (core estese + eval/* nuove)
├── quickstart.md        # Phase 1: percorso utente
├── contracts/
│   ├── cli-eval.md      # contratto sottocomando `sertor-rag eval`
│   ├── artifacts-toml.md# schema suite.toml + baseline.toml
│   └── event-eval.md    # evento osservabilità `eval`
└── tasks.md             # Phase 2 (/speckit-tasks — NON creato qui)
```

### Source Code (repository root)
```text
src/sertor_core/
├── engines/
│   └── evaluation.py            # ESTESO: + QueryOutcome, EvalReport.per_query (additivo)
├── services/
│   └── eval/                    # NUOVO servizio deterministico
│       ├── suite_io.py          # load/write/add/amend suite (tomllib read + writer a mano)
│       ├── baseline_io.py       # load/write baseline TOML
│       ├── regression.py        # compare_to_baseline → RegressionVerdict (puro)
│       └── runner.py            # run_evaluation (avvolge evaluate, evento eval) + validate_paths
├── domain/
│   └── errors.py                # + SuiteNotFoundError/SuiteValidationError/SuiteWriteError/RegressionDetected
├── config/
│   └── settings.py              # + eval_dir, eval_tolerance (default + env)
├── composition.py               # + build_eval_runner, build_indexed_docs (vehicle, Princ. XI)
└── cli/
    ├── __main__.py              # + sottocomando `eval` (run/add-case/validate-path)
    └── output.py                # + format_eval_report/comparison/regression/path_validation

packages/sertor/src/sertor_installer/assets/rag/
├── env.local.tmpl               # + SERTOR_EVAL_DIR / SERTOR_EVAL_TOLERANCE (commentate)
└── env.azure.tmpl               # idem

eval/                            # DOGFOOD (repo Sertor): suite migrata dal fixture
└── suite.toml                   # esempio, non spedito agli ospiti

tests/
├── unit/                        # suite_io, baseline_io, regression, runner, validate_paths, cli eval, output
└── integration/                 # gate non-regressione e2e su mock/Chroma (not cloud)
```

**Structure Decision**: single project. Il **core** ospita la misura (servizio `services/eval/` +
estensione additiva di `evaluation.py`); il **CLI** è un thin consumer; l'**installer** cabla le
manopole. Le skill (FEAT-008/009) sono separate e seguono (P2).

## Phase 0 — Research
Vedi [`research.md`](research.md). Forche decise: **DA-a** TOML + serializzatore a mano (tomllib
read-only; `tomli-w` scartato/rivalutabile); **DA-b** baseline-su-file + tolleranza (pavimento assoluto
rinviato Could); **DA-c** skill nuova che riusa il *pattern* di `derive-entity-types`; **DA-d**
`sertor-rag eval` (run/non-regressione/authoring CLI) + skill per genesi/feedback (confine D↔N); **DA-e**
validazione path via `IndexManifest` esposto da `build_indexed_docs` (il CLI è il vehicle). Nodi:
**N1** suite/baseline in `eval/` versionato (NON `.sertor/`); **N2** report umano+JSON + evento
metrics-only; **N3** installabilità (manopole `.env` ora, skill P2 tracciate come debito di completamento).

## Phase 1 — Design
[`data-model.md`](data-model.md) (entità + servizi + factory) · [`contracts/`](contracts/) (CLI / TOML /
evento) · [`quickstart.md`](quickstart.md). `CLAUDE.md` aggiornato (riferimento al piano corrente).

## Constitution Check (POST-design)

*Re-check dopo Phase 1.*

- [x] **I** — Design confermato: `services/eval/` puro nel core, CLI thin, mock-testabile. **PASS**
- [x] **II** — Nessun nuovo boundary provider; local-first preservato. **PASS**
- [x] **III** — Zero porte nuove, zero dipendenze nuove; serializzatore a mano giustificato per schema
  piatto + fail-safe `SuiteWriteError`. **PASS**
- [x] **IV** — Errori di dominio espliciti + degrado onesto del manifest (`None` gestito). **PASS**
- [x] **V** — Funzioni pure F.I.R.S.T.; la feature realizza la misura del Principio V. **PASS**
- [x] **VI** — Writer non-distruttivo/idempotente (round-trip validato); baseline solo su flag. **PASS**
- [x] **VII** — Naming di dominio, unità piccole. **PASS**
- [x] **VIII** — `eval_dir`/`eval_tolerance` solo in `Settings`. **PASS**
- [x] **IX** — Evento `eval` metrics-only (contract `event-eval.md`). **PASS**
- [x] **X** — Suite/baseline = dato ospite in `eval/` (config override); fixture Sertor solo dogfood;
  manopole nell'installer. **PASS**
- [x] **XI** — Run via factory `build_*` (CLI = vehicle); skill esterna via sottocomandi, mai import di
  `sertor_core`. **PASS**

**Esito POST-design: 11/11 PASS, nessuna deroga. Complexity Tracking vuoto.**

## Complexity Tracking
Nessuna violazione da giustificare.
