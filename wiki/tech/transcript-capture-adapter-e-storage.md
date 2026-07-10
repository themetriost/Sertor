---
title: Transcript Capture Adapter & Memory Archive (9ª porta + adapter + store)
type: tech
tags: [memoria, capture, adapter, storage, sqlite, host-agnostico, principio-x, feat-001, feat-008, ports-adapters]
created: 2026-06-14
updated: 2026-06-22
sources: ["src/sertor_core/domain/ports.py", "src/sertor_core/domain/memory.py", "src/sertor_core/adapters/capture/", "src/sertor_core/adapters/memory/", "src/sertor_core/services/memory_archive.py", "src/sertor_core/composition.py"]
---

# Transcript Capture Adapter & Memory Archive — le tre componenti

La cattura e l'archiviazione dei transcript è costruita su tre livelli ortogonali: una **porta astratta** (host-agnostico), un **adapter** concreto (host-specifico), uno **store** locale (generico). Parallelo al pattern dei retriever ([[ports-adapters]]).

## 9ª Porta: `TranscriptCaptureAdapter` (Principio X)

Definita in `domain/ports.py` (15 righe di contratto), implementata come `@runtime_checkable` Protocol (structural typing).

```python
@runtime_checkable
class TranscriptCaptureAdapter(Protocol):
    kind: str  # e.g. "claude-code"
    
    def list_sessions(self) -> list[SessionRef]:
        """Current project's sessions at the source. 
        Source absent/empty → [] (adapter warns, service leaves archive unchanged)."""
        ...
    
    def read_session(self, ref: SessionRef) -> TranscriptContent:
        """Read session and structure turns (best-effort, defensive).
        Unparsable lines → skip + warning, never fatal.
        A session with no extractable turns returns turns=()."""
        ...
```

### Responsabilità della porta

- **Enumerare** le sessioni presso una sorgente host-specifica (e.g. file JSONL di Claude Code).
- **Leggere** il contenuto di una sessione e **strutturarlo in turni** (boundaries preserved per la ricerca di FEAT-002).
- **Produrre** riferimenti leggeri (`SessionRef`: session key, project id, source path opaco).
- **Non modificare né cancellare** la sorgente (read-only).
- **Essere tolerante**: sorgente assente → `[]` + warning; linee non-parsabili → skip + warning; mai fatale.

### Entità di dominio (pure)

Tre dataclass in `domain/memory.py`:

1. **`SessionRef`**: lightweight reference a una sessione presso la sorgente.
   - `session_key` (str): chiave canonica, dal filename per Claude Code, drives idempotency.
   - `project_id` (str): namespace del progetto ospite (Principio X: diverse cartelle per diversi progetti).
   - `source_path` (str): opaco, host-specifico; il servizio non lo interpreta.

2. **`TranscriptTurn`**: singolo turno conversazionale (pre-scrub).
   - `index` (int): ordinale stabile nel flusso.
   - `role` (str): 'user' | 'assistant'.
   - `text` (str): non ancora scrubbed.
   - `ts` (float | None): epoch UTC, nullable se assente nella sorgente.

3. **`TranscriptContent`**: output di `read_session`, pre-scrub.
   - `session_key`, `project_id`, `adapter_kind`, `captured_at` (epoch UTC).
   - `turns` (tuple[TranscriptTurn, ...]): confini preservati.

## Adapter Concreto: Claude-Code

In `adapters/capture/claude_code.py` (165 righe).

### Come funziona

1. **Enumerazione**: scandisce `CLAUDE_PROJECTS_DIR` (default `~/.claude/projects`) cercando cartelle di progetto encoded (e.g. `C--Workspace-Git-Sertor`), poi dentro cerca i file `*.jsonl` di sessione.

2. **Parsing JSONL**: per ogni file, parsifica best-effort:
   - Linea = JSON record con `role` (user | assistant), `content`/`blocks` (testo).
   - Linee non-JSON → skip + warning.
   - Fallback: se il JSON non ha le chiavi attese, estrae best-effort (nessun crash).

3. **Chiave canonica**: dal stem del filename (e.g. `abc12345.jsonl` → session_key = `abc12345`), drives `INSERT OR IGNORE` idempotenza.

