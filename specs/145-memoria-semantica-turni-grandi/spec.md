# Feature Specification: Memoria semantica che regge i turni grandi e i rifiuti del provider

**Feature Branch**: `145-memoria-semantica-turni-grandi`

**Created**: 2026-10-20

**Status**: Draft

**Deriva da**: E4-FEAT-016 (epica `memoria-conversazioni`, BUG) · **Requisiti**: REQ-033..036 in
[`requirements/memoria-conversazioni/ricerca-semantica/requirements.md`](../../requirements/memoria-conversazioni/ricerca-semantica/requirements.md) §5.2.2
· **Feature d'origine**: [`specs/072-ricerca-semantica-memoria/`](../072-ricerca-semantica-memoria/)

**Input**: segnalazione del nodo **Kaelen** (bacheca Acta, canale *Feedback Sertor*, 2026-10-20, Sertor
0.6.0, embedding `openai:text-embedding-3-large`): `memory index-semantic` su 11 sessioni chiude con
`embedded=1540 skipped=0 errors=181` e `reason=provider_unavailable detail=http 400`; rilanciato, l'errore
si ripete identico. I 181 errori sono **tutti** i turni di una sola sessione, nella quale un turno è lungo
circa 290.000 caratteri (il testo di una skill caricata in conversazione) — circa dieci volte il limite
d'ingresso del modello.

---

## Perché questa feature esiste

La memoria semantica serve a ritrovare una conversazione passata **per significato**. Oggi una sola
cosa di routine — caricare una skill grande, riprendere una sessione dopo una compattazione — basta a
renderne invisibile **l'intera sessione** alla ricerca per significato, e a farlo in un modo che il nodo
non può diagnosticare: l'esito dice «servizio non disponibile» quando il servizio era raggiungibile e ha
rifiutato un testo preciso, e non dice quale. Kaelen ha dovuto contare i turni a mano per capirlo.

Sono tre difetti distinti nello stesso punto dell'indicizzazione:

1. **Il turno va al servizio intero.** Il corpus applica già un tetto in token ai propri pezzi; la
   memoria no.
2. **Un rifiuto fa perdere i vicini.** Il turno rifiutato è uno, ma vanno persi tutti i turni nuovi della
   sessione, anche quelli brevi e validi.
3. **L'esito chiama l'errore col nome sbagliato** e non nomina sessione né turno.

Per la missione, è una questione di **qualità del retrieval resa all'agente**: una sessione che manca
dall'indice è una risposta «non ne abbiamo mai parlato» falsa, e l'agente non ha modo di accorgersene.

## Clarifications

### Session 2026-10-20

- Q: Un turno oltre il limite si spezza o si tronca? → A: Si **spezza** in pezzi che rientrano nel
  limite, tutti indicizzati — come i pezzi del corpus, con lo stesso tetto configurabile. Troncare
  perderebbe proprio il contenuto che si vuole ritrovare (Kaelen indica lo spezzare come esito atteso).
- Q: Un turno spezzato in N pezzi compare N volte nei risultati? → A: No: **un risultato per turno**,
  quello del pezzo più pertinente. L'unità di citazione resta il turno (REQ-010 invariato).
- Q: La sessione e il turno rifiutati compaiono negli eventi di osservabilità? → A: No. Gli eventi
  restano metrics-only (conteggi e motivi, REQ-026); sessione e turno compaiono nel **resoconto per
  l'utente** del comando, che è dove chi indaga li cerca.
- Q: Se un pezzo di un turno spezzato viene rifiutato, cosa si indicizza di quel turno? → A: Niente: il
  turno è indicizzato **tutto o niente**, così al run successivo viene ritentato per intero e non resta
  mai a metà in modo silenzioso.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Un turno grande non fa più sparire la sessione (Priority: P1)

Un nodo con la memoria semantica accesa archivia una sessione in cui un turno supera di molto il limite
d'ingresso del modello (una skill caricata, un file incollato). Lancia l'indicizzazione semantica: la
sessione entra nell'indice per intero, turno grande compreso, e una ricerca per significato su un
concetto presente **solo** nel turno grande la ritrova.

**Why this priority**: è il danno segnalato — una sessione intera persa per un turno. Da solo restituisce
al nodo le sessioni oggi escluse.

**Independent Test**: archiviare una sessione con un turno oltre il limite e alcuni turni brevi,
indicizzare con un provider che rifiuta i testi oltre il limite, verificare che tutti i turni siano
indicizzati e che la ricerca ritrovi il turno grande una sola volta.

**Acceptance Scenarios**:

1. **Given** una sessione di 181 turni con un turno oltre il limite, **When** si lancia l'indicizzazione
   semantica, **Then** l'esito riporta 181 turni indicizzati e 0 errori.
2. **Given** il turno grande indicizzato in più pezzi, **When** si cerca un concetto presente solo nella
   sua parte finale, **Then** il turno compare fra i risultati **una sola volta**, citato con la sua
   sessione e il suo indice di turno.
