# Tasks — Qualità del retrieval fuso code+doc (FEAT-003)

**Branch**: `069-qualita-fusione-code-doc` | **Generato**: 2026-06-21
**Spec**: [`spec.md`](spec.md) · **Piano**: [`plan.md`](plan.md) · **Dati**: [`data-model.md`](data-model.md)
**Contratti**: [`contracts/cli-eval-fused.md`](contracts/cli-eval-fused.md) ·
[`contracts/artifacts-toml.md`](contracts/artifacts-toml.md) ·
[`contracts/event-fused-eval.md`](contracts/event-fused-eval.md)

> **Nota di processo.** I task marcati `[P]` sono parallelizzabili all'interno della stessa fase
> (nessuna dipendenza reciproca). Il suffisso `→ dipende da` lista i task prerequisiti per ordine di
> esecuzione. Git **mai** qui: brief di commit al fondo per il `configuration-manager`. Il confine
> D↔N è vincolante: il run di misura è **deterministico** (core/CLI, tutto il Must è meccanico);
> il giudizio su quale query/intento/leva adottare è **skill** (US3/US4/US5, P2 Should).
>
> **Strategia MVP/incrementale.** Le fasi seguono il grafo di dipendenze:
> - **Setup** (TASK-G01–G02): manopola `eval_fusion_k` e errore `FusedSuiteValidationError` —
>   zero dipendenze, bloccanti per tutto il resto.
> - **Fondazionale** (TASK-F01–F06): entità pure, field `intent`, I/O TOML (preserve-both),
>   metrica fusion coverage, adattatori-superficie, regression per-superficie, baseline_io
>   esteso — tutti parallelizzabili tra loro dopo il Setup. Zero dipendenza dal CLI.
> - **US1** (TASK-A01–A06): factory `build_fused_eval_runner`, formatter, CLI `eval run --fused` +
>   `eval add-case --intent` + evento — richiede Fondazionale completa; costituisce il core dell'MVP
>   (P1 Must: misura per-superficie + fusion coverage + gate).
> - **US2** (TASK-B01–B03): baseline per-superficie + gate non-regressione per superficie/fusione;
>   template `.env` installer — P1 Must, parallelizzabile con parte di US1.
> - **US3** (TASK-C01–C02): dogfood NL intent-typed + registrazione baseline reali — P1 Must
>   (empirico, dopo MVP meccanico). Natura **mista**: authoring casi = giudizio, registrazione
>   baseline = meccanico via CLI.
> - **US4** (TASK-D01–D02): confronto leve guidato-da-misura (valutazione ≥1 leva opt-in;
>   adozione SOLO con lift misurato) — P2 Should, dopo baseline.
> - **US5** (TASK-E01–E02): genesi assistita (skill `eval-suite-author` estesa) — P2 Should,
>   debito di completamento.
> - **Polish** (TASK-P01–P03): smoke test e2e, lint ruff, verifica additività.
>
> La feature è **additiva a leve spente**: senza invocare `eval run --fused`, `index`/`search`/
> `eval run` (IR) restano invariati (RNF-1). L'MVP (Fasi Setup+Fondazionale+US1+US2+US3) realizza
> US1 e US2 (misura + gate + baseline, P1 Must) e può essere consegnato indipendentemente
> da US4/US5/Polish.

---

## Fase 0 — Setup (2 task)

> Prerequisiti zero. Eseguibili in parallelo tra loro; bloccanti per tutto il resto.

### TASK-G01 — Aggiungi manopola `eval_fusion_k` in Settings [P]
**File**: `src/sertor_core/config/settings.py`
→ dipende da: nessuno
- [x] Aggiungi campo `eval_fusion_k: int` con default `5`, letto da
      `SERTOR_EVAL_FUSION_K` (pattern identico a `eval_tolerance` e `default_k`; es.
      `int(os.getenv("SERTOR_EVAL_FUSION_K", "5"))`).
- [x] Il default deve essere definito **solo** qui (Principio VIII); nessun componente fuori
      da `Settings` hardcoda `5` come top-k per la fusion coverage.
- [x] `eval_tolerance` esiste già e viene **riusato** (non aggiungere un `eval_fusion_tolerance`
      separato — la tolleranza è unica, come da `data-model.md` §10). Verificare che il campo
      esista già in `settings.py` prima di toccare (non duplicare).
- [x] Verifica: `Settings` resta importabile senza dipendenze esterne; i test esistenti di
      `settings.py` continuano a passare invariati (RNF-5).

### TASK-G02 — Aggiungi errore di dominio `FusedSuiteValidationError` [P]
**File**: `src/sertor_core/domain/errors.py`
→ dipende da: nessuno
- [x] Aggiungi `FusedSuiteValidationError(SuiteValidationError)` (o `(SertorError)` se la
      gerarchia `SuiteValidationError` non è adatta): campo `case_query: str` e `detail: str`,
      messaggio che nomina il caso offendente con l'`intent` invalido (Principio IV, REQ-004).
      Alternativa: verificare se `SuiteValidationError` esistente è già sufficiente per nominare
      il campo `intent`; usare quello se basta (YAGNI — non creare una sottoclasse inutile).
- [x] Il messaggio deve contenere il valore di `intent` ricevuto E l'insieme atteso
      `{code,doc,both}`, così l'utente sa esattamente cosa correggere.
- [x] Verifica: l'errore è sottoclasse di `SertorError`; `domain/errors.py` non importa
      nessun SDK esterno né adapter (Principio I); i test esistenti continuano a passare (RNF-5).

---

## Fase 1 — Fondazionale: entità e servizi core (6 task)

> Tutti i task di questa fase sono **indipendenti tra loro** e parallelizzabili `[P]`.
> Prerequisiti comuni: TASK-G01 (Settings), TASK-G02 (errori).

### TASK-F01 — Estendi `EvalCase` e `EvalSuite` con `intent` e helper puri in `models.py` [P]
**File**: `src/sertor_core/services/eval/models.py`
→ dipende da: TASK-G02
- [x] Aggiungi campo `intent: str | None = None` a `EvalCase` (frozen dataclass, additivo):
      `intent ∈ {"code", "doc", "both"}` o `None` (default retrocompatibile — RNF-5/Principio VI).
      Il campo `intent` è **distinto da `kind`**: coesistono sullo stesso caso (es. `kind="nl"`,
      `intent="both"`). Non rinominare, non unire.
- [x] Aggiungi metodi helper **puri** su `EvalSuite` (additivi, non toccano le proiezioni IR):
      - `cases_for_intent(self, intent: str) -> tuple[EvalCase, ...]`: filtra per `intent`.
      - `fusion_cases(self) -> tuple[EvalCase, ...]`: == `cases_for_intent("both")`.
      Verificare che `to_ground_truth()`/`kinds()`/`rebased()` restino **invariati** e che
      `rebased()` propaghi `intent` nel nuovo `EvalCase` ribasato (additivo).
- [x] Aggiungi le entità di report per la fusion coverage (frozen dataclasses, pure, zero I/O):
      - `FusionCaseResult`: `query: str`, `expected: tuple[str, ...]`, `has_doc: bool`,
        `has_code: bool`, `covered: bool` (= `has_doc and has_code`, REQ-020),
        `hit_at_k: bool` (per rendere visibile REQ-022: hit@k ma non covered).
      - `FusionReport`: `cases: tuple[FusionCaseResult, ...]`, `coverage: float`
        (`covered_count / cases_count`, 0.0 se `cases_count == 0` — report vuoto onesto),
        `cases_count: int`, `hit_but_not_covered: int` (la lacuna esplicita, REQ-022).
