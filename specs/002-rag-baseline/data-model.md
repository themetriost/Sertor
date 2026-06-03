# Phase 1 — Data Model: Motore RAG vettoriale (baseline)

Entità di FEAT-002. Riusa le entità del nucleo (`Document`, `Chunk`, `RetrievalResult`,
`IndexReport`, `EmbeddedChunk`) senza ridefinirle; aggiunge solo ciò che è proprio del motore
(valutazione) e una eccezione di dominio.

---

## Riuso dal nucleo (FEAT-001)

| Entità | Ruolo in FEAT-002 |
|--------|-------------------|
| `Document` | prodotto dall'ingestione del nucleo durante l'index |
| `Chunk` / `ChunkMetadata` | prodotti dal chunking del nucleo |
| `EmbeddedChunk` | record persistito nel vector store |
| `RetrievalResult` | **risultato di query del motore** (path, doc_type, chunk_id, score, text/metadata) — copre REQ-006/007 |
| `IndexReport` | **report di indicizzazione** (collection, documents, chunks, embedding_dim, elapsed_ms) — copre REQ-003 |

> REQ-007 (path, source-type, chunk index, score, preview): `RetrievalResult` espone `path`,
> `doc_type`, `chunk_id` (contiene l'indice `…#N`), `score`, `text` (anteprima). Nessuna nuova entità
> di risultato necessaria.

---

## GroundTruthItem / GroundTruth (input di valutazione — REQ-011)

Insieme di valutazione fornito dal chiamante (A-4): mappa query → file attesi.

| Campo | Tipo | Note |
|-------|------|------|
| `query` | `str` | testo della query nota |
| `expected_paths` | `list[str]` | path (relativi) dei file considerati pertinenti |

`GroundTruth` = `list[GroundTruthItem]` (o iterabile di tuple `(query, expected_paths)`).

---

## EvalReport (output di valutazione — REQ-011)

Risultato della valutazione della pertinenza.

| Campo | Tipo | Note |
|-------|------|------|
| `hit_rate` | `dict[int, float]` | hit-rate@k per k ∈ {1,3,5,10} |
| `mrr` | `float` | MRR@10 |
| `queries` | `int` | numero di query valutate |
| `provider` | `str` | nome del provider di embeddings usato |

**Regole.**
- `hit@k` = (n. query con ≥1 `expected_path` nei primi k risultati) / `queries`.
- `mrr@10` = media su tutte le query di `1/rango` del primo risultato pertinente nei primi 10 (0 se assente).
- `queries == 0` → report con valori a 0 e nessun errore (input vuoto lecito).

---

## IndexNotFoundError (eccezione di dominio — REQ-009) [estensione additiva del nucleo]

Sollevata dal motore quando si interroga un indice inesistente.

| Aspetto | Valore |
|---------|--------|
| Base | `SertorError` (gerarchia di FEAT-001) |
| Campi | `collection`, messaggio azionabile ("costruisci l'indice prima di interrogare") |
| Quando | `BaselineEngine.query()` con `store.exists(collection) == False` |

> Differenza voluta rispetto alla `RetrievalFacade` del nucleo (che su indice assente ritorna `[]`):
> a livello di motore l'assenza è un errore d'uso esplicito (Principio IV, R4 in research).

---

## Estensioni additive del nucleo (non nuove entità, ma firma)

| Elemento | Modifica | Requisito |
|----------|----------|-----------|
| Porta `VectorStore` | `+ reset(collection: str) -> None` | REQ-002 |
| `IndexingService.index` | `+ rebuild: bool = False` (reset dopo embed, prima di upsert) | REQ-002/004 |

---

## Relazioni

```text
BaselineEngine(name="baseline")
   ├─ index(root, rebuild=True) ──> [nucleo] discover → chunk → embed → reset → upsert ──> IndexReport
   ├─ query(text, k) ─────────────> exists? --no--> IndexNotFoundError
   │                                  └─yes─> embed(query) → store.query(k) ──> list[RetrievalResult]
   └─ name ───────────────────────> "baseline"  (REQ-013/014)

evaluate(engine, GroundTruth) ──> EvalReport (hit_rate@k, mrr@10)        (REQ-011)
```