3. **Given** una sessione con soli turni entro il limite, **When** si indicizza, **Then** il
   comportamento è identico a oggi (stesso numero di unità, stesse identità).

---

### User Story 2 - Un rifiuto colpisce solo il turno rifiutato (Priority: P1)

Il provider rifiuta un testo per una ragione diversa dalla lunghezza (contenuto non accettato, limite di
un modello più piccolo di quanto configurato). I turni validi della stessa sessione vengono indicizzati
lo stesso; perde l'indicizzazione solo il turno rifiutato.

**Why this priority**: il tetto in token risolve il caso segnalato, ma il difetto strutturale è che un
rifiuto contamina i vicini. Senza questa storia, ogni rifiuto futuro di qualunque natura ripete il danno.

**Independent Test**: provider finto che rifiuta un solo turno preciso; verificare che gli altri turni
della sessione risultino indicizzati e che l'errore conti uno.

**Acceptance Scenarios**:

1. **Given** una sessione di 10 turni in cui il provider rifiuta il turno 4, **When** si indicizza,
   **Then** l'esito riporta 9 turni indicizzati e 1 errore.
2. **Given** lo stesso stato e un nuovo run, **When** si reindicizza, **Then** i 9 turni già indicizzati
   non vengono rimandati al provider e il turno 4 viene ritentato.
3. **Given** il provider **irraggiungibile** (non un rifiuto), **When** si indicizza, **Then** l'esito
   resta quello di oggi: i turni nuovi contano come errori, senza un tentativo turno per turno.

---

### User Story 3 - L'esito dice cosa è successo e dove (Priority: P2)

Chi lancia `memory index-semantic` legge nell'esito se un turno è stato **rifiutato** dal provider (e
quale: sessione e indice di turno) oppure se il provider o lo store **non erano disponibili**. Non deve
più contare i turni a mano.

**Why this priority**: non cambia cosa entra nell'indice, ma è ciò che rende diagnosticabile il caso
residuo. Dopo le storie 1 e 2 i rifiuti saranno rari; quando capitano, devono essere leggibili.

**Independent Test**: provider finto che rifiuta un turno; leggere l'esito del comando in forma umana e
JSON e trovarvi sessione, turno e motivo.

**Acceptance Scenarios**:

1. **Given** un turno rifiutato, **When** si legge l'esito umano del comando, **Then** compare una riga
   che nomina la sessione, l'indice del turno e il motivo del rifiuto.
2. **Given** lo stesso caso, **When** si chiede l'esito in JSON, **Then** contiene i conteggi di oggi
   **più** l'elenco dei turni rifiutati con sessione, turno e motivo.
3. **Given** un rifiuto, **When** si leggono gli eventi di osservabilità, **Then** il motivo è
   `input_rejected` (non `provider_unavailable`) e nessun evento contiene testo del transcript né
   identificativi di sessione.
4. **Given** il provider irraggiungibile, **When** si leggono esito ed eventi, **Then** il motivo resta
   `provider_unavailable`.

---

### Edge Cases

- **Turno vuoto o di soli spazi**: resta trattato come oggi (nessuna regressione); non produce pezzi
  aggiuntivi.
- **Sessione indicizzata prima di questa feature**: i turni già presenti hanno l'identità di sempre e non
  vengono rimandati al provider; nessun rebuild.
- **Turno perso in passato per il difetto**: al primo run dopo l'aggiornamento risulta nuovo, viene
  spezzato e indicizzato.
- **Nessun tokenizzatore preciso installato**: la stima di ripiego è prudente (sovrastima i token), quindi
  può produrre più pezzi del necessario ma mai un pezzo oltre il limite.
- **Turno spezzato in moltissimi pezzi**: ogni pezzo rientra nel limite da solo; se il provider rifiuta
  l'invio in blocco, il ripiego turno per turno manda i pezzi singolarmente.
- **Filtro temporale in ricerca**: si applica ancora alla data della sessione; la deduplicazione per turno
  non cambia quali sessioni passano il filtro.
- **Indicizzazione automatica a fine sessione**: beneficia della stessa correzione (stesso percorso), e
  resta non-fatale per l'archiviazione (REQ-008).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** *(REQ-033)*: Il sistema DEVE spezzare un turno il cui testo supera il budget d'ingresso
  configurato (lo stesso tetto già applicato ai pezzi del corpus) in pezzi che rientrano ciascuno nel
  budget, e indicizzarli tutti.
- **FR-002** *(REQ-033)*: Un turno che rientra nel budget DEVE conservare l'identità che ha oggi
  nell'indice, così che le sessioni già indicizzate non cambino.
- **FR-003** *(REQ-033)*: La ricerca semantica DEVE restituire al più **un** risultato per turno; se più
  pezzi dello stesso turno sono pertinenti, vale il più pertinente, e il risultato cita sessione e
  indice di turno come oggi.
