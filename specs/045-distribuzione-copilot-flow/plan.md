# Implementation Plan: Distribuzione governance/SDLC su GitHub Copilot (`sertor-flow`)

**Branch**: `045-distribuzione-copilot-flow` | **Date**: 2026-06-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/045-distribuzione-copilot-flow/spec.md`

## Summary

Portare la governance/SDLC di `sertor-flow` su **GitHub Copilot** a parità funzionale, riusando il seam
`--assistant` di FEAT-007. Due leve (vedi `research.md`):
1. **Pivot vendoring → launch-installer (decisione utente):** `sertor-flow` smette di vendorare SpecKit;
   **lancia l'installer di spec-kit** (`specify init --ai <assistant>` via il `CommandRunner` del kit, a
   versione fissata) che deposita la variante per l'assistente (Claude `.claude/...` · Copilot
   `.github/prompts/`+`.github/agents/`; `.specify/` condiviso). Refactor del path **anche per Claude**
   (non-regressione FR-012); fail-fast se spec-kit assente (FR-004).
2. **Superfici Sertor-authored** (`requirements-analyst`, `configuration-manager`, skill `requirements`,
   blocco rituale SDLC): **tradotte** per Copilot come in FEAT-007, riusando il **renderer** che viene
   **spostato nel `sertor-install-kit`** (condiviso `sertor`↔`sertor-flow`, anti-drift/DRY).

Il targeting per-assistente è quello di FEAT-007 (`AssistantId`/`Surface`/`AssistantProfile`, già su
master). La costituzione-starter resta assistant-agnostic.

## Technical Context

**Language/Version**: Python ≥ 3.11 (`sertor-flow`, `sertor-install-kit`).

**Primary Dependencies**: `sertor-install-kit` (stdlib). **Nuova dipendenza a install-time: l'installer
di spec-kit** (CLI `specify`/`uvx`, versione pinnata) — invocato via `CommandRunner` (mockabile). **Nessuna
dipendenza da `sertor-core`** (invariante dura, FR-016).

**Storage**: filesystem del repo ospite.

**Testing**: `pytest` (`packages/sertor-flow/tests`, `packages/sertor-install-kit/tests`); il lancio di
`specify` è **mockato** via `CommandRunner` (nessuna rete nei test). `ruff`.

**Target Platform**: cross-platform (Windows + POSIX); spec-kit emette script `ps`/`sh` (campo
`profile.script`).

**Project Type**: CLI/installer in uv-workspace.

**Performance Goals**: install rapido; il lancio di `specify init` aggiunge il costo del fetch upstream
(una tantum, a versione pinnata).

**Constraints**: install ≠ run; non distruttivo/idempotente; **fail-fast** se spec-kit non
disponibile; segreti non versionati; gap dichiarati; **no dipendenza da `sertor-core`**.

**Scale/Scope**: ~3 categorie di superficie (SpecKit via launch · Sertor-authored tradotte · blocco
SDLC/costituzione) × 2 assistenti.

## Constitution Check

*GATE: Pre-Phase 0 — PASS con 1 deroga giustificata (vedi Complexity Tracking). Re-check post-design in fondo.*

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** `sertor-flow` resta **senza dipendenza da
  `sertor-core`** (FR-016, SC-006); il kit è stdlib. Il lancio di `specify` è una CLI esterna dietro
  `CommandRunner`, non un import. **PASS.**
- [⚠️] **II — Boundary & local-first:** il pivot **reintroduce un fetch a install-time** di spec-kit,
  invertendo la proprietà *offline/dipendenza-zero* del bundle vendorato odierno. **Deroga giustificata**
  (decisione utente; vedi Complexity Tracking): la governance **non è una capacità RAG** (II mira ai
  provider LLM/vector); il fetch è pinnato, deterministico, **fail-fast**, e dietro un boundary
  (`CommandRunner`). **PASS-con-nota.**
- [x] **III — YAGNI & unità piccole:** si **riusa** il seam FEAT-007 e si **sposta** (non duplica) il
  renderer nel kit; si **rimuove** il vendoring SpecKit (meno da mantenere); il launch-helper vive in
  `sertor-flow` (unico consumatore — niente astrazione prematura). **PASS.**
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** spec-kit assente/non eseguibile/layout inatteso →
  errore esplicito azionabile, nessuno stato parziale (FR-004, SC-007). **PASS.**
- [x] **V — Testabilità & misure:** lancio `specify` **mockato** via `CommandRunner`; test di parità
  governance (SC-002), non-regressione Claude (SC-003), no-core-dep (SC-006). **PASS.**
- [x] **VI — Idempotenza & non-distruttività:** install ≠ run preservato (lanciare `specify init`
  **deposita file**, non avvia ingestione); idempotente/non distruttivo (skip-if-present). **PASS.**
- [x] **VII — Leggibilità:** vocabolario `assistant`/`surface`/`launch`/`render`. **PASS.**
- [x] **VIII — Configurabilità centralizzata:** assistente target = parametro (`--assistant`, riuso
  FEAT-007); versione spec-kit pinnata in config, non hardcoded sparso. **PASS.**
- [x] **IX — Osservabilità:** l'install emette `log_event`; l'evento del lancio `specify` registra
  assistente, versione, esito. **PASS.**
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** estende il Principio X all'assistente anche per la
  governance; l'assistente si configura. **PASS (embodiment).**
- [x] **XI — Consumo via vehicles:** N/A diretto (la governance non consuma `sertor_core` a runtime);
  nessun accesso diretto introdotto. **PASS.**

## Project Structure

### Documentation (this feature)

```text
specs/045-distribuzione-copilot-flow/
├── plan.md · research.md · data-model.md · quickstart.md
├── contracts/{cli-assistant,governance-parity,speckit-launch}.md
└── tasks.md   # /speckit-tasks
```

### Source Code (repository root)

```text
packages/sertor-install-kit/src/sertor_install_kit/
├── assistant.py        # riuso (FEAT-007): AssistantId/Surface/AssistantProfile
└── surfaces.py         # SPOSTATO qui da packages/sertor (renderer prompt-file/custom-agent condiviso)

