# Quickstart — Report dell'osservabilità (feature 021)

## Prerequisito

Avere la persistenza di F1 attiva (`SERTOR_OBSERVABILITY=true`) e aver svolto qualche operazione, così
lo store `<index_dir>/observability.sqlite` contiene eventi.

## Usare i report (da libreria)

```python
from sertor_core import build_observability_reports

reports = build_observability_reports()      # cablato dalla configurazione (riusa lo store di F1)

cache = reports.cache_report()               # hit/miss + risparmio stimato
print(cache.total_hits, cache.total_misses, cache.estimated_tokens_saved)

cost = reports.cost_report()                 # token per provider/giorno
print(cost.total_tokens, cost.by_provider)

health = reports.health_report()             # ultimo index: documenti/chunk/dim
latency = reports.latency_report()           # p50/p95 per operazione
reliability = reports.reliability_report()   # errori/ritentativi/astensioni
```

Ogni report accetta un intervallo (`since`/`until`, epoch) e — dove ha senso — la granularità di
raggruppamento (`bucket`, default `day`, da `SERTOR_OBSERVABILITY_BUCKET`).

## Note

- **Nessun dato → report vuoto:** se la persistenza è spenta o non ci sono eventi, i report sono a zeri
  (non un errore): il pannello a valle mostrerà «nessun dato».
- **Risparmio = stima:** `estimated_tokens_saved` è una stima (dedup in-call della cache 019).
- **Solo metriche:** i report aggregano i numeri conservati, mai contenuto grezzo.
- **A valle:** il pannello TUI (F3/F4) e la CLI renderanno questi report; la conversione in € è una
  feature separata che si appoggia a `CostReport`.
