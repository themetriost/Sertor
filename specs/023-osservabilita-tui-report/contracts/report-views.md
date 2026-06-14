# Contract — viste report (rese pure + schede)

## Funzioni di resa (in `observability/live.py`) — pure

```
render_cache_report(r: CacheReport) -> str
render_cost_report(r: CostReport) -> str
render_corpus_report(r: HealthReport, now: float) -> str
```

Garanzie:
- **Pure/deterministiche:** stesso report (+ `now`) → stessa stringa; nessuna scrittura, nessun Textual
  (FR-009/SC-006).
- **Thin consumer:** ricevono i report **già calcolati** da F2; nessuna aggregazione (FR-005).
- **Stato vuoto onesto:** report a zeri → testo con messaggio «nessun dato», mai eccezione (FR-006/SC-004).
- **Solo metriche** (FR-011). La vista costo mostra i **token** (la € è una capacità separata: ripiego
  di default, FR-007).
- **Freschezza:** `render_corpus_report` mostra `now − last_index_ts` in forma leggibile; `now` iniettato.

## Finestra temporale (pure)

```
time_window(preset: str, now: float) -> (since|None, until|None)   # all | 7d | 24h
next_window(preset: str) -> str                                    # cicla all→7d→24h→all
```

## App a schede (`ObservabilityApp`, estende F3)

`TabbedContent`: Live / Cache / Cost / Corpus. Binding `t` cicla l'intervallo (mostrato in sub-title);
`_update` ricalcola le viste sulla finestra selezionata. Sola lettura. Navigazione schede nativa.
Stesso entry point `sertor-rag observe`, stesso extra `[tui]`, stessa degradazione (store vuoto / extra
assente) di F3.

## Fuori contratto

Export CSV/Markdown (Could), intervallo libero da-data/a-data (rifinitura), conversione € (FEAT-007),
confronto freschezza-vs-repo (host-specifico), modalità web.
