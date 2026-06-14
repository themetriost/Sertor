# Data Model — Aggancio della distillazione all'archivio episodico (FEAT-003)

Phase 1. La feature **legge** entità già modellate da FEAT-001 e aggiunge **una** sola entità di vista.
Nessuna modifica allo schema SQLite (sola lettura su `sessions`/`turns`).

## Entità riusate (FEAT-001, INVARIATE)

### `ArchivedSession` (`src/sertor_core/domain/memory.py:49-62`)

Unità conservata, ricomposta da `MemoryArchive.get`. Letta e **esposta** da questa feature, non
ridefinita.

| Campo | Tipo | Note |
|-------|------|------|
| `session_key` | `str` | chiave opaca (filename stem), host-agnostica |
| `project_id` | `str` | namespace dell'ospite |
| `captured_at` | `float` | epoch UTC dell'istante di cattura |
| `adapter_kind` | `str` | tipo di adapter sorgente (dato opaco) |
| `turns` | `tuple[TranscriptTurn, ...]` | turni post-scrub, ordinati per `index` |
| `retention_days` | `int \| None` | gancio retention (non applicato qui) |

### `TranscriptTurn` (`src/sertor_core/domain/memory.py:25-36`)

| Campo | Tipo | Note |
|-------|------|------|
| `index` | `int` | ordinale stabile (ordine di emissione) |
| `role` | `str` | `'user'` \| `'assistant'` |
| `text` | `str` | testo del turno (già scrubbato in archivio) |
| `ts` | `float \| None` | epoch UTC del turno, `None` se assente |

## Nuova entità di vista

### `SessionSummary` (NUOVA — `src/sertor_core/domain/memory.py`)

Vista sintetica per la **scoperta** (FR-002, Key Entity «Voce di elenco sessione»): identifica una
sessione **senza** caricarne il contenuto dei turni. `@dataclass(frozen=True)`, nessun import SDK
(Principio I), coerente con `SessionRef`/`SearchQuery` come dataclass pure di dominio.

| Campo | Tipo | Origine | Note |
|-------|------|---------|------|
| `session_key` | `str` | `sessions.session_key` | chiave opaca per il successivo `show` |
| `captured_at` | `float` | `sessions.captured_at` | epoch UTC; chiave di ordinamento (recency) |
| `turn_count` | `int` | `sessions.metadata.turn_count` | numero di turni, senza join su `turns` |

**Regole di validazione**: nessuna oltre i tipi (i valori provengono da record già validati in scrittura
da FEAT-001). `turn_count >= 0` per costruzione.

**Razionale `turn_count` da metadata**: `_metadata_json` (`archive.py:142-150`) persiste già
`turn_count`; leggerlo da lì evita un `COUNT(*)`/join su `turns` (research D-3).

## Operazioni di lettura (sul componente esistente `MemoryArchive`)

### `MemoryArchive.get(session_key) -> ArchivedSession | None` — RIUSATA (invariata)

Già esistente (`archive.py:104-139`). Esiti rilevanti per il consumer (research D-4):
- `None` → sessione **assente** (→ not-found in CLI).
- `ArchivedSession` con `turns == ()` → sessione **esistente ma vuota** (→ stato vuoto, successo).
- `ArchivedSession` con N turni → transcript intero (FR-001/SC-001).
- store ko → `None` + warning `memory_archive_unavailable` (degradazione non-fatale, FR-004).

> Nota: il `None` di `get` per «store ko» e per «sessione assente» coincide. È accettabile: in entrambi i
> casi l'esito utente è «non posso mostrarti questa sessione» con messaggio azionabile + exit non-zero; il
> warning loggato distingue il guasto-store per la diagnostica (Principio IX). La distinzione **richiesta**
> da FR-003 è quella tra *assente* e *vuota* — e quella È distinta (vuota = `ArchivedSession` non `None`).

### `MemoryArchive.list_recent(limit: int) -> tuple[SessionSummary, ...]` — NUOVA

Elenco delle sessioni più recenti (FR-002). Comportamento:

- Query: `SELECT session_key, captured_at, metadata FROM sessions ORDER BY captured_at DESC LIMIT ?`;
  `turn_count` estratto da `json.loads(metadata)["turn_count"]` (fallback `len`/`0` se assente, difensivo).
- Ordine: **recency-first** (`captured_at DESC`), tie-break implicito stabile per chiave.
- Limite: `limit` (risolto dal consumer; default `Settings.memory_list_limit`, D-7).
- Archivio assente/vuoto/illeggibile → `()` + warning `memory_archive_unavailable` (non-fatale, FR-004),
  identico alla policy di `get`.
- Sola lettura: nessuna scrittura, nessuna creazione/alterazione di schema o indici.

## Manopola di configurazione (NUOVA)

### `Settings.memory_list_limit: int = 20` (`SERTOR_MEMORY_LIST_LIMIT`)

Default in `Settings` (Principio VIII), letta in `Settings.load()` accanto a `episodic_limit`
(`settings.py:129,257`). Sovrascrivibile per-invocazione dal flag CLI `-k/--limit`.

## Relazioni

```
sessions (FEAT-001)  --get-->        ArchivedSession --> tuple[TranscriptTurn]   (transcript intero, show)
sessions (FEAT-001)  --list_recent--> tuple[SessionSummary]                       (elenco recente, list)
                                          ^
                              MemoryArchive (concreto, NO porta)
                                          ^
                              build_memory_reader(settings) gated  --> CLI memory show / memory list
```

Nessuna nuova porta `Protocol` in `domain/ports.py` (SC-007: invariato).
