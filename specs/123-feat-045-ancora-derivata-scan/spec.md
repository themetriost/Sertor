# Feature Specification: Ancora derivata per la rilevazione del lavoro non registrato

**Feature Branch**: `123-feat-045-ancora-derivata-scan`

**Created**: 2026-07-27

**Status**: Draft

**Input**: E10-FEAT-045 (Must/P0, `requirements/debito-tecnico/epic.md`) — riqualificata dal nodo *Acta* il 2026-07-26 da «incoerenza fra strumenti» a **deadlock**. Assorbe E10-FEAT-048 sugli host git. Scope deciso dall'utente il 2026-07-27 (il «giudizio registrato» è **fuori scope**, promosso a E10-FEAT-051).

## Il problema, in una frase

La domanda «c'è lavoro non registrato nel wiki?» oggi non viene **derivata** da un fatto: viene **stimata** confrontando orologi di file. Dopo un merge quegli orologi vengono tutti riscritti insieme, l'ordine diventa arbitrario, e la risposta smette di significare qualcosa — pur continuando ad avere l'aria di funzionare.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Chiudere la sessione dopo aver consegnato un merge (Priority: P1)

Un agente lavora, registra il lavoro nel wiki, consegna il tutto con un merge sulla mainline e allinea il repo locale. A quel punto chiede di chiudere la sessione. Poiché ha registrato ciò che ha fatto, la sessione **deve poter chiudere**.

Oggi non può, e non per un difetto di disciplina: il merge riscrive sul disco sia i file del lavoro sia il file di giornale, tutti con lo stesso istante. Il confronto fra orologi diventa una lotteria. Quando la perde, il gate blocca; per soddisfarlo bisogna scrivere ancora nel giornale, il che produce **nuovo** lavoro da consegnare, che al merge successivo ricrea la stessa condizione. **Non esiste un ordine di operazioni che chiuda.** L'unica uscita è lasciare il lavoro non consegnato — cioè violare la disciplina che il gate esiste per proteggere.

**Why this priority**: è il difetto per cui la feature esiste, ed è **Must/P0** perché un gate bloccante insoddisfacibile non è una rete di sicurezza — è un ostacolo, e la via d'uscita che insegna (albero sporco, oppure toccare il giornale solo per far avanzare la stima) è la nostra stessa classe di guasto. Sul nodo *Acta* si è manifestato **sette volte in una giornata**. Da noi «funziona», ma è una corsa vinta: non deterministico, quindi **peggio di sempre-rotto**, perché nessuno lo indaga.

**Independent Test**: su un repo di prova, eseguire la sequenza reale — lavoro + voce di giornale nello stesso commit → merge sulla mainline → allineamento del repo locale → interrogare la rilevazione. Deve rispondere «niente in sospeso» **in modo ripetibile**, indipendentemente da quale file il sistema operativo abbia scritto per ultimo. Vale da solo: consegna la fine del deadlock anche senza le altre storie.

**Acceptance Scenarios**:

1. **Given** un repo dove l'ultima consegna conteneva sia il lavoro sia la sua voce di giornale, **When** la consegna viene mergiata e il repo locale allineato, **Then** la rilevazione riporta zero elementi in sospeso.
2. **Given** la stessa situazione, **When** la rilevazione viene ripetuta più volte e dopo aver forzato gli orologi dei file a valori arbitrari, **Then** la risposta è **sempre la stessa** (la risposta non dipende dagli orologi).
3. **Given** un repo con lavoro consegnato **senza** voce di giornale, **When** si interroga la rilevazione, **Then** riporta quel lavoro come in sospeso (il gate continua a mordere quando deve).
4. **Given** un albero di lavoro con modifiche **non ancora consegnate** e nessuna voce di giornale nuova, **When** si interroga la rilevazione, **Then** quelle modifiche risultano in sospeso — è il caso normale a fine turno, quando il lavoro della sessione non è ancora stato committato.
5. **Given** lo stesso albero, **When** l'agente scrive la voce di giornale di oggi (ancora non committata), **Then** la rilevazione riporta zero in sospeso — **il gate si soddisfa in un turno, senza dover committare**.

---

### User Story 2 — Sapere QUALI file sono in sospeso, e non essere bloccati da uno scarto (Priority: P2)

