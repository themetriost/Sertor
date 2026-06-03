# Feature Specification: Skill — mantenere il wiki vivo (lint / indice / documentazione)

**Feature Branch**: `spec/005-wiki-manutenzione`

**Created**: 2026-06-03

**Status**: Draft

**Input**: Decomposizione di `requirements/sertor-core/wiki-manutenzione/requirements.md` (deriva da
FEAT-007, prioritizzata). Dipende da FEAT-003 (convenzioni/struttura wiki, in `master`) e dalla porta
`LLMProvider` (solo distillazione/contraddizioni semantiche). Domande aperte DA-1..DA-8 già risolte.
Vincoli: `.specify/memory/constitution.md` (Principi III, IV, VI, VIII, IX).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Lint del wiki: report di igiene e coperture (Priority: P1) 🎯 MVP

Come maintainer (o agente), eseguo il **lint** su un wiki e ottengo un **report strutturato** dei
problemi — wikilink rotti, pagine orfane, indice disallineato, **aree di documentazione mancanti** —
**senza che alcun file venga modificato**.

**Why this priority**: è il valore centrale ("mantenere il wiki vivo") ed è completamente
deterministico/LLM-free; senza lint non c'è diagnosi.

**Independent Test**: su un wiki sandbox con un link rotto, una pagina orfana e una pagina non in
indice, il lint elenca esattamente quei problemi e **non scrive nulla**.

**Acceptance Scenarios**:
1. **Given** un wiki con un `[[link]]` verso una pagina inesistente, **When** si esegue il lint,
   **Then** il report elenca il link rotto con la pagina sorgente.
2. **Given** una pagina non referenziata da `index.md` né da alcun wikilink, **When** si esegue il
   lint, **Then** è segnalata come **orfana** (`index.md`/`log.md` esenti).
3. **Given** una pagina presente su disco ma assente dal catalogo di `index.md`, **When** si esegue
   il lint, **Then** è segnalata come indice disallineato.
4. **Given** un set atteso di documentazione (es. una pagina architettura), **When** manca,
   **Then** il lint segnala la **copertura mancante**.
5. **Given** qualunque esecuzione di lint, **When** termina, **Then** nessun file del wiki è stato
   creato/modificato/eliminato (sola lettura).

### User Story 2 - Gate ricorrente a fine feature (Priority: P1)

Come team, eseguo il lint come **gate** non interattivo a fine di ogni feature (o in CI/pre-merge) e
ottengo un esito **pass/fail** consumabile da automazione, abbastanza **veloce** da girare spesso.

**Why this priority**: il valore della manutenzione è tenere la documentazione **sempre** allineata;
serve che il lint sia eseguibile di continuo come gate.

**Independent Test**: invocare l'operazione in modalità non interattiva su un wiki "sano" → esito
**pass** (exit 0); introdurre un problema → esito **fail** (exit ≠ 0); misurare che su un wiki tipico
completi in pochi secondi.

**Acceptance Scenarios**:
1. **Given** un wiki senza problemi, **When** si esegue il gate, **Then** esito **pass** (exit 0).
2. **Given** un wiki con link rotti/orfani, **When** si esegue il gate, **Then** esito **fail**
   (exit ≠ 0) con il report dei problemi.
3. **Given** due esecuzioni consecutive su wiki invariato, **When** si confrontano, **Then** l'esito è
   identico (idempotente, nessun side-effect).

### User Story 3 - Rigenerazione idempotente dell'indice (Priority: P1)

Come maintainer, rigenero il **catalogo di `index.md`** in modo idempotente, aggiornando **solo** il
blocco gestito tra marcatori e **preservando** il contenuto curato a mano; disponibile anche come
`--fix` sicuro del lint.

**Why this priority**: l'indice disallineato è il problema più comune e l'unico "fix" sicuro;
completa il ciclo diagnosi→correzione.

**Independent Test**: aggiungere una pagina, eseguire la rigenerazione → il catalogo include la nuova
pagina, il resto di `index.md` è intatto; rieseguire → file identico.

**Acceptance Scenarios**:
1. **Given** una nuova pagina, **When** si rigenera l'indice, **Then** il blocco tra marcatori
   `<!-- sertor:catalog -->…` include la pagina (link + sommario), e il resto di `index.md` resta intatto.