- [x] Aggiungi entità di report per-superficie e fused (frozen dataclasses, pure, zero I/O):
      - `SurfaceEvalReport`: `surface: str` (`"search_code"` | `"search_docs"` |
        `"search_combined"`), `report: EvalReport` (riuso invariato).
      - `FusedEvalReport`: `surfaces: tuple[SurfaceEvalReport, ...]`, `fusion: FusionReport`,
        `provider: str`.
- [x] Aggiungi entità baseline per-superficie e verdetto di non-regressione fused:
      - `SurfaceBaseline`: `surface: str`, `hit_rate: dict[int, float]`, `mrr: float`.
      - `FusedBaseline`: `surfaces: tuple[SurfaceBaseline, ...]`, `fusion_coverage: float`,
        `queries: int`, `provider: str`, `recorded_at: str` (ISO-8601 UTC).
      - `FusedRegressionVerdict`: `deltas: tuple[MetricDelta, ...]`, `tolerance: float`,
        `verdict: str` (`"pass"` | `"regressed"` | `"no-baseline"`).
        Metodo `exit_code() -> int`: 0 se `"pass"`/`"no-baseline"`, 1 se `"regressed"`.
        Riusare `MetricDelta` esistente (additivo, non creare `FusedMetricDelta` separato).
- [x] Verifica: nessun import di SDK esterni o adapter; tutte le nuove entità sono `frozen=True`;
      i test esistenti di `models.py` (inclusi quelli per `GraphCase`/`EvalCase` IR) continuano a
      passare invariati (RNF-5).

### TASK-F02 — Implementa `fusion.py`: metrica fusion coverage pura + `INTENT_SURFACE` [P]
**File nuovo**: `src/sertor_core/services/eval/fusion.py`
→ dipende da: TASK-F01, TASK-G01
- [x] Aggiungi costante di dominio (Principio VII):
      `INTENT_SURFACE: dict[str, str] = {"code": "search_code", "doc": "search_docs", "both": "search_combined"}`
      Unica fonte della mappatura intento→superficie; usata da `fused_runner.py` e dalla CLI.
- [x] Implementa `fusion_coverage(cases: tuple[EvalCase, ...], search_fn: Callable[[str, int], list[RetrievalResult]], k: int) -> FusionReport`
      come funzione **pura** (accetta una callable di ricerca, zero import di adapter):
      ```
      per ogni caso `both`:
        top_k = search_fn(case.query, k)                  # già rank-ordinati
        relevant = [r for r in top_k if r.path in set(case.expected)]
        has_doc  = any(r.doc_type == DocType.DOC  for r in relevant)
        has_code = any(r.doc_type == DocType.CODE for r in relevant)
        covered  = has_doc and has_code                    # REQ-020
        hit_at_k = any(r.path in set(case.expected) for r in top_k)
      coverage = covered_count / total_both_cases          # 0.0 se total == 0
      hit_but_not_covered = sum(1 for c in results if c.hit_at_k and not c.covered)
      ```
      - Il tipo del risultato (`doc_type`) si legge da `RetrievalResult.doc_type` a **runtime**
        (mai doppia etichettatura nel set, `data-model.md` §11).
      - `DocType` importato da `domain/entities.py` (non da adapter).
      - `total_both_cases == 0` → `FusionReport(cases=(), coverage=0.0, cases_count=0,
        hit_but_not_covered=0)` (report vuoto onesto, non un errore — exit 0, messaggio dalla CLI).
- [x] Verifica: funzione pura deterministica (stesso input → stesso output, REQ-041); mockabile
      con `search_fn=lambda q,k: [...]`; nessun import di composition/adapter.

### TASK-F03 — Implementa adattatori-superficie `_SurfaceEngine` in `fused_runner.py` [P]
**File nuovo**: `src/sertor_core/services/eval/fused_runner.py`
→ dipende da: TASK-F01, TASK-F02, TASK-G01
- [x] Implementa classe privata `_SurfaceEngine` (implementa `QueryableEngine` per structural
      typing — NESSUNA eredità, solo i due attributi/metodi del Protocol):
      ```python
      class _SurfaceEngine:
          def __init__(self, facade: RetrievalFacade, surface: str, provider: str): ...
          @property
          def provider(self) -> str: ...
          def query(self, query: str, k: int | None = None) -> list[RetrievalResult]:
              return getattr(self._facade, self._surface)(query, k)
      ```
      `surface ∈ {"search_code", "search_docs", "search_combined"}`. L'attributo `self._surface`
      corrisponde al nome del metodo sul `RetrievalFacade` (`data-model.md` §8).
- [x] Implementa `run_fused_evaluation(facade: RetrievalFacade, suite: EvalSuite, ks: tuple[int, ...], fusion_k: int) -> FusedEvalReport`
      come funzione (non pura — accede al facade — ma deterministica):
      - Per ogni superficie (`"search_code"`, `"search_docs"`, `"search_combined"`): costruisce un
        `_SurfaceEngine`, seleziona i casi della suite con `intent` corrispondente via
        `INTENT_SURFACE`, converte in `GroundTruth` via `to_ground_truth()` ribasato sui soli casi
        della superficie, chiama `evaluate(engine, ground_truth, ks)` → `EvalReport`; produce
        `SurfaceEvalReport`.
      - Calcola fusion coverage via `fusion_coverage(suite.fusion_cases(), facade.search_combined, fusion_k)`
        (facade.search_combined espone i `doc_type` che `evaluate` filtra via proiezione).
      - Ritorna `FusedEvalReport(surfaces=(...), fusion=fusion_report, provider=facade.provider)`.
      - Suite senza casi `intent` → `FusedEvalReport` con `surfaces` vuote e `fusion` con
        `cases_count=0` (report vuoto onesto — il messaggio azionabile viene dalla CLI).
- [x] Implementa `emit_fused_eval_event(report: FusedEvalReport, verdict: FusedRegressionVerdict) -> None`
      via `log_event` (contract `event-fused-eval.md`):
      - `operation="fused_eval"`, `provider=report.provider`,
        `cases={"code": n_code, "doc": n_doc, "both": n_both}`,
        `surface_mrr={"search_code": …, "search_docs": …, "search_combined": …}`,
        `surface_hit3={"search_code": …, "search_docs": …, "search_combined": …}`,
        `fusion_coverage=report.fusion.coverage`,
        `hit_but_not_covered=report.fusion.hit_but_not_covered`,
        `regressed=(verdict.verdict == "regressed")`,
        `tolerance=(verdict.tolerance if verdict.verdict != "no-baseline" else None)`.
      - **Mai** emettere query, path, `expected`, nomi di simboli, testo libero (RNF-3,
        Principio IX, contract `event-fused-eval.md`).
- [x] Solo import da `services/eval/` e da `RetrievalFacade` (facade = vehicle, Principio XI);
      nessun import di `composition.py` o adapter concreti.

### TASK-F04 — Estendi `regression.py`: `compare_fused_to_baseline` puro [P]
**File**: `src/sertor_core/services/eval/regression.py`
→ dipende da: TASK-F01
- [x] Implementa `compare_fused_to_baseline(report: FusedEvalReport, baseline: FusedBaseline | None, tolerance: float) -> FusedRegressionVerdict`
      come funzione **pura** (zero I/O):
      - `baseline is None` → `FusedRegressionVerdict(deltas=(), tolerance=tolerance, verdict="no-baseline")`.
      - Per ogni superficie in `report.surfaces`: confronta con il corrispondente `SurfaceBaseline`
        in `baseline.surfaces` (match per `surface`); calcola `MetricDelta` per MRR e per
        `hit_rate[k]` principali (es. @3 come rappresentativo); `regressed = delta < -tolerance`.
      - Aggiungi `MetricDelta` anche per `fusion_coverage` (`name="fusion_coverage"`,
        `current=report.fusion.coverage`, `baseline=baseline.fusion_coverage`).
      - Se **qualsiasi** delta ha `regressed=True` → `verdict="regressed"`, altrimenti `"pass"`.
        Questo include sia le superfici sia la fusion coverage (R-3, REQ-040).
      - Riusa `MetricDelta` esistente (non introdurre nuove dataclass se evitabile — YAGNI).
