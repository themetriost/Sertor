# Implementation Plan: Superficie CLI memoria + cattura automatica a fine sessione

**Branch**: `035-memoria-cli-hook` | **Date**: 2026-06-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/035-memoria-cli-hook/spec.md`

## Summary

L'MVP memoria (cattura/archivio + ricerca episodica) vive già su master solo come **libreria**:
`MemoryArchiveService.archive_all()` e `EpisodicSearch.search()`, cablati da factory **già gated**
(`build_memory_archiver`/`build_episodic_search` → `None` se `SERTOR_MEMORY` off). Mancano la
**superficie d'uso** e un **grilletto** che faccia scattare la cattura da sola.

Questa feature aggiunge tre capacità **sottili** (thin consumer, Principio I):
1. **`sertor-rag memory archive`** — gruppo di comando `memory` con sub-subcomando `archive`,
   delega a `archive_all()`, stampa il report `archived/skipped/errors` (umano + `--json`).
2. **`sertor-rag memory search <query>`** — sub-subcomando `search`, delega a
   `EpisodicSearch.search(SearchQuery(...))`, cita i turni (`session/role/turn/snippet/score`,
   umano + `--json`), con `--since/--until/-k`.
3. **Hook `SessionEnd`** (Claude Code) — script PowerShell `.claude/hooks/memory-capture.ps1` +
   voce in `.claude/settings.json`, che invoca `sertor-rag memory archive` in modo non-bloccante e
   non-fatale, no-op a memoria spenta.

Approccio (research): forma argparse a gruppo `memory` con sub-subparser; gate consumato
intercettando il `None` delle factory (comando → `ConfigError` exit 1) e con pre-check dell'env
nell'hook (no-op exit 0); l'hook e il comando archiviano **tutto** via `archive_all()` (idempotente);
output via due funzioni pure in `cli/output.py`. **Additivo puro**: core e comandi esistenti
invariati.

## Technical Context

**Language/Version**: Python >= 3.11

**Primary Dependencies**: stdlib + argparse (CLI già presente); PowerShell per l'hook (host Claude
Code). **Nessuna nuova dipendenza** (Principio III) — i servizi del core e le factory esistono già.

**Storage**: nessun nuovo stato. L'archivio (`<index_dir>/memory.sqlite`) e l'indice FTS5 sono di
FEAT-001/002 (master), consumati read-only/idempotente. Unico nuovo file versionato: lo script hook.

**Testing**: `uv run pytest` — unit test dei comandi con core mockato (stile
`tests/unit/test_cli_search.py`: monkeypatch di `build_memory_archiver`/`build_episodic_search`).
Logica dell'hook PowerShell: verifica manuale documentata (gate/no-op), §3 quickstart.

**Target Platform**: CLI cross-platform (i comandi); hook host-specifico Windows/PowerShell (Claude
Code, primo adattatore).

**Project Type**: libreria + veicolo CLI (single project, `src/sertor_core/`).

**Performance Goals**: N/A oltre il vincolo «hook non-bloccante» (cattura locale deterministica;
timeout host come cap). La latenza di `memory search` è quella del core (FTS5 locale, già loggata).

**Constraints**: thin consumer (nessuna logica core nei comandi/hook, Principio I); host-agnostici i
comandi, host-specifico solo l'hook (Principio X); gate `SERTOR_MEMORY` (privacy-by-default);
hook non-bloccante/non-fatale; additivo (core/CLI invariati); deterministico/idempotente; testabile.

**Scale/Scope**: 2 sub-subcomandi CLI + 2 funzioni di output + 1 script hook + 1 voce di config.
Nessuna nuova entità di dominio, nessuna porta nuova.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Gate derivati da `.specify/memory/constitution.md` v1.1.1.

### Esito PRE-ricerca (Phase 0)

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** PASS. Comandi e hook sono **thin
  consumer**: delegano interamente al core via le factory di composition
  (`build_memory_archiver`/`build_episodic_search`); nessuna logica di archivio/ricerca
  reimplementata (FR-001/005/011). Il CLI non importa SDK, solo `composition` + `domain.errors`. Il
  core resta testabile con mock senza CLI.
- [x] **II — Boundary & local-first:** PASS. Nessuna nuova dipendenza esterna; la sorgente di cattura
  è già dietro la porta `TranscriptCaptureAdapter`. Tutto locale (FTS5 + SQLite stdlib), zero cloud
  nel percorso memoria.
- [x] **III — YAGNI & unità piccole:** PASS. Nessuna astrazione nuova; si riusano factory, entità e
  funzioni di output esistenti. `archive_all()` (no nuovo metodo «solo-sessione-corrente»). Helper
  CLI piccoli (`_require_archiver`/`_require_episodic_search`, `_cmd_memory_*`).
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** PASS. Memoria off → `ConfigError` azionabile (exit
  1, nomina `SERTOR_MEMORY=true`); `since>until` → `InvalidTimeWindowError` (dal core). Nessun `None`
  silenzioso: il `None` delle factory è intercettato e tradotto in errore esplicito.
- [x] **V — Testabilità & misure:** PASS. Comandi testabili con core mockato (F.I.R.S.T.), come gli
  altri `_cmd_*`. La qualità del retrieval episodico è già misurata in FEAT-002; questa feature è
  superficie, non un nuovo motore (nessuna nuova soglia hit@k/MRR da fissare).
- [x] **VI — Idempotenza & non-distruttività:** PASS. `archive archive` idempotente (re-run →
  `archived=0`/`skipped`); `search` sola lettura; l'hook è sicuro da rilanciare. Install≠run: lo
  script hook non avvia ingestione da solo (scatta solo a fine sessione, gated).
- [x] **VII — Leggibilità:** PASS. Naming di dominio (archive/search/snippet/score); funzioni di
  output pure e piccole; guard clause nei comandi (pre-check → early raise).
- [x] **VIII — Configurabilità centralizzata:** PASS. `memory_enabled`, `episodic_limit`,
  `episodic_snippet_tokens` già in `Settings`; i comandi leggono da lì (nessun default hardcoded).
- [x] **IX — Osservabilità:** PASS. Gli eventi (`memory_session_archived/skipped`, `episodic_search`)
  sono già emessi dal core; la superficie non ne sopprime alcuno. Nessun segreto nei log (i conteggi
  e l'hash della query restano nel core).
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** PASS. I comandi non incorporano assunzioni
  dell'ospite (girano su qualsiasi progetto). L'hook è dichiaratamente host-specifico (Claude Code) e
  si limita ad **adattare il trigger** al comando host-agnostico (FR-018); la distribuzione su altri
  ospiti è fuori ambito (estensione). Il dogfood non giustifica deroghe nei comandi.

**Risultato pre-ricerca: PASS 10/10, nessuna deroga.**

### Esito POST-design (Phase 1) — dopo research/data-model/contracts

Riconfermato dopo aver fissato le decisioni D1-D6:
- **I**: il design dei comandi (D1) e dell'hook (D4/D6) resta thin: l'hook invoca il comando, il
  comando invoca la factory. Nessuna logica core trapelata. **PASS**.
- **IV**: il gate (D2) tramite intercettazione del `None` produce un `ConfigError` esplicito; nessun
  ramo restituisce `None` come segnale. **PASS**.
- **VI**: D3 (`archive_all()`) eredita l'idempotenza del core; l'hook non-fatale (D6) non lascia stato
  parziale. **PASS**.
- **X**: D4 colloca tutta la specificità host nello **script hook** (versionato per il dogfood); i due
  comandi e le funzioni di output restano portabili. **PASS**.
- Gli altri principi non mutano col design.

**Risultato post-design: PASS 10/10, nessuna deroga.** *(Complexity Tracking vuoto.)*

## Project Structure

### Documentation (this feature)

```text
specs/035-memoria-cli-hook/
├── plan.md              # questo file
├── research.md          # Phase 0 — D1..D6 (forma argparse, gate, archive_all, wiring, output, non-fatale)
├── data-model.md        # Phase 1 — entità core consumate + strutture di presentazione
├── quickstart.md        # Phase 1 — giro archivia→ritrova + hook
├── contracts/
│   ├── cli-memory.md     # `cli.memory/1` — memory archive / memory search
│   └── hook-session-end.md  # `hook.memory-capture/1` — hook Claude Code
└── checklists/          # (preesistente)
```

### Source Code (repository root)

```text
src/sertor_core/cli/
├── __main__.py          # MODIFICATO: + parser `memory` con sub-subparser archive/search;
│                        #   + _cmd_memory_archive / _cmd_memory_search;
│                        #   + _require_archiver / _require_episodic_search (gate → ConfigError);
│                        #   + parsing di --since/--until (ISO/epoch). Dispatch via set_defaults(handler).
└── output.py            # MODIFICATO: + format_archive_report(report, *, json)
                         #             + format_memory_results(results, settings, *, json)

.claude/
├── hooks/
│   └── memory-capture.ps1   # NUOVO (versionato): pre-check SERTOR_MEMORY → no-op; else invoca
│                            #   `sertor-rag memory archive`, try/catch, exit sempre 0.
└── settings.json            # MODIFICATO: + voce nel blocco SessionEnd (accanto al wiki hook).

tests/unit/
└── test_cli_memory.py       # NUOVO: archive/search con core mockato; caso gate (None → ConfigError);
                             #   idempotenza (archived=0 al re-run); since>until → exit 1; --json.
```

**Structure Decision**: single project esistente. La feature tocca **solo** il veicolo CLI
(`cli/__main__.py`, `cli/output.py`) e l'infrastruttura hook versionata (`.claude/`). Il core
(`services/`, `composition.py`, `domain/`, `config/`) resta **invariato** (FR-019). Nessuna nuova
porta, nessun nuovo adapter, nessuna nuova dipendenza.

## Complexity Tracking

> Nessuna violazione del Constitution Check: tabella non necessaria (PASS 10/10 pre e post design).
