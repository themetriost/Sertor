# Feature Specification: Nucleo wiki deterministico host-agnostico (FEAT-003-D)

**Feature Branch**: `spec/006-nucleo-wiki-deterministico`

**Created**: 2026-06-05

**Status**: Draft

**Input**: Decomposizione di FEAT-003 (consolidato FEAT-003 ⊕ FEAT-010 in
`requirements/sertor-core/wiki-creazione/requirements.md`): la **metà deterministica** del LLM Wiki,
separata dalla metà di giudizio (LLM) lungo il confine di delega. Tracker della metà LLM:
`requirements/sertor-core/wiki-llm/TODO.md`.

## Panoramica

Questa feature fornisce il **nucleo deterministico** delle operazioni del LLM Wiki: tutto ciò che è
**meccanico** (struttura, convenzioni, registri, ricerca di lavoro pendente, lint strutturale,
orchestrazione dell'indicizzazione) e che **non richiede alcun giudizio LLM**. È **guidato dalla
configurazione dell'ospite**: lo stesso nucleo opera su qualsiasi progetto (con codice e doc, solo
doc, solo codice) cambiando **soltanto** un file di configurazione, senza alcuna assunzione
hard-coded sul progetto. Espone risultati **strutturati e leggibili da una macchina**, consumati
dalle superfici sottili (skill, hook) e dalla metà LLM (FEAT-003-N), che vi costruisce sopra (DRY).

Vincolo architetturale dominante: **Principio X** della costituzione (host-agnostico, NON-NEGOZIABILE).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Configura, non presumere: stesso nucleo su ospiti diversi (Priority: P1)

