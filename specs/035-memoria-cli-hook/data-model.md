# Data Model — Superficie CLI memoria + hook (035)

**Feature**: `035-memoria-cli-hook` | **Date**: 2026-06-14 | **Fase**: Phase 1 (plan)

Questa feature è una **superficie sottile** (thin consumer): NON introduce nuove entità di dominio né
nuovo stato persistente. Riusa le entità del core già su master e ne formatta l'esito. Qui si
documentano (a) le entità del core consumate e (b) le strutture di presentazione del CLI (non sono
dati: sono proiezioni view-only).

## Entità del core CONSUMATE (immutate, da master)

### `ArchiveRunReport` (`services/memory_archive.py:21`)
Esito di una run di `archive_all()`. Solo contatori, mai segreti.

| Campo | Tipo | Significato |
|-------|------|-------------|
| `archived` | `int` | sessioni nuove archiviate in questa run |
| `skipped` | `int` | sessioni saltate (già presenti / vuote / race sullo store) |
| `errors` | `int` | errori non-fatali incontrati |

Prodotto da `MemoryArchiveService.archive_all() -> ArchiveRunReport`. Idempotente: una seconda run
immediata produce `archived=0` e i precedenti come `skipped` (SC-001).

### `SearchQuery` (`services/episodic_search.py:34`, frozen)
Input della ricerca episodica.

| Campo | Tipo | Default | Origine CLI |
|-------|------|---------|-------------|
| `text` | `str` | — | argomento posizionale `query` |
| `since` | `float \| None` | `None` | `--since` (parsato a epoch UTC) |
| `until` | `float \| None` | `None` | `--until` (parsato a epoch UTC) |
| `order` | `"relevance" \| "recency"` | `"relevance"` | `--order` (opzionale; default relevance) |
| `limit` | `int` | `20` | `-k`/`--limit`; default = `settings.episodic_limit` |
| `snippet_tokens` | `int` | `12` | non esposto da CLI; usa `settings.episodic_snippet_tokens` |

Vincolo: `since > until` → `InvalidTimeWindowError` (sollevato dal core, esposto come exit 1).

### `EpisodicHit` (`services/episodic_search.py:52`, frozen)
Un turno corrispondente con la sua citazione. Unità di output di `memory search`.

| Campo | Tipo | Reso da CLI |
|-------|------|-------------|
| `session_key` | `str` | sì (`session=`) |
| `captured_at` | `float` (epoch UTC) | sì (umano: ISO-8601 UTC; JSON: epoch) |
| `role` | `str` | sì (`role=`) |
| `turn_index` | `int` | sì (`turn=`) |
| `snippet` | `str` (già delimitato `[…]` dal core) | sì (riga indentata) |
| `score` | `float` (`-bm25()`, più alto = più pertinente) | sì (`score=`, arrotondato) |
| `source_path` | `str \| None` (oggi sempre `None`) | omesso finché `None` |

### `EpisodicResults` (`services/episodic_search.py:70`, frozen)
Esito esplicito (evita un `None` ambiguo, Principio IV).

| Campo | Tipo | Uso CLI |
|-------|------|---------|
| `hits` | `tuple[EpisodicHit, ...]` | corpo dell'output; vuoto = stato vuoto onesto |
| `latency_ms` | `float` | non nel payload per-hit; già loggato dal core (osservabilità) |

## Strutture di PRESENTAZIONE (CLI, non persistite)

Non sono entità di dominio: sono il prodotto delle funzioni pure di `cli/output.py`.

### Report di archiviazione (proiezione)
- **JSON**: `{"archived": int, "skipped": int, "errors": int}`.
- **Umano**: `archived=N skipped=N errors=N`.
Equivalenza dei conteggi umano↔JSON = invariante (FR-003, SC-001).

### Risultato di ricerca (proiezione)
- **JSON**: array di `{"session_key", "captured_at", "role", "turn_index", "snippet", "score"}`.
- **Umano**: blocchi numerati `[i] score=… role=… session=… turn=… @=<iso>` + snippet indentato;
  `(no results)` se vuoto.
Coerente con `format_search_results` (stesso stile di citazione, FR-006/SC-002).

## Interruttore di memoria (config, immutato)
`Settings.memory_enabled` (`SERTOR_MEMORY`, default `False`, `config/settings.py:123`). Unico gate
di privacy (A-003). Quando `False`: le factory `build_memory_archiver`/`build_episodic_search`
ritornano `None`; il comando solleva `ConfigError`; l'hook è no-op (pre-check env).

## Flussi (riepilogo)

```
memory archive: _resolve_settings → _require_archiver(settings)            [None→ConfigError]
                 → archiver.archive_all()  → format_archive_report(report, json)

memory search:  _resolve_settings → _require_episodic_search(settings)     [None→ConfigError]
                 → search.search(SearchQuery(text, since, until, order, limit, snippet_tokens))
                 → format_memory_results(results, settings, json)          [since>until→exit 1]

hook SessionEnd: pre-check SERTOR_MEMORY  [off→exit 0 no-op]
                 → invoca `sertor-rag memory archive` (try/catch, exit sempre 0, timeout host)
```

Nessuna nuova entità persistente, nessuna migrazione, nessun nuovo file su disco oltre allo script
hook versionato (`.claude/hooks/memory-capture.ps1`).
