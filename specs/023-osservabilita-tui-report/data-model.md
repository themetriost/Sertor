# Data Model — feature 023

Nessuna entità dati nuova: F4 **rende** i report di F2 (`CacheReport`/`CostReport`/`HealthReport`, già su
master). Le novità sono **funzioni di resa pure** e l'estensione a schede dell'app.

## 1. Funzioni di resa pure (`observability/live.py`)

| Funzione | Input | Output |
|---|---|---|
| `render_cache_report(r: CacheReport)` | report cache | testo: totali hit/miss + risparmio + serie per bucket |
| `render_cost_report(r: CostReport)` | report costo | testo: totale token + per provider + serie per bucket |
| `render_corpus_report(r: HealthReport, now: float)` | report salute + istante | testo: ultimo index (doc/chunk/dim) + **freschezza** = `now − last_index_ts` (leggibile) |

Ognuna gestisce il caso **vuoto** (zeri/nessun dato) con un messaggio onesto. Pure: nessun Textual,
`now` iniettato (deterministico nei test).

## 2. Finestra temporale (puro)

| Funzione | Comportamento |
|---|---|
| `time_window(preset: str, now: float) -> tuple[float\|None, float\|None]` | `all`→(None,None) · `7d`→(now−7·86400, None) · `24h`→(now−86400, None) |
| `next_window(preset: str) -> str` | cicla `all → 7d → 24h → all` |

## 3. App a schede (`observability/tui.py`, estende F3)

- `ObservabilityApp` ora compone un `TabbedContent` con schede **Live / Cache / Cost / Corpus** (ognuna
  un `Static`). Tiene `self._window` (preset corrente, default `all`).
- `_update()`: `now = time.time()`; `since, until = time_window(self._window, now)`; aggiorna:
  - Live: `render_snapshot(live_snapshot(reports))` (tutto, come F3);
  - Cache: `render_cache_report(reports.cache_report(since, until))`;
  - Cost: `render_cost_report(reports.cost_report(since, until))`;
  - Corpus: `render_corpus_report(reports.health_report(since, until), now)`.
  Imposta `self.sub_title` al preset corrente.
- BINDINGS: `t` → `action_cycle_window` (`next_window` + `_update`); `q` → quit. Navigazione schede =
  nativa di `TabbedContent`.
- Resta **sola lettura**; degradazione onesta invariata.

## 4. Manopole

Nessuna nuova manopola di prodotto: riusa `observability_refresh_s` (F3). I preset di intervallo sono
stato dell'UI, non config.
