# Feature Specification: Enforcement lato ospite del consumo via vehicles (istruzione + hook)

**Feature Branch**: `042-enforcement-vehicles-ospite`

**Created**: 2026-06-15

**Status**: Draft

**Input**: Gruppi **B** e **C** di `requirements/sertor-core/enforcement-principio-xi/requirements.md`
(REQ-B1..B3, REQ-C1..C4; CS-3/CS-4). Epica `sertor-cli`. Forma **host-facing** del Principio XI
(istruzione + vincolo), distinta dai gate costituzionali di Sertor.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - L'ospite è istruito a usare i vehicles (Priority: P1)

Come maintainer che installa la capacità RAG su un repo, voglio che l'agente LLM dell'ospite **sappia**
di dover usare la capacità via `sertor-rag` (CLI) o i tool MCP e di **non** importare `sertor_core` nei
propri script, così che non bypassi i concern trasversali (osservabilità/config/errori).

**Why this priority**: oggi `sertor install rag` non deposita alcuna istruzione d'uso → l'agente
ospite non ha modo di sapere la regola. È il livello più economico ed efficace (istruzione).

**Independent Test**: eseguire `sertor install rag` su un repo pulito e verificare che il `CLAUDE.md`
contiene un blocco a marker `SERTOR:RAG-USAGE` con l'istruzione (usa CLI/MCP, non importare la
libreria); una seconda esecuzione non duplica il blocco; il resto del `CLAUDE.md` è preservato.

**Acceptance Scenarios**:
1. **Given** un repo senza il blocco, **When** gira `sertor install rag`, **Then** il `CLAUDE.md`
   riceve il blocco `SERTOR:RAG-USAGE` (creato se il file non esiste).
2. **Given** un `CLAUDE.md` che contiene già blocchi wiki/SDLC, **When** gira `install rag`, **Then** il
   blocco RAG-usage coesiste senza toccare gli altri (marker distinti).
3. **Given** un'installazione già fatta, **When** si riesegue, **Then** il blocco non è duplicato
   (idempotente).

---

### User Story 2 - L'uso diretto della libreria è rilevato sull'ospite (Priority: P2)

Come maintainer, voglio che, se l'agente dell'ospite usa `sertor_core` direttamente (fuori da
CLI/MCP/test), ciò sia **rilevato e segnalato**, così che la deviazione dal Principio XI sia visibile
invece che silenziosa.

**Why this priority**: difesa in profondità oltre l'istruzione; rende la violazione osservabile.

**Independent Test**: con l'hook installato, simulare un'azione dell'agente che importa/usa
`sertor_core` direttamente e verificare che l'hook emette un segnale (warning) senza bloccare il flusso
(modalità default `warn`); un'azione che usa `sertor-rag`/MCP o un percorso di test non genera segnale.

**Acceptance Scenarios**:
1. **Given** l'hook installato in modalità `warn` (default), **When** un'azione dell'agente usa
   `sertor_core` direttamente fuori dai vehicles/test, **Then** viene emesso un warning non bloccante.
2. **Given** la stessa azione ma su un percorso di test, **When** l'hook valuta, **Then** non emette
   segnale (eccezione test).
3. **Given** l'hook che non riesce a valutare il contesto, **When** occorre, **Then** fallisce aperto
   (nessun blocco), non-fatale.

---

### Edge Cases
- `CLAUDE.md` assente → creato col solo blocco RAG-usage.
- Coesistenza di tre blocchi a marker (`SERTOR:WIKI-RITUAL`, `SERTOR:SDLC-RITUAL`, `SERTOR:RAG-USAGE`):
  ciascuno idempotente sui propri marker.
- Hook assente o shell non disponibile sull'ospite → la capacità RAG resta pienamente usabile (l'hook
  è un di più; la sua assenza non rompe nulla, Principio X).
- Falsi positivi del rilevamento → default `warn` + fail-open evitano blocchi indebiti.

## Requirements *(mandatory)*

### Functional Requirements — Gruppo B (istruzione)
- **FR-B1**: Quando `sertor install rag` gira, il sistema MUST depositare nel `CLAUDE.md` dell'ospite un
  blocco a marker `SERTOR:RAG-USAGE` che istruisce l'agente a usare la capacità RAG via `sertor-rag`
  (CLI) o i tool MCP e a NON importare `sertor_core` nei propri script.
- **FR-B2**: Il blocco MUST usare marker propri, distinti da `SERTOR:WIKI-RITUAL` e
  `SERTOR:SDLC-RITUAL`, ed essere idempotente e non distruttivo (re-run non duplica; il resto del file è
  preservato byte-per-byte fuori dai marker).
- **FR-B3**: Il blocco MUST essere host-facing in inglese e NON contenere clausole costituzionali
  Sertor-interne (è un'istruzione d'uso, non un gate di governance dell'ospite).

### Functional Requirements — Gruppo C (hook)
- **FR-C1**: Quando l'agente dell'ospite usa `sertor_core` direttamente fuori da vehicles e test, l'hook
  installato MUST rilevarlo ed emettere un segnale.
- **FR-C2**: In modalità `warn` (default) il sistema MUST emettere un avviso non bloccante; in modalità
  `block` (opzionale, Could) MUST impedire l'azione.
- **FR-C3**: L'hook MUST essere host/assistente-specifico (adattatore del trigger depositato
  dall'installer), non incorporato nel core; la sua assenza MUST NOT rompere l'uso di Sertor.
- **FR-C4**: Se l'hook non riesce a valutare il contesto, MUST fallire aperto (nessun falso blocco),
  non-fatale.
- **FR-C5**: L'hook MUST escludere i percorsi di test dalla rilevazione (l'uso diretto della libreria
  nei test è legittimo — Principio I/XI).

## Success Criteria *(mandatory)*

- **SC-1 (B)**: dopo `sertor install rag`, in **100%** dei casi il `CLAUDE.md` contiene il blocco
  `SERTOR:RAG-USAGE`; re-run → **0** duplicati; altri blocchi a marker intatti.
- **SC-2 (C)**: in ≥1 scenario verificabile, l'uso diretto di `sertor_core` fuori dai vehicles/test
  **viene segnalato** (warn) senza bloccare; un uso via vehicle o in test **non** genera segnale.
- **SC-3 (non-distruttività/idempotenza)**: re-run dell'installer → **0** modifiche su artefatti già
  presenti; nessun file utente sovrascritto.
- **SC-4 (host-agnostico/Principio X)**: l'assenza dell'hook non impedisce l'uso della capacità RAG.
- **SC-5 (non-regressione)**: suite installer (`packages/sertor`) e core restano verdi.

## Assumptions
- `sertor install rag` oggi deposita solo `.env`/`.mcp.json`/`.gitignore` + deps in `.sertor/`
  (`build_rag_plan`); B aggiunge un artefatto `MARKER_BLOCK` riusando il motore esistente
  (`write_marker_block` del toolkit) + un asset host-facing.
- L'hook (C) è host-specifico (Claude Code per primo); il meccanismo concreto (evento, script,
  rilevazione) è materia del **plan**. Default severità `warn`; `block` = Could.
- Fuori ambito: gruppo A (già su master), gruppo D (plan-template neutro), enforcement su assistenti
  non-Claude.
