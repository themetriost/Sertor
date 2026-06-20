# Tasks — Ground-truth & valutazione della pertinenza (FEAT-001)

**Branch**: `065-ground-truth-valutazione` | **Generato**: 2026-06-20
**Spec**: [`spec.md`](spec.md) · **Piano**: [`plan.md`](plan.md) · **Dati**: [`data-model.md`](data-model.md)
**Contratti**: [`contracts/cli-eval.md`](contracts/cli-eval.md) ·
[`contracts/artifacts-toml.md`](contracts/artifacts-toml.md) ·
[`contracts/event-eval.md`](contracts/event-eval.md)

> **Nota di processo.** I task marcati `[P]` sono parallelizzabili all'interno della stessa fase
> (nessuna dipendenza reciproca). Il suffisso `→ dipende da` lista i task prerequisiti per ordine di
> esecuzione. Git **mai** qui: brief di commit al fondo per il `configuration-manager`. LLM nel design
> = agente via skill (FEAT-008/009), mai chiamata programmatica nel core.

---

## Fase 0 — Setup (2 task)

### TASK-001 — Aggiungi errori di dominio per il modulo eval
**File**: `src/sertor_core/domain/errors.py`
- [x] Aggiungi `SuiteNotFoundError(SertorError)`: campo `path: str`, messaggio azionabile
      «suite non trovata in `<path>` — crea la suite con `sertor-rag eval add-case`».
- [x] Aggiungi `SuiteValidationError(SertorError)`: campo `case_index: int`, `detail: str`,
      messaggio che identifica il caso offendente per indice e contenuto parziale (REQ-004).
- [x] Aggiungi `SuiteWriteError(SertorError)`: campo `path: str`, messaggio che segnala
      l'impossibilità di serializzare in modo sicuro (round-trip fallito, DA-a).
- [x] Aggiungi `RegressionDetected(SertorError)`: campo `verdict: RegressionVerdict` (forward
      ref; `from __future__ import annotations` già presente), messaggio che nomina ogni metrica
      degradata oltre tolleranza (exit 1, gate REQ-043).
- [x] Verifica: ogni nuovo errore è sottoclasse di `SertorError`; nessun import esterno in
      `errors.py`; `domain/` non importa SDK (Principio I).

### TASK-002 — Aggiungi manopole `eval_dir` / `eval_tolerance` in Settings
**File**: `src/sertor_core/config/settings.py`
- [x] Aggiungi campo `eval_dir: Path` con default `Path("eval")`, letto da `SERTOR_EVAL_DIR`
      (stesso pattern di `index_dir`; usa `Path(os.getenv(..., "eval"))`).
- [x] Aggiungi campo `eval_tolerance: float` con default `0.0`, letto da `SERTOR_EVAL_TOLERANCE`
      (usa `float(os.getenv(..., "0.0"))`).
- [x] Verifica: i default non sono hardcodati in nessun componente diverso da `Settings`
      (Principio VIII); la classe `Settings` resta importabile senza dipendenze esterne.

---

## Fase 1 — Fondazionale: entità e servizi core (6 task)

> Tutti i task di questa fase sono **indipendenti tra loro** e parallelizzabili `[P]`.
> Prerequisiti comuni: TASK-001 (errori), TASK-002 (Settings).

