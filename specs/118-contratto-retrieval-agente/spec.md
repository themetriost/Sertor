# Feature Specification: Contratto di retrieval verso l'agente

**Feature Branch**: `118-contratto-retrieval-agente`

**Created**: 2026-07-24

**Status**: Draft

**Input**: E5-FEAT-012 — portare il segnale strutturale del code-graph dentro la ricerca combinata come
terzo flusso etichettato (dietro interruttore, spento di default), e prima costruire l'harness di
valutazione agent-facing che ne è il gate. Requisiti: `requirements/retrieval-qualita/contratto-retrieval-agente/requirements.md`.
Design note: `wiki/concepts/llm-facing-retrieval-contract.md`.

## Clarifications

### Session 2026-07-24

Risolte **senza interazione**, su autorizzazione esplicita a procedere fino all'implementazione
fermandosi solo su dubbi genuini. Ogni decisione è motivata; nessuna è un default silenzioso.

- Q: Quale calo sulle domande non strutturali fa fallire la metà «non-regressione» del gate?
  → A: **Due gate separati.** La consegna in forma **opt-in** richiede che il calo non superi
  **5 punti percentuali**; l'**attivazione di default** per tutti richiede **nessun calo misurabile**.
  *Motivo:* «la capacità è utile» e «è abbastanza sicura da accenderla per tutti» sono due domande
  diverse, e un'unica soglia costringe a sbagliarne una. Con una soglia sola: severa → la capacità non
  si consegna mai; permissiva → si accende per tutti sulla base del rumore.
- Q: Quanti punti d'ingresso al massimo per una singola domanda?
  → A: **3.** *Motivo:* sopra i tre il materiale strutturale comincia a competere con i flussi di
  somiglianza per lo spazio di contesto (il costo di §4 dei requisiti), e le domande reali che
  riguardano più di tre simboli distinti sono rare. Il numero è una manopola, non una costante murata.
- Q: Quando un simbolo è candidato per il confronto lessicale con la domanda?
  → A: Quando la domanda **ne nomina per intero** il nome, **oppure** ne condivide **almeno due parti
  distinte**. *Motivo:* una sola parte in comune aggancia troppo (una domanda che contiene «index»
  pescherebbe ogni simbolo con «index» nel nome, pagando il costo dove il beneficio è nullo); tre
  ricadono di fatto sul nome intero. Due è il primo valore che discrimina, ed è comunque da tarare
  sulla misura.
