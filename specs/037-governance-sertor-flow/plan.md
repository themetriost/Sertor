# Implementation Plan: Installer di governance/SDLC `sertor-flow`

**Branch**: `037-governance-sertor-flow` | **Date**: 2026-06-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/037-governance-sertor-flow/spec.md` · Requisiti:
`requirements/sertor-cli/governance-sertor-flow/requirements.md` (25 REQ + 6 NFR, 7 DA risolte).

## Summary

Distribuire l'apparato di **metodo di sviluppo (SDLC)** di Sertor (flusso SpecKit, gestione requisiti,
delega git, costituzione-starter, blocco rituale `CLAUDE.md`) come **pacchetto installabile separato
`sertor-flow`**, ortogonale al RAG e **senza dipendenza da `sertor-core`**. L'approccio: **estrarre il
motore di installazione** già esistente in `packages/sertor/src/sertor_installer` in un **toolkit
condiviso `sertor-install-kit`** (terzo membro del workspace, puro stdlib), su cui poggiano sia `sertor`
(wiki/rag) sia `sertor-flow` (governance). Il bundle governance è in gran parte **vendoring** di asset
spec-kit (MIT, pinnato 0.8.18) + asset Sertor-authored, depositati con la stessa meccanica non
distruttiva del wiki. **Il pezzo di lavoro principale e più rischioso è l'estrazione del kit** (refactor
di codice funzionante: la non-regressione di `sertor` è il gate); il bundle è in confronto
copia-di-asset + un plan-builder.

## Technical Context

**Language/Version**: Python ≥ 3.11.

**Primary Dependencies**: nessuna a runtime per `sertor-install-kit` e `sertor-flow` (solo stdlib:
`importlib.resources`, `logging`, `json`, `pathlib`). `sertor-flow` dipende dal solo
`sertor-install-kit`. **NON** dipende da `sertor-core`.

**Storage**: filesystem dell'ospite (asset depositati in `.claude/`, `.specify/`, `CLAUDE.md`). Nessun
DB.

**Testing**: `pytest` (unit + integration su directory temporanee); `CommandRunner` mockabile (non
necessario alla governance MVP); guard test anti-drift asset↔dogfood.

**Target Platform**: cross-platform (Windows + POSIX); per questo si spediscono entrambe le varianti di
script (ps + bash).

**Project Type**: monorepo uv a **tre** pacchetti — `sertor-core` (root), `sertor` (packages/sertor),
e i nuovi `sertor-install-kit` + `sertor-flow` (packages/).

**Performance Goals**: N/A (installer locale, una manciata di file); l'install completa in pochi secondi.

**Constraints**: install ≠ run; non distruttivo/idempotente; offline; host-agnostico; nessun segreto
versionato; indipendenza da `sertor-core`.

**Scale/Scope**: ~poche decine di asset nel bundle; 1 nuovo toolkit + 1 nuovo pacchetto + modifiche
minime additive a `packages/sertor` (repoint import + puntatore governance).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Costituzione v1.1.1. Per questa feature (installer di metodo, **nessun retrieval**) i gate RAG-specifici
sono N/A; gli altri PASS.

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** il *motore* è il toolkit `sertor-install-kit`
  puro (stdlib, niente SDK provider, niente CLI framework); `sertor-flow` è un **thin consumer** che lo
  cabla. Il kit è testabile in isolamento. **PASS.**
- [x] **II — Boundary & local-first:** nessun provider esterno; tutto offline. `CommandRunner` astrae gli
  eventuali comandi esterni (non usati dalla governance MVP). **PASS** (parte vector-store = N/A).
- [x] **III — YAGNI & unità piccole:** l'estrazione del kit è giustificata da un **secondo consumatore
  reale** (sertor-flow), non speculativa; bundle completo senza selettività speculativa (Could);
  generalizzazioni minime (marker parametrico, executor a callback). **PASS.**
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** `InstallerError`/`ConfigError` di dominio; fail-fast
  no-rollback; errori del core avvolti al boundary; niente `None` silenzioso né stato parziale nascosto
  (il passo fallito è nominato). **PASS.**
- [x] **V — Testabilità & misure:** test F.I.R.S.T. su temp dir, deterministici; nessun cloud. Misure di
  retrieval = N/A (nessun retrieval). **PASS.**
- [x] **VI — Idempotenza & non-distruttività:** cuore della feature — CREATE_IF_ABSENT, merge additivi,
  blocco a marker, install≠run, re-run a zero modifiche. **PASS.**
- [x] **VII — Leggibilità:** naming di dominio dell'installer (artifact/outcome/plan/merge/marker);
  guard clause; funzioni piccole. **PASS.**
- [x] **VIII — Configurabilità centralizzata:** i default vivono nei template/asset (starter
  costituzione, template init), non hardcoded nel corpo (modello `config_gen`). **PASS.**
- [x] **IX — Osservabilità:** `log_event` stdlib del kit emette eventi strutturati (operazione, esiti),
  nessun segreto. **PASS.**
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** è il cuore — asset host-facing in inglese, host-specifici
  generati per-host (init/integration), nessuna assunzione sul progetto ospite nel corpo; gira su repo
  nuovo/esistente, code/doc-agnostico. Il dogfooding (Sertor su sé stesso) non giustifica deroghe.
  **PASS.**

**Esito:** PASS 10/10, **nessuna deroga**. Complexity Tracking vuoto.

## Project Structure

### Documentation (this feature)

```text
specs/037-governance-sertor-flow/
├── plan.md              # questo file
├── research.md          # Fase 0 — D1..D10 + Constitution pre-design
├── data-model.md        # Fase 1 — entità (migrate + nuove) + piano governance
├── quickstart.md        # Fase 1 — uso ospite/sviluppo/smoke
├── contracts/
│   ├── cli-sertor-flow.md      # contratto CLI `sertor-flow/1`
│   └── install-kit-api.md      # contratto toolkit `install-kit/1`
└── tasks.md             # Fase 2 (/speckit-tasks — non creato qui)
```

### Source Code (repository root)

```text
packages/
├── sertor-install-kit/            # NUOVO — toolkit condiviso (no dipendenza da sertor-core)
│   ├── pyproject.toml             # name=sertor-install-kit, stdlib-only
│   ├── src/sertor_install_kit/
│   │   ├── artifacts.py           # migrato da sertor_installer
│   │   ├── errors.py              # NUOVO — InstallerError/ConfigError
│   │   ├── observability.py       # NUOVO — log_event stdlib
│   │   ├── resources.py           # migrato (anchor parametrico)
│   │   ├── claude_md.py           # migrato + write_marker_block(marker_start,end)
│   │   ├── report.py              # migrato (to_json)
│   │   ├── executor.py            # NUOVO — execute_plan(plan, apply) generico
│   │   ├── settings_merge.py / env_merge.py / mcp_merge.py / gitignore_append.py  # migrati
│   │   ├── command_runner.py      # migrato
│   │   └── sync.py                # migrato (radici asset parametriche)
│   └── tests/                     # test migrati dei primitivi
│
├── sertor/                        # ESISTENTE — repoint import al kit + wrapping errori core
│   └── src/sertor_installer/
│       ├── install_wiki.py        # importa dal kit; wrappa errori sertor_core al boundary
│       ├── install_rag.py         # importa dal kit
│       ├── config_gen.py / rag_profile.py   # restano (wiki/rag-specifici)
│       └── __main__.py            # `install governance` → messaggio-puntatore a sertor-flow (D9)
│
└── sertor-flow/                   # NUOVO — installer governance
    ├── pyproject.toml             # name=sertor-flow, dep=sertor-install-kit, script `sertor-flow`
    ├── src/sertor_flow/
    │   ├── __main__.py            # CLI: `sertor-flow install [--target] [--json]`
    │   ├── install_governance.py  # build_governance_plan + apply-functions (thin sul kit)
    │   ├── profile.py             # GovernanceProfile (inferenza host)
    │   ├── generate.py            # generazione file init/integration per-host
    │   └── assets/                # bundle (claude/** + specify/** + starter + blocco SDLC + NOTICE)
    └── tests/
        ├── unit/                  # plan, apply, generate, non-distruttività, indipendenza-core
        ├── integration/          # install end-to-end su temp dir, idempotenza, re-run
        └── unit/test_assets_sync.py  # guardia anti-drift asset↔dogfood (subset governance)
