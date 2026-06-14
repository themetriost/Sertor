# Research — Pannello TUI vista live (feature 022)

Decisioni di design risolte. Nessuna NEEDS CLARIFICATION residua.

## D1 — Framework TUI: Textual, come extra opzionale `[tui]`

- **Decision:** **Textual** (verificato installabile: 8.2.7). Aggiunto come
  `optional-dependencies.tui` in `pyproject.toml` (import lazy in `tui.py`), e al gruppo `dev` per i
  test. Il core resta senza dipendenze obbligatorie nuove.
- **Rationale:** Python-native, ottimo prior art (Toolong/dolphie/posting), testabile **headless** via
  `App.run_test()`/Pilot (essenziale per Principio V), licenza permissiva. Coerente col pattern degli
  extra esistenti (`rerank`/`graph`).
- **Alternatives considered:** Rich-only (meno adatto a un'app live interattiva); curses (basso livello,
  poco testabile); web (fuori ambito, F8). Respinte.

## D2 — Meccanismo "live": rilettura periodica dei report (pull) — risolve DA-O-c

- **Decision:** la vista si aggiorna **rileggendo** periodicamente i report di F2 su un **timer**
  (Textual `set_interval`), intervallo `Settings.observability_refresh_s` (default 2.0s). Lo store è
  scritto in tempo reale dallo strato persistente (F1), quindi il pull mostra i dati aggiornati.
- **Rationale:** semplice, disaccoppiato (il pannello non si aggancia al flusso di log → nessun
  accoppiamento al logging), riusa F2 così com'è. Sufficiente per una vista "live" a refresh.
- **Alternatives considered:** **push** (tailare il flusso di log in tempo reale) — più reattivo ma
  accoppia il pannello al canale di logging e duplica la cattura; **ibrido** — complessità non
  giustificata ora. Respinte; la porta `ObservabilityStore`/F2 resta il confine.
- **Conseguenza:** la vista live **richiede la persistenza attiva** (legge lo store). Persistenza spenta
  → stato **vuoto onesto** con call-to-action (FR-005), non un crash.

## D3 — Separazione stato↔rendering (testabilità, Principio V/I)

- **Decision:** `LiveSnapshot` (dataclass) + `live_snapshot(reports, recent_limit)` **funzione pura** che
  compone la fotografia dai report di F2 — **senza Textual**. L'app Textual riceve lo snapshot e lo
  disegna; sul timer richiama `live_snapshot` e aggiorna i widget.
- **Rationale:** il *cosa mostrare* (logica) è testabile offline e senza TTY (FR-010/SC-005); il *come
  disegnarlo* (Textual) è un guscio sottile, smoke-testato via Pilot. Separazione "Humble Object".
- **Alternatives considered:** logica dentro i widget Textual — non testabile senza terminale, viola
  Principio I/V. Respinta.

## D4 — Ultimi eventi: `recent_events` additivo su F2

- **Decision:** aggiungere `ObservabilityReports.recent_events(limit, since=None, until=None)` (additivo,
  su questo branch) che ritorna gli ultimi `limit` eventi (via `query_events` ordinati per ts, coda). Lo
  snapshot lo usa per la sezione "ultimi eventi".
- **Rationale:** gli "ultimi eventi" sono una lettura naturale di F2 (che possiede lo store); evita che
  F3 acceda allo store direttamente (resta thin consumer di F2). Additivo, non rompe F2.
- **Alternatives considered:** F3 legge lo store direttamente — accoppia F3 all'adapter, salta F2.
  Respinta.

## D5 — Avvio ed extra mancante: `sertor-rag observe` + errore azionabile

- **Decision:** un sottocomando `observe` della CLI `sertor-rag` avvia il pannello
  (`run_live_panel(settings)`). `run_live_panel` importa Textual **lazy**; se assente → `ConfigError`
  con istruzione (`uv add "sertor-core[tui]"` …), come per `rerank`/`graph`. Persistenza spenta →
  il pannello parte e mostra lo stato vuoto onesto.
- **Rationale:** riusa la superficie CLI esistente (un solo entry point per il prodotto), coerenza degli
  errori con gli altri extra (Principio IV).
- **Alternatives considered:** un console-script separato — più superfici da mantenere; respinto.

## D6 — Manopola

- **Decision:** `Settings.observability_refresh_s: float = 2.0` (env `SERTOR_OBSERVABILITY_REFRESH`).
  Default in Settings (Principio VIII).
