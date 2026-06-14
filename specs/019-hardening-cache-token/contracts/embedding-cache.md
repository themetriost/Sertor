# Contract — CachingEmbedder + EmbeddingCache

Contratto interno (la porta pubblica `EmbeddingProvider` **non cambia**; questo descrive il decoratore e
lo store che vivono dietro di essa).

## `CachingEmbedder` (implementa `EmbeddingProvider`)

```
CachingEmbedder(inner: EmbeddingProvider, cache: EmbeddingCache)
  name: str        # delega a inner.name
  dim: int | None  # lunghezza del primo vettore prodotto (hit o miss); None finché non ne produce
  batch_size: int  # delega a inner.batch_size
  embed(texts: list[str]) -> list[list[float]]
```

**Garanzie di `embed`:**

1. **Ordine preservato**: l'output corrisponde 1:1 all'ordine di `texts` (contratto della porta).
2. **Hit non ri-embeddano**: per ogni `text` la cui chiave `(inner.name, sha256(text))` è in cache, il
   vettore arriva dalla cache; l'inner riceve **solo** i miss.
3. **Dedup in-call**: testi identici nello stesso `texts` producono un solo miss verso l'inner.
4. **Equivalenza**: i vettori restituiti (cache o inner) sono numericamente identici a quelli che
   l'inner avrebbe prodotto (round-trip float64 esatto) → indice equivalente con/senza cache (FR-005).
5. **Aggiornamento cache**: i vettori dei miss sono scritti in cache prima del ritorno (disponibili al
   rebuild successivo, FR-006).
6. **Degrado non-fatale**: se lo store è illeggibile/scrivibile, `embed` si comporta come se fosse tutto
   miss (chiama l'inner su tutto) ed emette un warning — **mai** solleva per colpa della cache (FR-004).
7. **`[]` su input vuoto**; **`dim`** valorizzato dal primo vettore prodotto (regge il caso 100% hit in
   cui l'inner non viene mai chiamato).
8. **Osservabilità**: emette `embeddings_cache` (hits/misses/total) per chiamata (FR-010).

L'inner conserva il proprio comportamento: retry (`with_retry`), evento `embeddings` coi token,
`EmbeddingError` sui guasti del provider (la cache non li intercetta — un errore del provider sui miss
si propaga come oggi).

## `EmbeddingCache` (store SQLite)

```
EmbeddingCache(index_dir: Path | str)        # apre/crea <index_dir>/embed_cache.sqlite (lazy)
  get(model: str, hashes: list[str]) -> dict[str, list[float]]
      # mappa hash→vettore per le sole chiavi presenti; {} se store assente/illeggibile (+ warning)
  put(model: str, items: list[tuple[str, list[float]]]) -> None
      # INSERT OR IGNORE delle (hash, vettore); no-op su errore store (+ warning); idempotente
```

**Invarianti:**
- Tabella `embeddings(model, content_hash, vector, PK(model, content_hash))`, `CREATE IF NOT EXISTS`.
- Vettore serializzato `array("d", v).tobytes()` ⇄ `array("d").frombytes(blob)`.
- Nessuna eccezione propagata al chiamante per guasti dello store (cattura `sqlite3.Error`).
- Nessuna eviction (MVP); la cancellazione del file è sicura (ricostruita al prossimo embed).

## Eventi di log (schema in data-model.md §3/§4)

- `embeddings` (INFO): `provider`, `texts`, `tokens?` — emesso dall'embedder reale (Azure/Ollama).
- `embeddings_cache` (INFO): `provider`, `hits`, `misses`, `total` — emesso da `CachingEmbedder`.
- `embeddings_cache_unavailable` (WARNING): `provider?`, `reason` — degrado dello store.

## Contratto retro-compatibilità (default off)

Con `SERTOR_EMBED_CACHE=false` (default) `build_indexer` non costruisce il decoratore: il percorso è
identico a prima della feature (nessun file `embed_cache.sqlite` creato, nessun evento `embeddings_cache`).
L'evento `embeddings` coi token (REQ-H5) è **indipendente** dalla cache: presente anche con cache off.
