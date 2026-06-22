# Phase 0 — Research: Cattura memoria su GitHub Copilot CLI (FEAT-008)

**Branch**: `073-cattura-copilot-cli` · **Data**: 2026-06-22 · **Epica**: memoria-conversazioni

> Chiude le forche residue di design (DA-CM-1..4 della spec) ancorando ogni decisione al codice reale
> (verifica via MCP `sertor-rag`, nessun errore tool) e alla **ricognizione empirica su sessioni Copilot
> CLI 1.0.63 reali** (2026-06-22). Le decisioni di scope già fissate (sorgente = `events.jsonl`; solo
> dialogo nei turni; associazione via cwd/gitRoot di `session.start`; nome adapter `copilot-cli`; sede
> legacy ignorata; cloud-sync sola documentazione) **non** si riaprono: qui si chiude il *come* di
> dettaglio.

## Ancoraggio verificato (dato di partenza, non da progettare)

- **Porta di cattura** = `TranscriptCaptureAdapter` (8ª porta, `domain/ports.py#31`,
  `@runtime_checkable Protocol`): `list_sessions() -> list[SessionRef]`,
  `read_session(ref) -> TranscriptContent`, attributo `kind`. È host-agnostica: separa il *cosa*
  (elencare sessioni, leggerne il contenuto come turni) dal *come* host-specifico. Claude è la prima
  implementazione; il nuovo adapter è la **seconda**, dietro la stessa porta (nessuna nuova porta).
- **Entità di dominio** (`domain/memory.py`, frozen dataclass, niente SDK — Principio I):
  - `SessionRef(session_key, project_id, source_path)` — riferimento leggero prodotto da
    `list_sessions`, NON carica il contenuto.
  - `TranscriptTurn(index, role, text, ts)` — turno (`role ∈ {user, assistant}`, `ts: float | None`).
  - `TranscriptContent(session_key, project_id, adapter_kind, captured_at, turns)` — contenuto
    strutturato pre-scrub prodotto da `read_session`.
  Tutte e tre **riusate invariate** dal nuovo adapter (REQ-016, A-007).
- **Adapter di riferimento** = `ClaudeCodeCaptureAdapter`
  (`src/sertor_core/adapters/capture/claude_code.py`, `kind="claude-code"`): stdlib-only
  (`json`/`logging`/`datetime`/`pathlib`), best-effort non-fatale. Pattern da rispecchiare:
  - `list_sessions`: dir assente → `[]` + warning `memory_capture_source_absent` (mai errore);
  - `read_session`: `path.read_text(errors="replace").splitlines()` → parsing riga-per-riga;
    `OSError` → warning `memory_capture_unreadable` + `[]`; riga non-JSON → warning
    `memory_capture_unparsable_line` + skip; `captured_at` = mtime del file sorgente;
    `_parse_timestamp` ISO-8601 → epoch, `None` se assente/illeggibile (mai errore).
- **Selezione** = `composition.py#build_capture_adapter` (riga 399): oggi
  `_VALID_MEMORY_ADAPTERS = ("claude-code",)` (riga 29), valore ignoto → `ConfigError` azionabile che
  nomina i valori ammessi (`key="SERTOR_MEMORY_ADAPTER"`); import LAZY dell'adapter (gira solo a leva
  accesa). `project_id = str(Path.cwd())`.
- **Manopole memoria in `Settings`** (`config/settings.py`): `memory_enabled` (`SERTOR_MEMORY`, default
  `False`), `memory_adapter` (`SERTOR_MEMORY_ADAPTER`, default `"claude-code"`, riga 135),
  `claude_projects_dir` (default `~/.claude/projects`, override env `SERTOR_MEMORY_CLAUDE_PROJECTS_DIR`,
  righe 152/328). **Il nome della env override di Claude è `SERTOR_MEMORY_CLAUDE_PROJECTS_DIR`** — il
  gemello Copilot ne segue la forma (DA-CM-3).
- **Gate privacy**: `build_capture_adapter`/`build_memory_archiver` ritornano logica costruita solo a
  `SERTOR_MEMORY=true`; a leva spenta nessun adapter è costruito, nessun file aperto (RNF-3).
