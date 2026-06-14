# Quickstart — Strato di osservabilità persistente (feature 020)

## Abilitare la persistenza

Nel `.env` (o ambiente) del runtime:

```bash
SERTOR_OBSERVABILITY=true     # default: false (eventi solo su stderr, come oggi)
```

Da quel momento ogni evento che il core emette (indicizzazioni, embedding, cache, ricerche) viene
**conservato** in `<index_dir>/observability.sqlite` (es. `.index-sertor/observability.sqlite`),
gitignored. A persistenza spenta non viene creato nulla e il comportamento è identico a oggi.

## Cosa viene conservato

Solo **metriche/metadati** (gli stessi campi che già vedi nei log strutturati), con i segreti **già
mascherati**. Niente testo grezzo (le query non sono salvate). Esempi di eventi: `index`
(documenti/chunk/dim/tempo), `embeddings` (provider/texts/tokens), `embeddings_cache`
(hits/misses/total), `retrieve`, `embeddings_error`/`embeddings_retry`, `low_confidence`.

## Verificare (a valle: FEAT-002 farà i report)

Questa feature dà solo l'**archivio interrogabile**; i report leggibili arriveranno con la feature di
aggregazione. Per ora si verifica che gli eventi siano conservati e recuperabili per tipo e intervallo
(test offline `test_observability_store.py`/`test_observability_capture.py`).

## Note

- **Sicuro da cancellare:** l'archivio è un artefatto rigenerabile; cancellarlo non intacca il
  funzionamento del core (si ricomincia a registrare al prossimo evento).
- **Non rompe nulla:** se l'archivio fosse danneggiato o non scrivibile, le operazioni (index/search)
  **proseguono** comunque; il guasto è solo un avviso nei log.
- **Retention:** per ora l'archivio cresce; una politica di scadenza/rotazione è prevista come gancio e
  verrà definita in seguito.
- **Privacy:** conservare il *testo* (query/conversazioni) sarà una scelta esplicita di una feature
  successiva; di default non accade.
