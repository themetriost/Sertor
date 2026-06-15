# Feature Specification: Installer di governance/SDLC `sertor-flow`

**Feature Branch**: `037-governance-sertor-flow`

**Created**: 2026-06-15

**Status**: Draft

**Input**: Deriva da FEAT-005 (epica `sertor-cli`). Requisiti:
`requirements/sertor-cli/governance-sertor-flow/requirements.md` (25 REQ EARS + 6 NFR, 7 domande
aperte tutte risolte).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Portare il metodo SDLC su un progetto con un comando (Priority: P1)

Come maintainer, voglio installare su un mio repository l'apparato di **metodo di sviluppo** di Sertor
(flusso SpecKit, gestione requisiti, delega git, costituzione-starter, blocco rituale nel `CLAUDE.md`)
con **un solo comando**, in modo che il progetto adotti lo stesso flusso di lavoro senza ricostruirlo a
mano e **senza** che il comando avvii da solo alcuna attività (install ≠ run).

**Why this priority**: è il valore centrale della feature. Senza questo, `sertor-flow` non esiste: tutto
il resto (indipendenza dal RAG, idempotenza, puntatore) qualifica *questo* atto.

**Independent Test**: su un repo pulito, eseguire il comando d'installazione e verificare che dopo
l'esecuzione sono presenti e invocabili tutte le superfici del metodo (skill/agenti SpecKit, skill
requisiti + agente analista, agente di delega git, template di metodo, costituzione-starter, blocco
rituale SDLC nel `CLAUDE.md`) e che **nessuna** fase SDLC, operazione git o indicizzazione è partita da
sola.

**Acceptance Scenarios**:

1. **Given** un repository ospite senza apparato di governance, **When** l'utente esegue il comando
   d'installazione di `sertor-flow`, **Then** il sistema deposita l'intero bundle di metodo e produce un
   resoconto che elenca ogni artefatto con il suo esito (creato/saltato/unito/blocco), senza eseguire
   alcuna fase SDLC né git.
2. **Given** un repository ospite, **When** l'installazione completa, **Then** è presente una
   **costituzione-starter neutra** (principi generali, non quelli RAG-specifici di Sertor),
   personalizzabile dall'ospite con la skill di costituzione.
3. **Given** un repository ospite il cui `CLAUDE.md` non esiste, **When** l'installazione gira,
   **Then** il `CLAUDE.md` è creato con il blocco rituale SDLC delimitato da marker.

---

### User Story 2 - Installare la governance senza il dominio RAG (Priority: P2)

Come maintainer di un progetto che **non** usa il RAG di Sertor, voglio installare solo il metodo SDLC
**senza** tirarmi dietro il core di retrieval, in modo che l'ambiente resti leggero e la governance —
ortogonale al RAG — non imponga dipendenze che non userò.

**Why this priority**: è la ragione architetturale della scissione in pacchetto separato. Distingue
`sertor-flow` da `sertor install wiki`/`rag` (che sono retrieval-backed).

**Independent Test**: in un ambiente in cui il core di retrieval **non** è installato, eseguire
l'installazione di `sertor-flow` e verificare che completa con successo, senza richiedere né risolvere
il pacchetto del core.

**Acceptance Scenarios**:

1. **Given** un ambiente privo del core di retrieval, **When** si installa `sertor-flow`, **Then**
   l'installazione riesce senza errori di dipendenza.
2. **Given** un ospite che vuole solo wiki o solo RAG, **When** installa quelle capacità, **Then** non
   riceve gli asset SDLC della governance (nessun accoppiamento tra i pacchetti).

---

### User Story 3 - Re-install idempotente e non distruttivo su repo esistente (Priority: P2)

Come maintainer di un progetto già avviato (con propri file, magari un `CLAUDE.md` che già contiene il
blocco Definition-of-Done del wiki), voglio poter (ri)eseguire l'installazione senza che sovrascriva i
miei file o duplichi blocchi, in modo da poterla rieseguire in sicurezza dopo un aggiornamento.

**Why this priority**: la sicurezza su repo esistente è condizione d'adozione; senza, l'installer è
inutilizzabile su progetti reali.

**Independent Test**: eseguire l'installazione due volte di fila e su un repo con file preesistenti, e
verificare che i file utente non sono modificati, che i blocchi a marker non sono duplicati e che la
seconda esecuzione non riporta modifiche per gli artefatti già presenti.

**Acceptance Scenarios**:

1. **Given** un repo dove alcuni artefatti del bundle esistono già, **When** si esegue l'installazione,
   **Then** quegli artefatti sono riportati come *saltati* e non sovrascritti.
2. **Given** un `CLAUDE.md` che contiene già il blocco wiki, **When** si installa `sertor-flow`,
   **Then** è aggiunto un blocco SDLC **distinto** (marker propri) senza toccare il blocco wiki.
3. **Given** un'installazione già completata, **When** la si riesegue, **Then** non sono riportate
   modifiche (idempotenza).
