# Contract — `TranscriptCaptureAdapter` (porta di cattura, host-agnostica)

**Feature**: 031 · **Tipo**: porta `Protocol` (`src/sertor_core/domain/ports.py`) · **ID contratto**: `memory.capture/1`

L'8ª porta del core. Astrae la *sorgente* host-specifica dei transcript. Claude Code è la prima
implementazione; altri assistenti sono adapter futuri (FEAT-008). Selezione **solo via config** (FR-005).

## Interfaccia

```python
@runtime_checkable
class TranscriptCaptureAdapter(Protocol):
    kind: str
    def list_sessions(self) -> list[SessionRef]: ...
    def read_session(self, ref: SessionRef) -> TranscriptContent: ...
```

## `kind: str`
- Identifica l'adapter (es. `"claude-code"`). Finisce in `sessions.adapter_kind` (FR-012) e negli eventi.

## `list_sessions() -> list[SessionRef]`
| Caso | Comportamento |
|---|---|
| Sorgente presente con N sessioni | Lista di N `SessionRef`, `session_key` = stem filename (FR-008) |
| Sorgente assente/vuota (dir inesistente) | `[]` + warning `memory_capture_source_absent`; **nessun errore** (FR-006) |
| Sola lettura | NON modifica né cancella i file della sorgente (FR-007) |

- Deterministico per uno stato dato della sorgente. Ordine non garantito (il servizio non vi dipende).

## `read_session(ref) -> TranscriptContent`
| Caso | Comportamento |
|---|---|
| Sessione leggibile | `TranscriptContent` con `turns` nell'ordine di emissione (FR-013) |
| Righe non parsabili | Skip + warning `memory_capture_unparsable_line` (numero riga); **mai fatale** (D3) |
| Evento non-turno (system/tool/…) | Ignorato (non genera turno) |
| Zero turni estraibili | `turns=()` (il servizio salta la sessione) |
| `timestamp` illeggibile | `ts=None` nel turno (non un errore) |

## Invarianti
- **Host-agnostico nel core**: il servizio e il dominio NON conoscono l'encoding del path, i nomi dei
  campi JSONL, i tipi di block. Tutta questa conoscenza vive **solo** nell'adapter concreto (Principio X).
- **Non-distruttivo**: la sorgente è di sola lettura (Principio VI).
- **Mockabile**: structural typing → un fake con gli stessi metodi è conforme senza ereditarietà (SC-005).

## Test del contratto (offline)
- Fake adapter A e B con la stessa interfaccia → il servizio si comporta in modo identico (SC-005).
- Adapter con sorgente assente → `[]`, archivio invariato (US3 scenario 3).
- Adapter con righe miste (valide + corrotte) → solo i turni validi, warning sui salti.
