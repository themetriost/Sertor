# Implementation Plan: Ricerca episodica full-text locale (FEAT-002)

**Branch**: `033-ricerca-episodica` | **Date**: 2026-06-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/033-ricerca-episodica/spec.md`

## Summary

Rende **interrogabile** l'archivio dei transcript prodotto da FEAT-001 (già su master): risponde alle
domande di memoria episodica («ne avevamo già parlato?», «com'è finita quella cosa?») con **ricerca
full-text locale a grana di turno**, riferita alla sessione padre. Approccio tecnico (da
`research.md`): **SQLite FTS5 nativo** — tabella virtuale external-content `turns_fts` che indicizza
`turns.content` nello stesso file `memory.sqlite`, con ranking `bm25()` + snippet `snippet()` nativi,
mantenuta **sincrona da trigger** su `turns`. **Zero dipendenze** (stdlib `sqlite3`), **zero cloud**
nel percorso query (privacy by design), **componente concreto + servizio** senza porta (coerente con
`MemoryArchive`). Additivo: FEAT-001 e core invariati; sola lettura sull'archivio (l'indice FTS è
derivato e ricostruibile). Filtro temporale, ordinamento pertinenza/recency, limite e snippet
configurabili; osservabilità con query **hashata**; degradazione non-fatale ovunque tranne la
finestra temporale invalida (errore esplicito).

## Technical Context

**Language/Version**: Python ≥ 3.11 (venv progetto: 3.12.13, SQLite 3.50.4 — FTS5 disponibile,
verificato live).

**Primary Dependencies**: stdlib soltanto (`sqlite3` con FTS5, `hashlib`, `time`, `logging`).
Nessuna nuova dipendenza di terze parti, nessun extra opzionale.

**Storage**: SQLite `<index_dir>/memory.sqlite` di FEAT-001 (DATO). Aggiunge la tabella virtuale FTS5
`turns_fts` (external-content su `turns`) + trigger nello **stesso** file. Git-ignored.

**Testing**: pytest, offline, F.I.R.S.T. — archivio sintetico in `tmp_path`; nessun mock di rete
(la ricerca è puro SQLite locale).

**Target Platform**: libreria cross-platform (host con CPython + `sqlite3`/FTS5).

**Project Type**: libreria (`sertor-core`), Clean Architecture; nessuna UI (la superficie è altrove,
fuori ambito).

**Performance Goals**: latenza singola query budget **< 200 ms p95** su archivio tipico (misurato
<0.1 ms su 5062 turni dogfood); SC-006.

**Constraints**: stdlib-only nel corpo; zero rete nel percorso query (SC-004); host-agnostico
(Principio X); additivo (FEAT-001 invariata); sola lettura sull'archivio; degradazione non-fatale
(archivio/indice assente → stato vuoto, mai errore — eccezione solo per finestra invalida).

**Scale/Scope**: archivio dogfood odierno 36 sessioni / 5062 turni / ~4 MB; dimensionato per crescere
di 1–2 ordini di grandezza restando nei millisecondi (B-tree FTS5).

**Unknowns**: nessuno residuo. Tutte le `DA-FT-*` (A-005..A-009) risolte in `research.md`. Nessun
`NEEDS CLARIFICATION`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Gate derivati dalla costituzione (v1.1.1).

### Check pre-ricerca (Phase 0)

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** PASS — entità in `domain/`/`services/`,
  servizio in `services/`, wiring in `composition.py`. Il corpo importa solo stdlib (`sqlite3`),
  nessun SDK provider, nessuna CLI. Esercitabile come libreria su `tmp_path` senza cloud/CLI.
- [x] **II — Boundary & local-first:** PASS — nessuna dipendenza esterna da astrarre (è stdlib,
  on-machine); local-first per costruzione. Nessun vector store (full-text lessicale, non semantico).
- [x] **III — YAGNI & unità piccole:** PASS — FTS5 nativo evita di reimplementare BM25/snippet;
  **nessuna porta** (un solo consumatore/backend, come `MemoryArchive`); riuso del BM25 RAG
  scartato perché di dominio diverso (no accoppiamento accidentale).
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** PASS — `InvalidTimeWindowError` esplicito su
  `since > until`; esito via `EpisodicResults` (no `None` ambiguo); assenze = stato vuoto **esplicito**
  + warning (outcome legittimo loggato, non null silenzioso).
- [x] **V — Testabilità & misure:** PASS — test F.I.R.S.T. offline su archivio sintetico in
  `tmp_path`; SC-006 misurabile (latenza); SC-001/003/005/008 verificabili. (Hit@k/MRR del retrieval
  RAG **non si applica**: questo è full-text esatto, non ranking semantico da baseline-prototipo; la
  misura pertinente è la completezza dei match esatti SC-001 — vedi Complexity Tracking.)
- [x] **VI — Idempotenza & non-distruttività:** PASS — ricerca **sola lettura** sull'archivio; indice
  FTS **derivato e ricostruibile** (`'rebuild'`); schema/trigger idempotenti (`IF NOT EXISTS`);
  install≠run (gate `memory_enabled`); archivio resta append-only (FEAT-001 invariata).
- [x] **VII — Leggibilità:** PASS — naming di dominio (`search`, `EpisodicHit`, `SearchQuery`,
  `snippet`, `score`); guard clause/early return per i casi vuoti.
- [x] **VIII — Configurabilità centralizzata:** PASS — `episodic_limit`/`episodic_snippet_tokens` in
  `Settings` (env `SERTOR_EPISODIC_*`), nessun default hardcoded nei componenti.
- [x] **IX — Osservabilità:** PASS — evento `episodic_search` (query hashata, filtri, conteggio,
  latenza); nessun segreto nei log; guasto osservabilità non-fatale.
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** PASS — il corpo non conosce l'assistente sorgente:
  opera sull'archivio locale qualunque sia la provenienza (`adapter_kind`/`project_id` sono dati
  opachi). Nessun path fisso/nome di dominio dell'host nel codice. Test SC-007.

**Esito pre-ricerca: PASS 10/10, nessuna deroga.**

### Check post-design (Phase 1) — ri-valutazione

Dopo `data-model.md` + `contracts/episodic-search.md` + `quickstart.md`, nessun principio cambia di
esito:

- **I/II/III**: il design conferma stdlib-only, nessuna porta speculativa, riuso scartato con
  motivazione → invariato PASS.
- **IV**: il contratto distingue chiaramente stato vuoto (8 casi P-*) da errore (1 caso C-ERR) → PASS.
- **V**: il quickstart mostra i test offline `tmp_path` e la mappatura SC → PASS.
- **VI**: invarianti indice I-SYNC/I-REBUILD/I-IDEMP/I-ONCE rendono additività e ricostruibilità
  esplicite; lo schema FTS NON tocca `MemoryArchive` → PASS.
- **IX**: campi evento definiti, `query_hash` mai in chiaro → PASS.
- **X**: contratto C-HOST + SC-007 → PASS.

**Esito post-design: PASS 10/10, nessuna deroga. Constitution Check superato (pre e post).**

## Project Structure

### Documentation (this feature)

```text
specs/033-ricerca-episodica/
├── plan.md              # questo file
├── research.md          # Phase 0 — decisioni DA-FT-* risolte
├── data-model.md        # Phase 1 — entità + schema FTS5 derivato
├── quickstart.md        # Phase 1 — uso come libreria + test offline
├── contracts/
│   └── episodic-search.md   # Phase 1 — contratto sertor.episodic-search/1
└── tasks.md             # Phase 2 (/speckit-tasks — non creato qui)
```

### Source Code (repository root)

```text
src/sertor_core/
├── domain/
│   ├── memory.py            # INVARIATO (FEAT-001: ArchivedSession, TranscriptTurn, …)
│   └── errors.py            # + InvalidTimeWindowError (nuova eccezione di dominio)
├── services/
│   └── episodic_search.py   # NUOVO: EpisodicSearch + SearchQuery/EpisodicHit/EpisodicResults
│                            #        (schema FTS5 lazy/idempotente, trigger, query, snippet, obs)
├── adapters/
│   └── memory/archive.py    # INVARIATO (FEAT-001) — la ricerca legge lo stesso memory.sqlite
├── config/
│   └── settings.py          # + episodic_limit / episodic_snippet_tokens (env SERTOR_EPISODIC_*)
└── composition.py           # + build_episodic_search(settings) -> EpisodicSearch | None
                             #   (gate memory_enabled, accanto a build_memory_archive)

