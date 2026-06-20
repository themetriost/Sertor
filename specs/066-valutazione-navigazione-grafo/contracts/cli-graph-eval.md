# Contract — CLI `sertor-rag graph-eval` (FEAT-011)

Superficie **deterministica** della valutazione a insiemi della navigazione del grafo (vehicle,
Principio XI). Thin consumer: parsing → composition factory (`build_graph_eval_runner`) → navigatore +
metriche set-based (core) → `output.py`. **Nessuna** logica di navigazione/metrica nel CLI (Principio I).
Stile, pattern argparse (sub-subparser + `set_defaults(handler=…)`) ed exit code ereditati da
`cli/__main__.py` (gruppo `eval` esistente). **Niente LLM** in alcun percorso (RNF-2).

Gruppo **separato** da `eval` (IR): semantica e baseline diverse (insiemi vs rank/@k), report in **sezione
distinta** (REQ-030). Vedi research §N5.

## Exit codes
| Code | Significato |
|---|---|
| `0` | successo (run pass / nessuna regressione / no-baseline / validate-ref) |
| `1` | `SertorError` su stderr: `GraphSuiteValidationError`, `SuiteNotFoundError`, `SuiteWriteError`, `GraphRegressionDetected`, `GraphNotFoundError` |
| `2` | usage error (argparse) |

---

## `sertor-rag graph-eval run`

```
sertor-rag graph-eval run [--record-baseline] [--exact]
                          [--corpus C] [--json] [-v] [--log-json] [--log-config F]
```

| Flag | Effetto |
|---|---|
| `--record-baseline` | registra/aggiorna `eval/graph_baseline.toml` con le metriche correnti (REQ-031/044-gemello). Senza il flag la baseline non si tocca. |
| `--exact` | abilita il gate **match-esatto** (REQ-022): un caso con `got != expected` fa fallire il run (override di `SERTOR_GRAPH_EVAL_EXACT`). |
| `--json` | report come oggetto JSON (equivalenza informativa col testo). |

### Comportamento
1. `_resolve_settings` + `_check_backend` + `enable_observability` (pattern esistente).
2. Carica `eval/suite.toml` via `load_suite` (esteso): legge i `[[graph_case]]`. Suite assente →
   `SuiteNotFoundError`; **nessun `[[graph_case]]`** → messaggio azionabile («crea casi di navigazione con
   `graph-eval add-case`») e exit 0 con report vuoto onesto (non uno zero ingannevole su un gate).
   `[[graph_case]]` malformato o relazione non supportata → `GraphSuiteValidationError` (exit 1, nomina il
   caso, REQ-004/005).