Quando la rilevazione dice «c'è lavoro non registrato», chi la riceve deve poter capire **di cosa si tratta** senza indagini. E un file che il controllo di versione **ignora** — una bozza, uno scratch, un artefatto rigenerabile — non deve contare come lavoro da registrare: nessuno lo consegnerà mai a nessuno.

**Why this priority**: è E10-FEAT-048, misurata dal nodo *Acta*: una bozza appoggiata in una cartella ignorata produceva «1 in sospeso»; rimossa, zero, nessun'altra variabile. Poiché la rilevazione alimenta un gate **bloccante**, qualunque scarto appoggiato nella cartella di lavoro impedisce la chiusura della sessione — e la diagnosi non è ovvia, perché il messaggio dice **quanti** file, non **quali** (*Acta* ha dovuto ricostruirli a mano). Entra qui, e non resta una feature separata, perché **cade fuori gratis** dalla derivazione: chi deriva dal controllo di versione ottiene l'esclusione degli ignorati per costruzione e i nomi dei file senza lavoro aggiuntivo.

**Independent Test**: appoggiare un file in una cartella ignorata dal controllo di versione e interrogare la rilevazione: deve riportare zero. Poi modificare un file reale e verificare che il suo **percorso** compaia nell'output.

**Acceptance Scenarios**:

1. **Given** un file presente nell'albero di lavoro ma **ignorato** dal controllo di versione, **When** si interroga la rilevazione, **Then** quel file **non** viene contato fra gli elementi in sospeso.
2. **Given** uno o più file realmente in sospeso, **When** si interroga la rilevazione, **Then** l'output **nomina i percorsi** dei file, sia nel messaggio leggibile sia nel dato strutturato.
3. **Given** un numero elevato di file in sospeso, **When** si interroga la rilevazione, **Then** l'elenco è **limitato** e dichiara quanti altri ne restano, invece di produrre un muro di testo.
4. **Given** un ospite la cui configurazione personalizza il messaggio, **When** si interroga la rilevazione, **Then** il messaggio personalizzato continua a funzionare e i nomi dei file compaiono comunque.

---

### User Story 3 — Un ospite senza controllo di versione riceve comunque il gate, e sa che è una stima (Priority: P3)

La capacità è installabile su qualunque progetto, anche su uno che non usa un controllo di versione. Lì la derivazione è impossibile. L'ospite deve continuare a ricevere la rilevazione — **e deve sapere che quella risposta è una stima, non un fatto**.

**Why this priority**: è il vincolo del Principio X, ed è scritto nella decisione originale del meccanismo, non è un'inferenza. Passare al solo controllo di versione romperebbe gli ospiti non-repo. Ma tenere la stima **senza dichiararla** ripeterebbe, dentro il fix, esattamente il difetto che il fix chiude: un artefatto che presenta come fatto un valore che è una copia o un'approssimazione (Principio XIV). È P3 perché non sblocca nessuno — è **onestà del contratto**, ed è ciò che permetterà a un ospite di capire perché lì il gate si comporta diversamente.

**Independent Test**: eseguire la rilevazione in un progetto **non** sotto controllo di versione: deve produrre un risultato utilizzabile e **dichiarare** che l'ancora usata è un'approssimazione.

**Acceptance Scenarios**:

1. **Given** un progetto non sotto controllo di versione, **When** si interroga la rilevazione, **Then** funziona come prima e l'output **dichiara** che l'ancora è un'approssimazione temporale.
2. **Given** un progetto sotto controllo di versione, **When** si interroga la rilevazione, **Then** l'output **dichiara** che l'ancora è derivata dalla storia, e **identifica** la consegna da cui è derivata.
3. **Given** un progetto sotto controllo di versione in cui l'interrogazione della storia **non è possibile** (storia troncata, comando non disponibile, cartella di giornale mai consegnata), **When** si interroga la rilevazione, **Then** ricade sull'approssimazione temporale, **la dichiara**, e **dichiara anche il motivo** della ricaduta — non tace.

---

### Edge Cases