- [x] Verifica: funzione deterministica (stesso input → stesso output); nessun import I/O;
      i test esistenti di `regression.py` (IR) continuano a passare invariati (RNF-5).

### TASK-F05 — Estendi `suite_io.py`: supporto campo `intent` su `[[case]]` (preserve-both) [P]
**File**: `src/sertor_core/services/eval/suite_io.py`
→ dipende da: TASK-F01, TASK-G02
- [x] Estendi `_parse_case(d: dict) -> EvalCase` per leggere il campo opzionale `intent`:
      - `intent` assente → `None` (retrocompatibile — RNF-5).
      - `intent` presente ma non in `{"code", "doc", "both"}` → solleva `FusedSuiteValidationError`
        (o `SuiteValidationError` riusato, vedi TASK-G02) che nomina la `query` del caso e il
        valore invalido (Principio IV, REQ-004).
      - Stringa vuota → errore (equivale a campo invalido).
- [x] Estendi il **serializzatore TOML a mano** `_serialize_suite` per emettere il campo `intent`
      quando non `None`, nell'ordine stabile: `query`, `expected`, `kind` (se presente), `intent`
      (se presente). Non deve cancellare i `[[graph_case]]` (FEAT-011, DA-d — preserve-both
      invariato: riusa il pattern già in place, non riscrivere il serializzatore).
- [x] Estendi `add_case(path: Path, case: EvalCase) -> None` per accettare `case.intent`:
      - Dedup per `query` (idempotente, REQ-002/042).
      - Se un caso con la stessa `query` esiste già e l'`intent` è diverso → errore azionabile
        (non sovrascrivere silenziosamente — Principio IV/XII).
- [x] Estendi `amend_case(path: Path, query: str, ...) -> None` per aggiornare `intent`:
      aggiunge un parametro opzionale `intent: str | None = _UNSET` (sentinella) così che
      `amend_case` senza `intent` non tocchi il campo esistente (idempotenza).
- [x] Verifica che `write_suite` + `load_suite` facciano round-trip preservando **entrambe** le
      sezioni `[[case]]` (con e senza `intent`) e `[[graph_case]]` (`SuiteWriteError` se fallisce).
- [x] Solo stdlib: `tomllib`, `pathlib`; nessun import da `composition.py`.

### TASK-F06 — Estendi `baseline_io.py`: sezione `[fused_baseline]` (preserve-both) [P]
**File**: `src/sertor_core/services/eval/baseline_io.py`
→ dipende da: TASK-F01
- [x] Implementa `load_fused_baseline(path: Path) -> FusedBaseline | None`:
      - File assente → `None` (assenza legittima, gate passa con `"no-baseline"` — contract
        `artifacts-toml.md`).
      - File presente ma senza sezione `[fused_baseline]` → `None` (il file può contenere solo
        `[baseline]` IR — non è un errore; additività).
      - File malformato → `SuiteValidationError` (stile `baseline_io.py` esistente).
      - Legge con `tomllib.load` la sezione `[fused_baseline]` per
        `fusion_coverage`, `queries`, `provider`, `recorded_at` e `[[fused_baseline.surface]]`
        (schema contract `artifacts-toml.md` §2).
- [x] Implementa `write_fused_baseline(path: Path, baseline: FusedBaseline) -> None`:
      - Serializzatore TOML a mano per la sezione `[fused_baseline]` + `[[fused_baseline.surface]]`
        (schema esatto in `contracts/artifacts-toml.md` §2).
      - **Preserve-both**: non deve toccare la sezione `[baseline]` IR esistente. Approccio:
        leggi il file esistente, sostituisci/aggiungi solo la sezione `[fused_baseline]`,
        riscrivi il file (o appendi in fondo se `[fused_baseline]` è assente). Verifica round-trip.
      - Crea le cartelle intermedie (`path.parent.mkdir(parents=True, exist_ok=True)`).
      - Round-trip di validazione con `tomllib` dopo scrittura (`BaselineWriteError` o
        `SuiteWriteError` se fallisce — il file deve tornare parsabile).
      - `recorded_at` generato con `datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")`.
      - Scritto **solo** su `--record-baseline` esplicito (controllo nel CLI, non qui).
- [x] Solo stdlib: `tomllib`, `pathlib`, `datetime`; nessun import di composition/adapter.

---

## Fase 2 — US1: run fuso, formatter, CLI `--fused` / `--intent` (MVP P1 Must) (6 task)

> US1 = misura per-superficie + fusion coverage + CLI `eval run --fused` + `eval add-case --intent`.
> Prerequisiti: Fase 0 e Fase 1 complete. TASK-A02 e TASK-A04/A05 parallelizzabili con TASK-A01.

### TASK-A01 — Factory `build_fused_eval_runner` in `composition.py`
**File**: `src/sertor_core/composition.py`
→ dipende da: TASK-F01, TASK-F02, TASK-F03, TASK-F04, TASK-F05, TASK-F06, TASK-G01, TASK-G02
- [x] Implementa classe privata `_FusedEvalRunner`:
      - Costruttore: riceve `settings: Settings`.
      - Metodo `run_fused(suite: EvalSuite) -> tuple[FusedEvalReport, FusedRegressionVerdict]`:
        1. Costruisce il facade via `build_facade(settings)` (vehicle, Principio XI).
        2. Chiama `run_fused_evaluation(facade, suite, ks, settings.eval_fusion_k)`.
        3. Carica `FusedBaseline` via `load_fused_baseline(settings.eval_dir / "baseline.toml")`.
        4. Confronta con `compare_fused_to_baseline(report, baseline, settings.eval_tolerance)`.
        5. Emette evento via `emit_fused_eval_event(report, verdict)`.
        6. Ritorna `(report, verdict)`.
- [x] Implementa `build_fused_eval_runner(settings: Settings | None = None) -> _FusedEvalRunner`:
      - `settings = settings or Settings()`.
      - Chiama `_wire_runtime(settings)` (auto-wire osservabilità, pattern FEAT-041 — obbligatorio,
        Principio XI / composition.py invariante).
      - Ritorna `_FusedEvalRunner(settings)`.
- [x] Riesporta `build_fused_eval_runner` da `__init__.py` coerentemente con le altre factory
      pubbliche (`build_eval_runner`, `build_graph_eval_runner`, ecc.).
- [x] Verifica: `build_fused_eval_runner` è l'UNICO punto di composizione per questo percorso
      (Principio I/XI); i test esistenti di `composition.py` continuano a passare (RNF-5).