4. **Non-mutativo**: legge i file senza modificarli né cancellarli. Nessun hook runtime; dipende da Claude Code che persiste.

### Configurazione

- `SERTOR_MEMORY_ADAPTER` = "claude-code" (default).
- `SERTOR_MEMORY_CLAUDE_PROJECTS_DIR` = path a ~/.claude/projects (per testabilità).

### Limitazioni e fallback

- **Directory assente**: warning, `list_sessions()` ritorna `[]`, servizio lascia archivio invariato.
- **Progetto non trovato** (CWD encoded non esiste): warning, `[]`.
- **File di sessione corrotto**: skip + warning per quella sessione, continua con le altre.

## Secondo Adapter: GitHub Copilot CLI (FEAT-008)

In `adapters/capture/copilot_cli.py` (180 righe, implementato 2026-06-22).

### Come funziona

1. **Enumerazione**: scandisce `~/.copilot/session-state/` cercando directory UUID, poi dentro legge `events.jsonl`.

2. **Parsing JSONL**: identico a Claude Code (stesso formato JSONL, stesso parsing best-effort).

3. **Associazione progetto**: il `session.start` event contiene metadati `cwd` (working directory) e `gitRoot` (antenato git). Una sessione appartiene al progetto se:
   - `cwd` **è dentro-o-uguale** il progetto (POSIX path normalization, case-sensitive), **OPPURE**
   - `gitRoot` **è antenato-o-uguale** il progetto.
   
   Logica **asimmetrica**: se nessuna condizione è soddisfatta, la sessione è ignorata (no-op, non associata). Evita misattribuzioni quando Copilot è aperto in una cartella diversa dal progetto.

4. **Non-mutativo**: legge i file senza modificarli né cancellarli. Privacy by design — Sertor legge il locale, ignora la sincronizzazione cloud di Copilot.

### Configurazione

- `SERTOR_MEMORY_ADAPTER` = "copilot-cli" (sostituisce default "claude-code").
- `SERTOR_MEMORY_COPILOT_SESSION_DIR` = path a ~/.copilot/session-state (per testabilità).

### Differenze da Claude-Code

| Aspetto | Claude Code | Copilot CLI |
|---------|-------------|------------|
| **Cartella sessioni** | `~/.claude/projects/` (encoded per progetto) | `~/.copilot/session-state/` (UUID globali) |
| **Filename** | `<session-id>.jsonl` (filename = chiave) | `events.jsonl` in cada UUID (UUID = chiave) |
| **Associazione progetto** | Nome cartella encoded include CWD | Letta da `session.start` event (cwd/gitRoot) |
| **Formato JSONL** | Identico | Identico |

### Limitazioni e fallback

- **Cartella assente**: warning, `list_sessions()` ritorna `[]`.
- **Sessione senza metadati di progetto**: warning, ignorata (associazione fallita).
- **Associazione fallita** (cwd/gitRoot non corrispondono): no-op, sessione ignorata, continua.
- **File events.jsonl corrotto**: skip + warning, continua con le altre UUID.

## Store Concreto: `MemoryArchive`

In `adapters/memory/archive.py` (150 righe).

### Schema e struttura

SQLite locale `<index_dir>/memory.sqlite` (gitignored, creato on-demand).

Tabelle:
1. **`sessions`** (chiave: `(project_id, session_key)`):
   - `id` (PK integer autoincrement).
   - `project_id`, `session_key`: namespace e chiave canonica.
   - `captured_at` (epoch UTC).
   - `adapter_kind` (e.g. "claude-code").
   - `content_scrubbed` (TEXT: JSON-array di turn scrubbed).
   - `size_bytes` (dopo scrub, metrica).
   - `retention_days` (int | NULL): policy registrata, non applicata qui.
   - Indice: `(project_id, session_key)` per idempotenza rapida.

2. **`turns`** (reference a sessions):
   - `id` (PK).
   - `session_id` (FK a sessions.id).
   - `turn_index` (ordinale nello stream).
   - `role` (user | assistant).
   - `text_scrubbed` (per ricerca FEAT-002).
   - `ts_epoch` (nullable).

### Operazioni

