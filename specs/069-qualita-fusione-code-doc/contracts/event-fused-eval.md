# Contract — Evento di osservabilità `fused_eval` (FEAT-003, RNF-3 / Principio IX)

Il run di misura fusa (`eval run --fused`) emette **un** evento strutturato via `log_event` — **gemello**
degli eventi `eval` (065) e `graph_eval` (066). **Solo metriche, nessun testo libero**: niente `query`,
niente `expected`/path, niente nomi. Le dimensioni ammesse sono a cardinalità chiusa (la `surface` ∈
insieme chiuso). Catturato dallo store solo se `SERTOR_OBSERVABILITY=true` (no-op altrimenti —
`enable_observability` già chiamato dal pattern CLI). Coerente con la policy export OTel **metrics-only**
(feature 061) e con la redazione del core.

## Evento `fused_eval`
| Campo | Tipo | Note |
|---|---|---|
| `operation` | `"fused_eval"` | nome evento |
| `provider` | str | provider/backend di embedding usato |
| `cases` | dict[str,int] | conteggio casi per intento (chiavi chiuse: `code`/`doc`/`both`) |
| `surface_mrr` | dict[str,float] | MRR per superficie (chiavi chiuse: `search_code`/`search_docs`/`search_combined`) |
| `surface_hit3` | dict[str,float] | hit-rate@3 per superficie (rappresentativo; @k completo nel report, non nell'evento) |
| `fusion_coverage` | float | coverage sui casi `both` |
| `hit_but_not_covered` | int | n. casi REQ-022 (hit@k ma manca un tipo) — la lacuna, come metrica |
| `regressed` | bool | esito gate (false se no-baseline) |
| `tolerance` | float \| null | tolleranza del gate (null se no-baseline) |

## Esempio (record strutturato)
```json
{"operation": "fused_eval", "provider": "ollama:nomic",
 "cases": {"code": 8, "doc": 8, "both": 6},
 "surface_mrr": {"search_code": 0.64, "search_docs": 0.73, "search_combined": 0.69},
 "surface_hit3": {"search_code": 0.75, "search_docs": 0.88, "search_combined": 0.82},
 "fusion_coverage": 0.50, "hit_but_not_covered": 2,
 "regressed": false, "tolerance": 0.0}
```

## Invarianti
- **Nessun query / path / nome / testo libero** (RNF-3): `query`, `expected`, i path recuperati non
  compaiono mai. Solo metriche aggregate e dimensioni a cardinalità chiusa (`surface`/`intent`).
- **Additivo:** nessuna modifica a `log_event`/handler; un solo nuovo nome-evento. A osservabilità spenta,
  zero overhead (Principio IX/III).
- **Twin di `eval`/`graph_eval`:** stessa forma e policy; **un** evento per run fuso (REQ-042).
- La fusion coverage e `hit_but_not_covered` rendono **storicizzabile** il trend del differenziatore
  code+doc (gate «Allineamento alla missione»).
