# Feature Specification: Superficie CLI memoria + cattura automatica a fine sessione

**Feature Branch**: `035-memoria-cli-hook`

**Created**: 2026-06-14

**Status**: Draft

**Input**: User description: "Superficie CLI memoria + cattura automatica a fine sessione — l'MVP memoria (cattura/archivio + ricerca episodica) vive solo come libreria. Manca la superficie per usarlo e un momento in cui la cattura scatti da sola. Tre capacità sottili (thin consumer): comando `memory archive` (archivia le sessioni del progetto), comando `memory search` (ricerca episodica), hook `SessionEnd` che richiama l'archiviazione automaticamente a fine sessione. Privacy gated su SERTOR_MEMORY (default off). Comandi host-agnostici; hook host-specifico (Claude Code per primo). Hook non-bloccante e non-fatale."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Archiviare le conversazioni del progetto con un comando (Priority: P1)

L'utente (o un agente) vuole portare le conversazioni recenti del progetto corrente nell'archivio
di memoria, senza dover scrivere codice né conoscere i dettagli interni dell'archiviazione. Lancia
un comando dedicato e ottiene un report leggibile di ciò che è stato archiviato e di ciò che è stato
saltato perché già presente. Rilanciare il comando è sicuro: non duplica nulla e non altera ciò che
è già stato archiviato.

**Why this priority**: È la prima superficie che rende *usabile* l'archivio: senza un modo per
avviare l'archiviazione dall'esterno, il tier grezzo resta una libreria inerte. Da sola questa
storia è già un MVP utile (popolare la memoria su comando).

**Independent Test**: Con la memoria abilitata, si esegue il comando su un progetto che ha sessioni
non ancora archiviate, si verifica che il report elenchi quante sessioni sono state archiviate e
quante saltate, e che un secondo lancio immediato riporti zero nuove archiviazioni (tutte saltate).

**Acceptance Scenarios**:

1. **Given** la memoria abilitata e sessioni del progetto non ancora archiviate, **When** si esegue
   il comando di archiviazione, **Then** le sessioni vengono archiviate e il comando stampa un report
   leggibile con il numero di sessioni archiviate e saltate.
2. **Given** lo stesso stato, **When** si esegue il comando una seconda volta senza nuove sessioni,
   **Then** il report riporta zero nuove archiviazioni e tutte le sessioni risultano saltate
   (idempotenza: nessun duplicato, nessuna alterazione).
3. **Given** la memoria abilitata, **When** si esegue il comando richiedendo l'output in formato
   leggibile dalla macchina, **Then** il report è restituito in una forma strutturata e consumabile
   programmaticamente, con gli stessi conteggi della versione umana.

---

### User Story 2 - Ritrovare una conversazione passata da riga di comando (Priority: P1)

L'utente si chiede se un certo argomento sia già stato discusso e vuole interrogare l'archivio
direttamente da riga di comando. Fornisce una query testuale e, opzionalmente, una finestra temporale
e un limite di risultati; riceve la lista dei turni corrispondenti citati in modo coerente con la
ricerca di codice/documenti già offerta dallo strumento (sessione, ruolo, indice del turno, frammento
di contesto, segnale di pertinenza). L'operazione è di sola lettura e non modifica l'archivio.

**Why this priority**: Rende interrogabile dall'esterno la memoria episodica che già esiste come
libreria. Insieme alla US1 forma il giro minimo «archivia → ritrova» dalla riga di comando, il valore
centrale della feature.

**Independent Test**: Con un archivio popolato con contenuto noto, si interroga con una parola
presente in un turno e si verifica che il turno corretto compaia nei risultati con la sua citazione;
si aggiunge un filtro temporale e si verifica che i risultati fuori finestra spariscano; si impone un
limite e si verifica che il numero di risultati non lo superi.

**Acceptance Scenarios**:

1. **Given** un archivio con un turno che contiene una certa frase, **When** si interroga con una
   parola di quella frase, **Then** il comando stampa quel turno tra i risultati con sessione, ruolo,
   indice del turno, frammento di contesto e segnale di pertinenza, in un formato coerente con la
   ricerca di codice/documenti già offerta dallo strumento.