tests/unit/
└── test_episodic_search.py  # NUOVO: F.I.R.S.T. offline (tmp_path, archivio sintetico)
```

**Structure Decision**: feature **additiva** dentro `sertor-core`. Un solo modulo nuovo di servizio
(`services/episodic_search.py`) che ospita componente + entità di input/output (vicine al loro unico
uso, YAGNI), una eccezione nuova in `domain/errors.py`, due manopole in `Settings`, una `build_*` in
`composition.py`. Nessuna porta nuova in `domain/ports.py` (coerente con `MemoryArchive`, che è
"concrete component, NO port"). FEAT-001 (`domain/memory.py`, `adapters/memory/archive.py`) **non
viene toccata**: lo schema FTS è creato (lazy, idempotente) dal componente di ricerca, non
dall'archivio.

## Complexity Tracking

> Nessuna violazione del Constitution Check. Tabella delle deroghe non necessaria.

Nota di chiarimento (non deroga): il gate **V** sulla misura hit@k/MRR con baseline-prototipo è
pensato per il *retrieval semantico* dei motori RAG; questa feature è **full-text lessicale esatto**,
quindi la misura di qualità pertinente è la **completezza dei match esatti** (SC-001, 100%) e la
**latenza** (SC-006), non una metrica di ranking semantico. È allineamento allo spirito del principio
(qualità provata da misure), non una deroga.
