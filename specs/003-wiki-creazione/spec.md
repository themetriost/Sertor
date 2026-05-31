# Feature Specification: Skill — creare/indicizzare l'LLM Wiki

**Feature Branch**: `spec/003-wiki-creazione`

**Created**: 2026-05-31

**Status**: Draft

**Input**: Decomposizione di `requirements/sertor-core/wiki-creazione/requirements.md` (Deriva da
FEAT-003 dell'epica `sertor-core`). Il documento EARS è la fonte di dettaglio. Contesto generale:
`requirements/sertor-core/epic.md`. **Perimetro vincolato da DA-W1/DA-2** (`epic.md §9`): l'MVP è
**creare + indicizzare** il wiki nel RAG (ruolo 3). Vincoli architetturali:
`.specify/memory/constitution.md` (Principi III, IV, VI, VIII, IX). **Dipende da FEAT-001** per
l'indicizzazione (Gruppo Indicizzazione).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Inizializzare la struttura del wiki (Priority: P1)

Come maintainer di un nuovo progetto, creo da zero la **struttura standardizzata** del wiki (cartelle
tematiche, file fondamentali, convenzioni) in un'unica invocazione, senza sovrascrivere un wiki
esistente.

**Why this priority**: è il prerequisito di tutto; senza struttura non si può documentare né indicizzare.

**Independent Test**: invocare la skill su un repo privo di wiki e verificare la presenza e conformità
formale di `index.md`, `log.md` e delle cartelle tematiche; reinvocare su un wiki esistente e verificare
che non sovrascriva i contenuti.

**Acceptance Scenarios**:

1. **Given** un repository senza wiki, **When** si invoca la creazione, **Then** il sistema crea le
   cartelle tematiche (`concepts/`, `tech/`, `experiments/`, `sources/`, `syntheses/`) e i file
   `index.md` e `log.md` con contenuto iniziale valido.
2. **Given** un repository con un wiki esistente, **When** si reinvoca la creazione, **Then** il
   sistema **non** sovrascrive né tronca `index.md`/`log.md` e lascia intatto il contenuto pre-esistente.
3. **Given** una pagina nuova, **When** viene creata, **Then** ha frontmatter YAML (`title`, `type`,
   `tags`, `created`, `updated`, `sources`), nome in kebab-case nella sottocartella corretta e usa
   wikilink `[[...]]` per i cross-riferimenti.

### User Story 2 - Documentare in continuo (record) (Priority: P1)

Come agente LLM (attore primario), invoco l'operazione **record** con un brief strutturato (attività o
decisione) e ottengo la creazione/aggiornamento della pagina tematica, l'aggiornamento dell'indice e
una voce nel log — senza duplicati.

**Why this priority**: è il flusso minimo che alimenta il wiki in modo programmatico e riproducibile.

**Independent Test**: invocare record con un brief e verificare che la pagina corretta sia creata/
aggiornata, che `index.md` includa il link e che `log.md` abbia esattamente una nuova voce; reinvocare
con input identico e verificare l'assenza di duplicati.

**Acceptance Scenarios**:

1. **Given** un brief di attività/decisione, **When** si invoca record, **Then** il sistema crea o
   aggiorna la pagina del tema senza creare pagine duplicate per lo stesso tema.
2. **Given** un record completato, **When** termina, **Then** `index.md` include link + sommario di
   una riga della pagina nuova e `log.md` riceve **esattamente una** voce `## [YYYY-MM-DD] record | <titolo>`.
3. **Given** un record invocato due volte con input identico su wiki invariato, **When** si confronta
   l'esito, **Then** è identico alla prima esecuzione (nessun duplicato di pagina/voce di log).

### User Story 3 - Indicizzare il wiki nel RAG (Priority: P1)

Come maintainer, indicizzo le pagine del wiki nel **corpus documentale del RAG** così che diventino
interrogabili insieme ai sorgenti — come **corpus paritario**, senza boost di ranking.

**Why this priority**: è la definizione stessa del confine MVP secondo DA-W1 (*creare + indicizzare*);
rende la conoscenza distillata recuperabile dal retrieval.

**Independent Test**: con un wiki esistente e un RAG configurato, eseguire l'indicizzazione e verificare
che una query documentale pertinente restituisca pagine del wiki.

**Acceptance Scenarios**:

1. **Given** un wiki e un RAG configurato, **When** si esegue l'indicizzazione, **Then** tutte le
   pagine Markdown sotto la radice del wiki sono ingerite nel corpus con metadati che le identificano
   come documenti wiki, e l'operazione conferma il numero di documenti ingeriti.
