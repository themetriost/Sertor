# Feature Specification: Server MCP di produzione (`sertor_mcp`)

**Feature Branch**: `spec/007-mcp-sertor-core`

**Created**: 2026-06-06

**Status**: Draft

**Input**: `requirements/sertor-core/mcp/requirements.md` (FEAT-MCP, epica sertor-core)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - L'agente interroga la codebase via tool MCP (Priority: P1)

Un agente LLM (es. Claude Code) avvia il server MCP del progetto e ottiene **tre strumenti di
ricerca** sul corpus indicizzato: uno per il **codice**, uno per la **documentazione**, uno
**combinato**. L'agente invoca il tool adatto con una query in linguaggio naturale e riceve una lista
di risultati pertinenti — con path del file, tipo (codice/doc), score e un'anteprima — sufficienti a
citare le fonti nella sua risposta.

**Why this priority**: È la capacità stessa della feature; senza i tre tool di ricerca non c'è
superficie MCP. Da sola costituisce l'MVP utile (un agente può interrogare il progetto).

**Independent Test**: Con un indice del corpus configurato disponibile, avviare il server, invocare
`search_code` / `search_docs` / `search_combined` con una query nota e verificare che ciascuno
restituisca risultati strutturati, con `search_code` ristretto al codice, `search_docs` alla doc, e
`search_combined` a entrambi.

**Acceptance Scenarios**:

1. **Given** un corpus indicizzato e il server avviato, **When** il client elenca i tool, **Then**
   vede registrati `search_code`, `search_docs`, `search_combined`.
2. **Given** il server avviato, **When** il client invoca `search_code("...")`, **Then** riceve una
   lista di risultati di **solo codice**, ciascuno con path, tipo, id chunk, score e anteprima.
3. **Given** il server avviato, **When** il client invoca `search_docs("...")`, **Then** riceve
   risultati di **sola documentazione**.
4. **Given** il server avviato, **When** il client invoca `search_combined("...")`, **Then** riceve
   risultati da **codice e doc** insieme.
5. **Given** un risultato con testo lungo, **When** viene restituito, **Then** l'anteprima è troncata
   e marcata come tale.

---

### User Story 2 - Comportamento robusto quando l'indice manca o una ricerca fallisce (Priority: P2)

Chi usa il server (agente o manutentore) può lanciarlo anche **prima** che esista un indice per il
corpus configurato, o su un corpus vuoto, senza che il server si interrompa. In quella condizione i
tool restituiscono **nessun risultato** e una segnalazione comprensibile; un eventuale errore interno
al motore viene riportato in modo leggibile e il server resta operativo per le chiamate successive.

**Why this priority**: Un server che crasha quando l'indice non c'è è inusabile in pratica (l'indice
viene costruito separatamente, può non esserci ancora). Il degrado pulito è condizione d'uso reale.

**Independent Test**: Avviare il server **senza** un indice per il corpus configurato, invocare un
tool e verificare che restituisca lista vuota + warning, senza eccezioni non gestite, e che una
seconda invocazione funzioni ancora.

**Acceptance Scenarios**:

1. **Given** nessun indice per il corpus configurato, **When** il client invoca un tool, **Then**
   riceve una lista vuota e una segnalazione, e il server resta attivo.
2. **Given** un errore interno al motore durante una ricerca, **When** il tool viene invocato,
   **Then** il client riceve un errore leggibile e il server resta disponibile per le chiamate
   successive (nessuno stato parziale).

---

### User Story 3 - Configurazione host-agnostica e sostituzione del server del prototipo (Priority: P3)

Il manutentore può puntare il server a un **corpus**, **backend** e **provider** diversi cambiando
**solo la configurazione** (nessuna modifica al codice), e il binding del repository punta al server
**di produzione** invece che a quello del prototipo. Il default di prodotto è il corpus `sertor`.

**Why this priority**: Rende reale la portabilità (Principio X) e chiude il disallineamento del
binding attuale (che interroga il corpus congelato del prototipo). Importante ma costruibile dopo che
i tool funzionano.

