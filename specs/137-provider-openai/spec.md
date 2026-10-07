# Feature Specification: Embedding con l'API OpenAI diretta

**Feature Branch**: `137-provider-openai`

**Created**: 2026-10-07

**Status**: Draft

**Deriva da**: FEAT-012 (epica `sertor-core`) · **Requisiti**: [`requirements/sertor-core/provider-openai/requirements.md`](../../requirements/sertor-core/provider-openai/requirements.md)

**Input**: aggiungere un provider di embedding che usi l'API OpenAI diretta (o un servizio compatibile
OpenAI), selezionabile con `SERTOR_EMBED_PROVIDER=openai`, con modello di default
`text-embedding-3-large`.

---

## Perché questa feature esiste

Sertor rende all'agente un corpus fatto di codice e documentazione; la **qualità del retrieval** è il
suo fronte di valore, e dipende in larga parte dal provider di embedding. Oggi l'unico provider cloud
è **Azure OpenAI**: chi ha una chiave OpenAI ma nessuna sottoscrizione Azure può scegliere solo fra
provider locali, con semantica più debole.

Il caso è concreto e di oggi: sul progetto stesso la chiave Azure è stata rifiutata dal servizio
(`http 401`) e le ricerche via MCP si sono fermate. Il ripiego locale funziona ma degrada la risposta
resa all'agente. Una chiave OpenAI è la credenziale cloud più diffusa: un provider che la usi
direttamente ripristina un embedding di qualità senza dipendere da Azure.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Indicizzare e cercare con una chiave OpenAI (Priority: P1)

Un utente con una chiave OpenAI imposta il provider `openai` e la chiave nella configurazione del
progetto, ricostruisce l'indice e interroga il corpus da CLI e da agente (MCP), ottenendo risultati
pertinenti. Non serve alcuna configurazione Azure.

**Why this priority**: è il valore intero della feature; senza questo non c'è nulla.

**Independent Test**: con solo provider e chiave impostati, `index` completa e `search` restituisce
risultati; la stessa cosa via i tool MCP di ricerca.

**Acceptance Scenarios**:

1. **Given** provider `openai` e chiave valida, nessuna variabile Azure, **When** l'utente indicizza il
   progetto, **Then** l'indice viene costruito e il riepilogo nomina il provider OpenAI e il modello.
2. **Given** un indice costruito con `openai`, **When** l'utente o l'agente esegue una ricerca su codice
   o documentazione, **Then** riceve risultati del corpus.
3. **Given** nessun modello indicato, **When** l'utente indicizza, **Then** viene usato
   `text-embedding-3-large`.
4. **Given** un modello diverso indicato in configurazione, **When** l'utente indicizza, **Then** viene
   usato quel modello.

---

### User Story 2 - Capire subito cosa non va (Priority: P1)

Un utente che ha configurato male il provider (chiave mancante, chiave rifiutata, servizio
irraggiungibile) riceve una diagnosi che nomina il problema e il provider, senza mai vedere stampata la
chiave.

**Why this priority**: un provider cloud che fallisce in silenzio o con messaggi opachi è il guasto che
ha motivato la feature; la diagnosi chiara è parte del minimo.

**Independent Test**: si provocano i tre guasti e si legge l'output di `doctor`, della CLI e dei tool
MCP.

**Acceptance Scenarios**:

1. **Given** provider `openai` e chiave vuota, **When** l'utente esegue il controllo di salute,
   **Then** l'area *provider* fallisce e nomina `OPENAI_API_KEY`.
2. **Given** una chiave rifiutata dal servizio, **When** l'utente indicizza o cerca, **Then** l'errore
   nomina il provider e lo stato restituito dal servizio, e non contiene la chiave.
3. **Given** il servizio irraggiungibile, **When** l'utente indicizza, **Then** l'errore è marcato come
   transitorio e, se i tentativi ripetuti sono configurati, l'operazione viene ritentata.

---

### User Story 3 - Cambiare provider senza mescolare gli indici (Priority: P2)

Un utente passa da un provider all'altro (per esempio da `azure` o `glove` a `openai`, o fra due
modelli OpenAI). Gli indici restano separati: nessuna ricerca interroga vettori prodotti da un
provider o modello diverso da quello attivo.

**Why this priority**: indispensabile per la correttezza, ma già garantito dal meccanismo esistente;
qui va solo confermato per il nuovo provider.

**Independent Test**: si indicizza con due provider/modelli e si verifica che le collezioni hanno nomi
distinti e che la cache non serve vettori incrociati.

**Acceptance Scenarios**:

1. **Given** un indice `glove` esistente, **When** l'utente passa a `openai` e indicizza, **Then** viene
   creato un indice distinto e quello `glove` resta intatto.
2. **Given** due modelli OpenAI diversi, **When** l'utente indicizza con entrambi, **Then** ottiene due
   indici distinti.

---

### User Story 4 - Usare un servizio compatibile OpenAI (Priority: P3)

Un utente indica un URL di base diverso da quello ufficiale, verso un servizio che espone la stessa
interfaccia di embedding, e lo usa come provider `openai`.

**Why this priority**: allarga il bacino a costo quasi nullo, ma non è il bisogno che ha mosso la
feature.

**Independent Test**: con un URL di base personalizzato, le richieste vanno a quell'indirizzo.

**Acceptance Scenarios**:

1. **Given** un URL di base personalizzato, **When** l'utente indicizza, **Then** le richieste di
   embedding vanno a quell'indirizzo.

---

### Edge Cases

- URL di base con o senza barra finale: il risultato deve essere lo stesso.
- Modello inesistente o non abilitato per la chiave: il servizio risponde con errore; va riportato
  come errore del provider con lo stato, non come indice vuoto.