### TASK-A02 — Formatter output `eval --fused` in `cli/output.py` [P]
**File**: `src/sertor_core/cli/output.py`
→ dipende da: TASK-F01, TASK-F04
- [x] Aggiungi `format_fused_eval_report(report: FusedEvalReport, verdict: FusedRegressionVerdict, json_mode: bool) -> str`
      come funzione **pura** (zero I/O, zero side-effect):
      - Output umano (schema da `contracts/cli-eval-fused.md` §Output umano):
        ```
        fused eval  cases: code=N docs=N fusion=N  provider=<provider>

        per-surface (hit-rate@k / MRR):
          search_code      @1=… @3=… @5=…  MRR=…
          search_docs      @1=… @3=… @5=…  MRR=…
          search_combined  @1=… @3=… @5=…  MRR=…

        fusion coverage: <float>  (<covered>/<total> covered;  <N> hit@k but NOT covered ← one type drowns the other)
          [covered] <query>   doc+code
          [GAP    ] <query>   <tipo mancante>
          …

        non-regression: PASS|REGRESSED|no baseline (tolerance=<float>)
          <delta MRR per superficie> + fusion_coverage Δ=…
        ```
      - Riga `[covered]`/`[GAP    ]` solo per i casi `both` con dettaglio del tipo mancante
        (`doc only (missing CODE)` o `code only (missing DOC)`).
      - Output JSON: equivalente informativo (tutti i campi di `FusedEvalReport` + `verdict`,
        `tolerance`, `deltas`); valido JSON; stessa struttura usata per `--json`.
- [x] Aggiungi `format_fused_regression(verdict: FusedRegressionVerdict, json_mode: bool) -> str`:
      compatta (`PASS`/`REGRESSED`/`no baseline` + delta per superficie + fusion_coverage).
      Funzione pura riusabile in standalone.
- [x] Verifica: nessuna delle funzioni ha side-effect; equivalenza informativa umano↔JSON;
      formato `[covered]`/`[GAP    ]` con spaziatura fissa per leggibilità; funzioni pure testabili
      senza dipendenze (Principio I/V).

### TASK-A03 — Estendi CLI `eval run --fused` e `eval add-case --intent` in `cli/__main__.py`
**File**: `src/sertor_core/cli/__main__.py`
→ dipende da: TASK-A01, TASK-A02
- [x] Estendi il sottocomando `eval run` con il flag `--fused` (booleano, default `False`):
      - Senza `--fused` → comportamento odierno invariato (additività, SC-009, RNF-1).
      - Con `--fused`:
        1. `_resolve_settings` + `_check_backend` + `enable_observability` (pattern esistente).
        2. Carica `load_suite(settings.eval_dir / "suite.toml")`:
           suite assente → `SuiteNotFoundError` (exit 1).
           `FusedSuiteValidationError` (intent invalido) → exit 1, messaggio che nomina il caso.
        3. Suite senza casi con `intent` → messaggio azionabile:
           «Nessun caso NL intent-typed trovato. Aggiungi casi con `eval add-case --intent code|doc|both`
           o usa la skill `eval-suite-author`.» + report vuoto onesto, exit 0 (non 1 — non è un
           gate su zero casi).
        4. Costruisce via `build_fused_eval_runner(settings)` (Principio XI).
        5. Chiama `runner.run_fused(suite)` → `(report, verdict)`.
        6. Con `--record-baseline`: scrive `eval/baseline.toml` via
           `write_fused_baseline(settings.eval_dir / "baseline.toml", fused_baseline_from(report))`.
           **Non** tocca la sezione `[baseline]` IR (preserve-both).
        7. `verdict.verdict == "regressed"` → solleva `RegressionDetected` (riuso errore esistente
           o crea `FusedRegressionDetected`, a seconda di ciò che `main()` già gestisce) → exit 1.
        8. Stampa con `format_fused_eval_report(report, verdict, args.json)`.
        9. Exit 0 se nessun gate scatta (incluso `no-baseline`).
- [x] Estendi il sottocomando `eval add-case` con il flag `--intent`:
      ```
      eval add-case --query Q --expected P[,P…]
                   [--kind K] [--intent code|doc|both] [--confirm] [--corpus C] [--json]
      ```
      - `--intent` usa `choices=["code", "doc", "both"]` (exit 2 su valore fuori insieme — argparse).
      - Validazione write-time del path atteso: comportamento invariato (065).
      - Chiama `add_case(settings.eval_dir / "suite.toml", EvalCase(..., intent=args.intent))`.
      - **Preserva** `[[graph_case]]` esistenti (via `write_suite` già invariante, TASK-F05).
- [x] Estendi il sottocomando `eval amend-case` con il flag `--intent` (ri-tipizzazione):
      - `--intent` opzionale; se assente, non modifica l'`intent` del caso esistente.
      - Chiama `amend_case(path, query, ..., intent=args.intent)`.
- [x] Verifica: CLI thin (nessuna logica di metrica nel CLI, Principio I); exit code coerenti
      (0=success/no-baseline, 1=errore/regressione, 2=usage); nessun import diretto di adapter.
      Il gruppo `graph-eval` e il comportamento `eval run` senza `--fused` sono **invariati** (RNF-5).

### TASK-A04 — Test unitari: fusion.py + fused_runner.py (funzioni pure + facade mock) [P]
**File nuovi**: `tests/unit/test_fusion.py`, `tests/unit/test_fused_runner.py`
→ dipende da: TASK-F02, TASK-F03
- [x] `test_fusion.py` (funzioni pure, zero rete, zero adapter reali):
      - `fusion_coverage([caso_both], search_fn=mock_ritorna_doc_e_code, k=5)`:
        → `covered=True`, `coverage=1.0`, `hit_but_not_covered=0`.
      - `fusion_coverage([caso_both], search_fn=mock_ritorna_solo_doc, k=5)`:
        → `covered=False`, `coverage=0.0`, `hit_but_not_covered=1` (hit@k=True, covered=False — REQ-022).
      - `fusion_coverage([caso_both], search_fn=mock_ritorna_solo_code, k=5)`:
        → `covered=False`, `coverage=0.0`, `hit_at_k=True, covered=False`.
      - `fusion_coverage([], search_fn=mock_qualsiasi, k=5)`:
        → `FusionReport(cases=(), coverage=0.0, cases_count=0, hit_but_not_covered=0)`.
      - Caso `hit@k=False, covered=False` (nessun risultato pertinente):
        → `hit_but_not_covered` non viene incrementato (solo hit@k=True & covered=False conta).
      - Determinismo: stessa `search_fn` mock → stesso `FusionReport` su chiamate multiple (REQ-041).
      - `INTENT_SURFACE` mappa correttamente `{"code": "search_code", "doc": "search_docs", "both": "search_combined"}`.
- [x] `test_fused_runner.py` (facade mock a structural typing — nessuna eredità):
      - `run_fused_evaluation(facade_mock, suite_con_casi_intent, ks=(1,3,5), fusion_k=5)`:
        → `FusedEvalReport` con 3 `SurfaceEvalReport` e `FusionReport` coerente.
      - Suite senza casi `intent` → `FusedEvalReport` con `surfaces=()` e `fusion.cases_count=0`.
      - `emit_fused_eval_event` NON emette query/path/expected/nomi (verifica con `caplog` o mock
        di `log_event` che le chiavi RNF-3 sono assenti — Principio IX).
      - Tutti i test: `@pytest.mark.not_cloud` o nessun marker (non richiedono rete).

### TASK-A05 — Test unitari: suite_io intent + baseline_io fused (round-trip) [P]
**File nuovi**: `tests/unit/test_suite_io_intent.py`, `tests/unit/test_baseline_io_fused.py`
→ dipende da: TASK-F05, TASK-F06
- [x] `test_suite_io_intent.py`:
      - Round-trip `write_suite`→`load_suite` per una suite con `[[case]]` con `intent` + senza
        `intent` + `[[graph_case]]`: verifica che tutte le sezioni siano preservate (non-distruttività
        — preserve-both, RNF-5).
      - `load_suite` su file con casi senza `intent` → `EvalCase.intent is None` (retrocompatibile).
      - `load_suite` su caso con `intent="invalid"` → `FusedSuiteValidationError` (o `SuiteValidationError`)
        che nomina la query del caso (Principio IV).
      - `load_suite` su caso con `intent=""` → errore (stringa vuota non valida).
      - `add_case` con `intent="both"` → idempotente su `query` duplicata.
      - `add_case` con la stessa `query` e `intent` diverso → errore azionabile (non sovrascrittura
        silenziosa).
      - `amend_case` aggiorna `intent` correttamente.
      - `amend_case` senza `intent` → non tocca l'`intent` esistente (sentinella `_UNSET`).
      - `SuiteWriteError` se round-trip fallisce (mock `tomllib` che solleva).
