# Data Model — feature 022

Nessuna entità di dominio del retrieval cambia. Le entità qui sono lo **snapshot** dello stato live e la
manopola. Vivono in `observability/live.py` (modello puro) e `tui.py` (guscio).

## 1. `LiveSnapshot` (dataclass frozen) — `observability/live.py`

| Campo | Tipo | Significato |
|---|---|---|
| `has_data` | bool | `False` se non ci sono eventi (persistenza spenta/store vuoto) → stato vuoto onesto |
| `last_index` | `HealthReport` | ultima indicizzazione (documents/chunks/embedding_dim/last_index_ts) |
| `cache_hits` | int | hit totali della cache |
| `cache_misses` | int | miss totali |
| `cache_hit_rate` | float | `hits/(hits+misses)` (0.0 se nessuno) |
| `estimated_tokens_saved` | int | stima dal report cache |
| `total_tokens` | int | consumo totale (dal report costo) |
| `tokens_by_provider` | dict[str,int] | consumo per provider |
| `recent_events` | list[`ObservedEvent`] | gli ultimi N eventi (ts/operation/fields) |
| `errors` / `retries` / `low_confidence` | int | dal report affidabilità |

Costruito da `live_snapshot(reports, recent_limit=20, since=None, until=None) -> LiveSnapshot`: chiama
`reports.cache_report()`, `cost_report()`, `health_report()`, `reliability_report()`,
`recent_events(limit)` e li compone. **Funzione pura** (stesso store → stesso snapshot); nessun Textual.
`has_data` = vero se almeno un evento è presente.

## 2. Estensione di F2: `ObservabilityReports.recent_events`

```
recent_events(limit: int = 20, since: float|None = None, until: float|None = None) -> list[ObservedEvent]
```
Gli ultimi `limit` eventi (tutti i tipi) ordinati per ts, coda (additivo su F2).

## 3. App Textual — `observability/tui.py`

- `ObservabilityApp(reports, refresh_s)` (sottoclasse `textual.app.App`): al mount disegna lo snapshot;
  `set_interval(refresh_s, self._refresh)` → ricalcola `live_snapshot(reports)` e aggiorna i widget.
  Sola lettura. Import di `textual` al top del modulo (il modulo è importato lazy da `run_live_panel`).
- `run_live_panel(settings) -> None`: costruisce i report (`build_observability_reports`) e lancia
  l'app. Import lazy di `tui`/Textual; se `ImportError` → `ConfigError` con l'istruzione d'installazione.

## 4. Manopola (`Settings`)

| Campo | Env | Default | Significato |
|---|---|---|---|
| `observability_refresh_s` | `SERTOR_OBSERVABILITY_REFRESH` | `2.0` | Intervallo di refresh del pannello (secondi). |

## 5. CLI

`sertor-rag observe` → `run_live_panel(Settings.load())`. Errore azionabile se l'extra `[tui]` manca;
stato vuoto onesto se la persistenza è spenta.

## 6. Dipendenze (pyproject.toml)

```
[project.optional-dependencies]
tui = ["textual>=8,<9"]
# + textual nel gruppo dev (per i test headless via Pilot)
```
