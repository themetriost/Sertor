# Feature Specification: Ricerca episodica full-text locale

**Feature Branch**: `033-ricerca-episodica`

**Created**: 2026-06-14

**Status**: Draft

**Input**: User description: "FEAT-002 «Ricerca episodica full-text locale» — rende interrogabile l'archivio dei transcript prodotto da FEAT-001 (già su master). Risponde alle domande di memoria episodica nei casi speciali («ne avevamo già parlato?», «com'è finita quella cosa?») con ricerca full-text LOCALE: il contenuto non lascia la macchina (privacy by design). Granularità di ricerca = turno (con riferimento alla sessione padre). Solo full-text lessicale: niente embedding, niente LLM nel percorso di query."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ritrovare una conversazione passata per parola chiave (Priority: P1)

Durante una sessione di lavoro, l'agente (o l'utente) si chiede se un certo argomento sia già
stato discusso. Pone una query testuale — una parola chiave o una frase — e riceve la lista dei
turni di conversazione passati che contengono quel testo, ciascuno citato con la sessione di
provenienza, il momento in cui è avvenuto e un frammento di contesto che mostra dove il testo
compare. Così la memoria episodica «risponde» invece di restare un archivio inerte.

**Why this priority**: È il cuore della feature e il motivo della sua esistenza: senza la
capacità di trovare per parola chiave un turno passato e vederne il contesto, l'archivio non è
memoria interrogabile. Da sola questa storia è già un MVP utile (rispondere a «ne avevamo già
parlato?»).

**Independent Test**: Si archivia un piccolo insieme di sessioni con contenuto noto, si interroga
con una parola presente in uno dei turni e si verifica che il turno corretto compaia tra i
risultati con la sua citazione (id sessione, timestamp, indice turno) e uno snippet che evidenzia
il match. Testabile interamente in locale senza rete.

**Acceptance Scenarios**:

1. **Given** un archivio con sessioni che contengono un turno con la frase «decidiamo Azure»,
   **When** si interroga con «Azure», **Then** quel turno compare tra i risultati con id sessione,
   timestamp della sessione, ruolo, indice del turno, riferimento al path (se disponibile) e uno
   snippet che mostra il contesto del match.
2. **Given** lo stesso archivio, **When** la query non corrisponde ad alcun testo archiviato,
   **Then** la ricerca restituisce uno stato vuoto esplicito senza errore.
