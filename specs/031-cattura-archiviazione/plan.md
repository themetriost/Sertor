# Implementation Plan: Cattura & archiviazione locale dei transcript

**Branch**: `031-cattura-archiviazione` | **Date**: 2026-06-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/031-cattura-archiviazione/spec.md` (FEAT-001 dell'epica
«Memoria delle conversazioni», prima metà MVP). Fonte requisiti:
`requirements/memoria-conversazioni/cattura-archiviazione/requirements.md` (27 requisiti EARS).

## Summary

Aggiunge il **tier grezzo episodico** oggi mancante: cattura le conversazioni dell'agente con il
progetto ospite e le conserva in un archivio locale SQLite, persistente, conservato (non ruotato),
namespaced per progetto, gitignored. Privacy-by-default (spenta salvo opt-in); il contenuto è ripulito
dai segreti prima di persistere. La *ricerca* (FEAT-002), la distillazione (FEAT-003), il remember-this
(FEAT-005), l'enforcement retention (FEAT-006) e il multi-assistente (FEAT-008) sono **fuori ambito**.

**Approccio tecnico (da [research.md](./research.md)):** un'unica porta nuova `TranscriptCaptureAdapter`
(8ª porta `Protocol`) astrae la sorgente host-specifica; l'adapter Claude-Code legge i file `.jsonl` di
sessione best-effort. Lo store `MemoryArchive` è un componente concreto stdlib (SQLite, **senza** porta —
nessun secondo consumatore oggi), schema a due tabelle `sessions`+`turns` (**granularità ibrida**: unità
archiviata = sessione, ma confini turni preservati per l'indicizzazione per-turno di FEAT-002). Idempotenza
via stem-filename + `INSERT OR IGNORE`. Una funzione pura `scrub_text` estende la redazione per-campo
esistente al contenuto testuale libero. Il servizio `MemoryArchiveService` orchestra scoperta → lettura →
scrub → upsert; cablato in composition con tre `build_*` lazy, gated su `SERTOR_MEMORY` (flag-off = zero
import/file). Tutto additivo: porte/servizi esistenti invariati.

## Technical Context

**Language/Version**: Python >= 3.11 (`from __future__ import annotations`, `StrEnum`, `match`).

**Primary Dependencies**: **nessuna nuova**. Corpo del core: solo **stdlib** (`sqlite3`, `json`, `re`,
`hashlib`, `pathlib`, `datetime`). L'adapter Claude-Code legge file locali con la stdlib; nessuna
dipendenza host-specifica importata a flag off.

**Storage**: SQLite locale `<index_dir>/memory.sqlite` (gitignored), schema `sessions`+`turns`. Pattern
riusato da `SqliteObservabilityStore` ed `EmbeddingCache`.

**Testing**: `pytest` offline (`-m "not cloud"`): adapter mock + `tmp_path` per lo store, file JSONL
sintetici per il parser. F.I.R.S.T., nessuna rete, nessun Claude Code reale.

**Target Platform**: cross-platform (libreria). Il path della sorgente Claude Code è derivato dalla config
(host-agnostico), non assunto.

**Project Type**: single project — libreria `sertor-core` (`src/sertor_core/`).

**Performance Goals**: nessun obiettivo numerico imposto (Edge Case «transcript enorme»: la cattura non
deve fallire né bloccare; scrub proporzionato). Insert sincrono: bassa cardinalità (poche sessioni per
run), coerente con `SqliteObservabilityStore`.

**Constraints**: additivo (porte/servizi esistenti invariati); stdlib-only nel corpo; host-specifico SOLO
nell'adapter; default-off = nessun import/file; scrub mai bypassabile; non-distruttivo/idempotente;
testabile offline.

**Scale/Scope**: ~6 file nuovi (`domain/memory.py`, +1 porta in `domain/ports.py`, `observability/scrub.py`,
`adapters/capture/claude_code.py`, `adapters/memory/archive.py`, `services/memory_archive.py`), +4 manopole
in `Settings`, +3 `build_*` in `composition.py`.

## Constitution Check

*GATE: superato PRIMA della Phase 0 e RI-VALUTATO dopo la Phase 1. Costituzione v1.1.1 (10 principi).*

### Esito PRIMA della ricerca (Phase 0) — PASS 10/10

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** il corpo (dominio/servizio/store/scrub) non
  importa SDK di provider né la CLI. La cattura host-specifica sta dietro la porta `Protocol`
  `TranscriptCaptureAdapter`; il wiring è solo in `composition.py`. Esercitabile con adapter mock, senza
  cloud/CLI. **PASS**
- [x] **II — Boundary & local-first:** la sorgente dei transcript è dietro un'astrazione di Sertor (la
  porta); l'archivio è locale (SQLite), nessun cloud richiesto. Scelta dell'adapter via config. **PASS**
- [x] **III — YAGNI & unità piccole:** **una sola** porta nuova (la cattura, che varia davvero per
  ospite); lo store è concreto senza porta (nessun secondo consumatore oggi — come `EmbeddingCache`).
  `scrub_text` separata da `redact()` per SRP. Nessuna astrazione senza evidenza presente. **PASS**
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** errori di dominio dove serve; le **assenze legittime**
  (sorgente assente, riga illeggibile, store guasto) sono **warning espliciti + continuazione**, non
  `None` silenziosi (sono esiti loggati, non nulli muti — distinzione del Principio IV già codificata in
  `errors.py` e `store.py`). Nessuno stato parziale: l'upsert sessione+turni è in una transazione. **PASS**
- [x] **V — Testabilità & misure:** tutto offline con mock (adapter, `tmp_path`); `scrub_text` pura;
  parser su JSONL sintetici. Niente retrieval qui (la misura hit@k/MRR è di FEAT-002, fuori ambito);
  i SC sono criteri verificabili (conteggi, 0 segreti, ≥2 adapter). **PASS**
- [x] **VI — Idempotenza & non-distruttività:** chiave canonica = stem-filename; `INSERT OR IGNORE`;
  ri-archiviazione → skip, record invariato; nessuna rotazione/cancellazione (conservato). La sorgente è
  letta in sola lettura. Install≠run: la cattura non parte da sola (è invocazione esplicita). **PASS**
- [x] **VII — Leggibilità:** naming di dominio (`archive`, `capture`, `scrub`, `session`, `turn`); funzioni
  piccole, guard clause / early return, nessun SESE forzato (allineato al chiarimento v1.1.1). **PASS**
- [x] **VIII — Configurabilità centralizzata:** 4 manopole nuove con default **solo** in `Settings`
  (`SERTOR_MEMORY`, `SERTOR_MEMORY_ADAPTER`, `SERTOR_MEMORY_RETENTION_DAYS`,
  `SERTOR_MEMORY_SCRUB_PATTERNS`); nessun default hardcoded nei componenti. **PASS**
- [x] **IX — Osservabilità:** ogni operazione emette `log_event` strutturato (archived/skipped/
  source_absent/unparsable_line/scrub_fallback/archive_unavailable); **nessun segreto nei log** (FR-027:
  eventi senza `content` grezzo, solo `content_size`; `redact()` per-campo come rete). **PASS**
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** la conoscenza host-specifica (encoding path, campi JSONL,
  tipi di block) vive **solo** nell'adapter Claude-Code; servizio e dominio la ignorano. Selezione adapter
  via config, nessun ramo sull'identità dell'host nel servizio (SC-005). Il `project_id`/path sorgente
  sono **forniti** (config/adapter), non presunti. Dogfooding (Sertor su sé stesso) non giustifica
  deroghe. **PASS**

### Esito DOPO il design (Phase 1) — PASS 10/10 (invariato)

Il design (entità pure in `domain/memory.py`, porta in `domain/ports.py`, store concreto, `scrub_text`
pura, servizio orchestratore, 3 `build_*` lazy gated) **conferma** tutti i gate. In particolare:
- **I/X**: i tre contratti ([transcript-capture-port](./contracts/transcript-capture-port.md),
  [memory-archive-store](./contracts/memory-archive-store.md),
  [memory-archive-service](./contracts/memory-archive-service.md)) tengono l'host-specifico confinato
  nell'adapter e il servizio agnostico (nessun ramo host).
- **III**: confermata **una** sola porta (D2); lo store senza porta è coerente con il precedente
  `EmbeddingCache`/`SqliteObservabilityStore` del repo.
- **IV/IX**: la degradazione non-fatale è modellata come nel pattern esistente (warning + no-op), non come
  null muto; gli eventi non trasportano segreti.

Nessuna violazione → **Complexity Tracking vuoto** (nessuna deroga da giustificare).

## Project Structure

### Documentation (this feature)

```text
specs/031-cattura-archiviazione/
├── plan.md              # questo file
├── research.md          # Phase 0 (D1..D9)
├── data-model.md        # Phase 1 (entità, porta, store, scrub)
├── quickstart.md        # Phase 1 (uso + verifiche)
├── contracts/           # Phase 1
│   ├── transcript-capture-port.md
│   ├── memory-archive-store.md
│   └── memory-archive-service.md
└── tasks.md             # Phase 2 (/speckit-tasks — NON creato qui)
```

### Source Code (repository root)

```text
src/sertor_core/
├── domain/
│   ├── memory.py            # NUOVO: SessionRef, TranscriptTurn, TranscriptContent, ArchivedSession
│   └── ports.py             # ESTESO: + TranscriptCaptureAdapter (8ª porta Protocol)
├── observability/
│   └── scrub.py             # NUOVO: scrub_text(text, extra_patterns) — funzione pura
├── adapters/
│   ├── capture/
│   │   └── claude_code.py   # NUOVO: ClaudeCodeCaptureAdapter (host-specifico, parser difensivo)
│   └── memory/
│       └── archive.py       # NUOVO: MemoryArchive (SQLite store, stdlib, non-fatale)
├── services/
│   └── memory_archive.py    # NUOVO: MemoryArchiveService + ArchiveRunReport (orchestratore)
├── config/
│   └── settings.py          # ESTESO: 4 manopole + _int_or_none_env (gemello di _float_or_none_env)
└── composition.py           # ESTESO: build_capture_adapter / build_memory_archive / build_memory_archiver

