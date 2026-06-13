# Feature Specification: Hardening di produzione del livello retrieval (Must)

**Feature Branch**: `018-hardening-retrieval`

**Created**: 2026-06-13

**Status**: Draft

**Input**: User description: i due Must dal RAG Production Audit (2026-06-13) —
(1) affidabilità delle chiamate di embedding (retry con backoff su errori transitori),
(2) segnale di confidenza / soglia di score per abilitare l'abstention del consumer.
Fonte requisiti: `requirements/sertor-core/hardening-produzione/requirements.md` (REQ-H1/H2/H3).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Le chiamate di embedding sopravvivono agli errori transitori (Priority: P1)

Chi indicizza o interroga il corpus si affida a un provider di embedding (locale o cloud). In
produzione il provider risponde a tratti con limiti di frequenza o errori temporanei del server. Oggi
un singolo errore di questo tipo fa abortire l'intera operazione, anche quando un secondo tentativo
sarebbe andato a buon fine. Questa storia rende il sistema **resiliente agli errori transitori**:
ritenta automaticamente, con attese crescenti, e fallisce in modo esplicito solo quando l'errore
persiste davvero.

**Why this priority**: è il Critical dell'audit (F1). Senza resilienza, una qualunque finestra di
rate-limiting del provider trasforma un'indicizzazione lunga (minuti, centinaia di chunk) in un
fallimento totale da ricominciare da capo — il punto di rottura più probabile in esercizio reale.

**Independent Test**: si simula un provider che restituisce prima una condizione ritentabile
(es. rate-limit) e poi successo: l'operazione si completa senza intervento manuale. Si simula un
provider che fallisce sempre con condizione ritentabile: l'operazione solleva un errore di embedding
esplicito dopo il numero massimo di tentativi. Tutto offline, senza rete.

**Acceptance Scenarios**:

1. **Given** un provider che fallisce con condizione ritentabile (rate-limit / errore server / errore
   di rete) al primo tentativo e poi riesce, **When** si richiede un embedding, **Then** l'operazione
   si completa con successo senza alcun intervento manuale.
2. **Given** un provider che fallisce sempre con condizione ritentabile, **When** si esauriscono i
   tentativi massimi configurati, **Then** il sistema solleva un errore di embedding esplicito (lo
   stesso tipo di errore di oggi) e registra il fatto di aver rinunciato.
3. **Given** un provider che fallisce con condizione **non** ritentabile (es. credenziali errate,
   richiesta malformata), **When** si richiede un embedding, **Then** il sistema fallisce
   immediatamente, senza ritentare.
4. **Given** la configurazione che imposta i tentativi massimi a 1, **When** una chiamata fallisce con
   condizione ritentabile, **Then** non avviene alcun ritentativo (comportamento identico a quello
   odierno) — la resilienza è disattivabile.

---

### User Story 2 - L'agente consumer può sapere quando il retrieval è debole (Priority: P2)

Un agente che consuma il retrieval riceve oggi sempre i primi *k* risultati, anche quando la domanda
è fuori dal dominio del corpus e i risultati sono semanticamente irrilevanti. Senza un segnale di
"bassa confidenza", l'agente non ha appiglio per **astenersi** e rischia di rispondere su contesto
spurio. Questa storia introduce una **soglia di confidenza opzionale**: sotto soglia, il retrieval non
restituisce contesto debole e segnala esplicitamente la bassa confidenza, così l'agente può decidere
di astenersi.

