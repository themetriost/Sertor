# Feature Specification: hook wiki SessionStart host-agnostico (E10-FEAT-029)

**Feature Branch**: `117-feat-029-wiki-hook-host-agnostic`

**Created**: 2026-07-22

**Status**: Implemented

**Input**: E10-FEAT-029 (epica `debito-tecnico`). BUG confermato (triage 2026-07-22 vs codice `ec9129c`):
l'hook `wiki-session-start.py` hardcoda i path invece di leggerli da `wiki.config.toml` → viola Principio X.
Requisiti EARS: `requirements/debito-tecnico/feat-029-wiki-hook-host-agnostic/requirements.md`.

## User Scenarios & Testing *(mandatory)*

L'hook host-facing `wiki-session-start` (installato da `sertor install wiki`) inietta a inizio sessione la
direttiva «carica il contesto del wiki». Oggi la compone con path **letterali** (`wiki/syntheses/roadmap.md`,
`wiki/index.md`, `wiki/log/...`): funziona sul dogfood solo perché la sua config coincide, ma un ospite con
`root`/tassonomia diversi riceve l'ordine di leggere path inesistenti; e un wiki appena creato apre con
letture fallite (la roadmap non esiste ancora).

### User Story 1 - Direttiva costruita dalla config, non da letterali (Priority: P1)

L'hook legge `root`/`index_file`/`log_dir` (+ l'opt-in `[ritual].exec_page`) da `wiki.config.toml` e
costruisce la direttiva coi path reali dell'ospite. Un ospite con `root="docs"` riceve `docs/...`, non
`wiki/...`.

**Why this priority**: è il bug (violazione Principio X). Senza, la capacità non è host-agnostica.

**Independent Test**: config con `root≠"wiki"` → la direttiva usa quel root; nessun letterale `wiki/`.

**Acceptance Scenarios**:
1. **Given** `wiki.config.toml` con `root="docs"`, **When** parte la sessione, **Then** la direttiva
   ordina di leggere `docs/index.md`, `docs/log/<partizione>` — nessun `wiki/` hardcoded.
2. **Given** l'ospite ha `[ritual].exec_page="syntheses/roadmap.md"` e il file esiste, **When** parte la
   sessione, **Then** la direttiva include la roadmap + «mostra l'executive summary tra i marker EXEC».

### User Story 2 - Nessuna lettura fallita su wiki nuovo / ospite generico (Priority: P1)

Un wiki appena inizializzato (o un ospite senza roadmap) non riceve l'ordine di leggere un file che non
esiste: la direttiva **degrada**, includendo solo i file presenti; senza `exec_page` non cita la roadmap.

**Why this priority**: evita l'ordine «Read <inesistente>» — il sintomo osservato su un wiki nuovo.

**Independent Test**: config presente ma senza index/log/roadmap → nessuna direttiva (o solo i file esistenti).

**Acceptance Scenarios**:
1. **Given** un wiki fresco (config, ma nessun index/log/roadmap), **When** parte la sessione, **Then**
   nessun ordine di lettura verso un path inesistente (direttiva vuota/omessa).
2. **Given** un ospite generico senza `exec_page`, **When** parte la sessione, **Then** la direttiva carica
   index + log ma **non** cita la roadmap/EXEC (concept dogfood-specifico).

### User Story 3 - Parità Copilot (Priority: P2)

Il prompt SessionStart Copilot (statico) non hardcoda più la roadmap: resta generico (index + log del wiki),
host-agnostico.

**Why this priority**: parità cross-assistente; il prompt statico non può leggere config a runtime, ma non
deve imporre una roadmap che un ospite non ha.

**Independent Test**: il prompt Copilot generato non contiene il letterale `syntheses/roadmap.md`.

### Edge Cases

- **Config assente/illeggibile:** l'hook non emette nulla (fail-safe, exit 0) — come `wiki-pending-check`.
- **`log_dir` non configurato (single-file):** il fallback punta al log single-file, non a `wiki/log/log.md`.
- **`exec_page` configurato ma file assente:** degrada (omette la roadmap), non ordina la lettura.

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: L'hook DEVE costruire la direttiva dai valori di `wiki.config.toml`, non da letterali.
- **FR-002**: La direttiva DEVE omettere ogni file assente (degradazione) invece di ordinarne la lettura.
- **FR-003**: Su un wiki fresco la direttiva non DEVE ordinare la lettura di un file non creato.
- **FR-004**: Il prompt Copilot SessionStart DEVE essere host-agnostico (niente letterale roadmap).
- **FR-005**: Il fallback log DEVE risolvere al layout della config (rotazione vs single-file).
- **FR-006**: L'hook DEVE restare stdlib-only, non-bloccante (exit 0), host-agnostico.
- **FR-007**: Una guardia DEVE asserire l'assenza di letterali `wiki/` nella direttiva quando il root differisce.

### Key Entities
- **`[ritual].exec_page`**: config **opt-in** — la pagina caricata per prima + di cui mostrare l'EXEC
  summary. Presente sul dogfood (`syntheses/roadmap.md`), assente su un ospite generico.

## Success Criteria *(mandatory)*
- **SC-001**: Con `root≠"wiki"`, la direttiva contiene solo path di quel root; zero letterali `wiki/`.
- **SC-002**: Su un wiki fresco (config senza contenuti), l'hook non ordina letture di file inesistenti.
- **SC-003**: Con `exec_page` configurato+presente, la direttiva include roadmap+EXEC (comportamento dogfood
  preservato — verificato LIVE).
- **SC-004**: Il prompt Copilot non contiene il letterale `syntheses/roadmap.md`.
- **SC-005**: L'hook resta non-bloccante (exit 0) in tutti gli scenari, config assente inclusa.

## Assumptions
- La config-location è `<host>/wiki/wiki.config.toml` (o `<host>/wiki.config.toml`); il campo `root` indica
  la dir dei contenuti — coerente con l'installer.
- `[ritual].exec_page` è opt-in: il dogfood lo aggiunge (per preservare la roadmap/EXEC); il template ospite
  non lo semina (un ospite generico non ha `syntheses/roadmap.md`).
- DA-1 sciolta = **degradazione** (no seed forzato in `structure.py`). DA-2 = **prompt Copilot generico**.
