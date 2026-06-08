# Feature Specification: Meccanica del log del wiki

**Feature Branch**: `spec/008-meccanica-log`

**Created**: 2026-06-08

**Status**: Draft

**Input**: Requisiti EARS approvati in `requirements/sertor-core/meccanica-log/requirements.md` (estende FEAT-003-D `wiki_tools`).

## User Scenarios & Testing *(mandatory)*

Gli "utenti" qui sono i consumatori del nucleo wiki: il **flusso principale (LLM)** e l'agente **curator**
che registrano voci di log, e l'**hook** che rileva il lavoro pendente. Il confine è netto: l'LLM produce il
**contenuto** della voce (formato `log-craft`); la meccanica deterministica fa il **piazzamento**.

### User Story 1 - Append di una voce curata nel file del giorno (Priority: P1)

Chi registra una voce di log fornisce la voce già formattata (heading + lead + bullet + riga d'esito) e la
meccanica la scrive nel file della **data della voce** (es. `wiki/log/2026-06-08.md`), creandolo se non
esiste. Il file monolitico non cresce più.

**Why this priority**: è il cuore della feature (rotazione implicita + write-back curato). Da sola ferma la
crescita illimitata del log e sposta la meccanica del piazzamento dall'LLM al deterministico.

**Independent Test**: appendere una voce in un wiki di test e verificare che compaia, **byte-identica** alla
forma `log-craft`, nel file della sua data e in nessun altro; ri-appenderla e verificare che non si duplichi.

**Acceptance Scenarios**:

1. **Given** un wiki configurato e nessun file per la data odierna, **When** si appende una voce curata,
   **Then** viene creato il file del giorno con un header valido e la voce vi compare integra.
2. **Given** un file del giorno già esistente con una voce, **When** si appende una seconda voce diversa,
   **Then** la seconda voce è aggiunta in coda, senza toccare la prima.
3. **Given** una voce già presente nel file del giorno, **When** si ri-appende la stessa voce
   (stesso `data+op+titolo`), **Then** non viene scritto nulla (idempotenza).

---

### User Story 2 - Rilevazione del lavoro pendente preservata (Priority: P1)

L'hook che avvisa del lavoro non registrato deve continuare a funzionare identico dopo la rotazione: il
conteggio del pendente si basa sulla **partizione di log più recente**, non più su un file unico.

**Why this priority**: rompere questa rilevazione è una **regressione** silenziosa (l'hook diventerebbe cieco
o rumoroso). Va garantita insieme alla US1.

**Independent Test**: con partizioni di log su più giorni, confrontare il conteggio del pendente con quello
prodotto dal comportamento monolitico precedente sugli stessi dati: deve coincidere.

**Acceptance Scenarios**:

1. **Given** più file-giorno di log e file-sorgente modificati dopo l'ultima voce, **When** si rileva il
   lavoro pendente, **Then** il conteggio è identico a quello che darebbe il log monolitico equivalente.
2. **Given** nessuna partizione di log, **When** si rileva il pendente, **Then** tutto è considerato pendente
   (parità col comportamento a registro assente).
3. **Given** la rilevazione post-rotazione, **When** l'hook la consuma, **Then** il contratto e l'output
   osservato dall'hook non cambiano.

---

### User Story 3 - Split retroattivo dello storico (Priority: P2)

Un'operazione una-tantum trasforma il `log.md` monolitico esistente in file giornalieri, una partizione per
data distinta, preservando ordine e contenuto delle voci.

**Why this priority**: porta lo storico nel nuovo schema (coerenza con la rotazione), ma non blocca l'uso
quotidiano (US1/US2 funzionano anche senza). È un'operazione esplicita e isolata.

**Independent Test**: eseguire la migrazione su un `log.md` di esempio con voci di più date e verificare che
ogni data abbia il suo file con le voci nell'ordine originale; rieseguire e verificare il no-op.

**Acceptance Scenarios**:

1. **Given** un `log.md` con voci di N date distinte, **When** si esegue la migrazione, **Then** si ottengono
   N file-giorno con tutte le voci, nell'ordine originale, senza perdite.
2. **Given** più voci con la stessa data, **When** si migra, **Then** finiscono tutte nella stessa partizione,
   nell'ordine originale.
3. **Given** una migrazione già eseguita, **When** la si riesegue, **Then** è un no-op (idempotente, non
   distruttiva).

---

### User Story 4 - Indice navigabile delle partizioni (Priority: P3)

Un indice dentro la directory di log elenca i giorni disponibili, così il log resta navigabile mentre le
partizioni crescono nel tempo.

**Why this priority**: migliora la navigabilità ma non è necessario al funzionamento; è un complemento.

**Independent Test**: dopo la creazione di alcune partizioni, verificare che l'indice elenchi tutti i giorni
presenti e si aggiorni in modo idempotente.

**Acceptance Scenarios**:

1. **Given** alcune partizioni giornaliere, **When** si aggiorna l'indice, **Then** elenca tutti i giorni
   presenti, ordinati.
2. **Given** un indice già aggiornato, **When** lo si rigenera senza nuove partizioni, **Then** non cambia.

### Edge Cases

- Voce con data esplicita (`on_date`) diversa da oggi → finisce nella partizione di quella data.
- File del giorno presente ma senza header valido → l'append non corrompe il file (header garantito).
- `log.md` storico assente al momento della migrazione → no-op senza errore.
- Voce il cui heading non rispetta lo schema datato → errore esplicito (non si indovina la partizione).
- Profilo in **modalità file-unico** (back-compat) → comportamento odierno invariato, rotazione disattivata.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il sistema MUST scrivere ogni nuova voce di log nel file di partizione corrispondente alla
  **data della voce** (un file per giorno).
- **FR-002**: Il sistema MUST creare il file di partizione mancante (con header/frontmatter valido) prima di
  appendere, senza sollevare errore (creazione idempotente).
- **FR-003**: Il sistema MUST derivare la directory di log e il pattern di naming giornaliero (data ISO) dalla
  configurazione dell'ospite, senza percorsi hard-coded.
- **FR-004**: L'operazione di append MUST accettare il **corpo curato completo** della voce e scriverlo
  **senza appiattirlo né riformattarlo**.
- **FR-005**: Il sistema MUST esporre l'operazione di append via la CLI con un **contratto strutturato e
  versionato**.
- **FR-006**: L'append MUST essere **idempotente**; l'identità di una voce è il suo **heading**
  (`data + op + titolo`): un secondo append con lo stesso heading non scrive.
- **FR-007**: L'operazione di append MUST riportare l'esito (se ha scritto, quale partizione, eventuale
  creazione del file).
- **FR-008**: Il sistema MUST determinare l'àncora del lavoro pendente dalla **partizione più recente**,
  mantenendo **parità di conteggio** col comportamento a file unico e **senza** cambiare il contratto né
  l'output osservato dall'hook.
- **FR-009**: Il sistema MUST fornire un'operazione una-tantum, **non distruttiva e idempotente**, che
  **splitta retroattivamente** il `log.md` monolitico in file giornalieri (una partizione per data distinta),
  preservando ordine e contenuto delle voci.
- **FR-010**: Il sistema MUST mantenere un **indice navigabile delle partizioni** dentro la directory di log,
  aggiornato in modo idempotente.
- **FR-011**: Where la configurazione indica la **modalità a file unico**, il sistema MUST conservare il
  comportamento attuale (rotazione disattivata) per retro-compatibilità.
- **FR-012**: Tutte le operazioni MUST funzionare **offline**, fallire con **errori espliciti** su
  configurazione assente/malformata, e non lasciare stati parziali.

### Key Entities *(include if feature involves data)*

- **Partizione di log giornaliera**: un file che raccoglie tutte le voci di una stessa data; ha un header
  valido; identità = la sua data.
- **Voce di log**: heading datato (`## [YYYY-MM-DD] <op> | <titolo>`) + corpo curato (lead, bullet, riga
  d'esito, formato `log-craft`); identità per l'idempotenza = l'heading.
- **Indice delle partizioni**: elenco navigabile dei giorni disponibili, dentro la directory di log.
- **Configurazione del log (profilo ospite)**: directory di log, naming giornaliero, modalità (rotazione vs
  file unico) — l'unica fonte di specificità.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Una voce appesa compare nel file della **sua data** e in **nessun altro**.
- **SC-002**: Una voce scritta dalla meccanica è **byte-identica** a una scritta a mano secondo `log-craft`
  (zero riformattazione).
- **SC-003**: Dopo la rotazione, il conteggio del lavoro pendente è **identico** a quello del log monolitico
  equivalente, e l'hook non cambia comportamento (0 regressioni).
- **SC-004**: Ri-appendere una voce identica produce **0 duplicati** e **0 modifiche** ai file.
- **SC-005**: Lo split retroattivo produce **una partizione per data distinta** senza perdere voci; rieseguito
  è un **no-op**.
- **SC-006**: Cambiando **solo** la configurazione dell'ospite, la stessa logica opera su un progetto diverso
  (host-agnostico).
- **SC-007**: Tutte le operazioni completano **offline** (nessuna rete).

## Assumptions

- Le voci di log seguono lo schema con heading datato `## [YYYY-MM-DD] <op> | <titolo>` (convenzione
  `log-craft`): la data di partizione si deriva dall'heading.
- Il **contenuto** curato della voce è prodotto dal flusso LLM (`log-craft` resta invariato e fuori scope).
- Lo storico `log.md` usa lo stesso schema di heading datato (necessario per lo split retroattivo).
- La feature estende `wiki_tools` (FEAT-003-D) e ne rispetta i vincoli: host-agnostico (Principio X), stdlib,
  offline, idempotente, errori espliciti, contratti versionati; Constitution Check 10/10 atteso.
- Il write-back dell'**indice** (`upsert_index`) e la rotazione di altri file sono **fuori scope**.