**Independent Test**: Cambiare corpus/backend nella configurazione e verificare che il server
interroghi la destinazione indicata senza modifiche al codice; verificare che il binding del progetto
avvii il server di produzione e non più quello del prototipo.

**Acceptance Scenarios**:

1. **Given** una configurazione che seleziona un corpus diverso, **When** il server è avviato,
   **Then** le ricerche operano su quel corpus senza modifiche al codice.
2. **Given** il binding del progetto, **When** un client MCP lo usa, **Then** avvia il server di
   produzione (`python -m sertor_mcp.server`) e non il server del prototipo.

---

### Edge Cases

- **Indice assente**: lista vuota + warning, nessun crash (US2).
- **Corpus configurato diverso dal default**: il server lo rispetta (US3).
- **Testo del risultato molto lungo**: anteprima troncata e marcata (FR-011).
- **`k` non fornito**: si usa il default del motore.
- **Tool di grafo/ibrido richiesti** (es. `find_symbol`): non esistono in questo MVP; i metadati del
  server elencano solo i tool disponibili così l'agente non li invoca a vuoto.
- **SDK MCP non installato**: è una dipendenza del solo server (extra opzionale); l'assenza riguarda
  l'avvio del server, non l'uso della libreria core.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il sistema MUST esporre il retrieval del core come tool MCP utilizzabili da un client
  MCP qualunque, sul trasporto stdio. *(REQ-001, REQ-030)*
- **FR-002**: Il sistema MUST registrare esattamente tre tool di ricerca — `search_code`,
  `search_docs`, `search_combined` — ognuno con una query testuale e un conteggio risultati `k`
  opzionale. *(REQ-002)*
- **FR-003**: Il sistema MUST restituire, per `search_code`, risultati ristretti al **codice**; per
  `search_docs`, alla **documentazione**; per `search_combined`, a **entrambi**. *(REQ-003/004/005)*
- **FR-004**: Il sistema MUST esporre **solo** tool di lettura/ricerca e MUST NOT esporre tool che
  modificano indice, corpus o filesystem. *(REQ-006)*
- **FR-005**: Il sistema MUST delegare tutto il retrieval alla capacità di ricerca del core, senza
  reimplementare ricerca, ranking o accesso a store/embeddings (strato sottile). *(REQ-010)*
- **FR-006**: Il sistema MUST costruire la capacità di retrieval **una volta** dalla configurazione e
  riusarla tra le invocazioni. *(REQ-011)*
- **FR-007**: Il sistema MUST ottenere provider di embeddings, backend e corpus dalla configurazione
  centralizzata, senza valori o percorsi dell'ospite scritti nel codice. *(REQ-020)*
- **FR-008**: Il sistema MUST puntare per default al corpus di prodotto `sertor`, sostituendo il
  valore legacy del prototipo. *(REQ-021)*
- **FR-009**: Il sistema MUST operare su un backend/corpus diverso scelto in configurazione senza
  modifiche al codice. *(REQ-022)*
- **FR-010**: Ogni tool MUST restituire una lista di risultati strutturati con almeno: path,
  tipo sorgente (codice/doc), id chunk, score, anteprima testuale; con set di campi **identico** tra
  i tre tool. *(REQ-040/042)*
- **FR-011**: Quando il testo di un risultato supera la lunghezza d'anteprima, il sistema MUST
  troncare l'anteprima e marcarla come troncata. *(REQ-041)*
- **FR-012**: Se non esiste un indice per il corpus configurato, il sistema MUST restituire una lista
  vuota e una segnalazione, senza errore non gestito né arresto del server. *(REQ-050)*
- **FR-013**: Se una ricerca fallisce internamente, il sistema MUST riportare un errore leggibile al
  client e MUST restare disponibile per le invocazioni successive. *(REQ-051)*
- **FR-014**: Il sistema MUST fornire metadati/istruzioni che guidano il client nella scelta del tool
  (codice/doc/combinato) e nella citazione dei file. *(REQ-032)*