- **FR-004** *(REQ-034)*: Quando il provider rifiuta l'invio con un errore di **rifiuto del testo**
  (richiesta non valida, testo troppo grande, contenuto non elaborabile), il sistema
  DEVE isolare i turni effettivamente rifiutati ritentandoli separatamente, indicizzare tutti gli altri
  turni della sessione nello stesso run e contare come errori **solo** i turni rifiutati.
- **FR-005** *(REQ-034)*: Un turno è indicizzato **tutto o niente**: se anche un solo pezzo viene
  rifiutato, nessun pezzo di quel turno entra nell'indice.
- **FR-006** *(REQ-034)*: Quando il provider è **irraggiungibile**, l'errore è ritentabile o riguarda la
  configurazione (credenziali rifiutate, modello inesistente), il sistema NON DEVE tentare il ripiego
  turno per turno; il comportamento resta quello attuale.
- **FR-007** *(REQ-035)*: L'esito dell'indicizzazione DEVE distinguere `input_rejected` (testo rifiutato)
  da `provider_unavailable` e `store_unavailable`, sia negli eventi sia nell'esito restituito.
- **FR-008** *(REQ-035)*: L'esito di `memory index-semantic`, in forma umana e JSON, DEVE elencare per
  ogni turno rifiutato la sessione, l'indice del turno e il motivo; i campi attuali (`embedded`,
  `skipped`, `errors`) DEVONO restare invariati nel nome e nel significato.
- **FR-009** *(REQ-035, REQ-026)*: Gli eventi di osservabilità emessi dall'indice semantico DEVONO
  restare metrics-only: possono portare conteggi (incluso il numero di turni rifiutati) e motivi, mai
  testo del transcript né identificativi di sessione. *(Fuori da questa feature e invariato: l'evento
  che l'archiviazione emette quando l'indicizzazione automatica solleva un'eccezione porta già la
  `session_key`.)*
- **FR-010** *(REQ-036)*: L'incrementalità DEVE restare quella di oggi: un turno è «già indicizzato» se
  tutte le sue unità sono presenti nell'indice; i turni già indicizzati non tornano al provider; un turno
  rifiutato o perso in passato viene ritentato al run successivo senza rebuild.
- **FR-011**: Il conteggio `embedded` DEVE contare i **turni** indicizzati (non i pezzi), così che il suo
  significato per l'utente non cambi.

### Key Entities

- **Turno**: l'unità di memoria archiviata (sessione, indice, ruolo, testo). Resta l'unità di conteggio
  e di citazione.
- **Pezzo di turno**: porzione del testo di un turno che rientra nel budget d'ingresso; esiste solo per i
  turni oltre il budget e porta il riferimento al turno di cui fa parte.
- **Turno rifiutato**: registrazione, nell'esito di un run, di un turno che il provider non ha accettato:
  sessione, indice di turno, motivo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Riprodotto il caso di Kaelen (una sessione di 181 turni con un turno da ~290.000 caratteri,
  provider che rifiuta oltre il limite), l'indicizzazione chiude con **181 turni indicizzati e 0 errori**
  invece di 0 indicizzati e 181 errori.
- **SC-002**: Con un rifiuto mirato a un solo turno su N, gli errori riportati sono **esattamente 1** e i
  turni indicizzati **N−1**.
- **SC-003**: In un run su un indice già completo, il provider riceve **zero** richieste (incrementalità
  invariata, NFR-009 della 072).
- **SC-004**: Una ricerca il cui termine compare solo in un turno spezzato restituisce quel turno **una
  sola volta**.
- **SC-005**: Chi lancia il comando identifica sessione e turno di ogni rifiuto **dall'esito stesso**, in
  zero passaggi aggiuntivi.
- **SC-006**: Tutti i test esistenti della memoria semantica, della memoria e della CLI restano verdi
  (nessuna regressione sul pregresso).

## Assumptions

- Il budget d'ingresso è lo stesso tetto in token già configurabile per il corpus (default dimensionato
  sul modello cloud più grande in uso); chi usa un modello con finestra più piccola lo abbassa come già
  documentato per il corpus.
- La lunghezza dei turni archiviati non cambia: l'archivio grezzo resta intatto e append-only; la
  correzione vive tutta nell'indice semantico derivato.
- Gli identificativi di sessione **non** sono testo del transcript e possono comparire nell'esito per
  l'utente (che li vede già in `memory list`), ma non negli eventi di osservabilità.
- L'aggiornamento non richiede di ricostruire l'indice semantico né di cambiare la configurazione del
  nodo: un normale run di `memory index-semantic` recupera i turni persi.

## Out of Scope

- **Limite complessivo per richiesta del provider** (somma dei token di un intero invio): riguarda anche
  l'indice del corpus ed è gestito dal ripiego per turno di FR-004 nel caso della memoria; un tetto
  esplicito per richiesta non è introdotto qui. *Casa durevole:* nessuna voce nuova — se emergerà dal
  campo per il corpus, apparterrà all'epica `sertor-core`.
- **Troncamento** come alternativa allo spezzare: scartato (vedi Clarifications).
- **Comando di diagnosi dei turni** (`memory show` con dimensione in token): non serve dopo FR-008.
