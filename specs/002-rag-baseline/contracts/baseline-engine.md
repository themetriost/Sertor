# Contratto — `BaselineEngine`

Motore RAG vettoriale (modalità "baseline"). Consuma il nucleo di FEAT-001; non ne ridefinisce le
primitive. Costruito dal composition root (`build_baseline_engine`) a partire da `Settings`.

## Interfaccia

```python
class BaselineEngine:
    name: str = "baseline"   # nome stabile della modalità (REQ-013)

    def __init__(self, embedder, store, collection, default_k, settings): ...

    def index(self, root: Path | str) -> IndexReport:
        """Indicizza la codebase ricostruendo l'indice da zero (rebuild idempotente)."""

    def query(self, query: str, k: int | None = None) -> list[RetrievalResult]:
        """Top-k chunk per similarità vettoriale. Errore esplicito se l'indice non esiste."""
```

## Contratto comportamentale

| # | Precondizione | Comportamento | Postcondizione | Req |
|---|---------------|---------------|----------------|-----|
| 1 | path + provider configurato | discover→chunk→embed→reset→upsert | indice persistente con tutti i chunk; `IndexReport` con chunks+dim | REQ-001/003 |
| 2 | indice già esistente | rebuild-from-scratch (reset prima dell'upsert) | nessun chunk duplicato né residuo da file rimossi | REQ-002 |
| 3 | provider down durante index | `embed` solleva `EmbeddingError` **prima** del reset | indice preesistente **intatto**, nessun parziale | REQ-004, NFR-004 |
| 4 | indice esistente, query | embed query (stesso provider) → similarità → top-k | `list[RetrievalResult]` (path, doc_type, chunk_id, score, text) | REQ-005/006/007 |
| 5 | `k` dato / assente | usa `k` o `default_k` da Settings | ≤ k risultati; k>disponibili → tutti | REQ-008 |
| 6 | indice inesistente, query | `store.exists` False → `IndexNotFoundError` | errore azionabile ("costruisci l'indice"); **non** `[]` | REQ-009 |
| 7 | provider down, query | propaga `EmbeddingError` | nessun risultato parziale/vuoto silenzioso | REQ-010 |
| 8 | modalità baseline attiva | usa **solo** retrieval vettoriale | nessuna chiamata a ibrido/grafo/agentico | REQ-012/014 |
| 9 | provider via config | `build_baseline_engine` cabla da Settings | cambio provider senza modifiche al codice | REQ-010(cfg)/012 |
| 10 | qualunque codebase (path) | nessuna assunzione hardcoded | funziona su ≥2 repo | REQ-015, SC-001 |

## Invarianti

- L'embedding di query e indice usa **lo stesso provider** (coerenza dimensionale, REQ-006).
- `index` è idempotente: a input invariato → stesso n. di chunk e stessi risultati alle stesse query (SC-003).
- Ogni `index`/`query` emette log strutturato (operazione, provider, conteggi, tempi, errori) (REQ-015/NFR-007).
- Il motore non importa SDK di provider né la CLI (Principio I); è esercitabile con mock.

## Distinzione errore vs vuoto (Principio IV)

- **Indice assente** = errore d'uso del motore → `IndexNotFoundError` (REQ-009). *Non* `[]`.
- **Indice presente ma 0 hit** = risultato lecito → `[]`.
- **Provider/backend down** = errore → `EmbeddingError`/`VectorStoreError` (REQ-010).

## Test (contract tests)

Con `FakeEmbedder` + `InMemoryStore`/`ChromaStore`: index→query (#1,#4), rebuild senza duplicati
(#2), abort su provider down in index (#3), k default/override/oversize (#5), indice mancante→errore
(#6), provider down in query→errore (#7), uso come libreria. Idempotenza in integrazione (SC-003).
