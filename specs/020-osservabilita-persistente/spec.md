# Feature Specification: Strato di osservabilità persistente

**Feature Branch**: `020-osservabilita-persistente`

**Created**: 2026-06-14

**Status**: Draft

**Input**: FEAT-001 dell'epica osservabilità — fonte requisiti `requirements/osservabilita/strato-osservabilita-persistente/requirements.md`. Dare agli eventi strutturati che il core già emette (oggi effimeri, su stderr) un archivio locale interrogabile, così esistono report storici. È il fondamento dell'epica: l'aggregazione/report e il pannello TUI leggeranno questo archivio.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - I numeri restano e si possono ritrovare (Priority: P1)

Chi gestisce un indice o un progetto con Sertor svolge operazioni (indicizzazioni, ricerche) che già
producono numeri utili — quanti documenti/chunk, quanti token consumati, quanti risultati serviti dalla
cache, quanto è durata l'operazione. Oggi questi numeri **scorrono via** (finiscono solo nel log che
sparisce a fine comando). Con questa capacità **abilitata**, ogni evento viene **conservato** in un
archivio locale, così è possibile **ritrovarlo in seguito** — filtrando per tipo di operazione e per
intervallo di tempo. È ciò che rende possibili i report storici (a valle: «quanto ho speso questa
settimana?», «quanto risparmia la cache nel tempo?»).

**Why this priority**: è il valore portante e il **fondamento** dell'intera epica: senza un luogo dove
i numeri restano, non esistono né report né pannello. Tutto il resto vi si appoggia.

**Independent Test**: con la persistenza abilitata, eseguire alcune operazioni e verificare che gli
eventi corrispondenti siano poi **recuperabili** dall'archivio, filtrabili per tipo di operazione e per
intervallo temporale, con i loro campi e l'istante. Interamente offline (eventi simulati, nessuna rete).

**Acceptance Scenarios**:

1. **Given** la persistenza abilitata, **When** vengono svolte N operazioni che emettono eventi, **Then** l'archivio contiene almeno N eventi recuperabili, ciascuno con il proprio tipo di operazione, i campi e l'istante.
2. **Given** un archivio con eventi di tipi diversi su un arco temporale, **When** si chiedono i soli eventi di un dato tipo in un dato intervallo, **Then** vengono restituiti esattamente quelli.
3. **Given** la persistenza abilitata, **When** un'operazione emette un evento con un campo che assomiglia a un segreto, **Then** quel valore è **mascherato** anche nell'archivio (come già nei log).
4. **Given** la persistenza abilitata e nessun opt-in per il testo grezzo, **When** si svolge una ricerca, **Then** l'archivio contiene solo metriche/metadati e **nessun testo di query**.

---

### User Story 2 - Chi non la attiva non vede alcun cambiamento (Priority: P2)

Chi usa Sertor oggi e **non** abilita la persistenza non deve subire **nessuna** differenza: stesso
comportamento, stesse prestazioni, nessun file nuovo creato. La capacità è **opt-in** e conservativa
per default: deve essere invisibile finché non la si accende esplicitamente.

**Why this priority**: tutela la base installata e rispetta il vincolo di non-regressione; è la
condizione che rende la feature **additiva** e sicura da introdurre.

**Independent Test**: con la persistenza **disattivata** (default), verificare che il comportamento di
logging odierno (output e mascheramento) sia invariato, che **nessun archivio** venga creato, e che la
suite di test esistente resti verde senza modifiche ai consumatori attuali.

**Acceptance Scenarios**:

1. **Given** la persistenza disattivata (default), **When** si svolgono operazioni, **Then** nessun archivio è creato e l'output di logging è identico a oggi.
2. **Given** un consumatore esistente del logging, **When** la feature è presente ma disattivata, **Then** il consumatore funziona esattamente come prima (nessuna modifica richiesta).

---

### User Story 3 - Conservare non deve mai rompere né rallentare il lavoro (Priority: P3)

