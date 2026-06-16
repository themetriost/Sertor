# Data Model — Refresh incrementale dell'indice (FEAT-009)

Tutto **additivo** sul dominio esistente; nessuna nuova porta. Il manifest è uno **store concreto**
(come `EmbeddingCache`/`MemoryArchive`).

## Entità nuove

### IndexManifest (store concreto, SQLite)
Memoria di «cosa è già indicizzato» per una collezione `(corpus, provider)`. File:
`<index_dir>/index_manifest.sqlite`. Schema (`sertor.manifest/1`):

- **`meta`** — `schema_version TEXT`, `collection TEXT`, `logic_version TEXT`, `reconcile_counter INTEGER`.
- **`files`** — `path TEXT PK`, `mtime REAL`, `content_hash TEXT`, `logic_version TEXT`.
- **`documents`** — `doc_id TEXT PK`, `text TEXT`, `doc_type TEXT`, `language TEXT`.
- **`chunks`** — `chunk_id TEXT PK`, `doc_id TEXT`, `ordinal INTEGER`, `text TEXT`, `doc_type TEXT`,
  `path TEXT`, `metadata_json TEXT`. (Indice su `doc_id`.)

Operazioni (metodi del componente, non una porta):
- `load(collection) -> ManifestState | None` (None/incompatibile → caller fa full, FR-011)
- `classify(current_files) -> Classification` (UNCHANGED/NEW/MODIFIED/DELETED per file, FR-002/003)
- `units_for(doc_ids) -> (documents, chunks)` (ricostruzione BM25/graph dagli invariati, FR-007)
- `apply(added, updated, removed)` (aggiorna files/documents/chunks in transazione atomica, FR-005)
- `chunk_ids_for(doc_ids) -> list[str]` (per il `delete` mirato sul VectorStore)
- `bump_reconcile() -> bool` (gestione `RECONCILE_EVERY`, FR-019)

### FileClassification (enum di dominio)
`UNCHANGED`, `NEW`, `MODIFIED`, `DELETED` — esito del confronto file↔manifest.

### IndexLockedError (errore di dominio, in `domain/errors.py`)
Sollevato quando una seconda indicizzazione concorrente tenta di acquisire il lock già preso (FR-020,
Principio IV). Messaggio azionabile (indica l'indice e che un altro processo sta indicizzando).

## Entità estese (additivo)

### IndexReport (`domain/entities.py`)
Campi nuovi, default 0 (retro-compatibili; il full li popola come «tutto added»):
- `added: int` — file nuovi indicizzati
- `updated: int` — file modificati riprocessati
- `removed: int` — file cancellati le cui unità sono state rimosse
- `unchanged: int` — file saltati
- `cache_hits: int` — chunk serviti dalla cache embeddings (FEAT-019)
- `mode: str` — `"full"` | `"incremental"` (per osservabilità)

## Stato persistito altrove (riuso, non ridefinito)
- **Vector store** (Chroma): record per `chunk_id`; aggiornato con `upsert`/`delete` mirati.
- **BM25 sidecar** (`lexical/<collection>.json`) e **code-graph** (`graph/<corpus>.json`): rigenerati
  pieni dall'insieme completo di unità (mirror `build()`).
- **EmbeddingCache** (`embed_cache.sqlite`): invariato (FEAT-019).

## Transizioni di stato (per file, a ogni run incrementale)
```
presente nel manifest + hash uguale            → UNCHANGED  (skip; refresh mtime)
presente + hash diverso | logic_version diversa → MODIFIED   (delete vecchi chunk, re-chunk+embed+upsert)
assente dal manifest                            → NEW        (chunk+embed+upsert)
nel manifest ma non più sul disco               → DELETED    (delete chunk, rimuovi da manifest)
```
Invarianti: ID chunk stabili preservati; equivalenza col full (FR-012); idempotenza (FR-017); nessuno
stato parziale su errore a metà file (FR-014).
