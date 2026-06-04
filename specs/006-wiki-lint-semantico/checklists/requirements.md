# Specification Quality Checklist: Lint semantico del wiki (scope ampliato US3/US4-scrittura/US5)

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-06-04
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) — *eccezione consapevole: spec brownfield di libreria; nomina porte/entità coerenti col resto della feature, dettagli di firma rinviati a plan/contracts*
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders — *per quanto possibile in una feature di tooling interno*
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded — *P1 fatto vs P2 in scope vs fuori-ambito esplicitati*
- [x] Dependencies and assumptions identified — *dipendenza FEAT-009 (D1) e assunzioni su watermark/mappa/override*

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification — *vedi eccezione consapevole sopra*

## Notes

- Finding dell'analyze incorporati: U1 (contratti → rinviati a plan/contracts), D1 (FEAT-009 → solo
  fallback, dichiarato in spec), C1 (GitPort + gate in CLI/hook → FR-017, confine architetturale),
  U2 (watermark path fissato → FR-018), U3 (mappa entità↔pagine derivata da `sources:`/backlink → US3.4),
  U4 (override come parametro esplicito + record → Assumptions/US5.4), A1 (gate = `report.ok`→exit≠0 → US5.3).
- Le firme esatte delle nuove funzioni (incrementale, `apply_fixes`, `GitPort`, gate) vanno definite in
  `plan.md` + `contracts/` nella fase successiva (`/speckit-plan`).
