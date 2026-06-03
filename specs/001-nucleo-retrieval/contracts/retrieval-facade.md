# Contratto — Facade di retrieval (interfaccia pubblica del nucleo)

Punto d'accesso unico e stabile per i consumatori (motori RAG, skill wiki, layer CLI). È l'interfaccia
che rende il nucleo **riusabile come libreria** (REQ-029, REQ-E1). Dipende solo dalle porte
`EmbeddingProvider` e `VectorStore` (Principio I).

## Interfaccia

```python
class RetrievalFacade:
    def __init__(self, embedder: EmbeddingProvider, store: VectorStore,
                 collection: str, default_k: int): ...

    def search_code(self, query: str, k: int | None = None) -> list[RetrievalResult]:
        """Ricerca semantica sul solo CODICE (filtro doc_type=code)."""

    def search_docs(self, query: str, k: int | None = None) -> list[RetrievalResult]:
        """Ricerca semantica sulla sola DOCUMENTAZIONE (filtro doc_type=doc)."""

    def search_combined(self, query: str, k: int | None = None) -> list[RetrievalResult]:
        """Ricerca su CODICE + DOC insieme (doc_type=both)."""
```

> Costruita dal **composition root** (`composition.py`) a partire da `Settings`: il consumatore importa
> la facade già cablata, **senza** conoscere store/embeddings (REQ-029). Nessun reranking/grafo qui
> (fuori ambito §4 — quelli sono FEAT-004/005).

## Contratto comportamentale

| # | Precondizione | Comportamento | Postcondizione | Req |
|---|---------------|---------------|----------------|-----|
| 1 | indice popolato | embed query → `store.query` con filtro tipo | lista di `RetrievalResult` con testo, path, chunk_id, doc_type, score | REQ-023/024/025 |
| 2 | richiesta filtrata (code/doc) | applica filtro `doc_type` | risultati del solo tipo, senza indici separati | REQ-027 |
| 3 | `k` passato o default | usa `k` o `default_k` | ≤ k risultati; `k` > disponibili → tutti i disponibili | REQ-026 |
| 4 | indice vuoto/non inizializzato | `store.exists` False | `[]` + **warning strutturato** (assenza indice); nessuna eccezione | REQ-028 |
| 5 | provider/backend non disponibile | propaga errore di dominio | `EmbeddingError`/`VectorStoreError`; **non** vuoto silenzioso | REQ-012/021 |
| 6 | importata da un consumatore | usabile senza accesso a store/embeddings | risultati con metadati stabili | REQ-029 |

## Invarianti

- Ogni `RetrievalResult` riporta **almeno**: `text`, `path`, `chunk_id`, `doc_type`, `score` (REQ-025).
- La facade è indipendente dal backend: cambiare store/provider via config non cambia la firma né il
  formato dei risultati (REQ-023).
- Osservabilità: ogni query emette log strutturato (operazione, provider/backend, k, tempi) senza
  segreti (REQ-031).

## Esempio d'uso (consumatore)

```python
from sertor_core.composition import build_facade

facade = build_facade()                      # cablata da Settings (env/file)
hits = facade.search_code("come si valida un input", k=5)
for h in hits:
    print(h.path, h.chunk_id, round(h.score, 3))
```

## Test (contract tests)

- Con mock embedder + mock store: formato risultati (#1), filtro tipo (#2), k/default e oversize (#3),
  indice vuoto→[]+warning (#4), propagazione errori (#5), uso come libreria importata (#6).
- Misura `precision@k` su corpus ground-truth con baseline prototipo (SC-004) — test di qualità.
