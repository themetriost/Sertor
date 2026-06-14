# Research — Servizio di aggregazione/report (feature 021)

Decisioni di design risolte. Nessuna NEEDS CLARIFICATION residua.

## D1 — Forma dell'API: una facciata con metodi per famiglia di report

- **Decision:** un servizio `ObservabilityReports(store)` con un metodo per famiglia: `cache_report`,
  `cost_report`, `health_report`, `latency_report`, `reliability_report`. Ciascuno accetta
  `since`/`until` (opzionali) e — dove ha senso — un `bucket` (granularità). Ritorna un **dataclass**
  di report (valore immutabile).
- **Rationale:** leggibilità (Principio VII) e consumo semplice da F3/F4 (un metodo = una vista);
  evita un'unica entry-point con un selettore stringa (meno scopribile, meno tipizzata).
- **Alternatives considered:** un solo `report(kind, ...)` con dispatch — più opaco; funzioni libere
  senza facciata — il composition root preferisce un oggetto cablato (build_*), coerente col resto.

## D2 — Aggregazione: funzioni pure in memoria sugli eventi della porta

- **Decision:** ogni report fa `store.query_events(operation, since, until)` per i tipi rilevanti e
  aggrega **in memoria** con funzioni pure. Niente SQL di aggregazione nello store (lo store resta il
  minimo di F1); l'aggregazione vive in F2.
- **Rationale:** mantiene F1 semplice e F2 testabile con un fake store; l'aggregazione su migliaia di
  eventi in memoria è millisecondi. Le funzioni pure → determinismo (FR-009) e test facili.
- **Alternatives considered:** spingere le aggregazioni in SQL nello store — accoppia F2 al backend e
  gonfia la porta; respinta (lo store resta un KV temporale).

## D3 — Bucket temporali: per giorno (UTC) di default, granularità selezionabile

- **Decision:** funzione pura `bucket_key(ts, granularity)` che mappa un `ts` epoch al bucket (default
  `"day"` → `YYYY-MM-DD` in UTC via `time.gmtime`/`strftime`). Granularità supportate minime: `day`
  (estendibile a `hour`). I `SeriesPoint` sono ordinati per bucket.
- **Rationale:** UTC deterministico (no fuso locale → test ripetibili); il giorno è la granularità
  più utile per «quanto ho speso/risparmiato». Configurabile via `Settings` (default in Settings).
- **Alternatives considered:** fuso locale (non deterministico nei test); bucket per-evento (è già la
  serie grezza, non un report).

## D4 — Percentili di latenza: calcolo manuale deterministico

- **Decision:** p50/p95 con metodo del **rango su lista ordinata** (nearest-rank): dato l'elenco
  ordinato degli `elapsed_ms`, l'indice = `ceil(p/100 * n) - 1`. Deterministico, nessuna dipendenza.
- **Rationale:** semplice, riproducibile, niente ambiguità di interpolazione tra librerie; sufficiente
  per p50/p95 di latenze operative.
- **Alternatives considered:** `statistics.quantiles` (interpolazione, default method='exclusive' → meno
  intuitivo per p95 su pochi campioni); respinto per chiarezza/determinismo.

## D5 — Stima del risparmio della cache (caveat dedup 019)

- **Decision:** dal report cache, `estimated_tokens_saved` = `hits * (token_per_elemento medio)` dove
  il rapporto token/elemento è ricavato dagli eventi `embeddings` (somma `tokens` / somma `texts`)
  nell'intervallo. **Dichiarato come stima** nel dataclass (campo/nome esplicito), mai come misura.
- **Rationale:** è il segnale che l'utente vuole («quanto ho risparmiato»), reso onesto. La
  deduplicazione in-call della 019 fa sì che `texts` (verso il provider) ≤ chunk processati → il
  rapporto è una stima, non esatta. Documentato (FR-002, Assumptions della spec).
- **Alternatives considered:** non stimare (perde il valore richiesto); stimare con un prezzo fisso
  per token (è la € di FEAT-007, fuori ambito).

## D6 — Dati assenti: report vuoto esplicito

- **Decision:** se `query_events` ritorna `[]` (store assente/illeggibile — F1 degrada a `[]` — o
  intervallo vuoto), ogni report ritorna il proprio **dataclass a zeri** (liste vuote, totali 0),
  **non** un'eccezione né `None` (FR-010, Principio IV).
- **Rationale:** degradazione onesta; il pannello a valle mostra «nessun dato» senza crash.

## D7 — Manopola e wiring

- **Decision:** granularità di default in `Settings` (es. `observability_bucket` = `"day"`); il
  composition root espone `build_observability_reports(settings)` che riusa `build_observability_store`
  e costruisce il servizio. Esportato da `__init__` (seam per F3/F4/CLI).
- **Rationale:** coerente con le altre `build_*`; default in Settings (Principio VIII).
