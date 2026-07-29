# Feature Specification: la registrazione copre un changeset, non una data

**Feature Branch**: `124-copertura-changeset-scan`

**Created**: 2026-07-29

**Status**: Draft

**Input**: E10-FEAT-062 — il gate di freschezza del wiki smette di vedere il lavoro non appena una registrazione del giorno compare fra le modifiche non consegnate. Requisiti EARS in `requirements/debito-tecnico/feat-062-copertura-changeset-scan/requirements.md`.

## User Scenarios & Testing *(mandatory)*

Gli attori sono due: l'**agente** che lavora su un progetto ospite e deve registrare ciò che fa, e il
**manutentore dell'ospite**, che si fida del gate per sapere che il wiki non è andato alla deriva.

### User Story 1 - Il gate resta vivo per tutta la sessione (Priority: P1)

Un agente lavora, registra ciò che ha fatto fino a quel momento, **e poi continua a lavorare**. Oggi,
dal momento della registrazione in avanti, il gate non vede più nulla: la sessione si chiude senza
attrito anche se metà del lavoro non è registrato. L'agente vuole che la registrazione valga **per ciò
che ha registrato**, non per il resto della giornata.

**Why this priority**: è il difetto per cui la capacità esiste. Un gate che smette di guardare appena
lo si soddisfa è indistinguibile da un gate disinstallato, e chi segue la regola è **esattamente** chi
lo disattiva. Senza questa storia le altre due non hanno valore.

**Independent Test**: si registra una voce, si produce altro lavoro, si chiede se c'è lavoro non
registrato. Deve dire di sì e nominare i file prodotti dopo.

**Acceptance Scenarios**:

1. **Given** una sessione che ha registrato il proprio lavoro e poi ne ha prodotto altro, **When** si
   verifica se c'è lavoro non registrato, **Then** il lavoro successivo risulta **non registrato** e i
   suoi file sono **nominati**.
2. **Given** una sessione che ha registrato tutto ciò che ha prodotto, **When** si verifica, **Then**
   non risulta nulla di non registrato e la sessione può chiudersi.
3. **Given** lavoro già consegnato e mai registrato, e una registrazione del giorno presente
   nell'albero che **non lo riguarda**, **When** si verifica, **Then** quel lavoro risulta ancora non
   registrato.
4. **Given** due sessioni che lavorano in parallelo sullo stesso progetto, **When** la prima registra
   il proprio lavoro, **Then** il lavoro della seconda risulta comunque non registrato.
5. **Given** una registrazione scritta ma **non ancora consegnata**, **When** si verifica, **Then**
   vale come registrazione — non si deve consegnare per soddisfare il gate.

---

### User Story 2 - Un verdetto «pulito» non può nascere da un controllo fallito (Priority: P2)

Il manutentore vede «nessun lavoro da registrare» e si fida. Oggi quella risposta può significare due
cose diverse — *ho guardato e non c'è niente* oppure *non sono riuscito a guardare* — e le due sono
indistinguibili nell'esito.

**Why this priority**: è un difetto **indipendente** dal primo e con lo stesso verso: produce un via
libera che sembra pulizia. Non è ipotetico su progetti che eseguono operazioni di versionamento in
parallelo, dove il controllo può non riuscire proprio mentre la sessione si chiude.

**Independent Test**: si rende indisponibile la fonte da cui il controllo deriva la risposta, si
verifica, e si guarda se l'esito dichiara la condizione invece di dire «pulito».

**Acceptance Scenarios**:

1. **Given** un progetto in cui la fonte del controllo non è interrogabile in quel momento, **When**
   si verifica se c'è lavoro non registrato, **Then** l'esito **dichiara** che la determinazione non è
   riuscita, in un campo ispezionabile.
2. **Given** lo stesso stato del progetto con la fonte disponibile, **When** si verifica, **Then**
   l'esito riporta il lavoro non registrato — cioè il «pulito» del caso precedente **non** era la
   realtà.
3. **Given** un esito la cui determinazione non è riuscita, **When** la sessione tenta di chiudersi,
   **Then** il gate **non** lo tratta come «pulito».

---

### User Story 3 - La registrazione dice cosa copre (Priority: P3)

Chi legge il giornale — una persona, o uno strumento che ne deriva altro — vuole sapere **su cosa**
una voce si è espressa, senza doverlo dedurre dalla data o dalla prosa.

**Why this priority**: è il meccanismo che rende possibile la Storia 1, ma ha valore proprio anche
senza il gate: rende il giornale verificabile e rende falsificabile una registrazione superficiale.
Ha priorità più bassa perché il valore percepito è indiretto.

**Independent Test**: si registra una voce e si legge il giornale: la voce deve indicare l'insieme su
cui si è espressa, e quell'insieme deve corrispondere al lavoro presente in quel momento.

**Acceptance Scenarios**:

1. **Given** una sessione con del lavoro non registrato, **When** si aggiunge una voce di giornale,
   **Then** la voce riporta l'insieme di elementi che copre, **derivato** dallo stato del progetto e
   non chiesto a chi scrive.
2. **Given** due voci scritte nello stesso giorno su lavori diversi, **When** si verifica, **Then**
   ciò che risulta coperto è **l'unione** delle due.
3. **Given** una voce che copre un elemento, **When** quell'elemento viene modificato di nuovo,
   **Then** torna a risultare non registrato. *(Vedi FR-011: opzionale, dipende dalla granularità
   scelta.)*

---

### Edge Cases

- **Registrazione priva di contenuto.** Una registrazione del giorno **vuota**, o toccata senza
  scrivervi nulla (spaziatura, normalizzazione automatica del testo), **non** deve valere come
  registrazione. Oggi la soddisfa: è la stessa distinzione fra «risulta modificato» e «il contenuto è
  cambiato» già pagata una volta su questa capacità.
- **Registrazione di un altro giorno.** Una voce non consegnata che appartiene a un giorno diverso non
  copre il lavoro di oggi, ma il suo esistere va **nominato**: senza, il manutentore vede un giornale
  già modificato e un gate che blocca comunque, e la diagnosi diventa un'indagine.
- **Progetto senza sistema di versionamento.** Resta supportato: l'esito continua a dichiarare che sta
  usando una stima e **perché** (comportamento già esistente, da non regredire).
- **Registrazioni scritte prima di questa capacità.** Non dichiarano cosa coprono → vedi
  [NEEDS CLARIFICATION Q1].
- **Elemento rimosso.** Una rimozione è lavoro: deve poter risultare non registrata come una modifica.
- **Registrazione che dichiara di coprire tutto.** Resta possibile, ma diventa **scritta e
  falsificabile** — è un miglioramento rispetto all'azzeramento invisibile di oggi, non un'eliminazione
  del giudizio.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il sistema MUST determinare il lavoro non registrato confrontando il lavoro cambiato con
  l'insieme di elementi **coperti dalle registrazioni**, e MUST NOT trattare la sola esistenza di una
  registrazione come copertura di alcunché.
- **FR-002**: Il sistema MUST riconoscere una registrazione solo quando **una voce è stata aggiunta**,
  e MUST NOT riconoscere come registrazione un file di giornale vuoto, privo di voci, o toccato senza
  contenuto nuovo.
- **FR-003**: Quando del lavoro è prodotto **dopo** una registrazione, il sistema MUST riportarlo come
  non registrato.
- **FR-004**: Il sistema MUST determinare la copertura **indipendentemente dalla data** della
  registrazione in cui una voce risiede.
- **FR-005**: L'operazione di registrazione MUST **derivare e conservare** l'insieme di elementi che la
  voce copre, senza richiederlo a chi la scrive.
- **FR-006**: Se le informazioni necessarie a determinare il lavoro non registrato non sono
  ottenibili, il sistema MUST dichiarare quella condizione in un campo ispezionabile e MUST NOT
  riportare «nessun lavoro non registrato» come se la determinazione fosse riuscita.
- **FR-007**: Il sistema MUST NOT sostituire in silenzio un insieme vuoto quando un controllo non
  riesce.
- **FR-008**: Quando il consumatore bloccante riceve un esito la cui determinazione **non** è
  riuscita, MUST NOT trattarlo come «pulito».
- **FR-009**: L'identificatore di schema dell'esito MUST restare invariato; ogni informazione nuova
  MUST essere veicolata da campi **aggiuntivi**.
- **FR-010**: Il sistema MUST nominare gli elementi non registrati, conservando il troncamento con
  conteggio dichiarato già esistente.
- **FR-011**: Dove l'identità del **contenuto** è disponibile, il sistema SHOULD considerare
  nuovamente non registrato un elemento coperto il cui contenuto è cambiato da quando è stato coperto.
- **FR-012**: Il meccanismo di copertura MUST essere indipendente dal progetto ospite: ogni
  impostazione specifica dell'ospite MUST derivare dalla sua configurazione, senza percorsi cablati.
- **FR-013**: Su progetti privi di sistema di versionamento il sistema MUST conservare il
  comportamento attuale e continuare a dichiarare la causa tipizzata del ripiego.
- **FR-014**: Una registrazione **non consegnata** MUST valere come registrazione; il sistema MUST NOT
  richiedere la consegna per considerare coperto il lavoro.
- **FR-015**: Una registrazione non consegnata che appartiene a un **giorno diverso** MUST essere
  nominata nell'esito, pur non contribuendo alla copertura di oggi.
- **FR-016**: Per le registrazioni prive di copertura dichiarata, il sistema MUST applicare la regola
  di transizione decisa in [NEEDS CLARIFICATION Q1].

### Key Entities

- **Registrazione**: una voce di giornale. Ha un giorno di residenza (che **non** determina cosa
  copre), un contenuto, e un **insieme coperto**.
