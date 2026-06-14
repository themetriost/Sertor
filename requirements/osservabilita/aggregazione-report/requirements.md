# Requisiti — Servizio di aggregazione e report

<!-- Deriva da: FEAT-002 (epica `requirements/osservabilita/epic.md`) -->

## 1. Contesto e problema (perché)

FEAT-001 ha introdotto lo **strato di osservabilità persistente**: un archivio locale
interrogabile che cattura — senza perderli — gli eventi già emessi da `log_event` in
`src/sertor_core/observability/logging.py`. Gli eventi disponibili oggi sono:

| Evento | Campi chiave |
|--------|-------------|
| `index` | `collection`, `provider`, `documents`, `chunks`, `embedding_dim`, `elapsed_ms` |
| `embeddings` | `provider`, `texts`, `tokens` |
| `embeddings_cache` | `provider`, `hits`, `misses`, `total` |
| `embeddings_cache_unavailable` | `provider`, `reason` |
| `embeddings_error` | `provider`, `reason`, `retriable` |
| `embeddings_retry` | `provider`, `attempt`, `reason`, `wait_ms` |
| `low_confidence` | `collections`, `provider`, `min_score`, `best_score`, `candidates` |
| `retrieve` | `collection`, `provider`, `doc_type`, `k`, `results`, `elapsed_ms` |
| `config_no_env_found` | (segnale di configurazione) |

Gli eventi sono presenti nel codice reale: `embeddings` e `embeddings_error` emessi dagli adapter
`src/sertor_core/adapters/embeddings/azure.py` e `ollama.py`; `embeddings_cache` e
`embeddings_cache_unavailable` dall'adapter `cache.py`; `embeddings_retry` da `_retry.py`;
`index` dal servizio `src/sertor_core/services/indexing.py`; `retrieve` e `low_confidence` dal
servizio `src/sertor_core/services/retrieval.py`.

Il problema: questi eventi, ora persistiti da FEAT-001, rimangono **dati grezzi**. Non si può
rispondere direttamente a domande quali: *quanto mi sta costando l'indicizzazione? quanti token
ha risparmiato la cache? quante query restano senza risposta? le latenze stanno crescendo?* — senza
aggregarli a mano. FEAT-002 fornisce il **servizio del core** che esegue tali aggregazioni e
produce report strutturati. Non è la UI (FEAT-003/004) né la persistenza (FEAT-001): è il
consumatore dello store che trasforma eventi grezzi in **risposte alle domande chiave**.

> Il *come* (struttura del servizio, formato dei report in memoria, schema delle query allo store)
> è materia della **fase di design** a valle. Qui solo *cosa* e *perché*.

## 2. Obiettivi e criteri di successo

- **OB-1 — Report cache:** è possibile ottenere hit/miss nel tempo e il risparmio cumulativo
  stimato in token (token risparmiati = somma degli hit × token/embedding ricavati dagli eventi
  `embeddings` reali). *SC-1:* dato un insieme di eventi `embeddings_cache` e `embeddings`
  persistiti, il servizio produce un aggregato con `total_hits`, `total_misses`, `estimated_tokens_saved`
  coerenti con la somma degli eventi.
- **OB-2 — Report costo/consumo:** è possibile vedere i token cumulativi per provider e per
  intervallo (giorno, per re-index). *SC-2:* dato un insieme di eventi `embeddings` persistiti,
  il servizio produce aggregati `tokens_by_provider` e `tokens_by_interval` sommati correttamente.
  La conversione in euro **non** è compito di questa feature (è FEAT-007): qui si producono gli
  aggregati di token su cui FEAT-007 si appoggerà.
- **OB-3 — Report corpus/indice:** è possibile ottenere `#doc`, `#chunk`, `embedding_dim`
  dall'ultimo evento `index` e il trend nel tempo. *SC-3:* dato un insieme di eventi `index`
  persistiti, il servizio identifica correttamente l'ultimo evento per collection e produce la serie
  storica.