2. **Given** un corpus che già contiene chunk del wiki, **When** si reindicizza, **Then** il sistema
   esegue un **full rebuild** senza creare duplicati per lo stesso file.
3. **Given** il RAG non configurato/irraggiungibile, **When** si tenta l'indicizzazione, **Then** il
   sistema annulla l'operazione con un errore leggibile, senza corrompere lo stato dell'indice esistente.
4. **Given** chunk del wiki e chunk dei sorgenti nel corpus, **When** si interroga, **Then** ai chunk
   del wiki è assegnato lo **stesso peso** di ranking (nessun boost semantico).

### User Story 4 - Idempotenza delle operazioni (Priority: P1)

Come maintainer, rieseguo qualunque operazione del wiki sullo stesso input e ottengo un risultato
**stabile**: nessun file nuovo, nessuna voce di log duplicata, nessuna modifica allo stato dell'indice.

**Why this priority**: senza idempotenza il wiki diverge e degrada il RAG documentale (Principio VI,
CS-3).

**Independent Test**: eseguire due volte creazione/record/indicizzazione su input invariato e verificare
l'identità degli esiti (hash dei file invariato; stato indice invariato).

**Acceptance Scenarios**:

1. **Given** un'operazione (creazione/record/ingest/distillazione/indicizzazione) su input invariato,
   **When** la si esegue più volte, **Then** l'esito è identico alla prima esecuzione.
2. **Given** una reindicizzazione di un file invariato, **When** la si esegue, **Then** l'id del chunk
   (path relativo del file wiki) resta stabile, senza generare una nuova identità.

### User Story 5 - Ingest di fonti esterne (Priority: P2)

Come agente LLM, invoco **ingest** con una fonte esterna (riassunto) e ottengo una pagina in `sources/`,
la propagazione dei riferimenti nelle pagine correlate e l'aggiornamento di indice e log, con
segnalazione esplicita di eventuali contraddizioni.

**Why this priority**: aggiunge valore ma l'MVP può funzionare col solo record; caso d'uso meno frequente.

**Independent Test**: invocare ingest con una fonte e verificare la pagina `sources/`, i riferimenti
propagati e la voce di log `ingest`; con una fonte che contraddice una pagina, verificare la marcatura
esplicita.

**Acceptance Scenarios**:

1. **Given** una fonte esterna, **When** si invoca ingest, **Then** il sistema crea/aggiorna una pagina
   `sources/` con il riassunto e il riferimento alla fonte nel frontmatter.
2. **Given** una fonte che contraddice una pagina esistente, **When** si esegue ingest, **Then** il
   sistema marca esplicitamente la contraddizione nella pagina interessata prima di aggiornarla.

### User Story 6 - Distillare conversazioni/sessioni (Priority: P2)

