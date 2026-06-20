# Phase 1 — Data Model: Valutazione della navigazione del grafo (set-based) (FEAT-011)

**Branch**: `066-valutazione-navigazione-grafo` · **Date**: 2026-06-20 · **Spec**:
[`spec.md`](spec.md) · **Research**: [`research.md`](research.md)

Tutte le entità nuove sono **frozen dataclass pure** (zero I/O), additive a `services/eval/models.py`
(RNF-1/RNF-4). Nessuna nuova **porta** Protocol: la navigazione riusa `CodeGraph` (`domain/ports.py`),
l'identità di nodo riusa `SymbolHit.ref` (`domain/entities.py`). Il `domain` resta privo di SDK
(Principio I). Le entità della suite/baseline di navigazione sono **dato versionato del progetto**
(`eval/`, RNF-5), mai segreti, mai output rigenerabile.

---

## 1. Riuso senza modifiche (esistente, NON toccato)

| Entità | Modulo | Ruolo qui |
|---|---|---|
| `SymbolHit` (`path`,`line`,`kind`,`qualname`,`ref`) | `domain/entities.py` | `ref = path#qualname` = identità stabile del nodo (decisione D). |
| porta `CodeGraph` (`find_symbol`/`who_calls`/`exists`/…) | `domain/ports.py` | navigazione (riuso, **nessun** metodo nuovo). |
| `GraphNotFoundError` | `domain/errors.py` | grafo non costruito al run → fallimento azionabile (REQ-013). |
| `EvalCase` / `EvalSuite.cases` (IR) | `services/eval/models.py` | **invariati** (i `[[case]]` path-based coesistono, RNF-4). |
| `evaluate` / `EvalReport` / `QueryableEngine` | `engines/evaluation.py` | **invariati** (IR rank-based; il nuovo oracolo è parallelo, non passa di qui). |

---

## 2. Entità NUOVE (additive a `services/eval/models.py`)

### 2.1 `GraphCase` — il caso di navigazione *(artefatto-dato del progetto, REQ-001/003)*
```python
@dataclass(frozen=True)
class GraphCase:
    relation: str                  # MVP: "who_calls" | "defines" (REQ-001/005)
    target: str                    # simbolo target (nome, es. "build_facade")
    expected: tuple[str, ...]      # insieme atteso di `ref` (path#qualname), come tupla ordinata
```
- `relation` ∈ insieme MVP supportato (`who_calls`, `defines`); fuori insieme → `GraphSuiteValidationError`
  che rifiuta la suite (REQ-005).
