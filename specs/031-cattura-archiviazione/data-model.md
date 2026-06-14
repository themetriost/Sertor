# Phase 1 — Data Model: Cattura & archiviazione locale dei transcript (031)

**Feature**: `031-cattura-archiviazione` · **Spec**: [spec.md](./spec.md) · **Research**: [research.md](./research.md)

Entità di dominio (pure, nessun import di SDK — Principio I), schema persistente e porta. Tutte le
strutture sono `@dataclass(frozen=True)` come le entità esistenti in
`src/sertor_core/domain/entities.py`. I tipi vivono in un nuovo modulo `domain/memory.py` (separato per
SRP; importato da `entities.py`-style consumer dove serve).

---

## 1. Entità di dominio

### SessionRef — riferimento leggero a una sessione presso la sorgente

Prodotto da `TranscriptCaptureAdapter.list_sessions()` durante la scoperta; porta la chiave canonica e
quanto basta per leggere il contenuto, **senza** caricarlo (lazy).

```python
@dataclass(frozen=True)
class SessionRef:
    session_key: str   # chiave canonica = stem del filename (FR-008); idempotenza
    project_id: str    # namespace del progetto ospite (FR-010), fornito dall'adapter
    source_path: str   # percorso opaco alla sorgente (host-specifico; il servizio non lo interpreta)
```

- `session_key`: stabile, derivato dal nome file (D4). Chiave PK in `sessions`.
- `project_id`: host-agnostico — l'adapter lo fornisce (per Claude Code = identità del progetto/`cwd`);
  il servizio lo tratta come opaco (Principio X).
- `source_path`: usato **solo** dall'adapter in `read_session`; il servizio non lo apre né lo interpreta.

### TranscriptTurn — un turno conversazionale (confine preservato)

Unità a grana di turno **prima dello scrub** (lo scrub avviene nel servizio). `role` ∈ {`user`,
`assistant`}; `ts` nullable (timestamp assente/illeggibile nella sorgente → `None`, D3 regola 4).

```python
@dataclass(frozen=True)
class TranscriptTurn:
    index: int          # ordinale stabile nell'ordine di emissione (idempotenza turni)
    role: str           # 'user' | 'assistant'
    text: str           # testo del turno (ancora NON scrubbed)
    ts: float | None = None   # epoch UTC del turno, None se assente nella sorgente
```

### TranscriptContent — contenuto strutturato di una sessione (pre-scrub)

Prodotto da `TranscriptCaptureAdapter.read_session(ref)`: i turni estratti best-effort dalla sorgente.

```python
@dataclass(frozen=True)
class TranscriptContent:
    session_key: str
    project_id: str
    adapter_kind: str            # tipo di adapter sorgente (→ sessions.adapter_kind, FR-012)
    captured_at: float           # epoch UTC dell'istante di cattura (FR-012)
    turns: tuple[TranscriptTurn, ...]   # confini dei turni preservati (FR-013)
```

- Una sessione con `turns` vuota viene **saltata** dal servizio (non crea record vuoto, D3 regola 5).

### ArchivedSession — l'unità conservata nell'archivio (post-scrub)

Vista di dominio del record persistito. `content` dei turni è **già scrubbed**. Usata come valore di
lettura (es. test, o FEAT-002 in futuro); la scrittura passa per `MemoryArchive.upsert`.

```python
@dataclass(frozen=True)
class ArchivedSession:
    session_key: str
    project_id: str
    captured_at: float
    adapter_kind: str
    turns: tuple[TranscriptTurn, ...]   # scrubbed
    retention_days: int | None = None   # gancio retention (FR-021), registrato nei metadati
```

---

## 2. Porta nuova (host-agnostica)

### TranscriptCaptureAdapter — l'8ª porta `Protocol`

In `src/sertor_core/domain/ports.py`, stesso stile delle 7 esistenti (`@runtime_checkable`, structural
typing, no inheritance, mockabile senza subclassing — `domain/ports.py:24+`).

```python
@runtime_checkable
class TranscriptCaptureAdapter(Protocol):
    """Astrazione host-agnostica della cattura dei transcript (FR-004).

    Separa il *cosa* (elencare sessioni, leggerne il contenuto in turni) dal *come* host-specifico.
    Claude Code è la prima implementazione, scelta SOLO via configurazione (FR-005). La sorgente è
    di sola lettura: list/read non modificano né cancellano i file (FR-007)."""

    kind: str  # tipo di adapter (es. "claude-code") → sessions.adapter_kind (FR-012)

    def list_sessions(self) -> list[SessionRef]:
        """Riferimenti alle sessioni del progetto corrente presso la sorgente.

        Sorgente assente/vuota → [] (l'adapter emette il warning; il servizio lascia l'archivio
        invariato, FR-006). Non solleva un errore non gestito."""
        ...

    def read_session(self, ref: SessionRef) -> TranscriptContent:
        """Legge la sessione e ne struttura i turni (best-effort difensivo, D3).

        Righe non parsabili → skip + warning, mai fatale. Una sessione senza turni estraibili
        ritorna `turns=()` (il servizio la salta)."""
        ...
```