tests/unit/
├── test_scrub.py                  # scrub_text: pattern noti + extra + ripiego conservativo (SC-004)
├── test_memory_archive_store.py   # MemoryArchive: idempotenza, non-fatale, namespacing (SC-001/002/006/007)
├── test_claude_code_capture.py    # parser difensivo su JSONL sintetici (D3)
└── test_memory_archive_service.py # orchestrazione, skip osservabile, ≥2 mock adapter (SC-005), off=no-op (SC-003)
```

**Structure Decision**: single project, libreria `sertor-core`. Si rispetta la Clean Architecture
esistente: dominio (entità pure + porta), adapters (cattura host-specifica + store concreto),
observability (scrub puro), services (orchestratore), composition (unico wiring). Le dipendenze puntano
verso l'interno; l'host-specifico è isolato in `adapters/capture/claude_code.py`.

## Complexity Tracking

> Nessuna violazione del Constitution Check (PASS 10/10 in entrambe le valutazioni) → **nessuna deroga da
> giustificare**.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| — | — | — |

## Note operative (fuori dal corpo del piano)

- **`.gitignore`**: verificato che `**/.index/`/`**/.index-*/` (righe 21-25) copre già
  `<index_dir>/memory.sqlite`; **nessuna** modifica al `.gitignore` necessaria (annotato per i tasks come
  verifica esplicita, non come edit).
- **Hook SpecKit**: NON eseguiti (per policy del workspace).
- **Git**: nessuna operazione git eseguita; vedi il brief di commit nel report finale (delega al
  `configuration-manager`).