2. **Given** lo stesso archivio, **When** si fornisce una finestra temporale (inizio, fine o
   entrambe), **Then** compaiono solo i turni delle sessioni il cui momento cade nell'intervallo.
3. **Given** molti turni corrispondenti, **When** si impone un limite di risultati, **Then** il
   comando restituisce al più quel numero di risultati.
4. **Given** una qualsiasi interrogazione, **When** viene eseguita, **Then** l'archivio non viene
   modificato (operazione di sola lettura) e, su richiesta, i risultati sono restituiti anche in una
   forma strutturata consumabile programmaticamente.

---

### User Story 3 - La cattura scatta da sola a fine sessione (Priority: P1)

L'utente non vuole ricordarsi di archiviare manualmente: vuole che, a ogni fine sessione di lavoro
con l'assistente, le conversazioni vengano archiviate automaticamente, senza intervento e senza
rallentare o interrompere la chiusura della sessione. Se l'archiviazione automatica per qualsiasi
ragione non va a buon fine, la sessione si chiude comunque normalmente: l'automatismo non deve mai
degradare l'esperienza.

**Why this priority**: È il *grilletto* che trasforma la memoria da capacità esercitabile a manina in
una memoria che si popola da sola, in continuità. Senza di esso l'archivio resta vuoto a meno di un
gesto manuale costante. È l'anello che rende «continua» la cattura.

**Independent Test**: Con la memoria abilitata, si simula la fine di una sessione e si verifica che
l'archiviazione venga avviata automaticamente e che le sessioni risultino poi archiviate; si simula
un fallimento dell'archiviazione e si verifica che la chiusura della sessione avvenga comunque, senza
errore propagato all'esperienza dell'utente.

**Acceptance Scenarios**:

1. **Given** la memoria abilitata, **When** una sessione di lavoro termina, **Then** l'archiviazione
   delle sessioni del progetto viene avviata automaticamente senza alcun intervento dell'utente.
