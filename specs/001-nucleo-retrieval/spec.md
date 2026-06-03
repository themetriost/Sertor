# Feature Specification: Nucleo di retrieval condiviso

**Feature Branch**: `spec/001-nucleo-retrieval`

**Created**: 2026-05-31

**Status**: Draft

**Input**: Decomposizione di `requirements/sertor-core/nucleo-retrieval/requirements.md` (Deriva da
FEAT-001 dell'epica `sertor-core`). Il documento EARS è la fonte di dettaglio; questa spec ne
riformula il *cosa/perché* in user story, scenari di accettazione, requisiti funzionali e criteri di
successo misurabili. Contesto generale: `requirements/sertor-core/epic.md`. Vincoli architetturali:
`.specify/memory/constitution.md` (in particolare Principi I, II, VIII, IX).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ingestione repo-agnostica (Priority: P1)

Come maintainer (o motore consumatore), indico al nucleo un repository qualunque e ne ottengo la
**scoperta e lettura** di codice e documentazione, escludendo automaticamente artefatti, virtualenv
e file di segreti, così che i motori RAG possano indicizzarlo senza conoscere a priori la struttura
del progetto.

**Why this priority**: senza ingestione non esiste alcun corpus da indicizzare; è il primo anello
della catena e abilita la repo-agnosticità (CS-5 dell'epica).

**Independent Test**: puntare il nucleo su due codebase diverse (es. il prototipo stesso + un secondo
repo) e verificare che produca l'elenco dei documenti indicizzabili con identificatori stabili, senza
configurazione hardcoded e senza includere artefatti/segreti.

**Acceptance Scenarios**:

1. **Given** un repository arbitrario, **When** si avvia l'ingestione sulla sua radice, **Then** il
   sistema scopre tutti i file indicizzabili (codice + Markdown) e assegna a ciascuno un id stabile
   derivato dal path relativo.
2. **Given** un repository con virtualenv, artefatti e un file di segreti, **When** si esegue
   l'ingestione, **Then** quei file sono esclusi in base a una lista di esclusione configurabile.
3. **Given** un file illeggibile (encoding/permessi), **When** lo si incontra, **Then** il sistema lo
   salta registrando un warning con path e motivo e prosegue con gli altri.

### User Story 2 - Chunking code-aware multilinguaggio (Priority: P1)

Come motore consumatore, ottengo dai documenti dei **chunk ai confini sintattici** per un set di
linguaggi mainstream, con metadati strutturali stabili, e un **fallback testuale** per qualunque
altro linguaggio, così che il retrieval lavori su unità di codice coerenti.

**Why this priority**: la qualità del retrieval dipende dalla qualità dei chunk; il supporto
multilinguaggio dall'MVP è una decisione di ambito (set di 14 linguaggi).

**Independent Test**: dati file in più linguaggi del set, verificare che i chunk corrispondano a unità
sintattiche (funzioni/classi/metodi) con metadati (path, qualname, tipo, offset) e che un file in un
linguaggio fuori set ricada sul chunking dimensionale senza errore.

**Acceptance Scenarios**:

1. **Given** un file sorgente in un linguaggio del set MVP (Python, JS/TS, Java, C#, Go, C/C++, PHP,
   Ruby, PowerShell, Bash, T-SQL, PL/SQL), **When** lo si chunka, **Then** i chunk corrispondono a
   unità sintattiche complete con metadati strutturali stabili.
2. **Given** un file in un linguaggio fuori dal set, **When** lo si chunka, **Then** il sistema ricade
   sul chunking dimensionale (dimensione/overlap configurabili) senza sollevare errore.
3. **Given** un file Markdown, **When** lo si chunka, **Then** i chunk seguono i confini di heading e
   riportano la gerarchia di sezione.
4. **Given** lo stesso documento invariato, **When** lo si ri-chunka, **Then** gli identificatori dei
   chunk sono identici (idempotenza).

### User Story 3 - Embeddings via provider intercambiabili (Priority: P1)

Come operatore, scelgo **via configurazione** il provider di embeddings (almeno uno locale e almeno
uno cloud) senza modificare il codice, così da poter passare local↔cloud o cambiare vendor.

**Why this priority**: gli embeddings sono necessari per le modalità testuali; l'intercambiabilità
provider è cardine (Principi II e VIII).

**Independent Test**: produrre vettori con un provider locale e con un provider cloud cambiando solo
la configurazione; in modalità local-only verificare l'assenza di chiamate di rete cloud.

**Acceptance Scenarios**:

1. **Given** un provider configurato, **When** si richiede l'embedding di una lista di testi, **Then**
   il sistema restituisce i vettori elaborandoli a batch (dimensione del batch configurabile).
2. **Given** una configurazione local-only, **When** si producono embeddings, **Then** non viene
   avviata alcuna connessione di rete verso servizi cloud.
3. **Given** il provider non disponibile o in errore, **When** si richiede un embedding, **Then** il
   sistema solleva un errore strutturato che identifica provider, causa e ritentabilità.

### User Story 4 - Persistenza e interrogazione via astrazione del vector store (Priority: P1)

Come motore consumatore, **persisto e interrogo** i chunk indicizzati attraverso un'unica astrazione
di vector store, con backend locale e cloud selezionabili via configurazione e collezioni namespaced
per corpus, così che indici di repository diversi coesistano senza interferenze.

**Why this priority**: è il sostrato di persistenza/ricerca su cui poggia ogni modalità testuale.

**Independent Test**: indicizzare due corpora distinti in collezioni namespaced sullo stesso store e
verificare che le query di uno non restituiscano risultati dell'altro; ripetere con un secondo backend
cambiando solo la configurazione.

**Acceptance Scenarios**:

1. **Given** un backend configurato, **When** si memorizzano chunk con vettori e metadati, **Then**
   sono interrogabili per similarità vettoriale.
2. **Given** due corpora diversi, **When** si indicizzano in namespace distinti, **Then** le query di
   un corpus non restituiscono chunk dell'altro.
3. **Given** il backend non disponibile, **When** si interroga, **Then** il sistema solleva un errore
   strutturato (backend + causa) senza restituire silenziosamente risultati vuoti.

### User Story 5 - Facade di retrieval riusabile come libreria (Priority: P1)

Come agente LLM o motore consumatore, interrogo il corpus attraverso un **unico punto d'accesso**
stabile (ricerca su codice, su documentazione, combinata), indipendente dal backend sottostante e
**importabile come componente** senza conoscere i dettagli di store/embeddings.

**Why this priority**: è l'interfaccia che rende il nucleo *riusabile come libreria* (REQ-E1) e su cui
tutti i motori si appoggiano (Principio I).

**Independent Test**: da un modulo consumatore, importare la facade e ottenere risultati pertinenti su
query note con metadati stabili, senza accedere a store/embeddings; verificare il comportamento su
indice vuoto.

**Acceptance Scenarios**:

1. **Given** un indice popolato, **When** si interroga la facade (codice/doc/combinata) con un `k`
   configurabile, **Then** restituisce per ogni risultato testo, path, id del chunk, tipo
   (codice/doc) e punteggio di pertinenza.
2. **Given** una richiesta filtrata per tipo (solo codice / solo doc), **When** si interroga, **Then**
   i risultati rispettano il filtro senza richiedere strutture d'indice separate.
3. **Given** un indice vuoto o non inizializzato, **When** si interroga, **Then** la facade restituisce
   un risultato vuoto segnalando l'assenza d'indice con un warning strutturato, senza eccezioni
   non gestite.

### User Story 6 - Configurazione centralizzata e osservabilità (Priority: P2)

Come operatore, governo **tutte** le scelte (provider, backend, percorsi, parametri di chunking, `k`,
batch, esclusioni) da un'**unica configurazione** senza toccare il codice, e ottengo **log strutturati**
a runtime per diagnosticare i fallimenti.

**Why this priority**: trasversale e abilitante (Principi VIII e IX); non blocca le singole capacità
ma è parte della definizione di "production-grade".

**Independent Test**: cambiare ambiente/provider/parametri solo via configurazione e verificare il
comportamento atteso; ispezionare i log di un'indicizzazione e di una query e trovare i campi richiesti.

**Acceptance Scenarios**:

1. **Given** una configurazione centralizzata, **When** si cambia provider o parametro, **Then** il
   comportamento cambia senza modifiche al codice e senza default hardcoded nei componenti.
2. **Given** un'operazione di indicizzazione o di retrieval, **When** viene eseguita, **Then** emette
   log strutturati con almeno: operazione, provider/backend, numero di documenti/chunk, dimensione
   dell'embedding, tempi ed eventuali errori, **senza** segreti nei log.

### Edge Cases

- Repository senza file di codice né Markdown → ingestione completa con corpus vuoto e avviso, senza errore.
- File con linguaggio non rilevabile → trattato come testo, mai scartato silenziosamente.
- Re-indicizzazione su corpus invariato → stesso insieme di chunk (idempotenza), nessun duplicato.
- Segreto richiesto da un componente → letto solo da ambiente/file non versionato; mai scritto su path versionato.
- Query con `k` superiore ai chunk disponibili → restituisce tutti i risultati disponibili senza errore.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il sistema MUST scoprire e leggere i file indicizzabili (codice + Markdown) di un
  repository qualunque dato il path di radice, senza conoscenza a priori della sua struttura.
- **FR-002**: Il sistema MUST escludere dall'indicizzazione i file/cartelle che corrispondono a una
  lista di esclusione **configurabile** (virtualenv, artefatti, binari, directory VCS, pattern di segreti).
- **FR-003**: Il sistema MUST saltare i file illeggibili registrando un warning (path + causa) e proseguire.
- **FR-004**: Il sistema MUST assegnare a ogni documento un identificatore stabile derivato dal path
  relativo, tale che la re-ingestione produca gli stessi id per i file invariati.
- **FR-005**: Il sistema MUST chunkare il codice ai confini sintattici per il set MVP di linguaggi
  (Python, JS/TS, Java, C#, Go, C/C++, PHP, Ruby, PowerShell, Bash, T-SQL, PL/SQL) con metadati
  strutturali stabili, ed essere estendibile ad altri linguaggi come incremento.
- **FR-006**: Il sistema MUST ricadere su chunking dimensionale (dimensione/overlap configurabili)
  per i linguaggi fuori dal set, senza errore.
- **FR-007**: Il sistema MUST chunkare la documentazione Markdown ai confini di heading con la
  gerarchia di sezione, e assegnare a ogni chunk un id stabile.
- **FR-008**: Il sistema MUST esporre un'unica interfaccia di embeddings con almeno un provider locale
  e almeno uno cloud, selezionabili via configurazione, con elaborazione a batch.
- **FR-009**: Il sistema MUST esporre un'unica astrazione di vector store (memorizza/aggiorna/interroga)
  con almeno un backend locale e uno cloud selezionabili via configurazione, e collezioni namespaced
  per corpus.
- **FR-010**: Il sistema MUST esporre una facade di retrieval unica e stabile con le operazioni:
  ricerca su codice, su documentazione e combinata; ogni risultato riporta testo, path, id del chunk,
  tipo e punteggio; supporta `k` configurabile e filtro per tipo.
- **FR-011**: Il sistema MUST essere utilizzabile come componente/libreria importabile dai consumatori
  (motori RAG, skill wiki, layer CLI) senza accedere ai dettagli di store/embeddings.
- **FR-012**: In caso di indisponibilità di provider o backend, il sistema MUST sollevare un errore
  strutturato (identità + causa) senza restituire silenziosamente risultati vuoti né lasciare stato parziale.
- **FR-013**: Il sistema MUST leggere tutte le scelte (provider, backend, percorsi, parametri di
  chunking, `k`, batch, esclusioni) da un'unica configurazione centralizzata, senza default hardcoded.
- **FR-014**: In modalità local-only il sistema MUST operare senza alcuna chiamata di rete verso cloud.
- **FR-015**: Il sistema MUST emettere log strutturati a runtime sia in indicizzazione sia in
  retrieval (operazione, provider/backend, conteggi, dimensione embedding, tempi, errori), senza segreti.
- **FR-016**: Il sistema MUST leggere i segreti esclusivamente da variabili d'ambiente o file non
  versionati e MUST NOT scriverli su alcun path versionato.

### Key Entities

- **Documento**: unità ingerita (codice o doc); attributi: path relativo (id stabile), tipo, linguaggio/markup.
- **Chunk**: porzione indicizzabile di un documento; attributi: id stabile, testo, metadati strutturali
  (qualname, tipo di nodo, offset / gerarchia heading), riferimento al documento.
- **Vettore + metadati**: rappresentazione del chunk nel vector store, dentro una collezione namespaced per corpus.
- **Risultato di retrieval**: testo, path, id del chunk, tipo (codice/doc), punteggio di pertinenza.
- **Configurazione**: insieme centralizzato di scelte (provider, backend, percorsi, parametri, esclusioni).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Il nucleo ingesta, chunka e indicizza **≥2 codebase distinte** senza modifiche al codice
  (es. il prototipo + un secondo repo), a dimostrazione della repo-agnosticità.
- **SC-002**: Il provider di embeddings è commutabile **locale↔cloud** modificando **solo** la
  configurazione, con risultati semanticamente equivalenti su query note.
- **SC-003**: Il backend di vector store è commutabile tra **≥2 opzioni** (locale embedded e cloud)
  modificando solo la configurazione.
- **SC-004**: La facade restituisce risultati pertinenti su un set di query note rispetto a un corpus
  campione; la pertinenza è **misurata** (precision@k) con il prototipo come baseline e la soglia di
  accettazione fissata in fase di design.
- **SC-005**: Ogni capacità del nucleo è coperta da test automatici; una re-indicizzazione su corpus
  invariato produce lo **stesso** insieme di chunk (idempotenza).
- **SC-006**: In modalità local-only si registrano **0** chiamate di rete verso servizi cloud.
- **SC-007**: Il **100%** delle operazioni di indicizzazione e retrieval emette log strutturati con i
  campi richiesti, senza segreti.

## Assumptions

- Il repository target è accessibile in lettura dal file system locale; repository remoti (clone da
  URL) sono fuori ambito di questa feature.
- Il corpus dell'MVP è composto da file di testo (codice + Markdown); formati non-testo
  (PDF/DOCX/notebook) sono fuori MVP.
- Le soglie numeriche di performance e pertinenza non sono fissate qui: si fissano in fase di design,
  con il prototipo come baseline (decisione "misurare prima").
- La configurazione del provider LLM/embeddings e del backend è **letta** dal nucleo ma **definita**
  a livello di epica `sertor-cli`; il nucleo non la duplica.
- L'aggiornamento incrementale dell'indice è fuori MVP (full re-index); l'incrementale è manutenzione
  (FEAT-009).