4. **Given** un passo d'installazione che fallisce, **When** l'errore occorre, **Then** il sistema si
   ferma indicando il passo fallito e lascia in posto gli artefatti già scritti (nessun rollback,
   nessuno stato parziale silenzioso).

---

### User Story 4 - Trovare la governance cercandola dall'ombrello (Priority: P3)

Come utente che conosce `sertor install <capacità>`, voglio che `sertor install governance` mi
**indirizzi** al pacchetto `sertor-flow`, in modo da non restare bloccato su uno stub o un errore secco.

**Why this priority**: preserva la coerenza della storia d'installazione senza accoppiare i pacchetti;
è una comodità, non un blocco.

**Independent Test**: invocare `sertor install governance` sull'ombrello e verificare che il messaggio
indica che la governance è fornita dal pacchetto separato `sertor-flow` e come installarlo, senza che
l'ombrello dipenda da `sertor-flow`.

**Acceptance Scenarios**:

1. **Given** il pacchetto ombrello installato, **When** l'utente esegue `sertor install governance`,
   **Then** riceve un messaggio che rimanda a `sertor-flow` e come ottenerlo (puntatore, non delega).

---

### Edge Cases

- **Ospite non-Windows (Linux/macOS):** il bundle deve includere entrambe le varianti di script
  (POSIX shell + PowerShell) così il metodo funziona indipendentemente dalla shell dell'ospite.
- **Costituzione già presente sull'ospite:** non sovrascriverla (riportata come *saltata*); l'ospite
  decide se rigenerarla con la skill di costituzione.
- **`.specify/` parzialmente presente** (alcuni template già lì): merge non distruttivo per-file
  (presenti → saltati), nessuna perdita.
- **Stato runtime nell'origine** (es. puntatore alla feature corrente): **non** deve essere distribuito
  all'ospite.
- **Asset di terze parti senza nota di licenza:** la distribuzione deve includere la nota MIT degli
  asset SpecKit vendored; un bundle privo della nota è un difetto.
- **Divergenza tra asset canonici e copia di sviluppo di Sertor:** deve essere intercettata da una
  guardia (l'ospite riceverebbe altrimenti una versione diversa da quella in uso).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il sistema MUST essere distribuibile come pacchetto installabile **separato** chiamato
  `sertor-flow`, con un proprio comando d'ingresso, distinto dal pacchetto ombrello `sertor`.
- **FR-002**: Il sistema MUST completare l'installazione **senza richiedere il core di retrieval**
  (nessuna dipendenza dal dominio RAG).
- **FR-003**: Quando l'utente esegue l'installazione su un repo target, il sistema MUST depositare il
  bundle di metodo **senza** avviare alcuna fase SDLC, operazione git o indicizzazione (install ≠ run).
- **FR-004**: In assenza di un target esplicito, il sistema MUST operare sulla directory di lavoro
  corrente.
- **FR-005**: Il sistema MUST derivare l'insieme degli artefatti dalla **composizione del bundle** (non
  da un conteggio fisso): aggiungere o togliere un asset cambia il piano automaticamente.
- **FR-006**: Il sistema MUST depositare le **skill e gli agenti SpecKit** (fasi
  specify/clarify/plan/tasks/analyze/checklist/implement/constitution/taskstoissues) e le **skill
  SpecKit-git** (feature/validate/remote/initialize/commit).
- **FR-007**: Il sistema MUST depositare la **skill di gestione requisiti** e l'**agente analista dei
  requisiti**.
- **FR-008**: Il sistema MUST depositare l'**agente di delega delle operazioni git**
  (configuration-manager).
- **FR-009**: Il sistema MUST depositare il **macchinario di metodo** (template, script in **entrambe**
  le varianti di shell, estensione git, workflow) nell'area `.specify/` dell'ospite.
- **FR-010**: Il sistema MUST fornire una **costituzione-starter neutra e host-agnostica** (solo
  principi ingegneristici generali, non quelli RAG-specifici di Sertor), che l'ospite personalizza con
  la skill di costituzione.
- **FR-011**: Quando l'installazione gira, il sistema MUST aggiungere al `CLAUDE.md` dell'ospite un
  **blocco rituale SDLC** delimitato da marker, **distinto** dall'eventuale blocco Definition-of-Done
  del wiki.
