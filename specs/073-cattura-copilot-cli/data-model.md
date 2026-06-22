# Phase 1 — Data Model: Cattura memoria su GitHub Copilot CLI (FEAT-008)

**Branch**: `073-cattura-copilot-cli` · **Data**: 2026-06-22

Cambiamento **additivo**: **nessuna nuova entità di dominio**, **nessuna nuova porta**. Si riusano le
entità della memoria (`SessionRef`, `TranscriptTurn`, `TranscriptContent`) e la porta esistente
`TranscriptCaptureAdapter` (8ª porta). Le uniche aggiunte sono: un **nuovo adapter concreto**, un
**campo Settings** (override percorso), un **valore in più** nel selettore d'adapter, e un **ramo di
dispatch** nel composition. Il tier a valle (archivio, full-text, semantica, distillazione) è
**invariato** (REQ-016/017, RNF-005).

## Entità di dominio riusate (INVARIATE — `domain/memory.py`)

```
SessionRef(session_key, project_id, source_path)   # prodotta da list_sessions
TranscriptTurn(index, role, text, ts)              # role ∈ {user, assistant}; ts: float | None
TranscriptContent(session_key, project_id, adapter_kind, captured_at, turns)
```

L'adapter Copilot le popola **esattamente** come l'adapter Claude:
- `session_key` = nome cartella **UUID** della sessione Copilot (id di sessione stabile → idempotenza,
  REQ-005). NON è un path di progetto.