Un manutentore porta la capacità wiki su un progetto qualsiasi fornendo **solo** un file di
configurazione (radice del wiki, tassonomia, cartelle-sorgente, lingua, profilo dell'ospite). Il
nucleo legge la config e opera senza alcun percorso o nome hard-coded; inoltre, su richiesta,
**segnala se c'è lavoro non ancora registrato** nel wiki (confronto tra modifiche recenti delle
fonti e l'ultima voce del registro).

**Why this priority**: è la prova vivente del Principio X e l'accoppiamento più isolato (sostituisce
la logica oggi cablata nell'hook di "lavoro pendente"). Senza questo, niente è host-agnostico.

**Independent Test**: si esegue l'operazione di "ricerca lavoro pendente" su Sertor stesso e su un
ospite finto "solo-doc" (radice e cartelle-sorgente diverse, lingua diversa) usando **lo stesso
nucleo immodificato**, cambiando **solo** la configurazione; entrambi producono un conteggio e un
messaggio coerenti con la rispettiva config.

**Acceptance Scenarios**:

1. **Given** una configurazione valida che descrive l'ospite, **When** si invoca la ricerca di
   lavoro pendente, **Then** il sistema riporta quanti file-sorgente sono più recenti dell'ultima
   voce di registro, nella lingua e con i percorsi della configurazione.
2. **Given** due configurazioni diverse (un ospite "code+doc" e uno "solo-doc"), **When** si esegue
   la stessa operazione su entrambi, **Then** il comportamento si adatta **senza modifiche al corpo**
   della capacità, solo in base alla configurazione.
3. **Given** una configurazione mancante o malformata, **When** si invoca un'operazione, **Then** il
   sistema fallisce in modo **esplicito** con un messaggio azionabile, senza stato parziale.

---

### User Story 2 — Struttura e convenzioni del wiki, in modo non distruttivo (Priority: P2)

Su un progetto senza wiki, il nucleo **inizializza** la struttura (cartelle tematiche + file indice e
registro) in modo idempotente e **non sovrascrive** un wiki preesistente. Sa inoltre **validare** che
le pagine rispettino le convenzioni (frontmatter richiesto, wikilink, naming, collocazione tematica).

**Why this priority**: è il prerequisito strutturale su cui poggiano record/lint/indicizzazione, ed è
interamente deterministico.

**Independent Test**: su una cartella temporanea vuota, l'inizializzazione crea la struttura attesa
dalla config; rieseguirla non cambia nulla; su un wiki con indice/registro esistenti, non li tocca; la
validazione segnala pagine con frontmatter incompleto o naming errato.

**Acceptance Scenarios**:

1. **Given** un repository senza wiki e una config, **When** si inizializza, **Then** si crea la
   struttura (cartelle della tassonomia + indice + registro) con contenuto minimo valido.
2. **Given** un wiki con indice/registro già presenti, **When** si inizializza di nuovo, **Then** i
   contenuti preesistenti restano intatti.
3. **Given** una pagina priva di campi frontmatter richiesti o con naming non conforme, **When** si
   valida, **Then** il sistema la segnala con il dettaglio della non conformità.

---

### User Story 3 — Lint strutturale (meccanico) del wiki (Priority: P2)

Il nucleo esegue un **lint deterministico** del wiki e ne riporta i difetti strutturali: **link
interni rotti**, **pagine orfane** (non raggiungibili dall'indice/altre pagine), **frontmatter
mancante/incompleto**. Non esprime alcun giudizio di merito sul contenuto (le contraddizioni e i
claim superati sono giudizio LLM, FEAT-003-N).

**Why this priority**: alto valore di manutenzione, completamente meccanico, separabile.

**Independent Test**: su un wiki-fixture con difetti iniettati (un wikilink verso una pagina
inesistente, una pagina orfana, una pagina senza frontmatter), il lint li rileva tutti e solo quelli.

**Acceptance Scenarios**:

1. **Given** un wikilink che punta a una pagina inesistente, **When** si esegue il lint, **Then** è
   riportato come link rotto con pagina e bersaglio.
2. **Given** una pagina non referenziata da nessuna altra né dall'indice, **When** si esegue il lint,
   **Then** è riportata come orfana.

---

### User Story 4 — Mappa delle pagine e registri idempotenti (Priority: P3)

Il nucleo **enumera** le pagine del wiki con i loro metadati (una mappa strutturata, senza il
contenuto integrale) per orientare i consumatori, e gestisce in modo **deterministico e idempotente**
le scritture meccaniche di registro/indice: appendere **una** voce di registro nel formato
configurato, inserire link+sommario nell'indice, con **identità stabile** delle pagine basata sul
percorso relativo.

**Why this priority**: abilita le operazioni LLM (che decidono *cosa* scrivere) fornendo il *dove/come*
deterministico; utile ma non bloccante per l'MVP.

**Independent Test**: l'enumerazione su un wiki noto restituisce la mappa attesa; due esecuzioni
identiche di append-registro/aggiorna-indice su input invariato producono un risultato identico
(nessun duplicato, nessun timestamp modificato).

**Acceptance Scenarios**:

1. **Given** un wiki con N pagine, **When** si enumera, **Then** si ottiene una mappa con percorso,
   tipo, titolo e metadati di ciascuna pagina, senza il corpo.
2. **Given** la stessa voce da registrare due volte su un wiki invariato, **When** si applica, **Then**
   il risultato è identico alla prima volta (idempotenza).

---

### User Story 5 — Orchestrazione dell'indicizzazione a collezioni separate (Priority: P3)

Il nucleo orchestra l'indicizzazione del wiki in una **collezione separata** dalle sorgenti, **rigenerabile
indipendentemente** (ricostruire una non tocca l'altra). L'indicizzazione riusa il motore di retrieval
del core (la chiamata al provider di embeddings è un dettaglio degli adapter, non un giudizio LLM).

**Why this priority**: completa il quadro deterministico ma dipende dal nucleo di retrieval esistente;
incrementale rispetto all'MVP.

**Independent Test**: indicizzando due corpora (wiki e sorgenti) in collezioni distinte, una rigenerazione
del wiki lascia invariata la collezione delle sorgenti.

**Acceptance Scenarios**:

1. **Given** wiki e sorgenti indicizzati separatamente, **When** si rigenera il solo wiki, **Then** la
   collezione delle sorgenti resta invariata.

### Edge Cases

- **Config assente/malformata** → errore esplicito e azionabile, nessuno stato parziale.
- **Cartella di tassonomia dichiarata ma assente sul disco** → avviso e salto, non errore fatale.
- **Wiki già esistente** → mai sovrascrittura silenziosa di indice/registro/pagine dell'utente.
- **File binario o non leggibile** in una cartella-sorgente → escluso, con segnalazione.
- **Wiki vuoto** (nessuna pagina) → operazioni terminano in modo pulito (conteggi a zero), non falliscono.
- **Profilo "solo-codice" o "solo-doc"** → l'insieme delle cartelle-sorgente si adatta dalla config (un ospite senza codice non richiede una cartella sorgenti).

## Requirements *(mandatory)*

### Functional Requirements

*(Ogni requisito qui deriva dal sottoinsieme deterministico del documento consolidato; la fonte è citata tra parentesi.)*

- **FR-001**: Il sistema MUST accettare **tutta** la specificità dell'ospite (radice del wiki, file indice/registro,
  tassonomia, cartelle-sorgente, esclusioni, lingua, profilo) da una **configurazione esterna**, senza alcun
  percorso o nome hard-coded nel corpo della capacità. *(REQ-006, FR-009)*
- **FR-002**: Il sistema MUST funzionare **senza alcun giudizio o chiamata LLM**: tutte le operazioni di questa
  feature sono deterministiche e ripetibili. *(confine di delega)*
- **FR-003**: Il sistema MUST inizializzare la struttura del wiki (cartelle della tassonomia + indice + registro)
  con contenuto minimo valido, **senza sovrascrivere** un wiki preesistente. *(REQ-001, REQ-002)*
- **FR-004**: Il sistema MUST validare che le pagine rispettino le convenzioni: presenza dei campi frontmatter
  richiesti, formato dei wikilink, naming, collocazione tematica. *(REQ-003, REQ-004, REQ-005)*
- **FR-005**: Il sistema MUST eseguire una **ricerca di lavoro pendente** confrontando le modifiche recenti delle
  cartelle-sorgente (con le esclusioni della config) rispetto all'ultima voce del registro, e riportarne il conteggio
  e un messaggio nella lingua configurata. *(sostituisce la logica dell'hook attuale)*
- **FR-006**: Il sistema MUST eseguire un **lint strutturale** del wiki rilevando link interni rotti, pagine orfane e
  frontmatter mancante/incompleto, **senza** valutazioni semantiche di contenuto. *(FR-006, parte meccanica)*
- **FR-007**: Il sistema MUST **enumerare** le pagine del wiki con i loro metadati (mappa strutturata, senza il corpo)
  a beneficio dei consumatori a valle.
- **FR-008**: Il sistema MUST gestire le scritture meccaniche di registro e indice (append di **una** voce nel formato
  configurato; inserimento di link+sommario nell'indice) in modo **idempotente**. *(REQ-011, REQ-012, REQ-013)*
- **FR-009**: Il sistema MUST usare il **percorso relativo** della pagina come **identità stabile** tra le esecuzioni,
  così che rieseguire su input invariato non generi nuove identità/duplicati. *(REQ-050, REQ-051)*
- **FR-010**: Il sistema MUST orchestrare l'indicizzazione del wiki in una **collezione separata** dalle sorgenti,
  **rigenerabile indipendentemente**. *(FR-010, FR-011)*
- **FR-011**: Il sistema MUST esporre i risultati delle operazioni in un **formato strutturato e leggibile da una
  macchina**, versionato, contenente metadati e riferimenti (non il contenuto integrale delle pagine), così che le
  superfici sottili e la metà LLM (FEAT-003-N) possano consumarli. *(contratto di consumo portabile, FR-027)*
- **FR-012**: Ogni operazione a runtime MUST emettere log strutturati (operazione, profilo, conteggi, esiti, errori),
  senza segreti. *(Principio IX)*

### Key Entities

- **Profilo dell'ospite (config)**: descrizione dichiarativa dell'ospite — radice del wiki, file indice/registro,
  tassonomia (nome→cartella→tipo), cartelle-sorgente + esclusioni, lingua, profilo (code+doc/solo-doc/solo-code),
  stringhe localizzate. È l'**unica** fonte di specificità dell'ospite.
- **Pagina del wiki**: un documento Markdown con frontmatter (campi richiesti), wikilink uscenti, percorso relativo
  (identità stabile), tipo/area tematica.
- **Risultato strutturato**: l'esito versionato di un'operazione (ricerca pendente, lint, enumerazione) — metadati e
  riferimenti, non il contenuto.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001 (host-agnosticità / Principio X)**: lo **stesso** nucleo immodificato esegue le sue operazioni su **≥2**
  profili d'ospite (Sertor "code+doc" e un ospite finto "solo-doc"), differendo **solo** per il file di configurazione.
- **SC-002 (idempotenza)**: rieseguire una qualsiasi operazione su input invariato produce un output **identico** —
  0 file duplicati, 0 voci di registro duplicate, 0 timestamp modificati su file invariati.
- **SC-003 (parità con l'hook)**: la ricerca di lavoro pendente su Sertor riproduce il **conteggio** dell'attuale hook
  di controllo, a parità di condizioni.
- **SC-004 (lint completo)**: su un wiki-fixture con difetti iniettati, il lint strutturale rileva **il 100%** dei
  difetti attesi (link rotti, orfani, frontmatter mancante) e **0** falsi positivi su un wiki pulito.
- **SC-005 (zero LLM / offline)**: tutte le operazioni della feature completano **senza rete e senza alcuna chiamata
  LLM**; sono verificabili in un ambiente isolato.
- **SC-006 (non distruttività)**: l'inizializzazione su un wiki esistente non modifica **alcun** file dell'utente.

## Assumptions

- I requisiti sono **già consolidati** in `requirements/sertor-core/wiki-creazione/requirements.md` (FEAT-003 ⊕
  FEAT-010): questa feature **non** li ri-elicita, ne implementa il sottoinsieme deterministico.
- La configurazione dell'ospite risiede in un percorso noto e **override-abile**; un default documentato (il profilo
  di Sertor) è un dato esterno sostituibile, non una costante nel corpo della capacità.
- Il nucleo **riusa** i componenti esistenti di `sertor-core` per configurazione, osservabilità ed errori, e — per
  l'indicizzazione — il motore di retrieval/embeddings esistente (la chiamata al provider è un dettaglio degli adapter,
  non un giudizio LLM).
- Le operazioni **di giudizio** (record-contenuto, distillazione, generazione, lint semantico, obsolescenza, gate al
  commit) sono **fuori ambito**: appartengono a FEAT-003-N e sono affrontate separatamente.
- La domanda aperta **FR-004** del documento consolidato (trigger esatto del popolamento) riguarda la metà LLM e **non
  vincola** questa feature.
