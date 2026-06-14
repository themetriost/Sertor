# Quickstart — Cache embeddings + token nei log (feature 019)

## Abilitare la cache

Nel `.env` (o ambiente) del runtime:

```bash
SERTOR_EMBED_CACHE=true     # default: false (rebuild full, comportamento odierno)
```

La cache vive in `<index_dir>/embed_cache.sqlite` (es. `.sertor/.index/embed_cache.sqlite` per un
install, `.index-sertor/embed_cache.sqlite` per il dogfood). È git-ignored (artefatto cache) e sicura da
cancellare in qualunque momento: la cancellazione causa al più un ri-embedding al prossimo `index()`.

## Verificare il risparmio (SC-001/006)

```bash
# 1) primo index (cache a freddo): tutti i chunk vengono embeddati
sertor-rag index . -v
#   log: op=embeddings_cache hits=0 misses=N total=N
#        op=embeddings provider=azure:text-embedding-3-large texts=N tokens=...

# 2) secondo index sullo stesso corpus invariato (cache calda): zero embedding
sertor-rag index . -v
#   log: op=embeddings_cache hits=N misses=0 total=N
#        (nessun token consumato: l'evento embeddings riporta texts=0 o tokens assenti)
```

Il confronto dei due `embeddings_cache` (misses N → 0) e dei token tra le due esecuzioni quantifica il
risparmio.

## Token nei log (REQ-H5, indipendente dalla cache)

Anche con cache **off**, l'evento `embeddings` riporta i token quando il provider li espone:

```bash
sertor-rag index . --log-json
# {"operation": "embeddings", "provider": "azure:text-embedding-3-large", "texts": 1755, "tokens": 412330}
```

Con provider che non riportano token (alcune configurazioni Ollama) il campo `tokens` è semplicemente
assente — l'evento è emesso comunque, senza errori.

## Note operative

- **Cambio modello/provider**: la cache è keyed su `(modello, contenuto)`; cambiando provider i vettori
  vecchi non vengono serviti (vengono ri-embeddati col nuovo modello) — nessuna pulizia manuale serve.
- **Costo Azure**: con cache attiva, i re-index del rituale di step (frequenti) ripagano l'embedding
  **solo** per i chunk effettivamente cambiati.
- **Dogfood**: dopo il merge si può abilitare `SERTOR_EMBED_CACHE=true` nel `.env` del corpus `sertor`
  per tagliare il costo dei rebuild ricorrenti.
