# Tasks — Valutazione della navigazione del grafo (set-based) (FEAT-011)

**Branch**: `066-valutazione-navigazione-grafo` | **Generato**: 2026-06-20
**Spec**: [`spec.md`](spec.md) · **Piano**: [`plan.md`](plan.md) · **Dati**: [`data-model.md`](data-model.md)
**Contratti**: [`contracts/cli-graph-eval.md`](contracts/cli-graph-eval.md) ·
[`contracts/artifacts-toml.md`](contracts/artifacts-toml.md) ·
[`contracts/event-graph-eval.md`](contracts/event-graph-eval.md) ·
**Quickstart**: [`quickstart.md`](quickstart.md)

> **Nota di processo.** I task marcati `[P]` sono parallelizzabili all'interno della stessa fase
> (nessuna dipendenza reciproca). Il suffisso `→ dipende da` lista i task prerequisiti per ordine di
> esecuzione. Git **mai** qui: brief di commit al fondo per il `configuration-manager`. LLM nel design
> = agente via skill (gruppo E), mai chiamata programmatica nel core (confine D↔N vincolante).
>
> **Strategia MVP/incrementale.** Le fasi seguono il grafo di dipendenze:
> - **Setup** (TASK-G01–G02): errori e Settings additivi — zero dipendenze, primi in assoluto.
> - **Fondazionale** (TASK-F01–F06): entità pure, I/O TOML, oracolo set-based, regression —
>   tutti parallelizzabili tra loro dopo il Setup. Questi moduli non toccano il CLI e sono
>   testabili in isolamento con grafo mockato.
> - **US1+US2** (TASK-A01–A07): composition factory, formatter, CLI `graph-eval` — richiede
>   Fondazionale completa; costituisce il core dell'MVP (P1 Must).
> - **US3** (TASK-B01–B04): skill `eval-suite-author` estesa (genesi assistita), cablaggio
>   installer, test statici — P2 Should, dopo MVP.
> - **Polish** (TASK-P01–P03): smoke test e2e, lint ruff, aggiornamento dogfood.
>
> La feature è **additiva a leve spente**: a capacità non invocata, `index`/`search`/`eval` IR
> restano invariati (RNF-1). L'MVP (Fasi Setup+Fondazionale+US1+US2) realizza US1 e US2
> (oracolo + gate, P1 Must) e può essere consegnato indipendentemente da US3.

---

## Fase 0 — Setup (2 task)

> Prerequisiti zero. Eseguibili in parallelo tra loro; bloccanti per tutto il resto.

### TASK-G01 — Aggiungi errori di dominio per il modulo graph-eval [P]
**File**: `src/sertor_core/domain/errors.py`
→ dipende da: nessuno
- [x] Aggiungi `GraphSuiteValidationError(SertorError)`: campi `case_index: int` e `detail: str`,
      messaggio che identifica il caso offendente (relazione/target/indice) — REQ-004/005.
      Può riusare/estendere `SuiteValidationError` se la forma del messaggio basta; l'entità
      separata è preferita per distinguere i casi di navigazione da quelli IR nel log.
- [x] Aggiungi `GraphRegressionDetected(SertorError)`: campo `verdict: GraphRegressionVerdict`
      (forward ref via `from __future__ import annotations`), messaggio che nomina la metrica
      degradata (`mean_f1`, delta, tolleranza) — REQ-032.
- [x] Verifica: entrambi i nuovi errori sono sottoclasse di `SertorError`; `domain/errors.py`
      non importa nessun SDK esterno né adapter (Principio I); i test esistenti su `errors.py`
      continuano a passare invariati (RNF-4).

### TASK-G02 — Aggiungi manopole `graph_eval_tolerance` / `graph_eval_exact` in Settings [P]
**File**: `src/sertor_core/config/settings.py`
→ dipende da: nessuno
- [x] Aggiungi campo `graph_eval_tolerance: float` con default `0.0`, letto da
      `SERTOR_GRAPH_EVAL_TOLERANCE` (pattern identico a `eval_tolerance`).
- [x] Aggiungi campo `graph_eval_exact: bool` con default `False`, letto da
      `SERTOR_GRAPH_EVAL_EXACT` (usa `os.getenv(..., "false").lower() in ("1", "true")`).
- [x] Verifica: i default sono definiti **solo** qui (Principio VIII); nessun componente fuori
      da `Settings` hardcoda un valore per queste manopole; `Settings` resta importabile senza
      dipendenze esterne.

---

## Fase 1 — Fondazionale: entità e servizi core (6 task)

> Tutti i task di questa fase sono **indipendenti tra loro** e parallelizzabili `[P]`.
> Prerequisiti comuni: TASK-G01 (errori), TASK-G02 (Settings).

### TASK-F01 — Estendi `EvalSuite` e aggiungi entità graph-eval in `models.py` [P]
**File**: `src/sertor_core/services/eval/models.py`
→ dipende da: TASK-G01
- [x] Aggiungi `GraphCase` (frozen dataclass): `relation: str`, `target: str`,
      `expected: tuple[str, ...]`. La validazione (relazione supportata, target non vuoto,
      expected ben formato) avviene nel loader (`GraphSuiteValidationError`), non nel
      costruttore. `expected` vuoto è valido (atteso «nessun chiamante» — asimmetria deliberata
      vs EvalCase; REQ-003/004/005).
- [x] Aggiungi `SetMetric` (frozen dataclass): `precision: float`, `recall: float`, `f1: float`,
      `exact: bool`, `got: tuple[str, ...]`, `expected: tuple[str, ...]`,
      `missing: tuple[str, ...]`, `extra: tuple[str, ...]`.
      Convenzioni casi-limite deterministiche (REQ-015):
        - entrambi vuoti → P=R=F1=1.0, `exact=True`;
        - `expected` vuoto & `got` non vuoto → P=0, R=1, F1=0;
        - `got` vuoto & `expected` non vuoto → P=1, R=0, F1=0.
- [x] Aggiungi `GraphCaseResult` (frozen dataclass): `relation: str`, `target: str`,
      `metric: SetMetric`.
