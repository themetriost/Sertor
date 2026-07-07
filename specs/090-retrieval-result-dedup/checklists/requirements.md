# Specification Quality Checklist: Dedup dei risultati near-duplicate nel retrieval

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-07-07
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) — *nota: nomi come `HybridEngine.retrieve`/`SERTOR_DEDUP` citati come vincoli/punti d'ancoraggio reali (dove la feature deve inserirsi), non come «come» implementativo; il «come» resta al plan*
- [x] Focused on user value and business needs (top-k distinto → doc canonici non sepolti; leva sulla missione code+doc)
- [x] Written for the maintainer/agent stakeholder
- [x] All mandatory sections completed (Scenarios, Requirements, Success Criteria)

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain (il brief era dettagliato; i default sono in Assumptions)
- [x] Requirements are testable and unambiguous (FR-001..008 con acceptance/independent test)
- [x] Success criteria are measurable (SC-001..005: 0 coppie duplicate, gate verde, hit@3 ≥ 0.75, no regressione search_code)
- [x] Success criteria are technology-agnostic (esiti osservabili: top-k distinto, metriche eval, bypassabilità)
- [x] All acceptance scenarios are defined (2 user story con Given/When/Then + no-op)
- [x] Edge cases are identified (boilerplate, pool esaurito, near-dup fuori ambito, reranker, determinismo)
- [x] Scope is clearly bounded (in: dedup esatto pre-cut, config, host-agnostico; out: fuzzy, exclude-from-corpus, MMR)
- [x] Dependencies and assumptions identified (normalizzazione, duplicazione-per-lo-più-esatta, punto d'inserimento, confine dev↔dogfood)

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows (US1 dedup, US2 config/host-agnostico)
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification (livello «cosa/perché»; il «come» = plan)

## Notes

- **Constitution Check** formale (12 principi + missione) all'`/speckit-plan`. Principi in gioco già anticipati:
  V (misura del lift), VI (determinismo/no-op), VIII (config `SERTOR_DEDUP`), IX (osservabilità rimossi),
  X (host-agnostico), e la **missione** (rafforza `search_docs`, la metà debole della fusione code+doc).
- Il **fuzzy near-duplicate** è *Out of Scope* e va **promosso** al backlog E5 al plan/tasks (non sepolto).
- Prossimo: `/speckit-plan` (con conferma del punto d'inserimento e della normalizzazione).