- **OB-4 — Report latenze:** è possibile ottenere la distribuzione p50/p95 di `elapsed_ms` per
  operation (`index`, `retrieve`). *SC-4:* dato un insieme di eventi con campo `elapsed_ms`, il
  servizio calcola p50 e p95 deterministicamente sullo stesso input.
- **OB-5 — Report affidabilità:** è possibile vedere conteggi di `embeddings_error` e
  `embeddings_retry`, e il tasso di `low_confidence` (astensioni sul totale delle retrieve).
  *SC-5:* i conteggi corrispondono esattamente al numero di eventi di quel tipo nell'intervallo
  richiesto; il tasso è `low_confidence_count / retrieve_count` sullo stesso intervallo.
- **OB-6 — Determinismo:** aggregare gli stessi eventi produce sempre lo stesso risultato.
  *SC-6:* la suite di test produce output identici su input fisso, offline, senza rete.
- **OB-7 — Testabilità offline:** tutti i report sono verificabili con eventi simulati nello
  store, senza cloud né rete. *SC-7:* la CI (senza cloud, `pytest -m "not cloud"`) esegue i test
  dei report senza dipendenze esterne.

## 3. Stakeholder e attori

- **FEAT-001 (strato di osservabilità persistente):** la sorgente — il servizio di aggregazione
  interroga lo store via la porta/astrazione definita da FEAT-001; non la reimplementa.
- **FEAT-003/004 (pannello TUI — vista live e report sfogliabili):** consumatori primari del
  servizio di aggregazione; la TUI legge i report prodotti qui, senza reimplementare aggregazioni.
- **FEAT-007 (stima costi in €):** si appoggia sugli aggregati di token prodotti da questo
  servizio per calcolare la stima monetaria.
- **Owner/operatore del progetto ospite:** vuole risposte alle domande chiave (costo, cache,
  salute, affidabilità) senza strumenti esterni.
- **Agente LLM (consumatore indiretto):** un agente con accesso al report ha contesto
  quantitativo sul funzionamento del sistema, utile per diagnosi.

## 4. Ambito

### In ambito

- Un **servizio nel core** (`sertor-core`) che interroga lo store di FEAT-001 tramite la sua
  porta/astrazione e produce aggregati strutturati.
- I cinque report canonici: **cache** (hit/miss + risparmio stimato), **costo/consumo** (token per
  provider e per intervallo), **corpus/indice** (doc/chunk/dim + trend), **latenze** (p50/p95 per
  operation), **affidabilità** (errori/retry/low_confidence).
- La **granularità temporale** dei report: aggregazione per giorno e per re-index (evento `index`
  come marker di sessione).
- Il **calcolo del risparmio stimato in token** dagli hit della cache: basato sugli eventi reali
  `embeddings` (campo `tokens`) e `embeddings_cache` (campo `hits`), senza stime hardcoded.
- La garanzia che le aggregazioni siano **funzioni pure/deterministiche** dato lo stesso insieme
  di eventi.
- L'essere **additivo**: non modifica il contratto di `log_event`, non altera FEAT-001 né i
  consumatori di logging esistenti.
- L'essere **host-agnostico**: opera su qualunque progetto ospite, come il resto del core
  (Principio X).
