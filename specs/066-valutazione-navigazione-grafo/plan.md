# Implementation Plan: Valutazione della navigazione del grafo (set-based) (FEAT-011)

**Branch**: `066-valutazione-navigazione-grafo` | **Date**: 2026-06-20 | **Spec**:
[`spec.md`](spec.md)

**Input**: `specs/066-valutazione-navigazione-grafo/spec.md` ·
`requirements/retrieval-qualita/valutazione-navigazione-grafo/requirements.md` (REQ-001..061, RNF-1..5) ·
`requirements/retrieval-qualita/epic.md` (FEAT-011, CS-1..5) · feature gemella su `master`:
`specs/065-ground-truth-valutazione/` (harness IR).

> **Nota di processo.** `.specify/scripts/.../setup-plan.ps1` e `.claude/skills/speckit-plan/SKILL.md`
> **assenti** nel repo → parametri per convenzione dal branch (modello di forma:
> `specs/065-ground-truth-valutazione/plan.md`); nessun hook SpecKit eseguito. Git **delegato** al
> flusso principale / `configuration-manager` (mai eseguito qui). MCP `sertor-rag` interrogato per
> l'ancoraggio al codice reale (`get_context run_evaluation`, `find_symbol build_graph_service`/`SymbolHit`,
> `search_code`); **nessun errore tool** da riportare.

## Summary

Rendere **misurabile** la potenza relazionale del code-graph: estendere l'harness eval di FEAT-001 con un
**secondo oracolo a insiemi** per i casi relazionali, **senza** toccare i casi/metriche path-based IR. Un
caso di navigazione = **relazione + simbolo target + insieme atteso di `ref`** (`[[graph_case]]` nello
stesso `eval/suite.toml`); un **run deterministico via vehicle** (`sertor-rag graph-eval run` →
`precision`/`recall`/`F1` per insiemi, report umano + `--json` con `expected`/`got`/`missing`/`extra`); un
**gate di non-regressione** sul **F1 medio** con **baseline separata** (`eval/graph_baseline.toml` +
tolleranza `SERTOR_GRAPH_EVAL_TOLERANCE`); i **seam** per la genesi assistita (skill `eval-suite-author`
estesa) **senza** che il run dipenda mai da un LLM. Approccio cardine: **riusare** la porta `CodeGraph`
(`build_graph_service`) per la navigazione e il **pattern** di `services/eval/` (suite_io/baseline_io/
regression/runner) per la misura, **estendendoli additivi non-breaking**; il nuovo oracolo è un **modulo
nuovo** parallelo a `evaluate` (NON dentro `RoutedEvalEngine`, NON dentro `evaluate`: la navigazione è
set-based, non rank-based). Tutto il resto in `services/eval/` (moduli nuovi) + gruppo CLI thin
`graph-eval` (Principio I/XI). 4 forche di design decise (research): **DA-a** F1-gate + baseline
separata; **DA-b** `related_docs` fuori MVP (schema agnostico al tipo); **DA-c** baseline≠snapshot
(re-record solo pavimento, ri-authoring per insiemi); **DA-d** stesso file `[[graph_case]]`.

## Technical Context

**Language/Version**: Python ≥ 3.11 (`tomllib` stdlib = floor del progetto).
**Primary Dependencies**: solo **stdlib** (`tomllib`-read, serializzatore TOML a mano già esistente);
**`networkx`** (extra `graph`) **solo** per la navigazione, lazy dietro `build_graph_service` (già così
oggi). **Nessuna nuova dipendenza.**
**Storage**: artefatti **versionati** `eval/suite.toml` (esteso con `[[graph_case]]`) +
`eval/graph_baseline.toml` (nuovo, separato dalla baseline IR); navigazione dal **grafo** persistito
(`<index_dir>/graph/<corpus>.json`, già prodotto da `index()`).
**Testing**: `pytest` (unit, `not cloud`, mock/Chroma locale — RNF-1); funzioni pure (metriche set-based,
`compare_graph_to_baseline`, IO suite/baseline) testabili senza rete; navigatore con `CodeGraph` mockato
(structural typing, fixture esistenti); CLI con runner mockato (stile `test_cli_search`/`test_cli_eval`).
**Target Platform**: CLI host-agnostica (qualunque progetto ospite indicizzato, Principio X).
**Project Type**: libreria + CLI (single project — core `src/sertor_core`, installer `packages/sertor`).
**Performance Goals**: suite di poche decine di graph-case in tempi interattivi/CI; costo dominato dalla
navigazione del grafo (in-memory networkx), non dall'harness.
**Constraints**: determinismo (REQ-015); additività a leve spente (costo identico, RNF-1); local-first
**zero LLM** nel run (RNF-2); confine D↔N (run nel core/CLI, genesi nella skill); privacy metrics-only
(RNF-3).
**Scale/Scope**: ~3 moduli nuovi in `services/eval/` (`graph_eval.py`, `graph_runner.py`,
`graph_regression.py` + estensioni a `models.py`/`suite_io.py` + nuovo `graph_baseline_io.py`), ~1 gruppo
CLI (`graph-eval` + 4 azioni), ~2 errori di dominio, ~2 manopole `Settings`, ~2 voci nei template `.env`,
1 factory `build_graph_eval_runner` (riusa `build_graph_service`), 1 estensione della skill (debito P2).