- **La cartella di giornale non è mai stata consegnata** (ospite nuovo, wiki appena creato): non esiste una consegna da cui derivare → nessuna ancora → *tutto* è in sospeso, che è il comportamento odierno a giornale assente. Nessuna regressione.
- **Storia troncata** (clone superficiale): la consegna cercata può essere fuori dalla storia disponibile → ricaduta dichiarata sull'approssimazione, con motivo.
- **La voce di giornale è stata scritta ma è di un giorno passato** e non consegnata: non conta come registrazione della sessione corrente — altrimenti un file dimenticato nell'albero di lavoro spegnerebbe il gate a tempo indeterminato, che è precisamente la via d'uscita che stiamo togliendo. **Il blocco però la nomina** (FR-004a): senza, il giornale sembrerebbe «già aggiornato» a fronte di un gate che blocca lo stesso, e la diagnosi tornerebbe a essere un'indagine.
- **Lavoro consegnato dopo la voce di giornale, nella stessa sessione**: risulta in sospeso. Corretto: la registrazione non descrive quel lavoro.
- **Ramo di lavoro non ancora consegnato**: l'ultima registrazione può trovarsi sulla mainline; tutto il lavoro del ramo successivo a essa risulta in sospeso finché non viene registrato. Corretto.
- **Nessun cambiamento di alcun tipo** (sessione di sola lettura o di sole domande): zero in sospeso, il gate non si attiva. Invariante da non rompere.
- **Le esclusioni configurate dall'ospite** continuano ad applicarsi in entrambe le modalità: la derivazione non le scavalca.

## Clarifications

### Sessione 2026-07-27

- **Q — Una voce di giornale scritta ma non ancora consegnata vale come registrazione, e con quale scadenza?**
  **A — Vale solo se è la voce del giorno corrente.** *(→ FR-004, FR-004a, A-2)*

  La prima metà non era in discussione ed è un vincolo, non una scelta: il gate interviene **a fine
  turno**, quando tipicamente **nulla è ancora consegnato** — il lavoro è scritto, la voce è scritta, e
  la consegna è delegata e parte dopo. Se contasse solo una registrazione consegnata, il gate
  pretenderebbe una consegna per potersi soddisfare: una richiesta che non gli compete e che
  ricreerebbe un deadlock di forma diversa.

  La scadenza, invece, era la scelta vera. **Senza scadenza, una voce dimenticata nell'albero di lavoro
  diventa un interruttore permanente**: è la stessa via d'uscita in cui il nodo *Acta* è stata
  costretta (chiudere lasciando il lavoro non consegnato), qui però **resa legittima** invece che
  tolta — e senza che nulla lo segnali. Alternativa considerata e scartata: nessuna scadenza ma
  dichiarazione dello stato nell'output; scartata perché quando il gate **non** blocca non stampa
  nulla, quindi quella dichiarazione non la leggerebbe nessuno.

  **Attrito accettato consapevolmente:** se un giorno non si consegna nulla e il giorno dopo non si
  lavora, il gate chiede comunque una voce nuova per lavoro già descritto nella voce del giorno prima.
  Costo giudicato inferiore a quello di una scappatoia permanente. **Contromisura:** FR-004a — il
  blocco **nomina** la voce non consegnata e la sua data, invece di lasciare che il giornale sembri
  «già aggiornato» mentre il gate blocca lo stesso.

## Requirements *(mandatory)*

### Functional Requirements

**Derivazione dell'ancora**

- **FR-001**: La rilevazione MUST determinare l'ancora del lavoro registrato da un **fatto derivato dalla storia** del progetto — l'ultima consegna che ha toccato la cartella di giornale del wiki — ogni volta che il progetto è sotto controllo di versione e la storia è interrogabile.
- **FR-002**: La risposta MUST essere **deterministica**: interrogazioni ripetute sullo stesso stato del progetto devono produrre lo stesso risultato, **indipendentemente dagli orari di modifica dei file**.
- **FR-003**: L'insieme in sospeso MUST comprendere sia il lavoro **consegnato dopo** l'ultima registrazione, sia le modifiche **presenti nell'albero di lavoro e non ancora consegnate** (sia a file già noti al controllo di versione sia a file nuovi). *Senza la seconda metà il gate non vedrebbe mai il lavoro di una sessione in corso, che è il caso normale al momento in cui interviene.*
- **FR-004**: Una registrazione **presente nell'albero di lavoro e non ancora consegnata** MUST valere come registrazione — il gate deve potersi soddisfare **senza obbligare a una consegna** — **a condizione che sia una registrazione del giorno corrente** (deciso in `clarify`, vedi Clarifications e A-2).
- **FR-004a**: Quando esiste una registrazione non consegnata che **non** è del giorno corrente, l'output MUST **nominarla** (con la sua data) e dichiarare che **non vale** per il giorno corrente. *Senza questo, chi riceve il blocco vede un giornale «già modificato» e un gate che blocca lo stesso, senza modo di capire perché.*

