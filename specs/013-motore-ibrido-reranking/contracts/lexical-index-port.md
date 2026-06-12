# Contract — Porta `LexicalIndex`

Astrazione dell'indice lessicale (Protocol, structural typing — come `EmbeddingProvider`/
`VectorStore`). Il core dipende SOLO da questa porta; l'adapter concreto (BM25 + sidecar JSON)
vive in `adapters/lexical/`.

## Metodi

### `build(collection: str, entries: list[LexicalEntry]) -> None`
- Sostituisce integralmente l'indice della collezione (rebuild-from-scratch).
- Idempotente: stessi `entries` → stesso indice (NFR-06).
- Scrittura atomica (tmp + rename): un fallimento non lascia un sidecar corrotto né cancella
  il precedente (Principio IV/VI).
- `entries` vuoto → indice vuoto valido (non un errore).

### `query(collection: str, query: str, k: int, doc_type: DocTypeFilter = "both") -> list[str]`
- Restituisce gli id chunk in ordine di rilevanza lessicale decrescente, max `k`.
- Filtro `doc_type` applicato PRIMA del taglio a `k`.
- `k <= 0` → `[]`.
- Precondizione: `exists(collection)` è True — il chiamante (motore ibrido) la verifica;
  la policy sull'assenza (degradazione REQ-034) è del motore, non dell'adapter.
- Deterministico: stessa query + stesso indice → stessa lista (pareggi per `chunk_id`).

### `exists(collection: str) -> bool`
- True ⟺ l'indice della collezione è presente e leggibile (formato riconosciuto).
- Formato sconosciuto/corrotto → False NON è ammesso come risposta silenziosa: `exists` può
  tornare True e `query` fallire con errore esplicito (`ConfigError`), oppure il caricamento
  pigro solleva — mai degradazione non loggata.

### `reset(collection: str) -> None`
- Elimina l'indice della collezione; assente = no-op (idempotente).

## Namespacing

La chiave è il **nome collezione** già namespaced per `(corpus, provider)` da
`collection_name()`: due corpora o provider distinti non condividono mai un indice (REQ-005).

## Mock di test

`InMemoryLexicalIndex` in `tests/fixtures/mocks.py`: stessa semantica, dict in memoria,
nessun file system (NFR-03).
