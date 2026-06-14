# Contract — CLI `sertor-rag memory show` / `memory list` (`sertor.cli.memory-show-list/1`)

Estende il gruppo di sotto-comandi `memory` (feature 035) con due azioni di sola lettura. Layer **thin**
(Principio I): parsing → factory di composition → funzione pura di output. Coerente con i contratti CLI
di `memory archive`/`memory search`.

## Comando `memory show <session_key> [--json]`

### Sintassi

```
sertor-rag memory show <session_key> [--json] [--corpus C] [-v|--verbose] [--log-json] [--log-config F]
```

| Argomento | Tipo | Default | Descrizione |
|-----------|------|---------|-------------|
| `session_key` | posizionale, str | — (richiesto) | chiave opaca della sessione (filename stem) |
| `--json` | flag | off | output strutturato JSON anziché umano |
| `--corpus` | str | da env | override `SERTOR_CORPUS` (coerenza con gli altri comandi) |
| flag logging | — | — | `-v/--verbose`, `--log-json`, `--log-config` (condivisi) |

### Comportamento (handler `_cmd_memory_show`)

1. `setup_logging(args)`; `settings = _resolve_settings(args)`; `enable_observability(settings)`.
2. **Gate privacy**: `reader = _require_memory_reader(settings)` → se `build_memory_reader` ritorna
   `None`, solleva `ConfigError("memory is disabled; set SERTOR_MEMORY=true …", key="SERTOR_MEMORY")`
   (exit 1, FR-008). Identico a `_require_archiver`/`_require_episodic_search`.
3. `session = reader.get(args.session_key)`.
4. **not-found**: se `session is None` → `raise SessionNotFoundError(args.session_key)` (SertorError →
   exit 1 via `main()`), messaggio azionabile su stderr (FR-009). **Distinto** dal caso vuoto.
5. **successo**: `print(output.format_session_transcript(session, json=args.json))` → exit 0. Una
   sessione esistente con `turns == ()` stampa uno stato vuoto esplicito ed esce 0 (edge case).

### Output umano (esempio)

```
session=C--Workspace-Git-Sertor-abc123  @=2026-06-14T10:21:03Z  turns=3  adapter=claude-code
[0] user      @=2026-06-14T10:20:55Z
    <testo completo del turno 0>
[1] assistant @=2026-06-14T10:21:01Z
    <testo completo del turno 1>
[2] user      @=2026-06-14T10:21:03Z
    <testo completo del turno 2>
```

Sessione vuota → riga di intestazione + `(empty session)`.

### Output `--json` (forma)

```json
{
  "session_key": "C--Workspace-Git-Sertor-abc123",
  "project_id": "C:\\Workspace\\Git\\Sertor",
  "captured_at": 1781777663.0,
  "adapter_kind": "claude-code",
  "turns": [
    {"index": 0, "role": "user", "ts": 1781777655.0, "text": "..."},
    {"index": 1, "role": "assistant", "ts": 1781777661.0, "text": "..."}
  ]
}
```

Equivalenza informativa umano↔JSON (invariante SC-002). Testo **completo**, nessuna troncatura (FR-001).

## Comando `memory list [-k/--limit N] [--json]`

### Sintassi

```
sertor-rag memory list [-k N | --limit N] [--json] [--corpus C] [-v|--verbose] [--log-json] [--log-config F]
```

| Argomento | Tipo | Default | Descrizione |
|-----------|------|---------|-------------|
| `-k`, `--limit` | int (`dest=k`) | `Settings.memory_list_limit` (20) | numero massimo di sessioni |
| `--json` | flag | off | output strutturato JSON |
| `--corpus` | str | da env | override `SERTOR_CORPUS` |
| flag logging | — | — | condivisi |

### Comportamento (handler `_cmd_memory_list`)

1. `setup_logging`; `settings`; `enable_observability`.
2. **Gate privacy**: come `show` (FR-008).
3. `limit = args.k if args.k is not None else settings.memory_list_limit`.
4. `summaries = reader.list_recent(limit)` (recency-first, ≤ limit, FR-002/SC-002).
5. `print(output.format_session_list(summaries, json=args.json))` → exit 0. Archivio vuoto → stato vuoto
   esplicito (`(no sessions)` / `[]`), exit 0 (no errore, FR-004/edge case).

### Output umano (esempio)

```
[1] session=C--…-abc123  @=2026-06-14T10:21:03Z  turns=3
[2] session=C--…-def456  @=2026-06-13T18:02:11Z  turns=12
```

### Output `--json` (forma)

```json
[
  {"session_key": "C--…-abc123", "captured_at": 1781777663.0, "turn_count": 3},
  {"session_key": "C--…-def456", "captured_at": 1781712131.0, "turn_count": 12}
]
```

## Exit code (coerenti con il `main()` esistente)

| Codice | Condizione |
|--------|------------|
| `0` | successo (incluso stato vuoto: sessione vuota, archivio vuoto) |
| `1` | `SertorError` — memoria spenta (`ConfigError`) o sessione assente (`SessionNotFoundError`) |
| `2` | usage error argparse (`session_key` mancante, sotto-comando assente, `--limit` non intero) |

## Invarianti di test (contratto)

- **C-GATE**: `SERTOR_MEMORY` off → entrambi i comandi `ConfigError` exit 1 che nomina la manopola.
- **C-NOTFOUND**: `show` su chiave assente → exit 1, messaggio azionabile, **non** confuso con vuoto.
- **C-EMPTY-SESSION**: `show` su sessione esistente con 0 turni → exit 0 + stato vuoto esplicito.
- **C-EMPTY-ARCHIVE**: `list` su archivio vuoto → exit 0 + `(no sessions)`/`[]`.
- **C-ORDER**: `list` ordina recency-first; rispetta il limite (≤ N).
- **C-FULLTEXT**: `show` restituisce tutti gli N turni in ordine, testo intero (nessuna troncatura).
- **C-EQUIV**: umano e `--json` portano la stessa informazione (SC-002).
- **C-LOCAL**: nessuna chiamata di rete nel percorso (SC-006); nessun testo conversazionale negli eventi
  di log (RNF-2).
