# Feature Specification: Pannello TUI — vista live dell'osservabilità

**Feature Branch**: `022-osservabilita-tui-live`

**Created**: 2026-06-14

**Status**: Draft

**Input**: FEAT-003 dell'epica osservabilità — fonte requisiti `requirements/osservabilita/pannello-tui-live/requirements.md`. La prima superficie **visibile**: un pannello da terminale che mostra lo stato corrente di Sertor (ultimo index, cache, consumo, ultimi eventi) e si aggiorna **dal vivo**, leggendo i report di F2 (già su master). È un consumatore sottile: non ricalcola nulla, non persiste nulla.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Aprire il cruscotto dal vivo (Priority: P1)

Chi usa Sertor vuole **vedere** cosa sta succedendo senza leggere righe di log o file: apre un pannello
nel terminale e trova, a colpo d'occhio, lo **stato corrente** — l'ultima indicizzazione (quanti
documenti/chunk, dimensione embedding), l'efficacia della **cache** (hit/miss), il **consumo** di token,
e gli **ultimi eventi** accaduti. Il pannello si **aggiorna automaticamente** mentre Sertor lavora, così
durante un'indicizzazione o una serie di ricerche i numeri cambiano sotto i suoi occhi.

**Why this priority**: è il primo momento in cui l'osservabilità diventa **visibile** — il valore che
l'utente aspettava dopo F1 (i numeri restano) e F2 (i numeri si leggono). È l'MVP della superficie.

**Independent Test**: con eventi conservati (simulati), avviare il modello della vista e verificare che
produca uno **snapshot** coerente dello stato corrente; verificare che un aggiornamento periodico
rilegga i dati e rifletta i nuovi eventi. La logica di stato è testabile **senza** un terminale reale.

**Acceptance Scenarios**:

1. **Given** eventi conservati, **When** si apre il pannello, **Then** mostra lo stato corrente (ultimo index, hit-rate cache, token consumati, ultimi eventi).
2. **Given** il pannello aperto, **When** arrivano nuovi eventi (una nuova operazione), **Then** entro il prossimo aggiornamento il pannello li riflette, senza riavvio.
3. **Given** il pannello aperto, **When** l'utente esce, **Then** il pannello si chiude in modo pulito senza alterare nulla.

---

### User Story 2 - Degradazione onesta quando manca qualcosa (Priority: P2)

Il pannello dipende da due cose: che la **persistenza** dell'osservabilità sia attiva (altrimenti non ci
sono dati) e che il **componente di interfaccia** sia disponibile (è un'aggiunta opzionale). Se manca
l'uno o l'altro, l'utente deve ricevere un **messaggio chiaro e azionabile** — «attiva l'osservabilità»
o «installa il componente del pannello» — **non** un errore oscuro o un crash.

**Why this priority**: la portabilità e la non-sorpresa: il pannello gira su qualunque progetto ospite,
e quando un prerequisito manca lo dice in modo utile.

**Independent Test**: con persistenza disattivata, verificare che il pannello comunichi «nessun dato /
attiva l'osservabilità» (stato vuoto onesto); con il componente d'interfaccia assente, verificare il
messaggio azionabile (errore esplicito con l'istruzione).

**Acceptance Scenarios**:

1. **Given** persistenza disattivata o nessun evento, **When** si apre il pannello, **Then** mostra uno stato **vuoto onesto** con l'indicazione di come abilitare la raccolta dati (non un crash).
2. **Given** il componente d'interfaccia non installato, **When** si prova ad aprire il pannello, **Then** si riceve un messaggio esplicito con l'istruzione per installarlo.

---

### User Story 3 - Sola lettura e non intrusivo (Priority: P3)

Il pannello **osserva**: non deve alterare gli indici, le configurazioni o le operazioni in corso, né
rallentarle. È un visore in sola lettura.

**Why this priority**: un osservatore che disturba l'osservato non è accettabile (coerente con la
non-intrusività dello strato persistente).

**Independent Test**: verificare che l'apertura/aggiornamento del pannello non scriva nello store né
modifichi alcun artefatto; che il modello di stato sia una pura lettura dei report.

**Acceptance Scenarios**:

1. **Given** il pannello in esecuzione, **When** si aggiorna, **Then** non avviene alcuna scrittura sugli indici/store né modifica di file.

---

### Edge Cases

- **Persistenza spenta / store vuoto:** stato vuoto onesto con call-to-action, mai crash.
- **Componente d'interfaccia assente:** errore esplicito con l'istruzione d'installazione (come per gli
  altri componenti opzionali del prodotto).
