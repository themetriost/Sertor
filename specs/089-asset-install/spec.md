# Feature Specification: asset-install — gli asset del dogfood dall'installer (0 special-case)

**Feature Branch**: `089-asset-install`

**Created**: 2026-07-04

**Status**: Draft

**Input**: E15 fedelta-dogfood, scope B di FEAT-001. Requisiti in
`requirements/fedelta-dogfood/asset-install/requirements.md`. Direttiva utente (2026-07-04):
«da adesso in poi Sertor usa gli asset di Sertor partendo dall'installer, 0 special-case locali».

## User Scenarios & Testing *(mandatory)*

### User Story 1 — La FONTE degli asset del dogfood è il vero installer (Priority: P1)

Il manutentore del dogfood vuole che gli asset host-facing (`.claude/` hook+skill+agenti, machinery
`.specify/`, blocchi marker in `CLAUDE.md`, wiring in `settings.json`, `.sertor/sertor-cli-reference.md`)
abbiano come **origine** l'esecuzione dei veri `sertor install rag`, `sertor install wiki`,
`sertor-flow install` **sul dogfood** — non il `sync` interim né `materialize-speckit.ps1`.

**Why this priority**: è il cuore della direttiva e dell'obiettivo E15 (process-fidelity). Senza questa,
il dogfood resta un client «finto» sugli asset.

**Independent Test**: eseguire i 3 installer sul dogfood; il risultato è **idempotente** sugli asset già
fedeli (skip/aggiorna, mai duplica) e lo stato committato del dogfood coincide con l'output dell'install
(o ne è un superset dichiarato).

**Acceptance Scenarios**:

1. **Given** il dogfood a uno stato pulito, **When** si eseguono i 3 installer, **Then** gli asset
   host-facing risultano `skipped (already present)` o aggiornati, senza duplicazioni, e `.env` /
   costituzione v1.4.0 / `.mcp.json` / `wiki.config.toml` restano **preservati** (byte-invariati).
2. **Given** l'install eseguito una volta, **When** lo si ri-esegue, **Then** l'esito è idempotente
   (nessun diff distruttivo su artefatti curati; un eventuale superset è dichiarato).

### User Story 2 — CLAUDE.md riconciliato (ibrido blocco+prosa), nessuna duplicazione (Priority: P1)

L'agente che legge `CLAUDE.md` non deve trovare i 3 blocchi marker generici **duplicati** rispetto alla
prosa dogfood ricca. Ibrido per-blocco (decisione presa): RAG-USAGE tieni-blocco/prosa-quasi-intatta ·
WIKI-RITUAL prosa-vince (valuta rimozione blocco) · SDLC-RITUAL ibrido vero (tieni blocco, sfronda i
duplicati puri dalla prosa).

**Why this priority**: senza riconciliazione, ogni install duplica contenuto; `CLAUDE.md` è il contratto
di governance letto a ogni sessione — la duplicazione lo degrada.

**Independent Test**: dopo la riconciliazione, ogni tema (RAG usage · rituale wiki · SDLC/git) è coperto
**una sola volta** (blocco **o** prosa, non entrambi in modo ridondante); un ri-install non re-inserisce
il contenuto già presente.

**Acceptance Scenarios**:

1. **Given** i 3 blocchi inseriti dall'install, **When** si applica la riconciliazione ibrida, **Then**
   nessun tema è coperto due volte e i blocchi che restano sono posseduti dai marker (idempotenti al
   ri-install).
2. **Given** `CLAUDE.md` riconciliato, **When** si ri-esegue `sertor(-flow) install`, **Then** i blocchi
   non vengono duplicati (replace-if-marker) e la prosa dogfood è preservata.

### User Story 3 — Diff pulito: nessun churn CRLF (Priority: P2)

Chi revisiona il diff dell'install deve vedere **solo i cambiamenti reali**, non un churn di line-ending
sull'intero file (oggi CLAUDE.md 1228 righe «cambiate» vs 174 reali, perché l'installer scrive CRLF e i
sorgenti erano LF; il repo è già CRLF-inconsistente: `.claude/` CRLF, sorgenti LF).

**Why this priority**: senza normalizzazione, il diff dell'asset-install (e di ogni futuro install su
host Windows) è illeggibile e la review impossibile — mina l'ispezionabilità richiesta (Principio XII).

**Independent Test**: introdotta la normalizzazione, ri-scrivere un file via installer produce **zero**
righe-diff spurie da line-ending; `git ls-files --eol` mostra un repo line-ending-consistente.

**Acceptance Scenarios**:

1. **Given** il repo CRLF-inconsistente, **When** si applica la policy di normalizzazione, **Then**
   `git diff` di un file toccato dall'install mostra solo il contenuto cambiato, non ogni riga.

