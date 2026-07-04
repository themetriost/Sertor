# Implementation Plan: Rituale post-merge — re-lock del runtime `.sertor/` a HEAD

**Branch**: `092-f8-relock-runtime` | **Date**: 2026-07-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/088-relock-runtime/spec.md` (E15-FEAT-008).

## Summary

Meccanizza il re-aggancio del runtime `.sertor/` all'HEAD di `origin/master` dopo un merge, spostandolo
dalla memoria dell'agente a un passo deterministico (confine D↔N). Approccio deciso (Q1 = opzione a): uno
**script dogfood-only** `scripts/dev/relock-runtime.ps1` (check-then-act, fail-loud) invocato dal **rituale
post-merge** del flusso principale — **non** un hook distribuito, così il re-lock non leakka sui client (che
pinnano versioni). Contestualmente si **gitignora** `.sertor/uv.lock` (correzione di F1: un lock tracciato +
re-lock produrrebbe churn/loop), lasciando tracciato solo `.sertor/pyproject.toml`. Una **guardia** blinda il
tracking; la doc del rituale in `CLAUDE.md` aggiunge il passo di re-lock (prima di re-index/smoke) e il **gate
«suite completa + ruff verdi» prima del merge** (regressione emersa il 2026-07-03). `sertor-core` INVARIATO.

## Technical Context

**Language/Version**: PowerShell (script `.ps1`, coerente con l'ecosistema hook/script del repo — regola
standing «solo PowerShell»); Python 3.11+ solo indirettamente (il runtime `.sertor/` è un progetto `uv`).

**Primary Dependencies**: `uv` (vehicle: `uv lock --upgrade` / `uv sync` nel progetto `.sertor/`), `git`
(vehicle: `git rev-parse origin/master`, confronto commit). Nessuna dipendenza Python nuova.

**Storage**: N/A (agisce su `.sertor/pyproject.toml` tracciato e `.sertor/uv.lock` locale/gitignorato).

**Testing**: `pytest` (guardia di regressione sul tracking git in `tests/unit/`, offline, presence-agnostica).

**Target Platform**: workspace di sviluppo di Sertor (dogfood-only). Lo script è Windows/pwsh-first come gli
altri `scripts/dev/`; non è un asset distribuito → non serve parità mac/Linux (a differenza degli hook host).

**Project Type**: tooling di sviluppo/governance del dogfood (non prodotto). Nessun modulo `src/`.

**Performance Goals**: il check è cheap (un `git rev-parse` + lettura del commit lockato); il re-sync
costoso avviene **solo** se il runtime è indietro (check-then-act, NFR-2).

**Constraints**: dogfood-only (fuori dagli asset distribuiti); solo via vehicle (`uv`/`git`), mai import di
`sertor_core`; fail-loud (Principio XII); rete richiesta per il re-lock (dichiarata, fail-loud se offline).

**Scale/Scope**: un file script (~80-120 righe), una voce `.gitignore`, un `git rm --cached`, un file di test
di guardia, modifiche di doc in `CLAUDE.md`. Nessun impatto su `src/`, `packages/`, asset distribuiti.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* (costituzione v1.4.0)

- [x] **I — Dipendenze verso l'interno:** **N/A** — nessun codice del core toccato; feature di tooling
  dogfood. `sertor-core` invariato.
- [x] **II — Boundary & local-first:** **N/A** — nessun provider/backend coinvolto.
- [x] **III — YAGNI & unità piccole:** **PASS** — un solo script minimale check-then-act, nessuna astrazione
  nuova; niente hook/framework dove basta uno script invocato dal rituale.
- [x] **IV — Errori espliciti:** **PASS** — lo script fallisce esplicitamente (exit non-zero + messaggio
  azionabile) su rete/risoluzione/`uv` assente/progetto mancante; nessuno stato parziale spacciato per ok.
- [x] **V — Testabilità & misure:** **PASS** — guardia di regressione F.I.R.S.T. sul tracking git (offline,
  deterministica); la logica check-then-act è verificabile dal vivo (accettazione).
- [x] **VI — Idempotenza & non-distruttività:** **PASS** — re-lock idempotente (a HEAD già lockato = no-op);
  non tocca file dell'utente (agisce solo sul runtime `.sertor/`, artefatto locale).
- [x] **VII — Leggibilità:** **PASS** — script piccolo, guard clause/early return, naming di dominio
  (`relock`, `runtime`, `behind`).
- [x] **VIII — Configurabilità centralizzata:** **N/A** — nessun default di core; il ramo/remote è
  `origin/master` (convenzione del repo), non un parametro di prodotto.
- [x] **IX — Osservabilità:** **PASS (proporzionale)** — lo script stampa cosa fa (check → no-op oppure
  re-lock verso `<sha>`) e gli errori; non è un'operazione di retrieval → nessun log strutturato di core.
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** **PASS** — la feature è **dogfood-only per costruzione**: lo
  script vive in `scripts/dev/` (mai bundlato dagli installer) e una guardia verifica che **non** compaia negli
  asset distribuiti né nell'hook `rag-freshness.ps1`. Non introduce assunzioni dell'ospite in alcuna capacità
  distribuita; il dogfooding **non** viene usato come licenza per accoppiare un asset host — al contrario, il
  design isola esplicitamente il meccanismo dal percorso host (rispetta il confine invece di sfumarlo).
- [x] **XI — Consumo via vehicles:** **PASS** — il re-lock passa **solo** per `uv` e `git`; **non** importa
  `sertor_core` (FR-006). `sertor-core` invariato.
- [x] **XII — Fail Loud, Fix the Cause:** **PASS** — è l'incarnazione del principio: rimuove la *causa* del
  runtime stantio (re-lock meccanico) invece di tollerarla; fallisce rumorosamente se non può (FR-005). La
  correzione del lock committato rimuove la causa del churn/loop, non la maschera.
- [x] **Allineamento alla missione:** **PASS** — serve direttamente la stella polare «contesto dell'agente
  sempre reale»: il dogfood tramite RAG serve codice che corrisponde al `master` reale, non stantio. Rafforza
  la fedeltà del corpus code+doc reso all'agente durante il dogfooding.

**Esito gate:** PASS 12/12 + missione. Nessuna violazione → Complexity Tracking vuoto.

## Project Structure

### Documentation (this feature)

```text
specs/088-relock-runtime/
├── plan.md              # questo file
├── research.md          # Phase 0 — decisioni di design (Q1/Q2 risolte)
├── data-model.md        # Phase 1 — entità (script/lock/rituale), minimale
├── quickstart.md        # Phase 1 — come si usa il re-lock + rituale post-merge
├── contracts/
│   └── relock-runtime.md # Phase 1 — contratto CLI dello script (input/exit/output)
└── checklists/
    └── requirements.md   # dalla fase specify