2. **Given** un wiki invariato, **When** si rigenera l'indice due volte, **Then** `index.md` è
   identico (idempotente).
3. **Given** il lint con `--fix`, **When** lo si esegue, **Then** applica **solo** la rigenerazione
   dell'indice (fix sicuro), **mai** auto-fix dei link rotti.

### User Story 4 - Documentazione ufficiale distillata dagli artifact (Priority: P2)

Come maintainer/agente, distillo gli **artifact** (epic/requirements/spec/plan/tasks/costituzione) e
le discussioni in **pagine di documentazione** (entità di business, funzionalità, motivazioni,
architettura) conformi alle convenzioni, che **rimandano con link** alle fonti **senza duplicarle**;
operazione **assistita** e **non distruttiva**.

**Why this priority**: è il ruolo prioritario (il wiki è la documentazione ufficiale), ma richiede
LLM ed è non deterministico → segue il nucleo deterministico (P1).

**Independent Test**: con `FakeLLM`, distillare un artifact → pagina conforme (frontmatter, kebab-case,
cartella tematica) con **backlink** alla fonte; rieseguire su pagina curata a mano → **non**
sovrascrive il contenuto curato.

**Acceptance Scenarios**:
1. **Given** un artifact (es. `specs/001-…/spec.md`) e un LLM configurato, **When** si distilla,
   **Then** è prodotta/aggiornata una pagina di documentazione conforme con **backlink** alla fonte.
2. **Given** una pagina già curata a mano, **When** si ridistilla, **Then** il contenuto curato **non**
   è sovrascritto (assistita/non distruttiva; idempotenza strutturale).
3. **Given** nessun LLM configurato, **When** si invoca la distillazione, **Then** errore esplicito.
4. **Given** la pagina distillata, **When** la si esamina, **Then** **rimanda** alla fonte e **non**
   ne duplica il contenuto.

### User Story 5 - Segnalazione delle contraddizioni (Priority: P2)

