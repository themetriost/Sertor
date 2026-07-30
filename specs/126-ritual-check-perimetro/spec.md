# Feature Specification: il perimetro dello step è anche ciò che non hai ancora consegnato — e va dichiarato

**Feature Branch**: `126-ritual-check-perimetro`

**Created**: 2026-07-30

**Status**: Draft

**Input**: E10-FEAT-060 (epica `debito-tecnico`) — requisiti EARS in
[`requirements/debito-tecnico/feat-060-perimetro-ritual-check/requirements.md`](../../requirements/debito-tecnico/feat-060-perimetro-ritual-check/requirements.md)

## User Scenarios & Testing *(mandatory)*

L'«utente» qui è **chi chiude uno step di lavoro** — una persona o un agente — e usa l'aiuto
deterministico che elenca cosa andrebbe dichiarato prima di considerare lo step finito.

### User Story 1 — Ricevo i candidati del lavoro che ho davvero fatto (Priority: P1)

Sto chiudendo uno step. Ho modificato pagine e file, e **non ho ancora consegnato niente al controllo
di versione** — perché la regola stessa dice di consegnare e registrare *insieme*. Chiedo all'aiuto
cosa dovrei dichiarare, e voglio l'elenco del lavoro che ho **sotto le mani**, non di quello che ho
già consegnato ieri.

**Why this priority**: è il difetto riscontrato dal campo e la ragione d'essere dell'aiuto. Oggi la
risposta è *«non c'è niente da dichiarare»* nel momento esatto in cui c'è tutto da dichiarare, e il
controllo d'uscita blocca due passi dopo. Senza questa storia la capacità non esiste.

**Independent Test**: si prende lo stesso identico lavoro in due stati — consegnato e non consegnato —
e si verifica che l'elenco dei candidati sia **lo stesso**. Se dipende dallo stato di consegna, la
storia non è soddisfatta.

**Acceptance Scenarios**:

1. **Given** una pagina modificata e non ancora consegnata, **When** chiedo i candidati dello step,
   **Then** quella pagina compare fra quelle in perimetro.
2. **Given** una pagina **nuova e mai consegnata**, **When** chiedo i candidati, **Then** la pagina
   compare in perimetro **e** viene considerata «pagina aggiunta» nello step.
3. **Given** lo stesso contenuto in due stati (tutto consegnato · niente consegnato), **When** chiedo i
   candidati nei due casi, **Then** ottengo lo stesso elenco.
4. **Given** metà lavoro consegnato e metà no, **When** chiedo i candidati, **Then** **non** ricevo
   segnalazioni che affermano il falso sulla metà non consegnata.
5. **Given** una modifica che il controllo di versione ignora deliberatamente, **When** chiedo i
   candidati, **Then** quella modifica **non** entra nel perimetro.

---

### User Story 2 — So sempre quale realtà è stata guardata (Priority: P2)

Leggo la risposta dell'aiuto. Che sia un elenco pieno o vuoto, voglio **sapere su cosa è stata
calcolata**: quanto veniva da lavoro già consegnato, quanto da lavoro ancora sotto le mani.

**Why this priority**: è la causa profonda, non il sintomo. Il difetto non è nato perché un numero era
sbagliato, ma perché **nessuno poteva accorgersi** che la domanda posta e la domanda risposta fossero
diverse. Senza questa storia il difetto può ripresentarsi in silenzio a ogni futura divergenza.

**Independent Test**: si esegue l'aiuto e si verifica che la dichiarazione del perimetro sia presente
**sempre** — anche quando l'esito è «nessun candidato», che è il caso in cui serve di più.

**Acceptance Scenarios**:

1. **Given** un perimetro composto da entrambe le sorgenti, **When** leggo la risposta, **Then** la
   risposta dichiara entrambe e quanto ciascuna ha contribuito.
2. **Given** un perimetro con **zero** candidati, **When** leggo la risposta, **Then** la risposta
   dichiara comunque cosa è stato guardato — così uno zero non è ambiguo.
3. **Given** che ho indicato io esplicitamente le pagine da esaminare, **When** leggo la risposta,
   **Then** la risposta dichiara che il perimetro è quello che ho fornito io.
4. **Given** una risposta destinata a una persona (non alla forma dati), **When** la leggo, **Then** la
   dichiarazione del perimetro è presente anche lì.

---

### User Story 3 — Se non può guardare, me lo dice (Priority: P3)

Se l'aiuto non riesce a determinare cosa è cambiato, voglio un errore chiaro. **Non** voglio una
risposta vuota che assomiglia a «è tutto a posto».

