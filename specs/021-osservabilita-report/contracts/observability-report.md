# Contract — servizio `ObservabilityReports`

Servizio del core (in `services/`) che trasforma gli eventi conservati (letti via la porta
`ObservabilityStore` di F1) in report. È il **seam** verso il pannello (F3/F4) e la CLI: loro chiamano
questi metodi e rendono il risultato, senza ricalcolare nulla.

```
ObservabilityReports(store: ObservabilityStore)
  cache_report(since: float|None = None, until: float|None = None, bucket: str = "day") -> CacheReport
  cost_report(since=None, until=None, bucket="day") -> CostReport
  health_report(since=None, until=None, bucket="day") -> HealthReport
  latency_report(since=None, until=None) -> LatencyReport
  reliability_report(since=None, until=None) -> ReliabilityReport
```

## Garanzie

- **Sola lettura, deterministico:** ogni metodo legge gli eventi via la porta e aggrega con funzioni
  pure; lo stesso insieme di eventi → lo stesso report (FR-009). Nessuno stato mutato, niente persistenza.
- **Dati assenti → report vuoto esplicito:** store assente/illeggibile (la porta degrada a `[]`) o
  intervallo senza eventi → report a **zeri** (liste vuote, totali 0), mai eccezione né `None` (FR-010).
- **Solo via la porta:** il servizio dipende **solo** da `ObservabilityStore` (astrazione), mai
  dall'adapter SQLite — testabile con un fake store (Principio I/V).
- **Privacy:** aggrega solo i campi conservati (metriche già redatte); nessun contenuto grezzo (FR-012).
- **Token mancanti:** eventi senza `tokens` contribuiscono ai conteggi-operazione ma **non** al totale
  token (assenza ≠ zero, FR-004).
- **Stima del risparmio:** `CacheReport.estimated_tokens_saved` è una **stima** (rapporto token/elemento
  × hit), dichiarata tale per via della dedup in-call della 019 (FR-002).

## Wiring (composition root)

```
def build_observability_reports(settings) -> ObservabilityReports:
    return ObservabilityReports(build_observability_store(settings))
```

Riusa lo store di F1; esportato da `__init__.py` come seam per F3/F4/CLI. Nessuna nuova dipendenza.

## Fuori contratto (feature successive)

Rendering/TUI (F3/F4), export OTel (F5), conversione € (FEAT-007, si appoggia a `CostReport`),
freschezza-vs-repo (host-specifica, fuori ambito).
