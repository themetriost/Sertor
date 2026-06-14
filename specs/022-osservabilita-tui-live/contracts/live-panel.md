# Contract — modello di stato live + pannello

## `live_snapshot(reports, recent_limit=20, since=None, until=None) -> LiveSnapshot`

Funzione **pura** (in `observability/live.py`): compone una fotografia dello stato corrente dai report
di F2. Garanzie:
- **Deterministica/sola lettura:** stesso store → stesso snapshot; nessuna scrittura (FR-004/SC-007).
- **Thin consumer:** usa **solo** `ObservabilityReports` (F2); nessuna aggregazione propria (FR-003).
- **Stato vuoto onesto:** nessun evento → `LiveSnapshot(has_data=False, …)` con valori a zero, mai
  eccezione (FR-005/SC-003).
- **Solo metriche** (FR-011): i campi sono numeri/eventi già redatti; nessun contenuto grezzo.
- **Testabile senza terminale** (FR-010/SC-005): nessun Textual coinvolto.

## `run_live_panel(settings) -> None` (in `observability/tui.py`)

Avvia il pannello. Garanzie:
- **Import lazy dell'extra:** importa Textual solo qui; se assente → `ConfigError` con istruzione
  (`uv add "sertor-core[tui]" …`), come `rerank`/`graph` (FR-006/SC-004). Non un errore oscuro.
- **Refresh periodico:** rilegge `live_snapshot` ogni `settings.observability_refresh_s` e aggiorna i
  widget (FR-002/SC-002), senza riavvio.
- **Sola lettura, chiusura pulita:** non scrive nulla; esce pulito su richiesta (FR-004/009).
- **Persistenza spenta:** parte comunque e mostra lo stato vuoto onesto (non blocca).

## `ObservabilityApp` (Textual)

Guscio di rendering: disegna i campi di `LiveSnapshot` (ultimo index, cache hit/miss + risparmio,
consumo per provider, ultimi eventi, affidabilità) e li aggiorna sul timer. Smoke-testato via il
test-harness di Textual (`run_test`/Pilot) quando l'extra è presente.

## CLI

`sertor-rag observe` → `run_live_panel(Settings.load())`. Unico entry point del prodotto (riusa la CLI
esistente); coerente con gli altri comandi.

## Fuori contratto (feature successive)

Report sfogliabili/storici (F4), export OTel (F5), conversione € (FEAT-007), modalità web (F8).
