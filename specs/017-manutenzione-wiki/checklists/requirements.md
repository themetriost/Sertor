# Specification Quality Checklist: Manutenzione wiki deterministica (move · reconcile · collect+status)

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-06-13
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- 15 FR mappati sui REQ EARS della fonte (gruppi B: REQ-010..015; C: REQ-020..027 + REQ-021; D:
  REQ-028 Could) + 2 trasversali (forward-compat, host-agnostico). Gruppi E/F **fuori ambito**
  (già consegnati, PR #27/#28/#29); gruppo A **Won't** (D1). Zero NEEDS CLARIFICATION: i requisiti
  erano già elicitati e le decisioni D1..D4 chiuse.
- Tensione di vocabolario accettata (come per le feature 011/015/016): i nomi dei contratti JSON
  versionati (`wiki.move/1`, `wiki.reconcile/1`, `wiki.collect/1`) e i flag (`--dry-run`) sono la
  **superficie-contratto** del comando — il valore della feature — non un leak implementativo.
- Una sola assunzione di design da confermare in plan/clarify: la **fonte del "successore"** di una
  pagina superata (campo frontmatter dedicato vs banner nel corpo); documentata in Assumptions, non
  bloccante.
