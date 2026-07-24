# Specification Quality Checklist: Contratto di retrieval verso l'agente

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-07-24
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [ ] No [NEEDS CLARIFICATION] markers remain
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

### Esito della validazione (giro 1)

**Un marker [NEEDS CLARIFICATION] resta aperto, deliberatamente.**

- **FR-037** — la soglia quantitativa oltre la quale la metà «non-regressione» del gate si considera
  fallita. Non ha un default ragionevole: dire «nessun calo» rende la capacità quasi certamente non
  consegnabile (qualunque materiale aggiuntivo produce un po' di rumore); dire «tolleranza libera»
  svuota il gate. È una decisione di **scope** — determina se la capacità viene consegnata attiva,
  consegnata opt-in, o non consegnata — e per la regola dei requisiti (SC-002/FR-005) va fissata
  **prima** di eseguire la misura, non dopo averne visto l'esito. Va risolta in `/speckit-clarify`.

### Correzioni applicate durante la validazione

1. **Ambiguità su «qualità della risposta»** — la prima stesura di SC-004/SC-005 diceva «risponde
   meglio», non misurabile. Riformulati sulla **quota di risposte che citano le fonti attese**, che è
   deterministica e verificabile.
2. **Dettaglio implementativo in FR-011** — la prima stesura nominava il meccanismo di derivazione
   della descrizione. Riformulato come proprietà osservabile: «riflette la configurazione attiva».
3. **Edge case mancante** — aggiunta la varianza fra esecuzioni superiore all'effetto misurato: è
   l'esito che rende una misura non conclusiva, e va dichiarato invece che nascosto.
4. **US2 conteneva due storie** — la blindatura delle invarianti e la dichiarazione dell'ambito del
   punteggio sono restate insieme perché condividono lo stesso valore («il contratto dice la verità su
   ciò che consegna») e lo stesso test indipendente; separarle avrebbe prodotto due slice non
   autonome.

### Nota sulla priorità

L'ordine P1 → P3 **inverte** l'ordine di valore: la capacità più preziosa (il flusso strutturale) è
l'ultima. È deliberato e discende dai requisiti: senza la misura di US1, US3 si consegnerebbe sulla
fiducia, e il costo che introduce (materiale aggiuntivo su *ogni* ricerca) è precisamente il danno che
non si vede senza misurarlo.