### User Story 4 — 0 special-case: sync/script come guardia, non come fonte (Priority: P2)

Il manutentore vuole che le scorciatoie dev-time (`sertor_installer.sync`, `materialize-speckit.ps1`)
**non siano più la via di fedeltà** (la fonte è l'installer), ma le loro **guardie byte** restino come
rete anti-drift dogfood↔bundle.

**Why this priority**: è la clausola «0 special-case» della direttiva; senza, resta ambiguità sulla
sorgente. Le guardie però vanno tenute (decisione: «guardia sì, fonte no»).

**Independent Test**: la documentazione/rituale non indica più il `sync`/script come modo di *ottenere*
gli asset (solo il vero install); le guardie byte (`test_assets_sync`, `test_assets_rag_dogfood_sync`)
girano ancora verdi e falliscono se il dogfood diverge dal bundle.

**Acceptance Scenarios**:

1. **Given** il nuovo modello, **When** un asset del dogfood diverge dal bundle, **Then** la guardia byte
   **fallisce** in CI (rete anti-drift attiva).
2. **Given** la documentazione, **When** si cerca «come ottenere gli asset», **Then** indica il vero
   install, non il `sync`/script (retrocessi a guardia/dev-tooling, marcati come tali).

### User Story 5 — `wiki/log.md` legacy risolto (Priority: P3)

L'install crea il monolitico `wiki/log.md`, ma il dogfood usa la rotazione `wiki/log/<data>.md`. Il file
spurio va **scartato** nel dogfood e il **template installer allineato** alla rotazione (E15-FEAT-006).

**Why this priority**: minore (staleness inversa del template); coordinato con FEAT-006, non blocca il
cuore di asset-install.

**Independent Test**: dopo l'install il dogfood non contiene un `wiki/log.md` spurio; il template
installer produce la struttura `wiki/log/` (o l'estensione dogfood è dichiarata).

**Acceptance Scenarios**:

1. **Given** l'install che crea `wiki/log.md`, **When** si applica la policy, **Then** il dogfood non
   traccia `wiki/log.md` e la conoscenza resta in `wiki/log/<data>.md`.

### Edge Cases

- **Clobber non mappato:** un installer distrugge un artefatto curato non ancora identificato → scoperta
  su branch con diff ispezionato prima del commit; installer preservanti estesi caso per caso (il dry-run
  ha già mostrato `.env`/costituzione/`.mcp.json`/`wiki.config` preservati).
- **CRLF↔byte-guard:** normalizzare il dogfood a LF senza normalizzare il bundle romperebbe la guardia
  byte → la policy line-ending deve valere **su entrambi** (dogfood + bundle) o la guardia va resa
  eol-insensibile (vedi decisione DD-1).
- **Ri-install ripetuto:** deve essere idempotente (no duplicazione blocchi, no diff distruttivo).
- **Host non-Windows:** la normalizzazione LF non deve introdurre regressioni sugli host Unix (LF è già
  il loro default).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Gli asset host-facing del dogfood MUST avere come fonte l'esecuzione dei veri installer
  (`sertor install rag`/`wiki`, `sertor-flow install`) sul dogfood, non `sertor_installer.sync` né
  `materialize-speckit.ps1`. *(REQ-001)*
- **FR-002**: L'esecuzione degli installer sul dogfood MUST essere **idempotente** sugli asset già fedeli
  e **non distruttiva** sugli artefatti curati (`.env`, costituzione v1.4.0, `.mcp.json`,
  `wiki.config.toml`). *(REQ-005/006)*
- **FR-003**: I blocchi marker in `CLAUDE.md` (RAG-USAGE, WIKI-RITUAL, SDLC-RITUAL) MUST comparire **una
  sola volta** e non duplicare la prosa dogfood; la riconciliazione segue l'ibrido per-blocco deciso.
  *(REQ-003, DA-1 risolta)*
- **FR-004**: Un ri-install MUST NOT duplicare i blocchi (replace-if-marker) né distruggere la prosa
  dogfood preservata. *(REQ-006/007)*
- **FR-005**: Il repository MUST adottare una policy di line-ending consistente (vedi DD-1) tale che
  l'output dell'install non produca churn CRLF nel diff. *(REQ-002/012, FEAT-010)*
- **FR-006**: Le guardie byte (`test_assets_sync`, `test_assets_rag_dogfood_sync`) MUST restare attive e
  verdi come rete anti-drift dogfood↔bundle; il `sync`/script MUST essere retrocessi a **guardia/dev-tool**,
  non fonte di fedeltà (documentazione/rituale aggiornati). *(REQ-008/010, decisione «guardia sì fonte no»)*
- **FR-007**: `.sertor/sertor-cli-reference.md` e gli altri residui non-byte prodotti dall'install MUST
  essere presenti nel dogfood (o l'assenza dichiarata con motivo). *(REQ-004, ex-FEAT-003)*
- **FR-008**: Il `wiki/log.md` legacy prodotto dall'install MUST essere scartato nel dogfood; il template
  installer MUST essere allineato alla rotazione `wiki/log/` (coord. E15-FEAT-006). *(FR di coordinamento)*
- **FR-009**: L'operazione (distruttiva sul repo vivo) MUST avvenire su branch con **diff ispezionabile
  prima del commit** e MUST essere reversibile (Principio XII, fail-loud, esito onesto). *(REQ-012)*
- **FR-010**: `sertor-core` MUST restare invariato e **nessun asset distribuito** MUST essere reso
  Sertor-specifico (Principio X/XI). Le eventuali modifiche host-agnostiche (installer preservante sui
  blocchi, `.gitattributes` nel template) restano generiche. *(REQ-011)*

### Decisioni di design

- **DD-1 (CRLF↔byte-guard) — da confermare al plan.** Opzione raccomandata **(A)**: normalizzare **tutto
  a LF** — `.gitattributes` (`* text=auto eol=lf`) nel dogfood **e** rinormalizzazione del bundle
  `assets/` a LF, così le guardie byte confrontano LF↔LF; il `.gitattributes` va anche nel **template
  installer** (host-facing, beneficia ogni ospite Windows — è il contenuto di FEAT-010). Opzione (B)
  (mantenere CRLF coerente ovunque) scartabile: innaturale per i sorgenti. **Implicazione host:** (A) è
  una modifica host-facing → richiede il gate «feature completa = installabile su un ospite» + doc utente.
- **DD-2 (CLAUDE.md bilingue) — assunzione.** I blocchi restano **EN** (host-agnostici, come tutti gli
  asset distribuiti) e la prosa dogfood resta **IT**: `CLAUDE.md` del dogfood è **bilingue** per
  costruzione (blocco-client EN + governance-dogfood IT). Accettato salvo diverso indirizzo.

### Key Entities

- **Asset host-facing**: hook/skill/agenti (`.claude/`), machinery `.specify/`, blocchi marker
  (`CLAUDE.md`), wiring (`settings.json`), reference (`.sertor/sertor-cli-reference.md`). *Fonte attesa:*
  l'installer.
- **Artefatto curato preservato**: `.env`, costituzione v1.4.0, `.mcp.json`, `wiki.config.toml`, prosa
  dogfood di `CLAUDE.md`. *Invariante:* mai distrutto dall'install.
- **Guardia byte**: `test_assets_sync`, `test_assets_rag_dogfood_sync`. *Ruolo nuovo:* rete anti-drift,
  non fonte.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Ri-eseguendo i 3 installer sul dogfood, **0** artefatti curati persi e **0** blocchi
  duplicati (idempotenza verificata su due esecuzioni consecutive).
- **SC-002**: Il diff dell'output install mostra **0** righe spurie da line-ending (churn CRLF azzerato);
  `git ls-files --eol` = repo line-ending-consistente.
- **SC-003**: Ogni tema di governance (RAG usage · rituale wiki · SDLC/git) è coperto **una sola volta**
  in `CLAUDE.md` (blocco o prosa), verificabile da un conteggio marker/sezioni.
- **SC-004**: Le guardie byte restano **verdi** e falliscono su un drift indotto (test negativo), mentre
  la documentazione/rituale non cita più il `sync`/script come modo di *ottenere* gli asset.
- **SC-005**: `sertor-core` **byte-invariato**; suite completa (`-m "not cloud"`) + `ruff` verdi
  pre-merge (gate E15-FEAT-008).

## Assumptions

- **Il dry-run è rappresentativo:** l'esito «per lo più idempotente / preservante» osservato il
  2026-07-04 vale anche per l'esecuzione reale (stessa versione `@master`); ogni clobber nuovo si scopre
  su branch prima del commit.
- **DD-2 (bilingue) accettato** salvo diverso indirizzo dell'utente.
- **FEAT-006** (template `wiki/log/`) e la parte «`.gitattributes` nel template installer» di FEAT-010
  possono essere **fette coordinate** di questa feature o feature adiacenti — da fissare al plan; il
  cuore (fonte=install, CLAUDE.md ibrido, no-churn locale) resta in ambito.
- **Confine dev↔dogfood** invariato: i test/sviluppo restano sull'editable `.venv`; l'operazione tocca lo
  stato del dogfood, non il ciclo di sviluppo.
- **Rete richiesta** per `uvx`/`specify init` durante l'esecuzione reale.
