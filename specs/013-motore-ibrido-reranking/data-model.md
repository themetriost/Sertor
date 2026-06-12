# Data Model — Motore RAG ibrido + reranking (013)

Entità e contratti dati. Le entità di dominio esistenti (`Document`, `Chunk`, `EmbeddedChunk`,
`RetrievalResult`, `IndexReport`) **non cambiano** (FR-009/REQ-013).

## Porte nuove (`domain/ports.py`)

### `LexicalIndex` (Protocol)

Astrazione dell'indice lessicale; l'adapter concreto è BM25 con sidecar (research D1/D2).

| Metodo | Contratto |
|---|---|
| `build(collection: str, entries: list[LexicalEntry]) -> None` | Costruisce/sostituisce l'indice della collezione dagli stessi chunk dell'upsert vettoriale (rebuild-from-scratch, idempotente sugli stessi input). |
| `query(collection: str, query: str, k: int, doc_type: DocTypeFilter = "both") -> list[str]` | Ranking lessicale: lista ordinata di `chunk_id` (max `k`), filtrata per `doc_type` prima del taglio. Collezione assente → comportamento NON definito qui: il chiamante deve verificare `exists()` (la degradazione è policy del motore, REQ-034). |
| `exists(collection: str) -> bool` | True se l'indice lessicale della collezione è presente. |
| `reset(collection: str) -> None` | Elimina l'indice della collezione (idempotente: assente = no-op). |

`LexicalEntry` (dataclass frozen, dominio): `chunk_id: str`, `text: str`, `doc_type: str`,
`path: str`.

### `Reranker` (Protocol)

| Membro | Contratto |
|---|---|
| `model: str` | Identificativo del modello (per il log `rerank`, REQ-061). |
| `rerank(query: str, results: list[RetrievalResult], k: int) -> list[RetrievalResult]` | Ri-ordina i risultati per rilevanza query-passaggio; restituisce i top-k con `score` = punteggio del cross-encoder. Lista vuota → lista vuota. |

### `RetrieverStrategy` (Protocol)

Il seam con cui il composition root inietta la strategia di retrieval nella facade (research D6).

| Metodo | Contratto |
|---|---|
| `retrieve(query: str, k: int, doc_type: DocTypeFilter) -> list[RetrievalResult]` | Retrieval sulla collezione primaria, collezione **già verificata esistente** dal chiamante (la facade conserva la sua policy tollerante). |

## Sidecar lessicale (formato su disco)

Percorso: `<Settings.index_dir>/lexical/<collection>.json` — il nome collezione codifica già
`(corpus, provider)` (REQ-005); il file vive nel perimetro dell'index dir (REQ-072).

```json
{
  "format": "sertor.lexical/1",
  "tokenizer_version": 1,
  "collection": "sertor__azure_text_embedding_3_large",
  "entries": [
    {"chunk_id": "src/sertor_core/domain/ports.py#0",
     "path": "src/sertor_core/domain/ports.py",
     "doc_type": "code",
     "text": "..."}
  ]
}
```

- Il testo è memorizzato grezzo; la tokenizzazione avviene al caricamento (research D3) — il
  `tokenizer_version` consente di invalidare/diagnosticare in futuro.
- `format` versionato: un formato sconosciuto → errore esplicito (`ConfigError`), non parsing
  parziale (Principio IV).
- Scrittura atomica: write su file temporaneo + rename (nessun sidecar troncato, Principio VI).

## `Settings` — campi nuovi (env → default)

| Campo | Env | Default | Note |
|---|---|---|---|
| `engine` | `SERTOR_ENGINE` | `"hybrid"` | `baseline` \| `hybrid` (REQ-030); valore invalido → `ConfigError` nel composition root. |
| `rrf_c` | `SERTOR_RRF_C` | `60` | Costante RRF (REQ-011, Cormack et al.). |
| `rrf_pool` | `SERTOR_RRF_POOL` | `30` | Candidati per fonte prima della fusione (REQ-011; prototipo: POOL=30). |
| `rerank_enabled` | `SERTOR_RERANK` | `False` | Abilita il secondo stadio (REQ-020; default off per R-3). |
| `rerank_pool` | `SERTOR_RERANK_POOL` | `15` | Pool fuso passato al reranker (≈3×k, REQ-024). |

Tutti i default vivono SOLO in `Settings` (Principio VIII, NFR-05).

## `HybridEngine` (`engines/hybrid.py`)

Stato: `embedder`, `store`, `lexical`, `collection`, `settings`, `reranker | None`.
Interfaccia = quella del `BaselineEngine` (REQ-033) + la strategia per la facade:

| Membro | Semantica |
|---|---|
| `name = "hybrid"` | Nome stabile della modalità. |
| `provider` | Nome del provider di embeddings (come baseline). |
| `index(root)` | Pipeline del nucleo con sink lessicale: vettoriale + sidecar dagli stessi chunk (REQ-001/003). |
| `ensure_index()` | Strict sulla **collezione vettoriale** (FR-004): assente → `IndexNotFoundError`. |
| `query(query, k=None)` | `ensure_index()` → `retrieve(query, k, "both")` (via strict, per consumatori diretti). |
| `retrieve(query, k, doc_type)` | Cuore ibrido: sidecar assente → degradazione dense-only + WARNING `lexical_index_missing` (REQ-034); altrimenti pool denso + pool lessicale → RRF → (rerank se attivo) → top-k. |

### Flusso `retrieve` (stati)

```
collezione esiste (garantito dal chiamante: facade exists() / ensure_index())
 ├─ lexical.exists()? NO → dense top-k + WARNING lexical_index_missing   (REQ-034)
 └─ SÌ → dense_pool(rrf_pool, doc_type) + lexical_pool(rrf_pool, doc_type)
         → RRF(c) → ordina (-score, chunk_id)                            (REQ-010/012)
         ├─ rerank_enabled? NO → top-k                                   (REQ-023)
         └─ SÌ → reranker.rerank(query, fused[:rerank_pool], k)          (REQ-020/024)
```

Punteggi nel `RetrievalResult`: score RRF (fusione) o score del cross-encoder (rerank) — sempre
ordinamento decrescente deterministico.

## Ground-truth (`tests/fixtures/ground_truth.py`)

```python
# (query, [path relativi attesi], kind)  — kind ∈ {"symbol", "nl"} per LSC-1 sul sottoinsieme symbol
GROUND_TRUTH: list[tuple[str, list[str], str]] = [
    ("EmbeddingProvider", ["src/sertor_core/domain/ports.py"], "symbol"),
    ...
]
```

Path relativi POSIX (REQ-053, Principio X); ≥10 coppie in implementazione, 6 fissate in research
D10. Consumato da: `evaluate()` (confronto baseline/ibrido/ibrido+rerank, REQ-051) e dai 2 test
strict (REQ-052).

## Eventi di log (schema, REQ-060/061/062)

| Evento | Livello | Campi |
|---|---|---|
| `hybrid_query` | INFO | `engine, provider, collection, lexical_hits, dense_hits, fused_k, rerank_applied, elapsed_ms` |
| `rerank` | INFO | `reranker_model, pool_size, top_k, elapsed_ms` |
| `lexical_index_missing` | WARNING | `collection, hint` (re-index abilita l'ibrido) |

Redazione segreti: meccanismo esistente (`observability/logging.py`), nessun campo segreto negli
schemi.
