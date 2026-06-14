# Feature Specification: Servizio di aggregazione e report dell'osservabilità

**Feature Branch**: `021-osservabilita-report`

**Created**: 2026-06-14

**Status**: Draft

**Input**: FEAT-002 dell'epica osservabilità — fonte requisiti `requirements/osservabilita/aggregazione-report/requirements.md`. Trasformare gli eventi grezzi conservati dallo strato persistente (F1, già su master) in **report leggibili**: quanto risparmia la cache, quanto si è speso, qual è la salute del corpus, le latenze e l'affidabilità. È il servizio nel core che precede il pannello (F3/F4 leggeranno questi report).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Quanto mi fa risparmiare la cache (missing vs hit) (Priority: P1)

Chi gestisce un indice vuole sapere se e quanto la cache degli embedding sta aiutando. Dagli eventi
conservati (gli eventi di cache con conteggi hit/miss), il servizio produce un **report cache**: quanti
risultati sono arrivati dalla cache vs ricalcolati, **nel tempo**, e una **stima del risparmio** (gli
hit sono token che non si sono pagati). È la domanda esplicita più sentita («missing vs hit») resa una
risposta.

**Why this priority**: è il valore portante e la richiesta diretta dell'utente; è anche ciò che dà
senso, a posteriori, all'aver acceso la persistenza. Funziona da solo (MVP) sui soli eventi di cache.

**Independent Test**: con un insieme di eventi cache conservati (simulati), chiedere il report cache su
un intervallo e verificare hit/miss aggregati e la stima di risparmio in token; tutto offline.

**Acceptance Scenarios**:

1. **Given** eventi di cache conservati su un arco temporale, **When** si chiede il report cache su un intervallo, **Then** si ottengono i totali hit/miss e l'andamento per intervallo (es. per giorno).
2. **Given** N hit registrati, **When** si chiede il risparmio, **Then** è restituita una **stima** dei token non consumati grazie agli hit (con il caveat dichiarato sotto).
3. **Given** nessun evento di cache nell'intervallo, **When** si chiede il report, **Then** il risultato è un report **vuoto esplicito** (zero hit/zero miss), non un errore.

---

### User Story 2 - Quanto sto spendendo (consumo di token) (Priority: P2)

Chi paga un provider vuole vedere il **consumo**. Dagli eventi di embedding (che riportano i token), il
servizio produce un **report costo**: token **cumulativi per provider**, aggregati per intervallo
(es. per giorno) e — utile — per **singola indicizzazione**. La conversione in valuta è una capacità
separata che si appoggerà a questi aggregati; qui si producono i numeri di consumo.

**Why this priority**: «quanto spendo» è la seconda domanda più sentita; insieme a US1 chiude il quadro
costo/risparmio.

**Independent Test**: con eventi di embedding conservati (con token), chiedere il report costo e
verificare i token aggregati per provider e per intervallo.

**Acceptance Scenarios**:

1. **Given** eventi di embedding con token su più giorni e provider, **When** si chiede il report costo, **Then** i token sono aggregati correttamente per provider e per intervallo.
2. **Given** eventi senza token (provider che non li riporta), **When** si aggrega, **Then** quei contributi sono esclusi dal totale token (non contati come zero arbitrario) senza errori.

---

### User Story 3 - Salute, latenze e affidabilità (Priority: P3)

Chi osserva il sistema vuole un quadro di **salute**: l'ultima fotografia del corpus (quanti
documenti/chunk, dimensione dell'embedding) e il suo andamento; le **latenze** delle operazioni
(tempo tipico e di coda, es. mediana e 95° percentile) per indicizzazione e ricerca; e l'**affidabilità**
(quanti errori/ritentativi del provider, con quale frequenza si è attivata l'astensione di bassa
confidenza).

**Why this priority**: completa l'osservabilità oltre il costo; utile per diagnosi, ma secondario
rispetto alla domanda costo/risparmio.

**Independent Test**: con eventi `index`/`retrieve`/errore/ritentativo/bassa-confidenza conservati,
verificare i conteggi del corpus dall'ultimo `index`, i percentili di latenza per operazione, e i tassi
di errore/astensione.

**Acceptance Scenarios**:

1. **Given** eventi `index` su più momenti, **When** si chiede la salute del corpus, **Then** si ottiene la fotografia dell'**ultimo** index (documenti/chunk/dimensione) e l'andamento nel tempo.
2. **Given** eventi con tempi di esecuzione per operazione, **When** si chiedono le latenze, **Then** si ottengono mediana e 95° percentile per operazione.
3. **Given** eventi di errore/ritentativo/bassa-confidenza, **When** si chiede l'affidabilità, **Then** si ottengono i conteggi e i tassi corrispondenti.

---

### Edge Cases

- **Store assente/persistenza mai attivata:** un report richiesto senza eventi conservati restituisce un
  report **vuoto esplicito** (zeri), non un errore (degradazione onesta).
