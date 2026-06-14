# Research — Pannello TUI report sfogliabili (feature 023)

Decisioni di design risolte. Nessuna NEEDS CLARIFICATION residua.

## D1 — Estende F3 (stessa app), non un pannello separato

- **Decision:** F4 **estende** `ObservabilityApp` di F3 trasformandola in un'app a **schede**
  (`TabbedContent`): «Live» (la vista di F3) + «Cache» + «Cost» + «Corpus». Stesso entry point
  `sertor-rag observe`, stesso extra `[tui]`, stessa degradazione.
- **Rationale:** la spec lo richiede (un'unica superficie, FR-008); evita una seconda app/comando.
  Riuso massimo (Principio III).
- **Alternatives considered:** un comando separato `sertor-rag report` — duplica superficie e
  dipendenza; respinto.

## D2 — Funzioni di resa pure (testabilità, come F3)

- **Decision:** una funzione di resa pura per report — `render_cache_report(CacheReport)`,
  `render_cost_report(CostReport)`, `render_corpus_report(HealthReport, now)` — in `observability/live.py`
  (accanto a `render_snapshot` di F3). Ritornano testo; le schede Textual le disegnano.
- **Rationale:** il *cosa mostrare* è testabile offline (FR-009/SC-006); il *come* (schede) è il guscio
  sottile. Coerente con la separazione di F3.
- **Alternatives considered:** logica di resa dentro i widget — non testabile senza TTY; respinta.

## D3 — Intervallo temporale: preset puri + ciclo

- **Decision:** `time_window(preset, now) -> (since, until)` puro: `all`→(None,None),
  `7d`→(now-7·86400, None), `24h`→(now-86400, None). `next_window(preset)` cicla
  `all → 7d → 24h → all`. L'app tiene `now = time.time()` (impuro, solo nell'app) e passa la finestra ai
  report; un binding (`t`) chiama `next_window` e rinfresca. Il preset corrente è mostrato (sub-title).
- **Rationale:** le funzioni restano pure/deterministiche (now iniettato nei test); preset semplici
  coprono «settimana/giorno/tutto».
- **Alternatives considered:** intervallo libero da-data/a-data — UX più complessa, fuori MVP (rifinitura).

## D4 — Freschezza = tempo dall'ultimo index

- **Decision:** la vista «Corpus» mostra l'ultimo stato (`HealthReport`) + la **freschezza** =
  `now - last_index_ts` (in forma leggibile, es. «3h fa»). Nessun confronto con lo stato del repo
  (host-specifico → fuori ambito, come da requisiti).
- **Rationale:** ricavabile dai dati conservati, deterministico (now iniettato nel render per i test).

## D5 — Navigazione e degradazione

- **Decision:** la navigazione tra schede usa il supporto nativo di `TabbedContent` (focus da tastiera);
  l'intervallo si cicla con `t`. Store vuoto → ogni resa mostra uno stato vuoto onesto (riusa il
  pattern di `render_snapshot`); € assente → la vista costo mostra i **token** (ripiego, FR-007: in
  questa feature la € non esiste ancora → si mostrano sempre i token, "ripiego" già di default).
- **Rationale:** continuità con F3 (FR-008); robustezza (FR-006/007).
