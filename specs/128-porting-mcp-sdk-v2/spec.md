# Feature Specification: Il server MCP funziona su entrambe le linee dell'SDK

**Feature Branch**: `128-porting-mcp-sdk-v2`

**Created**: 2026-09-13

**Status**: Draft

**Deriva da**: E10-FEAT-070 · **Requisiti**: [`requirements/debito-tecnico/feat-070-porting-mcp-sdk-v2/requirements.md`](../../requirements/debito-tecnico/feat-070-porting-mcp-sdk-v2/requirements.md)

**Input**: portare il server MCP `sertor_mcp` all'SDK MCP v2 (`mcp` 2.2.0) con import a doppia via, preservando il funzionamento sugli ospiti il cui lock è fermo sulla linea 1.x.

---

## Perché questa feature esiste

Il server MCP di Sertor è uno dei **due vehicles** che la capability `rag` promette all'ospite (l'altro
è la CLI). Da fine luglio, su un numero crescente di ospiti, **non parte affatto**: l'SDK a monte ha
pubblicato una major che rimuove il modulo su cui il server è costruito, e il nostro vincolo di
dipendenza non aveva un tetto. Chi risolve le dipendenze dopo quella data ottiene la major nuova, il
processo muore prima di servire il primo tool, e `doctor` resta verde.

Il tetto messo il 2026-08-07 ha fermato l'emorragia per le installazioni *future*. Non ha guarito
nessuno: **tre nodi della federazione** hanno misurato il guasto sul proprio host, e due di loro
lavorano **senza MCP da oltre un mese** (34 e 36 giorni, degradati a CLI). Nessuno dei tre è
un'installazione nuova: sono stati colpiti **ri-risolvendo il lock seguendo la nostra procedura di
upgrade**. Hanno anche rifiutato, a ragione, di rattopparsi da soli — il file che dovrebbero
modificare lo rigenera il nostro installer.

Questa feature è il rimedio che li raggiunge tutti: un server che funziona **su entrambe le linee**
guarisce anche un lock già congelato sulla major nuova, senza chiedere all'ospite nulla oltre
l'aggiornamento di Sertor.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — L'ospite già colpito riottiene i suoi tool (Priority: P1)

Un ospite il cui ambiente ha già risolto la major nuova aggiorna Sertor. Alla sessione successiva il
suo agente vede di nuovo i tool di ricerca e navigazione, **senza** che l'ospite abbia dovuto toccare
il proprio file di lock, aggiungere vincoli a mano o reinstallare da zero.

**Why this priority**: è l'unica storia che chiude il danno **in essere**. Le altre migliorano o
proteggono; questa restituisce una capacità che oggi, su host reali e noti per nome, non c'è.

**Independent Test**: si prepara un ambiente che risolve la major nuova, si installa questa versione e
si verifica che il server completi la connessione e dichiari i suoi tool. Verificabile da sola, e
consegna da sola tutto il valore per la popolazione colpita.

**Acceptance Scenarios**:

1. **Given** un ambiente in cui la libreria a monte è alla major nuova, **When** l'agente apre la
   sessione, **Then** il server risponde alla connessione e dichiara **dieci** tool con i nomi attesi.
2. **Given** un ambiente in cui la libreria a monte è alla linea precedente, **When** l'agente apre la
   sessione, **Then** il comportamento è identico al punto 1 — stessi nomi, stessi parametri, stesse
   forme di risultato.
3. **Given** un ospite colpito che aggiorna **solo** Sertor, **When** apre la sessione, **Then** i tool
   funzionano senza che abbia rigenerato il proprio lock.

---

### User Story 2 — Un guasto previsto dice all'agente *cosa* è rotto (Priority: P1)

L'agente invoca una ricerca su un progetto il cui indice non è ancora stato costruito, o la cui chiave
del provider è scaduta. Riceve un errore che **nomina il problema** («indice assente», «provider non
raggiungibile»), non un generico «il tool è fallito». Se invece fallisce qualcosa di **inatteso**,
riceve un errore che identifica il tool, e la diagnosi completa resta nei registri del server.

**Why this priority**: è la regola standing del progetto — *un errore è un segnale, non rumore*. Senza
questa storia il porting consegnerebbe un server funzionante che, quando qualcosa non va, **non lo
dice**: la condizione che ha reso questo stesso guasto invisibile per settimane.

**Independent Test**: si provoca un guasto previsto e si legge cosa arriva al chiamante; si provoca un
guasto inatteso e si verifica che il chiamante riceva l'identificazione del tool e che il dettaglio sia
registrato. Indipendente dalla Storia 1 e testabile su entrambe le linee.

**Acceptance Scenarios**:

1. **Given** un corpus senza indice, **When** l'agente invoca una ricerca, **Then** riceve un esito di
   errore il cui testo nomina la causa, su entrambe le linee.
2. **Given** un guasto inatteso dentro un tool, **When** l'agente lo invoca, **Then** riceve un esito di
   errore che identifica il tool, **e** l'evento di errore corrispondente è registrato con il dettaglio.
