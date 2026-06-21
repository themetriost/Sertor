# Contract — Evento osservabilità `fused_eval` (070, delta su 069)

`emit_fused_eval_event` in `src/sertor_core/services/eval/fused_runner.py`. **Metrics-only**, gemello
OTel 061 (Principio IX): MAI `query`/`expected`/path/symbol o testo libero. Il contratto 069 resta;
cambia solo il **set di superfici** (3 → 2).

## Campi

| Campo | Tipo | Delta 070 |
|---|---|---|
| `provider` | str | invariato (nome embedder, non un segreto) |
| `cases` | `{"code": int, "doc": int, "both": int}` | invariato (`both` = `fusion.cases_count`) |
| `surface_mrr` | `{surface: float}` | **2 chiavi** (`search_code`/`search_docs`), era 3 |
| `surface_hit3` | `{surface: float}` | **2 chiavi**, era 3 |
| `fusion_coverage` | float | invariato — ora misurato sulle DUE liste |
| `hit_but_not_covered` | int | invariato |
| `regressed` | bool | invariato |
| `tolerance` | float \| null | invariato (null se `no-baseline`) |

## Invarianti

- **Cardinalità chiusa**: le chiavi di `surface_*` sono un insieme noto (`search_code`,
  `search_docs`) — niente cardinalità aperta, niente nomi/path/insiemi.
- Nessun testo libero (RNF-3, Principio IX); coerente con il gemello `eval`/`graph_eval`.

## Test atteso

- `test_fused_runner.py`: l'evento emesso ha `surface_mrr`/`surface_hit3` con esattamente le due
  chiavi `search_code`/`search_docs`; `cases.both` = `fusion.cases_count`; nessun campo di testo libero.
