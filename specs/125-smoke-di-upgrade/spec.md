# Feature Specification: smoke di upgrade — testare la strada che spediamo

**Feature Branch**: `124-copertura-changeset-scan` *(consegnata insieme a E10-FEAT-062, una sola PR)*

**Created**: 2026-07-29

**Status**: Draft

**Input**: E15-FEAT-012 — testiamo l'installazione, spediamo aggiornamenti. Requisiti EARS in
`requirements/fedelta-dogfood/smoke-di-upgrade/requirements.md`.

## User Scenarios & Testing *(mandatory)*

Gli attori: **chi rilascia** (deve poter affermare che l'aggiornamento funziona, con una prova) e
**l'ospite** che riceve il rilascio — oggi l'unico che esegue davvero il verbo che spediamo.

### User Story 1 - Chi rilascia sa che l'aggiornamento funziona (Priority: P1)

Prima che un rilascio raggiunga gli ospiti, un host usa-e-getta ha **installato la release
precedente**, ha **aggiornato** a quella corrente, e gli **esiti** dell'aggiornamento sono stati
verificati. Oggi si verifica solo l'installazione su un host pulito: nessuna prova tocca la strada che
gli ospiti percorrono davvero.

**Why this priority**: è l'intera feature. Su ~14 difetti reali arrivati dal campo, **13 stanno nella
superficie di consegna** e **7 richiedono un'installazione preesistente più vecchia** per manifestarsi
— un host pulito non può vederne nessuno, *per costruzione*.

**Independent Test**: si prende un difetto d'aggiornamento già noto, lo si ricrea nelle condizioni in
cui è stato osservato, e si verifica che il meccanismo lo **rilevi**.

**Acceptance Scenarios**:

1. **Given** un host su cui la release **precedente** è realmente installata, **When** si aggiorna alla
   versione in uscita, **Then** gli esiti dichiarati vengono verificati sullo **stato dell'host**, non
   sul contenuto del repository sorgente.
2. **Given** un host che **fissa** il runtime a un riferimento immutabile, **When** l'aggiornamento
   termina, **Then** si verifica che il riferimento punti alla versione **in uscita**.
3. **Given** un host con un automatismo di sessione già cablato in versione precedente, **When**
   l'aggiornamento termina, **Then** si verifica che ne resti **uno solo** e che sia quello corrente.
4. **Given** un host con configurazione **propria** già presente, **When** l'aggiornamento termina,
   **Then** quella configurazione è **preservata**.
5. **Given** un aggiornamento andato a buon fine, **When** si interroga la verifica di salute,
   **Then** l'host risulta sano.

---

### User Story 2 - Un fallimento è diagnosticabile senza rieseguirlo (Priority: P2)

Quando la verifica fallisce, chi legge il report deve capire **quale esito** diverge e **dove**, senza
riprodurre la situazione a mano.

**Why this priority**: senza questo la verifica esiste ma non è usabile sotto pressione — e una
verifica che costa troppo interpretare è una verifica che si disattiva. Ma non serve a nulla se la
Storia 1 non c'è.

**Independent Test**: si introduce deliberatamente una divergenza nota e si legge il report.

**Acceptance Scenarios**:

1. **Given** un esito che diverge, **When** la verifica termina, **Then** il report **nomina** l'esito
   divergente e l'host/assistente su cui è stato osservato.
2. **Given** un fallimento dovuto all'**ambiente** e non al prodotto (rete assente, strumenti
   mancanti), **When** la verifica termina, **Then** la causa ambientale è **distinta** da un difetto
   di prodotto invece di essere confusa con esso.

---

### User Story 3 - La verifica è vincolante al momento giusto (Priority: P3)

La verifica blocca un **rilascio**, non ogni singola modifica.

**Why this priority**: è la scelta che decide se il meccanismo sopravvive. Un controllo lento su ogni
modifica verrebbe aggirato; uno assente al rilascio non protegge nulla. Ha priorità più bassa perché
è una decisione di collocazione, non di capacità.

**Acceptance Scenarios**:

1. **Given** una modifica ordinaria, **When** viene proposta, **Then** la verifica d'aggiornamento
   **non** la rallenta.
2. **Given** un rilascio in preparazione, **When** lo si pubblica, **Then** la verifica
   d'aggiornamento è **già stata eseguita** ed è verde.

