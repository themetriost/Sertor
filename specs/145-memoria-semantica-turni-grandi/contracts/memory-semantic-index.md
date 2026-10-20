# Contract — `memory.semantic/1` (delta 145)

Delta sul contratto della 072 (`specs/072-ricerca-semantica-memoria/contracts/memory-semantic.md`). Ciò
che non è citato qui resta invariato.

## `MemorySemanticIndex.index_session(session) -> SemanticIndexReport`

- Ogni turno è diviso in unità: una se rientra in `max_chunk_tokens`, altrimenti i pezzi di
  `cap_to_tokens` (id e payload: `data-model.md`).
- Salta i turni le cui unità sono **tutte** già nella collezione (`skipped`); con una sessione già
  indicizzata non chiama il provider.
- Embedda le unità dei turni nuovi in **una** chiamata `embed()`.
  - Successo → `upsert`, `embedded = turni nuovi`.
  - `EmbeddingError` con `reason ∈ {"http 400","http 413","http 422"}` → ripiego: un `embed([pezzo])`
    per pezzo, turno per turno; i turni completi vengono scritti, quelli con un pezzo rifiutato finiscono
    in `rejected` (con `reason` del provider) e in `errors`; un errore di altro tipo durante il ripiego
    interrompe il ripiego e conta i turni non ancora trattati come errori `provider_unavailable`.
    Evento `memory_semantic_index_failed`, `reason=input_rejected`, `detail=<motivo>`,
    `rejected=<n>` (WARNING).
  - Qualunque altro `EmbeddingError` → come oggi: `errors = turni nuovi`, evento con
    `reason=provider_unavailable`.
- Guasto dello store → come oggi (`store_unavailable`).

## `MemorySemanticIndex.index_all(archive) -> SemanticIndexReport`

- Aggrega anche `rejected` (concatenazione nell'ordine delle sessioni).
- Evento `memory_semantic_index`: campi di oggi **+** `rejected=<conteggio>`. Mai id di sessione né testo.

## `MemorySemanticIndex.search(query)`

- Chiede allo store `2 × max(limit, 1)` candidati.
- Al più un risultato per `(session_key, turn_index)`, il primo nell'ordine dello store (il più
  pertinente); poi filtro temporale e taglio a `limit` come oggi.

## CLI `sertor-rag memory index-semantic`

Senza rifiuti: output **identico** a oggi.

```
embedded=1721 skipped=0 errors=0
{"embedded": 1721, "skipped": 0, "errors": 0}
```

Con rifiuti: righe/campo aggiuntivi, uno per turno rifiutato.

```
embedded=180 skipped=1540 errors=1
rejected session=<session_key> turn=<turn_index> reason=http 400
{"embedded": 180, "skipped": 1540, "errors": 1,
 "rejected": [{"session": "<session_key>", "turn": <turn_index>, "reason": "http 400"}]}
```