- [x] `test_baseline_io_fused.py`:
      - Round-trip `write_fused_baseline`→`load_fused_baseline` identico (tutte le superfici +
        `fusion_coverage` + `recorded_at`).
      - File assente → `None`.
      - File con solo `[baseline]` IR (senza `[fused_baseline]`) → `None` (non un errore).
      - `write_fused_baseline` non modifica `[baseline]` IR esistente (preserve-both).
      - `recorded_at` presente e formato ISO-8601 UTC non vuoto.
      - `BaselineWriteError`/`SuiteWriteError` se round-trip fallisce.

### TASK-A06 — Test unitari: formatter output + CLI `eval --fused` (core mockato) [P]
**File nuovi**: `tests/unit/test_output_fused_eval.py`, `tests/unit/test_cli_fused_eval.py`
→ dipende da: TASK-A02, TASK-A03
- [x] `test_output_fused_eval.py` (funzioni pure, zero I/O):
      - `format_fused_eval_report` con report completo: output umano contiene `fusion coverage`,
        `[covered]`/`[GAP    ]`, MRR per-superficie, riga non-regression `PASS`/`REGRESSED`.
      - Output `--json` valido JSON con stessi campi informativi (equivalenza).
      - `format_fused_regression` con `"regressed"` → stringa contiene `REGRESSED` + delta per
        superficie + `fusion_coverage`.
      - Report con `cases_count=0` → output vuoto onesto (non crash, non zero ingannevole).
- [x] `test_cli_fused_eval.py` (stile `test_cli_eval.py`, argparse + `_FusedEvalRunner` mockato):
      - `eval run --fused` con suite+facade mock → exit 0, metriche in stdout.
      - `eval run --fused` senza suite (file assente) → exit 1, messaggio azionabile.
      - `eval run --fused` con suite senza casi `intent` → exit 0, messaggio azionabile (non exit 1).
      - `eval run --fused` con `intent` invalido nella suite → exit 1 (`FusedSuiteValidationError`).
      - `eval run --fused --record-baseline` → scrive sezione `[fused_baseline]`, exit 0; la
        sezione `[baseline]` IR non viene toccata.
      - `eval run --fused` con regressione artificiale (mock baseline con metriche più alte) → exit 1.
      - `eval run --fused` con regressione entro tolleranza → exit 0.
      - `eval run --fused` con baseline assente → exit 0 (`no-baseline`).
      - `eval run` SENZA `--fused` → comportamento odierno invariato (nessun `FusedEvalRunner`
        invocato — additività, SC-009).
      - `eval add-case --intent code` → exit 0, caso con `intent` appare in `suite.toml`.
      - `eval add-case --intent invalid_value` → exit 2 (argparse choices).
      - `eval amend-case --intent both` su caso esistente → exit 0, `intent` aggiornato.
      - `eval amend-case` senza `--intent` → `intent` del caso invariato.
      - Gate exit-code: regressione artificiale → exit 1 riproducibile (SC-007).
      - Tutti i test: `not cloud`, no rete.

---

## Fase 3 — US2: baseline per-superficie + template installer (P1 Must) (3 task)

> US2 = baseline distinte per-superficie registrate + gate non-regressione + manopole installer.
> TASK-B01/B02 sono parallelizzabili con TASK-A04/A05/A06 (dipendono solo dalla Fase 1).
> TASK-B03 dipende da TASK-G01 (manopola `eval_fusion_k`).

### TASK-B01 — Verifica non-regressione della suite esistente (IR + graph-eval) [P]
**File**: nessun file nuovo — verifica di regressione sul corpus esistente
→ dipende da: TASK-F01, TASK-F05 (modifica a `models.py` e `suite_io.py`)
- [x] Esegui `uv run pytest -m "not cloud" tests/unit/` dopo aver implementato TASK-F01 e TASK-F05:
      verifica che TUTTA la suite unit esistente passi invariata (inclusi i test IR di `models.py`,
      `suite_io.py`, `baseline_io.py`, `regression.py`, `cli_eval.py` e graph-eval).
- [x] In particolare verifica che `EvalSuite` con soli `cases` (senza campo `intent`) costruita
      nei test esistenti continui a funzionare con `intent=None` di default (Principio VI, RNF-5).
- [x] Verifica che `load_suite` su `eval/suite.toml` esistente (con soli `[[case]]` senza `intent`
      e `[[graph_case]]`) non sollevi errori e produca `EvalSuite` valida con `intent=None` su tutti
      i casi (retrocompatibilità assoluta).
- [x] Documenta eventuali test che richiedono aggiornamento dei fixture per il nuovo campo `intent`;
      aggiornali senza modificare la semantica (solo aggiunta del default `intent=None`).

### TASK-B02 — Test unitari: `compare_fused_to_baseline` (regression fused) [P]
**File nuovo**: `tests/unit/test_regression_fused.py`
→ dipende da: TASK-F04
- [x] `test_regression_fused.py` (funzione pura, zero I/O, zero rete):
      - `compare_fused_to_baseline(report, None, 0.0)` → `"no-baseline"`, exit 0 (baseline assente
        = gate passa, contract `artifacts-toml.md`).
      - MRR di una superficie corrente < baseline - tolerance → `"regressed"`, exit 1.
      - Fusion coverage corrente < baseline - tolerance → `"regressed"`, exit 1 (R-3, REQ-040).
      - MRR di una superficie degradato MA entro tolleranza (es. corrente=0.78, baseline=0.80,
        tolerance=0.05) → `"pass"`, exit 0.
      - Tutte le superfici e fusion coverage entro tolleranza → `"pass"`, exit 0.
      - Leva che migliora MRR ma abbassa fusion_coverage oltre tolleranza → `"regressed"` (R-3).
      - Funzione pura: stesso input → stesso output sempre (deterministico, REQ-041).
      - Riuso di `MetricDelta` esistente: i deltas sono calcolati correttamente per MRR e
        `fusion_coverage` separatamente.

### TASK-B03 — Template `.env` installer: manopola `SERTOR_EVAL_FUSION_K` [P]
**File**: `packages/sertor/src/sertor_installer/assets/rag/env.local.tmpl`
**File**: `packages/sertor/src/sertor_installer/assets/rag/env.azure.tmpl`
→ dipende da: TASK-G01
- [x] Aggiungi in entrambi i template (sezione commentata, accanto alle manopole
      `SERTOR_EVAL_TOLERANCE` e `SERTOR_GRAPH_EVAL_*` già presenti — Principio X, REQ-042,
      corollario installabile):
      ```
      # Optional: top-k used to evaluate fusion coverage on "both" intent cases (default 5).
      # SERTOR_EVAL_FUSION_K=5
      ```
- [x] Verifica: la riga è commentata di default (additività, RNF-1); nessun segreto nei template.
- [x] Controlla che `test_packaging.py` (integration) non fallisca per la nuova riga; aggiorna
      eventuali riferimenti nel test se necessario.

---

