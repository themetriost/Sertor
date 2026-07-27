# Specification Quality Checklist: Ancora derivata per la rilevazione del lavoro non registrato

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-07-27
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

**Iterazione 1 → 2 (correzioni applicate).** La prima stesura falliva tre voci, tutte per lo stesso
vizio: descriveva la **soluzione** invece del **bisogno**.

- *No implementation details* — FR e criteri nominavano `git`, `scan.py`, `mtime`, `wiki.scan/1`,
  `gh pr merge`. Riscritti in termini di capacità («controllo di versione», «approssimazione
  temporale», «identificativo di schema», «consegna»). I riferimenti tecnici puntuali restano solo
  in **Assumptions** (A-7) e nel campo **Input**, dove sono provenienza, non design.
- *Success criteria technology-agnostic* — SC-002 diceva «anche dopo `touch` sui file»; ora «dopo aver
  alterato gli orari di modifica», che è la stessa verifica senza il comando.
- *Testable and unambiguous* — FR-004 non diceva **quando** una registrazione non consegnata valga.
  Aggiunto il vincolo del giorno corrente + assunzione **A-2** che ne porta il motivo.

**Assunzione da confermare in `clarify` (non è un blocco, è una scelta con un'alternativa reale):**
**A-2** — una registrazione presente nell'albero di lavoro ma non consegnata vale **solo se è del
giorno corrente**. È la voce con più conseguenze pratiche: decide se il gate si può soddisfare in un
turno (sì) e se una voce dimenticata lo può spegnere a tempo indeterminato (no). La scelta è coerente
col gate gemello del merge, che già usa «la partizione di oggi» come criterio — ma l'alternativa
(qualunque registrazione non consegnata vale) è difendibile ed è più permissiva.

**Vincolo di compatibilità da non perdere di vista nel `plan`:** FR-012. I due consumatori installati
si **disattivano** se l'identificativo di schema non corrisponde: è un fail-open, quindi un errore qui
non si manifesterebbe come guasto ma come **gate silenziosamente assente**. È esattamente la firma dei
difetti che questa feature chiude, e va coperto da una verifica anti-regressione — non dall'attenzione.
