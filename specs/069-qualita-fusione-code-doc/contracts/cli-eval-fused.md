# Contract — CLI `sertor-rag eval` esteso per la fusione (FEAT-003)

Estensione **additiva** del gruppo `eval` esistente (065): un nuovo modo `--fused` su `eval run` e il
campo `--intent` su `eval add-case`. Thin consumer: parsing → composition factory
(`build_fused_eval_runner`) → misura per-superficie + fusion coverage (core) → `output.py`. **Nessuna**
logica di metrica nel CLI (Principio I). Stile/exit code ereditati da `cli/__main__.py`. **Niente LLM**
in alcun percorso (RNF-3).

`eval run` SENZA `--fused` resta **identico** a oggi (additività, SC-009): misura hit@k/MRR globale +
gate IR. `graph-eval` invariato.

## Exit codes
| Code | Significato |
|---|---|
| `0` | successo (run pass / nessuna regressione / no-baseline / record-baseline) |
| `1` | `SertorError` su stderr: `SuiteNotFoundError`, `SuiteValidationError`, `SuiteWriteError`, `RegressionDetected`, `ConfigError` (backend) |
| `2` | usage error (argparse) |

---

## `sertor-rag eval run --fused`

```
sertor-rag eval run --fused [--record-baseline] [-k 1,3,5,10]
                    [--corpus C] [--json] [-v] [--log-json] [--log-config F]
```

| Flag | Effetto |
|---|---|
| `--fused` | misura **per-superficie** (`search_code`/`search_docs`/`search_combined`) + **fusion coverage** sui casi `intent="both"`, e gate per-superficie/fusione. Senza `--fused` → comportamento odierno invariato. |
| `--record-baseline` | registra/aggiorna la sezione `FusedBaseline` in `eval/baseline.toml` (per-superficie + fusion coverage). Senza il flag la baseline non si tocca. |
| `-k` | k per hit@k (default da Settings: 1,3,5,10). La fusion coverage usa `SERTOR_EVAL_FUSION_K`. |
| `--json` | report come oggetto JSON (equivalenza informativa col testo). |

### Comportamento
1. `_resolve_settings` + `_check_backend` + `enable_observability` (pattern esistente).
2. Carica `eval/suite.toml` via `load_suite` (esteso): legge il campo `intent` dei `[[case]]`. Suite
   assente → `SuiteNotFoundError` (exit 1). `intent` non valido → `SuiteValidationError` che **nomina il
   caso** (exit 1, REQ-004).
3. **Nessun caso con `intent`** → messaggio azionabile («aggiungi casi NL con `eval add-case --intent
   code|doc|both`, o usa la skill `eval-suite-author`») e report vuoto onesto (exit 0) — non uno zero
   ingannevole sul gate.
4. Costruisce il facade via `build_fused_eval_runner` (riusa `build_facade`, Principio XI).
5. Misura ogni superficie con la `search_*` corrispondente, **solo** sui casi di quell'`intent`, riusando
   `evaluate` (3 `EvalReport` → `SurfaceEvalReport`). REQ-010/013.
6. Calcola la **fusion coverage** sui casi `intent="both"` via `search_combined` diretto (legge i
   `doc_type` top-k): `covered = has_doc AND has_code` (REQ-020). REQ-021/022.
7. Baseline `FusedBaseline` presente (e non `--record-baseline`): `compare_fused_to_baseline(…,
   eval_tolerance)`. **Una qualsiasi** superficie sotto baseline oltre tolleranza, **o** la fusion
   coverage sotto baseline oltre tolleranza → `RegressionDetected` (exit 1, REQ-040/R-3). Entro
   tolleranza → exit 0.
8. `--record-baseline`: scrive la sezione `FusedBaseline` (accettazione esplicita), exit 0. **Preserva**
   il `Baseline` IR esistente e i `[[case]]`/`[[graph_case]]`.
9. Emette **un** evento `fused_eval` metrics-only (contract `event-fused-eval.md`).
10. Determinismo: due run a parità di indice+suite → metriche identiche (REQ-041, SC-004).

### Output umano (esempio)
```
fused eval  cases: code=8 docs=8 fusion=6  provider=ollama:nomic

per-surface (hit-rate@k / MRR):
  search_code      @1=0.50 @3=0.75 @5=0.88  MRR=0.64
  search_docs      @1=0.62 @3=0.88 @5=0.88  MRR=0.73
  search_combined  @1=0.55 @3=0.82 @5=0.91  MRR=0.69

fusion coverage: 0.50  (3/6 covered;  2 hit@k but NOT covered ← one type drowns the other)
  [covered] requirements of FEAT-003 and where implemented   doc+code
  [GAP    ] how the hybrid engine fuses BM25 and dense        doc only  (missing CODE)
  …

non-regression: PASS (tolerance=0.00)
  search_code MRR Δ=+0.01   search_docs MRR Δ=0.00   fusion_coverage Δ=+0.03
```

---

## `sertor-rag eval add-case --intent`

```
sertor-rag eval add-case --query Q --expected P[,P…]
                         [--kind K] [--intent code|doc|both] [--confirm] [--corpus C] [--json]
```

- Estende `add-case` esistente con `--intent` (`choices=[code,doc,both]`; usage error exit 2 fuori
  insieme). Persiste un `[[case]]` con `intent` in `eval/suite.toml` (writer non-distruttivo/idempotente
  su `query`, REQ-002), **preservando** `[[graph_case]]` e i casi senza intent (DA-d).
- Validazione write-time invariata (065): un path atteso assente dall'indice → warning + `--confirm`
  (o conferma TTY); senza conferma non scrive (exit 1 azionabile, nessuno stato parziale).
- `amend-case` accetta `--intent` per ri-tipizzare un caso esistente (percorso di ri-authoring, giudizio).

---

## Invarianti del contratto
- **Principio XI:** ogni accesso al retrieval passa da `build_fused_eval_runner`→`build_facade` (il CLI è
  il vehicle); la skill `eval-suite-author` (esterna) passa dai sottocomandi (`eval add-case --intent`,
  `eval validate-path`), **mai** importa `sertor_core`.
- **Additività (RNF-1):** `eval run` senza `--fused`, `graph-eval`, index/search e costo **identici a
  oggi**; il campo `intent` assente lascia i casi IR invariati.
- **Riportata accanto, non al posto (REQ-042/SC-008):** la fusion coverage è una metrica **aggiuntiva**;
  hit@k/MRR restano.
- **Equivalenza informativa** umano↔JSON (invariante CLI esistente).
- **Niente LLM nel run** (RNF-3); l'unico modello è l'embedder.