3. **Given** una query qualsiasi, **When** la ricerca viene eseguita, **Then** nessun frammento di
   contenuto lascia la macchina (nessun traffico di rete prodotto dall'operazione).

---

### User Story 2 - Restringere la ricerca a una finestra temporale (Priority: P1)

L'utente ricorda solo vagamente quando una cosa è stata discussa («tre settimane fa») e vuole
restringere i risultati a quel periodo. Fornisce un vincolo temporale (data di inizio, di fine, o
entrambe) insieme alla query, e la ricerca restituisce solo i turni delle sessioni il cui momento
cade nell'intervallo indicato.

**Why this priority**: I casi speciali dell'epica menzionano esplicitamente finestre temporali
(«tre settimane fa», «cosa avevamo deciso su X tre settimane fa»). Il filtro temporale è parte del
valore minimo della memoria episodica, non un extra.

**Independent Test**: Si archiviano sessioni datate in periodi diversi, si interroga con un vincolo
temporale che include solo alcune di esse e si verifica che i risultati fuori finestra non
compaiano e quelli dentro sì.

**Acceptance Scenarios**:

1. **Given** sessioni datate in mesi diversi, **When** si interroga con una finestra
   [inizio, fine] che copre un solo mese, **Then** solo i turni delle sessioni in quel mese
   compaiono.
2. **Given** una query, **When** si fornisce solo una data di inizio, **Then** compaiono i turni
   delle sessioni da quella data in poi; **When** si fornisce solo una data di fine, **Then**
   compaiono i turni fino a quella data inclusa.
3. **Given** una finestra in cui l'inizio è successivo alla fine, **When** si esegue la ricerca,
   **Then** la ricerca rifiuta il vincolo e restituisce un errore esplicito che descrive
   l'intervallo non valido.

---

### User Story 3 - Risultati ordinati e citati in modo utile (Priority: P2)

Chi interroga vuole vedere prima i risultati più pertinenti e non essere sommerso dall'intero
archivio. I risultati sono ordinati per pertinenza lessicale (a parità, il più recente prima),
limitati a un numero massimo ragionevole, e ciascuno è citato in modo da poter risalire alla
conversazione originale. Su richiesta, l'ordinamento può privilegiare la recency.

**Why this priority**: L'ordinamento e il limite rendono i risultati consultabili e affidabili;
senza di essi la US1 funziona ma è meno usabile. La variante recency-first è un comfort
secondario.

**Independent Test**: Si archiviano molti turni corrispondenti, si interroga e si verifica che il
numero di risultati sia limitato al massimo configurato, che l'ordine rifletta la pertinenza con
tie-break sulla recency, e che richiedendo l'ordine recency-first l'ordine cambi di conseguenza.

**Acceptance Scenarios**:

1. **Given** molti turni corrispondenti, **When** si interroga senza opzioni, **Then** i risultati
   sono ordinati per pertinenza lessicale e, a parità di pertinenza, il turno della sessione più
   recente è prima.
2. **Given** lo stesso archivio, **When** si richiede l'ordinamento recency-first, **Then** i
   risultati sono ordinati per momento della sessione decrescente, ignorando le differenze relative
   di pertinenza.
3. **Given** un numero di corrispondenze superiore al massimo configurato, **When** si interroga,
   **Then** vengono restituiti al più il numero massimo di risultati, mai l'intero archivio
   incondizionatamente.

---

### User Story 4 - Robustezza su archivio assente, vuoto o danneggiato (Priority: P2)

La ricerca deve comportarsi bene anche quando l'archivio non è ancora stato creato, è vuoto, o
contiene una voce illeggibile o malformata. In nessuno di questi casi l'operazione deve fallire in
modo bloccante: restituisce uno stato vuoto o salta la voce difettosa con un avviso, continuando a
servire il resto.

**Why this priority**: La feature è invocata da un agente nel mezzo di una sessione; un'eccezione
non gestita interromperebbe il flusso. La degradazione graceful è una proprietà di affidabilità
attesa dal core, non un di più.

**Independent Test**: Si interroga su un archivio inesistente e si verifica uno stato vuoto con
avviso; si introduce una voce malformata e si verifica che venga saltata con un avviso mentre le
voci valide restano ricercabili.

**Acceptance Scenarios**:

1. **Given** nessun archivio (mai creato o cancellato), **When** si interroga, **Then** la ricerca
   restituisce uno stato vuoto esplicito con un avviso, non un errore.
2. **Given** un archivio vuoto, **When** si interroga, **Then** la ricerca restituisce uno stato
   vuoto esplicito senza errore.
3. **Given** un archivio con una voce illeggibile o strutturalmente non valida, **When** si
   interroga, **Then** la ricerca salta quella voce, registra un avviso e continua a cercare nelle
   voci rimanenti senza interrompere l'operazione.

---

### Edge Cases

- **Query vuota o di soli spazi**: la ricerca restituisce uno stato vuoto esplicito senza errore
  (nessun match possibile), non l'intero archivio.
- **Finestra temporale che non include alcuna sessione**: stato vuoto esplicito, non errore.
- **Match all'estremità del testo di un turno** (inizio/fine): lo snippet di contesto resta
  coerente anche quando il match è ai bordi del testo.
- **Sessione priva di path del transcript registrato**: il risultato omette il path ma resta valido
  e citabile (id sessione, timestamp, indice turno).
- **Fallimento nell'emissione dell'evento di osservabilità**: il risultato della ricerca viene
  comunque restituito al chiamante; il guasto di osservabilità è non-fatale.
- **Più turni della stessa sessione corrispondono**: ciascun turno corrispondente è un risultato a
  sé, tutti riferiti alla stessa sessione padre.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il sistema MUST accettare una query testuale e restituire la lista dei turni
  archiviati il cui contenuto contiene una corrispondenza lessicale, ordinati per pertinenza.
- **FR-002**: Per ogni turno corrispondente il sistema MUST riportare almeno: l'identificatore
  della sessione padre, il momento (timestamp) della sessione, il ruolo del turno, l'indice del
  turno all'interno della sessione, il riferimento/path del transcript se disponibile, e uno
  snippet di testo che mostra il contesto della corrispondenza.
- **FR-003**: Il sistema MUST operare interamente sulla macchina locale; non MUST inviare alcun
  frammento del contenuto dei transcript a un servizio esterno o endpoint di rete durante la
  ricerca.
- **FR-004**: Il sistema MUST restituire uno stato vuoto esplicito, senza sollevare errori, quando
  l'archivio è assente o vuoto, e quando nessun turno corrisponde alla query.
- **FR-005**: Il sistema MUST consentire un vincolo opzionale di finestra temporale (inizio, fine,
  o entrambi) che restringe i risultati ai turni delle sessioni il cui momento cade
  nell'intervallo indicato.
- **FR-006**: Quando viene fornita una sola estremità della finestra, il sistema MUST interpretare
  una sola data di inizio come «da quella data in poi» e una sola data di fine come «fino a quella
  data inclusa».
- **FR-007**: Quando l'inizio della finestra temporale è successivo alla fine, il sistema MUST
  rifiutare il vincolo e restituire un errore esplicito che descrive l'intervallo non valido.
- **FR-008**: Il sistema MUST ordinare i risultati per pertinenza lessicale alla query e, a parità
  di pertinenza, MUST far comparire prima i turni delle sessioni più recenti.
- **FR-009**: Il sistema MUST offrire, su richiesta, un ordinamento per recency (momento della
  sessione decrescente) che ignora le differenze relative di pertinenza lessicale.
- **FR-010**: Il sistema MUST limitare il numero di risultati restituiti a un massimo configurabile
  (default: un valore finito e documentato); non MUST restituire l'intero archivio in modo
  incondizionato.
- **FR-011**: Il sistema MUST includere in ogni risultato uno snippet di contesto di lunghezza
  configurabile (default: una finestra finita e documentata) estratto dal testo del turno in
  corrispondenza o intorno alla posizione del match.
- **FR-012**: Il sistema MUST esprimere l'identificatore di sessione, il timestamp della sessione e
  l'indice del turno in un formato leggibile dalla macchina (consumabile programmaticamente).
- **FR-013**: Quando una voce del transcript è illeggibile o strutturalmente non valida, il sistema
  MUST saltarla, registrare un avviso e continuare a cercare nelle voci rimanenti senza interrompere
  l'operazione.
- **FR-014**: Quando l'indice di ricerca è assente (non ancora costruito o cancellato), il sistema
  MUST restituire uno stato vuoto esplicito con un avviso, non un errore.
- **FR-015**: Il corpo della ricerca MUST non contenere alcuna assunzione sull'assistente ospite che
  ha catturato i transcript; MUST operare sull'archivio locale indipendentemente dalla sua
  provenienza (Principio X — host-agnostico).
- **FR-016**: Il sistema MUST essere utilizzabile da almeno due ambienti ospite diversi senza
  modifiche al corpo della feature.
- **FR-017**: Al completamento di una ricerca il sistema MUST emettere un evento strutturato che
  registra la query in forma sicura (in chiaro solo se non sensibile, altrimenti redatta o sotto
  forma di hash, coerentemente con la strategia di redazione di FEAT-001), i filtri temporali
  applicati, il numero di risultati restituiti e la latenza dell'operazione.
- **FR-018**: Quando l'emissione dell'evento di osservabilità fallisce, il sistema MUST restituire
  comunque il risultato della ricerca al chiamante; il guasto di osservabilità MUST essere
  non-fatale.
- **FR-019**: Il sistema MUST riflettere lo stato corrente dell'archivio prodotto da FEAT-001; non
  MUST introdurre stato persistente lato scrittura oltre a quanto necessario per indicizzare
  l'archivio ai fini della ricerca.
- **FR-020**: Quando una nuova sessione viene aggiunta all'archivio (FEAT-001), i suoi turni MUST
  essere ricercabili prima della successiva invocazione di ricerca (l'indice non diverge
  dall'archivio).
- **FR-021**: Il sistema MUST indicizzare e restituire i risultati alla granularità del **turno**,
  mantenendo per ciascun turno il riferimento alla **sessione** padre; la granularità MUST restare un
  parametro del comportamento, non un valore cablato.

### Key Entities *(include if feature involves data)*

- **Sessione archiviata**: una conversazione passata con l'agente, prodotta e persistita da
  FEAT-001. Attributi rilevanti per questa feature: identificatore di sessione, momento/timestamp,
  riferimento/path del transcript (facoltativo), provenienza/host (opaco a questa feature). È
  l'unità di **archiviazione**.
- **Turno**: una singola battuta all'interno di una sessione (ruolo, indice ordinale nella
  sessione, momento, contenuto testuale già scrubbed). È l'unità di **ricerca e di restituzione**:
  ogni turno punta alla sessione padre.
- **Query di ricerca**: l'input dell'utente/agente — testo da cercare più vincoli opzionali
  (finestra temporale, modalità di ordinamento, limite di risultati, lunghezza dello snippet).
- **Risultato di ricerca**: un turno corrispondente arricchito di citazione — id sessione,
  timestamp sessione, ruolo, indice turno, riferimento/path (se disponibile), snippet di contesto e
  un segnale di pertinenza usato per l'ordinamento.
- **Indice di ricerca**: la rappresentazione interrogabile dell'archivio a grana di turno; deriva
  dall'archivio di FEAT-001 e si mantiene allineato a esso. La sua forma concreta è materia di
  design.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Data una parola chiave o frase presente nel testo di un turno archiviato, la ricerca
  restituisce quel turno tra i risultati nel 100% dei casi (completezza dei match esatti).
- **SC-002**: Ogni risultato restituito riporta tutti i campi di citazione attesi (id sessione,
  timestamp, ruolo, indice turno, snippet; più il path quando registrato) nel 100% dei risultati.
- **SC-003**: Una query con vincolo temporale non restituisce alcun turno la cui sessione cade fuori
  dall'intervallo (zero falsi positivi temporali) e include tutti i turni delle sessioni dentro
  l'intervallo che corrispondono lessicalmente.
- **SC-004**: Durante una ricerca completa l'operazione non produce alcun traffico di rete
  (verificabile con un monitor di rete in ambiente di test): zero pacchetti in uscita attribuibili
  alla ricerca.
- **SC-005**: La ricerca su un archivio assente, vuoto o senza match restituisce uno stato vuoto
  esplicito senza eccezioni nel 100% dei casi; una voce malformata non impedisce di restituire i
  risultati delle voci valide.
- **SC-006**: La ricerca su un archivio di dimensione tipica restituisce risultati entro un tempo
  percettivamente immediato in un contesto interattivo (indicativamente sotto i 2 secondi su
  hardware consumer standard); la soglia quantitativa esatta è fissata in fase di design una volta
  nota la dimensione attesa dell'archivio.
- **SC-007**: La stessa ricerca, eseguita senza modifiche al suo corpo, produce risultati
  equivalenti su almeno due archivi di provenienza/host diversi (host-agnostico verificato).
- **SC-008**: Una nuova sessione archiviata è ricercabile (i suoi turni compaiono nei risultati
  pertinenti) alla prima ricerca successiva nel 100% dei casi.

## Assumptions

- **A-001 — Archivio fornito da FEAT-001 (su master)**: si assume FEAT-001 operativa, che produce un
  archivio locale di sessioni con almeno id sessione, timestamp, turni (ruolo, indice, momento,
  contenuto testuale già scrubbed) e path del transcript facoltativo. Se FEAT-001 non è operativa,
  la ricerca restituisce stato vuoto (FR-004/FR-014).
- **A-002 — Granularità ibrida risolta (decisione utente 2026-06-14, DA-M-b)**: l'unità archiviata è
  la sessione; l'unità indicizzata e restituita è il turno, con riferimento alla sessione padre. La
  granularità resta un parametro di design (FR-021), non un hardcode.
- **A-003 — Contenuto già scrubbed**: il testo che la ricerca riceve è già stato ripulito dai segreti
  da FEAT-001; questa feature non applica scrub aggiuntivo. Conseguenza nota: termini eventualmente
  redatti da FEAT-001 non saranno trovabili (comportamento atteso, non un difetto di questa feature).
- **A-004 — Solo full-text lessicale, nessun cloud nel percorso di query**: nessun embedding, nessun
  vector store, nessun modello di linguaggio nel percorso di una query. La ricerca semantica è
  FEAT-004 (Should, opt-in separato) ed è fuori ambito. Nessuna credenziale o connettività cloud è
  richiesta per funzionare.
- **A-005 — Motore full-text deciso in design**: la scelta concreta del motore di indicizzazione
  full-text (full-text nativo dell'archivio SQLite, riuso dell'indice lessicale BM25 già presente
  nel core, oppure un indice dedicato dietro una porta) è materia del plan, non della spec. Vincolo
  di indirizzo (non hard): preferire funzionalità della stdlib o dipendenze già presenti nel core
  rispetto a nuove dipendenze di terze parti (local-first).
- **A-006 — Seam come porta Protocol (probabile, da confermare in design)**: coerentemente con lo
  stile delle porte Protocol del core, è plausibile che la ricerca episodica sia esposta dietro un
  contratto astratto; nome e metodi esatti, e se serva una porta dedicata o basti un componente
  concreto, sono materia di design.
- **A-007 — Aggiornamento dell'indice rispetto all'archiviazione**: si assume che la composizione tra
  FEAT-001 e questa feature garantisca che i turni di una nuova sessione siano ricercabili prima
  della ricerca successiva (FR-020). Se l'aggiornamento sia sincrono all'archiviazione o lazy
  alla prima ricerca è decisione di design.
- **A-008 — Testabilità senza terminale né corpus reale**: la logica di ricerca è pensata per essere
  testabile come funzione/componente isolato, senza terminale, assistente attivo o corpus reale,
  coerentemente con i pattern già stabiliti nel core.
- **A-009 — Soglia quantitativa di latenza rinviata al design**: la soglia numerica esatta (SC-006,
  NFR di scalabilità) è fissata in design una volta nota la cardinalità dell'indice (a grana di
  turno) e la dimensione tipica attesa dell'archivio.

### Dependencies

- **FEAT-001 (Must, a monte, già su master)**: cattura e archiviazione locale dei transcript — è la
  sorgente di dati. Senza FEAT-001 la ricerca non ha nulla da interrogare.
- **Pattern di osservabilità del core**: gli eventi di ricerca (FR-017/FR-018) seguono il pattern di
  logging strutturato già in uso nel core; l'osservabilità è non-fatale, quindi non è una dipendenza
  hard.

### Out of Scope

- Cattura e persistenza dei transcript (FEAT-001, dipendenza a monte già fornita).
- Ricerca semantica/embedding (FEAT-004, Should, opt-in separato).
- Aggancio diretto alla distillazione del wiki, `distill`/`record` (FEAT-003, Should).
- Cancellazione, governance e retention dell'archivio (FEAT-006).
- Roll-up cross-progetto (FEAT-007).
- Cattura multi-assistente (FEAT-008).
- Interfaccia grafica o TUI dedicata (epica `sertor-cli`).
