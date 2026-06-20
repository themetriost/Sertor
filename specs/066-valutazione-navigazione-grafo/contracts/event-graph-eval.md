# Contract — Evento di osservabilità `graph_eval` (FEAT-011, RNF-3 / Principio IX)

Il run di valutazione della navigazione emette **un** evento strutturato via `log_event` — **gemello**
dell'evento `eval` IR (065) — così l'epica `osservabilita` potrà storicizzarne il trend. **Solo metriche,
nessun testo libero**: niente `relation` come valore libero pericoloso? no — `relation` ∈ insieme chiuso
(`who_calls`/`defines`) è ammessa come **dimensione**; ciò che è **vietato** sono `target` (nome di
simbolo), i `ref`/path attesi o navigati, e gli insiemi `missing`/`extra` (RNF-3). Catturato dallo store
solo se `SERTOR_OBSERVABILITY=true` (no-op altrimenti — `enable_observability` già chiamato dal pattern
CLI). Coerente con la policy export OTel **metrics-only** (feature 061) e con la redazione del core.

## Evento `graph_eval`
| Campo | Tipo | Note |
|---|---|---|
| `operation` | `"graph_eval"` | nome evento |
| `cases` | int | n. graph-case valutati |
| `relations` | dict[str,int] | conteggio casi per relazione (chiavi = insieme chiuso `who_calls`/`defines`) |
| `mean_precision` | float | media |
| `mean_recall` | float | media (secondaria) |
| `mean_f1` | float | media (metrica di gate) |
| `regressed` | bool | esito gate sul `mean_f1` (false se no-baseline) |
| `tolerance` | float \| null | tolleranza del gate (null se no-baseline) |
| `exact_gate` | bool | se il gate match-esatto era attivo |

## Esempio (record strutturato)
```json
{"operation": "graph_eval", "cases": 6,
 "relations": {"who_calls": 4, "defines": 2},
 "mean_precision": 0.79, "mean_recall": 0.90, "mean_f1": 0.83,
 "regressed": false, "tolerance": 0.0, "exact_gate": false}
```

## Invarianti
- **Nessun nome di simbolo / path / insieme / testo libero** (RNF-3/RNF-5): `target`, `ref`, `missing`,
  `extra` non compaiono mai. Solo metriche aggregate e dimensioni a cardinalità chiusa (`relations`).
- **Additivo**: nessuna modifica a `log_event`/handler; un solo nuovo nome-evento. A osservabilità spenta,
  zero overhead (Principio IX/III).
- **Twin di `eval`**: stessa forma e stessa policy del 065; un solo evento per run di navigazione.