- **Insieme coperto**: gli elementi di lavoro su cui una registrazione si è espressa. Derivato al
  momento della scrittura; le registrazioni si **compongono** per unione.
- **Lavoro in perimetro**: gli elementi cambiati che appartengono alle aree che l'ospite dichiara di
  voler sorvegliare, esclusi quelli che l'ospite ha dichiarato di ignorare.
- **Esito della verifica**: quanto lavoro non registrato c'è, **quali** elementi, **come** è stata
  ottenuta la risposta, e — nuovo — **se la determinazione è riuscita**.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Negli **otto** scenari misurati in cui oggi il gate non vede lavoro non registrato, dopo
  la modifica lo vede in **tutti e otto**, nominando gli elementi → **0** casi di non-rilevazione
  residui su quell'insieme.
- **SC-002**: Gli scenari che oggi funzionano continuano a funzionare: **0** regressioni sui casi che
  hanno chiuso il blocco-di-sessione precedente, in particolare *«consegna seguita da allineamento non
  impedisce la chiusura»* e *«lavoro e registrazione consegnati insieme non lasciano nulla in
  sospeso»*.
- **SC-003**: Dopo una registrazione, il lavoro prodotto in seguito torna a risultare non registrato
  → il gate resta vivo per il **100%** della sessione, non solo fino alla prima registrazione.
- **SC-004**: Una registrazione vuota, priva di voci, o toccata senza contenuto **non** soddisfa il
  gate → **0** casi soddisfatti senza una voce reale.
- **SC-005**: Quando la determinazione non riesce, l'esito lo dichiara e il consumatore bloccante non
  lo interpreta come «pulito» → **0** verdetti «pulito» indistinguibili da un controllo fallito.
- **SC-006**: L'esito non dipende dal giorno in cui la voce risiede → rimuovere la data dalla logica
  non cambia **alcun** verdetto corretto.
- **SC-007**: L'identificatore di schema resta invariato e un consumatore non aggiornato continua a
  funzionare con l'esito nuovo, verificato da una guardia dedicata.
- **SC-008**: Il costo della verifica non cresce oltre il **+15%** rispetto al riferimento misurato
  (~330 ms per interrogazione, pagati a ogni fine turno).
- **SC-009**: Su un progetto privo di sistema di versionamento l'esito continua a dichiarare stima e
  causa → **0** regressioni sul comportamento host-agnostico.

## Assumptions

- **La verifica resta deterministica e senza giudizio**: decide un meccanismo, non un modello. Cosa
  scrivere in una registrazione resta giudizio di chi la scrive.
- **La copertura è a granularità di elemento, non di significato**: una voce può dichiarare di coprire
  un elemento di cui non parla. È un miglioramento grande, **non** l'eliminazione del giudizio, e va
  detto invece che lasciato intendere.
- **La registrazione è il posto giusto dove conservare la copertura**: sta nell'artefatto stesso,
  leggibile da chi lo consulta, invece che in un file di servizio invisibile — che sarebbe **una copia
  in più da riconciliare**.
- **L'operazione di registrazione può derivare la copertura da sé**, senza input umano e senza
  chiamare nulla di esterno al progetto.
- **Il consumatore bloccante e quello di promemoria consumano lo stesso esito**: non si introducono
  due nozioni diverse di «lavoro non registrato».
- **Il perimetro sorvegliato non cambia con questa capacità**: quali aree guardare è una decisione
  separata, già tracciata altrove.

## Clarifications

### Q1 — Registrazioni prive di copertura dichiarata (transizione)

**Context**: FR-016, ed edge case *«registrazioni scritte prima di questa capacità»*. Ogni ospite ha
un giornale pieno di voci scritte prima che la copertura esistesse.

**What we need to know**: una voce **senza** copertura dichiarata, cosa copre?

| Option | Answer | Implications |
|--------|--------|--------------|
| A | **Copre tutto** ciò che esisteva al momento in cui è stata scritta | Nessun blocco improvviso all'aggiornamento; il difetto sopravvive per le voci vecchie finché non ruotano (in pratica: un giorno). Compatibile, prudente, e il gate resta cieco per quella finestra. |
| B | **Non copre nulla** | Corretto immediatamente; ma al primo aggiornamento **ogni ospite** vede il gate bloccare su lavoro che credeva registrato — incluso chi ha otto progetti sullo stesso host. Rischia di insegnare ad aggirare il gate, che è il difetto che stiamo chiudendo. |
| C | **Copre tutto, e lo dichiara** — la voce vecchia vale come A, ma l'esito **nomina** quante registrazioni stanno valendo per compatibilità | Come A sul comportamento, ma la deroga è **visibile** invece che silenziosa (coerente col principio «conservare una copia stantia può essere giusto, conservarla in silenzio no»). Costa un campo in più nell'esito. |
| Custom | Rispondi con la tua regola | — |

**Your choice**: _[in attesa]_