## Constitution Check (PRE-design)

*GATE prima di Phase 0. Gate derivati da `.specify/memory/constitution.md` v1.2.0.*

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** la misura deterministica vive nel core
  (oracolo set-based puro in `services/eval/graph_eval.py`; navigatore dipende dalla **porta** `CodeGraph`,
  non dall'adapter); il CLI è **thin** (parsing → composition → format). Nessun import di SDK/adapter nei
  servizi; esercitabile con `CodeGraph` mock (structural typing). **PASS**
- [x] **II — Boundary & local-first:** nessun nuovo boundary verso provider esterni (suite/baseline sono
  **dati**, la navigazione riusa l'adapter `networkx` esistente dietro la porta); misura in locale, zero
  rete (RNF-2). **PASS**
- [x] **III — YAGNI & unità piccole:** **nessuna nuova porta Protocol** (la navigazione riusa `CodeGraph`;
  suite/baseline = dati, single consumer); **nessuna nuova dipendenza** (serializzatore a mano riusato);
  funzioni pure piccole (metriche/compare/IO); `related_docs` rinviata (Could) per non gonfiare lo scope.
  **PASS**
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** `GraphSuiteValidationError` (nomina il caso),
  `GraphRegressionDetected`, riuso di `GraphNotFoundError` (grafo non costruito → fallimento azionabile,
  REQ-013) e `SuiteWriteError` (round-trip writer). Simbolo assente → insieme **vuoto** gestito
  esplicitamente (assenza legittima, REQ-014), mai uno zero ingannevole sul gate; baseline assente →
  `None` gestito (gate passa, REQ-033). **PASS**
- [x] **V — Testabilità & misure:** **è** la feature della misura (precision/recall/F1 set-based su
  ground-truth relazionale, Principio V reso operativo per la navigazione); funzioni pure F.I.R.S.T.;
  navigatore con grafo mock; baseline = livello accettato del progetto. **PASS**
- [x] **VI — Idempotenza & non-distruttività:** `add_graph_case`/`amend_graph_case` preservano i casi
  esistenti **e i `[[case]]` IR** (DA-d), idempotenti su `(relation, target)`, round-trip validato;
  baseline aggiornata **solo** su `--record-baseline` esplicito; `--record-baseline` **non** tocca gli
  `expected` (DA-c). **PASS**
- [x] **VII — Leggibilità:** vocabolario di dominio (navigate/who_calls/defines/precision/recall/f1/
  baseline/regression); funzioni piccole, guard clause. **PASS**
- [x] **VIII — Configurabilità centralizzata:** `graph_eval_tolerance`/`graph_eval_exact` default **solo**
  in `Settings` (env `SERTOR_GRAPH_EVAL_TOLERANCE`/`SERTOR_GRAPH_EVAL_EXACT`), mai hardcodati. **PASS**
- [x] **IX — Osservabilità:** il run emette evento `graph_eval` (cases, relations, medie, regressed,
  tolerance) via `log_event`; **metrics-only, nessun nome/path/insieme/testo libero** (RNF-3, contract
  `event-graph-eval.md`), gemello dell'evento `eval`. **PASS**
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** suite/baseline = dato dell'**ospite** in `eval/`
  (override config), niente assunzioni Sertor nel corpo; `ref` relativi alla root indicizzata. Manopole nel
  template `.env` dell'installer (REQ-061); skill estesa via installer (debito P2 tracciato). **PASS**
- [x] **XI — Consumo via vehicles:** il run accede al grafo **solo** via `build_graph_service`
  (riuso) dietro `build_graph_eval_runner` (il CLI è il vehicle); la skill esterna invoca i **sottocomandi**
  (`graph-eval validate-ref`/`add-case`), **mai** importa `sertor_core`; eccezione test invariata. **PASS**

**Esito PRE-design: 11/11 PASS, nessuna deroga.**

## Project Structure

### Documentation (this feature)
```text
specs/066-valutazione-navigazione-grafo/
├── plan.md                  # questo file
├── research.md              # Phase 0: 4 forche (DA-a..DA-d) + 5 nodi
├── data-model.md            # Phase 1: entità nuove (additive a services/eval/models.py)
├── quickstart.md            # Phase 1: percorso utente
├── contracts/
│   ├── cli-graph-eval.md    # contratto sottocomando `sertor-rag graph-eval`
│   ├── artifacts-toml.md    # schema [[graph_case]] + eval/graph_baseline.toml
│   └── event-graph-eval.md  # evento osservabilità `graph_eval`
└── tasks.md                 # Phase 2 (/speckit-tasks — NON creato qui)
```

### Source Code (repository root)
```text
src/sertor_core/
├── services/
│   └── eval/
│       ├── models.py            # ESTESO: + GraphCase, SetMetric, GraphCaseResult, GraphEvalReport,
│       │                        #         GraphBaseline, GraphMetricDelta, GraphRegressionVerdict,
│       │                        #         RefValidation; EvalSuite + graph_cases (default ())
│       ├── suite_io.py          # ESTESO: load_suite legge [[graph_case]]; writer preserva entrambe
│       │                        #         le sezioni; + add_graph_case/amend_graph_case
│       ├── graph_baseline_io.py # NUOVO: load/write eval/graph_baseline.toml (pattern baseline_io)
│       ├── graph_eval.py        # NUOVO: evaluate_graph_case/suite (set-based puro) + navigate
│       ├── graph_regression.py  # NUOVO: compare_graph_to_baseline (gate su mean_f1, puro)
│       └── graph_runner.py      # NUOVO: run_graph_evaluation + emit_graph_eval_event + validate_refs
├── domain/
│   └── errors.py                # + GraphSuiteValidationError / GraphRegressionDetected
├── config/
│   └── settings.py              # + graph_eval_tolerance, graph_eval_exact (default + env)
├── composition.py               # + build_graph_eval_runner (riusa build_graph_service)
└── cli/
    ├── __main__.py              # + gruppo `graph-eval` (run/add-case/amend-case/validate-ref)
    └── output.py                # + format_graph_eval_report/regression/ref_validation

packages/sertor/src/sertor_installer/assets/rag/
├── env.local.tmpl               # + SERTOR_GRAPH_EVAL_TOLERANCE / SERTOR_GRAPH_EVAL_EXACT (commentate)
├── env.azure.tmpl               # idem
└── skills/eval-suite-author/SKILL.md  # ESTESO (genesi [[graph_case]]) — debito di completamento P2

eval/                            # DOGFOOD (repo Sertor): + qualche [[graph_case]] di esempio
└── suite.toml                   # esteso (esempio, non spedito agli ospiti)

tests/
├── unit/                        # graph_eval (metriche), graph_regression, graph_suite_io,
│                                # graph_baseline_io, graph_runner (navigate con CodeGraph mock),
│                                # cli graph-eval, output
└── integration/                 # gate non-regressione e2e su grafo costruito (not cloud)
```

**Structure Decision**: single project. Il **core** ospita la misura (moduli `services/eval/graph_*` +
estensione additiva di `models.py`/`suite_io.py`); il **CLI** è un thin consumer; l'**installer** cabla le
manopole. La navigazione riusa `build_graph_service`. La skill estesa è separata e segue (P2 — gruppo E).

## Phase 0 — Research
Vedi [`research.md`](research.md). Forche decise: **DA-a** gate su `mean_f1` + baseline separata
`eval/graph_baseline.toml` (`SERTOR_GRAPH_EVAL_TOLERANCE`, default 0.0; recall/precision medi secondari nel
report); **DA-b** `related_docs` fuori MVP (Could), schema `expected` agnostico al tipo (stringhe) → non
preclude i documenti; **DA-c** baseline (pavimento, `--record-baseline`) ≠ snapshot (insiemi, ri-authoring
via skill/`amend-case`), mai confuse; **DA-d** `[[graph_case]]` nello stesso `eval/suite.toml` (writer
preserva entrambe le sezioni). Nodi: **N1** oracolo set-based = modulo nuovo (non `RoutedEvalEngine`, non
`evaluate`); **N2** mapping `who_calls`→`who_calls`, `defines`→`find_symbol` (entrambi `SymbolHit.ref`);
**N3** report distinto + evento metrics-only; **N4** installabilità (manopole `.env` ora, skill P2 debito);
**N5** gruppo CLI `graph-eval` separato da `eval`.

## Phase 1 — Design
[`data-model.md`](data-model.md) (entità additive + servizi + factory) · [`contracts/`](contracts/)
(CLI / TOML / evento) · [`quickstart.md`](quickstart.md). `CLAUDE.md` aggiornato (riferimento al piano
corrente, marker SPECKIT).

## Constitution Check (POST-design)

*Re-check dopo Phase 1.*

- [x] **I** — Design confermato: oracolo set-based puro nel core, navigatore sulla **porta** `CodeGraph`,
  CLI thin, mock-testabile. Nessun SDK/adapter nei servizi. **PASS**
- [x] **II** — Nessun nuovo boundary provider; navigazione riusa l'adapter esistente; local-first
  preservato. **PASS**
- [x] **III** — Zero porte nuove (riuso `CodeGraph`), zero dipendenze nuove (serializzatore a mano);
  entità additive con default neutri; `related_docs` rinviata. **PASS**
- [x] **IV** — Errori di dominio espliciti + assenze gestite (simbolo→insieme vuoto, grafo→`GraphNotFound`,
  baseline→`None`). **PASS**
- [x] **V** — Funzioni pure F.I.R.S.T.; la feature realizza la misura set-based del Principio V per la
  navigazione. **PASS**
- [x] **VI** — Writer non-distruttivo/idempotente che **preserva i `[[case]]` IR** (DA-d, round-trip
  validato); baseline solo su flag; `--record-baseline` non tocca gli `expected` (DA-c). **PASS**
- [x] **VII** — Naming di dominio, unità piccole. **PASS**
- [x] **VIII** — `graph_eval_tolerance`/`graph_eval_exact` solo in `Settings`. **PASS**
- [x] **IX** — Evento `graph_eval` metrics-only (contract `event-graph-eval.md`); `relations` a cardinalità
  chiusa, nessun nome/path/insieme. **PASS**
- [x] **X** — Suite/baseline = dato ospite in `eval/` (config override); `ref` relativi; manopole nel
  template `.env`; skill estesa via installer (debito P2 tracciato). **PASS**
- [x] **XI** — Run via `build_graph_eval_runner`→`build_graph_service` (CLI = vehicle); skill esterna via
  sottocomandi, mai import di `sertor_core`. **PASS**

**Esito POST-design: 11/11 PASS, nessuna deroga. Complexity Tracking vuoto.**

## Complexity Tracking
Nessuna violazione da giustificare.

## Tracciamento dello scope (Out-of-Scope → casa durevole)
- **`related_docs`/callees `depends_on` (via `get_context`)**: **Could** già nel backlog d'epica
  (`requirements/retrieval-qualita/epic.md` §8) e nella MoSCoW dei requisiti
  (`requirements/retrieval-qualita/valutazione-navigazione-grafo/requirements.md` §9). Lo schema `expected`
  è progettato per non precludere i documenti (DA-b). Nessun rinvio reale vive solo dentro `specs/`.
- **Comando di *refresh* assistito dello snapshot**: **Could** (idem §9). MVP = `amend-case` deterministico
  + skill che propone.
- **Estensione della skill `eval-suite-author` ai `[[graph_case]]`**: **debito di completamento** della
  capacità host-side (gruppo E/Should), da chiudere prima che la feature conti come *done* su un ospite.