3. **Given** un guasto inatteso, **When** si esamina ciò che è arrivato al chiamante, **Then** non
   contiene il testo grezzo dell'eccezione interna.

---

### User Story 3 — Il ramo di compatibilità non marcisce (Priority: P2)

Un manutentore modifica il server mesi dopo il porting. Una verifica automatica gli dice se **entrambe**
le linee funzionano ancora, invece di dirgli che funziona quella che il suo ambiente ha risolto.

**Why this priority**: la compatibilità con due linee introduce un percorso alternativo che, se nessuna
esecuzione lo attraversa, si rompe in silenzio e lo scopre un ospite. È la lezione già pagata: *una
verifica che non può fallire ha lo stesso output di una che ha verificato tutto*.

**Independent Test**: si esegue la verifica in due ambienti che risolvono linee diverse e si controlla
che entrambe le esecuzioni siano avvenute (non salti, non esiti «non applicabile»).

**Acceptance Scenarios**:

1. **Given** la verifica automatica del progetto, **When** viene eseguita, **Then** i controlli sul
   server sono eseguiti **due volte**, una per linea supportata, e l'esito di ciascuna è leggibile.
2. **Given** un cambiamento che rompe una sola delle due linee, **When** la verifica viene eseguita,
   **Then** diventa rossa.

---

### User Story 4 — Chi installa oggi ottiene un server funzionante (Priority: P3)

Un progetto nuovo installa Sertor per la prima volta. Ottiene un server che parte, indipendentemente da
quale versione della libreria a monte il suo ambiente risolva fra quelle supportate.

**Why this priority**: oggi questa proprietà è garantita dal **tetto**, cioè dal vincolo che esclude la
major nuova. Dopo il porting è garantita dal **codice**, che è più robusto: il tetto diventa una scelta
di prudenza invece dell'unica difesa. Valore reale ma già coperto, quindi ultima.

**Independent Test**: installazione da zero in un ambiente pulito, verifica che il server risponda.

**Acceptance Scenarios**:

1. **Given** un host pulito, **When** si installa la capability di ricerca, **Then** il server risponde
   alla connessione e la documentazione utente dichiara quali versioni della libreria sono supportate.

---

### Edge Cases

- **Nessuna linea supportata disponibile** (libreria assente, o una major futura che non conosciamo):
  il fallimento deve **nominare la versione installata e l'intervallo supportato**, non presentarsi come
  un modulo interno mancante — che è esattamente il messaggio illeggibile con cui il guasto originale si
  è manifestato agli ospiti.
- **Guasto previsto sollevato fuori dal corpo di un tool** (durante il riscaldamento all'avvio, o in una
  struttura valutata dopo il ritorno): il server deve comunque partire, e l'errore azionabile deve
  arrivare alla prima invocazione anziché presentarsi come connessione caduta.
- **Superficie di memoria disattivata**: non è un guasto, è uno stato dichiarato; i tool relativi
  continuano a rispondere con il proprio stato invece di errori.
- **Comportamenti non misurati**: cancellazione di una richiesta, timeout, risultati molto grandi,
  invocazioni concorrenti. Le verifiche di questa feature coprono connessione, elenco dei tool, forma
  dei risultati ed errori. Il resto è **dichiarato non misurato**, non presunto equivalente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il server MUST esporre i suoi dieci tool con nomi, parametri, descrizioni e forme di
  risultato invariati, su qualunque linea supportata dell'SDK venga risolta.
- **FR-002**: All'avvio il server MUST ottenere la propria infrastruttura dalla linea più recente
  supportata e, se non disponibile, dalla precedente, senza che la scelta alteri la registrazione dei
  tool.
- **FR-003**: Se nessuna linea supportata è disponibile, il sistema MUST fallire dichiarando la versione
  installata e l'intervallo supportato.
- **FR-004**: Quando un tool incontra un **guasto previsto** (indice assente, provider non
  raggiungibile, componente opzionale mancante, indice bloccato), il server MUST restituire un esito di
  errore il cui contenuto porta il messaggio diagnostico d'origine, su **ogni** linea supportata.
- **FR-005**: Quando un tool incontra un guasto **non previsto**, il server MUST registrare l'evento di
  errore corrispondente e restituire un esito di errore che identifica il tool.
- **FR-005a** *(Optional feature — solo dove la linea risolta è la più recente)*: Where la linea nuova
  dell'SDK è quella risolta, il contenuto restituito al chiamante per un guasto **non previsto** MUST NOT
  contenere il testo grezzo dell'eccezione. *Sulla linea precedente questo non è ottenibile senza
  convertire ogni eccezione — scelta scartata in R-2 perché reintrodurrebbe l'inoltro che D-1 chiude e
  costerebbe la riscrittura di quattro test che presidiano il re-raise: la differenza resta, dichiarata.*
- **FR-006**: Il vincolo di dipendenza MUST ammettere entrambe le linee supportate fino alla minor
  verificata, in **tutti** i punti in cui è dichiarato, e MUST portare la ragione del limite e la
  condizione per alzarlo.
