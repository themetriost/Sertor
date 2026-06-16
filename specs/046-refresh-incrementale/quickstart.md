# Quickstart — Refresh incrementale dell'indice (FEAT-009)

## Uso normale (incrementale di default)
```
sertor-rag index .
```
Dal secondo run in poi, se esiste già un indice per la collezione, Sertor **riprocessa solo i file
cambiati** e rimuove le tracce di quelli cancellati. Il report mostra `mode=incremental` e i conteggi:
`added / updated / removed / unchanged / cache_hits`.

## Forzare un rebuild completo (reset sicuro)
```
sertor-rag index . --full
```
Ricostruisce tutto da zero e riscrive il manifest. È anche il **fallback automatico** se il manifest
manca o è incompatibile (non viene mai prodotto un indice parziale).

## Manopole (`.env`)
```
# Refresh incrementale dell'indice (FEAT-009)
SERTOR_INDEX_INCREMENTAL=true        # default; false = forza sempre il full
SERTOR_INDEX_RECONCILE_EVERY=0       # 0 = off; N>0 = full di riconciliazione ogni N run incrementali
```

## Cosa aspettarsi
- **Correttezza garantita:** dopo un run incrementale i risultati di ricerca sono identici a un full
  rebuild (vettore + parole chiave + grafo allineati).
- **Cancellazioni:** un file eliminato sparisce dai risultati al run successivo.
- **Cambio di logica:** se cambia il modo di spezzare/analizzare i file, i file interessati vengono
  riprocessati automaticamente (niente residui vecchi).
- **Concorrenza:** due indicizzazioni simultanee dello stesso indice non sono permesse (la seconda
  fallisce con un messaggio chiaro) — niente corruzione.

## Verifica rapida (dogfood)
```
sertor-rag index .            # run 1: full automatico (manifest assente) → mode=full
# (modifica un file)
sertor-rag index .            # run 2: mode=incremental, updated=1, unchanged=N-1
sertor-rag search "..."       # riflette la modifica
```