Come maintainer, ottengo nel report l'elenco delle pagine che contengono **marcatori di
contraddizione** (inseriti dall'ingest di FEAT-003); con LLM, opzionalmente, anche contraddizioni
semantiche.

**Why this priority**: utile per la coerenza, ma secondaria rispetto a lint/indice; la parte
semantica è opzionale (Could).

**Independent Test**: su un wiki con una pagina marcata come contraddittoria, il lint la elenca; senza
LLM, le contraddizioni semantiche sono semplicemente saltate (nessun errore).

**Acceptance Scenarios**:
1. **Given** una pagina con marcatore di contraddizione, **When** si esegue il lint, **Then** è
   elencata tra le contraddizioni.
2. **Given** nessun LLM configurato, **When** si esegue il lint, **Then** la rilevazione semantica è
   saltata senza errore (solo marcatori).

### Edge Cases
- Wiki vuoto o senza pagine → report vuoto, esito pass, nessuna modifica.
- `index.md` privo dei marcatori di catalogo → la rigenerazione li introduce in modo non distruttivo.
- Pagina referenziata solo dall'indice (non da wikilink) → **non** orfana (REQ-005/DA-5).
- Re-run di qualunque operazione su wiki invariato → esito identico, nessun timestamp modificato.
- Distillazione senza LLM → errore esplicito (non un risultato parziale).
- Tutti i test su **wiki sandbox** temporaneo, mai sul wiki di produzione.

## Requirements *(mandatory)*

### Functional Requirements
(dettaglio EARS e ID in `requirements/sertor-core/wiki-manutenzione/requirements.md`)

- **FR-001**: Il lint MUST scansionare le pagine e produrre un **report strutturato**, **sola lettura**. *(REQ-001/005/052)*
- **FR-002**: Il lint MUST segnalare i **wikilink rotti** (target inesistente). *(REQ-002)*
- **FR-003**: Il lint MUST segnalare le **pagine orfane** (non in `index.md` né in un wikilink; `index.md`/`log.md` esenti). *(REQ-003)*
- **FR-004**: Il lint MUST segnalare le pagine **assenti dal catalogo** di `index.md`. *(REQ-004)*
- **FR-005**: Il lint MUST segnalare le **coperture documentali mancanti** rispetto a un set atteso configurabile. *(REQ-064)*
- **FR-006**: Il lint MUST esporre un esito **pass/fail** non interattivo, consumabile come **gate** ricorrente (a fine feature/CI). *(REQ-053)*
- **FR-007**: La rigenerazione dell'indice MUST aggiornare **solo** il blocco tra marcatori, **idempotente** e **non distruttiva**. *(REQ-010/011/012)*
- **FR-008**: Il lint MUST essere **sola lettura di default**; con `--fix` esplicito MUST applicare solo **fix sicuri/idempotenti** (rigenera indice), **mai** auto-fix dei link. *(REQ-005/006)*
- **FR-009**: Il wiki MUST fungere da **documentazione ufficiale** (entità di business, funzionalità, motivazioni, architettura). *(REQ-060)*
- **FR-010**: Le sorgenti di distillazione MUST includere **discussioni + artifact** (`requirements/**`, `specs/**`, costituzione). *(REQ-061)*
- **FR-011**: Le pagine distillate MUST **linkare** le fonti e **non duplicarne** il contenuto. *(REQ-062)*
- **FR-012**: La distillazione documentale MUST produrre/aggiornare pagine conformi in modo **assistito/non distruttivo**; senza LLM MUST bloccarsi con errore esplicito. *(REQ-063/065)*
- **FR-013**: Il lint MUST segnalare le pagine con **marcatori di contraddizione**; le contraddizioni **semantiche** (con LLM) sono opzionali. *(REQ-020/021/022)*
- **FR-014**: Ogni operazione MUST essere **idempotente** su wiki invariato (nessun file/voce/timestamp nuovi). *(REQ-040/041)*
- **FR-015**: Il path del wiki MUST essere **configurabile**; repo-agnostico. *(REQ-050)*
- **FR-016**: Ogni operazione MUST emettere **log strutturati**. *(REQ-051)*

### Key Entities
- **Report di lint**: insieme tipizzato di problemi (link rotti, orfani, indice disallineato, coperture mancanti, contraddizioni) + esito pass/fail.
- **Blocco catalogo**: regione gestita di `index.md` tra marcatori, rigenerabile.
- **Pagina di documentazione**: pagina wiki (concept/synthesis/feature) con backlink alle fonti.
- **Sorgente**: discussione (`raw/`) o artifact (`requirements/**`, `specs/**`, costituzione).

## Success Criteria *(mandatory)*

- **SC-001**: Su un wiki con problemi noti, il lint li elenca tutti nel report **senza modificare file**.
- **SC-002**: Re-run di qualunque operazione su wiki invariato → esito **identico** (idempotenza, hash invariati).
- **SC-003**: La rigenerazione dell'indice **preserva** il contenuto curato a mano (non distruttiva).
- **SC-004**: La distillazione produce una pagina conforme con **backlink** alla fonte e **non** sovrascrive il curato.
- **SC-005**: Le pagine con marcatori di contraddizione sono elencate nel report.
- **SC-006**: Il gate restituisce **pass/fail** non interattivo, consumabile da automazione, in tempi adatti all'esecuzione frequente.
- **SC-007**: Le coperture documentali mancanti (rispetto al set atteso) sono segnalate.
- **SC-008**: Il **100%** delle operazioni emette log strutturati; funziona su ≥2 wiki diversi.

### Tracciabilità requisito → user story

| Requisito | User Story |
|---|---|
| REQ-001/002/003/004/005/052/064 (lint+report+coperture) | US1 |
| REQ-053 + NFR-07/08 (gate ricorrente) | US2 |
| REQ-006/010..013 (indice + `--fix`) | US3 |
| REQ-060/061/062/063/065 (doc ufficiale + distillazione) | US4 |
| REQ-020/021/022 (contraddizioni) | US5 |
| REQ-040/041/050/051 (idempotenza/config/osservabilità) | trasversali (tutte) |

## Assumptions
- Il wiki target è conforme alle convenzioni di FEAT-003 (frontmatter, wikilink, cartelle).
- Le operazioni LLM-free (lint, orfani, indice, coperture, contraddizioni marcate) non richiedono provider; **solo** distillazione e contraddizioni semantiche richiedono l'`LLMProvider`.
- Le operazioni sono **funzioni di libreria** del core in questa feature; l'esposizione via CLI (`sertor wiki …`) è una feature successiva (DA-6).
- Il gate si **aggancia** a un hook di fase come default; il meccanismo preciso è design (DA-8).
- Tutti i test su **wiki sandbox** temporaneo (mai sul wiki di produzione).
