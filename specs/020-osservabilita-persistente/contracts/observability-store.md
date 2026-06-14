# Contract — porta `ObservabilityStore`

La 7ª porta del core (in `domain/ports.py`), `Protocol` `runtime_checkable` come le altre. È il **seam**
tra "dove vivono gli eventi" (questa feature) e "chi li interroga" (FEAT-002 aggregazione/report).

```
@runtime_checkable
class ObservabilityStore(Protocol):
    def record_event(self, ts: float, operation: str, fields: dict) -> None:
        """Persiste un evento osservato (istante, tipo di operazione, campi già redatti)."""
        ...
    def query_events(
        self, operation: str | None, since: float | None, until: float | None
    ) -> list[ObservedEvent]:
        """Eventi filtrati per operation (None = tutti) e finestra [since, until] (None = aperta)."""
        ...
```

`ObservedEvent` = dataclass di dominio `(ts: float, operation: str, fields: dict)`.

## Garanzie

- **record_event**: aggiunge un evento (append); non solleva al chiamante su guasto dello store (lo
  cattura e logga). Ogni chiamata è un evento distinto (nessuna deduplicazione).
- **query_events**: ritorna gli eventi che soddisfano i filtri, **ordinati per `ts`** crescente; `[]` se
  nessuno o se lo store è assente/illeggibile (con warning). I filtri `None` sono "non vincolare".
- **Nessun tipo di backend** (sqlite3) risale nel dominio: la porta parla `float`/`str`/`dict`/
  `ObservedEvent`.
- **Privacy:** `fields` contiene i campi **già redatti** (la redazione avviene in `log_event` a monte);
  di default solo metriche (nessun contenuto grezzo).

## Consumatori

- **Scrittura:** `EventPersistenceHandler` (questa feature) — chiama `record_event` per ogni evento
  strutturato catturato dal logging.
- **Lettura:** **FEAT-002** (aggregazione/report) — chiamerà `query_events` per costruire i report
  (bucket temporali, somme di campi, correlazioni). Le aggregazioni NON sono in questa porta: la porta dà
  l'accesso grezzo agli eventi, F2 ci costruisce sopra.

## Adapter concreto

`SqliteObservabilityStore(index_dir)` (in `observability/store.py`): SQLite stdlib, file
`<index_dir>/observability.sqlite` gitignored. Cablato dal composition root **solo** se
`Settings.observability_enabled`. Import lazy (zero dipendenze nuove obbligatorie).