**Nota porte/store.** Lo store di archivio **non** ha una porta (D2): è il componente concreto
`MemoryArchive` (sotto), cablato in composition come `EmbeddingCache`/`SqliteObservabilityStore`.

---

## 3. Store di archivio (concreto, stdlib-only)

### MemoryArchive — `<index_dir>/memory.sqlite`

Componente concreto (no porta), pattern identico a `SqliteObservabilityStore`
(`observability/store.py:23`): lazy connect, schema idempotente, degradazione non-fatale.

```python
class MemoryArchive:
    def __init__(self, index_dir: Path | str): ...   # salva solo il path
    def _connect(self) -> sqlite3.Connection: ...     # lazy, CREATE TABLE IF NOT EXISTS, _conn None su corruzione

    def upsert(self, session: ArchivedSession) -> bool:
        """INSERT OR IGNORE della sessione + dei suoi turni (stessa transazione).
        Ritorna True se NUOVA (inserita), False se già presente (skip). Non-fatale su
        sqlite3.Error: warning + ritorna False (FR-025). Idempotente (FR-015/016)."""

    def exists(self, session_key: str) -> bool: ...   # per il controllo di idempotenza/skip

    def get(self, session_key: str) -> ArchivedSession | None: ...   # lettura (test/FEAT-002)
```

### Schema SQLite (vedi D1)

```sql
CREATE TABLE IF NOT EXISTS sessions (
    session_key   TEXT PRIMARY KEY,
    project_id    TEXT NOT NULL,
    captured_at   REAL NOT NULL,
    adapter_kind  TEXT NOT NULL,
    metadata      TEXT NOT NULL          -- JSON: {retention_days, source_path, turn_count}
);
CREATE TABLE IF NOT EXISTS turns (
    session_key  TEXT NOT NULL,
    turn_index   INTEGER NOT NULL,
    role         TEXT NOT NULL,          -- 'user' | 'assistant'
    ts           REAL,                   -- nullable
    content      TEXT NOT NULL,          -- scrubbed
    PRIMARY KEY (session_key, turn_index)
);
CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions (project_id);
CREATE INDEX IF NOT EXISTS idx_turns_session ON turns (session_key, turn_index);
```

**Idempotenza (FR-015/016).** PK su `session_key` e su `(session_key, turn_index)`; `INSERT OR IGNORE`.
Ri-archiviare una sessione esistente non altera nulla e non solleva errori (skip osservabile lato
servizio, FR-024). Conservazione (FR-014): nessun `DELETE`/`REPLACE` in questa feature.

**Gancio retention (FR-021/022).** `retention_days` vive in `sessions.metadata` (JSON): registrato, **mai
applicato** qui. FEAT-006 leggerà il campo senza migrazione di schema.

---

## 4. Funzione pura di scrub

### scrub_text — `observability/scrub.py` (vedi D6)

```python
def scrub_text(text: str, extra_patterns: tuple[str, ...] = ()) -> str:
    """Sostituisce i pattern di segreto con un segnaposto nel testo libero (FR-017/018).
    Pura, deterministica, testabile offline (SC-004). Pattern: API key (sk-…, AKIA…),
    bearer/Authorization, KEY=VALUE con hint di segreto, header inline; + extra_patterns
    configurabili (FR-020). Su errore di un pattern → redige il segmento + warning (FR-019)."""
```

Pre-compila le regch base una volta a livello di modulo (come `_WORD` in `observability/logging.py:19`);
`extra_patterns` compilate per chiamata (input di config, bassa cardinalità).

---

## 5. Mappa entità → requisiti

| Entità / componente | Requisiti |
|---|---|
| `SessionRef` | FR-008, FR-010, US3 |
| `TranscriptTurn` / `TranscriptContent` | FR-013 (confini turni), D3 |
| `ArchivedSession` | FR-012, FR-021 |
| `TranscriptCaptureAdapter` (porta) | FR-004, FR-005, FR-006, FR-007, US3 |
| `MemoryArchive` (store) | FR-009..016, FR-025, SC-001/002/006/007 |
| `scrub_text` | FR-017..020, FR-027, SC-004 |
| manopole Settings | FR-001/002/003, FR-020, FR-021 |
