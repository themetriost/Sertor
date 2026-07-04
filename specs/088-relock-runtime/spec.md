# Feature Specification: Rituale post-merge — re-lock del runtime `.sertor/` a HEAD

**Feature Branch**: `092-f8-relock-runtime`

**Created**: 2026-07-03

**Status**: Draft

**Input**: E15-FEAT-008 (epica `fedelta-dogfood`). Fonte requisiti:
`requirements/fedelta-dogfood/relock-runtime/requirements.md`. Decisione Q1 = opzione (a).

## Contesto (perché)

Il runtime `.sertor/` del dogfood (feature F1) installa `sertor-core` da `git=<repo>` a **HEAD**, ma
`.sertor/uv.lock` fissa il commit risolto. Dopo un merge su `master`, HEAD avanza e il runtime resta
inchiodato al commit vecchio: il dogfood servirebbe **codice stantio** rispetto al `master` reale. Poiché il
modello standing è «il dogfood traccia HEAD», il passo di re-aggancio (re-lock) va **meccanizzato** — spostato
dalla memoria dell'agente a un passo deterministico del rituale post-merge (confine D↔N).

Correzione collaterale di F1: `.sertor/uv.lock` è stato **committato per errore**; con un runtime che
re-locka ad ogni merge, un lock tracciato produce churn (un diff ad ogni merge) e un potenziale loop
(merge → re-lock → nuovo lock → commit → merge). Il lock del dogfood va **locale** (gitignorato); resta
tracciato solo `.sertor/pyproject.toml` (la spec stabile del runtime).

