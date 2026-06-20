# Contract — Evento di osservabilità `eval` (FEAT-001, RNF-3 / Principio IX)

Il run di valutazione emette **un** evento strutturato via `log_event`, così l'epica `osservabilita`
(FEAT-009) potrà storicizzarne il trend. **Solo metriche, nessun testo libero**: niente `query`, niente
`expected`/path nell'evento (coerente con la policy export OTel *metrics-only* della feature 061 e con la
redazione del core). Catturato dallo store solo se `SERTOR_OBSERVABILITY=true` (no-op altrimenti —
`enable_observability` già chiamato dal pattern CLI).

## Evento `eval`
| Campo | Tipo | Note |
|---|---|---|
| `operation` | `"eval"` | nome evento |
| `provider` | string | provider dell'engine valutato |
| `queries` | int | n. casi |
| `hit_rate` | dict[int,float] | hit-rate@k (chiavi = k) |
| `mrr` | float | MRR |
| `regressed` | bool | esito gate (false se no-baseline) |
| `tolerance` | float \| null | tolleranza del gate (null se no-baseline) |

## Esempio (record strutturato)
```json
{"operation": "eval", "provider": "ollama:nomic-embed-text",
 "queries": 11, "hit_rate": {"1": 0.55, "5": 0.91, "10": 1.0},
 "mrr": 0.83, "regressed": false, "tolerance": 0.0}
```

## Invarianti
- **Nessun segreto / nessun testo libero** (RNF-3/RNF-6): query e path non compaiono mai.
- **Additivo**: nessuna modifica a `log_event`/handler; un solo nuovo nome-evento. A osservabilità
  spenta, zero overhead (Principio IX/III).
- Per `--compare`, un evento per config (con `provider`/metriche distinti).
