# Feature Specification: Pannello TUI — report sfogliabili

**Feature Branch**: `023-osservabilita-tui-report`

**Created**: 2026-06-14

**Status**: Draft

**Input**: FEAT-004 dell'epica osservabilità — fonte requisiti `requirements/osservabilita/pannello-tui-report/requirements.md`. L'ultimo Must dell'osservabilità: dentro lo stesso pannello da terminale (F3), viste di **report sfogliabili** — l'andamento storico di cache (hit/miss), costo (token), salute e freschezza del corpus — navigabili da tastiera e filtrabili per intervallo. Rende i report di F2 (già su master); non ricalcola nulla.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sfogliare i report storici (Priority: P1)

Chi ha raccolto dati di osservabilità vuole **rivederli nel tempo**, non solo lo stato corrente: apre il
pannello e **naviga tra viste** — la **cache** (hit/miss giorno per giorno + risparmio cumulativo), il
**costo** (token per provider e per giorno), la **salute** del corpus (documenti/chunk + da quanto non
si re-indicizza). Si sposta tra le viste con la tastiera, a colpo d'occhio.

**Why this priority**: è la risposta alla domanda esplicita «missing vs hit **nel tempo**» e «quanto ho
speso questa settimana»; completa il pannello (la vista live mostra l'adesso, i report mostrano la
storia). È l'MVP di questa feature e l'ultimo Must dell'epica.

**Independent Test**: con eventi conservati su più giorni (simulati), verificare che le funzioni di
resa di ciascun report (cache/costo/salute) producano un testo coerente con gli eventi; la logica di
resa è testabile **senza** terminale.

**Acceptance Scenarios**:

1. **Given** eventi su più giorni, **When** si apre la vista cache, **Then** mostra hit/miss per giorno e i totali + il risparmio stimato.
2. **Given** eventi con token su più giorni/provider, **When** si apre la vista costo, **Then** mostra i token per provider e per giorno.
3. **Given** eventi di indicizzazione, **When** si apre la vista salute, **Then** mostra l'ultimo stato del corpus e **da quanto** non si re-indicizza (freschezza).
4. **Given** il pannello aperto, **When** l'utente cambia vista da tastiera, **Then** la vista selezionata appare senza riavvio.

---

### User Story 2 - Filtrare per intervallo temporale (Priority: P2)

L'utente vuole restringere i report a un **intervallo**: «ultimi 7 giorni», «ultime 24 ore», oppure
«tutto». Da tastiera cambia il preset e i report si aggiornano su quella finestra.

**Why this priority**: rende i report **utili** (il «quanto ho speso questa settimana» richiede la
finestra settimanale); senza, si vede solo l'aggregato totale.

**Independent Test**: con eventi distribuiti nel tempo, verificare che i report calcolati su una
finestra (`since`/`until`) includano solo gli eventi di quella finestra.

**Acceptance Scenarios**:

1. **Given** eventi su 30 giorni, **When** si seleziona «ultimi 7 giorni», **Then** i report riflettono solo gli eventi degli ultimi 7 giorni.
2. **Given** un preset selezionato, **When** è attivo, **Then** il pannello indica quale intervallo si sta guardando.

---

### User Story 3 - Degradazione onesta e coerenza col pannello (Priority: P3)

I report vivono nello **stesso pannello** della vista live (stessa app, stessa navigazione). Quando una
fonte manca — nessun dato (persistenza spenta), o un valore non disponibile (es. la stima in valuta, che
è una capacità separata) — il pannello mostra un messaggio chiaro o ripiega su ciò che ha (es. i token
grezzi), **senza** crash.

**Why this priority**: continuità d'esperienza e robustezza; un report mancante non deve rompere il
pannello.

**Independent Test**: report su store vuoto → viste a zeri con messaggio «nessun dato»; verifica che il
pannello (con i report) sia lo stesso di F3 (un'unica superficie).

**Acceptance Scenarios**:

1. **Given** persistenza spenta/store vuoto, **When** si apre una vista report, **Then** mostra uno stato vuoto onesto, non un errore.
2. **Given** la stima in valuta non disponibile, **When** si apre la vista costo, **Then** mostra i token (ripiego onesto), non un crash.

---

### Edge Cases

- **Store vuoto / persistenza spenta:** ogni vista mostra zeri + messaggio, mai crash.
- **Intervallo senza eventi:** vista vuota per quell'intervallo.
- **Componente d'interfaccia assente:** stesso messaggio azionabile del pannello (la dipendenza è la
  stessa di F3).
