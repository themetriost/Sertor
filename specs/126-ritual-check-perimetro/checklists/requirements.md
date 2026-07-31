# Specification Quality Checklist: il perimetro dello step è anche ciò che non hai ancora consegnato

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-07-30
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

**Iterazione 1 → 2 (correzioni applicate).** La prima stesura falliva tre voci, tutte per la stessa
ragione: la spec era scritta *nel vocabolario dell'implementazione* invece che in quello di chi usa la
capacità.

- *No implementation details* — la stesura iniziale nominava `git diff`, `--porcelain -z -uall`,
  `ritual_check.py:259` e i nomi delle funzioni. Riscritta in termini di **lavoro consegnato / non
  consegnato** e **interrogazioni al controllo di versione**. Le coordinate tecniche restano dove
  competono: nei requisiti EARS a monte e nel piano a valle.
- *Success criteria technology-agnostic* — SC-006 diceva «due invocazioni `git`»; ora dice «due
  interrogazioni al controllo di versione», che è misurabile senza nominare lo strumento.
- *Written for non-technical stakeholders* — le tre user story sono state riscritte in prima persona da
  chi chiude uno step, non dal punto di vista del modulo.

**Zero `[NEEDS CLARIFICATION]`, e non per comodità.** Le tre domande aperte lasciate dai requisiti sono
state **risolte con motivazione** e registrate in *Assumptions*, perché nessuna era un bivio reale:

1. *Opzione per restringere al solo consegnato?* → **no**, nessuno l'ha richiesta; sarebbe superficie
   non giustificata, e resta additiva se emergerà un caso d'uso.
2. *Collegamenti «nuovi» per una pagina mai consegnata?* → **tutti nuovi**, che è il comportamento
   corretto; la decisione è **dichiararlo** invece di ereditarlo tacitamente.
3. *Dichiarare il perimetro sempre o solo se composito?* → **sempre**: «solo se composito»
   reintrodurrebbe un silenzio nel caso semplice, cioè esattamente la classe del difetto che la feature
   chiude.

**Una nota su SC-002, che è il criterio più severo.** Non chiede «meno falsi positivi» ma **zero**, su
un caso minimo di due pagine — un bersaglio che si può mancare, non un'affermazione che si può sempre
dichiarare soddisfatta.
