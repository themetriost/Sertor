# Phase 1 — Data Model: Ground-truth & valutazione della pertinenza (FEAT-001)

**Branch**: `065-ground-truth-valutazione` · deriva da
[`research.md`](research.md) · Key Entities da [`spec.md`](spec.md) §Key Entities.

> **Principio guida**: *promuovere*, non reinventare. Le entità del core esistenti
> (`evaluate`/`EvalReport`/`QueryableEngine`/`GroundTruth`) restano **invariate** salvo **un'estensione
> additiva non-breaking** (campo `per_query` di `EvalReport`). Le entità NUOVE vivono in
> `services/eval/` (servizio deterministico) e in `cli/output.py` (proiezione). Nessuna nuova **porta**
> Protocol (la suite/baseline sono **dati**, non boundary verso provider esterni — Principio III/YAGNI,
> stesso pattern di `IndexManifest`/`EmbeddingCache`).

---

## 1. Entità del dominio (esistenti — invariate o estese)

### 1.1 `GroundTruth` (alias di tipo) — INVARIATO
`engines/evaluation.py:14`
```python
GroundTruth = list[tuple[str, list[str]]]  # (query, expected_paths)
```
La firma di `evaluate` resta `(query, expected_paths)`: **`kind` NON entra qui** (resta metadato
dell'artefatto/report, riassociato per indice dal chiamante CLI). Principio I/III: il core misura, non
classifica.

### 1.2 `QueryableEngine` (Protocol) — INVARIATO
`engines/evaluation.py:18`. `provider: str` + `query(query, k) → list[RetrievalResult]`. I `build_*`
engine vi aderiscono per structural typing.

### 1.3 `EvalReport` — ESTESO (additivo, non-breaking)
`engines/evaluation.py:32`
```python
@dataclass(frozen=True)
class EvalReport:
    hit_rate: dict[int, float]
    mrr: float
    queries: int
    provider: str
    per_query: tuple[QueryOutcome, ...] = ()   # NUOVO — default vuoto (retrocompatibile)
```
- **Additività garantita** (RNF-2, Principio I): il campo ha default `()`; i consumatori esistenti (2
  test strict, `test_baseline_quality`) ignorano il campo → restano verdi. `evaluate` lo popola sempre
  (il dettaglio è gratis: già calcola `rank` per query).

### 1.4 `QueryOutcome` — NUOVO (in `engines/evaluation.py`, accanto a `EvalReport`)
Esito per-query del run, per il dettaglio hit/miss del report (REQ-033).
```python
@dataclass(frozen=True)
class QueryOutcome:
    query: str
    expected: tuple[str, ...]
    hit: bool                 # rank trovato entro k=10
    rank: int | None          # 1-based, None se miss
    top_path: str | None      # path del 1° risultato (diagnosi)
```
`kind` **non** è qui (il core non lo conosce): il report CLI lo riassocia dalla suite.

---

## 2. Entità dell'artefatto-suite (NUOVE — `services/eval/`)

### 2.1 `EvalCase` — il caso di valutazione (REQ-001/003)
```python
@dataclass(frozen=True)
class EvalCase:
    query: str
    expected: tuple[str, ...]   # path attesi, POSIX, relativi alla root indicizzata
    kind: str | None = None     # "symbol" | "nl" | … (libero, opzionale — REQ-003)
```
- Unità di hit/miss. Validazione: `query` non vuota, `expected` non vuoto, ogni path non vuoto. Voce
  malformata → `SuiteValidationError` che **nomina il caso** offendente (REQ-004, Principio IV).

### 2.2 `EvalSuite` — la suite come dato del progetto (REQ-001/002/006)
```python
@dataclass(frozen=True)
class EvalSuite:
    cases: tuple[EvalCase, ...]

    def to_ground_truth(self) -> GroundTruth: ...   # (query, list(expected)) per `evaluate`
    def kinds(self) -> tuple[str | None, ...]: ...  # kind paralleli, per il report
    def rebased(self, prefix: str) -> "EvalSuite": ... # REQ-005, eredita `relative_to` del fixture
```
- **Persistita** come `eval/suite.toml` (array di `[[case]]`). Mai segreti (REQ-006/RNF-6): è dato
  versionato, non output. Vuota/assente al run → **fallimento azionabile** (REQ-032, non uno zero
  ingannevole).

### 2.3 `Baseline` — il riferimento di non-regressione (REQ-041)
```python
@dataclass(frozen=True)
class Baseline:
    hit_rate: dict[int, float]
    mrr: float
    queries: int
    provider: str
    recorded_at: str   # ISO-8601 UTC, informativo
```
- Persistito come `eval/baseline.toml` (dato versionato). Costruito da un `EvalReport` corrente su
  `--record-baseline` (REQ-040/044, solo su accettazione esplicita).

---

## 3. Entità di confronto e report (NUOVE)

### 3.1 `RegressionVerdict` — esito del gate (REQ-042/043)
```python
@dataclass(frozen=True)
class MetricDelta:
    name: str          # "mrr" | "hit@1" | "hit@3" | …
    current: float
    baseline: float
    delta: float       # current - baseline
    regressed: bool    # delta < -tolerance

@dataclass(frozen=True)
class RegressionVerdict:
    verdict: str                       # "pass" | "regressed" | "no-baseline"
    deltas: tuple[MetricDelta, ...]
    tolerance: float
    def exit_code(self) -> int: ...    # 0 se pass/no-baseline, 1 se regressed
```
- Funzione **pura** `compare_to_baseline(report, baseline, tolerance) → RegressionVerdict`
  (deterministica, testabile senza I/O — Principio V/VI).

### 3.2 `ComparisonReport` — confronto 2 config locali (REQ-034)
```python
@dataclass(frozen=True)
class ComparisonReport:
    reports: tuple[tuple[str, EvalReport], ...]  # [(label, report)…], es. ("baseline", …),("hybrid", …)
```
- Prodotto chiamando `evaluate` due volte (una per config) sulla **stessa** suite — promozione di
  `test_baseline_quality.py`. Reso affiancato (umano + JSON).

### 3.3 `PathValidation` — validazione write-time (REQ-012/DA-e)
```python
@dataclass(frozen=True)
class PathValidation:
    checked: tuple[str, ...]
    missing: tuple[str, ...]      # path NON presenti nell'indice → warning + conferma
    index_available: bool         # False se manifest assente/incompatibile (degrado onesto)
```

---

## 4. Servizi e funzioni (NUOVE — `services/eval/`)

| Componente | File | Responsabilità | Note |
|---|---|---|---|
| `load_suite(path) → EvalSuite` | `services/eval/suite_io.py` | Legge `suite.toml` via `tomllib`; valida; malformato → `SuiteValidationError` (REQ-004). | stdlib |
| `write_suite(path, suite)` / `add_case` / `amend_case` | `services/eval/suite_io.py` | Serializzatore TOML a mano (research DA-a); non-distruttivo, idempotente (REQ-011); round-trip validato; ambiguo → `SuiteWriteError`. | stdlib |
| `load_baseline(path) → Baseline \| None` / `write_baseline` | `services/eval/baseline_io.py` | TOML; assente → `None` (gestito esplicitamente dal chiamante, REQ-040). | stdlib |
| `compare_to_baseline(report, baseline, tol) → RegressionVerdict` | `services/eval/regression.py` | Funzione pura (REQ-042/043). | stdlib |
| `run_evaluation(engine, suite, ks) → (EvalReport, kinds)` | `services/eval/runner.py` | Avvolge `evaluate`; riporta `EvalReport` + kind paralleli per il report; emette evento `eval` (RNF-3). | usa core `evaluate` |
| `validate_paths(suite_or_paths, indexed_paths) → PathValidation` | `services/eval/runner.py` | Confronto path↔indice (REQ-012). | pura |

### Factory composition (vehicle, Principio XI)
| Factory | Ritorna | Gate |
|---|---|---|
| `build_eval_runner(settings)` | runner che costruisce l'engine via `build_engine`/`build_baseline_engine` e chiama `evaluate` | — (sempre disponibile; il run non ha gate-privacy) |
| `build_indexed_docs(settings) → frozenset[str] \| None` | path indicizzati dal `IndexManifest.load(collection_name(...))`; `None` se manifest assente/incompatibile | — |

- Le factory vivono in `composition.py`: **unico** punto che conosce gli adapter (Principio I/VIII). Il
  CLI `eval` consuma **solo** le factory (mai import diretto di engine/manifest — Principio XI; il CLI
  *è* il vehicle).

---

## 5. Superficie CLI (NUOVA — `cli/__main__.py` + `cli/output.py`)

Sottocomando `eval` con sub-azioni (argparse, pattern `memory`):

| Comando | Handler | Esito |
|---|---|---|
| `sertor-rag eval run [--compare A,B] [--record-baseline] [-k …] [--json]` | `_cmd_eval_run` | metriche + per-query; gate non-regressione (exit 1 se regressed); confronto se `--compare`. |
| `sertor-rag eval add-case --query Q --expected P[,P] [--kind K] [--confirm]` | `_cmd_eval_add` | persiste un caso; path assente → warning + richiede `--confirm` (REQ-012). |
| `sertor-rag eval validate-path P[…]` | `_cmd_eval_validate` | `PathValidation` (umano/JSON) — primitiva per la skill (FEAT-008). |

- **Exit codes** (coerenti col CLI esistente): `0` successo / `1` `SertorError` (suite assente
  `SuiteNotFoundError`, regressione `RegressionDetected`, malformato `SuiteValidationError`) / `2` usage
  (argparse).
- **Output**: `format_eval_report`, `format_comparison`, `format_regression_report`,
  `format_path_validation` in `output.py` — funzioni **pure** umano + `--json` (equivalenza informativa,
  invariante SC-002).

---

## 6. Errori di dominio (NUOVI — `domain/errors.py`, sottoclassi di `SertorError`)

| Errore | Quando | Exit |
|---|---|---|
| `SuiteNotFoundError` | run senza `eval/suite.toml` (REQ-032) — messaggio azionabile «crea la suite». | 1 |
| `SuiteValidationError` | voce malformata; **nomina il caso** offendente (REQ-004). | 1 |
| `SuiteWriteError` | il writer non sa serializzare in sicurezza (research DA-a, fail-safe). | 1 |
| `RegressionDetected` | metrica sotto baseline oltre tolleranza (REQ-043, gate). | 1 |

Tutti `SertorError` → catturati da `main()` (stderr + exit 1, Principio IV).

---

## 7. Manopole di configurazione (Settings — Principio VIII)

| Campo `Settings` | Env | Default | Uso |
|---|---|---|---|
| `eval_dir: Path` | `SERTOR_EVAL_DIR` | `Path("eval")` | sede di `suite.toml`/`baseline.toml` (REQ-002, versionata). |
| `eval_tolerance: float` | `SERTOR_EVAL_TOLERANCE` | `0.0` | tolleranza assoluta del gate (REQ-043). |

- Default **solo** in `Settings` (mai hardcodati nei componenti). A leve di default, comportamento e
  **costo** identici a oggi: il comando `eval` esiste ma **non viene chiamato** in un flusso normale di
  index/search → additività (REQ-062, Principi I/III, SC-009).

---

## 8. Relazioni (diagramma testuale)

```
eval/suite.toml ──load_suite──▶ EvalSuite ──to_ground_truth──▶ GroundTruth
                                    │                               │
                                    │ kinds()                       ▼
                                    │                    evaluate(engine, gt) ──▶ EvalReport(+per_query)
                                    │                               │
              build_engine(settings) [vehicle, Princ. XI] ─────────┘
                                                                    │
eval/baseline.toml ──load_baseline──▶ Baseline ──compare_to_baseline(report, …)──▶ RegressionVerdict
                                                                    │                     │
                                                              output.py ◀────────────────┘ exit_code()
IndexManifest.load(collection).files ──build_indexed_docs──▶ frozenset[path] ──validate_paths──▶ PathValidation
```

## 9. Invarianti
- **Determinismo** (REQ-035, Principio VI): stesso indice + stessa suite → stesso `EvalReport`
  (`evaluate` è già puro; il runner non introduce non-determinismo).
- **Non-distruttività/idempotenza** (REQ-011, Principio VI): `add-case`/`write_suite` preservano i casi
  esistenti, ordine stabile, re-run senza duplicati.
- **Core invariato fuori dai punti citati** (RNF-2): solo `EvalReport.per_query` + `QueryOutcome` nuovi
  in `evaluation.py`; porte/adapter/engine **invariati**.