## Fase 4 — US3: dogfood NL intent-typed + baseline reali (P1 Must, empirico) (2 task)

> US3 = curazione del set NL intent-typed nel dogfood Sertor + registrazione delle baseline reali.
> Natura mista: l'authoring dei casi è **GIUDIZIO** (utente/agente), la registrazione è **meccanica**
> via CLI. Prerequisiti: Fase 2 completa (CLI `eval add-case --intent` disponibile).
> ATTENZIONE: questi task richiedono un indice dogfood attivo (corpus `sertor` indicizzato).
>
> **STATO (2026-06-21): DIFFERITI.** L'infrastruttura meccanica (Setup+Fondazionale+US1+US2+P01+P02)
> è completa e verde; C01 (giudizio + corpus reale) e C02 (richiede indice dogfood attivo) sono
> lasciati al flusso principale dopo il merge dell'MVP meccanico.

### TASK-C01 — Curazione set NL intent-typed in `eval/suite.toml` (GIUDIZIO)
**File**: `eval/suite.toml`
→ dipende da: TASK-A03 (CLI `eval add-case --intent` disponibile)
- [ ] [GIUDIZIO] Aggiungi in `eval/suite.toml` almeno **22-30 casi NL intent-typed** distribuiti
      tra le tre superfici:
      - ≥8 casi `intent="code"` (query architetturali/NL su sorgente: «dove è definito X», «dove
        è implementata la porta Y», ecc.).
      - ≥8 casi `intent="doc"` (query sul perché/come: «perché il motore ibrido usa RRF»,
        «come funziona il composite retrieval», ecc.).
      - ≥6 casi `intent="both"` (query cross-artefatto, la categoria-firma della mission:
        «requisiti di FEAT-003 e dove è implementata la fusion coverage»,
        «specifica del campo intent e il codice che la serializza», ecc.).
      - Ogni caso con `kind="nl"` (distinto da `kind="symbol"` dei casi IR esistenti).
      - Ogni `expected` deve contenere path verificabili (reali nell'indice dogfood); per i casi
        `both`, `expected` deve contenere **sia** path doc (`requirements/`/`specs/`/`wiki/`) **sia**
        path code (`src/`), così che la fusion coverage sia calcolabile.
- [ ] Per ogni caso, verificare il path atteso con `sertor-rag eval validate-path` (o il flag
      `--confirm` durante `add-case`) prima di persistere.
- [ ] Verifica round-trip: `eval/suite.toml` rimane parsabile con `tomllib`; i `[[case]]` IR
      esistenti e i `[[graph_case]]` sono invariati (non-distruttività).

### TASK-C02 — Registrazione baseline reali sul dogfood (meccanico via CLI)
**File**: `eval/baseline.toml`
→ dipende da: TASK-C01, TASK-A01 (factory), TASK-A03 (CLI `--fused --record-baseline`)
- [ ] Con corpus dogfood `sertor` indicizzato e attivo, esegui:
      `uv run sertor-rag eval run --fused --record-baseline`
      Verifica: exit 0; sezione `[fused_baseline]` scritta in `eval/baseline.toml`; sezione
      `[baseline]` IR e `[graph_baseline]` invariate (preserve-both).
- [ ] Registra e documenta le metriche ottenute (metriche di riferimento del dogfood):
      - MRR e hit-rate@3 per `search_code`, `search_docs`, `search_combined`.
      - `fusion_coverage` sui casi `both`.
      - N. di casi per intento.
      - Se la fusion coverage iniziale è < 0.5: segnalarlo esplicitamente come finding (è la lacuna
        che la feature intende rendere visibile e migliorare — REQ-021/022).
- [ ] Verifica additività: esegui `uv run sertor-rag eval run` (senza `--fused`) → comportamento e
      output identici a prima (i casi IR esistenti non sono toccati, SC-009, RNF-1).

---

## Fase 5 — US4: confronto leve guidato-da-misura (P2 Should, empirico) (2 task)

> US4 = valutazione ≥1 leva opt-in; adozione SOLO con lift misurato ≥+0.05; nessun LLM nel run.
> Natura: tutto GIUDIZIO + misura (empirico). Prerequisiti: Fase 4 completa (baseline registrate).
> ATTENZIONE: questi task dipendono dai numeri reali della baseline (DA-a, ricerca §5). La leva da
> valutare è scelta dall'utente in base all'ordine raccomandato (metadata→contextual→query-transform).
> La query-transform/HyDE NON deve introdurre un LLM nel run deterministico (RNF-3) — se la leva
> richiede LLM a query-time, si documenta il pattern ma NON si integra nel run.
>
> **STATO (2026-06-21): DIFFERITI.** Empirici, dipendono dalle baseline reali (C02); al flusso
> principale dopo le baseline.

### TASK-D01 — Valutazione di ≥1 leva opt-in sul set NL (GIUDIZIO + misura)
→ dipende da: TASK-C02 (baseline registrate)
- [ ] [GIUDIZIO] Seleziona la prima leva da valutare seguendo l'ordine raccomandato (DA-a,
      `research.md` §5):
      1. **Filtro metadata esteso** (priorità 1: basso costo, deterministico, zero LLM extra).
      2. **Contextual retrieval** (priorità 2: tocca l'indicizzazione, non il run).
      3. **Query transformation** (priorità 3: solo se materializzabile offline; MAI LLM nel run).
- [ ] Abilita la leva opt-in in modalità sperimentale (manopola ad hoc o seam nel
      `fused_runner.py`/`facade`); esegui `eval run --fused` → ottieni il report con la leva attiva.
      Il run deve restare deterministico (RNF-3): nessun LLM invocato oltre l'embedder.
- [ ] Confronta i risultati con la baseline per-superficie e di fusion coverage:
      - Documenta il delta per-superficie (MRR, hit@3) e della fusion coverage.
      - Se delta ≥ +0.05 su almeno una superficie rilevante: leva candidata all'adozione (REQ-014).
      - Se delta < +0.05: leva non adottata; documentare il finding (non nascondere l'assenza di
        guadagno — Principio XII, REQ-031).
- [ ] La leva adottata resta **spenta di default** (`Settings` con default invariato); il cambio
      di default richiede decisione esplicita (REQ-031).

### TASK-D02 — Registrazione finding leva + aggiornamento baseline se adottata (meccanico)
→ dipende da: TASK-D01
- [ ] Aggiorna `eval/baseline.toml` (sezione `[fused_baseline]`) con i nuovi numeri SOLO se la
      leva viene adottata (lift misurato ≥ +0.05):
      `uv run sertor-rag eval run --fused --record-baseline`
- [ ] Documenta il finding nel wiki (`wiki/log/<data>.md` + pagina di concetto se la leva ha
      identità propria — rituale di step §1/§2): la leva e il suo lift (o assenza di lift);
      se la leva è FEAT-005/006/007, cita la feature dedicata come «il come».
- [ ] Verifica che `eval run --fused` senza la leva (leva spenta di default) produca i numeri
      pre-leva (additività, SC-009/RNF-1): la leva non altera il comportamento di default.

---

## Fase 6 — US5: genesi assistita del set NL (P2 Should, debito completamento) (2 task)

> US5 = skill `eval-suite-author` estesa per la proposta di candidati NL intent-typed.
> Debito di completamento della capacità host-side (Principio X, REQ-043, spec §US5).
> Prerequisiti: Fase 2 completa (CLI `eval add-case --intent` disponibile).
> Nature: GIUDIZIO (skill), nessuna logica LLM nel core/CLI.
>
> **STATO (2026-06-21): DIFFERITI.** E01 = scrittura del corpo della skill (giudizio, flusso
> principale); E02 = test della skill, dipende da E01. Debito di completamento P2.

### TASK-E01 — Estendi la skill `eval-suite-author` per la genesi di casi NL intent-typed [P]
**File**: `.claude/skills/eval-suite-author/SKILL.md`
**File distribuito**: `packages/sertor/src/sertor_installer/assets/rag/skills/eval-suite-author/SKILL.md`
→ dipende da: TASK-A03 (sottocomandi `eval add-case --intent` e `eval validate-path`)
- [ ] Estendi la skill esistente `eval-suite-author` aggiungendo la sezione
      **«Genesi di casi NL intent-typed (`[[case]]` con `intent`)»**:
      - L'agente esegue retrieval sul corpus via MCP (`search_code`/`search_docs`/`search_combined`)
        per scoprire contenuti candidati, poi **propone** coppie `(query NL, expected, intent)`:
        - Casi `intent="code"`: query che richiedono sorgente (dove/come è implementato X).
        - Casi `intent="doc"`: query che richiedono documentazione (perché, decisione, spec).
        - Casi `intent="both"`: query cross-artefatto (requisiti→implementazione), la
          categoria-firma della mission — proporre ≥6 di questi.
      - Per ogni caso proposto, l'agente usa `eval validate-path` (vehicle deterministico,
        Principio XI) per verificare che i path attesi esistano nell'indice.
      - Presenta la lista di candidati all'utente come **proposta da rivedere** (non persistenza
        automatica — confine D↔N, REQ-043).
      - **Solo dopo approvazione esplicita** dell'utente invoca:
        `sertor-rag eval add-case --query Q --expected P1,P2 --intent code|doc|both --kind nl --confirm`
        Mai scrittura implicita o automatica.
      - Se un path non è verificabile nell'indice: segnala esplicitamente e offre di escluderlo o
        di procedere con `--confirm` (Principio XII).