- **FR-007**: La verifica automatica MUST esercitare il server **parlando il protocollo** con un client
  reale, asserendo connessione, i dieci nomi, la forma del risultato di un tool e il contenuto
  diagnostico di un guasto previsto.
- **FR-008**: Il riscaldamento all'avvio e l'autodiagnosi MUST conservare la semantica attuale: non
  fatali, rumorosi sull'errore, mai impeditivi dell'avvio.
- **FR-009**: Gli eventi di osservabilità per invocazione MUST conservare nomi e campi attuali su
  entrambe le linee.
- **FR-010**: Quando un ospite il cui ambiente ha già risolto la major nuova aggiorna Sertor, il server
  MUST partire e servire i tool senza che l'ospite rigeneri il proprio lock.
- **FR-011**: La documentazione **utente** MUST dichiarare le versioni supportate e l'azione che deve
  compiere un ospite già colpito.
- **FR-012**: La verifica automatica MUST eseguire i controlli sul server su **entrambe** le linee
  supportate, così che nessuno dei due percorsi resti non attraversato.

### Key Entities

- **Linea supportata dell'SDK**: una delle due generazioni della libreria a monte con cui il server
  deve funzionare. Attributi osservabili: è disponibile o no; determina quale infrastruttura il server
  ottiene; **non** deve essere osservabile dal consumatore in nessun altro modo.
- **Esito di invocazione**: ciò che il chiamante riceve — un risultato, oppure un errore con un
  contenuto. Ha due varietà di errore, che questa feature rende distinte: *previsto* (porta la diagnosi)
  e *inatteso* (identifica il tool; la diagnosi vive nei registri).
- **Guasto previsto**: una condizione che il sistema sa descrivere e che l'utente può correggere. La
  classificazione **esiste già** nel dominio di Sertor e non viene inventata qui.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In due ambienti che risolvono linee diverse dell'SDK, il server completa la connessione ed
  espone dieci tool: **2 su 2** (oggi: 1 su 2).
- **SC-002**: Un guasto previsto arriva al chiamante con la propria diagnosi in entrambi gli ambienti:
  **2 su 2** (oggi: 1 su 2).
- **SC-003**: Il vincolo di dipendenza ammette entrambe le linee in tutti i punti in cui è dichiarato:
  **2 su 2** (oggi: 0 su 2).
- **SC-004**: Numero di verifiche che esercitano il server attraverso il protocollo: **almeno 1**
  (oggi: 0).
- **SC-005**: Un ospite il cui ambiente ha già risolto la major nuova ottiene i tool aggiornando solo
  Sertor: **verificato su un host usa-e-getta**, non dedotto (oggi: non soddisfatto).
- **SC-006**: Il cancello di pre-merge del progetto — l'intera batteria di test e il lint — resta verde,
  e le verifiche d'installazione reale (attive sui cambi di dipendenza) passano sulla stessa proposta di
  modifica.
- **SC-007**: Un ospite che legge la documentazione utente trova, **senza chiedere**, quali versioni
  sono supportate e cosa fare se è già colpito.

## Assumptions

- **La classificazione dei guasti previsti esiste già** nel dominio di Sertor (una gerarchia di errori
  con undici varietà): FR-004 la riusa, non ne crea una nuova. *Verificato nel codice.*
- **Le due linee espongono la stessa forma d'uso** per ciò che il server usa oggi — istruzioni del
  server, dichiarazione dei tool con descrizione, descrizione ricavata dalla documentazione della
  funzione, avvio sul trasporto standard. *Misurato il 2026-09-13 su entrambe.*
- **La forma dei risultati dei tool che restituiscono un elenco è identica sulle due linee.** *Misurato
  sul protocollo.* Per i tool che restituiscono una struttura singola esiste una differenza di contratto
  **preesistente e identica su entrambe le linee**: è fuori ambito qui e vive come voce propria nel
  backlog (E10-FEAT-076).
- **Il limite alla minor verificata è una scelta di prudenza condizionata**: presuppone che l'uscita di
  una versione successiva produca un avviso e una voce di backlog. Finché quel meccanismo non esiste
  (E10-FEAT-071), il limite è sorvegliato dalla sola memoria umana — ed è dichiarato, non presunto.
- **Il dogfood non è un rilevatore** per questa classe di guasti: il suo ambiente segue l'ultimo commit e
  non ri-risolve mai le dipendenze. La verifica di SC-005 richiede un host usa-e-getta.
- **Fuori ambito, con casa propria**: l'autodiagnosi che verifica l'avvio anziché la registrazione
  (E10-FEAT-072), il contratto dei risultati strutturati (E10-FEAT-076), la sorveglianza dei vincoli di
  dipendenza (E10-FEAT-071), le superfici nuove dell'SDK.
- **Condizione di consegna, non requisito funzionale**: perché questa capacità raggiunga gli ospiti
  serve una **release** — chi è agganciato a una versione pubblicata non può prenderla dal ramo
  principale — e la **risposta alla domanda aperta** che due nodi hanno posto in bacheca.