**Why this priority**: è l'unico gap che indebolisce il grounding **dentro** il modello agentico
composito (B1 dell'audit). La generazione/astensione-nella-risposta resta dell'agente, ma il
*materiale* per astenersi (il segnale di confidenza) spetta al retrieval e oggi manca. È P2 perché
abilita una qualità (grounding) mentre P1 evita un fallimento (resilienza): senza P1 il sistema si
rompe, senza P2 risponde ma può sbagliare contesto.

**Independent Test**: con una soglia configurata, una query manifestamente fuori-dominio non
restituisce contesto e produce un segnale di bassa confidenza osservabile; una query in-dominio
restituisce normalmente. Con soglia assente, i risultati sono identici a oggi. Tutto offline (store
mock con score controllati).

**Acceptance Scenarios**:

1. **Given** una soglia di confidenza configurata, **When** si interroga con una query i cui migliori
   risultati hanno score sotto soglia, **Then** il retrieval non restituisce quei risultati deboli e
   segnala bassa confidenza in modo che il consumer possa rilevarlo.
2. **Given** una soglia configurata, **When** si interroga con una query i cui risultati superano la
   soglia, **Then** i risultati vengono restituiti normalmente e nessun segnale di bassa confidenza è
   emesso.
3. **Given** nessuna soglia configurata, **When** si interroga, **Then** il comportamento è identico a
   quello odierno (nessun filtro, nessun segnale) — retro-compatibilità totale.
4. **Given** un consumer esistente che ignora il nuovo segnale, **When** interroga il sistema, **Then**
   continua a funzionare senza modifiche (il segnale è additivo al contratto dei risultati).

---

### Edge Cases

- **Tutti i risultati sotto soglia** → lista vuota + segnale di bassa confidenza (non un errore: il
  nucleo resta tollerante, coerente con "indice mancante → [] + warning").
- **Soglia che azzera tutti i risultati su un motore strict (baseline)** → si rispetta la policy
  errori esistente del motore (la soglia è filtro, non assenza d'indice: non muta la policy
  `IndexNotFoundError`).
- **Retry che si sovrappone a un'operazione lunga** (indicizzazione di molti chunk) → il tempo totale
  di attesa deve restare limitato (backoff con tetto), per non trasformare un transitorio in uno stallo.
- **Jitter deterministico nei test** → la randomizzazione del backoff deve essere iniettabile/neutra
  in test, per non rendere i test non deterministici né lenti (nessuna attesa reale).
- **Condizione ambigua del provider** (errore senza codice chiaro) → default prudente: classificare
  come ritentabile solo i casi noti (rate-limit/5xx/rete); il resto fallisce subito.

## Requirements *(mandatory)*

### Functional Requirements

**Resilienza embedding (User Story 1 — REQ-H3):**

- **FR-001**: Il sistema MUST ritentare una richiesta di embedding fallita con condizione ritentabile
  (limite di frequenza, errore del server, errore di rete) prima di propagare il fallimento.
- **FR-002**: I ritentativi MUST usare attese crescenti in modo esponenziale con una componente casuale
  (jitter), fino a un numero massimo di tentativi configurabile.
- **FR-003**: Esauriti i tentativi, il sistema MUST sollevare un errore di embedding esplicito,
  preservando il **tipo di errore** già usato oggi (nessuna rottura per i consumer che lo catturano).
- **FR-004**: Un fallimento con condizione **non** ritentabile MUST fallire immediatamente, senza
  ritentativi.
- **FR-005**: Il comportamento di retry MUST applicarsi in modo uniforme a tutti i provider di
  embedding (locale e cloud).
- **FR-006**: I parametri di retry (numero massimo di tentativi, base del backoff) MUST essere
  configurabili centralmente, con default attivi ma conservativi; impostare i tentativi a 1 MUST
  disattivare i ritentativi (comportamento odierno).
- **FR-007**: Il sistema MUST registrare ogni ritentativo (numero del tentativo e motivo) e la
  rinuncia finale, **senza** esporre segreti nei log.

**Segnale di confidenza (User Story 2 — REQ-H1/H2):**

- **FR-010**: Dove è configurata una soglia di score, il retrieval MUST escludere i risultati con score
  sotto la soglia, invece di restituire sempre i primi *k*.
- **FR-011**: Quando il miglior risultato disponibile è sotto soglia (o nessun risultato la supera), il
  sistema MUST segnalare bassa confidenza in modo che il consumer possa rilevarlo e decidere di
  astenersi.
- **FR-012**: La condizione di bassa confidenza MUST essere registrata nei log.
- **FR-013**: Quando **nessuna** soglia è configurata, il comportamento del retrieval MUST essere
  identico a quello odierno (nessun filtro, nessun segnale) — retro-compatibile.
- **FR-014**: Il segnale di confidenza MUST essere **additivo** al contratto dei risultati esistente:
  i consumer che lo ignorano continuano a funzionare invariati.
- **FR-015**: Soglia e segnale MUST applicarsi in modo coerente a tutti i punti d'ingresso del
  retrieval (la facade e i motori baseline e ibrido), rispettando la **policy errori esistente** di
  ciascuno (nucleo tollerante vs baseline strict). La soglia è un filtro sui risultati, NON cambia la
  semantica di "indice mancante".

### Key Entities *(include if feature involves data)*

- **Politica di retry dell'embedding**: parametri che governano i ritentativi (numero massimo di
  tentativi, base del backoff, presenza di jitter) e la classificazione "ritentabile / non
  ritentabile" di un fallimento. Vive nella configurazione centrale.
