# Feature Specification: Cattura & archiviazione locale dei transcript

**Feature Branch**: `031-cattura-archiviazione`

**Created**: 2026-06-14

**Status**: Draft

**Input**: FEAT-001 dell'epica «Memoria delle conversazioni» (MVP, prima metà). Fonte requisiti:
`requirements/memoria-conversazioni/cattura-archiviazione/requirements.md` (27 requisiti EARS).

## User Scenarios & Testing *(mandatory)*

Questa feature aggiunge il **tier grezzo episodico** oggi mancante: cattura le conversazioni
dell'agente con il progetto ospite e le conserva in un archivio locale, persistente e interrogabile
(la *ricerca* è FEAT-002, fuori ambito). È la fonte grezza da cui la distillazione del wiki potrà un
giorno attingere, e su cui la ricerca episodica opererà.

### User Story 1 - Archiviare le conversazioni di una sessione, conservandole (Priority: P1)

Con la memoria attiva, l'owner vuole che ogni sessione di lavoro con l'agente finisca in un archivio
locale **conservato** (non si cancella da solo) e **senza duplicati**, così la conoscenza grezza non
va più persa. Riprocessare le stesse sessioni non deve creare doppioni né alterare ciò che c'è già.

**Why this priority**: è il cuore della feature e dell'intero MVP della memoria — senza l'archivio
non esiste alcun tier episodico su cui costruire ricerca (FEAT-002) e distillazione (FEAT-003). È la
fetta minima che da sola consegna valore: «le conversazioni esistono e si conservano».

**Independent Test**: con la cattura attiva, archiviare N sessioni simulate e verificare che
l'archivio contenga esattamente N record (una voce per sessione, 0 duplicati); ri-archiviare le
stesse N e verificare che il conteggio resti N e i contenuti esistenti siano invariati.

**Acceptance Scenarios**:

1. **Given** la cattura attiva e un archivio vuoto, **When** vengono archiviate 3 sessioni distinte,
   **Then** l'archivio contiene 3 record, uno per sessione, ciascuno con identificatore di sessione,
   identificatore di progetto, timestamp di cattura (UTC) e contenuto del transcript.
2. **Given** una sessione già archiviata, **When** la stessa sessione (stessa chiave canonica) viene
   sottoposta di nuovo all'archiviazione, **Then** non viene creato alcun duplicato, il record
   esistente resta invariato e non viene sollevato alcun errore.
3. **Given** un archivio con sessioni storiche, **When** vengono archiviate nuove sessioni, **Then**
   nessuna sessione precedente viene cancellata o sovrascritta (archivio conservato, non ruotato).
4. **Given** sessioni di due progetti diversi, **When** entrambe vengono archiviate, **Then** i
   record sono separati per progetto e non si mescolano nello stesso spazio.

---

### User Story 2 - Privacy by default e contenuto ripulito dai segreti (Priority: P2)

L'owner deve potersi fidare: a memoria **spenta** (lo stato di default) non viene scritto nulla; a
memoria **accesa**, i segreti incollati nelle conversazioni (chiavi API, token, password) non
finiscono mai in chiaro nell'archivio.

**Why this priority**: i transcript interi sono il dato più sensibile del sistema (codice
proprietario, decisioni, segreti incollati). Senza questa garanzia la feature è inaccettabile da
attivare. Indipendente da US1: si testa attivando/disattivando la cattura e ispezionando l'output.

**Independent Test**: con `SERTOR_MEMORY=false` (default), eseguire il flusso di cattura e verificare
che **nessun** file o record di transcript sia stato creato o modificato; con la cattura attiva,
archiviare un transcript contenente segreti sintetici e verificare che **nessuno** appaia in chiaro
nell'archivio.

**Acceptance Scenarios**:

1. **Given** `SERTOR_MEMORY` non impostata o `false`, **When** il sistema si inizializza e
   opererebbe la cattura, **Then** nessun file/record di transcript viene creato, modificato o letto,
   e nessun adapter o store di memoria viene istanziato.
2. **Given** la cattura attiva e un transcript che contiene una API key (`sk-…`), un token bearer e
   un assegnamento `PASSWORD=…`, **When** la sessione viene archiviata, **Then** quei valori risultano
   sostituiti da un segnaposto e non compaiono in chiaro nel contenuto archiviato.
