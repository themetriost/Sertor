# Data Model — Qualità del retrieval fuso code+doc (FEAT-003)

**Branch**: `069-qualita-fusione-code-doc` · Fase 1 del `plan`. Tutte le entità sono **additive** a
`src/sertor_core/services/eval/models.py` (frozen dataclasses, dati puri, nessun I/O). Default neutri →
una suite/baseline esistente resta valida (Principio VI, RNF-5).

> **Principio guida.** `evaluate`/`EvalReport`/`QueryOutcome` (`engines/evaluation.py`) restano
> **INVARIATI**. La fusion coverage non passa per `evaluate` (che proietta via i soli `.path`): è un
> secondo passaggio puro sui `RetrievalResult` (che portano `doc_type`). Le superfici sono adattatori
> `QueryableEngine` sul `RetrievalFacade`.

---

## 1. Estensione di `EvalCase` (campo `intent` additivo)

```python
@dataclass(frozen=True)
class EvalCase:
    query: str
    expected: tuple[str, ...]
    kind: str | None = None
    intent: str | None = None     # NUOVO (069): "code" | "doc" | "both" | None
```

- `intent ∈ {"code", "doc", "both"}` o `None` (REQ-003). **Distinto da `kind`** (`kind` = natura della
  query per il routing/report; `intent` = tipo atteso + superficie). Coesistono.
- `intent=None` (default) → caso IR puro come oggi (REQ-004: un caso senza intent coerente non
  contribuisce alle metriche per-superficie/fusione, resta nei conteggi hit@k generali). **Retrocompatibile**:
  i casi esistenti in `eval/suite.toml` non hanno `intent` e restano validi.
- Validazione (`suite_io._parse_case`): se `intent` presente, deve essere uno di `{code,doc,both}`
  altrimenti `SuiteValidationError` che **nomina il caso** (Principio IV). Stringa vuota → errore.

**Helper su `EvalSuite` (additivi, puri).**
```python
def cases_for_intent(self, intent: str) -> tuple[EvalCase, ...]: ...   # filtra per intent
def fusion_cases(self) -> tuple[EvalCase, ...]: ...                    # == cases_for_intent("both")
```
Le proiezioni IR esistenti (`to_ground_truth`/`kinds`/`rebased`) restano invariate; `rebased` propaga
`intent` (additivo).

---

## 2. Mappa intento → superficie (costante di dominio)

```python
# services/eval/fusion.py (o models.py)
INTENT_SURFACE = {"code": "search_code", "doc": "search_docs", "both": "search_combined"}
```
Costante esplicita (Principio VII): l'`intent` di un caso determina la `search_*` con cui va misurato.

---

## 3. Fusion coverage — entità di report (NUOVE, pure)

```python
@dataclass(frozen=True)
class FusionCaseResult:
    """Esito di copertura fusa di un singolo caso `intent="both"` (REQ-020/022)."""
    query: str
    expected: tuple[str, ...]
    has_doc: bool          # ≥1 risultato DOC pertinente nel top-k
    has_code: bool         # ≥1 risultato CODE pertinente nel top-k
    covered: bool          # has_doc AND has_code
    hit_at_k: bool         # ≥1 path atteso nel top-k (per mostrare REQ-022: hit ma non covered)


@dataclass(frozen=True)
class FusionReport:
    """Aggregato della fusion coverage sul combined (REQ-021).

    Riportato ACCANTO a hit@k/MRR (campo additivo del report esteso), non al posto. Run senza casi
    `both` → coverage 0.0 e `cases=0` (report vuoto onesto, exit 0).
    """
    cases: tuple[FusionCaseResult, ...]
    coverage: float        # covered / cases (0.0 se cases==0)
    cases_count: int
    hit_but_not_covered: int   # quanti casi REQ-022 (hit@k ma manca un tipo) — la lacuna visibile
```

**Regola edge (REQ-020/022, deterministica):** `pertinente` = `r.path ∈ expected_set`; `covered` =
`has_doc AND has_code`; un caso `hit_at_k=True, covered=False` incrementa `hit_but_not_covered`.

---

## 4. Report per-superficie esteso (NUOVO, composizione)

```python
@dataclass(frozen=True)
class SurfaceEvalReport:
    """EvalReport di UNA superficie + la sua etichetta (REQ-010/013)."""
    surface: str               # "search_code" | "search_docs" | "search_combined"
    report: EvalReport         # hit@k/MRR sui casi pertinenti a quella superficie (riuso `evaluate`)


@dataclass(frozen=True)
class FusedEvalReport:
    """Esito completo del run di fusione (069): per-superficie + fusion coverage.

    Additivo: i singoli `EvalReport` sono prodotti da `evaluate` invariato; `fusion` è il passaggio
    puro aggiuntivo sul combined.
    """
    surfaces: tuple[SurfaceEvalReport, ...]   # code, docs, combined
    fusion: FusionReport
    provider: str
```

---

## 5. Baseline per-superficie (estensione `Baseline`)

Due opzioni studiate; **scelta = (B)** per additività massima sul file esistente.

- **(A)** Un nuovo file `eval/fusion_baseline.toml` (come `graph_baseline.toml`). Scartata: la misura è
  **rank-based** sulla stessa suite IR (non set-based come il grafo) → non c'è ragione di un file
  separato; il combined *è* parte dell'eval IR.
- **(B, SCELTA)** Estendo `eval/baseline.toml` con metriche **per-superficie** + fusion coverage:

```python
@dataclass(frozen=True)
class SurfaceBaseline:
    surface: str
    hit_rate: dict[int, float]
    mrr: float


@dataclass(frozen=True)
class FusedBaseline:
    """Baseline per-superficie + fusion coverage (REQ-010). Persistita in eval/baseline.toml,
    additiva al `Baseline` IR esistente (sezioni distinte, il writer preserva entrambe).
    """
    surfaces: tuple[SurfaceBaseline, ...]
    fusion_coverage: float
    queries: int
    provider: str
    recorded_at: str
```

