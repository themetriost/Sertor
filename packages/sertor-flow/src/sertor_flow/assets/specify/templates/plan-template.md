# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]

**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]

**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]

**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]

**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]

**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]

**Project Type**: [e.g., library/cli/web-service/mobile-app/compiler/desktop-app or NEEDS CLARIFICATION]

**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]

**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]

**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Gate derivati dalla costituzione (`.specify/memory/constitution.md`, v1.1.1). Marcare PASS/FAIL;
ogni FAIL va risolto o giustificato in "Complexity Tracking".

- [ ] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** il design del core non importa SDK di
  provider (LLM/embeddings/vector store) né la CLI; gli adapter dipendono dalle astrazioni del core;
  il wiring sta in un componente main/config. Il core è esercitabile con provider mock, senza cloud/CLI.
- [ ] **II — Boundary & local-first:** ogni dipendenza esterna è dietro un'astrazione di Sertor;
  scelta locale↔cloud guidata da config; vector store solo dove la modalità lo richiede.
- [ ] **III — YAGNI & unità piccole:** niente astrazioni/dipendenze senza evidenza presente; SRP/DRY;
  dipendenze pesanti isolabili.
- [ ] **IV — Errori espliciti (NON-NEGOZIABILE):** error handling a eccezioni di dominio; niente
  `None` silenzioso né stato parziale/corrotto.
- [ ] **V — Testabilità & misure:** test F.I.R.S.T. previsti; core testabile con mock; qualità
  retrieval misurata (hit@k/MRR, baseline=prototipo).
- [ ] **VI — Idempotenza & non-distruttività:** re-run stabile (ID stabili); install≠run; nessuna
  sovrascrittura silenziosa.
- [ ] **VII — Leggibilità:** naming di dominio (retrieve/rank/fuse/…); commenti solo per l'intenzione.
- [ ] **VIII — Configurabilità centralizzata:** scelte (provider/backend/parametri) via config unica,
  nessun default hardcoded.
- [ ] **IX — Osservabilità:** retrieval e creazione embeddings/indicizzazione emettono log strutturati
  (operazione, provider, conteggi, tempi, errori); nessun segreto nei log.
- [ ] **X — Host-agnostico (NON-NEGOZIABILE):** la capacità/skill non incorpora assunzioni dell'ospite
  (percorsi fissi, nomi di dominio, struttura cartelle); ciò che varia per ospite sta in config, non nel
  corpo. Test: gira su un progetto-ospite diverso (code+doc / solo-doc / solo-code) senza modifiche al
  corpo. Il dogfooding non giustifica deroghe.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