- [x] Aggiungi `GraphEvalReport` (frozen dataclass): `cases: tuple[GraphCaseResult, ...]`,
      `mean_precision: float`, `mean_recall: float`, `mean_f1: float`,
      `by_relation: dict[str, float]`, `cases_count: int`.
- [x] Aggiungi `GraphBaseline` (frozen dataclass): `mean_f1: float`, `mean_recall: float`,
      `mean_precision: float`, `cases: int`, `recorded_at: str` (ISO-8601 UTC).
- [x] Aggiungi `GraphMetricDelta` (frozen dataclass): `name: str`, `current: float`,
      `baseline: float`, `delta: float`, `regressed: bool`.
      Il gate scatta **solo** su `mean_f1` (`regressed=True`); `mean_recall`/`mean_precision`
      hanno `regressed=False` (informativi — DA-a).
- [x] Aggiungi `GraphRegressionVerdict` (frozen dataclass): `verdict: str`
      (`"pass"` | `"regressed"` | `"no-baseline"`), `deltas: tuple[GraphMetricDelta, ...]`,
      `tolerance: float`. Metodo `exit_code() -> int`: 0 se `"pass"`/`"no-baseline"`, 1 se
      `"regressed"`.
- [x] Aggiungi `RefValidation` (frozen dataclass): `checked: tuple[str, ...]`,
      `unverifiable: tuple[str, ...]`, `graph_available: bool`.
- [x] Estendi `EvalSuite` con campo `graph_cases: tuple[GraphCase, ...] = ()` (additivo,
      default `()` → suite IR-only invariata). I metodi `to_ground_truth()`/`kinds()`/`rebased()`
      operano solo su `cases` e restano **invariati** (RNF-4).
- [x] Verifica: nessun import di SDK esterni; `domain/` non è importato dai servizi fuori
      dalla porta `CodeGraph` (Principio I); i test esistenti di `models.py` continuano a
      passare (RNF-4).

### TASK-F02 — Implementa `graph_eval.py`: oracolo set-based puro [P]
**File nuovo**: `src/sertor_core/services/eval/graph_eval.py`
→ dipende da: TASK-F01, TASK-G01
- [x] Implementa costante `_SUPPORTED_RELATIONS: frozenset[str] = frozenset({"who_calls", "defines"})`
      come unica fonte dell'insieme MVP (N2 research).
- [x] Implementa `evaluate_graph_case(navigated: frozenset[str], expected: frozenset[str]) -> SetMetric`
      come funzione **pura** (zero I/O):
        - `intersection = navigated & expected`
        - `precision = |intersection| / |navigated|` (got vuoto & expected vuoto → 1.0;
          got non vuoto & expected vuoto → 0.0; got vuoto & expected non vuoto → 1.0 P)
        - `recall = |intersection| / |expected|` (expected vuoto → 1.0)
        - `f1 = 2*P*R / (P+R)` oppure 0.0 se P+R == 0
        - `exact = navigated == expected`
        - `missing = tuple(sorted(expected - navigated))`
        - `extra = tuple(sorted(navigated - expected))`
      Applica le convenzioni di `SetMetric` per i casi-limite (REQ-015).
- [x] Implementa `navigate(graph: CodeGraph, relation: str, target: str) -> frozenset[str]`:
        - `who_calls` → `frozenset(hit.ref for hit in graph.who_calls(target))`
        - `defines` → `frozenset(hit.ref for hit in graph.find_symbol(target))`
        - Simbolo assente → lista vuota dalla porta → `frozenset()` (REQ-014, assenza legittima)
        - Relazione fuori `_SUPPORTED_RELATIONS` → `GraphSuiteValidationError` (difesa in
          profondità; la suite è già stata rifiutata dal loader, ma si difende anche qui)
        - Grafo non costruito → `GraphNotFoundError` propagato dalla porta (REQ-013)
      Solo import dalla porta `CodeGraph` (`domain/ports.py`), mai da adapter concreti
      (Principio I).
- [x] Implementa `evaluate_graph_suite(results: list[GraphCaseResult]) -> GraphEvalReport`
      come funzione **pura**:
        - `mean_precision = media([r.metric.precision for r in results])`
        - `mean_recall = media([r.metric.recall for r in results])`
        - `mean_f1 = media([r.metric.f1 for r in results])`
        - `by_relation = {rel: media(f1 di quel rel) for rel in relations}`
        - `cases_count = len(results)`
        - Suite vuota → report con tutti i valori 0.0 e `cases_count=0`.
- [x] Verifica: `evaluate_graph_case` è deterministica (REQ-015); nessun import di composition
      o adapter; mockabile con `CodeGraph` a structural typing (nessuna eredità).

### TASK-F03 — Implementa `graph_regression.py`: funzione pura `compare_graph_to_baseline` [P]
**File nuovo**: `src/sertor_core/services/eval/graph_regression.py`
→ dipende da: TASK-F01
- [x] Implementa `compare_graph_to_baseline(report: GraphEvalReport, baseline: GraphBaseline | None,
      tolerance: float) -> GraphRegressionVerdict` come funzione **pura** (zero I/O):
        - `baseline is None` → `GraphRegressionVerdict(verdict="no-baseline", deltas=(), tolerance=tolerance)`.
        - Calcola `delta = current - baseline` e `regressed = delta < -tolerance` per le tre metriche:
            - `mean_f1`: gate principale → `regressed` attivo (DA-a/REQ-032)
            - `mean_recall`: informativo → `regressed=False` sempre
            - `mean_precision`: informativo → `regressed=False` sempre
        - Costruisce `tuple[GraphMetricDelta, ...]` nell'ordine `(mean_f1, mean_recall, mean_precision)`.
        - Se almeno un `MetricDelta.regressed=True` → `verdict="regressed"`, altrimenti `"pass"`.
- [x] Verifica: funzione deterministica (stesso input → stesso output); nessun import I/O.

