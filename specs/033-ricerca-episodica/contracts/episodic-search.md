# Contract — Ricerca episodica (`sertor.episodic-search/1`)

**Feature**: 033 · **Tipo**: interfaccia interna di libreria (componente concreto del core,
nessuna porta Protocol — vedi `research.md` §Porta). Consumata da una superficie d'uso fuori ambito.

Questo contratto descrive la **forma osservabile** del componente di ricerca episodica: cosa accetta,
cosa restituisce, quali invarianti garantisce. È il riferimento per i test di contratto (offline,
`tmp_path`, archivio sintetico).

---

## Componente: `EpisodicSearch`

Componente concreto in `services/episodic_search.py` (servizio) che usa l'indice FTS5 sul file
`<index_dir>/memory.sqlite` di FEAT-001. Stdlib-only (`sqlite3`, `hashlib`, `time`, `logging`).

### `search(query: SearchQuery) -> EpisodicResults`

Esegue una ricerca full-text locale a grana di turno.

**Precondizioni**

- `query.text`: stringa qualsiasi (sintassi MATCH FTS5). Vuota/whitespace → vedi P-EMPTY.
- `query.since`/`query.until`: epoch UTC o `None`. Se entrambi presenti, `since <= until`, altrimenti
  C-ERR.

**Postcondizioni / invarianti**

| Id | Garanzia | Requisito |
|----|----------|-----------|
| C-MATCH | Ogni turno il cui `content` contiene un match della query compare in `hits` (completezza match esatti) | FR-001, SC-001 |
| C-CITE | Ogni hit riporta `session_key`, `captured_at`, `role`, `turn_index`, `snippet`, `score` (+ `source_path` se disponibile) | FR-002, SC-002 |
| C-LOCAL | Nessun I/O di rete durante `search` (solo SQLite locale) | FR-003, SC-004 |
| C-ORDER-R | `order="relevance"` (default): pertinenza desc, tie-break `captured_at` desc | FR-008 |
| C-ORDER-T | `order="recency"`: `captured_at` desc, pertinenza relativa ignorata | FR-009 |
| C-LIMIT | `len(hits) <= query.limit`; mai l'intero archivio incondizionato | FR-010, SC US3.3 |
| C-SNIP | Ogni hit ha uno snippet di contesto finito, coerente anche ai bordi del testo | FR-011, edge |
| C-TIME | Con finestra, nessun hit la cui sessione cade fuori; tutti i match dentro inclusi | FR-005/006, SC-003 |
| C-FRESH | Una sessione archiviata da FEAT-001 è ricercabile alla prima `search` successiva | FR-020, SC-008 |
| C-MULTI | Più turni della stessa sessione che matchano → più hit distinti, stessa sessione padre | edge |
| C-OBS | A completamento emette evento `episodic_search` (query redatta/hashed, filtri, conteggio, latenza) | FR-017 |
| C-HOST | Il corpo non assume l'assistente sorgente; opera sull'archivio locale qualunque sia la provenienza | FR-015/016, SC-007 |

**Stato vuoto (NON errore)** — `EpisodicResults(hits=())`:

| Id | Caso | Requisito |
|----|------|-----------|
| P-EMPTY | `query.text` vuota o di soli spazi | edge |
| P-NOMATCH | Nessun turno corrisponde | FR-004, SC-005 |
| P-NOARCH | Archivio assente (file mai creato/cancellato) → warning + vuoto | FR-004/FR-014, SC-005 |
| P-EMPTYARCH | Archivio vuoto | FR-004 |
| P-NOINDEX | Indice FTS assente o FTS5 non disponibile nel `sqlite3` dell'host → warning + vuoto | FR-014, research DA-FT-001 |
| P-NOWINDOW | Finestra temporale che non include alcuna sessione | edge |
| P-BADROW | Voce illeggibile/malformata → salta quella, warning, continua sulle valide | FR-013, SC-005 |
| P-OBSFAIL | Guasto nell'emissione dell'evento → risultato comunque restituito (non-fatale) | FR-018, edge |

**Errori (eccezione esplicita, Principio IV)**

| Id | Caso | Eccezione |
|----|------|-----------|
| C-ERR | `since > until` | `InvalidTimeWindowError` (descrive l'intervallo non valido) |

---

## Indice FTS5 — invarianti di consistenza

| Id | Garanzia | Requisito |
|----|----------|-----------|
| I-SYNC | I trigger su `turns` mantengono `turns_fts` allineato a ogni INSERT/UPDATE/DELETE | FR-020 |
| I-REBUILD | `turns_fts` è ricostruibile da `turns` (`'rebuild'`); cancellarlo non perde dati (derivato) | VI |
| I-IDEMP | Creazione schema FTS + trigger idempotente (`IF NOT EXISTS`); non altera `MemoryArchive` | VI, additività |
| I-ONCE | Su archivio pre-esistente senza indice: prima connessione crea+popola una-tantum | FR-020, retrocompat |

---

## Osservabilità (evento `episodic_search`)

Campi: `query_hash` (sha256 troncato del testo — **mai** in chiaro), `query_len`, `since`, `until`,
`order`, `limit`, `results` (conteggio), `latency_ms`. Emesso via `log_event` (stdlib `logging`),
redazione per-campo già applicata (`observability/logging.py`). Non-fatale (P-OBSFAIL).

---

## Configurazione (manopole, da `Settings`)

| Manopola | Env | Default | Effetto |
|----------|-----|---------|---------|
| `episodic_limit` | `SERTOR_EPISODIC_LIMIT` | `20` | max risultati (FR-010) |
| `episodic_snippet_tokens` | `SERTOR_EPISODIC_SNIPPET_TOKENS` | `12` | lunghezza snippet (FR-011) |

Default solo in `Settings` (Principio VIII), nessun hardcode nei componenti. Il gate di opt-in è
`memory_enabled` (riusato da FEAT-001: senza memoria attiva, nessun indice/file).