- **Terminale piccolo / ridimensionamento:** il pannello resta leggibile (si adatta).
- **Nessun aggiornamento per un po':** il pannello continua a mostrare l'ultimo stato noto (non si svuota).
- **Uscita durante un aggiornamento:** chiusura pulita, nessuno stato corrotto.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il sistema MUST offrire un **pannello da terminale** che mostra lo **stato corrente**:
  ultima indicizzazione (documenti/chunk/dimensione), efficacia della cache (hit/miss), consumo token,
  e gli ultimi eventi.
- **FR-002**: Il pannello MUST **aggiornarsi periodicamente** in autonomia, riflettendo i nuovi eventi
  senza richiedere un riavvio.
- **FR-003**: Il pannello MUST essere un **consumatore sottile**: legge i report già calcolati (servizio
  di aggregazione) e **non** ricalcola né reimplementa la logica di aggregazione.
- **FR-004**: Il pannello MUST essere in **sola lettura**: non scrive nello store, non modifica indici,
  configurazioni o file, non altera né rallenta le operazioni osservate.
- **FR-005**: Quando non ci sono dati (persistenza spenta o store vuoto), il pannello MUST mostrare uno
  **stato vuoto onesto** con l'indicazione di come abilitare la raccolta, **senza** errore/crash.
- **FR-006**: Quando il **componente d'interfaccia** opzionale non è disponibile, il sistema MUST
  produrre un **messaggio esplicito e azionabile** (istruzione d'installazione), non un errore oscuro.
- **FR-007**: La **frequenza di aggiornamento** MUST essere governata dalla configurazione centralizzata
  (con un default ragionevole).
- **FR-008**: Il pannello MUST funzionare su **qualunque progetto ospite** senza modifiche al suo corpo
  (portabilità).
- **FR-009**: Il pannello MUST chiudersi in modo **pulito** su richiesta dell'utente, senza lasciare
  stato corrotto.
- **FR-010**: La **logica di stato** del pannello (cosa mostrare) MUST essere verificabile **senza** un
  terminale interattivo reale (separata dal rendering).
- **FR-011**: Il pannello MUST mostrare **solo metriche** (mai contenuto grezzo), coerente con la
  privacy-by-default dello strato sottostante.

### Key Entities *(include if feature involves data)*

- **Snapshot dello stato live**: la fotografia corrente che il pannello mostra — derivata dai report
  (ultimo index, cache, consumo, ultimi eventi). È l'unità che il rendering disegna e che si aggiorna.
- **Pannello (superficie)**: l'applicazione da terminale che rende lo snapshot e lo rinfresca a
  intervalli; un guscio sottile sopra il servizio di report.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All'apertura, il pannello mostra lo stato corrente coerente al 100% con gli eventi
  conservati (verificabile sul modello di stato con dati di test).
- **SC-002**: Dopo l'arrivo di nuovi eventi, il pannello li riflette entro il successivo ciclo di
  aggiornamento, senza riavvio.
- **SC-003**: Con persistenza spenta/store vuoto, il pannello mostra uno stato vuoto onesto nel 100% dei
  casi, senza eccezioni/crash.
- **SC-004**: Con il componente d'interfaccia assente, il sistema fornisce un messaggio azionabile (con
  l'istruzione d'installazione) nel 100% dei casi.
- **SC-005**: La logica di stato è verificabile offline e senza terminale reale (test automatici).
- **SC-006**: Il pannello opera su **≥2** progetti ospite diversi senza modifiche al corpo.
- **SC-007**: Nessuna scrittura su store/indici durante l'esecuzione del pannello (sola lettura).

## Assumptions

- **Dipendenza da F1+F2 (già su master):** il pannello legge i **report** del servizio di aggregazione
  (F2), che a sua volta legge lo store persistente (F1). Il pannello non raccoglie né aggrega dati.
- **Componente d'interfaccia opzionale:** il pannello richiede un componente di interfaccia da terminale
  fornito come **estensione opzionale** del prodotto (coerente con gli altri componenti opzionali, es.
  reranking/grafo); senza, il resto del prodotto funziona e il pannello dà un messaggio azionabile.
- **Meccanismo "live" = rilettura periodica:** il pannello si aggiorna **rileggendo** periodicamente i
  report (lo store è scritto in tempo reale dallo strato persistente); un intervallo di refresh
  ragionevole di default, configurabile. (La vista live richiede quindi la persistenza attiva.)
- **Vista live, non storica:** questo pannello mostra lo **stato corrente** e gli ultimi eventi; le viste
  di **report sfogliabili/storici** sono la feature successiva (F4).
- **Fuori ambito:** i report sfogliabili (F4), l'export verso strumenti esterni, la conversione in € e la
  modalità web — tutte feature successive/separate dell'epica.
