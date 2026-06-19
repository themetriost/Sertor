# Feature Specification: Distribuzione corretta della costituzione neutra + rifinitura principi

**Feature Branch**: `058-distribuzione-costituzione`

**Created**: 2026-06-19

**Status**: Draft

**Input**: Deriva da `requirements/debito-tecnico/distribuzione-costituzione/requirements.md`
(decomposizione di FEAT-009, epica `debito-tecnico`). Bug scoperto con **verifica empirica** (host Spike
+ install pulito in dir temp, 2026-06-19): `sertor-flow install` deposita sull'ospite il **template
placeholder di spec-kit** (`# [PROJECT_NAME] Constitution`, `[PRINCIPLE_1_NAME]`), **non** la
costituzione-starter neutra che il pacchetto promette. Causa accertata nel codice: dopo il pivot
launch-installer (FEAT-045), `execute_governance_plan` lancia `specify init` (Step 0) che scaffolda un
`.specify/memory/constitution.md` placeholder; poi il nostro CONFIG `CREATE_IF_ABSENT` fa **skip** perché
il file esiste già → lo starter non arriva mai. Decisioni D1–D3 risolte (replace-if-placeholder +
rifinitura principi).

---

> **Confine vincolante:** ambito = pacchetto **`sertor-flow`** (+ eventuale primitiva condivisa nel
> `sertor-install-kit`). **`sertor-core` INVARIATO**; `sertor-flow` resta **senza dipendenza** da
> `sertor-core`/`sertor`. La costituzione **di Sertor** (questo repo, scritta a mano) NON si tocca. Il fix
> è **non-distruttivo**: sovrascrive **solo** il placeholder di spec-kit, **preserva** una costituzione
> reale già personalizzata dall'ospite. Offline, idempotente, `install ≠ run`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - L'ospite riceve la costituzione neutra, non il placeholder (Priority: P1)

Un utente installa la governance con `sertor-flow install` su un progetto. Oggi, aprendo
`.specify/memory/constitution.md`, trova un **template vuoto** (`[PROJECT_NAME]`, `[PRINCIPLE_1_NAME]`,
commenti `<!-- Example: … -->`) da compilare a mano: la costituzione-starter curata che il pacchetto
dovrebbe fornire non c'è. Con questa storia l'ospite riceve la **costituzione-starter neutra** —
principi di ingegneria generali pronti all'uso, personalizzabili.

**Why this priority**: È il valore terminale e la causa-radice del bug verificato sul campo. Senza il
fix, la promessa «`sertor-flow` distribuisce una costituzione sensata» è falsa per **ogni** ospite.

**Independent Test**: Installare la governance in una dir pulita (con `specify init` simulato/reale che
deposita il placeholder) e verificare che `.specify/memory/constitution.md` finale sia lo starter neutro
(0 occorrenze di `[PROJECT_NAME]`/`[PRINCIPLE_1_NAME]`).

**Acceptance Scenarios**:

1. **Given** un install governance su host pulito in cui `specify init` ha depositato il placeholder
   spec-kit, **When** l'install completa, **Then** `.specify/memory/constitution.md` è lo starter neutro.
2. **Given** un host **senza** `.specify/` (nessuna costituzione pre-esistente), **When** si installa,
   **Then** lo starter neutro è depositato comunque (create-if-absent classico, nessuna regressione).
3. **Given** un host in cui l'utente ha già una **costituzione reale** personalizzata, **When** si
   installa/aggiorna, **Then** la sua costituzione è **preservata byte-per-byte** (non sovrascritta).

---

### User Story 2 - Lo starter neutro è completo e generico (Priority: P2)

Un manutentore di un progetto-ospite legge la costituzione-starter ricevuta e trova un insieme di
principi **generici e completi**, senza riferimenti al dominio di Sertor (RAG, host-agnosticità del
framework, veicoli). Con questa storia lo starter include anche i kernel generici finora mancanti
(consumo via interfacce stabili; dettagli rimpiazzabili / no lock-in) e una nota di leggibilità allineata.

**Why this priority**: Una volta che lo starter **arriva** (US1), vale renderlo il più utile possibile.
È P2 perché dipende da US1 (uno starter che non si distribuisce non serve a nessuno).

**Independent Test**: Ispezionare lo starter e verificare la presenza dei due nuovi principi e l'assenza
di principi Sertor/RAG-specifici.

**Acceptance Scenarios**:

1. **Given** lo starter neutro, **When** lo si legge, **Then** contiene un principio «Consume through
   stable interfaces, not internals» e uno «Replaceable details / no vendor lock-in».
2. **Given** lo starter neutro, **When** lo si cerca, **Then** NON contiene principi Sertor-specifici
   (host-agnosticità del framework, veicoli `sertor-rag`, motori RAG, hit@k/MRR).
3. **Given** lo starter aggiornato, **When** se ne legge l'intestazione/versione, **Then** la versione è
   bumpata (semver) e resta la nota «personalizza con `speckit-constitution`».

---

### User Story 3 - La regressione non rientra (Priority: P2)

