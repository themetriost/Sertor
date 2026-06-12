# Contract — `HybridEngine` e selezione del motore

## Interfaccia (REQ-033: sostituibile col baseline)

| Membro | Tipo/Firma | Note |
|---|---|---|
| `name` | `str` = `"hybrid"` | Nome stabile della modalità. |
| `provider` | `str` (property) | Nome del provider di embeddings. |
| `index(root) -> IndexReport` | come baseline | Rebuild congiunto: vettoriale + sidecar lessicale dagli stessi chunk (REQ-001/003). |
| `ensure_index() -> None` | come baseline | Strict sulla collezione vettoriale: assente → `IndexNotFoundError` (FR-004). |
| `query(query, k=None) -> list[RetrievalResult]` | come baseline | Via strict per consumatori diretti. |
| `retrieve(query, k, doc_type) -> list[RetrievalResult]` | `RetrieverStrategy` | Usata dalla facade (collezione già verificata). |

## Semantica di `retrieve`

1. **Sidecar lessicale assente** (corpus pre-ibrido): retrieval dense-only (equivalente
   baseline) + evento WARNING `lexical_index_missing` con hint al re-index. La query NON
   fallisce (REQ-034). Nessun altro effetto collaterale.
2. **Sidecar presente**: pool denso (`store.query`, `rrf_pool`, `doc_type`) + pool lessicale
   (`lexical.query`, `rrf_pool`, `doc_type`) → fusione RRF (`c` da Settings) → ordinamento
   `(-score_rrf, chunk_id)` → se `rerank_enabled`: rerank dei primi `rerank_pool` → top-k.
3. Risultati: `RetrievalResult` invariati (REQ-013); score = RRF o cross-encoder.
4. Eventi: `hybrid_query` sempre (REQ-060); `rerank` se applicato (REQ-061); mai segreti
   (REQ-062).

## Selezione del motore (composition root)

```
Settings.engine (SERTOR_ENGINE, default "hybrid")
  "baseline" → BaselineEngine          (risultati identici a oggi, REQ-071)
  "hybrid"   → HybridEngine            (default, REQ-030)
  altro      → ConfigError(valori ammessi)
```

- `build_engine(settings)` è l'UNICO punto di scelta (REQ-031).
- `build_facade(settings)`: con `engine == "hybrid"` inietta il motore come `retriever`
  (parametro keyword opzionale, additivo — interfaccia facade invariata per i consumatori,
  REQ-032); senza, comportamento attuale invariato.
- `build_indexer(settings)`: con `engine == "hybrid"` inietta l'adapter `LexicalIndex` nella
  pipeline (sidecar scritto nello stesso passaggio di indicizzazione); con `baseline`, pipeline
  identica a oggi.
- `build_baseline_engine()` resta invariata (REQ-070).
- Reranking: `rerank_enabled=True` + extra `rerank` assente → `ConfigError` azionabile al
  momento della composizione (REQ-022); extra presente → adapter FlashRank con import lazy
  (REQ-021).

## Fan-out multi-collezione (feature 010)

Con `extra_corpora` configurati, `search_combined` mantiene il percorso denso esistente
(fusione per score coseno fra collezioni omogenee): l'ibrido NON si applica al fan-out in questa
feature (research D6); il comportamento è dichiarato nei log e nel quickstart.