- **Intervallo senza eventi:** report vuoto per quell'intervallo.
- **Stima del risparmio e dedup:** il risparmio in token dagli hit è una **stima** — la deduplicazione
  in-call (introdotta con la cache) fa sì che il rapporto token/elemento non sia esatto; il report lo
  dichiara come stima, non come misura esatta (vedi Assumptions).
- **Eventi di tipi futuri:** nuovi tipi di evento non rompono i report esistenti (vengono ignorati dai
  report che non li riguardano).
- **Determinismo:** lo stesso insieme di eventi produce sempre lo **stesso** report (ripetibile).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il sistema MUST produrre un **report cache** dagli eventi conservati: totali hit/miss e
  andamento per intervallo temporale.
- **FR-002**: Il sistema MUST stimare il **risparmio** associato agli hit della cache (token non
  consumati), dichiarandolo come **stima** (non misura esatta).
- **FR-003**: Il sistema MUST produrre un **report costo**: token cumulativi **per provider**, aggregati
  per intervallo temporale e per singola indicizzazione.
- **FR-004**: Il sistema MUST escludere dal totale token i contributi di eventi privi di token (non
  contarli come zero), senza errori.
- **FR-005**: Il sistema MUST produrre un **report di salute del corpus**: l'ultima fotografia
  (documenti/chunk/dimensione embedding) e il suo andamento nel tempo.
- **FR-006**: Il sistema MUST produrre le **latenze** per operazione (almeno mediana e 95° percentile)
  per indicizzazione e ricerca.
- **FR-007**: Il sistema MUST produrre l'**affidabilità**: conteggi di errori e ritentativi del provider
  e tasso di astensioni di bassa confidenza.
- **FR-008**: Ogni report MUST accettare un **intervallo temporale** (inizio/fine, entrambi opzionali) e
  una **granularità di raggruppamento** temporale.
- **FR-009**: I report MUST essere **deterministici**: lo stesso insieme di eventi produce lo stesso
  report (Principio VI).
- **FR-010**: Quando non ci sono eventi rilevanti (store assente o intervallo vuoto), un report MUST
  restituire un risultato **vuoto esplicito** (zeri), non un errore (degradazione onesta).
- **FR-011**: Il servizio MUST leggere gli eventi **solo** attraverso lo strato di persistenza esistente
  (non re-implementa la persistenza) e MUST NOT produrre interfaccia utente (è un servizio del core).
- **FR-012**: I report MUST aggregare **solo** i dati conservati (metriche), mai contenuto grezzo
  (privacy-by-default ereditata).

### Key Entities *(include if feature involves data)*

- **Report**: una vista aggregata e leggibile derivata dagli eventi conservati (cache, costo, salute,
  latenze, affidabilità). Ha un intervallo temporale e una granularità di raggruppamento.
- **Punto di serie temporale**: un valore aggregato per un intervallo (es. token del giorno, hit/miss
  del giorno) — l'unità con cui i report mostrano un andamento.
- **Stima di risparmio**: i token non consumati attribuiti agli hit della cache, dichiarata come stima.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Dato un insieme di eventi cache conservati, il report cache riporta hit/miss totali e per
  intervallo coerenti al 100% con gli eventi (verificabile a mano sui dati di test).
- **SC-002**: Il report costo aggrega i token per provider e per intervallo con totale pari alla somma
  dei token degli eventi nell'intervallo.
- **SC-003**: Il report di salute riporta la fotografia dell'**ultimo** evento di indicizzazione e i
  percentili di latenza richiesti (mediana, 95°).
- **SC-004**: Un report richiesto senza eventi rilevanti restituisce un risultato vuoto esplicito nel
  100% dei casi, senza eccezioni.
- **SC-005**: Lo stesso insieme di eventi produce report **identici** su esecuzioni ripetute
  (determinismo).
- **SC-006**: Tutti i report sono verificabili **offline** (eventi simulati nello store), senza rete.
- **SC-007**: Nessun report espone contenuto grezzo o segreti (solo metriche aggregate).

## Assumptions

- **Dipendenza da F1 (già su master):** gli eventi sono letti dallo strato di persistenza
  dell'osservabilità (feature 020); F2 non li raccoglie né li persiste.
- **Granularità temporale di default = giorno**, configurabile (la scelta dei preset è dettaglio di
  design); i report accettano un intervallo libero.
- **Stima del risparmio:** calcolata dagli hit usando il rapporto token/elemento osservato sugli eventi
  di embedding; è una **stima** per via della deduplicazione in-call della cache — dichiarata come tale,
  mai come misura esatta.
- **Provider senza token:** alcuni provider non riportano i token; i loro eventi contribuiscono ai
  conteggi (operazioni) ma non al totale token (assenza, non zero).
- **Freschezza del corpus vs modifiche del repo:** richiede informazioni host-specifiche (stato del
  repository) → **fuori ambito** di F2; al più si espone il *quando* dell'ultimo evento di indicizzazione
  (il confronto con le modifiche del repo è una capacità separata).
- **Fuori ambito:** la presentazione (pannello TUI F3/F4), l'export verso strumenti esterni (F5), la
  conversione in valuta € (FEAT-007 — F2 fornisce gli aggregati di token su cui si appoggia), e la
  persistenza (F1).
