# Implementation Plan: dogfood client-fedele (machinery SpecKit)

**Branch**: `087-a05-dogfood-client-debt` | **Date**: 2026-07-03 | **Spec**: [spec.md](./spec.md)

**Input**: `specs/085-dogfood-client-fedele/spec.md` · Requisiti: `requirements/debito-tecnico/dogfood-client-fedele/requirements.md` · Deriva da E10-FEAT-027.

## Summary

Rendere il dogfood di Sertor un **client SpecKit fedele**: materializzare la machinery (skill `speckit-*` +
`.specify/scripts/`+template) via il percorso d'install in modo **isolato** (senza clobber degli artefatti
Sertor-authored), **gitignorare** la machinery rigenerabile con uno **step di setup documentato**,
**rimuovere** i 9 agenti hand-authored `speckit-*` (residuo pre-pivot 045), e aggiungere una **guardia**
anti-regressione. Approccio tecnico (research D-1/D-2): script di setup dogfood che isola `specify init`
(con overlay UTF-8) e copia solo la machinery rigenerabile, verificando l'invarianza degli artefatti Sertor.
**Zero `sertor-core`.**

## Technical Context

**Language/Version**: PowerShell (script di setup dogfood) + Python 3.11 (test-guardia, stdlib). **Nessun**
codice `sertor-core`.
**Primary Dependencies**: `uvx` + spec-kit `v0.8.18` (pin da `SPECKIT_VERSION`, fonte unica) al setup;
`git` per la guardia (`ls-files`). Nessuna nuova dipendenza di progetto.
**Storage**: filesystem (`.claude/skills/speckit-*`, `.specify/*` — gitignorati) · N/A DB.
**Testing**: `pytest` (guardia di root, offline) + `ruff`.
**Target Platform**: dogfood su Windows (percorso `--script ps`); la materializzazione via `uvx` è
cross-platform (fuori ambito il layout Copilot).
**Project Type**: governance/tooling di repo (non libreria di prodotto).
**Performance Goals**: N/A (setup one-shot, secondi).
**Constraints**: no clobber di `constitution.md`/`plan-template.md`/`feature.json`; no re-vendoring (0 file
machinery tracciati); guardia offline; overlay UTF-8 obbligatorio.
**Scale/Scope**: ~1 script + 1 test + `.gitignore` + rimozione 9 file + 1 sezione doc. Nessun `src/`.

## Constitution Check

*GATE: passato prima di Phase 0; ri-verificato post-design (invariato — la feature non tocca il core).*

- [x] **I — Dipendenze verso l'interno:** **PASS (N/A codice)** — `sertor-core` invariato; nessun import di SDK/CLI.
- [x] **II — Boundary & local-first:** **PASS (N/A)** — nessun adapter/provider toccato.
- [x] **III — YAGNI & unità piccole:** **PASS** — uno script minimo + un test; **evita** il re-vendoring
  (DRY con l'upstream). La complessità aggiunta (script) è giustificata: incapsula la materializzazione
  sicura che i passi manuali sbagliano (UTF-8/isolamento già falliti dal vivo).
- [x] **IV — Errori espliciti:** **PASS** — lo script **fallisce loud** se la materializzazione fallisce o
  se un artefatto Sertor-authored cambierebbe; nessuno stato parziale silenzioso.
- [x] **V — Testabilità & misure:** **PASS** — guardia F.I.R.S.T. offline; criteri SC-1..SC-6 misurabili.
- [x] **VI — Idempotenza & non-distruttività:** **PASS** — re-run idempotente; install≠run; artefatti
  Sertor mai sovrascritti (VI è il cuore del design).
- [x] **VII — Leggibilità:** **PASS** — script/test con nomi di dominio; commenti solo per l'intenzione.
- [x] **VIII — Config centralizzata:** **PASS** — pin spec-kit da fonte unica `SPECKIT_VERSION` (nessun
  hardcode duplicato).
- [x] **IX — Osservabilità:** **PASS (N/A)** — nessun retrieval/index; lo script logga in chiaro cosa copia.
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** **PASS** — la modifica è **dogfood-interna**; gli asset
  **distribuiti** (`sertor-flow`) sono invariati. Lo script di setup è dogfood-local, non un asset ospite →
  non impone assunzioni all'ospite. **Migliora** la fedeltà host (il dogfood esercita il percorso reale).
- [x] **XI — Consumo via vehicles:** **PASS** — il setup usa `specify init` (tool upstream) + copia file;
  **non** importa `sertor_core`. La guardia usa `git`. Nessun bypass dei vehicles.
- [x] **XII — Fail Loud, Fix the Cause:** **PASS (rafforzato)** — si **rimuove** la guardia che *tollerava*
  le skill assenti (A-05) e si elimina la causa (dogfood non fedele) invece di aggirarla; assenza dichiarata
  (doc), non silenziata.
- [x] **Allineamento alla missione:** **PASS (periferico ma allineato)** — non tocca il differenziatore
  code+doc/qualità-retrieval, ma rende **onesto il dogfooding dell'intero metodo** (il dogfood usa davvero
  il percorso ospite). Non è deriva su concern periferici: chiude un debito che minava la fedeltà del dogfood.

**Esito:** 12/12 PASS + missione PASS. **Complexity Tracking: vuoto** (nessuna deroga).

## Project Structure

### Documentation (this feature)
```text
specs/085-dogfood-client-fedele/
├── plan.md          # questo file
├── research.md      # Phase 0 (D-1..D-6)
├── spec.md          # specify
├── quickstart.md    # Phase 1
└── tasks.md         # (speckit-tasks — non creato qui)
```
*(Niente `data-model.md` — nessuna entità di dominio; niente `contracts/` — nessuna interfaccia esterna.)*

### Source Code / repo (paths reali toccati)
```text
scripts/dev/materialize-speckit.ps1     # NUOVO — materializzazione isolata + copia selettiva (D-2)
.gitignore                              # + blocco machinery rigenerabile (D-4)
.claude/agents/speckit-*.md             # RIMOSSI (9 file, D-3)
tests/unit/test_dogfood_speckit_fidelity.py   # NUOVO — guardia (D-5)
CLAUDE.md                               # + step di setup nella sezione Sviluppo (D-6)
# Gitignorati, materializzati localmente (NON committati):
#   .claude/skills/speckit-*/  ·  .specify/{scripts,workflows,integrations}/  ·  .specify/*.json
#   .specify/templates/{checklist,constitution,spec,tasks}-template.md
```
**Structure Decision:** nessun modulo `src/`. La feature vive in tooling di repo (`scripts/dev/`), guardia
(`tests/unit/`), config git (`.gitignore`), governance (`.claude/`) e doc dev (`CLAUDE.md`). `sertor-core`
e gli asset distribuiti `sertor-flow` **invariati**.

## Complexity Tracking
*(vuoto — nessuna violazione da giustificare)*

## Note di processo
- Machinery SpecKit **assente** nel dogfood → questo piano è stato prodotto **per convenzione** (senza
  `setup-plan.ps1`/`spec-template.md`): è precisamente il debito che la feature chiude.
- Git delegato al `configuration-manager`; i commit doc-per-fase.
- **Checkpoint utente** dopo `plan` (richiesto): prima di `tasks`/`implement`. `implement` (materializza,
  cancella agenti, gitignore) resta gated dall'autorizzazione (l'auto-mode esige review per
  integrazione-codice-esterno + cancellazione config).