3. **Given** un segmento di testo su cui lo scrub fallisce o incontra un pattern non riconosciuto,
   **When** la sessione viene archiviata, **Then** il sistema applica un ripiego conservativo (redige
   l'intero segmento) ed emette un warning, senza interrompere l'archiviazione.

---

### User Story 3 - Portabilità: stessa capacità su ospiti diversi (Priority: P3)

La capacità deve funzionare su qualunque progetto/assistente ospite senza modifiche al suo corpo: la
*sorgente* dei transcript (host-specifica) sta dietro un contratto astratto, con Claude Code come
prima implementazione, sostituibile via configurazione.

**Why this priority**: è il vincolo costituzionale (Principio X) che impedisce il lock-in su un
singolo assistente e abilita gli adapter futuri (FEAT-008). Indipendente: si testa con un adapter
fittizio, senza Claude Code reale.

**Independent Test**: eseguire archivio e contratto di cattura con ≥2 adapter simulati (mock) e
verificare che la logica di archivio sia identica; verificare che la scelta dell'adapter avvenga solo
via configurazione, senza rami condizionali sull'identità dell'host nel servizio o nel dominio.

**Acceptance Scenarios**:

1. **Given** due adapter di cattura simulati con la stessa interfaccia, **When** entrambi alimentano
   l'archivio, **Then** la logica di archiviazione, idempotenza e scrub si comporta in modo identico
   indipendentemente dall'adapter.
2. **Given** l'adapter Claude-Code configurato, **When** il sistema scopre le sessioni, **Then** le
   individua scandendo i file di sessione del progetto corrente sotto la sorgente Claude Code, senza
   modificarli né cancellarli, derivando l'identificatore di sessione dal nome del file.
3. **Given** la sorgente dei transcript assente (es. la directory dei progetti Claude Code non
   esiste), **When** la cattura viene avviata, **Then** il sistema emette un warning e lascia
   l'archivio invariato, senza sollevare un errore non gestito.

---

### Edge Cases

- **Sorgente assente o vuota**: directory dei transcript inesistente → warning + archivio invariato,
  nessun errore fatale.
- **Store di archivio guasto/corrotto**: degradazione non-fatale (warning + no-op), l'operazione
  principale dell'agente non si interrompe.
- **Riprocesso massivo**: archiviare in batch sessioni in parte già presenti → solo le nuove entrano,
  le esistenti generano uno skip osservabile (non un no-op silenzioso).
- **Transcript enorme** (sessione di ore): la cattura non deve fallire né bloccare; il costo dello
  scrub resta proporzionato (nessun limite rigido imposto in questa feature).
- **Segreto a cavallo di un confine di parsing**: lo scrub ripiega in modo conservativo redigendo il
  segmento, mai lasciando passare il dubbio.

## Requirements *(mandatory)*

### Functional Requirements

**Controllo di abilitazione (privacy-by-default)**

- **FR-001**: A cattura non esplicitamente abilitata (manopola di memoria assente o `false`), il
  sistema MUST NOT creare, modificare o leggere alcun file o record dell'archivio dei transcript.
- **FR-002**: A cattura disabilitata, il sistema MUST NOT istanziare l'adapter di cattura né lo store
  di archivio (nessuna dipendenza importata, nessun file aperto — comportamento lazy, zero overhead).
- **FR-003**: All'abilitazione, il sistema MUST caricare l'adapter di cattura indicato dalla
  configurazione senza introdurre dipendenze host-specifiche nel corpo del core.

**Contratto di cattura astratto (host-agnostico)**

- **FR-004**: Il sistema MUST esporre un'astrazione di cattura dei transcript (porta) che separi il
  *cosa* (elencare le sessioni, leggerne il contenuto) dal *come* host-specifico.
- **FR-005**: Il sistema MUST selezionare l'implementazione concreta dell'adapter **esclusivamente
  via configurazione**, senza diramazioni sull'identità dell'host nel servizio di archivio o nel
  dominio.
- **FR-006**: Se l'adapter configurato non trova la sorgente attesa dei transcript, il sistema MUST
  emettere un warning e lasciare l'archivio invariato, senza sollevare un errore non gestito.

**Adapter Claude-Code (prima implementazione)**

- **FR-007**: Dove è configurato l'adapter Claude-Code, il sistema MUST scoprire le sessioni
  scandendo i file di sessione del progetto corrente nella sorgente locale di Claude Code, leggendone
  il contenuto **senza modificarli o cancellarli**.
- **FR-008**: Dove è configurato l'adapter Claude-Code, il sistema MUST derivare l'identificatore
  canonico di sessione dal nome del file di sessione, usandolo come chiave per il controllo di
  idempotenza.

**Archivio locale e conservazione**

- **FR-009**: Il sistema MUST persistere i transcript archiviati in un archivio **locale** sotto la
  directory runtime del progetto, mai in una posizione accessibile da remoto per default.
- **FR-010**: L'archivio MUST essere **namespaced per progetto**, così che sessioni di progetti
  diversi non si mescolino.
- **FR-011**: L'archivio MUST essere escluso dal versionamento (gitignore o equivalente), così che il
  contenuto dei transcript non finisca mai accidentalmente sotto controllo di versione.
- **FR-012**: All'archiviazione di una sessione, il sistema MUST registrare almeno: identificatore di
  sessione, identificatore di progetto, timestamp di cattura (UTC), tipo di adapter sorgente, e il
  contenuto del transcript ripulito dai segreti.
- **FR-013**: L'archivio MUST conservare la struttura interna del transcript a grana di **turno**
  dentro il record di sessione, così che una futura ricerca possa indicizzare per turno senza
  ri-elaborare la sorgente grezza (decisione: granularità ibrida — vedi Assumptions).
- **FR-014**: All'archiviazione, il sistema MUST NOT cancellare o sovrascrivere alcuna sessione
  precedente, a prescindere dall'età, salvo un comando di cancellazione esplicito (archivio
  conservato, non ruotato).