L'atto di conservare gli eventi non deve **mai** interferire con l'operazione osservata: né rallentarla
in modo percepibile, né — soprattutto — farla **fallire** se l'archivio ha un problema (è pieno, non
scrivibile, danneggiato). In quel caso l'operazione prosegue come se la persistenza non ci fosse, e il
problema viene **segnalato** senza bloccare nulla.

**Why this priority**: l'osservabilità è un'aggiunta di servizio, non una fonte di verità: non può
degradare l'affidabilità di ciò che osserva (coerente con la cache della feature precedente).

**Independent Test**: simulare un archivio guasto (non scrivibile/danneggiato) durante un'operazione e
verificare che l'operazione **riesca lo stesso**, senza eccezioni propagate, con una segnalazione di
avviso; misurare che, ad archivio sano, l'overhead sull'operazione sia trascurabile.

**Acceptance Scenarios**:

1. **Given** un archivio non scrivibile o danneggiato, **When** un'operazione emette eventi, **Then** l'operazione si completa correttamente e il guasto è segnalato come avviso non fatale.
2. **Given** la persistenza attiva e l'archivio sano, **When** si svolge un'operazione, **Then** il tempo dell'operazione non aumenta in modo misurabile rispetto a persistenza spenta.

---

### Edge Cases

- **Riesecuzioni e riavvii:** appendere eventi in esecuzioni successive (o dopo un riavvio) **non**
  corrompe né perde gli eventi già archiviati (append non-distruttivo).
- **Archivio assente alla prima attivazione:** la prima operazione ad archivio attivo lo inizializza
  senza errori.
- **Più operazioni ravvicinate:** eventi emessi a raffica vengono tutti archiviati, senza perdite.
- **Tipi di evento nuovi in futuro:** un nuovo tipo di evento emesso dal core viene archiviato senza
  bisogno di interventi mirati (cattura per tutti i tipi, non per un sottoinsieme).
- **Spazio/retention:** è previsto un **gancio** per limitare la crescita dell'archivio (la politica di
  dettaglio è rinviata — vedi Assumptions).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Dove la persistenza è abilitata, il sistema MUST scrivere in un archivio locale ogni
  evento di osservabilità emesso, preservandone il tipo di operazione, i campi e l'istante.
- **FR-002**: Il sistema MUST catturare **tutti** i tipi di evento emessi, non un sottoinsieme (nessun
  tipo viene silenziosamente ignorato).
- **FR-003**: Il sistema MUST permettere di recuperare gli eventi archiviati filtrando per **tipo di
  operazione** e per **intervallo temporale**.
- **FR-004**: Se la persistenza non è abilitata, il sistema MUST comportarsi esattamente come oggi:
  nessun archivio creato, output di logging e mascheramento invariati.
- **FR-005**: Il sistema MUST mantenere additivo il comportamento di logging odierno: i consumatori
  attuali del logging non si rompono e non richiedono modifiche.
- **FR-006**: Mentre un'operazione è in corso, l'archiviazione dei suoi eventi MUST NOT bloccarla né
  rallentarla in modo misurabile.