- **Serie molto lunga:** la vista resta leggibile (riassume/limita la serie mostrata).
- **Coerenza:** report e vista live convivono nella stessa app, stessa navigazione da tastiera.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il pannello MUST offrire **viste di report sfogliabili** per: **cache** (hit/miss nel
  tempo + totali + risparmio stimato), **costo** (token per provider e per intervallo), **salute** del
  corpus (ultimo stato + **freschezza** = da quanto non si re-indicizza).
- **FR-002**: L'utente MUST poter **navigare tra le viste** (e la vista live) da tastiera, senza riavvio.
- **FR-003**: L'utente MUST poter selezionare un **intervallo temporale** tra preset (almeno: tutto /
  ultimi 7 giorni / ultime 24 ore); i report MUST riflettere la finestra selezionata.
- **FR-004**: Il pannello MUST **indicare** l'intervallo correntemente selezionato.
- **FR-005**: Le viste MUST essere **consumatori sottili** dei report già calcolati (servizio di
  aggregazione): nessuna logica di aggregazione nel pannello.
- **FR-006**: Quando non ci sono dati (persistenza spenta o intervallo vuoto), una vista MUST mostrare
  uno **stato vuoto onesto**, non un errore.
- **FR-007**: Quando la **stima in valuta** non è disponibile, la vista costo MUST **ripiegare** sui
  token (degradazione onesta), senza crash.
- **FR-008**: Le viste report MUST condividere il **medesimo pannello** della vista live (un'unica
  superficie, stessa navigazione), e il medesimo prerequisito del componente d'interfaccia opzionale.
- **FR-009**: La **logica di resa** di ogni report MUST essere verificabile **senza** un terminale
  interattivo (separata dal rendering del componente d'interfaccia).
- **FR-010**: Le viste MUST essere in **sola lettura** e funzionare su **qualunque progetto ospite**.
- **FR-011**: Le viste MUST mostrare **solo metriche** (mai contenuto grezzo).

### Key Entities *(include if feature involves data)*

- **Vista di report**: una resa leggibile e sfogliabile di un report (cache/costo/salute) su un
  intervallo; deriva dai report del servizio di aggregazione.
- **Intervallo selezionato**: la finestra temporale corrente (preset) applicata a tutte le viste report.
- **Freschezza**: il tempo trascorso dall'ultima indicizzazione (derivabile dai dati conservati; il
  confronto con le modifiche del repository resta fuori ambito).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Le viste cache/costo/salute mostrano valori coerenti al 100% con gli eventi conservati
  (verificabile sulle funzioni di resa con dati di test).
- **SC-002**: Selezionando un intervallo (es. 7 giorni), i report includono solo gli eventi di quella
  finestra (verificabile).
- **SC-003**: L'utente può passare tra le viste e cambiare intervallo da tastiera, senza riavvio.
- **SC-004**: Con store vuoto/persistenza spenta, ogni vista mostra uno stato vuoto onesto nel 100% dei
  casi, senza eccezioni.
- **SC-005**: Con la stima in valuta assente, la vista costo mostra i token (nessun crash).
- **SC-006**: La logica di resa è verificabile offline e senza terminale reale.
- **SC-007**: Le viste operano su **≥2** progetti ospite diversi senza modifiche al corpo, in sola
  lettura.

## Assumptions

- **Dipendenza da F1+F2+F3 (già su master):** le viste rendono i **report** di F2; condividono il
  pannello e il componente d'interfaccia opzionale di F3. Non raccolgono né aggregano dati.
- **Preset di intervallo:** almeno tutto / 7 giorni / 24 ore; il default è «tutto». Un intervallo libero
  da-data/a-data è una rifinitura possibile, fuori MVP.
- **Freschezza = tempo dall'ultima indicizzazione**, derivato dai dati conservati; il confronto con lo
  stato del repository (host-specifico) resta **fuori ambito**.
- **Stima in valuta (€):** è una capacità **separata** (FEAT-007) che si appoggia agli aggregati di
  token; qui, se assente, si mostrano i token (ripiego).
- **Export dei report** (CSV/Markdown): fuori MVP (eventuale Could successivo).
- **Fuori ambito:** export verso strumenti esterni, modalità web, conversione € — feature successive
  o separate.
