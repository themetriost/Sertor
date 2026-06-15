# Feature Specification: Consumo sicuro per costruzione (auto-wire dei concern nel composition root)

**Feature Branch**: `041-consumo-sicuro-vehicles`

**Created**: 2026-06-15

**Status**: Draft

**Input**: Gruppo A di `requirements/sertor-core/enforcement-principio-xi/requirements.md`
(REQ-A1..A5; CS-1/CS-2; NFR-1/2/5). Deriva dall'epica `sertor-core`. Realizza il **Principio XI**
(costituzione v1.2.0) "per costruzione".

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ogni percorso d'ingresso applica i concern trasversali (Priority: P1)

Come sviluppatore/operatore che usa il core, voglio che i concern trasversali (attivazione
osservabilità, configurazione centralizzata, avvolgimento errori al boundary) siano applicati **in
modo uniforme da qualunque percorso d'ingresso supportato** (CLI, MCP, factory `build_*`), così che
un'operazione non venga mai eseguita "a metà servizio" a seconda di come è stata invocata.

**Why this priority**: è la causa-radice del gap verificato — oggi un re-index via factory diretta
**non** viene tracciato in telemetria perché l'attivazione dell'osservabilità vive solo nei
consumatori CLI/MCP. È il valore centrale (rende il Principio XI vero "per costruzione").

**Independent Test**: con l'osservabilità abilitata in configurazione, eseguire un'operazione di
indicizzazione **attraverso la factory** e verificare che l'evento corrispondente è persistito nello
store — esito identico a quando la stessa operazione passa per la CLI.

**Acceptance Scenarios**:
1. **Given** osservabilità abilitata, **When** un'operazione di indicizzazione è eseguita via factory
   `build_*`, **Then** l'evento è persistito (come accade via CLI/MCP).
2. **Given** un'operazione che attraversa il boundary, **When** un componente sottostante fallisce,
   **Then** l'errore è avvolto in modo uniforme indipendentemente dal percorso d'ingresso.

---

### User Story 2 - La libreria resta importabile e testabile (Priority: P2)

Come manutentore, voglio che `sertor_core` resti **importabile** e che i test esercitino libreria e
funzioni **direttamente**, così che il Principio I (la libreria è il prodotto, testabile in
isolamento) sia preservato e i test non debbano passare per i vehicles.

**Why this priority**: vincolo cardine — l'enforcement "per costruzione" non deve trasformarsi in un
divieto d'import che romperebbe la testabilità.

**Independent Test**: importare `sertor_core` e invocare le factory/funzioni in un test diretto;
l'intera suite passa senza usare CLI/MCP.

**Acceptance Scenarios**:
1. **Given** un test unitario/integrazione, **When** invoca direttamente libreria e factory, **Then**
   funziona senza errori e senza richiedere un vehicle.

---

### User Story 3 - Opt-in e nessuna regressione (Priority: P2)

Come consumatore esistente (CLI/MCP) o come ambiente senza osservabilità, voglio che il
comportamento **non cambi**: l'osservabilità resta **opt-in** (default off, zero overhead) e i
consumatori che la attivano già non si rompono.

**Why this priority**: il cablaggio uniforme non deve accendere l'osservabilità da solo né duplicare
l'attivazione di chi già la fa.

**Independent Test**: con osservabilità disabilitata (default), eseguire un'operazione via qualunque
percorso e verificare che **nessuno** store viene creato e nessun evento persistito; con CLI/MCP che
attivano l'osservabilità, verificare che l'attivazione resta idempotente (nessun doppio effetto).

**Acceptance Scenarios**:
1. **Given** osservabilità disabilitata (default), **When** un'operazione è eseguita via qualunque
   percorso, **Then** non viene creato alcuno store e non è persistito alcun evento (comportamento
   odierno invariato).
2. **Given** un consumatore CLI/MCP che attiva l'osservabilità, **When** l'operazione gira, **Then**
   l'attivazione è idempotente (nessuna doppia attivazione, nessun errore).

---

### Edge Cases
- Osservabilità disabilitata → cablaggio no-op, zero overhead, nessuno store.
- CLI/MCP che attivano già l'osservabilità → attivazione idempotente (no doppio attach).
- Factory usata dentro un test → funziona; nessun effetto collaterale forzato che renda il test non
  isolato.
- Nessuna dipendenza del core verso CLI/MCP introdotta dal cablaggio (resta nel composition root).

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: Il composition root MUST cablare i concern trasversali (attivazione osservabilità,
  configurazione centralizzata, avvolgimento errori al boundary) così che **qualunque percorso
  d'ingresso supportato** (CLI, MCP, factory `build_*`) li applichi in modo uniforme.
- **FR-002**: Quando un'operazione di indicizzazione/retrieval è eseguita via factory `build_*` con
  osservabilità abilitata, il sistema MUST persistere l'evento corrispondente (chiusura del gap).
- **FR-003**: Il sistema MUST mantenere `sertor_core` importabile e testabile in isolamento; gli
  unit/integration test POSSONO invocare libreria e funzioni direttamente.
- **FR-004**: Se l'osservabilità è disabilitata in configurazione, il cablaggio MUST restare no-op
  (nessuno store, nessun evento, zero overhead) — comportamento di default odierno preservato.
- **FR-005**: L'attivazione dei concern MUST essere idempotente: i consumatori CLI/MCP che già la
  effettuano non devono subire doppia attivazione né errori.
- **FR-006**: Il cablaggio MUST NOT introdurre dipendenze del core verso la CLI o il server MCP (resta
  nel composition root; le dipendenze puntano verso l'interno — Principio I/NFR-1).
- **FR-007** *(Should)*: La superficie pubblica del pacchetto SHOULD documentare le factory come
  ingresso naturale; il **restringimento** degli export di `__init__` è **rinviato** (fuori da questo
  taglio).

### Key Entities
- **Composition root / factory `build_*`**: l'unico punto che cabla i concern trasversali; ingresso
  programmatico al core.
- **Concern trasversali**: attivazione osservabilità, configurazione centralizzata, avvolgimento
  errori al boundary — applicati uniformemente.

## Success Criteria *(mandatory)*

### Measurable Outcomes
- **SC-001**: **0** percorsi d'ingresso supportati bypassano i concern trasversali (verifica: re-index
  via factory con osservabilità abilitata → evento persistito, come via CLI).
- **SC-002**: L'intera suite (root + tutti i pacchetti) resta verde; `sertor_core` importabile e i
  test diretti passano (Principio I preservato).
- **SC-003**: Con osservabilità disabilitata (default), **0** store creati e **0** eventi persistiti
  da qualunque percorso (comportamento odierno invariato).
- **SC-004**: I test esistenti che verificano il wiring osservabilità dei consumatori
  (`test_index_wires_observability`, `test_main_wires_observability`) restano validi (nessuna
  regressione).

## Assumptions
- Il meccanismo concreto (quali `build_*` toccare, come fattorizzare l'attivazione oggi in
  `enable_observability`) è materia del **plan**; qui solo COSA/PERCHÉ.
- Osservabilità governata da `SERTOR_OBSERVABILITY` (default off), invariata.
- Fuori ambito: gruppi B (istruzione installer), C (hook), D (plan-template neutro) della stessa
  capacità; il restringimento di `__init__` (Should rinviato).