**Why this priority**: chiude una degradazione silenziosa già presente. Vale meno delle prime due
perché si manifesta solo quando qualcosa è rotto nell'ambiente — ma proprio in quel momento una
risposta rassicurante e falsa è il danno peggiore.

**Independent Test**: si rende indisponibile ciascuna interrogazione necessaria, una alla volta, e si
verifica che l'esito sia un errore dichiarato e non un elenco vuoto.

**Acceptance Scenarios**:

1. **Given** che la determinazione del lavoro consegnato non riesce, **When** chiedo i candidati,
   **Then** ottengo un errore esplicito, non un elenco vuoto.
2. **Given** che la determinazione del lavoro non consegnato non riesce, **When** chiedo i candidati,
   **Then** ottengo un errore esplicito.
3. **Given** che la determinazione delle **pagine aggiunte** non riesce, **When** chiedo i candidati,
   **Then** l'esito non viene trattato come «nessuna pagina aggiunta».
4. **Given** che il perimetro non è determinabile in alcun modo, **When** chiedo i candidati, **Then**
   fallisco in modo esplicito — comportamento odierno, da preservare.

---

### Edge Cases

- **Una modifica di sole terminazioni di riga.** Un file che risulta «toccato» senza che nessuno vi
  abbia scritto nulla non deve produrre candidati: bloccherebbe la chiusura di uno step per un file che
  nessuno ha modificato. *(Caso già occorso su un'altra superficie, non ipotetico.)*
- **Una pagina nuova mai consegnata che è essa stessa la distillazione.** Se ho appena creato la pagina
  d'entità, l'aiuto **non** deve suggerirmi di distillare: la nuova pagina va riconosciuta come tale
  anche se non è ancora stata consegnata.
- **Una cartella nuova non consegnata contenente più file.** Va nominata per i file che contiene, non
  collassata nel nome della cartella.
- **Rinomine.** Vanno contate una volta sola, sul nome di destinazione.
- **Perimetro fornito esplicitamente dall'utente.** Non deve mescolarsi con quello derivato: se
  l'utente dice cosa guardare, si guarda quello.
- **Un elenco vuoto legittimo** (non c'è davvero nulla) deve restare distinguibile da un elenco vuoto
  perché non si è riusciti a guardare.

## Requirements *(mandatory)*

### Functional Requirements

**Perimetro**

- **FR-001**: Il perimetro di uno step DEVE comprendere sia il lavoro già consegnato al controllo di
  versione sia quello ancora **non consegnato**.
- **FR-002**: Una pagina modificata e non consegnata DEVE comparire fra quelle in perimetro.
- **FR-003**: Una pagina **nuova e non ancora tracciata** DEVE comparire in perimetro ed essere trattata
  come pagina **aggiunta** nello step.
- **FR-004**: Una pagina nuova e non tracciata collocata in una **cartella-casa della distillazione**
  DEVE contare come distillazione già avvenuta, esattamente come se fosse consegnata.
- **FR-005**: Una differenza di sole terminazioni di riga NON DEVE far entrare un file nel perimetro.
- **FR-006**: I percorsi **ignorati dal controllo di versione** NON DEVONO entrare nel perimetro.
- **FR-007**: Quando l'utente indica esplicitamente le pagine, quello DEVE essere l'intero perimetro,
  senza unione con le sorgenti derivate.

**Dichiarazione**

- **FR-008**: Ogni risposta DEVE dichiarare **quali sorgenti** hanno composto il perimetro e **quanti
  percorsi** ciascuna ha contribuito.
- **FR-009**: La dichiarazione DEVE comparire **sempre**, anche quando non è stato trovato alcun
  candidato.
- **FR-010**: La dichiarazione DEVE comparire sia nella forma dati sia nella **risposta destinata a una
  persona**.
- **FR-011**: Quando il perimetro è fornito dall'utente, la risposta DEVE dichiararlo come tale.
- **FR-012**: L'identificativo del contratto dati DEVE restare invariato; l'estensione DEVE essere
  **additiva**.

**Fallimento dichiarato**

- **FR-013**: Il fallimento di una qualunque interrogazione necessaria al perimetro DEVE produrre un
  errore dichiarato, mai un risultato parziale presentato come completo.
- **FR-014**: Il fallimento della determinazione delle pagine **aggiunte** NON DEVE essere interpretato
  come «nessuna pagina aggiunta».
- **FR-015**: Un perimetro non determinabile DEVE continuare a produrre un errore esplicito.

**Invarianti**

- **FR-016**: La capacità DEVE restare di **sola lettura**: nessuna pagina creata, nessuna correzione
  applicata. Trova, non giudica.
- **FR-017**: La capacità DEVE restare utilizzabile **senza rete** e senza alcun modello linguistico.
- **FR-018**: La capacità DEVE restare **indipendente dal progetto ospite**: cartelle, tassonomia e
  soglie continuano a provenire dalla configurazione, e il ramo principale continua a essere rilevato a
  runtime, mai assunto.
- **FR-019**: L'ordine dei percorsi in uscita DEVE essere stabile fra esecuzioni, perché la risposta
  finisce in una dichiarazione che viene confrontata nel tempo.

### Key Entities

- **Perimetro dello step** — l'insieme del lavoro che lo step ha toccato. Ha due **sorgenti**
  (consegnato · non consegnato) e una **provenienza dichiarata**; oggi è implicito e coincide con una
  sola sorgente.
- **Sorgente del perimetro** — da dove è stato ricavato un insieme di percorsi, con il proprio conteggio.
  È l'entità che oggi **non esiste**, e la cui assenza rende il difetto invisibile.
- **Candidato** — una pagina o un gruppo di pagine che merita un giudizio (distillazione o deriva); non
  è un verdetto, è una proposta.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Lo stesso lavoro produce lo **stesso elenco di candidati** indipendentemente dal fatto che
  sia stato consegnato al controllo di versione: **0 differenze** fra i due casi.
- **SC-002**: Nello scenario misto (parte consegnata, parte no) il numero di segnalazioni che affermano
  il falso sul lavoro non consegnato è **0** (oggi è 1 su un caso minimo di due pagine).
- **SC-003**: Il **100%** delle risposte dichiara il perimetro misurato, inclusi i casi con zero
  candidati.
- **SC-004**: Per **ciascuna** interrogazione necessaria al perimetro esiste un caso che la rende
  indisponibile e verifica che l'esito sia un errore dichiarato: copertura **completa**, nessuna esclusa.
- **SC-005**: Chi chiude uno step **prima** di consegnare riceve un elenco non vuoto quando c'è lavoro —
  verificabile eseguendo la capacità su questo stesso progetto durante uno step reale, dove oggi
  risponde zero.
- **SC-006**: Il costo aggiuntivo per esecuzione resta entro **due** interrogazioni al controllo di
  versione, le stesse che la capacità gemella già paga.

## Assumptions

- **La semantica di derivazione del lavoro non consegnato già in produzione è corretta** e viene
  riusata, non ridiscussa: è in esercizio da due versioni ed è confermata dal campo.
- **Nessun consumatore programmatico** dipende oggi dalla forma dati di questa capacità (verificato sul
  repository): l'estensione additiva è quindi sicura, e resta additiva per prudenza.
- **La dichiarazione del perimetro è sempre presente**, non solo quando il perimetro è composito:
  l'alternativa reintrodurrebbe un silenzio proprio nel caso semplice, che è la classe del difetto.
- **Nessuna opzione per restringere il perimetro al solo consegnato** viene introdotta ora: nessuno
  l'ha richiesta, e aggiungerla senza un caso d'uso reale sarebbe superficie non giustificata. Se
  emergerà, è additiva.
- **Per una pagina mai consegnata tutti i collegamenti risultano nuovi**, perché non esiste una versione
  precedente con cui confrontarli. È il comportamento corretto e viene **dichiarato** invece che
  ereditato tacitamente.
- **L'unificazione strutturale** delle due derivazioni resta **fuori ambito** ed è già tracciata come
  voce di backlog a sé: qui si allinea il comportamento, non si fondono i moduli.
- **La metà «già consegnata» resta quella odierna, e questa è una scelta esplicita.** Le due capacità
  non divergevano solo sull'albero di lavoro: divergono **anche** su quale porzione di consegnato
  guardano — questa parte da un **riferimento indicato dall'utente** (tutto il ramo di lavoro dalla sua
  biforcazione), la gemella parte dall'**ultima registrazione**. Si mantiene la prima, perché è il
  significato dichiarato dell'opzione che l'utente passa: **cambiarla sotto lo stesso nome ridefinirebbe
  in silenzio un'opzione pubblica**, che è precisamente il difetto qui in riparazione. Conseguenza
  accettata: su un ramo che contiene più step già registrati, il perimetro è più ampio dello step
  corrente — e proprio per questo la dichiarazione del perimetro (FR-008) diventa la cosa che rende
  l'ampiezza **leggibile** invece che sorprendente.