```

### Source Code (repository root)

```text
scripts/dev/
└── relock-runtime.ps1        # NUOVO — check-then-act, fail-loud, dogfood-only

.gitignore                    # MODIFICATO — ignora .sertor/uv.lock
.sertor/
├── pyproject.toml            # TRACCIATO (invariato) — spec stabile del runtime
└── uv.lock                   # git rm --cached → locale/gitignorato

tests/unit/
└── test_relock_runtime_dogfood.py  # NUOVO — guardia: lock non tracciato, pyproject tracciato,
                                     #         script non presente negli asset distribuiti

CLAUDE.md                     # MODIFICATO — rituale post-merge: passo re-lock (prima di re-index/smoke)
                              #              + gate «suite+ruff verdi» prima del merge
```

**Structure Decision**: feature di **tooling dogfood** — nessun modulo di prodotto. Tutto vive in
`scripts/dev/` (script), root (`.gitignore`, `.sertor/`), `tests/unit/` (guardia) e `CLAUDE.md` (rituale). Il
confine dogfood↔distribuito è garantito dalla collocazione (`scripts/dev/`, non `packages/**/assets/`) e dalla
guardia. `sertor-core` (`src/sertor_core/`) e `packages/` non sono toccati.

## Complexity Tracking

> Nessuna violazione del Constitution Check → sezione vuota.
