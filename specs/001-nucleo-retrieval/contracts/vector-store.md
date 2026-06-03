# Contratto — Porta `VectorStore`

Astrazione del backend di persistenza+ricerca vettoriale (in `domain/ports.py`). Implementata da
`adapters/vectorstores/{chroma,azure_search}.py`. Sostituibile via config senza toccare il chiamante
(Principio II, REQ-018).

## Interfaccia

```python
class VectorStore(Protocol):
    def upsert(self, collection: str, records: list[EmbeddedChunk]) -> None:
        """Inserisce/sostituisce chunk (id, vettore, payload) nella collezione."""

    def query(self, collection: str, vector: list[float], k: int,
              doc_type: Literal["code", "doc", "both"] = "both") -> list[RetrievalResult]:
        """Top-k per similarità, con filtro opzionale su doc_type (no indici separati)."""

    def delete(self, collection: str, ids: list[str]) -> None: ...

    def exists(self, collection: str) -> bool:
        """True se la collezione esiste ed è inizializzata."""
```

## Contratto comportamentale

| # | Precondizione | Comportamento | Postcondizione | Req |
|---|---------------|---------------|----------------|-----|
| 1 | backend configurato | memorizza chunk con vettori+metadati | interrogabili per similarità | REQ-017 |
| 2 | due corpora in collezioni distinte | isolamento per namespace | query su A non ritorna chunk di B | REQ-019, SC-001 |
| 3 | `doc_type` = code/doc | filtro sui metadati | risultati del solo tipo, senza indici separati | REQ-027 |
| 4 | `k` > record disponibili | nessun errore | ritorna tutti i disponibili | edge case |
| 5 | collezione assente/non inizializzata | `query` → `[]` (la facade emette warning); `exists` → False | nessuna eccezione non gestita | REQ-028 |
| 6 | backend non disponibile | solleva `VectorStoreError` | `VectorStoreError(backend, reason)`; **non** ritorna vuoto silenzioso | REQ-021 |
| 7 | local-only | persiste solo su file system locale | nessuna credenziale/rete cloud | REQ-022 |

## Invarianti

- Una collezione è coerente per **(corpus, provider, dimensione embedding)**: la dimensione del
  `vector` in `query`/`upsert` deve combaciare con quella della collezione.
- `upsert` con gli stessi `chunk_id` **sostituisce** (idempotenza del full re-index, NFR-02): nessun
  duplicato.
- Namespacing via nome di collezione, non via strutture d'indice separate per tipo.

## Distinzione errore vs vuoto (Principio IV)

- **Collezione vuota/assente** = stato lecito → `[]` + warning (REQ-028). *Non* è un errore.
- **Backend irraggiungibile** = errore → `VectorStoreError` (REQ-021). *Non* è un risultato vuoto.

## Adapter MVP

- **Chroma** (locale embedded, default): collezioni Chroma, persistenza su file system. Estrarre la
  logica oggi sepolta in `prototype/02-hybrid-reranking/hybrid.py::HybridIndex` (senza BM25/rerank,
  fuori ambito).
- **Azure AI Search** (cloud, extra opzionale): vector index + filtro su campo `source`. Import SDK lazy.

## Test (contract tests)

- Mock store in-memory per il core (NFR-01).
- Verifica: isolamento namespace (#2), filtro tipo (#3), k oversize (#4), vuoto→[] (#5),
  backend down→errore (#6), upsert idempotente (no duplicati).