**Nominare e ignorare (assorbe E10-FEAT-048)**

- **FR-005**: Gli elementi che il controllo di versione **ignora** MUST NOT essere contati come lavoro in sospeso, ovunque la derivazione sia attiva.
- **FR-006**: L'output MUST **nominare i percorsi** dei file in sospeso, sia nel messaggio leggibile sia nel dato strutturato.
- **FR-007**: L'elenco nominato MUST essere **limitato** e, quando tronca, MUST dichiarare quanti elementi restano.
- **FR-008**: I messaggi personalizzati dall'ospite MUST continuare a funzionare: l'aggiunta dei nomi non deve richiedere che l'ospite aggiorni la propria configurazione.

**Onestà del contratto (Principio XIV)**

- **FR-009**: L'output MUST **dichiarare la natura dell'ancora** usata — derivata dalla storia oppure approssimazione temporale — come informazione esplicita, mai desumibile per convenzione.
- **FR-010**: Quando l'ancora è derivata, l'output MUST **identificare la consegna** da cui è derivata, così che l'ospite possa verificarla.
- **FR-011**: Quando la derivazione era attesa ma non è stata possibile, l'output MUST dichiarare **il motivo** della ricaduta sull'approssimazione. *Una ricaduta silenziosa sarebbe la stessa classe di difetto che questa feature chiude.*

**Compatibilità (vincolo critico)**

- **FR-012**: L'identificativo di schema del dato strutturato MUST restare **invariato**, e i campi nuovi MUST essere **additivi**. *I due consumatori installati verificano l'identificativo per uguaglianza e, se non corrisponde, si disattivano lasciando passare tutto: cambiarlo **spegnerebbe in silenzio** il gate su ogni ospite che non ha ancora aggiornato gli asset. Va coperto da una verifica anti-regressione, non affidato all'attenzione.*
- **FR-013**: Il significato e il tipo dei campi **già esistenti** MUST essere preservati: un consumatore che oggi legge il campo dell'ancora come istante temporale deve continuare a poterlo fare.
- **FR-014**: Il comportamento su progetti **non** sotto controllo di versione MUST restare quello odierno, salvo la dichiarazione di FR-009.
- **FR-015**: I due consumatori installati — il gate bloccante di fine turno e l'avviso non bloccante — MUST continuare a funzionare senza modifiche, e MUST essere aggiornati per **mostrare i nomi dei file** quando disponibili.

**Consegna (Definition of Done host-facing)**

- **FR-016**: Il cambiamento MUST raggiungere gli ospiti attraverso il percorso di installazione, non restare vivo solo sul progetto di riferimento.
- **FR-017**: La documentazione **utente** MUST riflettere il nuovo comportamento — in particolare la differenza fra ospiti sotto controllo di versione e non — **nello stesso step**.

### Key Entities