- **FR-015**: Il binding MCP del repository MUST puntare al server di produzione e MUST NOT più
  riferire il server del prototipo. *(REQ-031)*
- **FR-016**: La dipendenza dall'SDK MCP MUST essere confezionata come extra opzionale isolato, così
  che installare la libreria core senza quell'extra non installi le dipendenze del server. *(REQ-060)*
- **FR-017**: Il sistema SHOULD consentire di registrare tool aggiuntivi (grafo — FEAT-005; ibrido —
  FEAT-004) senza modificare né rompere i tre tool esistenti. *(REQ-061)*

### Key Entities *(include if feature involves data)*

- **Risultato di ricerca**: un singolo hit restituito da un tool; attributi: path del documento, tipo
  sorgente (codice/doc), id del chunk, score di pertinenza, anteprima testuale (troncata se lunga).
- **Configurazione**: i valori che determinano il comportamento del server — corpus, backend,
  provider — provenienti dalla fonte centralizzata, non dal codice.
- **Tool MCP**: lo strumento esposto al client (`search_code` / `search_docs` / `search_combined`),
  con la propria descrizione/uso.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un client MCP che avvia il server vede **≥1** tool di retrieval e lo invoca ottenendo
  risultati strutturati su una query nota. *(CS-1)*
- **SC-002**: Sono disponibili e distinti **3** tool (codice / doc / combinato), ciascuno con il
  proprio filtro osservabile. *(CS-2)*
- **SC-003**: I tool non duplicano la logica del core: rimossa la ricerca del core, i tool non
  producono risultati (verificabile con un doppio mock). *(CS-3)*
- **SC-004**: Lo stesso server opera su corpus/backend/provider diversi cambiando **solo** la
  configurazione, senza modifiche al codice. *(CS-4)*
- **SC-005**: Con un indice del corpus di produzione costruito, una query nota su Sertor restituisce
  risultati pertinenti **sia** dai sorgenti **sia** dalla documentazione. *(CS-5)*
- **SC-006**: Con l'indice assente, l'invocazione di un tool **non** fa crashare il server e
  restituisce nessun risultato + segnalazione. *(CS-6)*
- **SC-007**: Dopo la feature, il binding del progetto avvia il server di produzione e **non** più
  quello del prototipo. *(CS-7)*
- **SC-008**: Installare la libreria core senza l'extra del server **non** installa l'SDK MCP. *(CS-8)*

## Assumptions

- **Indice fuori scope**: esiste o sarà costruito separatamente un indice per il corpus configurato;
  la **costruzione** dell'indice è del nucleo/CLI, non di questa feature. La feature **consuma** un
  indice esistente.
- **DA-MCP1 (naming corpus)**: il corpus `sertor` si imposta via configurazione (binding/ambiente),
  **senza** cambiare il valore di default interno del core in questa feature.
- **DA-MCP4 (forma dei tool)**: si mantengono **tre tool distinti** (più chiari per l'agente),
  anziché un unico tool parametrico.
- **DA-MCP2 (tool di health)**: **non** incluso nell'MVP; la condizione "indice mancante" è resa
  osservabile da segnalazione + log.
- **DA-MCP3 (cap su `k`)**: **nessun** cap rigido nell'MVP; vale il default del motore e l'anteprima
  è comunque troncata.
- **Scope dei tool**: i tool di navigazione del grafo (`find_symbol`/`who_calls`/`related_docs`/
  `get_context`) e il reranking ibrido sono **fuori ambito** (tornano con FEAT-005 / FEAT-004).
- **Operazioni Wiki via MCP**: fuori ambito; qui si espone **solo il retrieval**.
- **Trasporto**: solo **stdio**; il client MCP gestisce il ciclo di vita del processo del server.
- **Esiste un'implementazione di riferimento** sul branch `feat/mcp-sertor-core` (commit `53b8e43`),
  pulita e compatibile con master, usata come **riferimento** (non merge dei sorgenti).
