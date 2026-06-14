# Research — Strato di osservabilità persistente (feature 020)

Decisioni di design risolte prima dell'implementazione. Nessuna NEEDS CLARIFICATION residua.

## D1 — Meccanismo di intercettazione: un `logging.Handler` stdlib (risolve DA-O-f)

- **Decision:** la cattura avviene con un **`logging.Handler`** custom (`EventPersistenceHandler`)
  attaccato dal composition root al logger `sertor_core` **solo** quando la persistenza è abilitata. Il
  handler riceve ogni `LogRecord`, e per i record che sono **eventi strutturati** (quelli con
  l'attributo `operation`, impostato da `log_event` via `extra`) ne ricostruisce l'evento (operation +
  campi dall'`extra` del record + istante da `record.created`) e lo scrive nello store.
- **Rationale:** è il punto di intercettazione **più additivo** possibile. `log_event` (in
  `observability/logging.py`) fa `safe = redact(fields)` poi `get_logger().log(level, ..., extra={"operation": operation, **safe})`:
  i campi strutturati e **già redatti** sono dunque attributi del `LogRecord`. Un handler li legge senza
  toccare né `log_event` né i call-site (FR-005). Tre proprietà arrivano **gratis**:
  - **Non-fatale (FR-007):** il framework `logging` **non propaga mai** un'eccezione sollevata in
    `Handler.emit` al chiamante — la incanala in `Handler.handleError`. Quindi un guasto dello store non
    può far fallire l'operazione osservata, **senza** codice difensivo sparso.
  - **Default-off (FR-004):** se la persistenza è spenta, **nessun handler** è attaccato → zero overhead,
    nessuno store creato.
  - **Privacy/redazione (FR-009):** l'`extra` contiene i campi **`safe`** (post-`redact`), quindi i
    segreti sono già mascherati prima ancora di arrivare al handler.
- **Alternatives considered:** **(ii) emissione esplicita dentro `log_event`** verso un sink registrato
  dal composition root — funziona, ma tocca il choke point, accoppia il modulo `observability` al sink e
  richiede try/except esplicito per la non-fatalità (che con l'handler è gratis). Respinta perché meno
  additiva e più accoppiata. **(iii) monkeypatch/wrapper di `log_event`** — fragile, respinta.

## D2 — Store: SQLite locale sotto `index_dir` (simmetrico alla cache 019)

- **Decision:** store SQLite `<index_dir>/observability.sqlite`. Tabella unica
  `events(id INTEGER PK, ts REAL, operation TEXT, fields TEXT)` dove `fields` è il JSON dei campi
  dell'evento; indici su `(operation, ts)` e su `(ts)`. Append-only; `CREATE TABLE IF NOT EXISTS` lazy.
- **Rationale:** stesso pattern collaudato della cache 019 (stdlib `sqlite3`, file gitignored sotto
  `index_dir`, degrado catturato). SQLite dà **query per operation e intervallo** (FR-003:
  `WHERE operation=? AND ts BETWEEN ? AND ?`) con un indice, e copre i bisogni di **FEAT-002**:
  - **Bucket temporali** (report per giorno/intervallo): funzioni data SQLite su `ts`
    (es. `strftime('%Y-%m-%d', ts, 'unixepoch')`).
  - **Estrazione di singoli campi metrici** (es. somma dei `tokens`): `json_extract(fields, '$.tokens')`.
  - **Correlazione tra tipi di evento** (es. `embeddings` vs `embeddings_cache` nello stesso run):
    query sullo stesso `events` filtrando per `operation` e finestra temporale.
  Lo schema è quindi **dimensionato** per F2 senza implementare F2 qui (FR-003 è la sola query richiesta
  ora; le aggregazioni vivono in F2).
- **Alternatives considered:** un file JSONL append (semplice ma niente query/indici → F2 dovrebbe
  ri-parsare tutto); un DB separato per tipo di evento (over-engineering, rompe la correlazione). SQLite
  singola tabella è il minimo che serve F2.

## D3 — Redazione e privacy-by-default (verifica chiave di FR-008/009)

- **Decision/Verifica:** confermato leggendo `observability/logging.py`: `log_event` **redige prima** di
  emettere (`safe = redact(fields)`), e mette in `extra` i campi `safe`. Quindi il handler che legge
  l'`extra` ottiene dati **già redatti** → **FR-009 soddisfatto** senza ri-redazione.
- **Solo-metriche (FR-008):** verificato che oggi **nessun** evento del core porta testo di query
  (`retrieve` logga `collection/status/doc_type`). Quindi il default «solo metriche» è realizzabile
  **senza filtrare nulla di esistente**. Quando in futuro un evento introdurrà un campo di contenuto,
  servirà una **classificazione** (allow-list di campi-metrica) per non persistirlo di default — annotato
  come DA-001 (fuori da questa feature, ma il handler dovrà supportare la policy quando arriverà).

## D4 — Porta `ObservabilityStore` (serve una 7ª porta?)

- **Decision:** **sì**, una porta `ObservabilityStore` (Protocol `runtime_checkable`) in
  `domain/ports.py`, con `record_event(...)` e `query_events(operation, since, until) -> list[...]`. Il
  handler scrive via la porta; **FEAT-002 leggerà** via la stessa porta; il composition root cabla
  l'adapter SQLite. È la 7ª porta accanto alle sei esistenti.
- **Rationale:** la porta è **giustificata da un consumatore reale** (FEAT-002, già a requisiti) — non è
  YAGNI: è il **seam** che separa "dove vivono gli eventi" da "chi li interroga", e tiene lo store
  sostituibile (Principio I/II). Il handler resta un dettaglio di `observability/`, la porta è il
  contratto stabile.
- **Alternatives considered:** nessuna porta, handler che scrive direttamente su SQLite e F2 che apre il
  file da sé — accoppia F2 al formato del file, contro Principio I. Respinta.

## D5 — Non-bloccante: insert sincrono ora, `QueueHandler` come via di fuga

- **Decision:** insert **sincrono** nello store dentro `Handler.emit`. Gli eventi sono **per-operazione**
  (un `index` per indicizzazione; pochi `embeddings`/`retrieve` per operazione) → bassa cardinalità →
  l'insert SQLite è nell'ordine dei microsecondi, overhead trascurabile (FR-006/SC-005). Se in futuro
  la cardinalità degli eventi crescesse (es. per-chunk), si passa a **`QueueHandler` + `QueueListener`**
  stdlib (coda + thread drenante) senza cambiare la porta né i call-site.
- **Rationale:** YAGNI (Principio III) — non si introduce una coda asincrona finché il volume non la
  richiede; la via di fuga è stdlib e a costo zero di interfaccia.
- **Alternatives considered:** `QueueHandler` da subito (robusto ma over-engineering per il volume
  attuale); thread di scrittura custom (reinventa `QueueListener`). Respinte per ora, documentate.

## D6 — Manopole `Settings`

- **Decision:** `observability_enabled: bool = False` (env `SERTOR_OBSERVABILITY`, parsing booleano
  tollerante come `SERTOR_GRAPH`/`SERTOR_EMBED_CACHE`); sede dello store **derivata** da `index_dir`
  (`<index_dir>/observability.sqlite`), non una manopola separata; **gancio di retention** previsto
  (es. `SERTOR_OBSERVABILITY_RETENTION`) ma la **politica** è rinviata (DA-O-b) — qui solo il punto di
  aggancio, default = nessuna scadenza.
- **Rationale:** coerente con le manopole esistenti (default in `Settings`, env `SERTOR_*`), default
  conservativo (FR-004), nessun percorso hardcoded (FR-011/Principio VIII).

## Punti aperti rinviati (non bloccano l'implementazione)
- **DA-O-b — politica di retention:** qui solo il gancio; limite per tempo/dimensione e rotazione da
  fissare (epica). 
- **DA-001 — classificazione campo-metrica vs contenuto:** rilevante solo quando si introdurranno campi
  di contenuto (oggi nessuno); il handler andrà esteso con la policy allora.
- **Forma esatta della query di F2:** `query_events` espone il minimo (operation + finestra); le
  aggregazioni/bucket sono di FEAT-002 (questa feature dà la materia prima, non i report).
