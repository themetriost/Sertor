# Implementation Plan: Parity guard esteso (.ps1/.json) + budget altitude blocchi CLAUDE.md (E10-FEAT-024)

**Branch**: `082-parity-guard-budget` | **Date**: 2026-06-30 | **Spec**: `specs/082-parity-guard-budget/spec.md`

**Input**: Feature specification from `/specs/082-parity-guard-budget/spec.md` ·
Requirements `requirements/debito-tecnico/parity-guard-budget/requirements.md` (audit ISSUE-10).

## Summary

Chiude due falle nei guard-rail offline emerse dall'audit ISSUE-10, con **tre guardie additive
solo-test, zero codice runtime**:
1. **Shape-guard di presenza (Gruppo A, Must)** — assicura che il `sertor-hooks.json` reso dal piano
   rag per `COPILOT_CLI` contenga gli eventi `SessionEnd`/`SessionStart`/`PreToolUse` (rimuovere un
   frammento → CI rossa che nomina l'evento). Complementa, non sostituisce, lo schema-test esistente.
2. **Budget altitude (Gruppo B, Must)** — soglie **per-blocco** costanti (`wiki=60`, `RAG=58`,
   `SDLC=70`) sui tre `claude-md-block*.md` always-on, con coverage esaustiva (un 4° blocco non
   registrato → rosso).
3. **Source-level guard rag (Gruppo C, Should)** — i 3 script rag SessionEnd non emettono un payload
   Copilot `decision` su stdout (commenti strippati prima della scansione).

Approccio (research): tre **nuovi file di test**; il Gruppo A riusa il pattern `_rag_wiring`
(`tmp_path`) di `test_schema_copilot_hooks.py`; il Gruppo B vive nella suite **root** (cross-package) e
legge gli asset via il reader parametrico del kit; il Gruppo C riusa lo strip-commenti di
`test_assets_hook_cli_invocation.py` e vieta la **chiave `decision`** (non `reason`, false-positive sul
breadcrumb FEAT-019). Nessun file esistente viene modificato.

## Technical Context

**Language/Version**: Python 3.11+ (test-only) · **Primary Dependencies**: pytest, stdlib (`re`,
`json`, `importlib.resources`); `sertor_install_kit.resources`, `sertor_installer.install_rag`,
`sertor_install_kit.surfaces` (solo lettura/esecuzione piano in `tmp_path`) · **Storage**: N/A ·
**Testing**: pytest, **offline** (no rete, no `uv` subprocess, no `pwsh` per gli assert critici) ·
**Target Platform**: Windows/Linux CI · **Project Type**: workspace `uv` multi-pacchetto (test su
`packages/sertor`, `packages/sertor-flow`, root `tests/`) · **Performance Goals**: N/A (guardie
istantanee) · **Constraints**: zero modifiche a `sertor_core`/runtime; comportamento installer
byte-identico · **Scale/Scope**: 3 nuovi file di test (~3 guardie + meta-test); 0 file di produzione.

## Constitution Check

*GATE pre-Phase 0 e re-check post-Phase 1. Costituzione v1.4.0 (12 principi + missione).*

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** N/A operativo — nessun codice di core
  toccato; le guardie sono test. PASS (non viola).
- [x] **II — Boundary & local-first:** PASS — nessun SDK/dipendenza nuova; lettura asset via il reader
  del kit, esecuzione piano in `tmp_path` (offline).
- [x] **III — YAGNI & unità piccole:** PASS — guardie minime; costanti esplicite invece di logica;
  nessuna astrazione condivisa nuova (ogni guard ridefinisce il piccolo strip-helper, convenzione del
  repo) → zero accoppiamento e zero modifica ai file esistenti.
- [x] **IV — Errori espliciti:** PASS — i fallimenti sono `AssertionError` che **nominano** evento/file/
  conteggio/soglia (nessun fallimento muto).
- [x] **V — Testabilità & misure:** PASS — è interamente testabilità: aggiunge reti F.I.R.S.T. con
  anti-pattern (non-vacuità) per ciascuna guardia.
- [x] **VI — Idempotenza & non-distruttività:** PASS — guardie deterministiche, sola lettura; nessuna
  scrittura sugli asset (il piano gira in `tmp_path`).
- [x] **VII — Leggibilità:** PASS — nomi di dominio (`assert_events_present`, `_BUDGETS`,
  `_DECISION_PAYLOAD`); commenti solidali sull'intento (lista frammenti, limite per-evento).
- [x] **VIII — Configurabilità centralizzata:** N/A — nessuna config del core; le soglie sono costanti
  di test deliberate (REQ-012). PASS (non viola).
- [x] **IX — Osservabilità:** N/A — nessuna operazione di runtime; nessun log/segreto coinvolto. PASS.
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** PASS — le guardie operano sugli **asset bundlati** e sul
  piano reso per entrambi gli assistenti; verificano proprio la portabilità host-facing (wiring Copilot
  integro, blocchi compatti). Nessuna assunzione d'ospite incorporata.
- [x] **XI — Consumo via vehicles (NON-NEGOZIABILE):** PASS — **zero** modifiche a `sertor_core`; le
  guardie sono test (unica eccezione ammessa al confine vehicles). Il Gruppo A usa il plan-builder/
  render dell'installer (`build_rag_plan`/`render_copilot_hooks`) come i test esistenti, non il core a
  runtime.
- [x] **XII — Fail Loud, Fix the Cause:** PASS — è l'essenza della feature: rende **rosso** (early
  feedback) ciò che oggi degrada in silenzio (frammento Copilot sparito; blocco gonfiato; payload
  `decision` su stdout). Nessuna soppressione; ogni guardia ha l'anti-pattern che ne prova la non-vacuità.