- **Soglia/segnale di confidenza del retrieval**: il valore di soglia (opzionale) e l'informazione di
  "bassa confidenza" associata a un esito di retrieval. La soglia vive in configurazione; il segnale è
  un'aggiunta all'esito restituito al consumer.
- **Esito di retrieval (esistente)**: l'insieme di risultati con i rispettivi score restituito al
  consumer; viene esteso in modo additivo con il segnale di confidenza, senza rotture.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Una richiesta di embedding che incontra un errore transitorio seguito da successo si
  completa **senza intervento manuale** (verificato simulando rate-limit→successo).
- **SC-002**: Una sequenza di errori transitori persistenti produce un errore esplicito entro un tempo
  totale di attesa **limitato e prevedibile** (backoff con tetto), non uno stallo indefinito.
- **SC-003**: Con una soglia configurata, una query fuori-dominio **non restituisce contesto spurio** e
  produce un segnale di bassa confidenza **osservabile**; una query in-dominio restituisce i risultati.
- **SC-004**: Con nessuna soglia configurata, gli esiti del retrieval sono **identici** a quelli
  precedenti alla feature (test di regressione: nessun cambiamento di comportamento di default).
- **SC-005**: L'intera feature è coperta da test **offline al 100%** (nessuna rete, nessuna attesa
  reale): provider mock che simula gli errori e store/embedder mock con score controllati.
- **SC-006**: Nessun consumer esistente del retrieval richiede modifiche per continuare a funzionare
  (il segnale di confidenza è additivo; la suite esistente resta verde).

## Assumptions

- I provider di embedding espongono informazioni sufficienti (codice di stato / tipo di errore) per
  classificare un fallimento come ritentabile o meno; per i casi ambigui si adotta un default prudente
  (ritentabile solo i casi noti: rate-limit, 5xx, errori di rete).
- Il default conservativo dei tentativi è un numero piccolo (ordine di pochi tentativi), tale da
  assorbire i transitori comuni senza allungare sensibilmente le operazioni normali; il valore esatto
  è dettaglio di pianificazione.
- La soglia di confidenza è **disattivata di default** (nessuna soglia): il sistema non cambia
  comportamento finché un consumer non la configura esplicitamente.
- L'**atto** di astenersi resta del consumer (l'agente): questa feature fornisce il *materiale* per
  astenersi (il segnale), non genera risposte né decide l'astensione.
- Si riusano le porte e i punti di configurazione esistenti (`Settings`, le porte di
  embedding/retrieval): la feature non introduce nuovi confini architetturali.
- La rotazione della API key Azure esposta in chat è un'azione **operativa fuori-codice** e **non** fa
  parte di questa feature.
- Fuori ambito (prossimi incrementi): cache embeddings + token nei log (Should REQ-H4/H5), query
  transformation, filtro metadata, tracing/metriche, contextual retrieval (Could REQ-H7..H11).
