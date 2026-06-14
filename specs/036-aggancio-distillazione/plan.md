# Implementation Plan: Aggancio della distillazione all'archivio episodico

**Branch**: `036-aggancio-distillazione` | **Date**: 2026-06-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/036-aggancio-distillazione/spec.md` (FEAT-003 dell'epica
`memoria-conversazioni`). Requisiti: `requirements/memoria-conversazioni/aggancio-distillazione/requirements.md`.

## Summary

FEAT-003 chiude il loop *cattura → distillazione*: l'archivio episodico (FEAT-001) e la ricerca
full-text (FEAT-002) sono su master, ma la **distillazione** (`distill`, modalità «from conversation»)
non sa raggiungere il grezzo conservato — oggi pretende un brief scritto a mano e **vieta** il
transcript grezzo, restando una rete di sicurezza solo teorica. Questa feature dà a quella modalità una
**fonte reale e recuperabile**: il **transcript intero** di una sessione archiviata, recuperabile dal
terminale, da portare in contesto, condensare (giudizio del flusso principale) e distillare.

Approccio tecnico — **thin consumer puramente additivo** sull'MVP memoria già su master, tre strati
sottili:

1. **Lettura nel core (Gruppo A).** Il recupero della sessione intera per chiave **riusa**
   `MemoryArchive.get(session_key)` — già esistente, ricompone i turni in ordine. L'unica novità di
   codice di lettura è l'**elenco** delle sessioni recenti: un metodo additivo `list_recent(limit)` su
   `MemoryArchive` (coerente con `get`/`exists`/`upsert`, single store), che ritorna viste sintetiche
   `SessionSummary(session_key, captured_at, turn_count)`. Esposizione thin-consumer via una factory di
   composition `build_memory_reader(settings)` gated su `memory_enabled` (ritorna `None` a memoria
   spenta), coerente con `build_memory_archiver`/`build_episodic_search`. **Nessuna nuova porta**
   (componente concreto single-consumer — YAGNI, come `MemoryArchive`/`EpisodicSearch`).

2. **Superficie CLI (Gruppo B).** Due sotto-comandi sul gruppo `memory` (feature 035): `sertor-rag
   memory show <session_key> [--json]` (transcript intero) e `sertor-rag memory list [-k/--limit N]
   [--json]` (sessioni recenti), con due nuove funzioni **pure** in `cli/output.py`
   (`format_session_transcript`, `format_session_list`), nello stile di `format_memory_results`. Gate
   `None → ConfigError` (exit 1, nomina `SERTOR_MEMORY`); not-found → messaggio azionabile + exit
   non-zero, **distinto** dalla sessione esistente-ma-vuota.

3. **Wiring documentale (Gruppo C).** Aggiornare `.claude/skills/wiki-author/ops/distill.md` (modalità
   «from conversation», righe ~16-22) perché indirizzi il flusso principale a **recuperare la sessione
   mirata** dall'archivio via `sertor-rag memory list`/`show`, condensarla e distillare — sostituendo
   l'obbligo del brief a mano. L'asset installabile `claude-md-block.md` cita `distill` solo come voce
   di una riga (NON contiene la procedura «from conversation»): FR-011 è quindi un **no-op documentato**
   (vedi research D-6).

**Vincolo cardine (FR-013):** nessun trigger automatico di distillazione, mai sull'intero archivio, mai
per-turno/per-sessione. La feature è **solo** recupero/elenco + wiring documentale; la distillazione
resta giudizio del flusso principale, su sessione mirata. Cattura (economica) e distillazione (costosa)
restano disaccoppiate. Local-first, zero rete/embedding/LLM nel percorso di lettura (FR-014).

## Technical Context

**Language/Version**: Python >= 3.11 (codebase su 3.12).

**Primary Dependencies**: nessuna nuova. Solo stdlib (`sqlite3`, `json`, `time`, `argparse`) +
`sertor_core` esistente. Nessun extra opzionale, nessun SDK.

**Storage**: SQLite locale `<index_dir>/memory.sqlite` (FEAT-001), tabelle `sessions`/`turns` (sola
lettura). Indici già presenti: `idx_sessions_project`, `idx_turns_session`. Nessuna scrittura di schema.

**Testing**: `pytest`. Unit per `list_recent` (su SQLite reale temporaneo), per le due funzioni pure di
output, e per i due handler CLI con core mockato (pattern `tests/.../test_cli_search`/`test_cli_memory`).
Marker `not cloud`/`not integration`: tutto locale, nessuna rete.

**Target Platform**: cross-platform (Windows/Linux/macOS); CLI `sertor-rag`.

**Project Type**: single project — libreria `sertor-core` + CLI thin (`src/sertor_core/cli/`).

**Performance Goals**: «percepibilmente immediato» (RNF-3). `get` e `list_recent` sono query SQLite
locali su indici esistenti; nessun budget stringente. Nessuna chiamata di rete (SC-006).

**Constraints**: additivo/non-breaking (FR-012); local-first, zero rete/LLM (FR-014); degradazione
non-fatale (FR-004); host-agnostico (Principio X); gating identico a feature 035 (FR-008).

**Scale/Scope**: archivi tipici migliaia di turni / decine-centinaia di sessioni (dogfood: ~5000 turni).
`list_recent` limitato (default `Settings.memory_list_limit`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Gate derivati dalla costituzione (`.specify/memory/constitution.md`, v1.1.1).

### Pre-design (prima di Phase 0)

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** il core (`MemoryArchive.list_recent`,
  factory) non importa SDK di provider né la CLI; la CLI dipende dal core via factory di composition; il
  wiring sta in `composition.py` (`build_memory_reader`). Esercitabile senza CLI/cloud (test su SQLite
  temporaneo). **PASS**
- [x] **II — Boundary & local-first:** nessuna dipendenza esterna nuova; tutto locale (SQLite stdlib);
  nessun vector store (modalità non-embedding). Local-first by construction. **PASS**
- [x] **III — YAGNI & unità piccole:** **nessuna nuova porta** (single consumer — coerente con
  `MemoryArchive`/`EpisodicSearch`); `list_recent` è additivo sul componente esistente; funzioni di
  output piccole e pure; nessun nuovo extra/dipendenza pesante. **PASS**
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** memoria spenta → factory `None` → `ConfigError`
  azionabile (exit 1); chiave assente → esito esplicito «not found» + exit non-zero, **distinto** da
  sessione vuota (no `None` silenzioso); archivio illeggibile → stato vuoto esplicito + warning (policy
  FEAT-001/002). **PASS**
- [x] **V — Testabilità & misure:** test F.I.R.S.T. previsti (core con SQLite temporaneo, output puro,
  CLI con core mockato), nessun cloud. Non è una feature di retrieval qualitativo → nessuna soglia
  hit@k/MRR applicabile (lettura deterministica): la «misura» è la correttezza di
  ordine/conteggio/gating, coperta dai test. **PASS**
- [x] **VI — Idempotenza & non-distruttività:** percorso **sola lettura** — non scrive `sessions`/
  `turns`, non crea/altera schema (a differenza di FEAT-002 che crea l'indice FTS derivato). `get`/
  `list_recent` deterministici e ripetibili. Install≠run: nessuna ingestione avviata. **PASS**
- [x] **VII — Leggibilità:** naming di dominio (`list_recent`, `SessionSummary`,
  `format_session_transcript`/`format_session_list`); guard clause, funzioni piccole; nessun commento
  ridondante. **PASS**
- [x] **VIII — Configurabilità centralizzata:** unica nuova manopola `memory_list_limit`
  (`SERTOR_MEMORY_LIST_LIMIT`, default 20) in `Settings`, nessun default hardcoded nei componenti
  (coerente con `episodic_limit`). **PASS**
- [x] **IX — Osservabilità:** il recupero/elenco emette log strutturati riusando `log_event`
  (`memory_archive_unavailable` già esistente per i guasti store; evento di lettura per `list_recent`/
  `show` con conteggi, **senza** contenuto in chiaro — coerente con `episodic_search` che hasha). **PASS**
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** `session_key`/`project_id`/`adapter_kind` trattati come
  dati opachi; nessun branch sull'identità dell'assistente; il comando opera su qualunque ospite via
  `index_dir`. Il wiring documentale (`distill.md`) resta nel veicolo skill; l'asset installabile è
  host-agnostico. Dogfooding non giustifica deroghe. **PASS**

**Esito pre-design: PASS 10/10, nessuna deroga.**

### Post-design (dopo Phase 1) — vedi fondo del file.

## Project Structure

### Documentation (this feature)

```text
specs/036-aggancio-distillazione/
├── plan.md              # questo file
├── research.md          # Phase 0 — decisioni di design (D-1..D-7)
├── data-model.md        # Phase 1 — SessionSummary + viste lette
├── quickstart.md        # Phase 1 — come usare show/list e il wiring distill
├── contracts/           # Phase 1 — contratti CLI + lettura core
│   ├── cli-memory-show-list.md
│   └── memory-reader.md
└── tasks.md             # Phase 2 (/speckit-tasks — NON creato qui)
```

### Source Code (repository root)

```text
src/sertor_core/
├── domain/
│   └── memory.py                 # + SessionSummary (dataclass frozen: key, captured_at, turn_count)
├── adapters/memory/
│   └── archive.py                # + MemoryArchive.list_recent(limit) -> tuple[SessionSummary, ...]
├── config/
│   └── settings.py               # + memory_list_limit (SERTOR_MEMORY_LIST_LIMIT, default 20)
├── composition.py                # + build_memory_reader(settings) (gated, None se off)
└── cli/
    ├── __main__.py               # + memory show / memory list (sub-subparser, handler + gate)
    └── output.py                 # + format_session_transcript / format_session_list (pure)