### TASK-F04 — Estendi `suite_io.py`: supporto `[[graph_case]]` + `add/amend_graph_case` [P]
**File**: `src/sertor_core/services/eval/suite_io.py`
→ dipende da: TASK-F01, TASK-G01
- [x] Estendi `load_suite(path: Path) -> EvalSuite` per leggere **entrambi** gli array TOML:
        - `data.get("case", [])` → lista di `EvalCase` (invariato, RNF-4)
        - `data.get("graph_case", [])` → lista di `GraphCase`:
            - campo `relation` mancante/non-stringa → `GraphSuiteValidationError(case_index=i, ...)`
            - `relation` fuori `_SUPPORTED_RELATIONS` → `GraphSuiteValidationError` (REQ-005)
            - `target` mancante/vuoto → `GraphSuiteValidationError`
            - `expected` mancante/non-lista → `GraphSuiteValidationError`
            - `expected` con elementi non-stringa → `GraphSuiteValidationError` (REQ-004)
        - `EvalSuite.graph_cases` = `()` se la chiave `graph_case` è assente (non un errore —
          suite IR-only valida).
- [x] Estendi il **serializzatore TOML a mano** `_serialize_suite` per emettere **entrambe** le sezioni
      nell'ordine stabile: prima i `[[case]]` IR (invariato), poi i `[[graph_case]]` (nuovi).
      Non deve cancellare i `[[case]]` quando si scrivono `[[graph_case]]` e viceversa (DA-d,
      Principio VI/RNF-4).
      Regole di escape per `expected`: ogni elemento è una stringa basic TOML
      (`"`→`\"`, `\`→`\\`). Array `expected` vuoto → `expected = []`.
- [x] Verifica che `write_suite` ri-legge con `tomllib` dopo ogni scrittura (round-trip —
      `SuiteWriteError` se fallisce, già esistente): il round-trip deve preservare ENTRAMBE le
      sezioni (test di non-distruttività).
- [x] Implementa `add_graph_case(path: Path, case: GraphCase) -> None`:
        - carica la suite esistente (o crea `EvalSuite()` se assente)
        - dedup su `(relation, target)`: se già presente, non aggiunge (idempotente — REQ-041)
        - appende in coda alla sezione `graph_cases`
        - chiama `write_suite`.
- [x] Implementa `amend_graph_case(path: Path, relation: str, target: str, expected: tuple[str, ...]) -> None`:
        - carica la suite; trova il caso per `(relation, target)` →
          `GraphSuiteValidationError` se non esiste
        - aggiorna `expected` del caso trovato (ri-authoring dello snapshot, DA-c)
        - chiama `write_suite`.
- [x] Solo stdlib: `tomllib`, `pathlib`; nessun import da `composition.py`.

### TASK-F05 — Implementa `graph_baseline_io.py`: load/write baseline di navigazione [P]
**File nuovo**: `src/sertor_core/services/eval/graph_baseline_io.py`
→ dipende da: TASK-F01
- [x] Implementa `load_graph_baseline(path: Path) -> GraphBaseline | None`:
        - file assente → `None` (assenza legittima, gate passa — REQ-033)
        - file malformato → `SuiteValidationError` (stile `baseline_io.py` esistente)
        - Legge con `tomllib.load` i campi `recorded_at`, `cases`, `mean_f1`,
          `mean_recall`, `mean_precision`.
- [x] Implementa `write_graph_baseline(path: Path, baseline: GraphBaseline) -> None`:
        - Serializzatore TOML a mano per lo schema piatto (contract `artifacts-toml.md`):
          `recorded_at`, `cases`, `mean_f1`, `mean_recall`, `mean_precision`.
        - Crea le cartelle intermedie (`path.parent.mkdir(parents=True, exist_ok=True)`).
        - Round-trip di validazione con `tomllib` dopo scrittura (`SuiteWriteError` se fallisce).
        - Scritto/aggiornato **solo** su `--record-baseline` esplicito (dal chiamante, non qui).
- [x] `recorded_at` generato con `datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")`.
- [x] Solo stdlib: `tomllib`, `pathlib`, `datetime`.

### TASK-F06 — Implementa `graph_runner.py`: `run_graph_evaluation` + `validate_refs` + evento [P]
**File nuovo**: `src/sertor_core/services/eval/graph_runner.py`
→ dipende da: TASK-F01, TASK-F02, TASK-F03, TASK-F04, TASK-F05, TASK-G01
- [x] Implementa `run_graph_evaluation(graph: CodeGraph, suite: EvalSuite) -> GraphEvalReport`:
        - Itera su `suite.graph_cases`; per ogni caso:
            - chiama `navigate(graph, case.relation, case.target)` →
              `GraphNotFoundError` se grafo non costruito (propagato, REQ-013)
            - chiama `evaluate_graph_case(navigated, frozenset(case.expected))`
            - costruisce `GraphCaseResult`
        - chiama `evaluate_graph_suite(results)` e ritorna `GraphEvalReport`.
        - Suite senza `graph_cases` (`graph_cases == ()`) → `GraphEvalReport` vuoto (report
          onesto, exit 0, messaggio azionabile dal CLI — non un errore del runner).
        - Determinismo garantito dall'ordine della suite e dal sorting dei `ref` (REQ-015).
- [x] Implementa `emit_graph_eval_event(report: GraphEvalReport, verdict: GraphRegressionVerdict,
      exact_gate: bool) -> None` via `log_event` (contract `event-graph-eval.md`):
        - `operation="graph_eval"`, `cases=report.cases_count`,
          `relations={rel: count for rel, count in …}` (cardinalità chiusa, non testo libero),
          `mean_precision`, `mean_recall`, `mean_f1`,
          `regressed=(verdict.verdict == "regressed")`,
          `tolerance=verdict.tolerance if verdict.verdict != "no-baseline" else None`,
          `exact_gate=exact_gate`.
        - **Mai** emettere `target`, `ref`, `missing`, `extra`, nomi di simboli, path
          o testo libero (RNF-3).
- [x] Implementa `validate_refs(graph: CodeGraph, relation: str, target: str,
      refs: tuple[str, ...]) -> RefValidation`:
        - Se grafo non costruito (`GraphNotFoundError`) → `RefValidation(checked=refs,
          unverifiable=(), graph_available=False)` (degrado onesto, non un crash).
        - Altrimenti: naviga `relation`+`target` per ottenere l'insieme dei `ref` reali;
          `unverifiable = tuple(r for r in refs if r not in real_refs)`.
        - Exit 0 sempre (è verifica, non gate — REQ-042/contract cli-graph-eval.md).
- [x] Solo import da `services/eval/` e dalla porta `CodeGraph`; nessun import di composition.

---

## Fase 2 — Fase US1+US2: run, gate, installabilità (MVP P1 Must) (7 task)

> US1 = oracolo a insiemi + gate non-regressione via `sertor-rag graph-eval`.
> US2 = US4 (installabilità host-side, gate, manopole nei template).
> Questa fase produce l'MVP consegnabile. Prerequisiti: Fase 0 e Fase 1 complete.

### TASK-A01 — Factory `build_graph_eval_runner` in `composition.py`
**File**: `src/sertor_core/composition.py`
→ dipende da: TASK-F01, TASK-F02, TASK-F03, TASK-F04, TASK-F05, TASK-F06, TASK-G02
- [x] Implementa classe privata `_GraphEvalRunner`:
        - costruttore: riceve un `CodeGraph` concreto
        - metodo `run(suite: EvalSuite) -> tuple[GraphEvalReport, GraphRegressionVerdict]`:
            - verifica `graph.exists(corpus)` → `GraphNotFoundError` se assente (REQ-013)
            - chiama `run_graph_evaluation(self._graph, suite)`
            - confronta con `compare_graph_to_baseline(report, baseline, tolerance)`
            - emette evento via `emit_graph_eval_event(report, verdict, exact_gate)`
            - ritorna `(report, verdict)`.
        - `baseline` caricata da `load_graph_baseline(settings.eval_dir / "graph_baseline.toml")`
          (può essere `None` — assenza legittima).
        - `tolerance` da `settings.graph_eval_tolerance`.
        - `exact_gate` da `settings.graph_eval_exact` o dal flag CLI (passato in costruzione).
- [x] Implementa `build_graph_eval_runner(settings: Settings) -> _GraphEvalRunner`:
        - chiama `_wire_runtime(settings)` (auto-wire osservabilità, FEAT-041 pattern)
        - costruisce il grafo via `build_graph_service(settings)` (riuso — Principio XI)
        - ritorna `_GraphEvalRunner(graph, settings)`.
- [x] Aggiorna `composition.py` per riesportare `build_graph_eval_runner` coerentemente con
      le altre factory pubbliche.
- [x] Verifica: `build_graph_eval_runner` è l'UNICO punto che conosce `NetworkxCodeGraph`
      concreto per questo percorso (Principio I/XI); i test esistenti di composition passano.

### TASK-A02 — Formatter output `graph-eval` in `cli/output.py` [P]
**File**: `src/sertor_core/cli/output.py`
→ dipende da: TASK-F01, TASK-F03
- [x] Aggiungi `format_graph_eval_report(report: GraphEvalReport, verdict: GraphRegressionVerdict,
      json_mode: bool) -> str` come funzione **pura** (zero I/O):
        - Output umano: intestazione `graph navigation eval  cases=N`,
          riga metriche (`mean_f1=… mean_recall=… mean_precision=…`),
          riga `by-relation: who_calls=…  defines=…`,
          per ogni caso: `[exact]`/`[part ]`/`[miss ]` + relation + target + P/R/F1 +
          `+extra: …`/`-missing: …` (solo se non vuoti),
          riga non-regression: `PASS`/`FAIL`/`no baseline` + delta `mean_f1` e `mean_recall`.
          Formato coerente con l'esempio in `contracts/cli-graph-eval.md`.
        - Output JSON: equivalente informativo (tutti i campi di `GraphEvalReport` +
          `verdict`, `tolerance`, `deltas`); valido JSON (SC-001/invariante CLI).
- [x] Aggiungi `format_graph_regression(verdict: GraphRegressionVerdict,
      json_mode: bool) -> str`: compatta (`PASS`/`REGRESSED` + deltas); riusabile standalone.
      Funzione pura.
- [x] Aggiungi `format_ref_validation(rv: RefValidation, json_mode: bool) -> str`:
      lista `checked`/`unverifiable`/`graph_available`. Funzione pura.
- [x] Verifica: nessuna delle funzioni ha side-effect; compatibilità informativa umano↔JSON;
      `[exact]`/`[part ]`/`[miss ]` corretti: `[exact]` se `metric.exact`, `[miss ]` se
      `metric.recall < 1.0 and metric.precision == 1.0`, `[part ]` negli altri casi.

### TASK-A03 — Gruppo CLI `graph-eval` in `cli/__main__.py`
**File**: `src/sertor_core/cli/__main__.py`
→ dipende da: TASK-A01, TASK-A02
- [x] Aggiungi gruppo di sottocomandi `graph-eval` al parser argparse con sub-azioni annidate
      (pattern identico al gruppo `eval` esistente: `add_subparsers` annidato,
      `set_defaults(handler=...)`):
        - `graph-eval run [--record-baseline] [--exact] [--corpus C] [--json] [-v] [--log-json] [--log-config F]`
        - `graph-eval add-case --relation who_calls|defines --target T --expected REF[,REF…] [--confirm] [--corpus C] [--json]`
        - `graph-eval amend-case --relation R --target T --expected REF[,REF…] [--confirm] [--corpus C] [--json]`
        - `graph-eval validate-ref --relation R --target T REF[…] [--corpus C] [--json]`
      `--relation` usa `choices=["who_calls", "defines"]` (exit 2 su valore fuori insieme — REQ-005).
- [x] Implementa `_cmd_graph_eval_run(args, settings)` seguendo il contratto `cli-graph-eval.md`:
        1. `_resolve_settings` + `_check_backend` + `enable_observability` (pattern esistente).
        2. Carica `load_suite(settings.eval_dir / "suite.toml")`:
           suite assente → `SuiteNotFoundError` (exit 1);
           `graph_cases == ()` → messaggio azionabile («crea casi con `graph-eval add-case`») +
           report vuoto onesto, exit 0 (non un gate fasullo su zero casi).
        3. Costruisce `build_graph_eval_runner(settings)` con `exact_gate` da `args.exact or
           settings.graph_eval_exact`.
        4. Chiama `runner.run(suite)` → `(report, verdict)`.
           `--exact` attivo e un caso `exact=False` → `GraphRegressionDetected` (exit 1).
           `verdict.verdict == "regressed"` → `GraphRegressionDetected` (exit 1, REQ-032).
        5. Con `--record-baseline`: scrive `eval/graph_baseline.toml` via
           `write_graph_baseline(settings.eval_dir / "graph_baseline.toml", baseline)` dove
           `baseline = GraphBaseline(mean_f1=report.mean_f1, ...)`. **Non** tocca mai
           gli `expected` dei casi (DA-c).
        6. Stampa con `format_graph_eval_report(report, verdict, args.json)`.
        7. Exit 0 se nessun gate scatta.
- [x] Implementa `_cmd_graph_eval_add(args, settings)`:
        - Analizza `--expected "r1,r2,r3"` → `tuple[str, ...]` (split su `,` e strip).
        - Costruisce `build_graph_eval_runner(settings)` per validare i `ref` via
          `validate_refs(graph, args.relation, args.target, refs)`.
        - `ref` non verificabili: **warning** espliciti che li nominano; richiede `--confirm`
          o prompt TTY (`isatty()`) prima di scrivere (REQ-042). Senza conferma → exit 1
          azionabile (non scrive mai parzialmente — Principio VI).
        - Grafo non disponibile → warning «non posso verificare i ref», scrive solo con
          `--confirm` (degrado onesto).
        - Chiama `add_graph_case(settings.eval_dir / "suite.toml", GraphCase(...))` (REQ-041).
        - Successo: messaggio `«caso aggiunto a eval/suite.toml»`, exit 0.
- [x] Implementa `_cmd_graph_eval_amend(args, settings)`:
        - Stessa validazione write-time di `_cmd_graph_eval_add`.
        - Chiama `amend_graph_case(path, relation, target, expected)`.
        - Caso inesistente → `GraphSuiteValidationError` (exit 1, nomina relation+target).
- [x] Implementa `_cmd_graph_eval_validate_ref(args, settings)`:
        - Costruisce `build_graph_eval_runner(settings)`.
        - Chiama `validate_refs(graph, args.relation, args.target, tuple(args.refs))`.
        - Stampa `format_ref_validation(rv, args.json)`. Exit 0 sempre (REQ-042/contract).
- [x] Aggiorna il blocco `except SertorError` in `main()`: `GraphRegressionDetected` e
      `GraphSuiteValidationError` sono già `SertorError` e vengono catturati automaticamente;
      verifica il messaggio azionabile nel formatter di errore.
- [x] Verifica: il CLI è thin (nessuna logica di navigazione/metrica); exit code coerenti
      (0/1/2); nessun import diretto di adapter (Principio XI).

### TASK-A04 — Test unitari: graph_eval, graph_regression (funzioni pure) [P]
**File nuovi**: `tests/unit/test_graph_eval.py`, `tests/unit/test_graph_regression.py`
→ dipende da: TASK-F02, TASK-F03
- [x] `test_graph_eval.py` (funzioni pure, zero rete):
        - `evaluate_graph_case({A,B}, {A,B})` → P=1.0, R=1.0, F1=1.0, `exact=True`, `missing=()`, `extra=()`.
        - `evaluate_graph_case({A}, {A,B})` → P=1.0, R=0.5, F1=0.67, `exact=False`, `missing=(B,)`.
        - `evaluate_graph_case({A,C}, {A,B})` → P=0.5, R=0.5, F1=0.5, `extra=(C,)`, `missing=(B,)`.
        - `evaluate_graph_case(frozenset(), frozenset())` → P=1.0, R=1.0, F1=1.0, `exact=True`.
        - `evaluate_graph_case(frozenset(), {A})` → P=1.0, R=0.0, F1=0.0.
        - `evaluate_graph_case({A}, frozenset())` → P=0.0, R=1.0, F1=0.0.
        - `evaluate_graph_suite([])` → `GraphEvalReport` con tutti i valori 0.0 e `cases_count=0`.
        - `navigate` con `CodeGraph` mock che ritorna lista vuota → `frozenset()` (REQ-014).
        - `navigate` con relazione non supportata → `GraphSuiteValidationError`.
        - Determinismo: `evaluate_graph_case` stesso input → stesso output su chiamate multiple (REQ-015).
- [x] `test_graph_regression.py` (funzioni pure, zero I/O):
        - `compare_graph_to_baseline(report, None, 0.0)` → `"no-baseline"`, exit 0.
        - `mean_f1` corrente < baseline - tolerance → `"regressed"`, exit 1.
        - `mean_f1` entro tolleranza (es. corrente=0.78, baseline=0.80, tolerance=0.05) → `"pass"`, exit 0.
        - `mean_recall` degradato (ma `mean_f1` ok) → `"pass"` (recall non è gate, DA-a).
        - Funzione pura: stesso input → stesso output sempre.

### TASK-A05 — Test unitari: graph_suite_io, graph_baseline_io, graph_runner [P]
**File nuovi**: `tests/unit/test_graph_suite_io.py`, `tests/unit/test_graph_baseline_io.py`,
               `tests/unit/test_graph_runner.py`
→ dipende da: TASK-F04, TASK-F05, TASK-F06
- [x] `test_graph_suite_io.py`:
        - Round-trip `write_suite`→`load_suite` per una suite con ENTRAMBI `[[case]]` e
          `[[graph_case]]`: verifica che i `[[case]]` IR siano invariati dopo aver scritto
          `graph_cases` (non-distruttività — RNF-4).
        - `load_suite` su file con solo `[[case]]` (nessun `[[graph_case]]`) → `graph_cases == ()`.
        - `load_suite` su file con solo `[[graph_case]]` → `cases == ()`.
        - `GraphSuiteValidationError` su `[[graph_case]]` senza `relation` (nomina indice).
        - `GraphSuiteValidationError` su `relation` fuori MVP (REQ-005).
        - `expected = []` valido (caso «nessun chiamante» — asimmetria vs EvalCase).
        - `add_graph_case` idempotente su `(relation, target)` duplicato.
        - `amend_graph_case` aggiorna `expected` correttamente.
        - `amend_graph_case` su caso inesistente → `GraphSuiteValidationError`.
        - `SuiteWriteError` se il round-trip fallisce (simula con mock `tomllib`).
- [x] `test_graph_baseline_io.py`:
        - Round-trip `write_graph_baseline`→`load_graph_baseline` identico.
        - File assente → `None`.
        - `recorded_at` presente e formato ISO-8601 non vuoto.
- [x] `test_graph_runner.py`:
        - `run_graph_evaluation` con `CodeGraph` mock (structural typing, no eredità) che
          ritorna `[SymbolHit(...)]`: report corretto con metriche calcolate.
        - Suite con `graph_cases == ()` → `GraphEvalReport` vuoto, exit 0 (non un errore).
        - `GraphNotFoundError` propagato se il mock `navigate` lo solleva.
        - `emit_graph_eval_event` non emette `target`/`ref`/`missing`/`extra` (verifica con
          `caplog` o mock `log_event` che i campi RNF-3 sono assenti — REQ-050).
        - `validate_refs` con grafo non disponibile → `RefValidation(graph_available=False)`.
        - `validate_refs` con ref non verificabile → compare in `unverifiable`.
        - Tutti i test: `not cloud`, no rete.

### TASK-A06 — Test unitari: formatter output graph-eval e CLI graph-eval (con core mockato) [P]
**File nuovi**: `tests/unit/test_output_graph_eval.py`, `tests/unit/test_cli_graph_eval.py`
→ dipende da: TASK-A02, TASK-A03
- [x] `test_output_graph_eval.py` (funzioni pure):
        - `format_graph_eval_report` con report completo: output umano contiene `mean_f1`,
          `[exact]`/`[part ]`/`[miss ]`, `+extra`/`-missing` corretti.
        - Output `--json` valido JSON con stessi campi informativi.
        - `format_graph_regression` con `"regressed"` → stringa contiene `REGRESSED` + delta.
        - `format_ref_validation` con `unverifiable` non vuoto → warning che li nomina.
- [x] `test_cli_graph_eval.py` (stile `test_cli_eval.py`, argparse + core mockato):
        - `graph-eval run` con suite e grafo mock → exit 0, metriche in stdout.
        - `graph-eval run` senza suite (file assente) → exit 1, messaggio azionabile.
        - `graph-eval run` con `graph_cases == ()` → exit 0, report vuoto onesto (non exit 1).
        - `graph-eval run` con grafo non costruito (mock `GraphNotFoundError`) → exit 1 azionabile.
        - `graph-eval run --record-baseline` → scrive `graph_baseline.toml`, exit 0.
        - `graph-eval run` con regressione artificiale oltre tolleranza → exit 1.
        - `graph-eval run` con regressione entro tolleranza → exit 0.
        - `graph-eval run --exact` con caso non-exact → exit 1.
        - `graph-eval add-case` con ref nell'insieme navigato → exit 0.
        - `graph-eval add-case` con ref non verificabile senza `--confirm` → exit 1, warning.
        - `graph-eval add-case` con ref non verificabile + `--confirm` → exit 0.
        - `graph-eval amend-case` su caso esistente → exit 0.
        - `graph-eval amend-case` su caso inesistente → exit 1 (`GraphSuiteValidationError`).
        - `graph-eval validate-ref` → exit 0 sempre; JSON valido con `--json`.
        - `graph-eval` senza sub-azione → exit 2 (usage).
        - Gate exit-code (SC-003): regressione artificiale → exit 1 riproducibile.

### TASK-A07 — Template `.env` installer: manopole `graph_eval_tolerance` / `graph_eval_exact`
**File**: `packages/sertor/src/sertor_installer/assets/rag/env.local.tmpl`
**File**: `packages/sertor/src/sertor_installer/assets/rag/env.azure.tmpl`
→ dipende da: TASK-G02
- [x] Aggiungi in entrambi i template (sezione commentata, accanto alle manopole `SERTOR_EVAL_*`
      già presenti — REQ-061):
      ```
      # Optional: absolute F1 tolerance for the graph-navigation non-regression gate (0.0 = zero tolerance).
      # SERTOR_GRAPH_EVAL_TOLERANCE=0.0
      # Optional: enable exact-set gate (case fails if got != expected). Default false.
      # SERTOR_GRAPH_EVAL_EXACT=false
      ```
- [x] Verifica: le righe sono commentate di default (additività RNF-1); nessun segreto nei
      template (RNF-5).
- [x] Controlla che `test_packaging.py` (integration) non fallisca per le nuove righe; aggiorna
      eventuali riferimenti nel test se necessario.

---

## Fase 3 — Fase US3: genesi assistita (P2 Should) (3 task)

> US3 = skill `eval-suite-author` estesa per la genesi dei `[[graph_case]]`.
> Debito di completamento della capacità host-side (Principio X, REQ-060).
> Prerequisiti: Fase 2 completa (in particolare TASK-A03 per i sottocomandi vehicle).

### TASK-B01 — Estendi la skill `eval-suite-author` per la genesi di `[[graph_case]]` [P]
**File**: `.claude/skills/eval-suite-author/SKILL.md`
**File distribuito**: `packages/sertor/src/sertor_installer/assets/rag/skills/eval-suite-author/SKILL.md`
→ dipende da: TASK-A03 (i sottocomandi `graph-eval validate-ref`/`add-case` devono esistere)
- [x] Estendi la skill esistente `eval-suite-author` aggiungendo la sezione
      **«Genesi di casi di navigazione del grafo (`[[graph_case]]`)»**:
        - l'agente **esegue la navigazione corrente** del grafo per la relazione+simbolo richiesti
          invocando `sertor-rag graph-eval validate-ref --relation R --target T --json`
          (vehicle deterministico — Principio XI): il risultato è l'insieme candidato.
        - Presenta l'insieme candidato all'utente come **proposta da approvare** (snapshot
          deterministico, non giudizio autonomo — REQ-040).
        - **Solo dopo approvazione esplicita** dell'utente invoca
          `sertor-rag graph-eval add-case --relation R --target T --expected "r1,r2" --confirm`
          (REQ-041). Mai scrittura implicita o automatica.
        - Se `unverifiable` non vuoto: **nomina** i ref non verificabili, offre di escluderli
          o di procedere con `--confirm` (REQ-042).
        - Se grafo non costruito (`graph_available=False`): skill **fallisce azionabile**
          («indicizza prima il progetto con `sertor-rag index .`»).
- [x] Il corpo della skill deve esplicitare il confine D↔N: il run deterministico
      (`graph-eval run`) non dipende dalla skill; la skill è la superficie di giudizio,
      il run è deterministico nel core (RNF-2/SC-005).
- [x] Corpo **host-agnostico** (Principio X): nessun riferimento a path Sertor-specifici
      (es. `src/sertor_core/`); nessun nome-modello hardcodato (regola parità dual-target).
- [x] Verifica che la skill citi `sertor-rag graph-eval validate-ref` e
      `sertor-rag graph-eval add-case` (vehicle), **mai** importi `sertor_core`.

### TASK-B02 — Skill cablata nel piano `build_rag_plan` (installabilità P2)
**File**: `packages/sertor/src/sertor_installer/` (piano RAG)
→ dipende da: TASK-B01
- [x] Individua il plan-builder `build_rag_plan` (o equivalente) nell'installer del pacchetto
      `sertor` e verifica che la skill `eval-suite-author` (già esistente dal 065) includa le
      nuove istruzioni per `[[graph_case]]` nell'asset installato.
- [x] Se la skill ha un file unico (`SKILL.md`) che è già nel piano, verifica che il suo
      aggiornamento (TASK-B01) si propaghi automaticamente via il meccanismo di
      `iter_asset_dir` (non serve una voce nuova — la skill è già cablata da FEAT-001 065).
- [x] Aggiorna `sertor_owned_paths` se il path della skill è cambiato o se ne è stata
      aggiunta una sottocartella.
- [x] Verifica (dry-run o test): `sertor install rag` include la skill aggiornata nel piano.

### TASK-B03 — Test unitari: invarianti skill genesi graph-eval [P]
**File nuovo**: `tests/unit/test_skill_graph_eval_author.py`
→ dipende da: TASK-B01
- [x] Verifica statica/strutturale del corpo della skill (nessun LLM, solo file check):
        - `.claude/skills/eval-suite-author/SKILL.md` esiste e contiene il richiamo esplicito a
          `sertor-rag graph-eval validate-ref` e `sertor-rag graph-eval add-case`.
        - Nessun import diretto di `sertor_core` menzionato nel corpo.
        - Nessun path Sertor-specifico assoluto (guard anti-leak ispirata a
          `test_assets_copilot_parity.py`; cerca `src/sertor_core/` come stringa nel body).
        - Nessun nome-modello Claude hardcodato (Opus/Haiku/Sonnet).
        - La keyword `approve` o `approvazione` compare (confine D↔N — non persistenza automatica).

---

## Fase 4 — Polish e cross-cutting (3 task)

### TASK-P01 — Smoke test end-to-end non-regressione grafo (integration, not cloud)
**File nuovo**: `tests/integration/test_graph_eval_gate.py`
→ dipende da: TASK-A01, TASK-A03, TASK-F04 (suite.toml con graph_cases)
- [x] Test `@integration` `not cloud` con grafo locale (Chroma + NetworkxCodeGraph temporanei
      su corpus minimale di 2-3 file Python sintetici indicizzati inline):
        - Esegue `sertor-rag graph-eval run` come subprocess → exit 0, metriche in stdout.
        - Esegue `sertor-rag graph-eval run --record-baseline` → scrive `graph_baseline.toml`.
        - Degrada artificialmente la suite (aggiunge `expected` impossibili) → `graph-eval run`
          → exit 1 (`GraphRegressionDetected`).
        - Ri-esegue con tolleranza alta (`SERTOR_GRAPH_EVAL_TOLERANCE=1.0`) → exit 0.
        - Due run identici su grafo e suite identici → metriche identiche (SC-001/REQ-015).
- [x] Test `@integration` `not cloud` per `add-case` e `validate-ref` su grafo costruito:
        - `add-case` con ref navigabili → exit 0, caso appare in `suite.toml`.
        - `add-case` con ref inesistente senza `--confirm` → exit 1, warning.
        - `validate-ref` → exit 0 sempre, JSON valido.
        - Gate baseline assente → `graph-eval run` exit 0 (REQ-033).
- [x] Tutti i test superano con `uv run pytest -m "not cloud" tests/integration/test_graph_eval_gate.py`.

### TASK-P02 — Lint ruff e verifica additività a leve spente
→ dipende da: tutti i task precedenti
- [x] Esegui `uv run ruff check .` e correggi eventuali errori nei file nuovi/modificati
      (regole E,F,I,UP,B; line-length 100). Zero errori come pre-condizione al merge.
- [x] Verifica **additività** (RNF-1/SC-002): con leve di default (nessun `SERTOR_GRAPH_EVAL_*`
      impostato, senza invocare `graph-eval`), esegui `sertor-rag index .` e
      `sertor-rag search "test"` e `sertor-rag eval run` (IR): comportamento e costo identici
      a prima (nessun warning, nessun overhead).
- [x] Esegui `uv run pytest -m "not cloud" tests/unit/` e verifica che TUTTA la suite unit
      passi (inclusi i test IR esistenti e i nuovi graph-eval).
- [x] Verifica che `EvalSuite` con solo `cases` (senza `graph_cases`) continui a funzionare
      invariata (default `()` — RNF-4): i test IR esistenti costruiscono `EvalSuite` senza il
      campo e devono continuare a passare.

### TASK-P03 — Aggiorna dogfood: aggiungi esempi `[[graph_case]]` in `eval/suite.toml`
**File**: `eval/suite.toml`
→ dipende da: TASK-F04, TASK-A03
- [x] Aggiungi in coda al file `eval/suite.toml` (dogfood Sertor) un blocco di 3-5 esempi
      reali di `[[graph_case]]` per le relazioni MVP:
        - almeno un caso `who_calls` su un simbolo con chiamanti noti nel corpus (es.
          `build_graph_service`, `build_facade`)
        - almeno un caso `defines` su un simbolo presente nel grafo del corpus
        - almeno un caso con `expected = []` (simbolo senza chiamanti noti — edge case)
      Aggiorna il commento in testa al file per includere `[[graph_case]]` nella descrizione.
- [x] Verifica round-trip: `tomllib.load(open("eval/suite.toml", "rb"))` non solleva; i
      `[[case]]` IR esistenti sono invariati (non-distruttività — RNF-4).
- [x] I `ref` usati sono verificabili sul corpus Sertor indicizzato (usa `sertor-rag
      graph-eval validate-ref` per confermare prima di committare).

---

## Grafo delle dipendenze (sintesi)

```
TASK-G01 (errori domain)  ──┐
TASK-G02 (settings)        ─┤
                             ├→ TASK-F01 [P] ─────────────────────┐
                             │               → TASK-F02 [P] ──────┤
                             │               → TASK-F03 [P] ──────┤
                             │               → TASK-F04 [P] ──────┤
                             │               → TASK-F05 [P] ──────┤
                             └───────────────→ TASK-F06 [P] ──────┤
                                                                   ↓
                                                      TASK-A01 (composition factory)
                                                                   │
                             TASK-A02 [P] ─────────────────────────┤
                                                                   ↓
                                                      TASK-A03 (CLI graph-eval)
                                                                   │
                  TASK-A04 [P] ← (TASK-F02, TASK-F03)             │
                  TASK-A05 [P] ← (TASK-F04, TASK-F05, TASK-F06)   │
                  TASK-A06 [P] ← (TASK-A02, TASK-A03) ────────────┤
                  TASK-A07    ← (TASK-G02)                         │
                                                                   ↓
                                               TASK-B01 [P] (skill genesi)
                                                   → TASK-B02 (cablaggio installer)
                                                       → TASK-B03 [P]
                                                                   │
                                                                   ↓
                                        TASK-P01 (smoke test e2e)
                                        TASK-P02 (lint + additività)
                                        TASK-P03 (dogfood examples)
```

---

## Criteri di test indipendenti per User Story

| US | Criterio di test indipendente | Task principali |
|---|---|---|
| **US1** (oracolo a insiemi + gate) | Due run identici → metriche identiche; regressione artificiale → exit 1; entro tolleranza → exit 0; suite assente → exit 1; suite senza `graph_cases` → exit 0 report vuoto; grafo non costruito → exit 1 azionabile. | TASK-A04, TASK-A05, TASK-A06, TASK-P01 |
| **US2** (gate non-regressione separato) | Baseline assente → gate passa (exit 0); registrata baseline → degradazione → exit 1; `--record-baseline` scrive `graph_baseline.toml` senza toccare `expected`; sezione distinta da metriche IR. | TASK-A05, TASK-A06, TASK-P01 |
| **US3** (genesi assistita) | Skill presente e corpo contiene `graph-eval validate-ref` + `graph-eval add-case`; no import `sertor_core`; body host-agnostico; confine D↔N esplicito; nessuna persistenza automatica. | TASK-B03 |
| **US4** (installabile host-side) | Template `.env` contiene le 2 manopole commentate; skill cablata nel piano install (dry-run); a leve spente `index`/`search`/`eval` IR invariati; suite e baseline in `eval/` del progetto ospite. | TASK-A07, TASK-B02, TASK-P02 |

---

## Parallelizzazione consigliata (MVP P1)

**Sprint 1 (parallelo — nessun prerequisito):**
- Sviluppatore A: TASK-G01 + TASK-G02
- (in attesa degli errori/settings per sbloccare tutto il resto)

**Sprint 2 (parallelo — dopo Sprint 1):**
- Sviluppatore A: TASK-F01 → TASK-F02 + TASK-F03 + TASK-F04 + TASK-F05
- Sviluppatore B: TASK-F06 (dipende da TASK-F01/F02/F03/F04/F05, ma in gran parte
  parallelizzabile se si accordano le interfacce prima)

**Sprint 3 (dopo Sprint 2 — MVP core):**
- TASK-A01 (composition factory) — bloccante per CLI
- TASK-A02 [P] (formatter) — parallelizzabile con TASK-A01

**Sprint 4 (dopo Sprint 3 — MVP completo):**
- TASK-A03 (CLI) → TASK-A04 [P] + TASK-A05 [P] + TASK-A06 [P] + TASK-A07 [P]

**Sprint 5 (P2/Should — dopo merge MVP):**
- TASK-B01 → TASK-B02 → TASK-B03 [P]

**Sprint finale:**
- TASK-P01 + TASK-P02 + TASK-P03

---

## Brief di commit (per il `configuration-manager`)

```
docs(tasks): genera tasks.md per FEAT-011 epica retrieval-qualita

Fase SpecKit "tasks" completata per specs/066-valutazione-navigazione-grafo.
22 task in 5 fasi (Setup 2 / Fondazionale 6 / US1+US2 7 / US3 3 / Polish 3).
Nessun hook SpecKit eseguito (script assenti nel repo); nessuna operazione git.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

**File da includere nel commit:**
- `specs/066-valutazione-navigazione-grafo/tasks.md` (questo file, nuovo)
