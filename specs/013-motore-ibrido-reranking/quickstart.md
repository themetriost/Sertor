# Quickstart — Motore RAG ibrido + reranking (013)

## Per chi usa Sertor (nessuna azione richiesta)

Con l'aggiornamento, il motore ibrido è il **default** (`SERTOR_ENGINE=hybrid`). I consumatori
(facade, server MCP `sertor-rag`, CLI `sertor-rag`) non cambiano.

- **Corpus già indicizzato (pre-ibrido)**: le ricerche continuano a funzionare in modalità
  vettoriale, con un warning nei log (`lexical_index_missing`). Per abilitare l'ibrido:

  ```bash
  sertor-rag index .        # re-index: costruisce vettoriale + indice lessicale insieme
  ```

- **Tornare al comportamento attuale** (identico a oggi):

  ```bash
  SERTOR_ENGINE=baseline
  ```

## Configurazione (tutte le manopole, default in `Settings`)

```bash
SERTOR_ENGINE=hybrid       # baseline | hybrid (default: hybrid)
SERTOR_RRF_C=60            # costante RRF
SERTOR_RRF_POOL=30         # candidati per fonte prima della fusione
SERTOR_RERANK=false        # secondo stadio cross-encoder (richiede extra `rerank`)
SERTOR_RERANK_POOL=15      # pool fuso passato al reranker (~3×k)
```

## Reranking (opzionale)

```bash
uv add "sertor-core[rerank]"   # installa FlashRank (ONNX, niente torch)
SERTOR_RERANK=true
```

Senza l'extra installato: `SERTOR_RERANK=true` → errore esplicito e azionabile;
`SERTOR_RERANK=false` (default) → fusione RRF pura, nessun degrado.

## Uso da libreria

```python
from sertor_core import build_facade           # consumatori: invariato
results = build_facade().search_code("EmbeddingProvider")

from sertor_core.composition import build_engine   # consumo diretto del motore (strict)
engine = build_engine()
engine.index(".")                               # vettoriale + lessicale insieme
hits = engine.query("IndexNotFoundError", k=5)
```

## Valutazione comparativa (ground-truth)

```bash
uv run pytest tests/integration/test_baseline_quality.py tests/integration/test_precision_at_k.py
```

I due test (ex `xfail`, ora strict) indicizzano `src/sertor_core/` senza rete (embedder mock +
indice lessicale reale) e verificano: hit@5 ibrido ≥ baseline, MRR ibrido ≥ baseline, e
+10 pp sulle query a simbolo (LSC-1). Il report comparativo (hit@1/3/5/10, MRR@10 per
baseline/ibrido/ibrido+rerank) si ottiene con `evaluate()` sul ground-truth
(`tests/fixtures/ground_truth.py`).

## Esito misurato (implementazione, 2026-06-12 — embedder mock, corpus `src/sertor_core`, 11 query)

| Modalità | hit@1 | hit@3 | hit@5 | hit@10 | MRR@10 |
|---|---|---|---|---|---|
| baseline (dense, embedder finto) | 0.00 | 0.00 | 0.00 | 0.18 | 0.022 |
| **hybrid (RRF)** | 0.18 | 0.36 | **0.73** | 0.91 | 0.348 |
| **hybrid+rerank** (FlashRank ms-marco-MiniLM-L-12-v2) | **0.91** | 1.00 | 1.00 | 1.00 | **0.939** |

Sul sottoinsieme a simbolo: baseline 0.00 → hybrid **1.00** (LSC-1 ampiamente superato). Replica
del fenomeno del prototipo 02 (MRR 0.13→0.94 con embedder debole). Latenza del rerank: ~600 ms
per query su CPU (pool 15) — coerente col default off (R-3: su embedder forte può non servire).

## Limiti dichiarati di questa iterazione

- **Fan-out multi-collezione** (`SERTOR_EXTRA_CORPORA`): resta dense-only (gli score RRF non si
  fondono con score coseno di altre collezioni).
- **Delega nativa per-store** (Azure AI Search hybrid + semantic ranker): seam pronto nel
  composition root, implementazione futura (Could, Gruppo E).
- **Persistenza scalabile** dell'indice lessicale: sidecar JSON adeguato a corpora <10k chunk;
  l'indice invertito su disco è rifinitura futura (FEAT-009 d'epica).