```

**Structure Decision**: terzo e quarto membro del workspace uv (`members` aggiornato). `sertor-flow`
dipende **solo** da `sertor-install-kit`; `sertor` dipende da `sertor-install-kit` + `sertor-core`.

## Sequenza d'implementazione consigliata (per /speckit-tasks)

1. **Estrai il toolkit** `sertor-install-kit` (sposta i primitivi, aggiungi errors/observability/
   executor, generalizza claude_md/resources/sync). Test dei primitivi verdi nel kit.
2. **Repoint `sertor`** ai simboli del kit + wrapping degli errori `sertor_core` al boundary. **Gate di
   non-regressione:** l'intera suite di `packages/sertor` resta verde (rischio #1).
3. **Crea `sertor-flow`**: pyproject + membro workspace + CLI + plan-builder + apply + generate +
   profilo.
4. **Porta gli asset** nel bundle: vendoring spec-kit (pinned + NOTICE/LICENSE), asset Sertor-authored
   (requirements, configuration-manager), starter costituzione, blocco SDLC; guard test anti-drift.
5. **Puntatore** `sertor install governance` → messaggio a sertor-flow (D9).
6. **Test end-to-end** (install/idempotenza/non-distruttività/indipendenza-core/attribuzione) + ruff +
   intera suite.

## Complexity Tracking

> Nessuna violazione costituzionale da giustificare. Tabella vuota.
