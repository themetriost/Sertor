# Specification Quality Checklist: Il server MCP funziona su entrambe le linee dell'SDK

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-13
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

- [~] All functional requirements have clear acceptance criteria — **vedi nota 2**
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

Due riserve dichiarate invece di essere spuntate. *Una checklist tutta verde ottenuta allentando la
lettura è una guardia che non poteva fallire — il difetto che questo progetto ha già pagato tre volte
([[guardia-verde-non-e-una-misura]]).*

**Nota 1 — «no implementation details»: cosa è dominio e cosa sarebbe implementazione.** La spec nomina
*SDK*, *linea/major/minor*, *lock*, *protocollo*, *trasporto*. Non sono scelte d'implementazione: sono
**il problema**, e una spec che li evitasse non descriverebbe niente. Ciò che è stato deliberatamente
tenuto fuori, e appartiene al `plan`: i nomi delle classi delle due linee, il file e le righe da
toccare, la forma del meccanismo di selezione (un `try/except` sull'import o altro), i nomi dei tipi
d'errore, la struttura del test end-to-end, la forma del job di verifica su due linee.

**Nota 2 — due requisiti sono presidiati da verifiche esistenti, non da scenari nuovi.** FR-008
(semantica del riscaldamento e dell'autodiagnosi all'avvio) e FR-009 (nomi e campi degli eventi di
osservabilità) sono proprietà **da non rompere**, già coperte dalla batteria di test attuale sul server.
Non hanno uno scenario d'accettazione dedicato, e sarebbe disonesto spuntare la voce come se lo
avessero. Il `plan` deve dichiarare **quali test esistenti** li presidiano: se non ne esistono, sono
requisiti scoperti e servono verifiche nuove.

**Nota 3 — un criterio di successo non è verificabile dal dogfood.** SC-005 (un ospite con la major già
risolta guarisce aggiornando solo Sertor) richiede un **host usa-e-getta**: l'ambiente del dogfood segue
l'ultimo commit e non ri-risolve mai le dipendenze, quindi non può esercitare quel salto
([[dogfood-fidelity]]). Il `plan` deve dire **dove** SC-005 viene misurato, altrimenti resta un criterio
dichiarato e mai calcolato.

**Nota 4 — il perimetro del *non misurato* è dichiarato.** Cancellazione, timeout, risultati grandi e
concorrenza sulla linea nuova non sono stati misurati e la spec lo dice (Edge Cases, Assumptions). Non è
una lacuna della spec: è il limite della conoscenza attuale, messo dove si legge.