Un manutentore modifica il flusso governance. Con questa storia una **guardia offline** fallisce se
l'ospite tornasse a ricevere il placeholder invece dello starter, o se una costituzione reale venisse
sovrascritta.

**Why this priority**: Il bug è passato perché nessun test verificava il *contenuto effettivo* della
costituzione depositata. Senza guardia il difetto può rientrare silenzioso.

**Independent Test**: Eseguire la guardia su due fixture (placeholder → atteso starter; costituzione
reale → attesa preservata) e verificarne il PASS; rompere il fix e verificare il FAIL.

**Acceptance Scenarios**:

1. **Given** fixture = placeholder spec-kit, **When** si esegue il flusso e la guardia, **Then** il
   risultato è lo starter neutro (PASS).
2. **Given** fixture = costituzione reale, **When** si esegue, **Then** è preservata (PASS).
3. **Given** il fix rimosso/rotto, **When** si esegue la guardia, **Then** almeno un controllo fallisce.

---

### Edge Cases

- **`specify init` fallisce / layout mancante** → osservato in ambiente dev (`layout_missing`). Il fix
  della costituzione NON deve dipendere dall'esito di `specify init`: se il placeholder c'è, lo si
  sostituisce; se non c'è, create-if-absent.
- **Costituzione reale che contiene per caso `[…]`** → usare sentinelle specifiche del template spec-kit
  (`[PROJECT_NAME]`, `[PRINCIPLE_1_NAME]`); in dubbio **preservare** (fail-safe non-distruttivo).
- **Re-run / upgrade** → idempotente: una seconda esecuzione su uno starter già depositato non cambia
  nulla; un placeholder residuo viene portato allo starter.
- **Spec-kit cambia i placeholder upstream** → guardia che fallisce se il template vendorato cambia forma.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Dopo `specify init`, se `.specify/memory/constitution.md` è riconosciuto come **placeholder
  di spec-kit**, il sistema MUST sovrascriverlo con lo **starter neutro**.
- **FR-002**: Se la costituzione è **reale** (non placeholder), il sistema MUST **preservarla** invariata
  (install e upgrade).
- **FR-003**: Il rilevamento del placeholder MUST essere **deterministico** (sentinelle del template
  spec-kit), offline, senza LLM né rete.
- **FR-004**: Se non esiste alcuna costituzione, il sistema MUST depositare lo starter (create-if-absent),
  senza regressioni del deposito attuale.
- **FR-005**: L'**upgrade** governance MUST applicare la stessa semantica replace-if-placeholder.
- **FR-006**: Lo starter neutro MUST includere i principi **«Consume through stable interfaces, not
  internals»** e **«Replaceable details / no vendor lock-in»**.
- **FR-007**: Il principio di leggibilità dello starter SHOULD riflettere la chiosa guard-clause/early-
  return vs SESE.
- **FR-008**: Lo starter MUST NOT contenere principi Sertor/RAG-specifici; la sua **versione** MUST essere
  bumpata e la nota d'intestazione preservata.
- **FR-009**: Una **guardia offline** MUST attestare: placeholder → starter; costituzione reale →
  preservata; e fallire se la regressione rientra.
- **FR-010**: Le suite esistenti MUST restare verdi; `sertor-flow` MUST restare senza dipendenza da
  `sertor-core`/`sertor`.

### Key Entities

- **Costituzione-starter neutra**: l'asset `constitution-starter.md` del pacchetto `sertor-flow`, insieme
  di principi generici, destinato a `.specify/memory/constitution.md` sull'ospite.
- **Placeholder spec-kit**: il template `.specify/memory/constitution.md` che `specify init` scaffolda
  (`[PROJECT_NAME]`/`[PRINCIPLE_1_NAME]`/`<!-- Example: -->`), da sostituire.
- **Costituzione reale dell'ospite**: una costituzione già personalizzata, da preservare.
- **Sentinella di placeholder**: i marcatori che distinguono il template spec-kit da una costituzione
  reale, base del rilevamento deterministico.
- **Guardia di distribuzione**: la suite offline che verifica il contenuto effettivo depositato.

## Success Criteria *(mandatory)*

- **SC-001**: Dopo `sertor-flow install` su host pulito, `.specify/memory/constitution.md` è lo starter
  neutro (oggi: il placeholder spec-kit).
- **SC-002**: Una costituzione reale pre-esistente è preservata byte-per-byte dopo install/upgrade.
- **SC-003**: Lo starter contiene i due nuovi principi e **0** principi Sertor/RAG-specifici.
- **SC-004**: Guardia offline verde; suite `sertor-flow`/`kit`/`sertor` verdi; `sertor-flow`↛`sertor-core`.
- **SC-005 (empirico)**: install pulito in dir temp → la costituzione depositata è lo starter neutro.

## Assumptions

- D1–D3 risolte a monte (requirements). Replace-if-placeholder confermato dall'utente (2026-06-19).
- `specify init` può fallire il layout in alcuni ambienti: il fix non vi dipende.
- Confine ai pacchetti installer; `sertor-core` invariato; `sertor-flow` senza dipendenza dal core.
- La costituzione di Sertor (questo repo) è scritta a mano e fuori ambito.