**Idempotenza**

- **FR-015**: Sottoponendo all'archiviazione la stessa sessione (per chiave canonica) più volte, il
  sistema MUST memorizzarla esattamente una volta, lasciando invariato il record esistente.
- **FR-016**: Se una sessione con la stessa chiave canonica esiste già, il sistema MUST NOT creare un
  duplicato e MUST NOT sollevare un errore (idempotenza silente).

**Scrub dei segreti nel contenuto**

- **FR-017**: Durante l'archiviazione, il sistema MUST applicare lo scrub dei segreti al **contenuto
  testuale libero** del transcript prima di persisterlo, sostituendo i pattern riconosciuti con un
  segnaposto.
- **FR-018**: Lo scrub MUST coprire almeno: chiavi API note, token bearer, assegnamenti del tipo
  `CHIAVE=VALORE` dove il nome chiave contiene hint di segreto (key/token/secret/password/
  authorization) e valori di header di autorizzazione inline.
- **FR-019**: Se lo scrub incontra un pattern non riconosciuto o fallisce su un segmento, il sistema
  MUST applicare un ripiego conservativo (redige l'intero segmento) ed emettere un warning, senza
  interrompere l'archiviazione.
- **FR-020**: Le regole di scrub MUST essere configurabili (pattern aggiuntivi via configurazione),
  così da coprire formati di segreto specifici del progetto senza modificare il corpo del core.

**Retention (solo gancio)**

- **FR-021**: Il sistema MUST esporre un parametro di retention (default: nessuna scadenza, conserva
  indefinitamente) il cui valore è registrato nei metadati dell'archivio, così che una feature futura
  possa applicarne l'enforcement senza migrazione di formato.
- **FR-022**: Se il parametro di retention è impostato, il sistema MUST registrarne la politica nei
  metadati ma MUST NOT applicare cancellazioni automatiche in questa feature (l'enforcement è
  fuori ambito, FEAT-006).

**Osservabilità minima e robustezza**

- **FR-023**: All'archiviazione riuscita di una sessione, il sistema MUST emettere un evento
  strutturato con almeno: chiave di sessione, identificatore di progetto, tipo di adapter, dimensione
  del contenuto (post-scrub) e se la sessione era nuova o già presente.
- **FR-024**: Quando una sessione viene saltata perché già presente, il sistema MUST emettere un
  evento strutturato di skip, così che le esecuzioni in batch siano osservabili senza no-op silenziosi.
- **FR-025**: Se lo store di archivio è indisponibile o corrotto, il sistema MUST emettere un warning
  e lasciare l'operazione in corso come no-op, senza propagare un errore fatale al chiamante.

**Integrazione**

- **FR-026**: Il sistema MUST cablare l'adapter di cattura e lo store di archivio **esclusivamente
  nel composition root**, tramite funzioni di costruzione che leggono la configurazione centralizzata
  e restituiscono istanze conformi al contratto.
- **FR-027**: Lo scrub MUST garantire che nessun segreto sia mai persistito né emesso negli eventi di
  osservabilità (la redazione si applica sia al contenuto sia ai campi degli eventi).

### Key Entities *(include if feature involves data)*

- **Sessione archiviata (Archived Session)**: l'unità conservata dell'archivio. Rappresenta una
  conversazione intera; attributi: chiave canonica di sessione, identificatore di progetto, timestamp
  di cattura (UTC), tipo di adapter sorgente, contenuto scrubbed con i confini dei turni preservati,
  metadati (incl. politica di retention). Una per sessione; idempotente sulla chiave.
- **Riferimento di sessione (Session Ref)**: il puntatore leggero a una sessione presso la sorgente
  (es. file di transcript), prodotto dall'adapter durante la scoperta; porta la chiave canonica.
- **Contenuto del transcript (Transcript Content)**: il testo grezzo di una sessione letto
  dall'adapter, strutturato in turni, prima dello scrub.
- **Adapter di cattura (Transcript Capture Adapter)**: il contratto astratto host-agnostico che
  elenca le sessioni e ne legge il contenuto; l'implementazione Claude-Code è la prima, selezionata
  via configurazione.
- **Archivio (Memory Archive)**: lo store locale, per-progetto, conservato e gitignored, che
  persiste le sessioni archiviate.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Con la cattura attiva, dopo N sessioni distinte l'archivio contiene esattamente N
  record (una voce per sessione; duplicati = 0).
- **SC-002**: Archiviare K volte la stessa sessione lascia esattamente 1 record e non altera il
  contenuto già presente (idempotenza conservativa verificabile).
- **SC-003**: Con la memoria disattivata (default), il flusso di cattura non crea né modifica alcun
  file o record su disco (verificabile: 0 scritture).
- **SC-004**: Su un corpus di test con segreti sintetici, nessun pattern di segreto noto (API key,
  token, password) compare in chiaro nell'archivio (0 occorrenze).
- **SC-005**: La logica di archivio e il contratto di cattura passano i test con ≥2 adapter simulati,
  senza alcun ramo condizionale sull'identità dell'host nel servizio o nel dominio.
- **SC-006**: Nessuna sessione precedentemente archiviata viene cancellata o sovrascritta
  dall'archiviazione di nuove sessioni (conservazione verificabile su sequenze di archiviazione).
- **SC-007**: Un guasto simulato dello store non interrompe l'operazione principale (l'esecuzione
  prosegue; viene emesso un warning), confermando la degradazione non-fatale.

