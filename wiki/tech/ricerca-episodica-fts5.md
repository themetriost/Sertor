---
title: Ricerca episodica FTS5 — Motore full-text locale
type: tech
tags: [sqlite, fts5, full-text-search, indice, trigger-synced, episodico, ricerca-episodica]
created: 2026-06-14
updated: 2026-07-23
sources: ["src/sertor_core/services/episodic_search.py", "src/sertor_core/domain/memory.py", "https://www.sqlite.org/fts5.html"]
---

# Ricerca episodica FTS5 — motore full-text locale

Componente concreto di FEAT-002: ricerca testuale a granularità di turno sull'archivio dei transcript conservato da FEAT-001, usando **FTS5 nativo di SQLite** per l'indicizzazione e il ranking.

## Motore scelto: SQLite FTS5

**Perché FTS5 e non alternativi:**

- **Già presente**: SQLite è una dipendenza del core (usata per l'archivio di FEAT-001). FTS5 è un extension nativo standard (no dipendenze esterne).
- **Full-text leggero**: BM25 ranking, snippet context extraction, tutto in stdlib (modulo sqlite3).
- **Locale-first**: tutta la logica nel database; niente server, niente rete.
- **Perf attesa**: archivi di dimensione tipica (5k–50k turni) interrogabili in <200ms su hardware consumer, anche con i vincoli di finestra temporale.

Alternativa scartata: il `LexicalIndex` BM25 già presente nel core (adapters/lexical/bm25.py) è basato su scikit-learn (dipendenza pesante + non adatta a query change-prone), non generico per la ricerca episodica standalone.

## Architettura del database

**Schema (estende FEAT-001)**

```sql
-- Tabella originale di FEAT-001
CREATE TABLE sessions (
    session_key TEXT PRIMARY KEY,
    captured_at INTEGER,  -- timestamp unix
    adapter TEXT,
    transcript_path TEXT
);

CREATE TABLE turns (
    id INTEGER PRIMARY KEY,
    session_key TEXT NOT NULL,
    turn_index INTEGER NOT NULL,
    role TEXT NOT NULL,
    captured_at INTEGER,  -- timestamp del turno
    content TEXT NOT NULL,
    FOREIGN KEY (session_key) REFERENCES sessions(session_key)
);

-- Indice FTS5 aggiunto da FEAT-002
CREATE VIRTUAL TABLE turns_fts USING fts5(
    content,          -- contenuto del turno
    content=turns,    -- colonna della tabella "turns"
    content_rowid=id  -- mapping alla PK
);

-- Trigger di sincronizzazione: ogni INSERT/DELETE in turns
-- aggiorna automaticamente turns_fts (freschezza per costruzione)
CREATE TRIGGER turns_ai AFTER INSERT ON turns BEGIN
    INSERT INTO turns_fts(rowid, content) 
    VALUES (new.id, new.content);
END;

CREATE TRIGGER turns_ad AFTER DELETE ON turns BEGIN
    INSERT INTO turns_fts(turns_fts, rowid, content) 
    VALUES ('delete', old.id, old.content);
END;
```

**Propriet√† di costruzione:**

- **Contenuto indicizzato**: solo il testo (`turns.content`), non metadata. Metadata (session_key, turn_index, ruolo, timestamp) sono raggiungibili via join su `rowid`.
- **Trigger sincroni**: FTS5 si aggiorna **subito** alla INSERT di una nuova sessione (FEAT-001), nessun rebuild lazy. Freschezza garantita: la ricerca successiva vede i turni nuovi.
- **Idempotenza**: `INSERT OR IGNORE` in FEAT-001 garantisce che lo stesso turno non viene inserito due volte; FTS5 segue.

## Componente `EpisodicSearch`

**Interfaccia pubblica:**

```python
class SearchQuery:
    """Input di una ricerca."""
    text: str                      # query testuale
    since: Optional[date] = None   # filtro: sessioni da questa data
    until: Optional[date] = None   # filtro: sessioni fino a questa data
    limit: int = 20                # max risultati
    snippet_tokens: int = 12       # lunghezza snippet
    order_by: Literal["relevance", "recency"] = "relevance"

class EpisodicHit:
    """Un turno che corrisponde alla query."""
    session_key: str               # id sessione padre
    captured_at: datetime          # timestamp della sessione
    role: str                       # "user" o "assistant"
    turn_index: int                # ordinale nella sessione
    snippet: str                   # frammento di contesto con match
    score: float                   # BM25 score (solo se order_by="relevance")

class EpisodicResults:
    """Output di una ricerca."""
    hits: List[EpisodicHit]
    latency_ms: float              # tempo totale query (benchmark)

class EpisodicSearch:
    """Servizio di ricerca."""
    def search(self, query: SearchQuery) -> EpisodicResults:
        """Esegui ricerca full-text con vincoli opzionali."""
```

**Logica di ricerca (funzione pura):**

1. **Validazione input**:
   - Query vuota/spazi → stato vuoto senza errore.
   - `since > until` → `InvalidTimeWindowError`.
   
2. **Costruzione query SQL**:
   ```sql
   SELECT 
       turns.id,
       turns.session_key,
       sessions.captured_at,
       turns.role,
       turns.turn_index,
       turns_fts.rank,
       snippet(turns_fts, 0, '[', ']', '…', 12) AS snippet
   FROM turns_fts
   JOIN turns ON turns_fts.rowid = turns.id
   JOIN sessions ON turns.session_key = sessions.session_key
   WHERE turns_fts MATCH ?       -- full-text match
     AND sessions.captured_at >= ? (if since)
     AND sessions.captured_at <= ? (if until)
   ORDER BY ...
   LIMIT ?
   ```

3. **Ordinamento**:
   - `relevance` (default): `turns_fts.rank ASC` (BM25), tie-break `sessions.captured_at DESC` (recency).
   - `recency`: `sessions.captured_at DESC`.

4. **Snippet**: FTS5 `snippet()` estrae un frammento di testo attorno al match, luogo configurabile.

5. **Degradazione**:
   - Archivio assente → warning, `EpisodicResults(hits=[], latency_ms=X)`.
   - FTS5 non disponibile (rarissimo: SQLite senza FTS5) → stesso.
   - Voce malformata nel join → skip + warning, continuare con le altre.

## Osservabilità

**Evento emesso al completamento di ogni ricerca**:

```python
log_event(
    operation="episodic_search",
    extra={
        "query_hash": sha256(text)[:16],      # mai il testo in chiaro
        "since": since.isoformat() if since else None,
        "until": until.isoformat() if until else None,
        "order_by": order_by,
        "hits": len(results.hits),
        "latency_ms": results.latency_ms,
    }
)
```

**Sicurezza**: la query **non si registra in testo**, solo il suo hash. Se una ricerca contiene informazioni sensibili (per errore), il testo non entra mai nei log. Inoltre:
- `since`/`until` sono date pubbliche, registrate.
- Il numero di risultati è interessante per l'analisi di utilizzo.
- La latenza è rilevante per il monitoring.

## Proprietà di performance e robustezza

| Proprietà | Realizzazione |
|-----------|---------------|
| **Offline** | Tutta la logica SQLite locale; zero rete. |
| **Non-distruttiva** | FTS5 è un indice derivato (ricostruibile da `turns`). L'archivio sottostante non è mai modificato dalla ricerca. |
| **Fresco** | Trigger sincroni garantiscono che le nuove sessioni di FEAT-001 sono ricercabili subito, senza rebuild. |
| **Robusto** | Archivio assente/vuoto/danneggiato → stato vuoto + warning, mai errore. |
| **Testabile** | Logica isolata, archivi mock in tmp_path, nessuna dipendenza esterna. |
| **Host-agnostico** | Opera sull'archivio indipendentemente da quale assistente lo ha prodotto (FEAT-001 è l'astrazione). |

## Limiti noti

- **No regex**: FTS5 non supporta regex. La ricerca è lessicale substring; pattern come `logistic|logistiche` non funzionano.
- **No stemming**: la ricerca è exact token match per la lingua italiana (no stemming built-in). Query «capire» non troverà «capito», «capace».
- **No semantica**: FTS5 è lessicale puro, non embeds nulla. Query semantica è FEAT-004 (out-of-scope).

Nessuno di questi è un problema per l'MVP: la ricerca testuale locale risponde agli use case («ne avevamo già parlato di X?») e prepara il terreno per estensioni future.

---

## Pagine collegate

- [[feat-002-ricerca-episodica-fulltext]] — record della feature implementata.
- [[memoria-conversazioni]] — il concetto, il tier episodico della memoria.
- [[feat-001-memoria-cattura-archiviazione]] — la sorgente dati (archivio FEAT-001).
- [[transcript-capture-adapter-e-storage]] — il formato dei dati (sessioni + turni).