- Q: Quante ripetizioni per caso nell'harness?
  → A: **3.** *Motivo:* è il minimo che permette di distinguere una differenza sistematica dal rumore
  di una singola esecuzione (edge case dichiarato: varianza maggiore dell'effetto). Sotto le 3 non si
  distingue; sopra, il costo cresce senza che la conclusione cambi per un gate a soglia.
- Q: Cosa conta come «la risposta cita le fonti attese» quando le fonti attese sono più di una?
  → A: **Almeno una** (unione, non congiunzione). *Motivo:* la congiunzione misurerebbe la
  *coincidenza* di segnali indipendenti anziché la loro combinazione — è l'errore già commesso e
  corretto in questo progetto, dove una metrica in AND diede 0.17 su un sistema che in OR risultava
  pienamente coperto. La quota per-fonte resta disponibile come dettaglio diagnostico.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sapere se una forma di risultato aiuta davvero l'agente (Priority: P1)

Chi cura la qualità del sistema vuole decidere **su evidenza** come presentare i risultati di ricerca
all'agente. Oggi non può: gli strumenti di misura esistenti dicono *cosa viene recuperato* (le fonti
giuste sono nell'elenco?), non *come l'agente usa* quell'elenco una volta ricevuto. Due modi diversi
di presentare lo stesso identico materiale possono produrre risposte di qualità diversa, e nessuno se
ne accorge.

Questa storia dà la capacità di porre la domanda: *«a parità di materiale, questa forma fa rispondere
meglio di quest'altra?»* — e di rispondere con un numero anziché con un'opinione.

**Why this priority**: è il prerequisito di ogni decisione delle altre storie, e ha valore **da sola**:
è la prima misura del progetto orientata al comportamento dell'agente, riusabile per qualunque futura
scelta di contratto. Senza, le storie successive si consegnerebbero sulla fiducia.

**Independent Test**: si sceglie una differenza qualunque fra due forme di risultato, si esegue la
misura su un insieme di domande con fonti attese note, e si ottiene un confronto ripetibile fra le due
condizioni. Vale anche se nessuna delle altre storie viene realizzata.

**Acceptance Scenarios**:

1. **Given** un insieme di domande con le fonti attese note, **When** si esegue la misura su due
   varianti che differiscono per un solo aspetto, **Then** si ottiene, per ciascuna variante, quante
   risposte citano le fonti attese e quante citano fonti assenti dal materiale fornito.
2. **Given** una misura già eseguita, **When** la si riesegue senza modifiche, **Then** la variazione
   fra le esecuzioni è visibile e distinguibile dall'effetto misurato.
3. **Given** una misura da eseguire, **When** la regola di decisione non è stata registrata prima
   dell'esecuzione, **Then** il risultato è marcato come non utilizzabile per decidere.
4. **Given** una misura eseguita, **When** se ne riesamina l'esito in un secondo momento, **Then**
   materiale fornito, risposte ricevute e verdetti sono ancora consultabili.

---

### User Story 2 - Il contratto dice la verità su cosa consegna (Priority: P2)

L'agente riceve, insieme ai risultati, un **punteggio**. Quel numero non è confrontabile fra flussi
diversi né fra ricerche diverse, e il suo significato **cambia a seconda di come il sistema è
configurato**: in una configurazione è una misura di somiglianza, in un'altra è un valore derivato
dall'ordine, che oltre all'ordine aggiunge poco. Nulla di tutto questo è dichiarato: l'agente riceve
un numero e ne trae le conclusioni che il numero sembra autorizzare.

C'è una seconda asimmetria taciuta: il valore su cui il sistema decide di **astenersi** quando i
risultati sono deboli e il valore eventualmente **mostrato** all'agente sono due grandezze diverse,
calcolate in momenti diversi.

Questa storia rende esplicito ciò che il sistema già fa, e protegge con verifiche automatiche due
comportamenti oggi corretti ma non presidiati, che una modifica futura potrebbe rompere in silenzio.

**Why this priority**: costo basso e valore immediato, indipendente dal resto. Ma non precede la
prima storia, perché la decisione su *quale* punteggio meriti di essere consegnato dipende da una
misura che la prima storia rende possibile.

**Independent Test**: si legge la descrizione degli strumenti di ricerca in due configurazioni diverse
del sistema e si verifica che dichiari, in ciascuna, l'ambito di validità del punteggio effettivamente
prodotto in quella configurazione. In parallelo, si altera deliberatamente il valore segnaposto interno
usato dalla valutazione e si verifica che nessuna misura cambi.

**Acceptance Scenarios**:

1. **Given** una configurazione che produce punteggi di somiglianza, **When** l'agente legge la
   descrizione dello strumento, **Then** vi trova che il punteggio è confrontabile solo entro il
   proprio elenco, mai fra elenchi, mai fra ricerche, mai come misura assoluta.
2. **Given** una configurazione che produce punteggi derivati dall'ordine, **When** l'agente legge la
   descrizione, **Then** vi trova dichiarato che il punteggio aggiunge poco rispetto all'ordine stesso.
3. **Given** che il valore su cui si decide l'astensione e quello mostrato sono grandezze diverse,
   **When** l'agente legge la descrizione, **Then** l'asimmetria è dichiarata.
4. **Given** la valutazione delle domande strutturali, **When** si modifica il valore segnaposto che
   accompagna quei risultati, **Then** l'esito della valutazione resta identico in ogni sua parte.
5. **Given** una domanda strutturale, **When** viene valutata, **Then** viene interrogata solo la
   navigazione strutturale; **e** data una domanda non strutturale, viene interrogata solo la ricerca
   per somiglianza.

---

### User Story 3 - Il segnale strutturale arriva senza che l'agente lo chieda (Priority: P3)

Il sistema costruisce a ogni indicizzazione una mappa strutturale del codice — dove ogni cosa è
definita, chi la chiama, quali documenti la menzionano — e la tiene pronta a ogni avvio. Ma la
raggiunge **solo** l'agente che decide di chiederla esplicitamente. Sulle domande strutturali la
ricerca per somiglianza è debole mentre la mappa è esatta: quindi la qualità della risposta dipende da
una scelta dell'agente che nessuno misura.

Questa storia porta quel segnale dentro la ricerca combinata come **terzo flusso etichettato**, così
che arrivi anche a chi non sapeva di doverlo chiedere — **e solo se** la misura dimostra che aiuta
senza danneggiare le altre domande.

**Why this priority**: è la capacità di maggior valore, ma dipende dalle due precedenti — dalla prima
per il gate, dalla seconda per la forma onesta del contratto. Consegnarla per prima significherebbe
non poter dire se serve.

**Independent Test**: attivato l'interruttore, una ricerca su una domanda strutturale restituisce, oltre
ai due flussi odierni, un terzo flusso con definizioni e relazioni raggruppate per simbolo. Disattivato
l'interruttore, la risposta è identica a quella odierna.

**Acceptance Scenarios**:

1. **Given** l'interruttore attivo e una domanda che nomina o implica un simbolo, **When** si esegue
   una ricerca combinata, **Then** la risposta contiene un terzo flusso con i risultati strutturali
   raggruppati per simbolo e per tipo di relazione.
2. **Given** l'interruttore spento, **When** si esegue una ricerca combinata, **Then** la risposta è
   identica a quella prodotta prima di questa feature.
3. **Given** una domanda dalla quale non si ricava alcun punto d'ingresso, **When** si esegue la
   ricerca, **Then** il flusso strutturale dichiara di non aver tentato, e non aggiunge materiale.
4. **Given** una risposta con flusso strutturale, **When** l'agente la esamina, **Then** per ciascun
   punto d'ingresso può vedere **come** quel punto è stato ricavato.
5. **Given** la mappa strutturale non consultabile, **When** si esegue la ricerca, **Then** il flusso
   dichiara di non aver potuto tentare e **perché**, e non presenta un risultato vuoto.
6. **Given** un simbolo con più relazioni di quante ne siano mostrate, **When** l'agente le esamina,
   **Then** vede quante ne sono mostrate e quante ne esistono.
7. **Given** una posizione presente sia nella ricerca per somiglianza sia nel flusso strutturale,
   **When** l'agente esamina la risposta, **Then** ciascuno dei due flussi rimanda all'altro.
8. **Given** la misura del gate eseguita, **When** sulle domande non strutturali il calo resta entro
   5 punti percentuali ma è misurabile, **Then** la capacità viene consegnata **spenta**, attivabile
   su richiesta; **When** il calo supera i 5 punti, **Then** la capacità non viene consegnata;
   **When** non c'è calo misurabile e il beneficio sulle strutturali è confermato, **Then**
   l'interruttore può essere attivo di default.

---

### Edge Cases

- **Nessun punto d'ingresso ricavabile** dalla domanda (per esempio: domanda posta in una lingua
  diversa da quella degli identificatori, senza sovrapposizione di vocabolario) → il flusso dichiara
  «non tentato», che è onesto e non costa nulla.