- `project_id` = `str(Path.cwd())` (fornito dal composition, host-agnostico — Principio X).
- `source_path` = path assoluto di `<uuid>/events.jsonl` (opaco al servizio).
- `adapter_kind` = `"copilot-cli"` (→ colonna `sessions.adapter_kind` dell'archivio, già esistente).
- `captured_at` = mtime di `events.jsonl`.
- `turns` = solo i turni `user`/`assistant`, in ordine (DA-CM-1).

## Componente nuovo (adapter concreto, NO nuova porta)

`CopilotCliCaptureAdapter` in `src/sertor_core/adapters/capture/copilot_cli.py` — implementa la porta
`TranscriptCaptureAdapter` (structural typing, nessuna ereditarietà), `kind = "copilot-cli"`,
**stdlib-only** (`json`/`logging`/`os`/`datetime`/`pathlib`), best-effort non-fatale. Rispecchia la
forma di `claude_code.py`.

```
CopilotCliCaptureAdapter
  kind = "copilot-cli"
  __init__(session_dir: Path | str, project_id: str)
      # session_dir = copilot_session_dir (default ~/.copilot/session-state, override-abile)

  list_sessions() -> list[SessionRef]
      # enumera le sottocartelle UUID sotto session_dir; per ciascuna apre <uuid>/events.jsonl,
      # estrae cwd/gitRoot dal primo session.start, include SOLO se _paths_match(project_id, cwd, gitRoot).
      # dir assente → [] + warning memory_capture_source_absent.
      # sottocartella senza events.jsonl / illeggibile → skip (+ warning memory_capture_unreadable).
      # progetto indeterminabile / nessun match → skip (+ warning memory_capture_session_unassociated).

  read_session(ref: SessionRef) -> TranscriptContent
      # legge events.jsonl riga-per-riga (best-effort), mappa user.message/assistant.message → turni,
      # scarta il resto; captured_at = mtime(events.jsonl). Riga non-JSON → skip+warning. OSError → turns=().
```

**Helper puri confinati nel modulo (host-specific vocabulary):**

| Helper | Firma | Ruolo |
|---|---|---|
| `_session_context` | `(events_path: Path) -> tuple[str | None, str | None]` | trova il primo `session.start`, ritorna `(cwd, gitRoot)` o `(None, None)` |
| `_paths_match` | `(project_id: str, cwd: str | None, git_root: str | None) -> bool` | True se cwd **o** gitRoot è antenato-o-uguale al progetto (normalizzato, case-insensitive) — DA-CM-4 |
| `_turn_from_event` | `(event: dict, index: int) -> TranscriptTurn | None` | `user.message`/`assistant.message` → turno (testo = `data.content`); altro → None — DA-CM-1 |
| `_parse_line` | `(line, session_key, lineno) -> dict | None` | una riga JSONL → dict, o None (vuota silente, non-JSON con warning) — parità Claude |
| `_parse_timestamp` | `(raw: object) -> float | None` | ISO-8601 → epoch, None se assente/illeggibile — parità Claude |

`_TURN_EVENT_ROLES = {"user.message": "user", "assistant.message": "assistant"}` confina il mapping
evento→ruolo (gli altri `type` non sono nel dict → scartati, REQ-008).

## Manopole (Settings — UNICA fonte di default, Principio VIII)

| Campo | Env | Default | Priorità | Nota |
|-------|-----|---------|----------|------|
| `memory_adapter` (esistente) | `SERTOR_MEMORY_ADAPTER` | `"claude-code"` | — | + valore ammesso `"copilot-cli"` (REQ-001); default invariato (FR-003) |
| `copilot_session_dir` (**nuovo**) | `SERTOR_MEMORY_COPILOT_SESSION_DIR` | `~/.copilot/session-state` | Should | override sorgente (REQ-004), mirror di `claude_projects_dir` (DA-CM-3) |

Nessuna nuova manopola di gate: si riusa `memory_enabled` (`SERTOR_MEMORY`). Provider/store **non**
intervengono nella cattura (la cattura non embedda).

## Selettore d'adapter (composition)

```
_VALID_MEMORY_ADAPTERS = ("claude-code", "copilot-cli")   # + "copilot-cli" (REQ-001)

build_capture_adapter(settings):
    if settings.memory_adapter not in _VALID_MEMORY_ADAPTERS:
        raise ConfigError(... allowed: claude-code, copilot-cli, key="SERTOR_MEMORY_ADAPTER")  # REQ-002
    project_id = str(Path.cwd())
    if settings.memory_adapter == "claude-code":
        # ramo esistente (encode_project_path + claude_projects_dir) — INVARIATO (FR-003, non-regressione)
        ...
    # settings.memory_adapter == "copilot-cli":
    from sertor_core.adapters.capture.copilot_cli import CopilotCliCaptureAdapter  # LAZY (RNF-3)
    return CopilotCliCaptureAdapter(settings.copilot_session_dir, project_id=project_id)
```

- Import **lazy** del nuovo adapter (gira solo a leva accesa e adapter selezionato → RNF-3).
- Il ramo `claude-code` resta **byte-identico** nel comportamento (default invariato, SC-010).
- Valore ignoto → stesso `ConfigError` azionabile di oggi, ora con due valori nell'elenco (REQ-002).

## Identità & idempotenza (REQ-005/011)

- `session_key` = UUID cartella → **stabile**: ri-eseguire `list_sessions`/`read_session` sulla stessa
  sessione produce lo stesso `session_key`. L'archiviazione (`MemoryArchive`, `INSERT OR IGNORE`) è
  **idempotente** per costruzione sul tier (REQ-011/FR-012) → nessun duplicato, **senza** che l'adapter
  faccia nulla di nuovo (idempotenza **ereditata**).

## Eventi di osservabilità (metrics-only, parità Claude)

| Evento | Quando | Campi (mai testo transcript) |
|---|---|---|
| `memory_capture_source_absent` | dir Copilot assente | `adapter_kind`, `source` (path) |
| `memory_capture_unreadable` | `events.jsonl` illeggibile | `session_key`, `reason` (tipo eccezione) |
| `memory_capture_unparsable_line` | riga JSONL non valida | `session_key`, `line` (numero) |
| `memory_capture_session_unassociated` (**nuovo**) | progetto indeterminabile → skip | `session_key`, `adapter_kind` |

## Confini (cosa NON cambia)

- `domain/memory.py`, `domain/ports.py` (porta `TranscriptCaptureAdapter`): **invariati**.
- `adapters/capture/claude_code.py`: **invariato**.
- `services/memory_archive.py`, `services/episodic_search.py`, `services/memory_semantic.py`,
  distillazione (FEAT-003), `MemoryArchive`: **invariati** (REQ-017, RNF-005). Le loro suite restano
  verdi senza tocchi (SC-003).
- Nessuna nuova dipendenza di terze parti (RNF-7).
