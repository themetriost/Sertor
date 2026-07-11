# Implementation Plan: Documentazione utente MVP (getting-started unico + README di valore)

**Branch**: `096-doc-utente-mvp` | **Date**: 2026-07-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/096-doc-utente-mvp/spec.md` (item di audit **A-18**, E13
Fase 1 Musts: FEAT-001 getting-started unico + FEAT-002 README di valore).

## Summary

Consegnare **due artefatti di documentazione statica, host-agnostici**: (1) un **nuovo**
`docs/getting-started.md` — percorso unico «dal nulla al primo valore» (prerequisiti → `sertor install
rag` → `index` → prima query) che **assorbe e ordina** i quickstart per-assistente e `retrieval.md`,
**delegando** ad essi il dettaglio divergente, e che **termina con un esempio concreto di fusione
code+doc**; (2) la **riscrittura** di `README.md` in chiave **valore-first**, che apre col
differenziatore code+doc + esempio, **preserva i fatti** di capacità/status, e punta al getting-started
come **ingresso unico**. Nessun codice/vehicle toccato: è **authoring** (D↔N). Comandi **copiati dagli
asset reali** (anti-drift). Decisioni di clarify: **esempi CLI con entrambe le varianti Claude+Copilot
affiancate**; **esempio code+doc illustrativo generico host-agnostico**.

## Technical Context

**Language/Version**: Markdown (documentazione statica) — **nessun codice sorgente**.

**Primary Dependencies**: gli **asset/vehicle reali** da cui derivare i comandi — `docs/install-claude.md`,
`docs/install-copilot.md`, `docs/retrieval.md`, `docs/install.md`, `packages/sertor/docs/install.md`,
`README.md` attuale. Comandi reali: `uvx --from "git+…#subdirectory=packages/sertor" sertor install rag
[--assistant copilot-cli] [--backend …]`, `sertor configure`, `uv run --project .sertor sertor-rag
index .`, `uv run --project .sertor sertor-rag search "…"`, MCP `search_combined`.

**Storage**: N/A (nessun dato persistito; solo file `.md`).

**Testing**: verifica **manuale/scriptata** — (a) walkthrough di accettazione (US1/US2/US3 della spec);
(b) verifica dei **link relativi** (ogni `[…](….md)` in `docs/` + `README.md` risolve a un file
esistente). **DA-4 risolta (research):** oggi **non esiste** un link/lint automatico per `docs/` (il
`sertor-wiki-tools validate` è scoped su `wiki/` via `wiki.config.toml`; la CI non tocca `docs/`) → il
check è manuale/scriptato in fase di implement; un linter automatico per `docs/` è **fuori scope**
(eventuale follow-up).

**Target Platform**: qualunque progetto ospite, su **Claude Code** e **GitHub Copilot CLI** (Principio X).

**Project Type**: **documentation authoring** (E13) — non una capacità di prodotto; nessun modulo
`src/`, nessun test unitario, nessun asset installabile nuovo.

**Performance Goals**: N/A. **Constraints**: artefatti statici (nessun LLM a runtime, D↔N); comandi
verificabili contro asset reali (anti-drift); separazione interna/esterna netta (mai `wiki/`/`specs/`
come doc utente). **Scale/Scope**: 2 file scritti/riscritti + rimandi di convergenza nei 4 doc esistenti.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Costituzione v1.4.0. È **authoring di documentazione**: molti principi di *codice* sono **N/A per
costruzione** (nessun `src/` toccato); quelli sulla **portabilità** e sull'**onestà** sono centrali.

- [x] **I — Dipendenze verso l'interno:** **N/A** — nessun codice del core toccato; `sertor-core`/CLI/
  installer **invariati**.
- [x] **II — Boundary & local-first:** **N/A** — nessun adapter/provider.
- [x] **III — YAGNI & unità piccole:** **PASS** — due file statici, nessuna astrazione, nessun tooling
  nuovo (docs-site esplicitamente fuori scope).
- [x] **IV — Errori espliciti:** **N/A** — nessun codice. (L'analogo documentale è FR-014: un comando non
  verificabile non si include.)
- [x] **V — Testabilità & misure:** **PASS (adattato)** — la «misura» è l'accettazione (SC-001..006) +
  verifica link; nessun test automatico perché non c'è codice.
- [x] **VI — Idempotenza & non-distruttività:** **PASS** — la riscrittura del README **preserva i fatti**
  (FR-010, R-3); nessuna sovrascrittura di file utente (sono file del repo di Sertor).
- [x] **VII — Leggibilità:** **PASS** — vale alla prosa: percorso lineare, senza gergo (FR-007).
- [x] **VIII — Configurabilità centralizzata:** **N/A** — nessuna config.
- [x] **IX — Osservabilità:** **N/A** — nessuna operazione a runtime.
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** **PASS (centrale)** — entrambi gli artefatti valgono su
  Claude e Copilot; ciò che diverge sta nei per-assistente delegati (FR-003/FR-011); esempi CLI con
  **entrambe le varianti affiancate** (clarify). È il cuore del gate per questa feature.
- [x] **XI — Consumo via vehicles:** **PASS** — la doc insegna a usare le capacità **solo** via CLI/MCP
  (`sertor-rag`, MCP); **mai** import di `sertor_core` (FR-012).
- [x] **XII — Fail Loud, Fix the Cause:** **PASS** — anti-drift: un comando errato/mancante è un
  **finding da segnalare**, non da mascherare nella doc (FR-014, edge case della spec).
- [x] **Allineamento alla missione:** **PASS (con motivo)** — comunicare il differenziatore **fusione
  code+doc** e portare al primo valore serve **adozione e portabilità** (Principio X), che sono la
  traduzione operativa della missione. È *periferico* alla qualità del retrieval in sé (E13 lo
  **racconta**, non lo costruisce) ma non deriva: l'esempio concreto mostra proprio la fusione code+doc.

**Esito gate: PASS 12/12 + missione.** Nessuna violazione → nessun *Complexity Tracking*.

## Project Structure

### Documentation (this feature)

```text
specs/096-doc-utente-mvp/
├── plan.md              # questo file
├── research.md          # Phase 0 — risoluzione DA-4 + decisioni di clarify
├── quickstart.md        # Phase 1 — walkthrough di verifica/accettazione
├── spec.md              # /speckit-specify
├── checklists/
│   └── requirements.md  # checklist di qualità della spec
└── tasks.md             # /speckit-tasks (non creato qui)
```

*Nessun `data-model.md` (nessuna entità dati) né `contracts/` (nessuna interfaccia esterna): la feature
non introduce dati né API — sono N/A per un artefatto documentale.*

### Source Code (repository root)

Nessun `src/` toccato. I file **prodotti/modificati** sono documentazione utente in radice/`docs/`:

```text
README.md                    # RISCRITTO — valore-first (FEAT-002)
docs/
├── getting-started.md       # NUOVO — percorso unico host-agnostico (FEAT-001)
├── install-claude.md        # rimando di convergenza al getting-started (no duplicazione)
├── install-copilot.md       # rimando di convergenza al getting-started
├── retrieval.md             # rimando di convergenza (concetti hybrid vs graph)
└── install.md               # resta il reference completo; citato dal getting-started
```

**Structure Decision**: authoring puro in `docs/` + `README.md` (nessun docs-site — DA-DM-b: si parte da
`docs/` consolidato). Convergenza: i doc esistenti puntano al getting-started; il getting-started delega
loro il dettaglio divergente e rimanda a `install.md`/`retrieval.md` per reference/concetti.

## Complexity Tracking

> Nessuna violazione del Constitution Check → sezione vuota.