- **Ricognizione empirica (Copilot CLI 1.0.63, 2026-06-22)** — schema di `events.jsonl` verificato su
  sessioni reali:
  - `{"type":"session.start","data":{"context":{"cwd":"...","gitRoot":"...","branch":"..."}},...}` —
    di norma **prima riga**; porta cwd/gitRoot del progetto in JSON puro (stdlib, niente YAML/db).
  - `{"type":"user.message","data":{"content":"<testo>","transformedContent":"...",...},"id":...,"timestamp":"ISO"}`
    — turno role=user, testo = `data.content` (NON `transformedContent`, che inietta system-reminder).
  - `{"type":"assistant.message","data":{"content":"<testo>","toolRequests":[...],"model":...},...}` —
    turno role=assistant, testo = `data.content`; i `toolRequests` **non** sono turni (REQ-008).
  - Scartati: `system.message`, `tool.execution_start/complete`, `hook.start/end`,
    `assistant.turn_start/turn_end`, `session.start/model_change/info/shutdown`, `permission.*`,
    `subagent.selected`. `vscode.metadata.json.origin = "other"` → inutile, scartato.

## Decisioni di design

### DA-CM-1 (residuo) — Ricomposizione del testo del turno → **`data.content` è già testo completo**

- **Decisione:** il testo del turno è **`data.content`** così com'è, per `user.message` e
  `assistant.message`. **Nessuna ricomposizione da delta/streaming**: nel `events.jsonl` persistito a
  fine sessione ogni `*.message` porta il contenuto **completo** del turno (lo streaming è un dettaglio
  di rendering a runtime, non si materializza come righe-delta nel file). Verificato su eventi reali
  (2026-06-22): un turno = un evento `*.message` con `data.content` intero.
- **Razionale:** parità con l'adapter Claude (`_extract_text` concatena blocchi testuali; qui il testo
  è già una stringa singola in `data.content`). `transformedContent` è **scartato** di proposito:
  contiene l'iniezione di system-reminder/contesto, non il prompt umano — includerlo sporcherebbe
  l'archivio e la ricerca (R-CM-4). Se in futuro un evento portasse `data.content` non-stringa
  (es. lista di blocchi), l'estrazione degrada a stringa vuota → turno saltato (non-fatale, FR-008).
