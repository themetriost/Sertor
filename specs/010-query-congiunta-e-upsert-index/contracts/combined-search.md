# Contratto — Ricerca combinata multi-collezione (`RetrievalFacade.search_combined`)

**Schema concettuale**: `facade.search_combined/2` (estensione retro-compatibile della /1 odierna)

## Firma (invariata per il consumatore)

```python
facade = build_facade()            # cabla corpus primario + extra_corpora da Settings
results = facade.search_combined(query: str, k: int | None = None) -> list[RetrievalResult]
```

Il consumatore non passa collezioni né conosce il naming: i corpora bersaglio sono dichiarati in
configurazione (`SERTOR_CORPUS` + `SERTOR_EXTRA_CORPORA`).

## Comportamento

| Condizione | Esito |
|---|---|
| `extra_corpora` vuoto (default) | Identico a oggi: una collezione, filtro `doc_type="both"` (FR-006) |
| Tutte le collezioni bersaglio esistono | ≤ `k` risultati totali, ordinati per `score` desc, tie-break per `chunk_id` asc (FR-001/002/003) |
| Una collezione attesa assente, corpus mai indicizzato | Warning `no_index` per quella collezione; contributo vuoto; le altre rispondono (FR-004) |
| Tutte le collezioni assenti | `[]` + warning (FR-005) |
| Collezione attesa assente MA il corpus esiste sotto altro provider (`{corpus}__*`) | `ProviderMismatchError` — nessun risultato parziale (FR-009, clarify #1) |
| Backend irraggiungibile | `VectorStoreError` (invariato) |

## Invarianti

- La query è embeddata **una sola volta** (un solo provider per facade).
- Output deterministico a input costante (ordinamento totale, Principio VI).
- `search_code` / `search_docs` NON fanno fan-out (FR-006bis).
- Evento di log `retrieve` con `collections=[...]`, `provider`, `k`, `results`, `elapsed_ms` (FR-008).

## Test di contratto (da tasks)

1. Due collezioni popolate → risultati da entrambe, ordinati, ≤ k.
2. Pertinenza concentrata in una → tutti i k dalla stessa (nessuna quota).
3. Parità di score → ordine stabile per `chunk_id`.
4. Extra assente (corpus mai indicizzato) → degradazione + warning.
5. Tutte assenti → `[]` + warning.
6. Extra sotto altro provider → `ProviderMismatchError` con corpus/expected/found nel messaggio.
7. `extra_corpora` vuoto → output identico al comportamento pre-feature (regressione).