---

### Edge Cases

- **La release precedente non è determinabile** (primo rilascio, riferimento assente) → vedi
  [NEEDS CLARIFICATION Q3].
- **Aggiornamento che salta più versioni.** Un ospite reale l'ha fatto (0.3.0 → 0.3.3 in un passo) ed è
  **la condizione in cui il difetto del riferimento fisso è emerso** → vedi [NEEDS CLARIFICATION Q1].
- **Ambiente non disponibile** (rete, strumenti): la verifica deve **dichiararlo** e distinguerlo da un
  difetto, mai passare in silenzio né fallire come se il prodotto fosse rotto.
- **Un esito nuovo da verificare** emerge da un difetto futuro: aggiungerlo deve essere un gesto ovvio,
  altrimenti l'elenco invecchia e la verifica protegge il passato.
- **L'aggiornamento riscrive ciò che è nostro e preserva ciò che è dell'ospite**: la distinzione è
  già costata una regressione reale e va verificata, non assunta.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: La verifica di rilascio MUST esercitare il percorso di **aggiornamento** dalla versione
  precedentemente rilasciata a quella in uscita.
- **FR-002**: La versione precedente MUST essere **realmente installata** su un host usa-e-getta prima
  dell'aggiornamento, e MUST NOT essere simulata con artefatti scritti a mano.
- **FR-003**: La verifica MUST asserire lo **stato dell'host risultante**, e MUST NOT asserire il
  contenuto di un artefatto nel repository sorgente.
- **FR-004**: Quando l'host fissa il runtime a un riferimento immutabile, la verifica MUST asserire che
  il riferimento indichi la versione in uscita dopo l'aggiornamento.
- **FR-005**: Quando un automatismo di sessione viene ri-cablato dall'aggiornamento, la verifica MUST
  asserire che ne esista **esattamente uno** e che sia quello corrente.
- **FR-006**: Quando esiste configurazione **propria dell'ospite** prima dell'aggiornamento, la verifica
  MUST asserire che l'aggiornamento l'abbia preservata.
- **FR-007**: La verifica MUST asserire che il controllo di salute riporti un host sano dopo
  l'aggiornamento.
- **FR-008**: Se un esito asserito diverge, la verifica MUST fallire **nominando** l'esito divergente e
  l'host/assistente su cui è stato osservato.
- **FR-009**: La verifica MUST coprire ogni assistente supportato.
- **FR-010**: La verifica MUST essere **vincolante prima della pubblicazione** di un rilascio.
- **FR-011**: La verifica MUST distinguere un fallimento **ambientale** da un difetto di prodotto, e
  MUST NOT presentare il primo come il secondo.
- **FR-012**: Se la versione precedente non è determinabile, la verifica MUST dichiarare la condizione
  invece di saltare in silenzio → forma decisa in [NEEDS CLARIFICATION Q3].
- **FR-013**: Il perimetro della verifica MUST essere quello deciso in [NEEDS CLARIFICATION Q2].
- **FR-014**: Il punto di partenza dell'aggiornamento MUST essere quello deciso in
  [NEEDS CLARIFICATION Q1].
- **FR-015**: L'elenco degli esiti asseriti MUST vivere in un punto dichiarato, così che aggiungerne
  uno dopo un difetto nuovo sia un'aggiunta e non una ristrutturazione.

### Key Entities

- **Release precedente**: la versione da cui l'ospite parte. Identificata da un riferimento pubblico
  stabile, non da una copia locale.
- **Host usa-e-getta**: un ambiente creato per la verifica e buttato dopo, sul quale la release
  precedente è **realmente** installata.
- **Esito asserito**: una proprietà osservabile dello **stato dell'host** dopo l'aggiornamento (il
  riferimento si è mosso? l'automatismo è uno e aggiornato? la configurazione è preservata? la salute è
  verde?).
- **Verdetto**: l'esito complessivo, con la **distinzione** fra divergenza di prodotto e impedimento
  ambientale.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001 (potere retrospettivo):** applicato ai **sette** difetti d'aggiornamento già occorsi, il
  meccanismo ne rileva almeno **cinque**. È il criterio che rende la feature falsificabile: non «esiste
  un test d'aggiornamento» ma «un test che, se fosse esistito, avrebbe fermato questi».