- **Mappa mai costruita** vs **capacità di navigazione non disponibile** vs **mappa illeggibile**: tre
  cause diverse, che l'agente deve poter distinguere perché portano a conclusioni diverse.
- **Fallimento parziale**: un simbolo risolto e un altro no; oppure le relazioni di chiamata calcolate
  ma i documenti collegati no. È il caso **normale**, non l'eccezione.
- **Simbolo molto chiamato**: decine di risultati, di cui se ne mostrano pochi. Senza dichiarare il
  taglio, l'agente afferma che i chiamanti sono solo quelli mostrati.
- **Stessa posizione in due flussi**: non è un errore da nascondere, è convergenza di due metodi
  indipendenti.
- **Misura che non discrimina**: le due varianti danno lo stesso risultato. È un esito legittimo, e
  significa che l'aspetto misurato non conta.
- **Varianza fra esecuzioni** maggiore dell'effetto misurato: la misura non è conclusiva e va detto.
- **Domanda non strutturale con interruttore attivo**: riceve materiale che non le serve. È
  esattamente ciò che la metà «non-regressione» del gate deve rilevare.

## Requirements *(mandatory)*

### Functional Requirements

**Misura del comportamento dell'agente (US1)**

- **FR-001**: Il sistema MUST permettere di misurare l'effetto di una variante di presentazione sulla
  risposta dell'agente a una domanda.