.claude/skills/wiki-author/ops/
└── distill.md                    # aggiornata: «from conversation» attinge all'archivio (Gruppo C)

packages/sertor/src/sertor_installer/assets/
└── claude-md-block.md            # FR-011 no-op documentato (non contiene la procedura «from conversation»)

tests/
└── unit/
    ├── test_memory_archive_list_recent.py   # list_recent: ordine recency, limite, vuoto, store ko
    ├── test_cli_output_session.py           # format_session_transcript/list (umano + json)
    └── test_cli_memory_show_list.py         # handler: gate None→ConfigError, not-found, json
```

**Structure Decision**: single project. La feature estende `sertor-core` (lettura additiva su
`MemoryArchive` + factory in composition) e la CLI thin (`cli/__main__.py` + `cli/output.py`), riusando
in toto i pattern già stabiliti da feature 031/033/035. Nessuna nuova cartella, nessun nuovo modulo
servizio (il «reader» è il `MemoryArchive` concreto esposto da una factory — vedi research D-2).

## Complexity Tracking

> Nessuna violazione costituzionale da giustificare. La tabella resta vuota: design additivo, thin
> consumer, nessuna nuova porta, local-first, non-fatale, host-agnostico.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Post-Design Constitution Check (dopo Phase 1)

Rivalutazione dopo `research.md` / `data-model.md` / `contracts/` / `quickstart.md`. Il design conferma
le scelte pre-design senza introdurre nuove dipendenze, porte o veicoli:

- **I** PASS — `build_memory_reader` ritorna il `MemoryArchive` concreto (o `None`); la CLI lo consuma
  via factory; nessun import SDK/CLI nel core.
- **II** PASS — solo SQLite stdlib, local-first; nessun backend cloud nel percorso.
- **III** PASS — il «reader» **non** è un nuovo servizio né una porta: è il `MemoryArchive` esistente
  con un metodo di lettura in più (research D-1/D-2). Massima parsimonia.
- **IV** PASS — `None` di gating consumato in `ConfigError`; «not found» esplicito distinto da vuoto
  (contract `cli-memory-show-list.md`); guasti store → vuoto + warning.
- **V** PASS — contratti testabili (core con SQLite temporaneo, output puro, CLI mockata).
- **VI** PASS — sola lettura, deterministico, nessuno schema scritto.
- **VII** PASS — naming di dominio, funzioni piccole/pure.
- **VIII** PASS — `memory_list_limit` in `Settings` (unica nuova manopola).
- **IX** PASS — eventi di lettura con conteggi, senza contenuto in chiaro.
- **X** PASS — dati opachi, host-agnostico; asset installabile coerente.

**Esito post-design: PASS 10/10, nessuna deroga.**