- **SC-002 (il verbo giusto):** esiste almeno una verifica in cui la versione precedente è **realmente
  installata** prima dell'aggiornamento → **0** verifiche che simulano lo stato di partenza.
- **SC-003 (esiti, non forme):** **100%** delle asserzioni riguardano lo stato dell'host dopo
  l'aggiornamento; **0** asserzioni sul contenuto del repository sorgente.
- **SC-004 (non basta l'uscita a zero):** esiste almeno una asserzione che **fallirebbe** su un
  aggiornamento terminato con successo apparente ma senza effetto — il difetto reale già osservato.
- **SC-005 (diagnosticabilità):** un fallimento identifica esito e contesto senza richiedere una
  riesecuzione manuale → **0** report che obbligano a riprodurre per capire.
- **SC-006 (collocazione):** la verifica **non** si aggiunge al percorso di ogni modifica ordinaria, ed
  è **verde prima** di ogni pubblicazione.
- **SC-007 (onestà sul residuo):** la documentazione della verifica **dichiara** quali difetti noti
  restano fuori copertura → il residuo è nominato, non implicito.

## Assumptions

- **La versione precedente è identificabile** da un riferimento pubblico stabile già in uso.
- **La verifica riusa la macchina esistente** dell'installazione end-to-end invece di costruirne una
  seconda: quella funziona, è onesta, e le manca **un verbo**, non rigore.
- **Il costo è reale e va speso dove serve**: due installazioni complete per combinazione, con rete.
  Il perimetro si sceglie perché il meccanismo resti eseguibile, non perché sia esaustivo.
- **Nessuna modifica al comportamento del prodotto**: questa feature **misura**, non cambia
  l'aggiornamento. I difetti che rileverà si chiudono altrove.
- **Il dogfood non può sostituirla**: il suo runtime insegue l'ultimo stato del codice e non passa mai
  da una versione alla successiva, quindi non esercita il verbo nemmeno per caso.

## Clarifications

### Q1 — Da quale versione parte l'aggiornamento?

**Context**: FR-014, ed edge case *«aggiornamento che salta più versioni»*.

| Option | Answer | Implications |
|--------|--------|--------------|
| A | Solo dall'**ultima** release | Caso più frequente, costo minimo (un aggiornamento per combinazione). Ma il difetto del riferimento fisso è emerso su un ospite che ha saltato **tre** versioni: quel percorso resterebbe non provato. |
| B | Anche da **più versioni indietro** | Copre la condizione in cui il difetto reale è stato osservato. Raddoppia (o più) il tempo, e richiede di decidere *quanto* indietro. |
| C | Dall'ultima release **più** un salto lungo, su una **sola** combinazione | Copre entrambi i percorsi pagando il salto lungo una volta sola invece che su tutta la matrice. |
| Custom | La tua regola | — |

**Your choice**: _[in attesa]_

### Q2 — Quanto perimetro?

**Context**: FR-013. L'installazione end-to-end oggi copre quattro combinazioni; l'aggiornamento le
raddoppierebbe come tempo.

| Option | Answer | Implications |
|--------|--------|--------------|
| A | **Tutte** le combinazioni assistente × capacità | Copertura massima, costo massimo; rischio che il costo porti a disattivarlo (R-1). |
| B | Un **sottoinsieme scelto**, dichiarando cosa resta fuori | Eseguibile e onesto (SC-007), ma qualcuno deve mantenere la scelta viva. |
| C | Una combinazione per **assistente**, sulla capacità dove sono nati i difetti | Copre la parità fra assistenti e la superficie che ha prodotto 7 difetti su 7; il resto è dichiarato fuori. |
| Custom | La tua regola | — |

**Your choice**: _[in attesa]_

### Q3 — Quando la release precedente non è determinabile

**Context**: FR-012.

| Option | Answer | Implications |
|--------|--------|--------------|
| A | **Dichiara e passa** | Non blocca il primo rilascio né un ambiente incompleto; il rischio è che la dichiarazione non venga letta e la verifica risulti «verde» senza aver verificato. |
| B | **Fallisce** | Impossibile ignorarlo, ma un impedimento ambientale bloccherebbe un rilascio legittimo — la stessa forma di difetto che questa giornata ha già pagato due volte. |
| Custom | La tua regola | — |

**Your choice**: _[in attesa]_