- **FR-002**: La misura MUST fornire all'agente il materiale nella stessa forma in cui lo riceve
  nell'uso normale.
- **FR-003**: La misura MUST registrare, per ogni domanda e ogni variante, se la risposta cita le
  fonti attese e se cita fonti assenti dal materiale fornito.
- **FR-003a**: Quando le fonti attese di una domanda sono più di una, la risposta MUST contare come
  «cita le fonti attese» se ne cita **almeno una**; la copertura per-fonte MUST restare disponibile
  come dettaglio diagnostico.
- **FR-004**: Le due varianti a confronto MUST essere identiche in tutto tranne l'aspetto in esame.
- **FR-005**: La regola di decisione MUST essere registrata prima dell'esecuzione della misura.
- **FR-006**: Se la regola di decisione non è stata registrata prima, il risultato MUST NOT essere
  usato per decidere.
- **FR-007**: La misura MUST registrare per ogni caso la dimensione del materiale fornito e il tempo
  impiegato, così che beneficio e costo siano misurati insieme.
- **FR-008**: La misura MUST ripetere ogni caso **3 volte**, così che la variazione fra esecuzioni sia
  distinguibile dall'effetto in esame; se la variazione fra le ripetizioni supera l'effetto misurato,
  la misura MUST essere dichiarata **non conclusiva** anziché riportata come risultato.
- **FR-009**: Materiale, risposte e verdetti MUST restare consultabili dopo l'esecuzione.

**Onestà del contratto attuale (US2)**

- **FR-010**: La descrizione di ogni strumento di ricerca MUST dichiarare l'ambito di validità del
  punteggio che espone: solo entro il proprio elenco, mai fra elenchi, mai fra ricerche, mai come
  misura assoluta di qualità.
- **FR-011**: La descrizione MUST riflettere la configurazione effettivamente attiva, non un testo
  fisso.
- **FR-012**: Quando la configurazione produce punteggi derivati dall'ordine, la descrizione MUST
  dichiarare che il punteggio aggiunge poco rispetto all'ordine.
- **FR-013**: La descrizione MUST dichiarare che il valore su cui si decide l'astensione e il valore
  eventualmente mostrato sono grandezze diverse.
- **FR-014**: La valutazione di una domanda strutturale MUST interrogare solo la navigazione
  strutturale; quella di una domanda non strutturale, solo la ricerca per somiglianza.
- **FR-015**: L'esito della valutazione MUST NOT dipendere dal valore segnaposto associato ai
  risultati strutturali.
- **FR-016**: Le due proprietà precedenti MUST essere protette da verifiche che falliscono se
  vengono violate.

**Il flusso strutturale (US3)**

- **FR-017**: Quando l'interruttore è attivo, la ricerca combinata MUST restituire un terzo flusso
  etichettato con il risultato strutturale, accanto ai due esistenti.
- **FR-018**: Quando l'interruttore è spento, la ricerca combinata MUST restituire esattamente ciò che
  restituisce oggi.
- **FR-019**: L'interruttore MUST essere spento di default finché il gate non è superato.
- **FR-020**: Il flusso strutturale MUST raggruppare i risultati per simbolo e, dentro ciascun
  simbolo, per tipo di relazione.