- [ ] Il corpo della skill deve esplicitare il confine D↔N: il run `eval run --fused` è
      deterministico nel core; la skill è solo la superficie di giudizio per la genesi (REQ-043).
- [ ] Corpo **host-agnostico** (Principio X): nessun riferimento a path Sertor-specifici (es.
      `src/sertor_core/`, `requirements/retrieval-qualita/`); nessun nome-modello hardcodato
      (Opus/Haiku/Sonnet — regola parità dual-target).
- [ ] Aggiorna la skill anche nell'asset dell'installer (`packages/sertor/…/eval-suite-author/SKILL.md`
      se sono file separati, o verifica che il meccanismo `iter_asset_dir` li mantenga in sincronia).
- [ ] Verifica che la skill citi `sertor-rag eval add-case --intent` e `sertor-rag eval validate-path`
      (vehicle), **mai** importi `sertor_core`.

### TASK-E02 — Test unitari: invarianti skill genesi NL intent-typed [P]
**File nuovo**: `tests/unit/test_skill_fused_eval_author.py`
→ dipende da: TASK-E01
- [ ] Verifica statica/strutturale del corpo della skill (nessun LLM nei test, solo file check):
      - `.claude/skills/eval-suite-author/SKILL.md` esiste e contiene il richiamo esplicito a
        `sertor-rag eval add-case --intent` e `sertor-rag eval validate-path`.
      - Nessun import diretto di `sertor_core` menzionato nel corpo della skill.
      - Nessun path Sertor-specifico assoluto (cerca `src/sertor_core/` come stringa nel body —
        guard anti-leak ispirata a `test_assets_copilot_parity.py`).
      - Nessun nome-modello Claude hardcodato (Opus/Haiku/Sonnet).
      - La keyword `approvazione` o `approva` o `approve` compare (confine D↔N — non persistenza
        automatica, REQ-043).
      - La keyword `intent` compare almeno una volta nella sezione aggiunta.
      - I tre valori `code`, `doc`, `both` compaiono nel corpo (copertura intenti).

---

## Fase 7 — Polish e cross-cutting (3 task)

### TASK-P01 — Smoke test end-to-end non-regressione fused (integration, not cloud)
**File nuovo**: `tests/integration/test_fused_eval_gate.py`
→ dipende da: TASK-A01, TASK-A03, TASK-F05 (suite.toml con casi intent)
- [x] Test `@integration` `not cloud` con Chroma locale e facade mock/locale (corpus minimale di
      3-5 file sintetici indicizzati inline, con `doc_type=CODE` e `doc_type=DOC` espliciti):
      - Aggiungi casi NL intent-typed alla suite di test (`intent="code"`, `"doc"`, `"both"`).
      - Esegui `eval run --fused` come subprocess → exit 0, metriche in stdout; output contiene
        `fusion coverage`.
      - Esegui `eval run --fused --record-baseline` → scrive sezione `[fused_baseline]` in
        `eval/baseline.toml`; la sezione `[baseline]` IR è invariata.
      - Degrada artificialmente: baseline con `fusion_coverage=1.0`, run attuale con `coverage=0.0`
        → exit 1 (regressione).
      - Ri-esegui con `SERTOR_EVAL_TOLERANCE=1.0` → exit 0 (tolleranza alta).
      - Due run identici su stesso indice+suite → metriche identiche (determinismo, SC-004).
      - Gate `no-baseline` (baseline assente) → exit 0 (contract `artifacts-toml.md`).
      - `eval run` SENZA `--fused` sul medesimo ambiente → exit 0 invariato (additività, SC-009).
- [x] Test `@integration` per `add-case --intent`:
      - `eval add-case --query "..." --expected path1,path2 --intent both --kind nl --confirm`
        → exit 0, caso con `intent="both"` appare in `suite.toml`; `[[graph_case]]` invariato.
      - Suite con `intent` invalido → exit 1 (`FusedSuiteValidationError`).
- [x] Tutti i test superano con `uv run pytest -m "not cloud" tests/integration/test_fused_eval_gate.py`.

### TASK-P02 — Lint ruff e verifica additività a leve spente
→ dipende da: tutti i task precedenti
- [x] Esegui `uv run ruff check .` e correggi eventuali errori nei file nuovi/modificati
      (regole E,F,I,UP,B; line-length 100). Zero errori come pre-condizione al merge.
- [x] Verifica **additività** (RNF-1/SC-009): senza invocare `eval run --fused`, esegui:
      - `uv run sertor-rag index .` → comportamento e costo identici a prima.
      - `uv run sertor-rag search "test"` → output invariato.
      - `uv run sertor-rag eval run` (IR, senza `--fused`) → output invariato (hit@k/MRR, nessun
        campo `fusion_coverage`, nessun overhead).
      - `uv run sertor-rag graph-eval run` → invariato.
- [x] Esegui `uv run pytest -m "not cloud" tests/unit/` e verifica che TUTTA la suite unit passi
      (inclusi i test IR/graph-eval esistenti e tutti i nuovi test fused).
- [x] Esegui `uv run pytest -m "not cloud" tests/` (root) e verifica che la suite complessiva
      passi (escludendo i test `@cloud`).