- **Ancora della registrazione** — il punto oltre il quale il lavoro conta come «non registrato». Ha due forme: **derivata** (una consegna identificabile nella storia) e **approssimata** (un istante temporale). Porta con sé **la propria natura** e, quando approssimata per ricaduta, **il motivo**.
- **Insieme in sospeso** — i file di lavoro non coperti dalla registrazione più recente. Non è più solo un **numero**: è un **elenco di percorsi**, di cui il numero è una proprietà derivata.
- **Registrazione** — l'atto che sposta l'ancora. Esiste in due medium: **consegnata** (nella storia) e **presente nell'albero di lavoro**.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: La sequenza «registro → consegno → allineo → chiudo» si completa **senza blocchi**, e si completa **10 volte su 10** — oggi l'esito dipende dall'ordine di scrittura del sistema operativo.
- **SC-002**: A parità di stato del progetto, la rilevazione produce **lo stesso risultato** anche dopo aver alterato arbitrariamente gli orari di modifica di tutti i file coinvolti.
- **SC-003**: Un file ignorato dal controllo di versione, appoggiato nella cartella di lavoro, **non impedisce** la chiusura della sessione.
- **SC-004**: Chi riceve un blocco può dire **quali** file lo hanno causato **senza eseguire altri comandi** — oggi occorre ricostruirli a mano.
- **SC-005**: La capacità continua a funzionare su un progetto **non** sotto controllo di versione, e in quel caso l'output **dichiara** di star stimando.
- **SC-006**: Un ospite che aggiorna **solo** la libreria e non gli asset installati **non perde il gate** (nessuna disattivazione silenziosa dei consumatori).
- **SC-007**: Il gate continua a mordere quando deve: lavoro reale non registrato produce un blocco in **tutti** gli scenari in cui lo produce oggi.
- **SC-008**: Una registrazione non consegnata **di un giorno passato** non impedisce al gate di bloccare, e chi riceve il blocco **legge la sua data** senza eseguire altri comandi.

## Assumptions

- **A-1 — L'ancora è la cartella di giornale, non l'intero wiki.** La registrazione si misura sul giornale, come oggi: aggiornare una pagina senza scrivere la voce di giornale non conta come registrazione. Preserva la semantica corrente e la disciplina del rituale («un passo non è chiuso finché commit e voce di log non sono entrambi fatti»).
- **A-2 — Una registrazione non consegnata vale solo se è del giorno corrente.** ✅ **Confermata in `clarify` (2026-07-27)** — vedi Clarifications. Senza questo vincolo, una voce dimenticata nell'albero di lavoro spegnerebbe il gate a tempo indeterminato, reintroducendo per un'altra via la scappatoia che stiamo togliendo. Il giornale è già partizionato per giorno e il gate gemello del merge usa già «la partizione di oggi»: la scelta è coerente con un meccanismo esistente, non nuova.
- **A-3 — Ricaduta dichiarata, non fallimento.** Se la derivazione è impossibile su un progetto che pure è sotto controllo di versione (storia troncata, comando assente, giornale mai consegnato), si ricade sull'approssimazione **dichiarandolo**, invece di interrompere. Il consumatore principale è un gate che per progetto non deve mai intrappolare un turno; interrompere qui trasformerebbe un caso limite in un blocco. La dichiarazione soddisfa comunque «non degradare in silenzio».
- **A-4 — Le esclusioni configurate restano.** La derivazione non scavalca le esclusioni dichiarate dall'ospite: si applicano a entrambe le modalità.
- **A-5 — Il limite all'elenco dei nomi è una scelta di leggibilità**, non un vincolo tecnico; il numero totale resta sempre esatto.
- **A-6 — L'esclusione degli elementi ignorati vale dove c'è il controllo di versione.** Su un ospite senza, l'informazione non esiste e il comportamento resta quello odierno: è un limite da dichiarare nella documentazione, non da simulare.
- **A-7 — Il riuso è possibile.** La macchina per interrogare la storia esiste già nello stesso componente (usata dallo strumento gemello che scopre i candidati del rituale) e include già il rilevamento del ramo principale a runtime: la feature la estrae e la condivide, non la reinventa.

## Out of Scope

> **Nota di processo:** ogni voce qui sotto ha già una **casa durevole**. Nessun rinvio vive solo dentro questa cartella.

- **Chiudere il gate con un «giudizio registrato»** («ho guardato questi file, non vanno registrati») — la terza forma di chiusura, non-binaria. **Rinviata per decisione utente (2026-07-27)** e promossa a **E10-FEAT-051**, con il motivo scritto: con l'ancora corretta i due sintomi peggiori spariscono da soli, quindi il residuo legittimo va misurato **in esercizio** prima di tararci sopra una via d'uscita. Tararla ora significherebbe tararla sul comportamento rotto.
- **Nominare i file su ospiti senza controllo di versione** — lì l'informazione «ignorato» non esiste. Resta il comportamento odierno; il limite si **dichiara** nella documentazione utente (FR-017).
- **Il lint sui riferimenti entranti** (E10-FEAT-049) e le altre voci del triage *Acta*: capacità distinte, già a backlog.
