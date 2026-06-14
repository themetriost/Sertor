# Contratto CLI — `sertor-rag memory archive` / `sertor-rag memory search`

**Feature**: 035 | **Schema**: `cli.memory/1` | **Stile**: coerente con `cli/__main__.py`
(thin consumer, exit `0`/`1`/`2`).

I comandi sono **host-agnostici** (Principio X): nessuna assunzione sull'assistente ospite. Tutta la
logica è delegata al core (`build_memory_archiver`/`build_episodic_search`); il CLI fa
parsing → composition → formattazione (Principio I).

---

## Gruppo `memory`

```
sertor-rag memory <subcommand> [...]
  subcommand ∈ { archive, search }
```
Invocare `sertor-rag memory` senza subcomando → errore d'uso argparse (exit 2).

---

## `memory archive`

```
sertor-rag memory archive [--json] [--corpus C] [-v|--verbose] [--log-json] [--log-config F]
```

**Comportamento**: delega a `MemoryArchiveService.archive_all()` (tutte le sessioni del progetto,
idempotente). Stampa il report dei conteggi.

| Opzione | Effetto |
|---------|---------|
| `--json` | report come oggetto JSON anziché riga umana |
| `--corpus` | override di `SERTOR_CORPUS` (coerente con gli altri comandi) |
| flag di logging | come `index`/`search` (`_add_logging_flags`) |

**Output umano**: `archived=N skipped=N errors=N`
**Output JSON**: `{"archived": N, "skipped": N, "errors": N}`

**Exit codes**:
- `0` — archiviazione eseguita (anche `archived=0`: nessuna sessione nuova NON è un errore).
- `1` — `ConfigError`: memoria disabilitata (`build_memory_archiver` → `None`). Messaggio su stderr:
  `error: memory is disabled; set SERTOR_MEMORY=true to enable archiving (key: SERTOR_MEMORY)`.
- `2` — errore d'uso argparse.

**Invarianti**:
- Idempotenza (FR-004, SC-001): seconda run immediata → `archived=0`, le precedenti come `skipped`.
- Read-side-effect solo additivo: nessuna modifica alle sessioni già archiviate.
- Equivalenza conteggi umano↔JSON (FR-003).

---

## `memory search`

```
sertor-rag memory search <query> [--since S] [--until U] [--order relevance|recency]
                                 [-k N | --limit N] [--json] [--corpus C] [logging flags]
```

**Comportamento**: delega a `EpisodicSearch.search(SearchQuery(...))`. Sola lettura (FR-008).

| Opzione | Effetto | Default |
|---------|---------|---------|
| `query` (posizionale) | testo FTS5; vuoto/whitespace → stato vuoto (non errore) | — |
| `--since` | limite inferiore temporale (ISO-8601 o epoch) su `captured_at` | aperto |
| `--until` | limite superiore temporale | aperto |
| `--order` | `relevance` (default) o `recency` | `relevance` |
| `-k`/`--limit` | massimo numero di risultati | `settings.episodic_limit` (20) |
| `--json` | risultati come array JSON | — |

**Output umano** (per ogni hit, blocco numerato):
```
[1] score=0.873  role=user  session=<session_key>  turn=12  @=2026-06-14T10:21:03Z
    …testo dello [snippet] con il match evidenziato…
```
`(no results)` se nessun hit.

**Output JSON**: array di
```json
{"session_key":"…","captured_at":1718360463.0,"role":"user","turn_index":12,
 "snippet":"…[match]…","score":0.873}
```

**Exit codes**:
- `0` — ricerca eseguita (anche zero risultati: stato vuoto onesto).
- `1` — `ConfigError` (memoria disabilitata, stesso messaggio di `archive`) **oppure**
  `InvalidTimeWindowError` (`--since` dopo `--until`): messaggio su stderr azionabile dal core.
- `2` — errore d'uso argparse.

**Invarianti**:
- Sola lettura: l'archivio non è modificato (FR-008, SC parità).
- Campi di citazione completi: `session_key`, `captured_at`, `role`, `turn_index`, `snippet`,
  `score` (FR-006, SC-002).
- Finestra temporale e limite applicati dal core (FR-007, SC-003): zero risultati fuori finestra;
  conteggio mai oltre il limite.
- `--json` e umano comunicano gli stessi risultati (FR-009).

---

## Gate di privacy (entrambi i comandi)

A `SERTOR_MEMORY` non abilitato (default), entrambi i comandi rispondono con `ConfigError` (exit 1)
e **non** eseguono alcuna archiviazione/ricerca (FR-016, SC-007). Il messaggio nomina esplicitamente
`SERTOR_MEMORY=true`.