- Limite di frequenza (429): trattato come transitorio e ritentato se configurato.
- Testo troppo lungo o batch rifiutato (400): errore non transitorio con lo stato.
- Risposta del servizio senza conteggio dei token: l'evento di costo omette il campo, non riporta zero.
- Variabili Azure e OpenAI entrambe presenti: decide solo il selettore del provider.
- Chiave presente nella shell ma non nel file di configurazione del progetto: vale la regola di
  risoluzione già in uso per le altre variabili.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il sistema MUST offrire `openai` come valore del selettore di provider di embedding, sia
  per l'indicizzazione sia per l'interrogazione.
- **FR-002**: Un valore sconosciuto del selettore MUST produrre un errore di configurazione che elenca
  `openai` fra i valori ammessi.
- **FR-003**: Il sistema MUST leggere chiave, modello e URL di base da tre impostazioni dedicate
  (`OPENAI_API_KEY`, `OPENAI_EMBED_MODEL`, `OPENAI_BASE_URL`).
- **FR-004**: I default MUST essere `text-embedding-3-large` per il modello e
  `https://api.openai.com/v1` per l'URL di base, definiti in un unico punto della configurazione.
- **FR-005**: La scelta del provider MUST dipendere solo dal selettore, non dalla presenza di altre
  variabili.
- **FR-006**: La validazione statica della configurazione MUST segnalare la chiave mancante senza
  contattare il servizio, e MUST NOT richiedere variabili Azure quando il provider è `openai`.
- **FR-007**: Il controllo di salute MUST far fallire l'area *provider* nominando la chiave mancante.
- **FR-008**: Il provider MUST restituire un vettore per testo, nell'ordine di ingresso, inviando i
  testi a lotti non più grandi della dimensione configurata.
- **FR-009**: Il provider MUST registrare la dimensione dei vettori dalla prima risposta.
- **FR-010**: Il provider MUST emettere l'evento di embedding col conteggio dei token quando il servizio
  lo fornisce, e ometterlo quando non lo fornisce.
- **FR-011**: Un errore HTTP del servizio MUST diventare un errore di embedding che nomina provider e
  stato, transitorio solo per 429 e 5xx.
- **FR-012**: Un servizio irraggiungibile MUST produrre un errore di embedding transitorio che nomina il
  provider e il tipo di guasto.
- **FR-013**: Con tentativi ripetuti configurati, il provider MUST ritentare gli errori transitori per
  singolo lotto, senza ri-elaborare i lotti già riusciti.
- **FR-014**: Una configurazione incompleta (chiave, modello o URL vuoti) MUST fallire alla costruzione
  con un errore non transitorio che nomina i campi mancanti.
- **FR-015**: Il valore della chiave MUST NOT comparire in log, eventi, messaggi d'errore, output di
  `doctor` o errori dei tool MCP.
- **FR-016**: L'identità del provider MUST includere il modello, così che indici e cache siano separati
  per provider e per modello.
- **FR-017**: Il comportamento del provider `azure` MUST restare invariato.
- **FR-018**: La documentazione utente MUST spiegare come attivare il provider, le tre impostazioni coi
  default, il costo indicativo e che cambiare provider richiede di re-indicizzare; il modello di
  configurazione d'esempio del repository MUST elencare le tre impostazioni.

### Key Entities

- **Provider di embedding `openai`**: trasforma testi in vettori tramite il servizio; identità =
  provider + modello; proprietà: dimensione del vettore (nota dopo la prima risposta).
- **Configurazione del provider**: chiave (segreta), modello, URL di base.
- **Indice/collezione**: per corpus e identità del provider; uno per modello.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Con solo selettore e chiave impostati, indicizzazione e ricerca (CLI e MCP) riescono al
  primo tentativo sul corpus di questo progetto, senza alcuna variabile Azure.
- **SC-002**: Cambiando provider o modello, il 100% degli indici precedenti resta intatto e separato.
- **SC-003**: In ciascuno dei tre guasti (chiave mancante, rifiutata, servizio irraggiungibile) la
  diagnosi nomina il problema; in 0 casi su 3 compare la chiave.
- **SC-004**: La suite di test senza rete resta verde, inclusi tutti i test esistenti del provider
  `azure` senza modifiche alle loro asserzioni.
- **SC-005**: Un utente che legge solo la documentazione utente attiva il provider senza consultare il
  codice.

## Assumptions

- Il servizio espone l'interfaccia di embedding nel formato OpenAI standard; i servizi compatibili che
  la rispettano funzionano senza modifiche.
- Le chiavi di progetto OpenAI bastano: le intestazioni di organizzazione/progetto sono fuori da questo
  taglio.
- Il nome `OPENAI_API_KEY` è quello convenzionale ed è accettabile condividerlo con altri strumenti.
- **Installer congelato** (decisione utente 2026-09-18): il wizard `sertor configure` e il modello
  `.env` depositato sugli ospiti non vengono toccati; il cablaggio è un debito tracciato verso il nodo
  Kaelen. Sugli ospiti il provider si attiva scrivendo le impostazioni nel `.env` (a mano o con
  `configure --set`).
- Il cambio di provider richiede un re-index, come per i provider esistenti.

## Out of Scope

- Cablaggio nel wizard dell'installer e nel suo modello `.env` → perimetro Kaelen (debito tracciato).
- Riduzione delle dimensioni del vettore e intestazioni organizzazione/progetto → da promuovere in
  roadmap.
- Provider LLM di chat/completamento: il core non chiama mai un LLM.
- Migrazione automatica di un indice fra provider.
