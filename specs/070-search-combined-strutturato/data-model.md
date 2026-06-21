# Phase 1 — Data Model: `search_combined` strutturato (Tempo 2 FEAT-003)

**Branch**: `070-search-combined-strutturato` · **Spec**: [`spec.md`](./spec.md) ·
**Research**: [`research.md`](./research.md)

Le entità sono **additive** salvo il cambio di **tipo di ritorno** di `search_combined` (breaking
change volontario, §6). Niente SDK nel `domain` (Principio I); frozen dataclass coerenti con le entità
esistenti (Principio VII).

---

## §1. Nuova entità di dominio — `FusedResults`

**Posizione:** `src/sertor_core/domain/entities.py` (accanto a `RetrievalResult`).

```python
@dataclass(frozen=True)
class FusedResults:
    """Structured return of `search_combined` (070): the two labelled flows of the fusion.

    The mission's differentiator made structural: `docs` (the *why*) and `code` (the *what*) are
    returned SIDE BY SIDE, each rank-ordered with its OWN top-k (separate budget). There is no
    cross-type blended ranking — code/doc scores are incommensurable (the root cause of 069's 0.17
    fusion coverage), so they are never merged by score. `flatten()` interleaves the two for the
    consumer that wants a single list, deterministically (never re-introducing the score merge).
    Pure data, no SDK (Principio I)."""

    docs: tuple[RetrievalResult, ...] = ()
    code: tuple[RetrievalResult, ...] = ()

    def flatten(self) -> list[RetrievalResult]:
        """Deterministic single list: interleave by rank (docs[0], code[0], docs[1], …); leftovers
        of the longer list appended in order (DA-c). Empty + empty → []."""
        out: list[RetrievalResult] = []
        for i in range(max(len(self.docs), len(self.code))):
            if i < len(self.docs):
                out.append(self.docs[i])
            if i < len(self.code):
                out.append(self.code[i])
        return out
```

| Campo | Tipo | Note |
|---|---|---|
| `docs` | `tuple[RetrievalResult, ...]` | risultati `doc_type=DOC`, rank-ordered, **proprio** top-k (default `()`) |
| `code` | `tuple[RetrievalResult, ...]` | risultati `doc_type=CODE`, rank-ordered, **proprio** top-k (default `()`) |

| Metodo | Firma | Contratto |
|---|---|---|
| `flatten()` | `() -> list[RetrievalResult]` | interleave per rank, deterministico; FR-002/SC-003 |

**Invarianti.**
- Forma **sempre strutturata**, anche con una lista vuota (edge case spec): indice senza codice →
  `code=()` ma la coppia esiste; query puramente doc → idem.
- `flatten()` **puro/deterministico**: stesso `FusedResults` → stessa lista, sempre (nessun
  float-compare, nessuna rete).
- **Nessun metadato** (query/provider/elapsed) sull'entità (YAGNI, Principio III); l'osservabilità
  resta nei `log_event` della facade. Estensione futura = campo additivo con default.

---

## §2. Cambio di contratto — `RetrievalFacade.search_combined`

**Posizione:** `src/sertor_core/services/retrieval.py:166`.

| | Prima (oggi) | Dopo (070) |
|---|---|---|
| Firma | `search_combined(query, k=None) -> list[RetrievalResult]` | `search_combined(query, k=None) -> FusedResults` |
| Budget | condiviso (`_search(..., "both")`, top-k unico) | **separato** (top-k `docs` + top-k `code`) |
| Composizione | una lista ranked blended per score | due liste etichettate, ciascuna rank-ordered |

**Comportamento (research DA-b).** La facade ottiene `docs` e `code` riusando il **percorso mono-tipo
esistente** con il rispettivo filtro:
- `docs = _search(query, k, "doc")` (lo stesso percorso di `search_docs`)
- `code = _search(query, k, "code")` (lo stesso percorso di `search_code`)

ed emette `FusedResults(docs=tuple(docs), code=tuple(code))`. `search_code`/`search_docs` restano
identici (FR-003): l'unica novità è che il combined li **compone**.

**Fan-out multi-corpus (feature 010), conservato.** Quando ci sono `extra_collections`, ogni lista
(`docs`/`code`) fa il fan-out con il **proprio** filtro `doc_type` e il proprio top-k sulle collezioni
in `_available_targets()`; la policy di degrado (`no_index` warning) e `ProviderMismatchError`
restano invariate (cambia solo che si filtra per tipo invece di blendare). Le porte non cambiano.

**Logging (Principio IX), invariato per costruzione.** I due `_search` per tipo emettono i propri
eventi `retrieve` (collection/provider/doc_type/k/results/elapsed) come oggi per `search_docs`/
`search_code`: nessun evento perso, nessun nuovo evento richiesto sul percorso facade.

---

## §3. Metrica di fusion coverage — adattata alle due liste

**Posizione:** `src/sertor_core/services/eval/fusion.py` (`fusion_coverage`).

| | Prima (069) | Dopo (070) |
|---|---|---|
| `search_fn` | `Callable[[str,int], list[RetrievalResult]]` (lista blended) | `Callable[[str,int], FusedResults]` (la coppia) |
| `has_doc` | `any(r.doc_type==DOC for r in relevant)` su **una** lista | doc pertinente nella **lista `docs`** (top-k) |
| `has_code` | `any(r.doc_type==CODE for r in relevant)` su **una** lista | code pertinente nella **lista `code`** (top-k) |
| `covered` | `has_doc AND has_code` | `has_doc AND has_code` (**invariato concettualmente**) |
| `hit_at_k` | path atteso in `top_k` | path atteso nell'**unione** delle due liste (≡ `flatten()`) |