### TASK-003 — Estendi `EvalReport` e aggiungi `QueryOutcome` [P]
**File**: `src/sertor_core/engines/evaluation.py`
→ dipende da: TASK-001, TASK-002
- [x] Aggiungi dataclass `QueryOutcome` (frozen=True) con campi `query: str`,
      `expected: tuple[str, ...]`, `hit: bool`, `rank: int | None`, `top_path: str | None`.
      Posizionala prima di `EvalReport` nello stesso file (accanto all'esistente).
- [x] Estendi `EvalReport` con campo `per_query: tuple[QueryOutcome, ...] = ()` (default vuoto,
      retrocompatibile — RNF-2; i 2 test strict e `test_baseline_quality` continuano a passare
      senza modifiche).
- [x] Aggiorna la funzione `evaluate` per popolare `per_query`: per ogni `(query, expected)` del
      ground-truth costruisci un `QueryOutcome` con `rank` calcolato dallo stesso loop già
      esistente (`next((i+1 …), None)`), senza duplicare la logica di calcolo delle metriche.
      `kind` non entra qui (resta metadato dell'artefatto, riassociato dal chiamante CLI).
- [x] Verifica che i test esistenti (`test_baseline_quality.py`, test strict in
      `tests/unit/test_evaluation.py` se presenti) passino invariati: il campo `per_query` con
      default `()` non rompe nessun consumatore.

### TASK-004 — Implementa entità suite: `EvalCase`, `EvalSuite`, `Baseline`, `RegressionVerdict` [P]
**File nuovo**: `src/sertor_core/services/eval/__init__.py` (package init, vuoto o re-export)
**File nuovo**: `src/sertor_core/services/eval/models.py`
→ dipende da: TASK-001
- [x] Crea il package `src/sertor_core/services/eval/` con `__init__.py` (può riesportare le
      entità pubbliche; non obbligatorio per ora).
- [x] Definisci `EvalCase` (frozen dataclass): `query: str`, `expected: tuple[str, ...]`,
      `kind: str | None = None`. Validazione: `query` non vuota, `expected` non vuoto, ogni
      path non vuoto — altrimenti `SuiteValidationError` dal chiamante (non nel costruttore).
- [x] Definisci `EvalSuite` (frozen dataclass): `cases: tuple[EvalCase, ...]`. Metodi:
      `to_ground_truth() -> GroundTruth` (import da `engines.evaluation`), `kinds() ->
      tuple[str | None, ...]`, `rebased(prefix: str) -> EvalSuite` (eredita logica
      `relative_to` dal fixture `tests/fixtures/ground_truth.py`).
- [x] Definisci `Baseline` (frozen dataclass): `hit_rate: dict[int, float]`, `mrr: float`,
      `queries: int`, `provider: str`, `recorded_at: str` (ISO-8601 UTC, informativo).
- [x] Definisci `MetricDelta` (frozen dataclass): `name: str`, `current: float`,
      `baseline: float`, `delta: float`, `regressed: bool`.
- [x] Definisci `RegressionVerdict` (frozen dataclass): `verdict: str` (`"pass"` |
      `"regressed"` | `"no-baseline"`), `deltas: tuple[MetricDelta, ...]`, `tolerance: float`.
      Metodo `exit_code() -> int`: `0` se `verdict in ("pass", "no-baseline")`, `1` altrimenti.
- [x] Definisci `PathValidation` (frozen dataclass): `checked: tuple[str, ...]`,
      `missing: tuple[str, ...]`, `index_available: bool`.
- [x] Nessun import di SDK esterni; solo stdlib e `engines.evaluation` per `GroundTruth`.

### TASK-005 — Implementa `suite_io.py`: load/write/add/amend [P]
**File nuovo**: `src/sertor_core/services/eval/suite_io.py`
→ dipende da: TASK-004
- [x] Implementa `load_suite(path: Path) -> EvalSuite` via `tomllib.load` (stdlib Python 3.11+):
      file assente → `SuiteNotFoundError(path=str(path))`; voce malformata (campo mancante, tipo
      errato, `expected` vuoto) → `SuiteValidationError(case_index=i, detail=...)`.
- [x] Implementa il **serializzatore TOML a mano** (research DA-a, Principio II/III — no `tomli-w`):
      funzione `_serialize_suite(suite: EvalSuite) -> str` che produce un array di `[[case]]`.
      Regole di escape: `"` → `\"`, `\` → `\\`; query multilinea → basic multiline `"""…"""`.
- [x] Implementa `write_suite(path: Path, suite: EvalSuite) -> None` (non-distruttivo,
      idempotente — REQ-011): scrive con il serializzatore; **round-trip di validazione** dopo ogni
      scrittura: ri-legge con `tomllib` (se `load_suite(path)` solleva → `SuiteWriteError`).
      Ordine stabile (casi esistenti prima, nuovi in coda); nessun duplicato per `query` uguale.
- [x] Implementa `add_case(path: Path, case: EvalCase) -> None`: carica la suite esistente (o
      crea vuota se assente), aggiunge il caso se non già presente (dedup su `query`), chiama
      `write_suite`.
- [x] Implementa `amend_case(path: Path, query: str, **kwargs) -> None`: carica, trova il caso per
      `query` (o `SuiteNotFoundError` se assente nella suite), aggiorna i campi specificati,
      chiama `write_suite`.
- [x] Solo stdlib: `tomllib`, `pathlib`, `dataclasses`; nessun import da `composition.py`.

### TASK-006 — Implementa `baseline_io.py`: load/write baseline [P]
**File nuovo**: `src/sertor_core/services/eval/baseline_io.py`
→ dipende da: TASK-004
- [x] Implementa `load_baseline(path: Path) -> Baseline | None`: file assente → `None` (gestito
      esplicitamente dal chiamante — Principio IV; non è un errore, è assenza legittima di
      riferimento). File malformato → `SuiteValidationError` (riusa lo stesso errore; il file
      TOML è curato, un malformato è un bug di authoring).
- [x] Implementa `write_baseline(path: Path, baseline: Baseline) -> None`: serializzatore TOML a
      mano per lo schema piatto `baseline.toml` (schema documentato in
      `contracts/artifacts-toml.md`). Chiama round-trip di validazione.
- [x] `write_baseline` crea le cartelle intermedie (`path.parent.mkdir(parents=True, exist_ok=True)`).
- [x] Solo stdlib: `tomllib`, `pathlib`, `datetime`.

### TASK-007 — Implementa `regression.py`: funzione pura `compare_to_baseline` [P]
**File nuovo**: `src/sertor_core/services/eval/regression.py`
→ dipende da: TASK-004
- [x] Implementa `compare_to_baseline(report: EvalReport, baseline: Baseline | None,
      tolerance: float) -> RegressionVerdict` come funzione **pura** (zero I/O, zero side-effect):
      - `baseline is None` → `RegressionVerdict(verdict="no-baseline", deltas=(), tolerance=tolerance)`.
      - Per ogni metrica comune (`mrr` + ogni `k` in `hit_rate`): calcola `delta = current - baseline`.
        `regressed = delta < -tolerance`. Raccoglie in `MetricDelta`.
      - Se almeno un `regressed=True` → `verdict="regressed"`, altrimenti `"pass"`.
- [x] Verifica: la funzione è deterministica (stesso input → stesso output); nessun import I/O.

### TASK-008 — Implementa `runner.py`: `run_evaluation` + `validate_paths` [P]
**File nuovo**: `src/sertor_core/services/eval/runner.py`
→ dipende da: TASK-003, TASK-004, TASK-005, TASK-006, TASK-007
- [x] Implementa `run_evaluation(engine: QueryableEngine, suite: EvalSuite,
      ks: tuple[int, ...] = (1, 3, 5, 10)) -> tuple[EvalReport, tuple[str | None, ...]]`:
      chiama `evaluate(engine, suite.to_ground_truth(), ks)` (RIUSA, non riscrive); ritorna
      `(report, suite.kinds())`. Emette evento `eval` via `log_event` (contratto
      `contracts/event-eval.md`: `operation="eval"`, `provider`, `queries`, `hit_rate`, `mrr`,
      `regressed`, `tolerance`; **nessun testo libero** — RNF-3/Principio IX). `regressed` e
      `tolerance` vengono dal `RegressionVerdict` calcolato dal chiamante o da valori di default
      se non ancora confrontato (il runner emette l'evento dopo il confronto, non prima).
- [x] Implementa `validate_paths(paths: tuple[str, ...], indexed_paths: frozenset[str] | None)
      -> PathValidation`: confronto puro path↔indice.
      - `indexed_paths is None` → `PathValidation(checked=paths, missing=(), index_available=False)`.
      - Altrimenti: `missing = tuple(p for p in paths if p not in indexed_paths)`,
        `index_available=True`.
- [x] Solo import da `engines.evaluation` e `services.eval.*`; nessun import di composition o
      adapter (quelli vivono nelle factory).

---

## Fase 2 — Fase US1+US5: run, non-regressione, installabilità (MVP completo) (7 task)

> US1 = misura + gate non-regressione via `sertor-rag eval`. US5 = host/installabile.
> Questa fase produce l'MVP consegnabile e installabile. Prerequisiti: tutte le fasi precedenti.

### TASK-009 — Factory `build_eval_runner` e `build_indexed_docs` in composition
**File**: `src/sertor_core/composition.py`
→ dipende da: TASK-003, TASK-004, TASK-005, TASK-006, TASK-007, TASK-008
- [x] Aggiungi `build_eval_runner(settings: Settings)` che restituisce un callable (o un oggetto
      leggero) che: recupera l'engine via `build_engine(settings)` o `build_baseline_engine(settings)`
      a seconda di `settings.engine`; usa `run_evaluation` dal runner; chiama `enable_observability`
      (pattern CLI esistente). Il CLI `eval` lo chiama come vehicle (Principio XI).
- [x] Aggiungi `build_indexed_docs(settings: Settings) -> frozenset[str] | None`: carica
      `IndexManifest` (già presente in `composition.py` per FEAT-009 refresh incrementale) per la
      collection corrente. Assente/incompatibile → `None` (degrado onesto, Principio IV).
      Espone i `path` dei documenti indicizzati come `frozenset[str]` per `validate_paths`.
- [x] Verifica: i nuovi `build_*` sono cablati esclusivamente dalla composition (Principio I/VIII);
      nessun import di questi nel core o nei servizi.
- [x] Aggiorna `__init__.py` del package `sertor_core` se ri-esporta le factory pubbliche.

### TASK-010 — Formatter output `eval` in `cli/output.py` [P]
**File**: `src/sertor_core/cli/output.py`
→ dipende da: TASK-003, TASK-004, TASK-007
- [x] Aggiungi `format_eval_report(report: EvalReport, kinds: tuple[str | None, ...],
      verdict: RegressionVerdict | None, json_mode: bool) -> str`: funzione **pura** (zero I/O).
      Output umano: riga di metriche aggregate (`hit@k`, `mrr`), tabella per-query `[hit]`/`[miss]`
      + kind + rank + path (pattern uguale all'esempio in `contracts/cli-eval.md`); se `verdict`
      presente, riga `non-regression: PASS/FAIL + delta per metrica`. Output JSON: equivalente
      informativo (SC-002, invariante CLI esistente).
- [x] Aggiungi `format_comparison(reports: tuple[tuple[str, EvalReport], ...],
      json_mode: bool) -> str`: tabella affiancata `metric / label1 / label2 / …` (pattern
      `--compare` in `contracts/cli-eval.md`). Funzione pura.
- [x] Aggiungi `format_regression_report(verdict: RegressionVerdict, json_mode: bool) -> str`:
      compatta (`PASS`/`REGRESSED` + deltas); usabile standalone se serve. Funzione pura.
- [x] Aggiungi `format_path_validation(pv: PathValidation, json_mode: bool) -> str`: lista
      `checked`/`missing`/`index_available`. Funzione pura.
- [x] Verifica: nessuna delle funzioni ha side-effect; compatibilità informativa umano↔JSON (SC-002).

### TASK-011 — Sottocomando `eval` nella CLI (`cli/__main__.py`)
**File**: `src/sertor_core/cli/__main__.py`
→ dipende da: TASK-009, TASK-010
- [x] Aggiungi sottocomando `eval` al parser argparse con sub-azioni annidate (stesso pattern del
      sottocomando `memory` già presente: `add_subparsers` annidato, `set_defaults(handler=...)`):
      - `eval run [--compare LABELS] [--record-baseline] [-k K[,K…]] [--corpus C] [--json]
        [-v] [--log-json] [--log-config F]`
      - `eval add-case --query Q --expected P[,P…] [--kind K] [--confirm] [--corpus C] [--json]`
      - `eval validate-path P[…] [--corpus C] [--json]`
- [x] Implementa `_cmd_eval_run(args, settings)`: segui il flusso del contratto
      `contracts/cli-eval.md` §`sertor-rag eval run` — carica suite, costruisce engine via
      `build_eval_runner`, chiama `run_evaluation`, confronta baseline con `compare_to_baseline`,
      gestisce `--record-baseline` (scrive `baseline.toml` solo su flag esplicito — REQ-044),
      gestisce `--compare` (costruisce engine per ogni label e valuta; un evento `eval` per config).
      Regressione → solleva `RegressionDetected` → catturata da `main()` (exit 1).
      Suite assente → `SuiteNotFoundError` → catturata da `main()` (exit 1, messaggio azionabile).
- [x] Implementa `_cmd_eval_add(args, settings)`: carica suite (o crea se assente), valida i path
      attesi via `build_indexed_docs` + `validate_paths`, path assente → **warning** + richiede
      `--confirm` o prompt TTY (`isatty()`) prima di scrivere; senza conferma → exit 1 azionabile
      (non scrive mai parzialmente). Chiama `add_case`.
- [x] Implementa `_cmd_eval_validate(args, settings)`: chiama `build_indexed_docs` + `validate_paths`
      su i path forniti; restituisce `PathValidation` umano/JSON; exit 0 sempre (è verifica, non gate).
- [x] Aggiorna il blocco `except SertorError` in `main()` per catturare anche `RegressionDetected`,
      `SuiteNotFoundError`, `SuiteValidationError`, `SuiteWriteError` (già sotto-tipi di `SertorError`,
      quindi catturati automaticamente se il blocco è `except SertorError`).
- [x] Verifica: il CLI è thin (nessuna logica di retrieval; solo parsing → factory → format); exit
      code coerenti col contratto (0/1/2); nessun import diretto di engine/manifest (Principio XI).

### TASK-012 — Test unitari: suite_io, baseline_io, regression, runner [P]
**File nuovi**: `tests/unit/test_suite_io.py`, `tests/unit/test_baseline_io.py`,
               `tests/unit/test_regression.py`, `tests/unit/test_eval_runner.py`
→ dipende da: TASK-005, TASK-006, TASK-007, TASK-008
- [x] `test_suite_io.py`: round-trip write→read identico al sorgente (REQ-011); query con `"`
      e `\` correttamente escappate; `SuiteValidationError` su voce senza `expected`; `SuiteWriteError`
      se il round-trip fallisce (simula con file non-riscrivibile o mock `tomllib`); `add_case`
      idempotente su query duplicata; `amend_case` aggiorna correttamente `expected`.
- [x] `test_baseline_io.py`: round-trip `write_baseline`→`load_baseline` identico; file assente →
      `None`; `recorded_at` ISO-8601 presente e non vuoto.
- [x] `test_regression.py`: `compare_to_baseline(report, None, 0.0)` → `"no-baseline"`, exit 0;
      `current < baseline - tolerance` → `"regressed"`, exit 1; entro tolleranza → `"pass"`, exit 0;
      funzione pura (stesso input → stesso output ogni chiamata).
- [x] `test_eval_runner.py`: `run_evaluation` con engine mock (stile `tests/fixtures/mocks.py`)
      richiama `evaluate` correttamente (non lo riscrive); `validate_paths` con `indexed_paths=None`
      → `index_available=False`; con `indexed_paths` popolato → `missing` corretto; evento `eval`
      emesso (mock `log_event` o verifica side-effect tramite `caplog`).
- [x] Tutti i test: `not cloud`, no rete, funzioni pure testabili senza I/O dove possibile.

### TASK-013 — Test unitari: formatter output e CLI eval (con core mockato) [P]
**File nuovi**: `tests/unit/test_output_eval.py`, `tests/unit/test_cli_eval.py`
→ dipende da: TASK-010, TASK-011
- [x] `test_output_eval.py`: funzioni pure — `format_eval_report` con `per_query` popolato produce
      stringhe contenenti `hit@k`, `mrr`, `[hit]`/`[miss]`, `kind`, `rank`; output `--json` è
      valido JSON con gli stessi campi informativi (SC-002); `format_comparison` produce colonne
      affiancate; `format_path_validation` con `missing` non vuoto produce warning.
- [x] `test_cli_eval.py`: stile `test_cli_search.py` / `test_cli_memory.py` — usa `subprocess` o
      `argparse.parse_args` con core mockato (`monkeypatch` / `MockEngine` da `mocks.py`):
      - `eval run` con suite presente e engine mock → exit 0, metriche in stdout.
      - `eval run` senza suite → exit 1, messaggio che nomina `add-case` in stderr.
      - `eval run` con `--record-baseline` → scrive `baseline.toml`, exit 0.
      - `eval run` con baseline che degrada oltre tolleranza → exit 1 (`RegressionDetected`).
      - `eval run` entro tolleranza → exit 0.
      - `eval add-case` con path nell'indice → exit 0, caso aggiunto.
      - `eval add-case` con path assente dall'indice senza `--confirm` → exit 1, warning.
      - `eval add-case` con path assente + `--confirm` → exit 0, caso aggiunto con warning.
      - `eval validate-path` → exit 0 sempre; JSON valido con `--json`.
      - `eval` senza sub-azione → exit 2 (usage).
- [x] Verifica gate exit-code (SC-004): il gate `RegressionDetected` produce exit 1 in modo
      riproducibile con suite e baseline fisse.

### TASK-014 — Migrazione fixture dogfood → `eval/suite.toml`
**File nuovo**: `eval/suite.toml`
→ dipende da: TASK-005
- [x] Crea `eval/suite.toml` a root del repo trasformando `tests/fixtures/ground_truth.py`
      (`GROUND_TRUTH`, 11 coppie) nel formato `[[case]]` documentato in
      `contracts/artifacts-toml.md` §`eval/suite.toml`. Preserva `kind` per ogni caso.
- [x] Commento in testa al file: `# Sertor eval suite (dogfood example). Versioned project data —
      no secrets. kind ∈ {"symbol","nl"} (optional). Paths are repo-root-relative POSIX.`
- [x] Verifica round-trip: `tomllib.load(open("eval/suite.toml", "rb"))` non solleva; ogni `case`
      ha `query` e `expected` non vuoti (eseguibile come micro-script di verifica durante il task).
- [x] Il fixture `tests/fixtures/ground_truth.py` resta **invariato** (i 2 test strict continuano
      a usarlo — RNF-2); la suite in `eval/` è l'artefatto ospite, non un sostituto.

### TASK-015 — Template `.env` installer: manopole `eval_dir` / `eval_tolerance` (US5 — installabilità)
**File**: `packages/sertor/src/sertor_installer/assets/rag/env.local.tmpl`
**File**: `packages/sertor/src/sertor_installer/assets/rag/env.azure.tmpl`
→ dipende da: TASK-002
- [x] Aggiungi in entrambi i template (sezione commentata, stile delle manopole esistenti come
      `SERTOR_EMBED_CACHE`):
      ```
      # Optional: directory for the eval suite and baseline (versioned project data). Default "eval".
      # SERTOR_EVAL_DIR=eval
      # Optional: absolute tolerance for the non-regression gate (0.0 = zero tolerance). Default 0.0.
      # SERTOR_EVAL_TOLERANCE=0.0
      ```
- [x] Verifica: le righe sono commentate di default (feature non attiva di default — REQ-062 additività);
      nessun segreto nei template (RNF-6).
- [x] Controlla che `test_packaging.py` (integration, se esegue il check di coerenza template) non
      fallisca per le nuove righe; aggiorna eventuali riferimenti nel test se necessario.

---

## Fase 3 — Fase US2+US4: genesi assistita + confronto 2 config (P2) (3 task)

> US2 = skill FEAT-008 (genesi assistita via agente). US4 = `--compare` nella CLI (confronto locale).
> US4 è già implementato in `_cmd_eval_run` (TASK-011); i task qui completano skill e debito installabile.
> Prerequisiti: tutte le fasi precedenti.

### TASK-016 — Skill `eval-suite-author` per genesi assistita (FEAT-008, US2) [P]
**File nuovo**: `.claude/skills/eval-suite-author/SKILL.md`
→ dipende da: TASK-011 (il sottocomando `eval` deve esistere per poter essere richiamato)
- [x] Crea la skill `eval-suite-author` (directory `.claude/skills/eval-suite-author/`) seguendo
      il pattern di `derive-entity-types` (research DA-c): la skill descrive come l'agente,
      usando i tool RAG/MCP del corpus indicizzato (`search_code`, `search_docs`, `find_symbol`),
      **deriva candidati** `query → path atteso` e li propone all'utente per approvazione.
- [x] Il corpo della skill deve esplicitare il confine D↔N (REQ-023/RNF-4): solo i casi
      approvati vengono persistiti; la skill **richiama `sertor-rag eval add-case`** (vehicle,
      Principio XI) per ogni caso approvato, MAI importando `sertor_core` direttamente.
- [x] La skill deve gestire il caso «corpus non indicizzato» (REQ-022): se `validate-path` o
      `search_code` ritornano vuoti/errori, la skill **fallisce con messaggio azionabile**
      («indicizza prima il progetto con `sertor-rag index .`»).
- [x] Corpo host-agnostico (Principio X): nessun riferimento a path Sertor-specifici; nessun
      nome-modello hardcodato (regola parità dual-target da FEAT-001 epica debito-tecnico).
- [x] Verifica invariante (US2 AC4): il run deterministico (`eval run`) non dipende dalla skill;
      la skill è separata e non contiene codice Python che chiami un LLM.

### TASK-017 — Skill cablata in `build_rag_plan` (debito di completamento installabilità, US5/P2)
**File**: `packages/sertor/src/sertor_installer/` (installer rag plan builder)
→ dipende da: TASK-016
- [x] Individua il plan-builder `build_rag_plan` (o equivalente) nell'installer del pacchetto
      `sertor` e aggiungi la skill `eval-suite-author` come artefatto da depositare su `sertor
      install` (pattern `iter_asset_dir` o equivalente, stesso meccanismo delle skill esistenti
      come `wiki-author`).
- [x] Verifica che `sertor install rag` (dry-run) includa la skill nel piano generato; aggiorna
      `sertor_owned_paths` se la funzione esiste per garantire la copertura upgrade/uninstall.
- [x] Verifica che il test di parità asset (se presente `test_assets_copilot_parity.py` o
      equivalente) non segnali leak di path Sertor-specifici o slash-command nel body della skill.

### TASK-018 — Test unitari: genesi assistita + confronto 2 config [P]
**File nuovo**: `tests/unit/test_cli_eval_compare.py`,
               `tests/unit/test_skill_eval_author.py` (verifica invarianti, non esecuzione live)
→ dipende da: TASK-016, TASK-017
- [x] `test_cli_eval_compare.py`: `eval run --compare baseline,hybrid` con due engine mock →
      exit 0; output affiancato con entrambi i label; un evento `eval` per engine (verificabile
      con `caplog` o mock `log_event`).
- [x] `test_skill_eval_author.py` (verifica statica/strutturale, non live LLM): il file
      `.claude/skills/eval-suite-author/SKILL.md` esiste e contiene il richiamo esplicito a
      `sertor-rag eval add-case` (nessun import `sertor_core` menzionato); nessun path
      Sertor-specifico (guard anti-leak ispirata a `test_assets_copilot_parity.py`).

---

## Fase 4 — Fase US3: feedback esplicito di pertinenza (P3) (3 task)

> US3 = skill FEAT-009 (feedback esplicito che raffina la suite via `amend_case`).
> Prerequisiti: tutte le fasi precedenti (in particolare TASK-005 per `amend_case`, TASK-011 per il CLI).

### TASK-019 — Skill `eval-feedback` per feedback esplicito (FEAT-009, US3) [P]
**File nuovo**: `.claude/skills/eval-feedback/SKILL.md`
→ dipende da: TASK-011, TASK-005
- [x] Crea la skill `eval-feedback` (directory `.claude/skills/eval-feedback/`) con il pattern
      di US3 (spec §US3): l'agente osserva i risultati di una ricerca, riceve il giudizio esplicito
      dell'utente (pertinente / non pertinente) e **richiama `sertor-rag eval add-case` o il
      meccanismo di amend** per aggiornare gli `expected` del caso corrispondente.
- [x] La skill deve garantire che **nessun giudizio venga inferito o persistito senza azione
      esplicita** (REQ-051): ogni modifica alla suite richiede conferma esplicita dell'utente.
- [x] La skill gestisce il caso «query senza caso corrispondente nella suite» (REQ-052): offre di
      creare un nuovo caso con `eval add-case`.
- [x] Corpo host-agnostico (Principio X); nessun nome-modello hardcodato.
- [x] Verifica (US3 AC2): la skill non ha accesso a modalità «automatica»; ogni azione di
      scrittura passa dal CLI (vehicle).

### TASK-020 — Skill `eval-feedback` cablata nell'installer (debito completamento, US5/P3)
**File**: `packages/sertor/src/sertor_installer/` (installer rag plan builder)
→ dipende da: TASK-019
- [x] Aggiungi `eval-feedback` al piano di `build_rag_plan` con lo stesso pattern di TASK-017.
- [x] Aggiorna `sertor_owned_paths` se necessario.
- [x] Verifica parità asset (nessun path/slash-command Sertor-specifico).

### TASK-021 — Test unitari: skill feedback e invarianti US3 [P]
**File nuovo**: `tests/unit/test_skill_eval_feedback.py`
→ dipende da: TASK-019
- [x] Verifica statica: `eval-feedback/SKILL.md` esiste; contiene riferimento esplicito al vehicle
      CLI (`sertor-rag eval add-case`); non menziona import diretti di `sertor_core`; corpo
      host-agnostico (no path Sertor-specifici, no nomi-modello Claude).
- [x] Verifica che `amend_case` in `suite_io.py` sia richiamabile con i parametri che la skill
      usa (test di tipo: la firma pubblica regge l'uso atteso).

---

## Fase 5 — Polish e cross-cutting (3 task)

### TASK-022 — Smoke test end-to-end non-regressione (integration, not cloud)
**File nuovo**: `tests/integration/test_eval_gate.py`
→ dipende da: TASK-009, TASK-011, TASK-014
- [x] Test `@integration` `not cloud` che usa Chroma locale (mock o istanza temporanea) e la suite
      `eval/suite.toml` del dogfood (o una suite minimale di 2-3 casi costruita inline): esegue
      `sertor-rag eval run` come subprocess; verifica exit 0 con metriche in stdout; esegue
      `sertor-rag eval run --record-baseline`; modifica artificialmente la suite per abbassare la
      qualità attesa; verifica exit 1 (`RegressionDetected`). Verifica SC-001 (determinismo: 2 run
      identici → stesse metriche) e SC-004 (gate).
- [x] Test `@integration` `not cloud` per `add-case` + `validate-path` con indice reale (o manifest
      temporaneo): verifica SC-003 (suite non vuota dopo aggiunta) e SC-010 (suite assente → exit 1).
- [x] Tutti i test superano con `uv run pytest -m "not cloud" tests/integration/test_eval_gate.py`.

### TASK-023 — Lint ruff e verifica additività a leve spente
→ dipende da: tutti i task precedenti
- [x] Esegui `uv run ruff check .` e correggi eventuali errori nei file nuovi/modificati
      (regole E,F,I,UP,B; line-length 100).
- [x] Verifica **additività** (REQ-062/SC-009): con leve di default (`SERTOR_EVAL_DIR=eval`,
      `SERTOR_EVAL_TOLERANCE=0.0`, senza invocare `eval`), esegui `sertor-rag index .` e
      `sertor-rag search "test"` e verifica che comportamento e costo siano identici a prima
      (nessun warning, nessun overhead — Principi I/III). Verifica con `uv run pytest -m
      "not cloud" tests/unit/` che tutta la suite unit passi.
- [x] Verifica che `EvalReport` senza il campo `per_query` (i test esistenti costruiscono
      `EvalReport` senza di esso) continui a funzionare (default `()` — RNF-2).

### TASK-024 — Aggiorna `composition.py` exports e `__init__.py`
**File**: `src/sertor_core/composition.py`, `src/sertor_core/__init__.py`
→ dipende da: TASK-009
- [x] Verifica che `build_eval_runner` e `build_indexed_docs` siano esportati coerentemente con
      le altre factory pubbliche (pattern `build_facade`, `build_indexer`, ecc.).
- [x] Aggiorna il docstring di `composition.py` per citare le nuove factory.
- [x] Se `src/sertor_core/__init__.py` ri-esporta le factory, aggiungici `build_eval_runner` e
      `build_indexed_docs`; altrimenti lascia invariato (dipende dalla convenzione del package).
- [x] Esegui `uv run pytest tests/unit/` per la suite completa: tutti i test passano (inclusi i
      test esistenti di evaluation, baseline_quality, CLI).

---

## Grafo delle dipendenze (sintesi)

```
TASK-001 (errori)  ──┐
TASK-002 (settings) ─┤
                      ├→ TASK-003 [P] ─────────────────────────┐
                      ├→ TASK-004 [P] → TASK-005 → TASK-008 ──┤
                      │              → TASK-006 → TASK-008 ──┤
                      │              → TASK-007 → TASK-008 ──┤
                      └──────────────────────────────────────┤
                                                              ↓
                                                 TASK-009 (composition factory)
                                                              │
                              TASK-010 [P] ──────────────────┤
                                                              ↓
                                                 TASK-011 (CLI eval)
                                                              │
                    TASK-012 [P] ← (TASK-005/006/007/008)    │
                    TASK-013 [P] ← (TASK-010, TASK-011) ─────┤
                    TASK-014    ← (TASK-005)                  │
                    TASK-015    ← (TASK-002)                  │
                                                              ↓
                                            TASK-016 [P] (skill genesi)
                                                → TASK-017 (cablaggio installer)
                                                    → TASK-018 [P]
                                            TASK-019 [P] (skill feedback)
                                                → TASK-020 (cablaggio installer)
                                                    → TASK-021 [P]
                                                              │
                                                              ↓
                                     TASK-022 (smoke test e2e)
                                     TASK-023 (lint + additività)
                                     TASK-024 (exports composition)
```

---

## Criteri di test indipendenti per User Story

| US | Criterio di test indipendente | Task principali |
|---|---|---|
| **US1** (run + gate) | Due run identici → metriche uguali; regressione artificiale → exit 1; entro tolleranza → exit 0; suite assente → exit 1 con messaggio azionabile. | TASK-012, TASK-013, TASK-022 |
| **US2** (genesi assistita) | Skill presente e corpo contiene `sertor-rag eval add-case`; no import `sertor_core`; body host-agnostico. `--compare` con 2 engine → output affiancato. | TASK-018 |
| **US3** (feedback) | Skill `eval-feedback` presente; ogni scrittura passa dal CLI; no persistenza automatica; body host-agnostico. | TASK-021 |
| **US4** (confronto 2 config) | `eval run --compare baseline,hybrid` con mock → exit 0, colonne affiancate, un evento `eval` per engine. | TASK-018 |
| **US5** (installabile) | Template `.env` contiene le manopole commentate; skill cablate nel piano install (dry-run); a leve spente `sertor-rag index/search` invariati. | TASK-015, TASK-017, TASK-020, TASK-023 |

---

## Parallelizzazione consigliata (MVP P1)

**Sprint 1 (parallelo):**
- Sviluppatore A: TASK-001 + TASK-002 + TASK-003
- Sviluppatore B: TASK-004 → TASK-005 + TASK-006 + TASK-007

**Sprint 2 (dopo Sprint 1):**
- TASK-008 → TASK-009 (bloccante per CLI)
- TASK-010 (parallelo a TASK-009)

**Sprint 3 (MVP completo):**
- TASK-011 (CLI) → TASK-012 + TASK-013 [P] + TASK-014 + TASK-015

**Sprint 4 (P2/P3, dopo merge MVP):**
- TASK-016 + TASK-019 [P] → rispettivi installer e test

**Sprint finale:**
- TASK-022 + TASK-023 + TASK-024

---

## Brief di commit (per il `configuration-manager`)

```
docs(tasks): genera tasks.md per FEAT-001 epica retrieval-qualita

Fase SpecKit "tasks" completata per specs/065-ground-truth-valutazione.
24 task in 5 fasi (Setup 2 / Fondazionale 6 / US1+US5 7 / US2+US4 3 / US3 3 / Polish 3).
Nessun hook SpecKit eseguito (script assenti nel repo); nessuna operazione git.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

**File da includere nel commit:**
- `specs/065-ground-truth-valutazione/tasks.md` (questo file, nuovo)