### TASK-P03 — Aggiornamento commenti e header in `eval/suite.toml` e `eval/baseline.toml`
**File**: `eval/suite.toml`, `eval/baseline.toml`
→ dipende da: TASK-C01, TASK-C02
> **STATO (2026-06-21): DIFFERITO.** Tocca i file dogfood `eval/suite.toml`/`eval/baseline.toml`
> che vengono curati in C01/C02 (giudizio + indice attivo); va eseguito insieme a quelli. Il
> commento-header del serializzatore `suite_io._serialize_suite` (generato a ogni scrittura) è
> GIÀ aggiornato con la riga `intent` (parte di TASK-F05, fatto).
- [ ] Aggiorna il commento in testa a `eval/suite.toml` per includere la descrizione dei campi
      `intent` e della categoria di fusione (cross-artefatto):
      ```toml
      # eval/suite.toml — Ground truth per la valutazione del retrieval Sertor.
      # [[case]]        = retrieval IR (hit@k/MRR). Campi: query, expected, kind.
      #   intent (069)  = "code" | "doc" | "both" — superficie misurata + tipi attesi (fusion coverage).
      # [[graph_case]]  = navigazione grafo (set-based, FEAT-011). Campi: relation, target, expected.
      ```
- [ ] Aggiorna il commento in testa a `eval/baseline.toml` (se presente) per documentare le due
      sezioni coesistenti: `[baseline]` (IR, FEAT-001) e `[fused_baseline]` (fusione, FEAT-003).
- [ ] Verifica round-trip finale: `tomllib.load(open("eval/suite.toml", "rb"))` e
      `tomllib.load(open("eval/baseline.toml", "rb"))` non sollevano; tutti i casi IR esistenti
      e i `[[graph_case]]` sono invariati (non-distruttività — RNF-5, Principio VI).

---

## Grafo delle dipendenze (sintesi)

```
TASK-G01 (settings fusion_k)  ─┐
TASK-G02 (errore dominio)      ─┤
                                ├→ TASK-F01 [P] (models + intent + entità) ─────────────┐
                                │               → TASK-F02 [P] (fusion.py) ─────────────┤
                                │               → TASK-F03 [P] (fused_runner) ───────────┤
                                │               → TASK-F04 [P] (regression fused) ───────┤
                                │               → TASK-F05 [P] (suite_io intent) ─────────┤
                                └───────────────→ TASK-F06 [P] (baseline_io fused) ───────┤
                                                                                          ↓
                                                                             TASK-A01 (composition factory)
                                                                                          │
                                TASK-A02 [P] ─────────────────────────────────────────────┤
                                                                                          ↓
                                                                             TASK-A03 (CLI --fused/--intent)
                                                                                          │
                  TASK-A04 [P] ← (TASK-F02, TASK-F03)                                   │
                  TASK-A05 [P] ← (TASK-F05, TASK-F06)                                   │
                  TASK-A06 [P] ← (TASK-A02, TASK-A03) ─────────────────────────────────┤
                                                                                          │
                  TASK-B01 [P] ← (TASK-F01, TASK-F05) [verifica non-regressione]        │
                  TASK-B02 [P] ← (TASK-F04) [test regression fused]                     │
                  TASK-B03 [P] ← (TASK-G01) [template env]                              │
                                                                                          ↓
                                                                             TASK-C01 (dogfood NL — GIUDIZIO)
                                                                                          │
                                                                             TASK-C02 (baseline reali)
                                                                                          │
                                                                             TASK-D01 (valutazione leva)
                                                                                          │
                                                                             TASK-D02 (finding + baseline)
                                                                                          │
                              TASK-E01 [P] (skill genesi NL)
                                   → TASK-E02 [P] (test skill)
                                                                                          ↓
                                                          TASK-P01 (smoke test e2e)
                                                          TASK-P02 (lint + additività)
                                                          TASK-P03 (commenti suite/baseline)
```

---

## Criteri di test indipendenti per User Story

| US | Criterio di test indipendente | Task principali | Natura |
|---|---|---|---|
| **US1** (misura fusione) | Run con suite intent-typed → `FusedEvalReport` con per-superficie + fusion coverage; caso `hit@k=True, covered=False` → `hit_but_not_covered` incrementato; suite senza intent → report vuoto onesto exit 0; intent invalido → exit 1 azionabile; determinismo (stesso run → stessi numeri). | TASK-A04, TASK-A05, TASK-A06, TASK-P01 | MECCANICO |
| **US2** (baseline + gate) | Baseline assente → gate `no-baseline` exit 0; baseline registrata → degradazione artificiale → exit 1; leva che abbassa fusion_coverage oltre tolleranza → exit 1 (R-3); `--record-baseline` scrive `[fused_baseline]` senza toccare `[baseline]` IR né `[[graph_case]]`. | TASK-B02, TASK-A06, TASK-P01 | MECCANICO |
| **US3** (dogfood NL) | `eval/suite.toml` contiene ≥22 casi intent-typed (≥6 `both`); tutti i path `expected` verificabili; suite parsabile; casi IR/graph-eval invariati. | TASK-C01, TASK-C02, TASK-P03 | GIUDIZIO (C01) + meccanico (C02) |
| **US4** (leva guidata da misura) | Delta per-superficie e fusion coverage documentato; adozione solo se delta ≥ +0.05; leva spenta di default (additività verificata); nessun LLM nel run. | TASK-D01, TASK-D02, TASK-P02 | GIUDIZIO + empirico |
| **US5** (genesi assistita) | Skill presente e corpo contiene `eval add-case --intent` + `eval validate-path`; no import `sertor_core`; body host-agnostico; confine D↔N esplicito; nessuna persistenza automatica; i tre valori `code`/`doc`/`both` compaiono. | TASK-E01, TASK-E02 | GIUDIZIO (skill) |

---

## Parallelizzazione consigliata (MVP P1)

**Sprint 1 (parallelo — nessun prerequisito):**
- Dev A: TASK-G01 + TASK-G02

**Sprint 2 (parallelo — dopo Sprint 1):**
- Dev A: TASK-F01 → TASK-F02 + TASK-F05
- Dev B: TASK-F03 + TASK-F04 + TASK-F06 (parallelizzabile se si concordano le interfacce prima)

**Sprint 3 (dopo Sprint 2 — MVP core):**
- TASK-A01 (composition factory) — bloccante per CLI
- TASK-A02 [P] (formatter) — parallelizzabile con TASK-A01
- TASK-B01 [P] (verifica non-regressione) — parallelizzabile con TASK-A01
- TASK-B02 [P] (test regression) — parallelizzabile con TASK-A01
- TASK-B03 [P] (template env) — parallelizzabile con TASK-A01

**Sprint 4 (dopo Sprint 3 — MVP completo):**
- TASK-A03 (CLI) → TASK-A04 [P] + TASK-A05 [P] + TASK-A06 [P]

**Sprint 5 (empirico — MVP meccanico su master, baseline reali):**
- TASK-C01 (dogfood, GIUDIZIO) → TASK-C02 (registrazione baseline, meccanico)

**Sprint 6 (P2/Should — dopo baseline):**
- TASK-D01 (valutazione leva, GIUDIZIO+misura) → TASK-D02 (finding + baseline)
- TASK-E01 [P] (skill) → TASK-E02 [P] (test skill)

**Sprint finale:**
- TASK-P01 + TASK-P02 + TASK-P03

---

## Brief di commit (per il `configuration-manager`)

```
docs(tasks): genera tasks.md per FEAT-003 epica retrieval-qualita

Fase SpecKit "tasks" completata per specs/069-qualita-fusione-code-doc.
25 task in 8 fasi (Setup 2 / Fondazionale 6 / US1 6 / US2 3 / US3 2 / US4 2 / US5 2 / Polish 3).
Meccanici: 19 task (Setup + Fondazionale + US1 + US2 + test/lint Polish).
Giudizio/empirici: 6 task (US3 C01, US4 D01+D02, US5 E01+E02, e la parte giudizio di C01).
Nessun hook SpecKit eseguito (script assenti nel repo); nessuna operazione git.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

**File da includere nel commit:**
- `specs/069-qualita-fusione-code-doc/tasks.md` (questo file, nuovo)