```python
def fusion_coverage(cases, search_fn, k) -> FusionReport:
    for case in cases:
        expected = set(case.expected)
        fused = search_fn(case.query, k)           # FusedResults
        has_doc  = any(r.path in expected for r in fused.docs)
        has_code = any(r.path in expected for r in fused.code)
        covered  = has_doc and has_code
        hit_at_k = any(r.path in expected for r in fused.flatten())
        ...
```

`FusionCaseResult`/`FusionReport` (`models.py`) **non cambiano forma** (query/expected/has_doc/
has_code/covered/hit_at_k · coverage/cases_count/hit_but_not_covered): cambia solo **da dove**
provengono `has_doc`/`has_code`. Più semplice e più fedele al contratto (REQ-020/FR-006).

---

## §4. Superfici IR ranked del fused-runner — da tre a due

**Posizione:** `src/sertor_core/services/eval/fused_runner.py` (`_SURFACES`, `run_fused_evaluation`).

| | Prima (069) | Dopo (070) |
|---|---|---|
| `_SURFACES` | `("search_code","search_docs","search_combined")` | `("search_code","search_docs")` |
| `search_combined` come superficie IR | misurata con `evaluate` (hit@k/MRR) | **rimossa** — misurata SOLO da fusion coverage |
| `FusedEvalReport.surfaces` | 3 `SurfaceEvalReport` | 2 `SurfaceEvalReport` |
| fusion coverage | `fusion_coverage(..., facade.search_combined, ...)` | `fusion_coverage(..., facade.search_combined, ...)` (ora la coppia) |

**Rationale (research §«superficie IR ranked»).** `evaluate` richiede una lista ranked unica
(`QueryableEngine.query → list[RetrievalResult]`); `search_combined` non la fornisce più. Il suo
ranking cross-tipo era la metrica sbagliata (score incommensurabili). La **fusion coverage** è ora
l'unica e corretta misura della superficie fusa (Principio XII — fix the cause). `_SurfaceEngine`
resta com'è per `search_code`/`search_docs`; **non** wrappa più `search_combined`.

**Evento `fused_eval` (`emit_fused_eval_event`).** `cases.both = report.fusion.cases_count` resta;
`surface_mrr`/`surface_hit3` ora hanno **due** chiavi (`search_code`/`search_docs`) invece di tre —
la cardinalità resta **chiusa** (insieme noto di superfici), metrics-only, nessun testo libero
(Principio IX, gemello OTel 061; contratto invariato salvo il set di chiavi). Vedi
`contracts/event-fused-eval.md`.

---

## §5. Baseline fusa — re-baseline (forma invariata, contenuto nuovo)

**Posizione:** sezione `[fused_baseline]` di `eval/baseline.toml`;
`FusedBaseline`/`SurfaceBaseline` in `models.py`; writer in `services/eval/baseline_io.py`.

| | Prima | Dopo |
|---|---|---|
| `[[fused_baseline.surface]]` | 3 voci (code/docs/**combined**) | **2 voci** (code/docs) |
| `fusion_coverage` | `0.1667` | **ri-registrato** (> 0.17 atteso, FR-007) |
| `FusedBaseline` forma | tuple di superfici + fusion_coverage + … | **invariata** (la tuple avrà 2 elementi) |

`_fused_baseline_from` (CLI) itera `report.surfaces` (ora due): nessuna modifica strutturale, solo il
numero di superfici cambia. La **ri-registrazione** è un **passo operativo del piano**
(`--record-baseline` dopo il refactor su Azure-large), non del data-model. La baseline IR `[baseline]`
(per-superficie code-graph/hit@k del 065/066) **non è toccata** (preserve-both writer, RNF-5/SC-005).

---

## §6. Serializzazione (MCP/CLI) — DA-d

**MCP** (`src/sertor_mcp/server.py`): il tool `search_combined` ritorna
`{"docs": [_fmt(r) …], "code": [_fmt(r) …]}` (era `list[dict]`). `_fmt` invariato (formato citabile
`path#chunk`). Vedi `contracts/mcp-search-combined.md`.

**CLI** (`src/sertor_core/cli/output.py`, `format_search_results`): per il combined, due sezioni
etichettate (`docs:` / `code:`), ciascuna resa con la logica esistente; in `--json`,
`{"docs": [...], "code": [...]}`. `search_code`/`search_docs` restano una sezione unica. Vedi
`contracts/cli-search-combined.md`.

---

## Diagramma dei tipi (delta)

```
RetrievalResult            (invariato)
FusedResults (NEW)         docs: tuple[RetrievalResult,...]
  └─ flatten()             code: tuple[RetrievalResult,...]
                              ↑ ritorno NUOVO di RetrievalFacade.search_combined

FusionReport / FusionCaseResult   (forma invariata; sorgente has_doc/has_code = le due liste)
FusedEvalReport.surfaces          (3 → 2 SurfaceEvalReport)
FusedBaseline.surfaces            (3 → 2 SurfaceBaseline; fusion_coverage ri-registrato)
```

## Tracciabilità entità → requisiti

| Entità / cambiamento | Requisiti |
|---|---|
| `FusedResults(docs, code)` | FR-001, SC-001, Key Entities «Risultato fuso strutturato» |
| `flatten()` interleave | FR-002, SC-003, Edge Cases |
| `search_code`/`search_docs` invariati | FR-003, SC-002 |
| fusion coverage sulle due liste | FR-006, SC-004/SC-009, REQ-020/021/022 |
| superfici IR 3→2 + fusion coverage come misura del combined | FR-006, research §superficie |
| re-baseline `[fused_baseline]` | FR-007, SC-005 |
| serializzazione MCP/CLI etichettata | FR-005, SC-007 |
| determinismo / vehicle | FR-009, SC-008, RNF-3 |
| deviazione additività circoscritta | RNF-1, SC-010 |