**Confine invariante:** questo re-lock è **dogfood-only**. Gli ospiti pinnano una versione e ricevono
l'auto-updater (E2-FEAT-013), NON tracciano HEAD → il meccanismo NON deve finire negli asset distribuiti
(in particolare l'hook `rag-freshness.ps1` che viene installato/sincronizzato sui client).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Il runtime si riallinea a HEAD dopo un merge (Priority: P1)

Come manutentore del dogfood, dopo aver mergiato una PR su `master` voglio che il runtime `.sertor/` si porti
automaticamente all'ultimo `master` mergiato, senza dovermi ricordare un comando manuale, così l'agente e gli
hook di dogfooding servono sempre il codice reale del progetto.

**Why this priority**: è il cuore della feature — chiude il gap «runtime stantio dopo il merge» che
contraddice il modello «il dogfood traccia HEAD». Senza questo, F1 resta a metà.

**Independent Test**: mergiare un cambiamento su `master`, poi eseguire il passo di re-lock; verificare che il
`sertor-core` risolto in `.sertor/.venv` corrisponda al nuovo `origin/master` (e non al commit precedente).

**Acceptance Scenarios**:

1. **Given** `.sertor/` lockato a un commit precedente e `origin/master` avanzato, **When** si esegue il passo
   di re-lock, **Then** il runtime viene ri-lockato e ri-sincronizzato all'HEAD di `origin/master`.
2. **Given** `.sertor/` già allineato all'HEAD di `origin/master`, **When** si esegue il passo di re-lock,
   **Then** il passo è un **no-op** (nessun re-sync costoso) e lo segnala.

---

### User Story 2 - Nessun churn/loop dal lock committato (Priority: P1)

Come manutentore, non voglio che il lock del runtime produca un diff ad ogni merge né un loop di commit; il
lock del dogfood deve essere un artefatto **locale**, mentre solo la spec stabile del runtime è versionata.

**Why this priority**: senza il gitignore, il re-lock stesso genererebbe il churn/loop che la feature vuole
evitare — è un prerequisito per attivare US1 in sicurezza.

**Independent Test**: verificare che `.sertor/uv.lock` non sia più tracciato da git (assente dall'output di
`git ls-files`) e che `.sertor/pyproject.toml` resti tracciato; dopo un re-lock, `git status` non mostra il
lock come modifica.

**Acceptance Scenarios**:

1. **Given** il repo, **When** si ispeziona il tracking git, **Then** `.sertor/uv.lock` è git-ignorato e non
   tracciato, mentre `.sertor/pyproject.toml` è tracciato.
2. **Given** un clone fresco, **When** si esegue il setup del runtime (`uv sync` in `.sertor/`), **Then** il
   runtime risolve `sertor-core` all'HEAD corrente (nessun lock committato che lo pinni a un vecchio commit).

---

### User Story 3 - Il re-lock è meccanico e fail-loud (Priority: P2)

Come agente/flusso principale, voglio che il passo di re-lock sia deterministico e che, se fallisce
(rete/risoluzione), riporti un errore azionabile invece di lasciare in silenzio un runtime stantio.

**Why this priority**: la qualità del passo (determinismo + fail-loud, Principio XII) è ciò che lo rende
affidabile come parte del rituale; secondaria rispetto all'esistenza del meccanismo (US1/US2).

**Independent Test**: simulare un re-lock con rete assente/risoluzione fallita e verificare che il passo esca
con errore azionabile (non zero-exit silenzioso) e non lasci un runtime parziale.

**Acceptance Scenarios**:

1. **Given** rete assente o risoluzione fallita, **When** si esegue il re-lock, **Then** il passo riporta un
   errore azionabile (fail-loud) e non degrada in silenzio.
2. **Given** il rituale post-merge, **When** lo si esegue, **Then** il passo di re-lock precede re-index/smoke
   (l'indice si ricostruisce sul runtime aggiornato).

---

### Edge Cases

- **Merge di sessione non ancora pushato:** il re-lock pulla da `git=<repo>` = **remote**, quindi confronta con
  `origin/master`; se il merge locale non è ancora su `origin`, il passo è no-op finché il push non avviene
  (comportamento voluto — il dogfood segue il remote HEAD).
- **`.sertor/.venv` assente** (clone fresco mai sincronizzato): il passo esegue un primo `uv sync` invece del
  confronto-poi-sync (non c'è un commit risolto da confrontare) — non è un errore.
- **Runtime avanti al remote** (commit locale non pushato risolto nel lock): il confronto tratta «non uguale a
  origin/master» in modo conservativo → esegue il re-lock verso `origin/master` (fonte di verità = remote).
- **`uv` non disponibile / progetto `.sertor/` mancante:** errore azionabile (il runtime non è installato → F1
  non eseguita), non un no-op silenzioso.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il sistema DEVE fornire un passo **deterministico** (script) che ri-locka e ri-sincronizza il
  runtime `.sertor/` all'HEAD di `origin/master` (equivalente a `uv lock --upgrade` + `uv sync` nel progetto
  `.sertor/`).
- **FR-002**: Il passo DEVE essere **check-then-act**: quando il runtime è già all'HEAD di `origin/master`, è un
  **no-op** (nessun re-sync costoso) e lo comunica; esegue il re-lock **solo se il runtime è indietro**.
- **FR-003**: `.sertor/uv.lock` DEVE essere git-ignorato e rimosso dal tracking; `.sertor/pyproject.toml` DEVE
  restare tracciato.
- **FR-004**: Un clone fresco DEVE ottenere un runtime all'HEAD corrente via il setup `uv sync` di `.sertor/`
  (nessun lock committato che lo pinni a un vecchio commit).
- **FR-005**: Se il re-lock fallisce (rete/risoluzione/`uv` assente/progetto mancante), il sistema DEVE
  riportare un errore **azionabile** (fail-loud, Principio XII) e NON lasciare un runtime stantio in silenzio.
- **FR-006**: Il re-lock DEVE avvenire **solo tramite vehicle** (`uv`/`git`), senza mai importare `sertor_core`;
  `sertor-core` resta **invariato**.
- **FR-007**: Il meccanismo DEVE essere **dogfood-only**: vive fuori dagli asset distribuiti (in `scripts/dev/`,
  mai bundlato dagli installer) e il suo innesco è il **rituale post-merge del flusso principale**. NON deve
  comparire nell'hook distribuito `rag-freshness.ps1` né in altri asset host-facing.
- **FR-008**: Il rituale post-merge documentato DEVE includere il passo di re-lock **prima** di re-index/smoke,
  e un **gate di verde** (suite di test completa + lint) **prima** del merge, così un merge non lascia il
  `master` rotto (regressione emersa il 2026-07-03).
- **FR-009**: Il progetto DEVE avere una **guardia di regressione** (test) che fallisce se `.sertor/uv.lock`
  torna tracciato o se `.sertor/pyproject.toml` esce dal tracking.

### Key Entities

- **Runtime `.sertor/`**: progetto `uv` che installa `sertor-core` da `git=<repo>` HEAD; artefatti
  `.sertor/pyproject.toml` (tracciato, spec stabile) e `.sertor/uv.lock` (locale, gitignorato dopo questa
  feature).
- **Passo di re-lock**: script deterministico `scripts/dev/relock-runtime.ps1` (check-then-act, fail-loud),
  innescato dal rituale post-merge del flusso principale.
- **Rituale post-merge**: sequenza documentata in `CLAUDE.md` che, dopo un merge su `master`, riallinea il
  runtime (re-lock) e poi re-indicizza/smoke-testa il RAG.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: dopo un merge su `master`, un solo passo deterministico porta il `sertor-core` risolto in
  `.sertor/.venv` a corrispondere all'HEAD di `origin/master` (verificabile per commit/versione).
- **SC-002**: `.sertor/uv.lock` non compare in `git ls-files`; `.sertor/pyproject.toml` sì; dopo un re-lock
  `git status` non mostra il lock come modifica → **zero churn**.
- **SC-003**: quando il runtime è già a HEAD, il passo termina come no-op **senza** eseguire un `uv sync`
  (osservabile dall'assenza di re-risoluzione/re-download).
- **SC-004**: un clone fresco, eseguito il setup del runtime, risolve `sertor-core` all'HEAD corrente (nessun
  pin a un commit vecchio da lock committato).
- **SC-005**: in caso di fallimento (rete/risoluzione), il passo esce con stato d'errore e messaggio azionabile;
  non lascia un `.sertor/.venv` parziale spacciato per aggiornato.
- **SC-006**: nessun artefatto del meccanismo compare negli asset distribuiti (`packages/**/assets/`,
  `rag-freshness.ps1`); una guardia lo verifica.
- **SC-007**: `sertor-core` invariato (nessun file sotto `src/sertor_core/` modificato dalla feature).

## Assumptions

- Non esiste un hook nativo «post-merge» in Claude Code; l'innesco è il **rituale del flusso principale**
  (opzione (a) scelta), non un hook distribuito — coerente col vincolo dogfood-only.
- I merge di sessione sono **pushati** su `origin` prima del merge (invariante del `configuration-manager`),
  quindi confrontare con `origin/master` è corretto.
- Il re-lock richiede **rete** (`uv lock --upgrade` risolve da `git=<repo>` remoto); dichiarato, fail-loud se
  offline (il runtime resta all'ultimo lock valido).
- F1 è ✅ (il runtime `.sertor/` esiste come progetto `uv`).
- Il `.venv` di sviluppo del workspace resta editable e **fuori ambito** (usato per test/sviluppo, non è il
  runtime dell'agente).