- **FR-012**: Il sistema MUST **generare per-host** i file di init/integrazione (che riflettono le
  scelte dell'ospite, es. tipo di assistente e di script), invece di copiare lo stato di Sertor.
- **FR-013**: Il sistema MUST **escludere** dalla distribuzione lo stato runtime (es. il puntatore alla
  feature corrente).
- **FR-014**: Se un file di destinazione esiste già, il sistema MUST NON sovrascriverlo e MUST riportarlo
  come *saltato*.
- **FR-015**: Quando il `CLAUDE.md` contiene già il blocco-marker SDLC, il sistema MUST NON duplicarlo.
- **FR-016**: Se un file strutturato viene unito, il sistema MUST fare un **merge additivo** senza
  rimuovere o sovrascrivere le voci esistenti dell'utente.
- **FR-017**: Quando l'installazione è rieseguita sullo stesso target, il sistema MUST riportare nessuna
  modifica per gli artefatti già presenti (idempotenza).
- **FR-018**: Il sistema MUST produrre un **resoconto d'installazione** che elenca ogni artefatto con il
  suo esito (creato/saltato/unito/blocco/errore).
- **FR-019**: Se un passo fallisce, il sistema MUST fermarsi **fail-fast**, identificare il passo
  fallito e lasciare in posto gli artefatti già scritti (nessun rollback).
- **FR-020**: Dove l'utente lo richiede, il sistema MUST poter emettere il resoconto in forma
  leggibile da macchina (JSON).
- **FR-021**: Gli asset host-facing MUST essere in **inglese** (host-agnostici), coerenti con
  l'installer esistente.
- **FR-022**: Il sistema MUST impacchettare gli asset SpecKit di terze parti a **versione pinnata** e
  MUST includere il testo della licenza MIT e la nota di copyright nel pacchetto e sull'ospite.
- **FR-023**: Quando l'utente esegue `sertor install governance` sull'ombrello, il sistema MUST
  riportare che la governance è fornita dal pacchetto separato `sertor-flow` e come installarlo,
  **senza** che `sertor` dipenda da `sertor-flow` (puntatore, non delega).
- **FR-024** *(Could)*: Dove l'utente richiede un sottoinsieme del bundle, il sistema potrà installare
  solo il sottoinsieme selezionato (selettività interna; fuori MVP).

### Key Entities *(include if feature involves data)*

- **Bundle di governance**: l'insieme degli asset di metodo distribuiti (skill/agenti SpecKit, skill
  requisiti + analista, agente di delega git, macchinario `.specify/`, costituzione-starter, blocco
  rituale). Composizione completa per l'MVP (all-or-nothing).
- **Artefatto d'installazione**: unità depositata con la propria regola di scrittura non distruttiva
  (crea-se-assente, merge additivo, blocco-a-marker, generazione, …) e un esito per-artefatto.
- **Resoconto d'installazione**: elenco degli esiti per-artefatto + indicazione dell'eventuale passo
  fallito; forma leggibile e forma JSON.
- **Costituzione-starter**: documento di principi generali host-agnostico, base personalizzabile.
- **Blocco rituale SDLC**: sezione a marker nel `CLAUDE.md` dell'ospite, owner della disciplina
  git/commit del flusso SDLC, distinta dal blocco wiki.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un utente installa `sertor-flow` con **un singolo comando** e ottiene il comando
  dedicato, su una macchina pulita, senza passi manuali aggiuntivi.
- **SC-002**: In **0** casi l'installazione avvia una fase SDLC, un'operazione git o un'indicizzazione.
- **SC-003**: Dopo l'install, **il 100%** delle superfici del bundle dichiarate è presente e
  invocabile sull'ospite.
- **SC-004**: L'installazione completa con successo in un ambiente in cui il core di retrieval **non** è
  presente (indipendenza dal RAG verificata).
- **SC-005**: Su un repo esistente, **0** file dell'utente vengono sovrascritti; una **seconda**
  esecuzione produce **0** modifiche sugli artefatti già presenti (idempotenza/non-distruttività).
- **SC-006**: L'installazione completa su **≥2** ospiti diversi (incl. ≥1 non-Windows) senza modifiche
  al corpo del codice, solo cambiando configurazione/ambiente.
- **SC-007**: Il pacchetto distribuito e l'ospite contengono la nota di licenza MIT degli asset SpecKit
  vendored (verificabile: file di attribuzione presente).
- **SC-008**: `sertor install governance` sull'ombrello rimanda a `sertor-flow` **senza** introdurre una
  dipendenza del pacchetto `sertor` da `sertor-flow`.

## Assumptions

- Il **motore di installazione** non distruttivo già esistente in Sertor (enumerazione artefatti,
  strategie di scrittura, esecuzione fail-fast, resoconto, sync con guardia anti-drift) è
  **riutilizzabile** da `sertor-flow` tramite estrazione in un componente condiviso **senza** dipendenza
  dal core di retrieval. *(Il come è materia del plan.)*
- Gli asset SpecKit sono di **GitHub spec-kit (licenza MIT, v0.8.18)** → **ridistribuibili** con
  inclusione della nota; la versione pinnata è una scelta voluta (riproducibilità del metodo).
- Le skill/agenti di metodo sono **asset di testo** deployabili con la stessa meccanica non distruttiva
  già usata per gli asset wiki.
- La costituzione-starter deriva dai principi **generali** della costituzione di Sertor (III/IV/VI/VII +
  kernel de-RAGizzati di I/V/VIII/IX + Sicurezza + Governance), **esclusi** II e X (RAG/mission).
- Distribuzione interim via `git+url` (PyPI fuori ambito).
- Fuori ambito (rinviati): selettività interna del bundle (FR-024, Could), ciclo di vita
  upgrade/uninstall (FEAT-008 `sertor-cli`), wizard di configurazione interattivo (FEAT-003), reviewer
  «clean code» attivo (capacità futura), hook di harness per la governance (Could).
