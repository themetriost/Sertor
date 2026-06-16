# Contract — Indicizzazione incrementale (FEAT-009)

Contratti osservabili della feature. Versione: `index.incremental/1`.

## 1. Vehicle CLI — `sertor-rag index`

```
sertor-rag index [PATH] [--full]
```
- **Default (senza `--full`):** **incrementale** se esiste un manifest valido per la collezione
  `(corpus, provider)`; altrimenti **full automatico** (FR-011). Riprocessa solo i file cambiati,
  rimuove le tracce dei cancellati.
- **`--full`:** forza un **rebuild completo** da zero e riscrive il manifest (reset sicuro, FR-010).
- **Exit code:** `0` successo; `≠0` su errore esplicito (es. `IndexLockedError` se un altro processo sta
  indicizzando lo stesso indice — FR-020).
- **Output:** report con `mode` (full|incremental) e i conteggi delta `added/updated/removed/unchanged/
  cache_hits` (FR-015).
- È l'unico percorso a runtime (Principio XI); il comportamento è identico via MCP dove esposto.

## 2. Service — `IndexingService.index(root, rebuild=False)`

| Condizione | Comportamento |
|---|---|
| `rebuild=True` **o** `SERTOR_INDEX_INCREMENTAL=false` **o** manifest assente/incompatibile | **full**: discover→chunk→embed→reset+upsert→build BM25/graph; (ri)scrive il manifest |
| `rebuild=False` **e** manifest valido **e** `RECONCILE_EVERY` non scattato | **incremental** (vedi §3) |
| `rebuild=False` **e** `RECONCILE_EVERY>0` e contatore al multiplo | **full di riconciliazione** (FR-019) |

**Postcondizione (FR-012, equivalenza):** per la stessa sorgente, lo stato di vector store + BM25 +
code-graph dopo un run incrementale è **identico** a quello prodotto da un full.

## 3. Algoritmo incrementale (semantica)

1. **Lock**: acquisisci il single-writer lock sull'indice; se preso → `IndexLockedError` (FR-020).
2. **Detect**: `stat` di tutti i file; per i candidati (mtime cambiato/nuovo) calcola l'hash; classifica
   UNCHANGED/NEW/MODIFIED/DELETED; se `logic_version` differisce → tutti MODIFIED (FR-013).
3. **Process changed**: per NEW/MODIFIED → chunk + embed (cache FEAT-019) → **upsert** mirato.
4. **Prune**: per MODIFIED/DELETED → **delete** mirato dei vecchi `chunk_id` dal vector store (FR-005).
5. **Rebuild secondari**: assembla l'insieme completo di unità = manifest(UNCHANGED) ∪ fresh(NEW/MODIFIED);
   `LexicalIndex.build(...)` e `CodeGraph.build(...)` pieni (FR-007/008).
6. **Persist**: `apply()` atomico al manifest; aggiorna `reconcile_counter`.
7. **Report**: emetti l'evento osservabile e ritorna `IndexReport` con i conteggi delta.
8. **Unlock** (anche su errore). Su fallimento a metà file → segnala, nessuno stato parziale (FR-014).

## 4. Manifest (schema `sertor.manifest/1`)
SQLite `<index_dir>/index_manifest.sqlite`, namespaced per `(corpus, provider)`; gitignored; nessun
segreto. Tabelle `meta/files/documents/chunks` (vedi data-model.md). Versione incompatibile → il caller
ripiega su full (FR-011).

## 5. Evento di osservabilità (Principio IX, FR-016)
Operazione `index` con campi: `mode`, `collection`, `documents`, `chunks`, `added`, `updated`,
`removed`, `unchanged`, `cache_hits`, `elapsed_ms`. Nessun segreto. Emesso via `log_event` come i run full.

## 6. Manopole (config centralizzata, Principio VIII)
- `SERTOR_INDEX_INCREMENTAL` (bool, default **true**) — disattiva = forza sempre full.
- `SERTOR_INDEX_RECONCILE_EVERY` (int, default **0** = off) — full di riconciliazione ogni N run (FR-019).