- **FR-021**: Il flusso MUST dichiarare, per ogni punto d'ingresso, come è stato ricavato.
- **FR-022**: I punti d'ingresso MUST essere ricavati dalla domanda con mezzi deterministici, senza
  interpellare un modello linguistico.
- **FR-023**: Il sistema MUST limitare a **3** il numero di punti d'ingresso risolti per una singola
  domanda, con il limite configurabile.
- **FR-023a**: Un simbolo MUST essere candidato come punto d'ingresso quando la domanda ne nomina per
  intero il nome, **oppure** ne condivide almeno **2 parti distinte**; la soglia MUST essere
  configurabile.
- **FR-024**: Se nessun punto d'ingresso è ricavabile, il flusso MUST dichiarare di non aver tentato e
  MUST NOT aggiungere altro materiale.

**Assenza tipizzata e troncamento (US3)**

- **FR-025**: Il flusso MUST distinguere tre esiti: non tentato, tentato e vuoto, non tentabile.
- **FR-026**: Il sistema MUST distinguere almeno tre cause di «non tentabile»: mappa mai costruita,
  capacità di navigazione non disponibile, mappa illeggibile.
- **FR-027**: Se la mappa non è consultabile per qualunque ragione, il flusso MUST NOT presentare un
  risultato vuoto, perché un risultato vuoto afferma un'assenza.
- **FR-028**: L'esito complessivo del flusso MUST derivare dagli esiti per relazione e MUST NOT essere
  impostabile indipendentemente da essi.
- **FR-029**: Il flusso MUST dichiarare «non tentato» se e solo se non ha usato alcun punto d'ingresso.
- **FR-030**: Quando un insieme di relazioni è troncato, il flusso MUST dichiarare quante ne sono
  mostrate e quante ne esistono.
- **FR-031**: I flussi per somiglianza MUST NOT dichiarare un totale, perché il loro taglio è
  costitutivo e non afferma esaustività.

**Corroborazione (US3)**

- **FR-032**: Quando la stessa posizione è presente sia in un flusso per somiglianza sia nel flusso
  strutturale, ciascuno MUST portare un riferimento all'altro.
- **FR-033**: Il sistema MUST NOT rimuovere un risultato da un flusso perché compare in un altro.

**Il gate di consegna (US3)**

- **FR-034**: Il flusso strutturale MUST essere misurato sia per il beneficio sulle domande
  strutturali sia per la non-regressione sulle domande non strutturali.
- **FR-035**: Se sulle domande non strutturali si misura un calo qualsiasi, l'interruttore MUST NOT
  essere attivo di default, anche quando il calo resta entro la soglia di consegna.
- **FR-036**: Se la metà beneficio fallisce, la capacità MUST NOT essere consegnata.
- **FR-037**: Il gate di non-regressione MUST avere **due soglie distinte**: la consegna della
  capacità in forma **attivabile su richiesta** richiede che il calo della quota di risposte che
  citano le fonti attese sulle domande non strutturali **non superi 5 punti percentuali**;
  l'**attivazione di default** richiede **nessun calo misurabile**.
- **FR-038**: Se il calo supera 5 punti percentuali, la capacità MUST NOT essere consegnata; se resta
  entro i 5 punti ma è misurabile, la capacità MUST essere consegnata **spenta**, attivabile solo da
  chi la richiede esplicitamente.

### Key Entities

- **Punto d'ingresso**: un simbolo dal quale interrogare la mappa strutturale, accompagnato
  dall'indicazione di **come** è stato ricavato dalla domanda. La provenienza è ciò che permette
  all'agente di dare più o meno fiducia a quel ramo di risultati.
- **Blocco di relazione**: l'insieme dei risultati di un certo tipo di relazione per un certo simbolo,
  con il proprio esito (riuscito, vuoto, non ottenibile e perché) e la propria dichiarazione di
  troncamento.
