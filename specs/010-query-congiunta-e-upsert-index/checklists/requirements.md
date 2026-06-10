# Specification Quality Checklist: Query congiunta multi-collezione & `upsert-index` in CLI

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-06-10
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain — **2 marker deliberati** (DA-1 policy di fusione
      con provider eterogenei; DA-4 come il sistema individua la seconda collezione), da sciogliere
      in `/speckit-clarify` su richiesta esplicita dell'utente — **sciolti in clarify 2026-06-10**
- [x] Requirements are testable and unambiguous (salvo i 2 marker di cui sopra)
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

- I 2 marker [NEEDS CLARIFICATION] (FR-007/DA-4 e edge case "spazi vettoriali non confrontabili"/DA-1,
  richiamato da FR-009) sono **intenzionali**: l'utente ha chiesto di porre le domande nella fase
  `/speckit-clarify`, non in specify. Le restanti domande a monte (DA-2, DA-3, DA-5, DA-6) sono
  assorbite come assunzioni/decisioni di piano e non bloccano la spec.
- Requisiti a monte: `requirements/sertor-core/query-congiunta-e-indice/requirements.md` (EARS,
  gruppi A/B). Mappatura: FR-001..009 ← REQ-A1..A9; FR-010..017 ← REQ-B1..B8; FR-018 nuovo (emerso
  dagli edge case: sommario vuoto/multilinea).