- **Mapping evento → turno (host-specifico, confinato nell'adapter):**
  | `type` evento | ruolo turno | testo | note |
  |---|---|---|---|
  | `user.message` | `user` | `data.content` | `transformedContent` ignorato |
  | `assistant.message` | `assistant` | `data.content` | `toolRequests` ignorati (non turni) |
  | ogni altro `type` | — | — | scartato (no turno) |
  - `index` del turno = ordinale progressivo nei soli turni estratti (come Claude: `index=len(turns)`).
  - `ts` del turno = campo `timestamp` (ISO-8601) dell'evento; assente/illeggibile → `None`
    (non-fatale, parità con Claude).
  - `data.content` vuoto/whitespace o non-stringa → turno **saltato** (come Claude: testo vuoto → no
    turno), mai un turno vuoto nell'archivio.

### DA-CM-2 (residuo) — Politica per progetto indeterminabile → **SKIP (silenzioso-con-warning)**

- **Decisione:** una sessione il cui progetto **non è determinabile** — manca `session.start`, oppure
  `data.context` non porta cwd né gitRoot leggibili — **non combacia** e viene **esclusa** da
  `list_sessions` (skip), con un warning `memory_capture_session_unassociated`. **Nessun marcatore
  esplicito** «unknown-project», **nessuna misattribuzione**.
- **Razionale:** la decisione cade naturalmente dal filtro per cwd/gitRoot (FR-010/011): se non c'è una
  cwd/gitRoot da confrontare, il match è `False` → la sessione non è elencata per il progetto corrente.
  Un marcatore «unknown-project» introdurrebbe un secondo `project_id` artificiale nell'archivio
  per-progetto, sporcandolo, senza un consumatore reale oggi (YAGNI, Principio III). La regola d'oro
  («mai misattribuire in silenzio», R-CM-3) è rispettata: la sessione è **esclusa**, non attribuita al
  progetto sbagliato. Il warning rende il guasto **visibile** (Principio XII — degradazione che segnala,
  non silenzio).
- **Conseguenza:** una sessione di Copilot avviata fuori da qualsiasi repo (o con metadata corrotta)
  semplicemente non entra nell'archivio di nessun progetto Sertor. È il comportamento voluto.

### DA-CM-3 — Nome della manopola di override del percorso sorgente → **`SERTOR_MEMORY_COPILOT_SESSION_DIR`**

- **Decisione:** nuovo campo `Settings.copilot_session_dir: Path`, default
  `~/.copilot/session-state`, da env **`SERTOR_MEMORY_COPILOT_SESSION_DIR`** (Should, REQ-004). Mirror
  **esatto** della forma esistente per Claude (`claude_projects_dir` ←
  `SERTOR_MEMORY_CLAUDE_PROJECTS_DIR`): stesso prefisso `SERTOR_MEMORY_<ASSISTANT>_<ROLE>_DIR`,
  stesso `default_factory` su `Path.home()`.
- **Razionale:** coerenza di naming (l'override Claude è `SERTOR_MEMORY_CLAUDE_PROJECTS_DIR`, **non**
  `SERTOR_CLAUDE_PROJECTS_DIR`) e host-agnosticità/testabilità (RNF-4): i test puntano una fixture
  senza Copilot installato. La sede sorgente è una sottocartella della struttura host-specifica, perciò
  il campo vive in `Settings` (Principio VIII, default solo qui) e l'adapter lo riceve dal composition.

### DA-CM-4 — Forma del filtro cwd/gitRoot → **path-containment normalizzato (cwd/gitRoot è antenato o uguale al progetto)**

- **Decisione:** una sessione Copilot appartiene al progetto corrente
  (`project_id = str(Path.cwd())`) se **almeno uno** tra il `cwd` e il `gitRoot` registrati nel suo
  `session.start` **contiene** (path-containment) il progetto corrente — cioè il progetto è uguale a, o
  un discendente di, quel path. Confronto su path **normalizzati**: `Path.resolve()` +
  case-insensitive su Windows (`os.path.normcase`), separatori normalizzati. Helper puro
  `_paths_match(project_id, cwd, git_root) -> bool` confinato nell'adapter.
- **Razionale (perché containment e non match esatto):** un agente Copilot avviato in una **sottocartella**
  del repo (es. `C:\...\Sertor\packages\sertor`) ha `cwd` = la sottocartella ma `gitRoot` = la radice
  del repo. Se Sertor è installato sulla radice (`project_id = C:\...\Sertor`), un match esatto su `cwd`
  perderebbe quella sessione; il `gitRoot` invece **contiene** il progetto → match. Specularmente, una
  sessione avviata nella radice mentre il progetto è una sottocartella non deve essere catturata: per
  questo il test è «cwd/gitRoot **è antenato o uguale al progetto**», non il viceversa. La normalizzazione
  robusta (resolve + case-insensitive) è obbligatoria su Windows (drive-letter case, `/` vs `\`,
  `8.3`/symlink) per non perdere match per differenze cosmetiche.
- **Robustezza:** se il path normalizzato non è risolvibile (es. su una macchina diversa da quella che
  ha generato la sessione, dove il path non esiste), si confrontano i path **lessicalmente** normalizzati
  (`normcase` + `PurePath`) senza toccare il filesystem, così il match non dipende dall'esistenza fisica
  del path catturato (testabilità offline, RNF-4).

## Discovery & identità (REQ-003/005/006)

- `list_sessions()`: enumera le **sottocartelle UUID** sotto `copilot_session_dir`; per ciascuna apre
  `<uuid>/events.jsonl`, cerca il **primo** `session.start` per estrarne cwd/gitRoot; include la
  sessione **solo** se `_paths_match` (DA-CM-4). `session_key` = **nome cartella UUID** (id di sessione
  stabile → idempotenza, REQ-005); `source_path` = path assoluto di `events.jsonl`.
- Dir assente → `[]` + warning `memory_capture_source_absent` (REQ-018, parità Claude).
- Sottocartella senza `events.jsonl`, illeggibile, o senza match progetto → **skip** (non elencata); la
  prima con warning `memory_capture_unreadable`, l'ultima con `memory_capture_session_unassociated`.
- `read_session(ref)`: legge `events.jsonl` riga-per-riga (best-effort), mappa `user.message`/
  `assistant.message` → turni (DA-CM-1), scarta il resto; `captured_at` = mtime di `events.jsonl`.
  Riga non-JSON → warning `memory_capture_unparsable_line` + skip; `OSError` → warning
  `memory_capture_unreadable` + `turns=()`. Mai fatale (REQ-007, NFR-001).

## Privacy & local-first (REQ-013/014/015)

- L'adapter legge **solo** `~/.copilot/session-state/**` (locale); **nessun** accesso a
  `~/.copilot/session-store.db` né al cloud-sync GitHub; **zero rete** (NFR-002). Verificabile con una
  fixture (monitor di rete a zero) senza Copilot installato.
- **Cloud-sync = sola documentazione** (REQ-015, DA-CM-6): Copilot può sincronizzare le sessioni sul
  cloud GitHub *di default* (comportamento a monte, fuori dal controllo di Sertor); il quickstart/doc
  lo dichiara esplicitamente, **nessun avviso a runtime**.
- **Scrub ereditato** (REQ-012): il testo dei turni è scrubbed dal percorso d'archiviazione esistente
  (`MemoryArchiveService`, FEAT-001); l'adapter produce contenuto **pre-scrub** e non lo aggira.

## Riuso vs nuovo componente (REQ-016, SC-002/003)

- **Nessuna nuova porta, nessun nuovo motore, nessun tocco al tier a valle.** Si aggiunge **un solo**
  componente: `CopilotCliCaptureAdapter` dietro la porta esistente. Selezione: un valore in più
  (`"copilot-cli"`) in `_VALID_MEMORY_ADAPTERS` + dispatch su `settings.memory_adapter` in
  `build_capture_adapter` (import lazy del nuovo adapter). Archivio, full-text (FEAT-002), semantica
  (FEAT-004), distillazione (FEAT-003) restano **invariati** e operano sui transcript Copilot per
  costruzione (host-agnostici nel corpo).

## Osservabilità (Principio IX, parità Claude)

L'adapter riusa gli **stessi eventi metrics-only** dell'adapter Claude (mai testo di transcript):
- `memory_capture_source_absent` (dir Copilot assente);
- `memory_capture_unreadable` (`events.jsonl` illeggibile);
- `memory_capture_unparsable_line` (riga JSONL non valida);
- **nuovo** `memory_capture_session_unassociated` (sessione senza progetto determinabile → skip).
Tutti portano `adapter_kind="copilot-cli"`; nessun contenuto di conversazione.

## Resilienza al formato (R-CM-1, NFR-001/006)

`events.jsonl` è un dettaglio **interno** di Copilot CLI, non un contratto pubblico. Mitigazione
(parità con l'adapter Claude): parsing best-effort/non-fatale (riga/evento inatteso → skip+warning, mai
crash, FR-020); la **versione verificata** (Copilot CLI 1.0.63, 2026-06-22) è dichiarata in `quickstart.md`
e nel docstring del modulo (NFR-006); copertura test su fixture (NFR-004). Un cambio di formato a monte
degrada a cattura best-effort/vuota con warning, non a un errore.

## Estensioni / debiti (promossi, non sepolti)

- **Distribuzione via installer** (DA-CM-7): cablare `SERTOR_MEMORY_ADAPTER=copilot-cli` (e l'override
  `SERTOR_MEMORY_COPILOT_SESSION_DIR`) nel template `.env` di `sertor install` su host Copilot →
  **debito di completamento, cross-ref FEAT-009** (owner di `sertor install`), già nel backlog
  d'epica. **Non** risolto qui: la feature non è *done* finché un ospite Copilot non riceve il valore
  adapter per il percorso d'installazione.
- **Sede legacy `~/.copilot/history-session-state/`** → **Could** (DA-CM-4 della spec / requisiti
  d'epica), fuori MVP; non letta.
- **Altri assistenti** (Codex, ecc.) → estendibili con lo stesso pattern (nuovo adapter + nuovo valore
  in `_VALID_MEMORY_ADAPTERS`); fuori da questa feature.
- **Fonte alternativa `session.db`** → non letta (lo stream `events.jsonl` è la fonte di verità, A-001).