2. **Given** la memoria abilitata, **When** l'archiviazione automatica fallisce o richiede tempo,
   **Then** la chiusura della sessione non viene né interrotta né rallentata in modo percepibile
   (l'automatismo è non-bloccante e non-fatale).
3. **Given** la memoria disabilitata (impostazione predefinita), **When** una sessione termina,
   **Then** l'automatismo non fa nulla e non produce alcun messaggio (no-op silenzioso).

---

### Edge Cases

- **Memoria disattivata (default) e comando invocato esplicitamente**: il comando non archivia/cerca
  nulla e risponde con un messaggio d'errore azionabile che spiega come abilitare la memoria; non
  fallisce in modo oscuro né archivia silenziosamente.
- **Nessuna sessione da archiviare**: il comando di archiviazione riporta zero archiviazioni in modo
  esplicito, non un errore.
- **Archivio assente o vuoto in ricerca**: la ricerca restituisce uno stato vuoto esplicito senza
  errore (comportamento ereditato dal core di ricerca episodica).
- **Finestra temporale con inizio successivo alla fine**: la ricerca rifiuta il vincolo con un errore
  esplicito che descrive l'intervallo non valido.
- **Hook invocato su un host diverso da quello previsto / fuori da una sessione**: l'hook non rompe
  nulla; nel peggiore dei casi non fa nulla.
- **Hook con memoria abilitata ma archiviazione che solleva un guasto**: il guasto è assorbito,
  registrato in modo non-fatale, e la sessione si chiude normalmente.
- **Output in formato strutturato richiesto in caso di errore (memoria off)**: l'errore azionabile è
  comunicato in modo coerente anche quando si è richiesto l'output strutturato.

## Requirements *(mandatory)*

### Functional Requirements

#### Comando di archiviazione

- **FR-001**: Il sistema MUST offrire un comando da riga di comando che avvia l'archiviazione delle
  sessioni del progetto corrente delegando interamente la logica al servizio di archiviazione già
  esistente nel core, senza reimplementare alcuna logica di cattura o persistenza.
- **FR-002**: Il comando di archiviazione MUST stampare un report leggibile che indichi almeno quante
  sessioni sono state archiviate e quante saltate (perché già presenti).
- **FR-003**: Il comando di archiviazione MUST offrire, su richiesta, lo stesso report in una forma
  strutturata e consumabile programmaticamente, coerente nei conteggi con la versione leggibile.
- **FR-004**: Il comando di archiviazione MUST essere idempotente: rilanciarlo non duplica le sessioni
  già archiviate e non altera quanto già presente.

#### Comando di ricerca

- **FR-005**: Il sistema MUST offrire un comando da riga di comando che esegue una ricerca episodica
  sull'archivio delegando interamente la logica al servizio di ricerca episodica già esistente nel
  core, senza reimplementare alcuna logica di ricerca.
- **FR-006**: Il comando di ricerca MUST accettare una query testuale e stampare i turni corrispondenti
  citati con almeno: sessione di provenienza, ruolo del turno, indice del turno, frammento di contesto
  e segnale di pertinenza, in un formato coerente con la ricerca di codice/documenti già offerta dallo
  strumento.
- **FR-007**: Il comando di ricerca MUST accettare vincoli temporali opzionali (inizio e/o fine) e un
  limite opzionale al numero di risultati, applicandoli tramite il servizio del core.
- **FR-008**: Il comando di ricerca MUST essere di sola lettura: non MUST modificare l'archivio.
- **FR-009**: Il comando di ricerca MUST offrire, su richiesta, i risultati in una forma strutturata e
  consumabile programmaticamente.

#### Cattura automatica a fine sessione (hook)

- **FR-010**: Il sistema MUST fornire un meccanismo che, alla fine di una sessione di lavoro con
  l'assistente ospite, avvia automaticamente l'archiviazione delle sessioni del progetto, senza
  intervento dell'utente.
- **FR-011**: Il meccanismo di cattura automatica MUST limitarsi a invocare il comando di archiviazione
  host-agnostico; non MUST contenere logica di archiviazione propria.
- **FR-012**: Il meccanismo di cattura automatica MUST essere non-bloccante: non MUST né interrompere
  né rallentare in modo percepibile la chiusura della sessione.
- **FR-013**: Il meccanismo di cattura automatica MUST essere non-fatale: un eventuale fallimento
  dell'archiviazione MUST essere assorbito senza propagare un errore all'esperienza di sessione.

#### Gate di privacy (trasversale)

- **FR-014**: Tutte e tre le capacità MUST essere subordinate a un unico interruttore di abilitazione
  della memoria, disattivato per impostazione predefinita (privacy-by-default).
- **FR-015**: Quando la memoria è disattivata, il meccanismo di cattura automatica MUST essere un
  no-op silenzioso (nessuna azione, nessun messaggio).
- **FR-016**: Quando la memoria è disattivata e un comando (archiviazione o ricerca) viene invocato
  esplicitamente, il comando MUST rispondere con un messaggio d'errore azionabile che spiega come
  abilitare la memoria, senza eseguire alcuna archiviazione o ricerca.

#### Portabilità e non-regressione

- **FR-017**: I comandi (archiviazione e ricerca) MUST essere host-agnostici: MUST funzionare su
  qualunque progetto ospite senza assunzioni sull'assistente ospite (Principio X).
- **FR-018**: Il meccanismo di cattura automatica MUST essere host-specifico (legato a un assistente
  ospite concreto) e MUST limitarsi ad adattare il *trigger* di fine sessione all'invocazione del
  comando host-agnostico, lasciando ad adattatori futuri il supporto di altri assistenti.
- **FR-019**: La feature MUST essere puramente additiva: i comandi e i servizi del core già esistenti
  MUST restare invariati nel comportamento.

### Key Entities *(include if feature involves data)*

- **Comando di memoria**: la superficie da riga di comando che l'utente invoca per archiviare o
  cercare. Non possiede stato né logica di dominio: traduce le opzioni dell'utente in una chiamata al
  servizio del core e ne formatta l'esito (umano o strutturato).
- **Report di archiviazione**: l'esito dell'archiviazione presentato all'utente — conteggi di sessioni
  archiviate e saltate, in forma leggibile o strutturata.
- **Risultato di ricerca (presentato)**: un turno corrispondente con la sua citazione (sessione, ruolo,
  indice turno, frammento, segnale di pertinenza), formattato per la riga di comando coerentemente con
  la ricerca di codice/documenti esistente.
- **Trigger di fine sessione**: l'evento dell'assistente ospite che segnala la conclusione di una
  sessione e fa scattare la cattura automatica. È host-specifico.
- **Interruttore di memoria**: l'impostazione unica, disattivata per default, che governa se le tre
  capacità sono attive; quando spenta, l'automatismo tace e i comandi rispondono con un errore
  azionabile.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Con la memoria abilitata, un singolo comando archivia le sessioni del progetto e ne
  riporta il conteggio; un secondo lancio immediato riporta zero nuove archiviazioni nel 100% dei casi
  (idempotenza verificabile dall'esterno).
- **SC-002**: Con la memoria abilitata, una query con una parola presente in un turno archiviato fa
  comparire quel turno tra i risultati del comando nel 100% dei casi, con tutti i campi di citazione
  attesi.
- **SC-003**: I filtri temporali e il limite di risultati passati al comando di ricerca producono
  esattamente l'effetto di filtro/troncamento previsto (zero risultati fuori finestra; numero di
  risultati mai superiore al limite imposto).
- **SC-004**: Alla fine di una sessione con la memoria abilitata, l'archiviazione viene avviata
  automaticamente senza alcun intervento dell'utente nel 100% delle chiusure di sessione osservate.
- **SC-005**: Un fallimento dell'archiviazione automatica non interrompe né rallenta in modo
  percepibile la chiusura della sessione: la sessione si chiude comunque normalmente nel 100% dei casi
  simulati di guasto.
- **SC-006**: Con la memoria disattivata (default), nessuna sessione viene archiviata né alcun
  contenuto persistito a fine sessione, e l'automatismo non emette alcun messaggio, nel 100% dei casi.
- **SC-007**: Con la memoria disattivata, ogni comando invocato esplicitamente restituisce un
  messaggio d'errore che nomina esplicitamente l'azione per abilitare la memoria, nel 100% dei casi,
  senza eseguire archiviazione o ricerca.
- **SC-008**: I comandi producono risultati equivalenti su almeno due progetti ospite diversi senza
  modifiche al loro corpo (host-agnosticità verificata).
- **SC-009**: L'introduzione della feature non altera il comportamento osservabile dei comandi e dei
  servizi del core preesistenti (nessuna regressione).

## Assumptions

- **A-001 — MVP memoria su master**: si assume operativo il nucleo di memoria già su master — un
  servizio di archiviazione delle sessioni (idempotente, deterministico, non-fatale) e un servizio di
  ricerca episodica full-text locale, entrambi esposti dal core. Questa feature li *consuma* e non ne
  ridefinisce il comportamento.
- **A-002 — Feature non a backlog (annotazione)**: questa feature *non* era nel backlog dell'epica
  «memoria-conversazioni» (che enumera cattura, ricerca, distillazione, semantica, ecc.). Nasce come
  *superficie d'uso + grilletto* per l'MVP già implementato; è additiva e non sposta i confini delle
  feature esistenti dell'epica.
- **A-003 — Gate unico di privacy**: l'abilitazione della memoria è un singolo interruttore
  disattivato per default (privacy-by-default), coerente con il principio di privacy condiviso
  dell'epica. Non si introducono gate multipli.
- **A-004 — Evento di trigger = fine sessione (deciso)**: il grilletto della cattura automatica è
  l'evento di *fine sessione* dell'assistente ospite, non la fine di ogni singolo turno. Razionale: a
  fine sessione il transcript è completo; ancorare la cattura alla fine di ogni turno catturerebbe una
  sessione ancora in corso e, data l'idempotenza, ne congelerebbe una versione parziale.
- **A-005 — Host-agnosticità asimmetrica (deciso)**: i comandi sono host-agnostici (girano su qualunque
  progetto ospite); l'hook è host-specifico (Claude Code per primo) ed è l'adattatore del *trigger*
  all'ospite, che si limita a invocare il comando host-agnostico. Altri assistenti = adattatori futuri.
- **A-006 — Struttura del comando rinviata al design**: se la memoria sia esposta come gruppo di
  sotto-comandi (es. un «memory» con «archive»/«search») o come comandi piatti è una scelta di
  realizzazione del plan; lo stile segue quello dei comandi già offerti dallo strumento.
- **A-007 — Ambito dell'archiviazione del comando rinviato al design**: se il comando (e quindi l'hook)
  archivi tutte le sessioni del progetto in modo idempotente o solo quella corrente è materia di
  design; in entrambi i casi l'idempotenza garantisce che il rilancio sia sicuro.