- Il vincolo **privacy-by-default**: aggrega solo ciò che è persistito nello store; di default
  metriche, mai contenuto grezzo (coerente con REQ-E8/E9 dell'epica e FEAT-001 REQ-008).

### Fuori ambito

- **Persistenza degli eventi** → FEAT-001 (questo servizio è solo un consumatore dello store).
- **Pannello TUI** (visualizzazione live e sfogliabile) → FEAT-003/004.
- **Conversione token → stima in €** → FEAT-007.
- **Export OpenTelemetry** → FEAT-005.
- **Freschezza del corpus** (confronto ultimo `index` vs modifiche del repo via `git log`):
  richiede informazioni host-specifiche esterne al core → rinviato a FEAT-010/Could o alla fase
  di design (vedi §10, DA-002-AGG).
- **Metriche del code-graph e del wiki** → FEAT-010.
- **Metriche di qualità/pertinenza del retrieval** (groundedness, rilevanza): epica separata.
- **Definizione dello schema** dei dati di report restituiti (strutture, campi, tipi): materia
  di design.
- **Alerting, SLO, notifiche** automatiche.

## 5. Requisiti funzionali (EARS)

### 5.1 Contratto generale del servizio

- **REQ-001 (Ubiquitous):** *The aggregation service shall consume the observability store
  exclusively through the port/abstraction defined by FEAT-001, without re-implementing
  persistence or querying the store directly through a concrete adapter.*

- **REQ-002 (Ubiquitous):** *The aggregation service shall reside within the core (`sertor-core`)
  and shall expose its report-producing capabilities without any UI, rendering or presentation
  logic.*

- **REQ-003 (Ubiquitous):** *The aggregation service shall be host-agnostic: it shall operate on
  any host project without changes to its body; only configuration may differ (Principio X).*

- **REQ-004 (Ubiquitous):** *The aggregation service shall not alter the `log_event` contract,
  shall not modify the FEAT-001 store schema, and shall not affect existing log consumers.*

- **REQ-005 (Unwanted):** *If the observability store is empty or unavailable, then the
  aggregation service shall return empty/zero-value reports and shall not raise an error that
  propagates to the caller (graceful degradation).*

- **REQ-006 (Ubiquitous):** *The aggregation service shall accept an optional time-range filter
  (start/end) applicable to all reports, so that consumers can request aggregates over a specific
  interval.*

### 5.2 Report cache

- **REQ-007 (Event-driven):** *When the cache report is requested, the aggregation service shall
  compute `total_hits`, `total_misses` and `hit_rate` from all `embeddings_cache` events in the
  requested interval.*

- **REQ-008 (Event-driven):** *When the cache report is requested, the aggregation service shall
  produce a time-series of `(timestamp_bucket, hits, misses)` at the configured temporal
  granularity (day by default), enabling trend visualisation over time.*

- **REQ-009 (Event-driven):** *When the cache report is requested and `embeddings` events with a
  `tokens` field are available, the aggregation service shall compute `estimated_tokens_saved` as
  the sum of `hits × (tokens / texts)` derived from co-occurring `embeddings` events, without any
  hardcoded price or token-count assumption.*

- **REQ-010 (Unwanted):** *If no `embeddings` event with a `tokens` field is present in the
  interval, then the aggregation service shall omit `estimated_tokens_saved` from the cache
  report (or mark it explicitly as unavailable) rather than returning a misleading zero.*

### 5.3 Report costo/consumo token

- **REQ-011 (Event-driven):** *When the token-consumption report is requested, the aggregation
  service shall compute cumulative `tokens` broken down by `provider`, summing over all
  `embeddings` events in the requested interval.*

- **REQ-012 (Event-driven):** *When the token-consumption report is requested, the aggregation
  service shall produce a time-series of `(timestamp_bucket, provider, tokens)` aggregated at
  the configured temporal granularity, so that FEAT-007 can apply per-provider pricing on top.*

- **REQ-013 (Event-driven):** *When the token-consumption report is requested, the aggregation
  service shall identify re-index sessions (boundaries marked by `index` events) and provide
  per-session token totals in addition to the time-based aggregation.*

- **REQ-014 (Unwanted):** *If an `embeddings` event does not carry a `tokens` field, then the
  aggregation service shall exclude it from token sums and shall not count it as zero tokens
  (partial data must not distort cumulative totals).*

### 5.4 Report corpus/indice

- **REQ-015 (Event-driven):** *When the corpus report is requested, the aggregation service shall
  return the snapshot from the most recent `index` event for each collection:
  `documents`, `chunks`, `embedding_dim`, `provider`, `elapsed_ms`, and the event timestamp.*

- **REQ-016 (Event-driven):** *When the corpus report is requested, the aggregation service shall
  produce the historical series of `(timestamp, collection, documents, chunks)` from all `index`
  events in the requested interval, enabling corpus-size trend visualisation.*

- **REQ-017 (Unwanted):** *If no `index` event is present in the store, then the aggregation
  service shall return an explicit "never indexed" indicator rather than empty numeric fields.*

### 5.5 Report latenze

- **REQ-018 (Event-driven):** *When the latency report is requested, the aggregation service
  shall compute p50 and p95 of `elapsed_ms` for each distinct `operation` that carries that
  field (at minimum `index` and `retrieve`), over the requested interval.*

- **REQ-019 (Ubiquitous):** *The latency percentile computation shall be deterministic and
  pure: given the same ordered set of `elapsed_ms` values, it shall always produce the same
  p50 and p95, with no dependency on external state or time.*

- **REQ-020 (Unwanted):** *If fewer than two `elapsed_ms` samples are available for an
  operation, then the aggregation service shall not compute percentiles for that operation and
  shall signal the insufficient-sample condition explicitly.*

### 5.6 Report affidabilità

- **REQ-021 (Event-driven):** *When the reliability report is requested, the aggregation service
  shall count `embeddings_error` events (total and by `provider`) and `embeddings_retry` events
  (total, by `provider`, cumulative `attempt` distribution) over the requested interval.*

- **REQ-022 (Event-driven):** *When the reliability report is requested, the aggregation service
  shall compute the `low_confidence_rate` as the ratio of `low_confidence` event count to
  `retrieve` event count over the same interval, expressing the fraction of queries that
  triggered an abstention.*

- **REQ-023 (Unwanted):** *If no `retrieve` event is present in the interval, then the
  aggregation service shall return a `low_confidence_rate` of `null`/unavailable rather than
  zero, to avoid misleading the consumer.*

- **REQ-024 (Event-driven):** *When the reliability report is requested, the aggregation service
  shall include the count of `embeddings_cache_unavailable` events, so that cache infrastructure
  failures are visible alongside embedding errors.*

### 5.7 Determinismo e privacy

- **REQ-025 (Ubiquitous):** *Each aggregation function shall be pure and deterministic: given
  the same set of persisted events and the same parameters, it shall always return the same
  result, with no side-effects on the store.*

- **REQ-026 (Ubiquitous):** *The aggregation service shall aggregate only metric/metadata fields
  already present in the store; it shall never request, expose or re-derive raw content (e.g.
  query text) not explicitly persisted with opt-in (REQ-E8/E9 of the epic).*

## 6. Requisiti non funzionali

- **RNF-001 — Testabilità offline:** tutti i report sono verificabili offline con eventi simulati
  nello store; la CI senza cloud (`pytest -m "not cloud"`) deve eseguire i test di ogni report
  senza dipendenze esterne (Principio V, coerente con FEAT-001 RNF-001).
- **RNF-002 — Nessuna nuova dipendenza obbligatoria:** il servizio di aggregazione non introduce
  librerie obbligatorie; se ne servisse, devono essere extra opzionali (Principio III, coerente
  con `graph`/`rerank`/`tui`/`otel`).
- **RNF-003 — Purezza funzionale delle aggregazioni:** le funzioni di aggregazione sono pure (no
  stato globale mutabile, no side-effect sullo store); una doppia chiamata con lo stesso input
  restituisce output identici (Principio VI / OB-6).
- **RNF-004 — Overhead trascurabile:** le query allo store per produrre i report non impattano
  le operazioni di indicizzazione/ricerca in corso; le aggregazioni non sono mai sul percorso
  caldo (read-only, asincronicamente rispetto alle operazioni core).
- **RNF-005 — Retro-compatibilità:** se FEAT-001 non è attivata (store assente), il servizio
  risponde con report vuoti/zero-value senza eccezioni propagate (REQ-005).

## 7. Vincoli, assunzioni e dipendenze

- **Dipendenza da FEAT-001 (bloccante):** il servizio di aggregazione presuppone lo store di
  FEAT-001; senza di esso i report sono vuoti (REQ-005). La porta/astrazione di FEAT-001 è
  l'unica interfaccia verso lo store (REQ-001).
- **Composizione nel composition root:** come tutti i componenti del core, l'istanza del servizio
  è costruita in `composition.py` da `Settings`; non si auto-istanzia (Principio I/VIII).
- **Additività (non-breaking):** il servizio è un nuovo componente; non modifica `log_event`,
  non altera FEAT-001, non rompe i consumatori esistenti (REQ-004).
- **Privacy condivisa con FEAT-001:** il contratto di aggregare solo metriche (REQ-026) è
  coerente con il default metriche-only di FEAT-001 (REQ-008 di FEAT-001) e con REQ-E8/E9
  dell'epica (decisione 2026-06-14).
- **Granularità temporale configurabile:** la granularità dei bucket temporali dei report
  (default: giorno) deve derivare dalla configurazione centralizzata, non essere hardcoded nei
  componenti (Principio VIII). Il valore di default è assunto "giorno", ma è soggetto a
  conferma (vedi §10, DA-003-AGG).
- **Assunzione — campi presenti:** il calcolo di `estimated_tokens_saved` presuppone che gli
  eventi `embeddings` abbiano il campo `tokens` (emesso dagli adapter quando il provider lo
  restituisce). Se assente, il campo del report è marcato unavailable (REQ-010/014).
- **Assunzione — timestamp degli eventi:** lo store di FEAT-001 persiste un timestamp per ogni
  evento (requisito REQ-001 di FEAT-001); questa feature presuppone che quel timestamp sia
  disponibile per qualunque filtro temporale.
- **Confine con FEAT-007:** gli aggregati di token prodotti da questo servizio sono la materia
  prima di FEAT-007 (stima €); questo servizio non conosce prezzi né valute.

## 8. Rischi

- **R-1 — Stima token risparmiati imprecisa:** il calcolo di `estimated_tokens_saved` dipende dal
  campo `tokens` degli eventi `embeddings`, che è presente solo quando il provider lo restituisce
  (es. Azure sì, Ollama opzionale). Se mancante, la stima non è disponibile (REQ-010 mitiga con
  segnalazione esplicita). Complicazione futura: la deduplicazione in-call della feat. 019 può
  alterare la correlazione hit/token (vedi §10, DA-004-AGG).
- **R-2 — Granularità temporale rigida:** se la granularità (giorno) è hardcodata, report su
  periodi brevi o molto lunghi non sono utili. Mitigazione: configurabile (vincolo §7).
- **R-3 — Freschezza del corpus non calcolabile offline:** il confronto "ultimo index vs
  modifiche del repo" richiede `git log` o metadati del filesystem, che sono host-specifici e
  fuori dal core. Rinviato o risolto in design (vedi §10, DA-002-AGG).
- **R-4 — Accoppiamento allo schema degli eventi:** se FEAT-001 cambia i nomi dei campi degli
  eventi, i report devono essere aggiornati. Mitigazione: mantenere il mapping centralizzato in
  un unico punto (design).
- **R-5 — Percentili su campioni piccoli:** con pochi eventi (es. un solo `index`) i percentili
  non sono significativi. REQ-020 mitiga con segnalazione esplicita di campione insufficiente.

## 9. Prioritizzazione (MoSCoW)

| Item | REQ | MoSCoW | Perché |
|------|-----|--------|--------|
| Contratto generale: porta FEAT-001, no UI, host-agnostico, non-breaking | REQ-001..006 | **Must** | Architettura e additività obbligatorie (Principi I/X/IV) |
| Report cache: hit/miss/trend + risparmio stimato | REQ-007..010 | **Must** | CS-2 dell'epica: domanda chiave sull'efficacia della cache |
| Report costo/consumo: token per provider + per intervallo/sessione | REQ-011..014 | **Must** | CS-3 dell'epica: base per FEAT-007 e per la fattura |
| Report corpus/indice: snapshot ultimo + trend | REQ-015..017 | **Must** | CS-1 dell'epica (lato aggregazione); indispensabile per la TUI |
| Report latenze: p50/p95 per operation | REQ-018..020 | **Should** | Utile per diagnosi; non blocca l'MVP ma atteso presto |
| Report affidabilità: errori/retry/low_confidence | REQ-021..024 | **Should** | Diagnostica; presto utile ma non strettamente bloccante per la TUI |
| Determinismo e privacy delle aggregazioni | REQ-025..026 | **Must** | Principio VI + privacy-by-default (REQ-E8/E9 epica) |
| Granularità temporale configurabile | vincolo §7 | **Should** | Rende i report utili su periodi variabili |
| Stima risparmio token (quando `tokens` disponibile) | REQ-009 | **Should** | Dipende dalla disponibilità del campo nel provider; segnalazione unavailable è Must |
| Freschezza corpus (confronto git) | fuori ambito | **Could** | Richiede info host-specifiche; rinviato (DA-002-AGG) |

## 10. Domande aperte

- **DA-001-AGG — Contratto/forma dell'API di report (design):** [DA CHIARIRE in design/SpecKit:
  il servizio espone un'unica entry point con selettore di tipo report, oppure metodi separati
  per ciascun report? I report sono dizionari, dataclass, TypedDict o altro? Questa è pura
  scelta di design e non cambia i requisiti qui.]

