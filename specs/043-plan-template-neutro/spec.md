# Feature Specification: Plan-template neutro nel bundle `sertor-flow`

**Feature Branch**: `043-plan-template-neutro`

**Created**: 2026-06-15

**Status**: Draft

**Input**: Gruppo **D** di `requirements/sertor-core/enforcement-principio-xi/requirements.md`
(REQ-D1..D3; CS-5). Epica `sertor-cli`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - L'ospite riceve un plan-template coerente con la propria costituzione (Priority: P1)

Come ospite che installa la governance via `sertor-flow`, voglio che il `plan-template` ricevuto faccia
derivare i gate del Constitution Check **dalla mia costituzione** (lo starter neutro), non dai gate
costituzionali Sertor-specifici, così che il metodo sia coerente sul mio progetto (non-RAG incluso).

**Why this priority**: oggi il bundle vendora il `plan-template` *gated* del dogfood di Sertor (11
gate, incl. XI CLI/MCP) ma spedisce una costituzione *neutra* → incoerenza: l'ospite ha un checklist
inchiodato ai principi di Sertor mentre la sua costituzione dice altro.

**Independent Test**: ispezionare il `plan-template.md` nel bundle e verificare che la sezione
Constitution Check è il **placeholder generico** (gate derivati dalla costituzione), **0** gate
Sertor-specifici (nessun riferimento a `sertor_core`/`SERTOR_ENGINE`/vehicles/XI). Il
`plan-template.md` del dogfood di Sertor resta **gated** (invariato).

**Acceptance Scenarios**:
1. **Given** il bundle `sertor-flow`, **When** ne ispeziono `assets/specify/templates/plan-template.md`,
   **Then** è la versione generica upstream (placeholder "gates derived from constitution"), senza i
   gate Sertor.
2. **Given** il dogfood di Sertor, **When** ispeziono `.specify/templates/plan-template.md`, **Then** è
   invariato (gated, 11 principi).
3. **Given** la guardia anti-drift del bundle, **When** gira, **Then** **non** segnala drift su
   `plan-template.md` (è intenzionalmente diverso dal dogfood → escluso dal confronto, come gli script).

### Edge Cases
- Il sync bundle↔dogfood NON deve propagare/sovrascrivere il `plan-template` (in nessuna direzione):
  i due sono intenzionalmente diversi.
- Gli altri template (`spec`/`tasks`/`checklist`/`constitution`-template) restano sincronizzati
  (sono generici in entrambi).

## Requirements *(mandatory)*

- **FR-D1**: Il bundle `sertor-flow` MUST spedire un `plan-template.md` **generico** (Constitution Check
  con gate derivati dalla costituzione dell'ospite), proveniente dall'**upstream spec-kit** (stessa
  logica di provenienza già usata per gli script, F3).
- **FR-D2**: Il `plan-template.md` del dogfood di Sertor (`.specify/templates/`) MUST restare invariato
  (gated, 11 principi) per l'uso interno.
- **FR-D3**: Il `plan-template.md` MUST essere **escluso** dal sync e dal confronto anti-drift
  bundle↔dogfood (intenzionalmente divergente), mentre gli altri template restano confrontati.

## Success Criteria *(mandatory)*

- **SC-1**: il `plan-template.md` del bundle non contiene gate Sertor-specifici (0 occorrenze di
  `sertor_core`/`SERTOR_ENGINE`/"Consumo via vehicles"/Principio-numerati); contiene il placeholder
  generico.
- **SC-2**: il `plan-template.md` del dogfood è invariato.
- **SC-3**: la guardia anti-drift del bundle resta verde (plan-template escluso; altri template
  confrontati); suite kit + sertor-flow verdi.

## Assumptions
- Fonte upstream: `ExternalRepos/spec-kit/templates/plan-template.md` (pinned 0.8.18, placeholder
  `[Gates determined based on constitution file]`).
- Meccanismo (esclusione nel sync) = materia del plan.
- Fuori ambito: gruppi A/B/C (già su master); generazione dinamica dei gate dalla costituzione ospite
  (oltre il placeholder).