- `expected` è un **insieme** semanticamente (l'ordine non conta per la metrica) ma è memorizzato come
  **tupla ordinata** per un TOML diffabile stabile; ogni elemento è un `ref` (`path#qualname`), non un nome
  nudo (REQ-003). `expected` può essere **vuoto** in un caso (atteso «nessun chiamante») — legittimo, **non**
  un errore di validazione (asimmetria deliberata vs gli IR-case che esigono ≥1 path).
- La validazione (relazione presente+supportata, `target` non vuoto, `expected` ben formato) è nel **loader**
  (`GraphSuiteValidationError` che **nomina il caso**), non nel costruttore (REQ-004).
- Progettazione future-proof (DA-b): `expected` è una tupla di **stringhe** → la stessa entità accoglierà
  `related_docs` (elemento = path-documento) senza cambiare schema.

### 2.2 `SetMetric` — metrica a insiemi di un caso *(REQ-020/023)*
```python
@dataclass(frozen=True)
class SetMetric:
    precision: float               # |got ∩ expected| / |got|     (got vuoto → 1.0 se expected vuoto, else 0.0)
    recall: float                  # |got ∩ expected| / |expected| (expected vuoto → 1.0)
    f1: float                      # media armonica P,R            (P=R=0 → 0.0)
    exact: bool                    # got == expected (per il gate match-esatto opzionale, REQ-022)
    got: tuple[str, ...]           # insieme navigato (ordinato)
    expected: tuple[str, ...]      # insieme atteso (ordinato)
    missing: tuple[str, ...]       # expected − got (REQ-023)
    extra: tuple[str, ...]         # got − expected (REQ-023)
```
- Convenzioni dei casi-limite (entrambi vuoti → P=R=F1=1.0, `exact=True`; `expected` vuoto & `got` non vuoto
  → P=0/R=1/F1=0; `got` vuoto & `expected` non vuoto → P=1/R=0/F1=0) sono **deterministiche** (REQ-015).
- **Nessun** rank, **nessun** @k (Won't): la metrica è puramente set-based (REQ-020).

### 2.3 `GraphCaseResult` — esito per-caso
```python
@dataclass(frozen=True)
class GraphCaseResult:
    relation: str
    target: str
    metric: SetMetric
```

### 2.4 `GraphEvalReport` — esito del run *(REQ-021/030)*
```python
@dataclass(frozen=True)
class GraphEvalReport:
    cases: tuple[GraphCaseResult, ...]
    mean_precision: float          # media sui casi
    mean_recall: float             # media sui casi (metrica secondaria nel report)
    mean_f1: float                 # media sui casi (metrica PRIMARIA del gate, DA-a)
    by_relation: dict[str, float]  # F1 medio per relazione (diagnosi)
    cases_count: int
```
- Resa in **sezione distinta** dalla IR (`EvalReport` hit@k/MRR) nel report umano e JSON (REQ-030).

### 2.5 `GraphBaseline` — pavimento metrico di navigazione *(REQ-031, separato dalla IR)*
```python
@dataclass(frozen=True)
class GraphBaseline:
    mean_f1: float
    mean_recall: float             # secondaria, salvata per diagnosi
    mean_precision: float          # secondaria
    cases: int
    recorded_at: str               # ISO-8601 UTC
```
- Persistita in `eval/graph_baseline.toml` (file **distinto** da `eval/baseline.toml`, DA-a/REQ-031).
  Scritta/aggiornata **solo** su `--record-baseline` (accettazione esplicita, REQ-040/044-gemello).
  Assente → `load_graph_baseline` ritorna `None` (assenza legittima, gate passa, REQ-033).

### 2.6 `GraphMetricDelta` / `GraphRegressionVerdict` — gate *(REQ-032/033)*
```python
@dataclass(frozen=True)
class GraphMetricDelta:
    name: str                      # "mean_f1" (gate) | "mean_recall" | "mean_precision" (informativi)
    current: float
    baseline: float
    delta: float                   # current - baseline
    regressed: bool                # delta < -tolerance  (solo "mean_f1" gate-a per default)

@dataclass(frozen=True)
class GraphRegressionVerdict:
    verdict: str                   # "pass" | "regressed" | "no-baseline"
    deltas: tuple[GraphMetricDelta, ...]
    tolerance: float
    def exit_code(self) -> int:    # 0 pass/no-baseline, 1 regressed
        return 1 if self.verdict == "regressed" else 0
```
- Gemello strutturale di `MetricDelta`/`RegressionVerdict` IR; il **gate scatta sul solo `mean_f1`**
  (DA-a); `mean_recall`/`mean_precision` figurano come delta **informativi** (mai `regressed=True`).

### 2.7 `RefValidation` — validazione write-time dei `ref` attesi *(REQ-042)*
```python
@dataclass(frozen=True)
class RefValidation:
    checked: tuple[str, ...]
    unverifiable: tuple[str, ...]  # ref che il grafo non conferma (nominati, non scartati silenziosi)
    graph_available: bool          # False se grafo non costruito (degrado onesto)
```
- Gemello di `PathValidation` (065), ma sul **grafo** invece che sull'indice: un `ref` atteso è
  *verificabile* se compare tra i `ref` derivabili dal grafo per il suo simbolo. `graph_available=False`
  (grafo assente) → degrado onesto: nessun `unverifiable` rivendicato, il chiamante avvisa.

---

## 3. Estensione di `EvalSuite` (convivenza nello stesso file — DA-d)

`eval/suite.toml` ospita **due** array di tabelle: `[[case]]` (IR, invariato) e `[[graph_case]]` (nuovo).
Per preservare **entrambe** le sezioni a ogni scrittura (Principio VI, non-distruttività), il modello che
il writer serializza deve contenerle **entrambe**:

```python
@dataclass(frozen=True)
class EvalSuite:
    cases: tuple[EvalCase, ...] = ()          # invariato (IR)
    graph_cases: tuple[GraphCase, ...] = ()   # NUOVO additivo, default () → suite IR-only invariata
```
- **Additivo non-breaking:** `graph_cases` ha default `()`; ogni costruzione esistente di `EvalSuite` resta
  valida; `to_ground_truth()`/`kinds()`/`rebased()` IR **invariati** (operano solo su `cases`).
- Il **loader** (`load_suite`) legge **entrambi** gli array (`data.get("case")` e `data.get("graph_case")`);
  il **writer** (`write_suite`/`_serialize_suite`) emette **prima** i `[[case]]` poi i `[[graph_case]]` nello
  stesso testo → scrivere un graph-case non cancella i case IR e viceversa (round-trip validato →
  `SuiteWriteError`, gemello esistente).
- `add_graph_case`/`amend_graph_case` (writer dedicati, gemelli di `add_case`/`amend_case`): idempotenti su
  `(relation, target)`, ordine stabile, preservano i `[[case]]` IR.

---

## 4. Servizi / funzioni (NUOVI in `services/eval/`)

| Funzione/modulo | Firma (essenziale) | Purezza | REQ |
|---|---|---|---|
| `graph_eval.evaluate_graph_case` | `(navigated: frozenset[str], expected: frozenset[str]) -> SetMetric` | pura | REQ-020/023 |
| `graph_eval.evaluate_graph_suite` | `(results: list[GraphCaseResult]) -> GraphEvalReport` | pura | REQ-021 |
| `graph_eval.navigate` | `(graph: CodeGraph, relation: str, target: str) -> frozenset[str]` | dipende dalla **porta** `CodeGraph` | REQ-011/012/014 |
| `graph_runner.run_graph_evaluation` | `(graph: CodeGraph, suite: EvalSuite) -> GraphEvalReport` | dipende dalla porta | REQ-010/015 |
| `graph_runner.emit_graph_eval_event` | `(report, verdict) -> None` (metrics-only) | I/O log | REQ-050 |
| `graph_runner.validate_refs` | `(graph, refs) -> RefValidation` | dipende dalla porta | REQ-042 |
| `graph_regression.compare_graph_to_baseline` | `(report, baseline\|None, tolerance) -> GraphRegressionVerdict` | pura | REQ-032/033 |
| `graph_suite_io` (estensione `suite_io`) | `add_graph_case`/`amend_graph_case`/`load_suite`(esteso) | I/O file | REQ-002/004/005 |
| `graph_baseline_io` | `load_graph_baseline`/`write_graph_baseline` | I/O file | REQ-031/044 |

- **`navigate` mapping relazione→porta (N2 research):** `who_calls`→`graph.who_calls(target)`;
  `defines`→`graph.find_symbol(target)`; entrambi → `frozenset(hit.ref ...)`. Simbolo assente → `frozenset()`
  (REQ-014). Relazione fuori MVP → la suite è già stata rifiutata dal loader (REQ-005); difesa in profondità
  qui = `ValueError`/`GraphSuiteValidationError`.
- **Nessun import di composition/adapter** nei moduli di servizio: la concretizzazione di `CodeGraph` è
  **solo** in composition (`build_graph_service`), Principio I/XI.

---

## 5. Composition (factory, l'UNICO posto che conosce i concreti)

| Factory | Ruolo |
|---|---|
| `build_graph_eval_runner(settings)` | costruisce il grafo via **`build_graph_service`** (riuso) e ritorna un `_GraphEvalRunner` che esegue `run_graph_evaluation` (vehicle, Principio XI). Wires observability (`_wire_runtime`). |
| `_GraphEvalRunner.run(suite)` | naviga + scora; richiede il grafo costruito (`graph.exists(corpus)` → altrimenti `GraphNotFoundError` azionabile, REQ-013). |

- **Riuso** di `build_graph_service` (esistente): nessuna nuova logica di costruzione del grafo.
- `build_graph_eval_runner` è una factory **consumer-entry** → applica `_wire_runtime` come le altre
  (feature 041, consumo sicuro via vehicle).

---

## 6. Settings (manopole — default SOLO qui, Principio VIII)

| Campo | Env | Default | Uso |
|---|---|---|---|
| `graph_eval_tolerance` | `SERTOR_GRAPH_EVAL_TOLERANCE` | `0.0` | tolleranza assoluta del gate su `mean_f1` (DA-a/REQ-032). |
| `graph_eval_exact` | `SERTOR_GRAPH_EVAL_EXACT` | `false` | abilita il gate **match-esatto** opzionale (REQ-022): un caso con `exact=False` fa fallire il run. |

- `eval_dir` (esistente) ospita anche `graph_baseline.toml` (nessun campo nuovo per il path: `eval_dir /
  "graph_baseline.toml"`). Entrambe le manopole **commentate** nei template `.env` dell'installer (REQ-061).
- A leve spente (`exact=false`, nessuna baseline): comportamento e costo **identici a oggi** (RNF-1) — il
  comando esiste ma non altera nulla finché non lo invochi su una suite con `graph_case`.

---

## 7. Errori di dominio (NUOVI, additivi — Principio IV)

| Errore | Quando | Exit |
|---|---|---|
| `GraphSuiteValidationError(index, msg)` | `[[graph_case]]` privo di `relation`/`target`/`expected`, o relazione non supportata, che **nomina il caso** (REQ-004/005) | 1 |
| `GraphRegressionDetected(verdict)` | `mean_f1` sotto baseline oltre tolleranza (gate, REQ-032), o match-esatto fallito con `exact` on (REQ-022) | 1 |

- Riuso degli esistenti: `GraphNotFoundError` (grafo non costruito al run, REQ-013), `SuiteNotFoundError`
  (suite assente), `SuiteWriteError` (round-trip writer fallito). Tutti `SertorError` → exit 1 nel `main`.
- `GraphSuiteValidationError` può **riusare** `SuiteValidationError` se la forma del messaggio basta;
  l'entità separata è preferita per nominare la relazione/target offendente in modo specifico (giudizio
  implementativo, non-breaking in entrambi i casi).

---

## Invarianti del modello
- **Additività (I/III/RNF-1/RNF-4):** entità nuove con default neutri; `EvalSuite.graph_cases` default `()`;
  IR (`EvalCase`/`evaluate`/`EvalReport`/baseline IR) **invariato**. A capacità non usata, zero overhead.
- **Identità per `ref` (D/REQ-003):** chiave d'insieme = `path#qualname` (da `SymbolHit.ref`), mai nome nudo.
- **Set-based puro (REQ-020, Won't @k/rank):** `SetMetric`/`GraphEvalReport` non portano rank né @k.
- **Determinismo (REQ-015):** `navigate` ordina i `ref` (l'adapter già ordina); le metriche sono funzione
  pura degli insiemi → due run identici.
- **Privacy (RNF-3):** nomi/path/insiemi vivono **solo** nel dato versionato e nel report umano locale; mai
  nell'evento `graph_eval` (metrics-only).
- **Nessuna nuova porta (III):** la navigazione riusa `CodeGraph`; suite/baseline sono **dati** (single
  consumer), come `IndexManifest`/`Baseline` IR.
