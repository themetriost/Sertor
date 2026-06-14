# Contract — cattura degli eventi (`EventPersistenceHandler`)

Il bridge da `logging` allo store. È un dettaglio di `observability/`; il contratto stabile verso il
resto è la porta [observability-store](./observability-store.md).

## Comportamento

```
EventPersistenceHandler(store: ObservabilityStore)  # logging.Handler
  emit(record: LogRecord):
    if not hasattr(record, "operation"):   # solo eventi strutturati di log_event
        return
    fields = { campi 'extra' aggiunti da log_event, già redatti }   # esclusi gli attr standard del record
    store.record_event(ts=record.created, operation=record.operation, fields=fields)
```

## Garanzie

1. **Additività totale:** `log_event` e i call-site **non cambiano**. Il handler si limita a leggere il
   `LogRecord` che `log_event` già produce (`extra={"operation": op, **safe}`).
2. **Solo eventi strutturati:** i record senza `operation` (log generici di librerie/app) sono ignorati.
3. **Privacy:** i campi letti sono quelli **già redatti** da `log_event` (`safe`); il handler non
   re-introduce contenuto. Di default solo metriche.
4. **Non-fatale (FR-007):** un'eccezione in `emit` è gestita da `logging` (`handleError`) e **non risale**
   all'operazione osservata. (Lo store a sua volta cattura i propri errori e logga un warning.)
5. **Default-off (FR-004):** il handler è attaccato al logger `sertor_core` **solo** dal composition root
   quando `observability_enabled`; altrimenti non esiste → nessun overhead, nessuno store.
6. **Non-bloccante (FR-006):** insert sincrono a bassa cardinalità (eventi per-operazione); via di fuga
   documentata = `QueueHandler`/`QueueListener` se il volume crescerà (research D5).

## Wiring (composition root)

```
if settings.observability_enabled:
    from sertor_core.observability.store import SqliteObservabilityStore
    from sertor_core.observability.capture import EventPersistenceHandler
    store = SqliteObservabilityStore(settings.index_dir)
    logging.getLogger("sertor_core").addHandler(EventPersistenceHandler(store))
```

Import lazy dentro il ramo abilitato (Principio III: niente costo a feature spenta). Lo store è anche
restituito/raggiungibile per i consumatori a valle (FEAT-002) tramite una factory `build_*` dedicata
(es. `build_observability_store`), da definire quando F2 lo userà — fuori ambito qui.

## Quali campi finiscono in `fields`

Gli attributi che `log_event` ha aggiunto via `extra` (es. per `index`: `collection`, `provider`,
`documents`, `chunks`, `embedding_dim`, `elapsed_ms`), **esclusi** gli attributi standard del
`LogRecord` (`msg`, `args`, `levelname`, `name`, …) e `operation` (già colonna a sé). In pratica: la
differenza tra gli attributi del record e quelli di un `LogRecord` "vuoto" — i campi applicativi.