3. Costruisce il grafo via `build_graph_eval_runner` (riusa `build_graph_service`, Principio XI). **Grafo
   non costruito** (`graph.exists(corpus)` False) → `GraphNotFoundError` (exit 1, «costruisci prima
   l'indice», REQ-013).
4. Per ogni `[[graph_case]]`: naviga (`who_calls`→chiamanti, `defines`→definizioni), confronta gli
   **insiemi** di `ref`, calcola `precision`/`recall`/`F1` + `missing`/`extra` (REQ-011/012/020/023). Target
   assente dal grafo → insieme navigato vuoto, scorato senza errore (REQ-014).
5. Aggrega: `mean_precision`/`mean_recall`/`mean_f1` + `by_relation` (REQ-021).
6. Con `--exact` (o `SERTOR_GRAPH_EVAL_EXACT`): un caso non `exact` → `GraphRegressionDetected` (exit 1,
   REQ-022).
7. Baseline presente (e non `--record-baseline`): `compare_graph_to_baseline(…, graph_eval_tolerance)`. Gate
   sul **`mean_f1`** (DA-a): `mean_f1 < baseline.mean_f1 - tolerance` → `GraphRegressionDetected` (exit 1,
   REQ-032). Entro tolleranza → exit 0. `mean_recall`/`mean_precision` mostrati come delta informativi.
8. `--record-baseline`: scrive `eval/graph_baseline.toml` (accettazione esplicita, REQ-044-gemello), exit 0.
   **NON** tocca mai gli `expected` dei casi (DA-c: re-record = solo pavimento metrico).
9. Emette **un** evento `graph_eval` metrics-only (contract `event-graph-eval.md`).
10. Determinismo: due run a parità di grafo+suite → metriche identiche (REQ-015/SC-001).

### Output umano (esempio)
```
graph navigation eval  cases=6
mean_f1=0.83  mean_recall=0.90  mean_precision=0.79
by-relation: who_calls=0.81  defines=0.86
[exact] defines    build_facade        P=1.00 R=1.00 F1=1.00
[part ] who_calls  build_graph_service P=0.75 R=1.00 F1=0.86  +extra: src/.../x.py#Y
[miss ] who_calls  EmbeddingProvider   P=1.00 R=0.50 F1=0.67  -missing: src/.../z.py#W
…
non-regression: PASS (tolerance=0.00)  mean_f1 Δ=+0.02  mean_recall Δ=+0.01
```

---

## `sertor-rag graph-eval add-case`

```
sertor-rag graph-eval add-case --relation who_calls|defines --target T
                               --expected REF[,REF…] [--confirm] [--corpus C] [--json]
```

- Persiste un `[[graph_case]]` in `eval/suite.toml` (writer TOML, non-distruttivo/idempotente su
  `(relation, target)`, REQ-002/041), **preservando i `[[case]]` IR esistenti** (DA-d).
- **Validazione write-time (REQ-042):** ogni `ref` atteso è verificato contro il **grafo** (`validate_refs`).
  Un `ref` che il grafo non conferma → **warning** che lo **nomina** e richiede `--confirm` (o conferma
  interattiva su TTY) prima di scrivere. Senza conferma: non scrive, exit 1 azionabile (nessuno stato
  parziale).
- Grafo non disponibile → warning «non posso verificare i ref»; persiste solo con `--confirm` (degrado
  onesto, Principio IV).
- Relazione fuori MVP (`who_calls`/`defines`) → usage error argparse (exit 2, `choices`).

---

## `sertor-rag graph-eval amend-case`

```
sertor-rag graph-eval amend-case --relation R --target T --expected REF[,REF…]
                                 [--confirm] [--corpus C] [--json]
```

- Aggiorna l'`expected` del caso identificato da `(relation, target)` (re-congelamento dello **snapshot**,
  DA-c) — è il percorso deterministico di ri-authoring degli insiemi; la **decisione** se i nuovi `ref` sono
  legittimi resta dell'utente (la skill propone, l'utente approva: REQ-041). Stessa validazione write-time
  di `add-case`. Caso inesistente → `GraphSuiteValidationError`.

---

## `sertor-rag graph-eval validate-ref`

```
sertor-rag graph-eval validate-ref --relation R --target T REF[…] [--corpus C] [--json]
```

- Primitiva **deterministica** per la skill di genesi assistita (gruppo E): la skill — consumatore esterno —
  la invoca **via CLI** (Principio XI), non importa `sertor_core`.
- Naviga la relazione+target e riporta `RefValidation` (`checked`/`unverifiable`/`graph_available`), umano +
  JSON. Exit 0 sempre (è una verifica, non un gate); `unverifiable` non vuoto è informazione, non errore.

---

## Invarianti del contratto
- **Principio XI**: ogni accesso al grafo passa dalle factory `build_*` (il CLI è il vehicle); la skill
  esterna passa dai sottocomandi, mai dalla libreria.
- **Sezione distinta (REQ-030)**: il report di navigazione è separato da quello IR (`eval run`) — comando
  distinto, formato distinto, baseline distinta.
- **Equivalenza informativa** umano↔JSON (invariante CLI esistente).
- **Niente LLM nel run** (RNF-2); **niente rank/@k** nel report (Won't).
- **Additività** (RNF-1): a comando non invocato, index/search e costo identici a oggi; i `[[case]]` IR e
  `eval run` invariati.
