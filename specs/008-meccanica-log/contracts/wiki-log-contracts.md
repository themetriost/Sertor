# Contratti JSON — Meccanica del log

Versionati (`<nome>/<versione>`), forward-compatible (i consumatori tollerano campi aggiuntivi).

## `wiki.append_log/1`
```json
{ "written": true, "partition": "log/2026-06-08.md", "created": false, "schema": "wiki.append_log/1" }
```
- `written` (bool) — `false` se la voce era già presente (idempotenza sull'heading).
- `partition` (str|null) — path relativo (rispetto a `root`) del file toccato; `null` solo su no-op senza target.
- `created` (bool) — la partizione è stata creata in questa chiamata.

## `wiki.migrate/1`
```json
{ "migrated_entries": 42, "created": ["2026-05-30.md", "2026-06-07.md"], "skipped": [], "schema": "wiki.migrate/1" }
```
- `migrated_entries` (int) — voci datate trasferite dal log monolitico.
- `created` / `skipped` (list[str]) — partizioni create / già esistenti (idempotenza).

## `wiki.scan/1` — INVARIATO
Nessuna modifica al contratto (FR-008/SC-003). Cambia solo *come* si calcola l'`anchor` (partizione più
recente in modalità rotazione), non la forma né la semantica osservata dall'hook.

## `wiki.error/1`
Riuso del contratto esistente per gli errori espliciti (heading malformato, config assente).