- [x] **Allineamento alla missione:** PASS — la stella polare è la **qualità/realtà del contesto reso
  all'agente ospite**: un wiring Copilot a cui manca un evento lascia l'agente senza freschezza-RAG/
  memoria enforced (contesto stantio non rilevato); blocchi always-on che ricrescono gonfiano
  l'istruzione e abbassano il segnale-rumore. Le guardie impediscono la regressione di capacità
  host-facing già consegnate (freschezza FEAT-076, altitude FEAT-021).

**Esito PRE-design:** **PASS 12/12 + missione PASS**, senza deroghe. **Complexity Tracking vuoto.**

**Re-check POST-design (Phase 1):** invariato — **PASS 12/12 + missione PASS**. Il design conferma
solo-test/zero-runtime: tre nuovi file di test, nessuna modifica a produzione o ai test esistenti,
tutto offline. Nessuna deroga, nessuna voce di Complexity Tracking.

## Project Structure

### Documentation (this feature)
```text
specs/082-parity-guard-budget/
├── plan.md          # questo file
├── research.md      # Phase 0 — DA-D-1/2/3 risolte
├── data-model.md    # Phase 1 — costanti soglia + guardie
├── contracts/
│   └── guards.md    # Phase 1 — contratto delle 3 guardie + soglie
├── quickstart.md    # Phase 1 — verifica delle guardie
└── tasks.md         # Phase 2 (/speckit-tasks — NON creato qui)
```

### Source Code (repository root)
```text
packages/sertor/tests/
├── test_copilot_hook_presence.py          # NUOVO — Gruppo A (shape-guard presenza)
└── test_hooks_rag_no_stdout_payload.py     # NUOVO — Gruppo C (source-level rag, Should)

tests/unit/
└── test_claude_md_block_budget.py          # NUOVO — Gruppo B (budget cross-package)
```
Invariati (additività): `packages/sertor/tests/test_schema_copilot_hooks.py`,
`test_assets_copilot_parity.py`, `test_hooks_script_copilot.py`, `tests/unit/test_assets_sync.py`;
tutto il codice di produzione (`install_rag.py`, `surfaces.py`, hook `.ps1`, blocchi `.md`,
`sertor_core`).

**Structure Decision**: tre file di test nuovi nelle suite esistenti. **Gruppo A** in `packages/sertor`
(il piano rag è di quel pacchetto). **Gruppo B** in `tests/unit/` root perché cross-package (sertor +
sertor-flow), precedente `test_assets_sync.py`. **Gruppo C** in `packages/sertor` ma in **file
separato** (non in `test_hooks_script_copilot.py`, che ha `pytestmark=skipif(pwsh)` di modulo → il
guard offline non deve essere skippabile).

## Phase 0 — Research (sintesi)
Vedi `research.md`. Tre forche risolte: **DA-D-1** file dedicato + funzione pura `assert_events_present`
(anti-pattern via rimozione del solo evento `PreToolUse`); **DA-D-2** suite root + registro `_BUDGETS`
con discovery esaustiva walk-`Traversable`; **DA-D-3** file dedicato offline, vieta la chiave `decision`
(non `reason`, false-positive breadcrumb), strip commenti riusato da `test_assets_hook_cli_invocation.py`.

## Phase 1 — Design (sintesi)
Vedi `data-model.md` (costanti + guardie) e `contracts/guards.md` (C-A/C-B/C-C + invarianti). Nessuna
entità di dominio; nessuna porta/adapter; nessuna dipendenza nuova.

## Complexity Tracking
*Nessuna violazione costituzionale: tabella vuota.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Nota di processo
`.specify/scripts/powershell/setup-plan.ps1` e `.claude/skills/speckit-plan/SKILL.md` **ASSENTI** nel
repo → parametri (`FEATURE_SPEC`/`IMPL_PLAN`/`SPECS_DIR`/`BRANCH`) ricavati per **convenzione dal
branch** `082-parity-guard-budget` (forma da `081`); nessun hook SpecKit eseguito. **MCP `sertor-rag`
interrogato** (`search_code` sul wiring hook Copilot e sui test di parità) — **nessun errore tool**;
l'ancoraggio puntuale (numeri di riga, conteggi righe) confermato con `Read`/walk del filesystem.
```