Come agente LLM, fornisco un **brief/riassunto già condensato** di una conversazione e ottengo una
pagina di distillazione conforme alle convenzioni, registrata nel log. La skill **non** elabora
trascrizioni grezze (la pre-elaborazione spetta all'agente chiamante).

**Why this priority**: capacità di alto valore ma dipende dal LLM ed è più complessa da rendere
idempotente; segue i Must.

**Independent Test**: fornire un brief condensato e verificare che la pagina prodotta rispetti
frontmatter/wikilink/kebab-case/posizione tematica e sia registrata nel log.

**Acceptance Scenarios**:

1. **Given** un brief condensato di una conversazione (non una trascrizione grezza), **When** si invoca
   la distillazione, **Then** il sistema produce una pagina che cattura decisioni/concetti/esiti chiave
   nella cartella tematica corretta e ne registra la voce nel log.
2. **Given** nessun LLM configurato, **When** si invoca la distillazione, **Then** l'operazione è
   bloccata con un errore esplicito.

### Edge Cases

- Radice del wiki vuota o senza file Markdown → indicizzazione conclusa con avviso, indice RAG immutato.
- Distillazione rieseguita: l'idempotenza riguarda la **struttura** (no pagine/voci duplicate), non il
  contenuto generato dall'LLM (che può variare se la pagina non esiste ancora).
- Operazioni strutturali (creazione, record, indicizzazione) **senza** LLM configurato → consentite
  (solo la distillazione richiede l'LLM).
- Test eseguiti su un wiki temporaneo/sandbox, mai sul wiki di produzione.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All'invocazione su un repository senza wiki, il sistema MUST creare la struttura di
  directory tematiche e i file `index.md`/`log.md` con contenuto valido minimo.
- **FR-002**: Se esiste già un wiki con `index.md`/`log.md`, il sistema MUST NOT sovrascriverli o
  troncarli, lasciando intatto il contenuto pre-esistente.
- **FR-003**: Ogni pagina nuova MUST avere frontmatter YAML (`title`, `type`, `tags`, `created`,
  `updated`, `sources`), nome kebab-case nella sottocartella corretta e wikilink `[[...]]` per i riferimenti.
- **FR-004**: All'operazione record con un brief, il sistema MUST creare/aggiornare la pagina del tema
  senza duplicati, aggiornare `index.md` e appendere **esattamente una** voce a `log.md`.
- **FR-005**: All'operazione ingest con una fonte, il sistema MUST creare/aggiornare una pagina
  `sources/`, propagare i riferimenti nelle pagine correlate esistenti, aggiornare indice e log, e
  marcare esplicitamente eventuali contraddizioni.
- **FR-006**: Alla distillazione con un **brief condensato** (non una trascrizione grezza), il sistema
  MUST produrre una pagina conforme alle convenzioni e registrarla nel log; MUST NOT gestire il
  chunking/suddivisione dell'input nell'MVP; MUST bloccarsi con errore esplicito se nessun LLM è configurato.
- **FR-007**: All'indicizzazione, il sistema MUST ingerire tutte le pagine Markdown sotto la radice del
  wiki nel corpus RAG configurato, con metadati che le identificano come documenti wiki, e confermare
  il numero di documenti ingeriti.
- **FR-008**: Alla reindicizzazione, il sistema MUST eseguire un **full rebuild** senza creare chunk
  duplicati per lo stesso file; l'identificatore del chunk MUST essere il path relativo del file wiki.
- **FR-009**: Il sistema MUST assegnare ai chunk del wiki lo **stesso peso** di ranking degli altri
  chunk del corpus (nessun boost semantico).
- **FR-010**: Se il RAG è non configurato/irraggiungibile o la radice wiki è vuota, il sistema MUST
  segnalare un errore/avviso esplicito senza corrompere lo stato dell'indice esistente.
- **FR-011**: Qualunque operazione eseguita più volte su input invariato MUST produrre un esito
  identico alla prima esecuzione (idempotenza strutturale).
- **FR-012**: Il sistema MUST operare su qualunque repository target senza dipendere dalla sua struttura
  interna; il percorso del wiki e il RAG di destinazione MUST essere configurabili senza modifiche al codice.
- **FR-013**: Il sistema MUST emettere log strutturati per ogni operazione (operazione, file coinvolti, esito).

### Key Entities

- **Wiki**: struttura Markdown (indice, log, cartelle tematiche) con convenzioni (frontmatter, wikilink, kebab-case).
- **Pagina**: unità di conoscenza tematica; attributi: frontmatter, tipo, backlink.
- **Voce di log**: riga append-only `## [YYYY-MM-DD] <operazione> | <titolo>`.
- **Brief**: input condensato/strutturato per record/ingest/distillazione (prodotto dall'agente chiamante).
- **Chunk wiki nel RAG**: rappresentazione documentale della pagina nel corpus (id = path relativo), peso paritario.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Dato un repo privo di wiki, la skill produce la struttura completa in **un'unica** invocazione.
- **SC-002**: Una seconda invocazione su input invariato lascia i file **identici** (hash invariato),
  senza duplicati (idempotenza).
- **SC-003**: Dopo record/ingest, l'indice riflette le nuove pagine e il log contiene la nuova voce.
- **SC-004**: Dato un wiki e un RAG configurato, dopo l'indicizzazione una query documentale pertinente
  restituisce pagine del wiki.
- **SC-005**: La skill funziona senza modifiche su **≥2 repository** diversi (repo-agnosticità).
- **SC-006**: Il **100%** delle operazioni emette log strutturati con esito.

## Assumptions

- L'attore primario è l'**agente LLM**; l'input di record/ingest/distillazione è un **brief condensato**
  (umano può invocare attraverso lo stesso canale). Nessun percorso in linguaggio naturale grezzo nell'MVP.
- Le pagine wiki sono in Markdown; altri formati sono fuori ambito.
- La struttura delle cartelle tematiche è **fissa** nell'MVP (configurabilità per progetto post-MVP).
- L'indicizzazione (Gruppo E) dipende da **FEAT-001**; le operazioni strutturali (creazione, record,
  ingest, distillazione) sono sviluppabili/testabili in isolamento.
- **Fuori ambito MVP** (DA-W1/DA-2): superficie wiki-nativa (query precisa, contesto iniettato),
  meccanismo di iniezione del contesto (host), spider/lint (FEAT-007), arricchimento bidirezionale (FEAT-008).
- Provider LLM necessario **solo** per la distillazione; le altre operazioni sono LLM-free.