## Assumptions

- **Granularità ibrida (decisione utente 2026-06-14, DA-M-b risolta)**: l'unità *archiviata* è la
  **sessione intera** (record idempotente, fedele al grezzo); l'archivio conserva però i **confini
  dei turni** dentro il record, così la ricerca di FEAT-002 potrà indicizzare a grana di turno senza
  ri-elaborare la sorgente. Una granularità più fine (thread/scambio) è rivalutabile in futuro.
- **Cattura tutto-con-opt-in (decisione utente 2026-06-14, DA-M-c risolta)**: con la cattura attiva
  si archiviano **tutte** le sessioni; la marcatura selettiva "remember this" è una feature
  successiva (FEAT-005) e questa feature **non** vi dipende.
- **Privacy-by-default**: la cattura è **disattivata** di default; richiede un opt-in esplicito.
- **Primo ospite = Claude Code**: la sorgente dei transcript per la prima implementazione sono i file
  di sessione che Claude Code già persiste localmente; la cattura li **legge** (nessun hook di
  intercettazione runtime necessario). La porta resta astratta: altri assistenti sono adapter futuri
  (FEAT-008, fuori ambito).
- **Formato della sorgente non documentato**: la struttura interna dei file di sessione di Claude
  Code non è documentata pubblicamente; l'adapter opera in modalità **best-effort difensiva**
  (parsing tollerante con fallback). Lo schema esatto e il parsing difensivo sono **decisioni di
  design** del plan a valle.
- **Collocazione e formato dell'archivio**: l'archivio risiede sotto la directory runtime del
  progetto, gitignored, coerente con gli artefatti runtime esistenti. La scelta esatta di posizione,
  formato e schema (incl. come preservare i confini dei turni) è **decisione di design** del plan.
- **Riuso di pattern esistenti**: il design a valle riuserà i pattern già nel repo (store SQLite
  locale non-fatale come la cache embeddings e lo store di osservabilità; scrub esteso dalla
  redazione per-campo esistente al contenuto libero; manopole centralizzate nella configurazione;
  stile delle porte Protocol). Se serva una porta Protocol dedicata o basti un adapter è materia di
  design.
- **Additivo / stdlib-only**: nessuna nuova dipendenza obbligatoria; il corpo del core usa solo la
  libreria standard. Le dipendenze host-specifiche restano confinate nell'adapter.

## Dependencies

- **A monte (nessuna hard)**: questa è la prima feature dell'epica; non dipende da altre feature di
  memoria. Si appoggia ai pattern e ai meccanismi del core già su master (configurazione, logging
  strutturato/redazione, composition root).
- **A valle (alimentate da questa feature)**: FEAT-002 (ricerca episodica) consuma l'archivio;
  FEAT-003 (distillazione) lo userà come fonte grezza; FEAT-004/005/006/008 lo estendono.