- **FR-007**: Se l'archiviazione di un evento fallisce (archivio non scrivibile, danneggiato o
  occupato), l'operazione osservata MUST proseguire senza essere influenzata, e il guasto MUST essere
  segnalato come avviso non fatale (mai un errore dell'operazione osservata).
- **FR-008**: Per default il sistema MUST archiviare **solo** campi di metrica/metadato e **mai**
  contenuto grezzo (es. testo di query); la persistenza del testo grezzo è una scelta esplicita
  successiva, fuori da questa feature.
- **FR-009**: Il sistema MUST applicare all'archivio lo **stesso mascheramento dei segreti** già attivo
  per i log (nessun segreto persistito).
- **FR-010**: L'attivazione e la **sede** dell'archivio MUST essere governate dalla configurazione
  centralizzata (nessun default codificato nei componenti), con un **gancio di retention** previsto.
- **FR-011**: La sede dell'archivio MUST derivare dalla configurazione (nessun percorso fisso) e
  l'archivio MUST essere un artefatto rigenerabile, escluso dal versionamento.
- **FR-012**: Appendere eventi in esecuzioni successive o dopo un riavvio MUST NOT corrompere
  l'archivio né perdere gli eventi già presenti (append non-distruttivo).
- **FR-013**: La capacità MUST funzionare su qualunque progetto ospite senza modifiche al suo corpo,
  solo cambiando configurazione (portabilità).

### Key Entities *(include if feature involves data)*

- **Evento di osservabilità (persistito)**: l'unità archiviata — tipo di operazione, insieme di campi
  (metrica/metadato), istante. È la versione conservata di ciò che oggi finisce solo nei log.
- **Archivio degli eventi**: il contenitore locale, interrogabile per tipo di operazione e intervallo
  temporale; rigenerabile, escluso dal versionamento; sede derivata dalla configurazione.
- **Manopola di persistenza**: l'impostazione centralizzata che attiva/disattiva la persistenza
  (default disattivata), individua la sede dell'archivio e prevede il gancio di retention.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Con la persistenza attiva, dopo **N** operazioni il numero di eventi recuperabili
  dall'archivio è **≥ N** (almeno uno per ogni evento emesso).
- **SC-002**: È possibile recuperare i soli eventi di un dato tipo di operazione in un dato intervallo
  temporale, ottenendo esattamente quegli eventi.
- **SC-003**: Con la persistenza disattivata (default), nessun archivio è creato e il comportamento
  osservabile è identico a oggi (nessuna regressione, suite esistente verde senza modifiche).
- **SC-004**: Un guasto dell'archivio durante un'operazione **non** causa il fallimento
  dell'operazione, nel 100% dei casi simulati; il guasto è segnalato.
- **SC-005**: Ad archivio sano, l'overhead introdotto dalla persistenza sull'operazione osservata è
  **trascurabile** e misurato (entro una soglia fissata in fase di design).
- **SC-006**: Nessun contenuto grezzo (es. testo di query) e nessun segreto compaiono nell'archivio
  nella configurazione di default.
- **SC-007**: La capacità opera su **≥2** progetti ospite diversi senza modifiche al corpo, solo
  cambiando configurazione.

## Assumptions

- **Default disattivata:** coerente con il principio privacy-by-default e con la non-regressione; la
  persistenza è una scelta esplicita dell'operatore.
- **Privacy decisa:** principio privacy-by-default a strati già fissato a livello di epica (default solo
  metriche; testo grezzo = opt-in di una feature successiva); qui è un **vincolo**, non si implementa
  l'opt-in del testo.
- **Stato attuale favorevole:** oggi nessun evento del core porta testo di query (verificato) → il
  default «solo metriche» è realizzabile senza dover filtrare nulla di esistente; servirà una
  classificazione dei campi quando si introdurranno campi di contenuto.
- **Retention (gancio, non politica):** si prevede solo il **gancio** di retention; la politica di
  dettaglio (limite per tempo/dimensione, rotazione) è rinviata (decisione aperta a livello di epica),
  con default conservativo configurabile.
- **Sede dell'archivio:** un artefatto locale rigenerabile in una posizione derivata dalla
  configurazione (accanto agli altri artefatti d'indice), escluso dal versionamento.
- **Neutralità sul meccanismo e sullo schema:** *come* gli eventi vengono intercettati e *come*
  l'archivio è strutturato sono decisioni di **design** a valle; lo schema sarà dimensionato sui
  bisogni di aggregazione della feature a valle (report per intervallo, correlazione tra eventi).
- **Fuori ambito:** aggregazione/report, pannello TUI, export verso strumenti esterni, stima dei costi
  in valuta, e l'opt-in per persistere il testo grezzo — tutte feature successive dell'epica.
