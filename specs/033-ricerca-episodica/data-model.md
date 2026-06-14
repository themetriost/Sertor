# Data Model — Ricerca episodica full-text locale (feature 033)

**Branch**: `033-ricerca-episodica` · **Data**: 2026-06-14 · **Fase**: 1 (Design)

Entità di dominio della ricerca episodica. **Additive**: NON modificano le entità di FEAT-001
(`domain/memory.py`: `ArchivedSession`, `TranscriptTurn`, `SessionRef`, `TranscriptContent`). Pure
dataclass, nessun import di SDK esterno (Principio I). Si appoggiano allo schema SQLite **dato** di
FEAT-001, che NON viene riprogettato.

---

## Schema SQLite esistente (DATO da FEAT-001 — riferimento, non modificato)

`<index_dir>/memory.sqlite` (`adapters/memory/archive.py:36-51`):

```sql
sessions(session_key TEXT PK, project_id TEXT, captured_at REAL, adapter_kind TEXT, metadata TEXT)
turns(session_key TEXT, turn_index INTEGER, role TEXT, ts REAL, content TEXT,
      PRIMARY KEY (session_key, turn_index))
```

La ricerca opera su `turns.content`, restituisce il **turno** + riferimento alla **sessione**
(`session_key`, `captured_at`, `role`, `turn_index`).

---

## Artefatto derivato (questa feature) — indice FTS5

Tabella virtuale **external-content** che indicizza `turns.content`, nello stesso file:

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS turns_fts
  USING fts5(content, content='turns', content_rowid='rowid');

-- trigger di sincronizzazione (external-content pattern), idempotenti
CREATE TRIGGER IF NOT EXISTS turns_ai AFTER INSERT ON turns BEGIN
  INSERT INTO turns_fts(rowid, content) VALUES (new.rowid, new.content);
END;
CREATE TRIGGER IF NOT EXISTS turns_ad AFTER DELETE ON turns BEGIN
  INSERT INTO turns_fts(turns_fts, rowid, content) VALUES('delete', old.rowid, old.content);
END;
CREATE TRIGGER IF NOT EXISTS turns_au AFTER UPDATE ON turns BEGIN
  INSERT INTO turns_fts(turns_fts, rowid, content) VALUES('delete', old.rowid, old.content);
  INSERT INTO turns_fts(rowid, content) VALUES (new.rowid, new.content);
END;
```

- **Derivato e ricostruibile** (Principio VI): `INSERT INTO turns_fts(turns_fts) VALUES('rebuild')`
  rigenera l'indice da `turns` — recovery se cancellato/corrotto; popolamento una-tantum per archivi
  pre-esistenti a questa feature.
- **Sincronia**: i trigger aggiornano l'indice nella stessa transazione dell'insert di FEAT-001
  (`archive.py:78`) → freschezza by construction (FR-020/SC-008). FEAT-001 resta invariata: lo schema
  FTS è creato (lazy, idempotente) dal componente di ricerca, non da `MemoryArchive`.
- **Git-ignored**: l'indice vive dentro `memory.sqlite`, già git-ignored come gli altri artefatti
  rigenerabili (Principio Sicurezza/`.gitignore`).

---

## Entità di dominio (nuove, additive)

### `SearchQuery` (input)

Input di una ricerca: testo + vincoli opzionali. `frozen=True`.

| Campo | Tipo | Note |
|-------|------|------|
| `text` | `str` | testo da cercare (sintassi MATCH FTS5; vuoto/spazi → stato vuoto, FR/edge) |
| `since` | `float \| None` | epoch UTC; `captured_at >= since` ("da quella data in poi", FR-006) |
| `until` | `float \| None` | epoch UTC; `captured_at <= until` ("fino a data inclusa", FR-006) |
| `order` | `Literal["relevance","recency"]` | default `"relevance"` (FR-008/FR-009) |
| `limit` | `int` | max risultati, default da `Settings` (FR-010); `<=0` → stato vuoto |
| `snippet_tokens` | `int` | lunghezza snippet, default da `Settings` (FR-011) |

**Validazione**: `since is not None and until is not None and since > until` →
`InvalidTimeWindowError` (Principio IV, FR-007). Query vuota/whitespace → stato vuoto (non errore).

### `EpisodicHit` (risultato per turno)

Un turno corrispondente arricchito di citazione. `frozen=True`. Unità di **restituzione** (FR-021).

| Campo | Tipo | Mappa da | Requisito |
|-------|------|----------|-----------|
| `session_key` | `str` | `turns.session_key` | FR-002/FR-012 |
| `captured_at` | `float` | `sessions.captured_at` | FR-002/FR-012 |
| `role` | `str` | `turns.role` | FR-002 |
| `turn_index` | `int` | `turns.turn_index` | FR-002/FR-012 |
| `source_path` | `str \| None` | (non in schema oggi → `None`) | FR-002 "se disponibile" |
| `snippet` | `str` | `snippet(turns_fts,…)` | FR-002/FR-011 |
| `score` | `float` | `-bm25(turns_fts)` (più alto = più pertinente) | FR-008 (segnale ordinamento) |

`source_path` resta `None` finché FEAT-001 non lo persiste (edge case "sessione priva di path":
risultato valido e citabile senza path).

### `EpisodicResults` (esito)

Contenitore esplicito dell'esito (evita `None` ambiguo, Principio IV).

| Campo | Tipo | Note |
|-------|------|------|
| `hits` | `tuple[EpisodicHit, ...]` | risultati ordinati; vuoto = stato vuoto esplicito |
| `latency_ms` | `float` | per osservabilità (FR-017) e test di latenza (SC-006) |

> Stato vuoto = `EpisodicResults(hits=(), …)`: distingue "nessun match / archivio assente / indice
> assente" (tutti FR-004/FR-014, non eccezioni) da "errore" (solo finestra invalida → eccezione).

---

## Errori di dominio

| Eccezione | Quando | Principio |
|-----------|--------|-----------|
| `InvalidTimeWindowError` | `since > until` (FR-007) | IV (errore esplicito, azionabile) |

Tutto il resto è **degradazione non-fatale** (stato vuoto + warning), MAI eccezione:
archivio assente/vuoto (FR-004/FR-014), indice FTS assente/`OperationalError` FTS5 mancante
(FR-014, research DA-FT-001), voce malformata (FR-013, salta + warning), guasto osservabilità
(FR-018). Pattern identico a `MemoryArchive`/`SqliteObservabilityStore` (warning + `[]`/`None`).

`InvalidTimeWindowError` è una nuova eccezione di dominio in `domain/errors.py` (accanto a
`ConfigError`), coerente con lo stile delle eccezioni di dominio del core.