- **DA-002-AGG — Freschezza del corpus (info host-specifiche):** [DA CHIARIRE: il confronto tra
  "timestamp dell'ultimo `index`" e "data dell'ultima modifica dei file indicizzati" richiede
  accesso al filesystem o a `git log` — entrambi host-specifici e fuori dal core (Principio X).
  Possibili risoluzioni: (a) la CLI/TUI calcola il delta e lo passa al servizio come parametro
  esterno; (b) si rinvia a FEAT-010 (Could); (c) si espone solo il timestamp dell'ultimo index,
  e la "freschezza" è responsabilità del consumatore. Impatto: se (a), il servizio riceve
  informazioni opache dall'esterno; se (b/c), questa feature non la implementa affatto.]

- **DA-003-AGG — Granularità dei bucket temporali:** [DA CHIARIRE: "giorno" come default è
  ragionevole, ma ci sono scenari d'uso in cui la granularità oraria o per-sessione (bounded da
  un evento `index`) è preferibile. Va deciso se supportare granularità multipla (day/hour/session)
  o una sola configurabile. Impatto sul contratto dei report e sulla complessità del servizio.]

- **DA-004-AGG — Stima risparmio token con deduplicazione in-call (feat. 019):** [DA CHIARIRE:
  la feature 019 introduce deduplicazione degli embedding in-call (chunk identici non vengono
  ri-embeddati nella stessa chiamata). Questo complica la correlazione `hits × (tokens/texts)`
  perché `texts` potrebbe riferirsi a chunk de-duplicati. La stima con REQ-009 resta corretta
  quando `tokens` e `texts` provengono dallo stesso evento `embeddings`; ma va verificato
  che la definizione rimanga coerente con ciò che la feat. 019 emette realmente.]

- **DA-005-AGG — Dipendenza dalla porta di FEAT-001 (design):** [DA CHIARIRE in design: la
  porta di osservabilità definita da FEAT-001 espone già primitive di query per operation e
  intervallo temporale (REQ-002 di FEAT-001). Va verificato, in fase di design, che le query
  necessarie a questo servizio (aggregazione per bucket temporale, join eventi diversi) siano
  esprimibili tramite quella porta senza aggiunte. Se la porta è troppo bassa (eventi uno per
  uno), le aggregazioni vivono interamente qui; se la porta espone già aggregati, questo
  servizio è più sottile. È materia di design ma potrebbe richiedere un'iterazione sui requisiti
  di FEAT-001.]