packages/sertor/src/sertor_installer/
└── surfaces.py         # rimosso/reimportato dal kit (aggiorna import; non-regressione FEAT-007)

packages/sertor-flow/src/sertor_flow/
├── install_governance.py  # build_governance_plan parametrico su assistant; rimuove speckit-*/.specify
│                          # dal vendoring; aggiunge lo step di lancio; Sertor-authored via AssistantProfile
├── speckit_launch.py      # NUOVO: lancia `specify init --ai <assistant>` via CommandRunner + verifica + fail-fast
├── profile.py             # GovernanceProfile.assistant già presente → guida targeting e launch
└── assets/
    ├── claude/agents/{requirements-analyst,configuration-manager}.md   # MANTENUTI (Sertor-authored)
    ├── claude/skills/requirements/**                                   # MANTENUTO (Sertor-authored)
    ├── constitution-starter.md · claude-md-block-sdlc.md               # MANTENUTI
    ├── claude/skills/speckit-* · claude/agents/speckit-* · specify/**  # RIMOSSI (ora da launch)
    └── NOTICE · LICENSES/spec-kit-MIT.txt                              # rivalutati (attribuzione segue l'output di spec-kit)

packages/sertor-flow/tests/ · packages/sertor-install-kit/tests/
└── test_install_governance_copilot.py · test_speckit_launch.py · test_governance_parity.py · test_no_vendored_speckit.py
```

**Structure Decision**: refactor di `sertor-flow` + **spostamento del renderer nel kit** (condiviso con
`sertor`). Nessun nuovo pacchetto. Niente che dipenda da `sertor-core`.

## Complexity Tracking

| Violazione | Perché necessaria | Alternativa più semplice scartata perché |
|-----------|------------|-------------------------------------|
| **II — fetch a install-time di spec-kit** (inverte l'offline del bundle vendorato) | Decisione utente (2026-06-15): seguire le varianti per-assistente di spec-kit upstream senza vendorare 2-3 copie; eliminare il debito di doppio/triplo vendoring | *Continuare a vendorare* (offline puro): scartata perché richiede vendorare e mantenere allineate N varianti per-assistente, e non segue automaticamente gli assistenti supportati upstream. Mitigazioni: versione **pinnata**, **fail-fast** esplicito (FR-004), boundary `CommandRunner`, governance ≠ capacità RAG (II mira ai provider) |