Il `Baseline` IR esistente (hit@k/MRR globale) **resta** per `eval run` corrente; la `FusedBaseline` è la
baseline del run di fusione (`eval run --fused`). Lo schema TOML tiene **entrambe** le sezioni (pattern
preserve-both di FEAT-011, contract `artifacts-toml.md`).

---

## 6. Verdetto di non-regressione per-superficie (riuso meccanismo)

Riuso `MetricDelta`/`RegressionVerdict` esistenti, applicati per-superficie + alla fusion coverage:

```python
@dataclass(frozen=True)
class FusedRegressionVerdict:
    """Esito del gate sul run di fusione (REQ-040).

    `verdict ∈ {"pass","regressed","no-baseline"}`. Una QUALSIASI superficie sotto baseline oltre
    tolleranza, O la fusion coverage sotto baseline oltre tolleranza → "regressed" (exit 1, R-3).
    """
    deltas: tuple[MetricDelta, ...]    # per-superficie hit@k/MRR + "fusion_coverage"
    tolerance: float
    verdict: str

    def exit_code(self) -> int:
        return 1 if self.verdict == "regressed" else 0
```

Funzione pura `compare_fused_to_baseline(report: FusedEvalReport, baseline: FusedBaseline | None,
tolerance: float) -> FusedRegressionVerdict` in `services/eval/regression.py` (estensione).

---

## 7. Servizi (moduli, dove vivono)

| Modulo | Stato | Contenuto |
|---|---|---|
| `services/eval/models.py` | ESTESO | `EvalCase.intent`; `FusionCaseResult`/`FusionReport`/`SurfaceEvalReport`/`FusedEvalReport`/`SurfaceBaseline`/`FusedBaseline`/`FusedRegressionVerdict`; helper su `EvalSuite` |
| `services/eval/suite_io.py` | ESTESO | `_parse_case`/`_serialize_suite` gestiscono `intent` (preservando `[[graph_case]]`); `add_case`/`amend_case` accettano `intent` |
| `services/eval/fusion.py` | **NUOVO** | `fusion_coverage(cases, search_combined_fn, k) → FusionReport` (puro: prende una callable di ricerca); `INTENT_SURFACE` |
| `services/eval/fused_runner.py` | **NUOVO** | `run_fused_evaluation(facade, suite, ks) → FusedEvalReport` (misura le 3 superfici via wrapper `QueryableEngine` + fusion) ; `emit_fused_eval_event` (metrics-only) |
| `services/eval/regression.py` | ESTESO | `compare_fused_to_baseline` |
| `services/eval/baseline_io.py` | ESTESO | load/write della sezione `FusedBaseline` in `eval/baseline.toml` (preserve-both) |

---

## 8. Adattatori-superficie (`QueryableEngine` sul facade)

```python
# fused_runner.py — wrapper minimi, puri (dipendono dal facade già costruito)
class _SurfaceEngine:
    """QueryableEngine che instrada query → facade.search_<surface> (REQ-010/013).

    `evaluate` ne usa solo `provider` + `query`; tre istanze (code/docs/combined) misurano le tre
    superfici con la STESSA macchina (`evaluate` invariato).
    """
    def __init__(self, facade, surface: str, provider: str): ...
    @property
    def provider(self) -> str: ...
    def query(self, query: str, k: int | None = None) -> list[RetrievalResult]:
        return getattr(self._facade, self._surface)(query, k)
```

La fusion coverage usa **direttamente** `facade.search_combined` (per accedere ai `doc_type`), non
l'adattatore (che è per `evaluate`). Entrambi consumano il `RetrievalFacade` costruito da `build_facade`
(Principio XI: la factory è il vehicle).

---

## 9. Factory (composition root)

```python
# composition.py
def build_fused_eval_runner(settings=None):
    """Vehicle per `sertor-rag eval --fused` (069). Riusa `build_facade` (Principio XI),
    cabla osservabilità (_wire_runtime). Espone run_fused(suite, ks)."""
```
`_FusedEvalRunner.run_fused(suite, ks)` costruisce il facade, esegue `run_fused_evaluation`, ritorna il
`FusedEvalReport`. Nessun import di adapter nei servizi.

---

## 10. Settings (manopole)

| Manopola | Env | Default | Uso |
|---|---|---|---|
| `eval_tolerance` | `SERTOR_EVAL_TOLERANCE` | `0.0` | **riuso** — gate non-regressione (anche per-superficie/fusione) |
| `eval_fusion_k` | `SERTOR_EVAL_FUSION_K` | `5` (o `default_k`) | top-k su cui si valuta la fusion coverage (DA-c) |

Le eventuali manopole delle **leve** (FEAT-005/006/007) sono fuori ambito qui (le introducono le loro
feature); se una leva opt-in viene cablata come seam nel run, la sua env va nel template `.env`
dell'installer (corollario installabile).

---

## 11. Invarianti del data-model
- `evaluate`/`EvalReport`/`QueryOutcome` **INVARIATI** (additività su `evaluate`, Principio I/III).
- `EvalCase.intent` ha default `None` → suite esistenti valide (RNF-5/Principio VI).
- Il writer TOML preserva **tutte** le sezioni (`[[case]]` con/senza `intent`, `[[graph_case]]`) — nessun
  drop (DA-d di FEAT-011, riusato).
- Tutte le nuove entità sono **frozen, pure, senza I/O** (Principio I).
- Tipi recuperati letti da `RetrievalResult.doc_type` a runtime → **nessuna doppia etichettatura** del
  tipo nel set (meno deriva).
