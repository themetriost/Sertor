---
title: FEAT-001 Memoria — Cattura & archiviazione locale dei transcript
type: experiment
tags: [FEAT-001, memoria-conversazioni, cattura, archive, episodico, hermes, speckit]
created: 2026-06-14
updated: 2026-06-14
sources: ["requirements/memoria-conversazioni/cattura-archiviazione/requirements.md", "specs/031-cattura-archiviazione/spec.md", "src/sertor_core/domain/memory.py", "src/sertor_core/adapters/capture/", "src/sertor_core/adapters/memory/", "src/sertor_core/services/memory_archive.py", "src/sertor_core/observability/scrub.py"]
---

# FEAT-001 — Cattura & archiviazione locale dei transcript

**Merger**: PR #45 (commit c1fa95d), 2026-06-14  
**Stato**: ✅ In produzione su master

## Cosa è stato costruito

**Il tier grezzo episodico della memoria conversazioni**: cattura le conversazioni dell'agente con il progetto ospite e le conserva in un archivio locale SQLite (`<index_dir>/memory.sqlite`, gitignored, idempotente, per-progetto), preparando il terreno per la ricerca episodica (FEAT-002) e la distillazione futura (FEAT-003).

### Architettura — 8ª porta + adapter + store

- **8ª porta `TranscriptCaptureAdapter`** (`domain/ports.py`): astrazione host-agnostica che separa il *cosa* (elencare le sessioni, leggerne il contenuto a grana di turni) dal *come* host-specifico. Primo adattatore: Claude Code che legge i JSONL di sessione da `~/.claude/projects/<encoded>/<session-id>.jsonl`. Selezionato via configurazione, nessun ramo condizionale nel core. Structural typing (Protocol) → mockabile senza ereditarietà.

- **Adapter Claude-Code** (`adapters/capture/claude_code.py`, 165 righe): legge i file JSONL di sessione che Claude Code già persiste localmente. Parsing best-effort difensivo: linee non-JSON saltate con warning (mai fatale), encoding del path del progetto, chiave canonica dal nome del file.

- **Store concreto `MemoryArchive`** (`adapters/memory/archive.py`, 150 righe): SQLite locale gitignored (`<index_dir>/memory.sqlite`), due tabelle `sessions`/`turns` (granularità ibrida: unità archiviata = sessione intera per idempotenza, ma confini dei turni conservati come righe interrogabili per FEAT-002 senza ri-elaborare il grezzo). `INSERT OR IGNORE` idempotente, conservato (no rotazione), degrado non-fatale (warning + no-op).

- **Entità di dominio puro** (`domain/memory.py`, 63 righe): `SessionRef` (riferimento leggero), `TranscriptTurn` (grana del turno, pre-scrub), `TranscriptContent` (sessione grezzo pre-scrub), `ArchivedSession` (unità conservata post-scrub). Nessun import di SDK esterno (Principio I).

### Servizio di orchestrazione + scrub del contenuto

- **`MemoryArchiveService`** (`services/memory_archive.py`, 90 righe): orchestrazione list→read→scrub→upsert, idempotente, non-bloccante. Emette eventi `log_event` `memory_session_archived`/skip per osservabilità.

- **Funzione pura `scrub_text`** (`observability/scrub.py`, 67 righe): estende la redazione per-campo esistente (`observability/logging.py`) al **contenuto testuale libero** del transcript prima di persistere. Pattern: `sk-…` (OpenAI), `AKIA…` (AWS), `bearer `… (token), `KEY=VALUE` con hint di segreto (key/token/secret/password/authorization), header Authorization inline. Ripiego conservativo (redige il segmento intero se fallisce), configurabile via manopola, mai bypassabile.

### Configurazione e wiring

- **5 manopole in `Settings`**: `SERTOR_MEMORY` (default false = privacy-by-default); `SERTOR_MEMORY_ADAPTER` (default claude-code); `SERTOR_MEMORY_RETENTION_DAYS` (default nessuna scadenza, solo gancio — enforcement FEAT-006); `SERTOR_MEMORY_SCRUB_PATTERNS` (configurabile); `SERTOR_MEMORY_CLAUDE_PROJECTS_DIR` (default ~/.claude/projects, per testabilità).

- **Wiring in `composition.py`**: `build_capture_adapter`, `build_memory_archive`, `build_memory_archiver`, costruiti SOLO se `SERTOR_MEMORY=true` (import lazy, zero overhead a flag off).

## Qualità

- **Test**: 29/29 task completati; 488 test non-cloud verdi (7 nuovi file di test: adapter + memory store + service + privacy + scrub + composition + settings); ruff pulito.
- **Constitution Check**: ✅ PASS 10/10 senza deroghe.
- **Additivo**: nessuna modifica a contratti esistenti; stdlib-only nel corpo; dipendenze host-specifiche confinate nell'adapter (Principio X, host-agnosticità dimostrata con mock adapter in test).

## Specifiche conseguite

Tutti i 27 requisiti EARS + 8 NFR implementati e testati:

- **FR-001/002**: Privacy-by-default, zero overhead a flag off.
- **FR-003**: Lazy loading dell'adapter via composizione.
- **FR-004/005/006**: Porta astratta, selezione esclusivamente via config, source assente → warning + archivio invariato.
- **FR-007/008**: Adapter Claude-Code legge file senza modificarli, chiave canonica dal filename.
- **FR-009/010/011/012/013/014**: Archivio locale, per-progetto, gitignored, conservato, grana ibrida (sessione + turni).
- **FR-015/016**: Idempotenza silente via `INSERT OR IGNORE`.
- **FR-017/018/019/020**: Scrub pattern-based, ripiego conservativo, configurabile.
- **FR-023/024/025**: Osservabilità `memory_session_archived`/skip, degradazione non-fatale.

## Nodo centrale: host-agnosticità (Principio X)

La cattura è **host-specifica** per definizione (ogni assistente ha un modo diverso di persistere le sessioni). Ciò che è **generico** (archiviazione, scrub, idempotenza, retention hook) è nel core. La 8ª porta `TranscriptCaptureAdapter` + il pattern di adapter è il mecanismo di **disaccoppiamento**: il core non conosce Claude Code; Claude Code è un'implementazione swappabile. Valido per Multi-Assistente (FEAT-008): futuri adattatori (e.g. LangSmith, BedRock) non toccheranno il core.

## Prossimo

- **FEAT-002** (ricerca episodica full-text locale): consuma questo archivio per query FTS senza embedding.
- **FEAT-003** (distillazione): userà l'archivio come fonte grezza da cui estrarre conoscenza per il wiki.

---

## Pagine collegate

- [[memoria-conversazioni]] — concetto (l'episodico tier, perché, pattern Hermes)
- [[transcript-capture-adapter-e-storage]] — tech (le tre componenti: porta + adapter + store)
- [[scrub-segreti-in-contenuto]] — tech (scrub del contenuto, ridazione estesa)
- [[memoria-negli-agenti]] — explainer (non-tecnico)
- [[diary-vs-graph]] — memoria del wiki vs memoria episodica
- [[thin-consumer]] — pattern di composizione usato per il wiring
