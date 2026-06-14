# Data Model — feature 019

Nessuna entità di **dominio** nuova (il contratto `RetrievalResult`/`EmbeddedChunk` e le porte restano
invariati — FR-011). Le entità qui sono artefatti di persistenza e schemi di log, confinati in
`adapters/embeddings/`.

## 1. Voce di cache embedding (riga SQLite)

Tabella `embeddings` nel file `<index_dir>/embed_cache.sqlite`:

| Campo | Tipo SQLite | Significato |
|---|---|---|
| `model` | TEXT | `embedder.name` (es. `azure:text-embedding-3-large`, `ollama:nomic-embed-text`). Parte della chiave → isola gli spazi vettoriali (FR-002). |
| `content_hash` | TEXT | `sha256(text.encode("utf-8")).hexdigest()` del testo del chunk embeddato. |
| `vector` | BLOB | `array("d", vector).tobytes()` — float64, round-trip esatto (D4/FR-005). |

- **Primary key:** `(model, content_hash)` → lookup O(1) per chunk, idempotenza della scrittura
  (`INSERT OR IGNORE`: ri-scrivere la stessa chiave è un no-op).
- **Schema bootstrap:** `CREATE TABLE IF NOT EXISTS` alla prima apertura (idempotente).
- **Ciclo di vita:** scritta dai miss di `CachingEmbedder.embed`; letta in blocco a inizio `embed`;
  **mai** cancellata dalla feature (cancellazione manuale sicura = solo ri-embedding). Nessuna eviction
  nell'MVP (Assumptions della spec).
- **Validazione/robustezza:** errori SQLite (corruzione/lock) → trattati come miss + warning, mai
  fatali (FR-004).

## 2. Manopola di configurazione (`Settings`)

| Campo | Env | Default | Significato |
|---|---|---|---|
| `embed_cache_enabled` | `SERTOR_EMBED_CACHE` | `False` | Abilita il decoratore cache sul percorso d'indicizzazione (FR-007). Off = comportamento odierno (rebuild full). Parsing booleano tollerante (`_bool_env`, come `SERTOR_GRAPH`/`SERTOR_RERANK`). |

La **sede** della cache non è una manopola separata: deriva da `Settings.index_dir`
(`<index_dir>/embed_cache.sqlite`), già auto-localizzato e git-ignored — coerente col sidecar BM25
(`<index_dir>/lexical/…`).

## 3. Evento di log `embeddings` (successo embedding, REQ-H5)

Emesso una volta per `EmbeddingProvider.embed()` (Azure/Ollama), livello INFO:

| Campo | Sempre presente | Significato |
|---|---|---|
| `provider` | sì | `embedder.name`. |
| `texts` | sì | numero di testi embeddati in questa chiamata. |
| `tokens` | **solo se disponibile** | conteggio token riportato dal provider (`usage.total_tokens` Azure; `prompt_eval_count` Ollama). **Omesso** quando assente (FR-009 — niente `0`/`None` finto). |

Si affianca all'evento `embeddings_error` già esistente (che resta invariato) e all'evento `index` di
`IndexingService`.

## 4. Evento di log `embeddings_cache` (REQ-H4 osservabilità, FR-010)

Emesso una volta per `CachingEmbedder.embed()`, livello INFO:

| Campo | Significato |
|---|---|
| `provider` | `embedder.name` dell'inner. |
| `hits` | chunk serviti dalla cache (non ri-embeddati). |
| `misses` | chunk embeddati realmente (passati all'inner). |
| `total` | `hits + misses`. |

Evento di degrado correlato: `embeddings_cache_unavailable` (WARNING, campo `reason`) quando lo store
SQLite non è leggibile/scrivibile — la `embed` prosegue come se fosse tutto miss.

## 5. Relazioni

```
build_indexer(settings)                      [composition.py]
  └─ build_embedder(settings, cache=True)     se settings.embed_cache_enabled
       └─ CachingEmbedder(inner, EmbeddingCache(index_dir))   [adapters/embeddings/cache.py]
            ├─ inner = AzureEmbedder | OllamaEmbedder   (porta EmbeddingProvider)
            └─ EmbeddingCache → embed_cache.sqlite       (tabella `embeddings`)

IndexingService.index() → embedder.embed(texts)   ← decoratore trasparente (servizio invariato)
```