- **A-008 — Formato preciso dell'output rinviato al design**: il layout esatto dell'output di ricerca
  e del report di archiviazione (umano e strutturato) è materia di design; il vincolo è la coerenza
  con la ricerca di codice/documenti già offerta dallo strumento e la completezza dei campi di
  citazione.
- **A-009 — Meccanismo di wiring dell'hook rinviato al design**: come l'hook di fine sessione sia
  cablato presso l'assistente ospite (file di configurazione/hook dell'host) è materia di design; in
  questa feature l'hook è cablato per il dogfood del progetto stesso.
- **A-010 — Comportamento esatto del gate rinviato al design**: la forma precisa della risposta a
  memoria disattivata (errore azionabile vs richiesta interattiva) è materia di design; il vincolo è
  che a comando esplicito corrisponda un errore azionabile e all'hook un no-op silenzioso.
- **A-011 — Determinismo dell'archiviazione**: l'archiviazione è deterministica, idempotente e
  non-fatale, dunque adatta a un automatismo unattended (lavoro meccanico, non giudizio); questa è una
  proprietà del servizio del core, non reintrodotta qui.

### Dependencies

- **Nucleo di memoria su master (a monte)**: servizio di archiviazione delle sessioni e servizio di
  ricerca episodica esposti dal core. Senza di essi i comandi non avrebbero nulla a cui delegare.