- **`upsert(session_key, project_id, content_scrubbed, retention_days)`**:
  - `INSERT OR IGNORE` idempotente sulla coppia `(project_id, session_key)`.
  - Se esiste → nessun cambio, nessun errore (idempotenza silente).
  - Se nuovo → inserisce sessione + righe di turni, registra retention policy nei metadati.

- **`query_sessions(project_id, since=None, until=None)`**:
  - Per FEAT-002: sessions di un progetto in un intervallo temporale.

- **`get_turns(session_id)`**:
  - Righe di turni di una sessione, per ricerca episodica.

### Robustezza

- **Store assente o corrotto**: `MemoryArchive.upsert()` cattura l'eccezione, emette warning, no-op (no-fatale).
- **Permessi insufficienti**: warning + no-op.
- **Disco pieno**: warning + no-op.
- Nessuna propagazione di errore al servizio.

## Servizio orchestrante: `MemoryArchiveService`

In `services/memory_archive.py` (90 righe).

Orchester il flusso list → read → scrub → upsert.

```python
def archive(self) -> ArchiveRunReport:
    """List sessions → read → scrub → upsert, idempotent.
    
    Emits memory_session_archived (new), memory_session_skip (already present),
    memory_archive_failed (degraded on store error).
    
    Returns counts: archived, skipped, failed.
    """
```

### Garanzie

- **Idempotente**: rilanciare con le stesse sessioni non crea duplicati.
- **Non-bloccante**: store failure → warning + skip, operazione principale non interrotta.
- **Osservabile**: evento per sessione (nuova/skip) e per fallo.
- **Scrubbed before persist**: il servizio chiama `scrub_text(transcript)` su tutto il contenuto prima di passarlo al store.

## Scrub del contenuto (ortogonale)

Il servizio + il store usano [[scrub-segreti-in-contenuto]] per ripulire il contenuto prima di persistere.

---

## Composizione e configurazione

Cablata in `composition.py`:

```python
_VALID_MEMORY_ADAPTERS = ("claude-code", "copilot-cli")

def build_capture_adapter(settings: Settings) -> TranscriptCaptureAdapter | None:
    if not settings.memory_enabled:
        return None
    match settings.memory_adapter_kind:
        case "claude-code":
            return ClaudeCodeCaptureAdapter(settings.memory_claude_projects_dir)
        case "copilot-cli":
            return CopilotCliTranscriptAdapter(
                settings.copilot_session_dir or Path.home() / ".copilot" / "session-state"
            )
        case _:
            raise ConfigError(f"Unknown memory adapter: {settings.memory_adapter_kind}")

def build_memory_archive(index_dir: Path) -> MemoryArchive:
    return MemoryArchive(index_dir / "memory.sqlite")

def build_memory_archiver(
    adapter: TranscriptCaptureAdapter,
    archive: MemoryArchive,
    scrubber: ScrubConfig
) -> MemoryArchiveService:
    return MemoryArchiveService(adapter, archive, scrubber)
```

Costruiti SOLO se `SERTOR_MEMORY=true` (import lazy).

## Stato

- ✅ **Port + adapter Claude-Code + store**: implementati in FEAT-001 (PR #45, 2026-06-14).
- ✅ **Adapter Copilot CLI**: implementato in FEAT-008 (branch 073, 2026-06-22). Parsing identico a Claude-Code, associazione progetto via cwd/gitRoot, privacy offline (niente cloud). 1039 test, Constitution 12/12.
- 📋 **Adapter futuri** (e.g. LangSmith, BedRock, Cline): slot nel composition root, no core changes.

---

## Pagine collegate

- [[memoria-conversazioni]] — concetto (il tier episodico, perché).
- [[feat-001-memoria-cattura-archiviazione]] — record della feature (adapter Claude-Code + store).
- [[feat-008-cattura-copilot-cli]] — record della feature (adapter Copilot CLI, multi-assistente).
- [[copilot-cli-session-storage]] — ricognizione tecnica storage Copilot CLI.
- [[scrub-segreti-in-contenuto]] — tecnica di scrub estesa.
- [[ports-adapters]] — pattern analogo per i retriever.
- [[thin-consumer]] — composizione e factory pattern.