- **Contesto del simbolo**: i blocchi di relazione che riguardano lo stesso simbolo, tenuti insieme.
- **Flusso strutturale**: i punti d'ingresso usati, i contesti dei simboli risolti, e un esito
  complessivo **derivato** da quelli sottostanti.
- **Caso di misura**: una domanda, le sue fonti attese, e le varianti di presentazione da confrontare.
- **Esito di misura**: per un caso e una variante, se le fonti attese sono citate, se sono citate
  fonti inesistenti, quanto materiale è stato fornito e quanto tempo è servito.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Si può rispondere con un numero, e non con un'opinione, alla domanda «questa forma di
  risultato fa rispondere meglio dell'altra?» su almeno 20 domande diverse.
- **SC-002**: Ogni misura eseguita ha la propria regola di decisione registrata **prima**
  dell'esecuzione: 100% delle misure.
- **SC-003**: La decisione su quale punteggio consegnare è presa sulla base di una misura, ed è
  differenziata per configurazione: 2 configurazioni decise.
- **SC-004**: Sulle domande strutturali, la quota di risposte che citano le fonti attese è **superiore**
  con il flusso strutturale rispetto a senza.
- **SC-005**: Sulle domande non strutturali, quando il flusso strutturale arriva non richiesto, la
  stessa quota non cala **oltre 5 punti percentuali** (condizione per consegnare la capacità) e non
  cala **affatto** (condizione, più stringente, per attivarla di default).
- **SC-006**: Le tre cause di indisponibilità della mappa sono distinguibili nel risultato: 3 su 3.
- **SC-007**: A interruttore spento, la risposta è indistinguibile da quella prodotta prima della
  feature: verificato su tutti i casi della suite esistente.
- **SC-008**: L'aumento di materiale consegnato su una domanda che non richiedeva il flusso
  strutturale è misurato e riportato, non stimato.
- **SC-009**: Due comportamenti oggi corretti ma non protetti (instradamento esclusivo, indipendenza
  dal valore segnaposto) hanno verifiche che falliscono se vengono violati: 2 su 2.
- **SC-010**: Una decisione di contratto presa oggi può essere riesaminata a distanza di tempo
  risalendo a materiale, risposte e verdetti che l'hanno prodotta.

## Assumptions

- **L'agente usato per misurare è sufficientemente stabile** perché due varianti confrontate nella
  stessa sessione di misura siano confrontabili. Le misure sono deliberatamente **relative** (variante
  A contro variante B), mai assolute, proprio per contenere questa variabilità.
- **Il giudizio sulla qualità della risposta è deterministico**, non affidato a un secondo agente: si
  misura se la risposta cita le fonti attese e se cita fonti assenti dal materiale. Le fonti attese
  esistono già nella suite di valutazione, quindi il criterio non costa nulla. Un giudizio più fine si
  aggiungerà **solo** se il criterio deterministico non discrimina.
- **La via d'ingresso che ricava simboli dai risultati della ricerca per somiglianza è rinviata**: la
  sua copertura sarebbe parziale, perché una parte dei risultati non trasporta il nome del simbolo.
  Restano le due vie deterministiche: identificatori riconosciuti nella domanda, e confronto lessicale
  con l'elenco dei simboli noti. Ampliare l'ambito per sanare quella copertura merita un requisito
  proprio, non un'aggiunta di straforo.
- **La mappa strutturale è già costruita e caricata**, quindi interrogarla costa un accesso e non un
  ricalcolo. È un'assunzione **da verificare nella misura** (SC-008), non da dare per buona.
- **La suite di valutazione esistente fornisce domande e fonti attese**, e la loro classificazione per
  tipo è la base della partizione fra beneficio e non-regressione.
- **La macchina di misura non è codice di prodotto**: richiede un agente, non è riproducibile a costo
  zero, e non gira nella verifica ordinaria.
- **Nessun modello linguistico entra nel percorso di ricerca**: l'agente è oggetto della misura, mai
  componente del retrieval.
- **La capacità è additiva**: a interruttore spento nulla cambia, e l'interruttore nasce spento.