- **Superficie da riga di comando esistente dello strumento**: i nuovi comandi si innestano nello stile
  e nelle convenzioni della riga di comando già offerta (ricerca di codice/documenti e affini).
- **Meccanismo di hook dell'assistente ospite**: l'hook di fine sessione si appoggia al sistema di
  hook dell'assistente ospite (Claude Code per primo), analogamente agli hook già presenti nel
  progetto.

### Out of Scope

- **Ricerca semantica/embedding sull'archivio** (FEAT-004 dell'epica): qui solo full-text locale via il
  servizio episodico esistente.
- **Aggancio alla distillazione del wiki** (FEAT-003): l'archivio non viene qui collegato a
  `distill`/`record`.
- **Governance/retention ed enforcement della scadenza** (FEAT-006): nessuna politica di retention è
  introdotta o applicata qui.
- **Cattura selettiva «remember this»** (FEAT-005): qui non si marca selettivamente cosa archiviare.
- **Hook per assistenti diversi da Claude Code** (analogo a FEAT-008): qui l'hook copre il primo
  assistente ospite; altri adattatori sono successivi.
- **Distribuzione dell'hook su ospiti esterni** (es. installazione su un progetto terzo): qui l'hook è
  cablato per il dogfood del progetto stesso; la distribuzione è un'estensione successiva.
- **Politica di aggiornamento di una sessione parziale già cresciuta**: l'idempotenza attuale è
  «inserisci-o-ignora»; un eventuale refresh di sessioni parziali è una decisione futura.
- **Interfaccia grafica o pannello dedicato**: qui la superficie è solo la riga di comando.
