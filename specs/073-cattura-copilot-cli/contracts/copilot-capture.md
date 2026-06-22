# Contract — `memory.capture.copilot/1` (FEAT-008)

**Branch**: `073-cattura-copilot-cli` · **Data**: 2026-06-22

Contratto del **secondo adapter di cattura transcript** (GitHub Copilot CLI) dietro la porta esistente
`TranscriptCaptureAdapter`. Vehicle = CLI `sertor-rag memory archive` / hook `SessionEnd` (Principio XI).
Tutto **gated** da `memory_enabled` (`SERTOR_MEMORY`); a leva spenta l'adapter non è costruito.

## Porta (riusata, INVARIATA): `TranscriptCaptureAdapter`

```
kind: str                                   # "copilot-cli"
list_sessions() -> list[SessionRef]
read_session(ref: SessionRef) -> TranscriptContent
```

## Componente: `CopilotCliCaptureAdapter` (adapters/capture/copilot_cli.py)

### `list_sessions() -> list[SessionRef]`
- Enumera le **sottocartelle UUID** sotto `copilot_session_dir`
  (default `~/.copilot/session-state`, override `SERTOR_MEMORY_COPILOT_SESSION_DIR`).
- Per ciascuna sottocartella apre `<uuid>/events.jsonl`, estrae cwd/gitRoot dal **primo** evento
  `session.start`, e **include** la sessione SOLO se `cwd` **o** `gitRoot` è antenato-o-uguale al
  progetto corrente (`project_id = str(Path.cwd())`, path-containment normalizzato — DA-CM-4).
- `session_key` = nome cartella **UUID** (id stabile → idempotenza, REQ-005); `source_path` = path
  assoluto di `events.jsonl`; `project_id` = quello iniettato dal composition.
- **Degradazione non-fatale (REQ-018):**
  - `copilot_session_dir` assente → `[]` + warning `memory_capture_source_absent` (NON errore).
  - sottocartella senza `events.jsonl` o illeggibile → **skip** (la seconda con warning
    `memory_capture_unreadable`).
  - sessione senza `session.start` leggibile / senza cwd-gitRoot / nessun match progetto → **skip** +
    warning `memory_capture_session_unassociated` (nessuna misattribuzione — REQ-010, DA-CM-2).

### `read_session(ref: SessionRef) -> TranscriptContent`
- Legge `events.jsonl` **riga per riga** (best-effort, `errors="replace"`); produce `TranscriptContent`
  con i soli turni `user`/`assistant` in ordine.
- **Mapping evento → turno (REQ-006/008, DA-CM-1):**
  - `type == "user.message"` → `TranscriptTurn(index, "user", data.content, ts)`.
  - `type == "assistant.message"` → `TranscriptTurn(index, "assistant", data.content, ts)`;
    `data.toolRequests` **ignorati** (non sono turni).
  - ogni altro `type` (`system.message`, `tool.*`, `hook.*`, `session.*`, `permission.*`,
    `subagent.*`, `assistant.turn_*`) → **scartato** (no turno).
  - `data.content` vuoto/non-stringa → turno **saltato** (mai un turno vuoto).
  - `transformedContent` **mai** usato (è iniezione di system-reminder, non il dialogo).
  - `ts` = `timestamp` ISO-8601 dell'evento → epoch; assente/illeggibile → `None` (non-fatale).
- `captured_at` = mtime di `events.jsonl`.
- **Degradazione non-fatale (REQ-007/019, NFR-001):**
  - riga non-JSON → **skip** + warning `memory_capture_unparsable_line`, prosegue.
  - `OSError` in lettura → warning `memory_capture_unreadable` + `turns=()`.
  - formato inatteso (evento privo dei campi attesi) → l'evento non produce turno; **mai crash**.

## Vehicle CLI / hook (INVARIATI — nessun nuovo artefatto host)

### `sertor-rag memory archive`
- Con `SERTOR_MEMORY=true` e `SERTOR_MEMORY_ADAPTER=copilot-cli`, il comando esistente usa il nuovo
  adapter come sorgente: discovery → read → scrub (FEAT-001) → upsert (idempotente). Nessun cambiamento
  alla CLI: la selezione avviene in `build_capture_adapter` (REQ-001).
- `SERTOR_MEMORY_ADAPTER` con valore ignoto → `ConfigError` azionabile (exit 1) che nomina
  `claude-code, copilot-cli` (REQ-002).
- `SERTOR_MEMORY=false` → factory `None` → no-op (nessun file Copilot aperto, REQ-013).

### Hook `SessionEnd` (già depositato da FEAT-009)
- Su un ospite Copilot con memoria attiva e adapter Copilot, l'hook (che invoca `memory archive`)
  **cattura effettivamente** le sessioni — cessa di essere inerte (REQ-020, US7). Nessun nuovo artefatto
  è introdotto: l'hook esistente diventa funzionante perché ora ha una sorgente.

## Invarianti

- **Additività a leva spenta** (RNF-003, SC-011): `SERTOR_MEMORY=false` → nessun adapter costruito,
  nessun import del path Copilot, nessun file letto; costo/comportamento identici a oggi.
- **Default invariato** (FR-003, SC-010): senza selezione esplicita l'adapter resta `claude-code`; il
  ramo Claude di `build_capture_adapter` è invariato (non-regressione).
- **Host-specificità confinata** (REQ-016, SC-003): tutta la conoscenza Copilot (percorsi, formato
  eventi, associazione progetto) vive SOLO nell'adapter; tier a valle invariato.
- **Parità di tier** (REQ-017, SC-002): le sessioni Copilot sono archiviate, full-text (FEAT-002),
  semantica (FEAT-004) e distillabili (FEAT-003) alla pari di Claude, senza modifiche a quei componenti.
- **Local-first / no rete** (REQ-014, NFR-002): solo file locali Copilot; mai cloud-sync, mai
  `session-store.db`; zero rete.
- **Idempotenza ereditata** (REQ-011, FR-012): `session_key` UUID stabile + `INSERT OR IGNORE` del tier
  → nessun duplicato.
- **Scrub ereditato non bypassabile** (REQ-012): il testo passa per lo scrub di `MemoryArchiveService`;
  l'adapter produce contenuto pre-scrub e non lo aggira.
- **Best-effort / non-fatale** (NFR-001): nessuna eccezione non gestita su formato inatteso/parziale;
  guasto = warning, mai crash (parità con l'adapter Claude).
- **Stdlib-only** (RNF-7): nessuna nuova dipendenza di terze parti.
- **Vehicle** (Principio XI, RNF-8): cattura esercitata via CLI/hook, mai importando il core
  (eccezione: i test).
