# Feature Specification: Motore RAG vettoriale (baseline)

**Feature Branch**: `spec/002-rag-baseline`

**Created**: 2026-05-31

**Status**: Draft

**Input**: Decomposizione di `requirements/sertor-core/rag-baseline/requirements.md` (Deriva da
FEAT-002 dell'epica `sertor-core`). Il documento EARS è la fonte di dettaglio. Contesto generale:
`requirements/sertor-core/epic.md`. **Dipende da FEAT-001** (nucleo di retrieval condiviso). Vincoli
architetturali: `.specify/memory/constitution.md` (Principi I, II, IV, V, VI, IX).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Creare un indice vettoriale da una codebase (Priority: P1)

Come maintainer, costruisco un **indice vettoriale** sul codice e la documentazione di un progetto,
così da renderlo interrogabile in linguaggio naturale. Il motore si appoggia al nucleo condiviso
(ingestione, chunking, embeddings, vector store) e non lo ridefinisce.

**Why this priority**: è la **capacità minima di "creare un RAG" interrogabile** (CS-1), la ragione
d'essere della prima release del core.

**Independent Test**: dato il path di una codebase e un provider di embeddings configurato, eseguire
l'indicizzazione e verificare che venga prodotto un indice persistente contenente i chunk di codice e
doc, con report di chunk totali e dimensione dell'embedding.

**Acceptance Scenarios**:

1. **Given** una codebase e un provider configurato, **When** si esegue l'indicizzazione, **Then** il
   sistema produce un indice vettoriale persistente con tutti i chunk di codice e documentazione.
2. **Given** un'indicizzazione completata, **When** termina, **Then** il sistema riporta il numero
   totale di chunk indicizzati e la dimensione dell'embedding usata.
3. **Given** il provider di embeddings non disponibile durante l'indicizzazione, **When** si verifica
   l'errore, **Then** il sistema annulla l'operazione senza lasciare un indice parziale o corrotto.

### User Story 2 - Interrogare per similarità vettoriale (Priority: P1)

Come agente LLM o maintainer, sottopongo una query testuale e ottengo i **top-k chunk più simili**,
ciascuno con i metadati necessari a citare la fonte (path, tipo, indice del chunk, punteggio, anteprima).

**Why this priority**: l'indice è utile solo se interrogabile; query e indicizzazione insieme
costituiscono il ciclo minimo del motore.

**Independent Test**: con un indice esistente, sottoporre una query nota e verificare che restituisca
i top-k risultati con i metadati richiesti; con `k` specificato dal chiamante.

**Acceptance Scenarios**:

1. **Given** un indice esistente, **When** si sottopone una query, **Then** il sistema calcola
   l'embedding della query con lo **stesso** provider dell'indicizzazione ed esegue una ricerca per
   similarità restituendo i top-k chunk.
2. **Given** una query, **When** il chiamante specifica `k`, **Then** il sistema restituisce esattamente
   fino a `k` risultati; se `k` non è specificato usa un valore di default.
3. **Given** l'indice del provider richiesto inesistente, **When** si interroga, **Then** il sistema
   restituisce un errore chiaro che indica di costruire l'indice prima di interrogare.

### User Story 3 - Idempotenza del re-index (Priority: P2)

Come maintainer, rieseguo l'indicizzazione sullo stesso progetto e ottengo un risultato **stabile**:
l'indice viene ricostruito da zero senza duplicati di chunk.

**Why this priority**: garantisce affidabilità e ripetibilità (Principio VI); abilita aggiornamenti
sicuri senza divergenze.

**Independent Test**: indicizzare due volte la stessa codebase invariata e verificare che l'indice
risultante abbia lo stesso numero di chunk e produca gli stessi risultati alle stesse query.

**Acceptance Scenarios**:

1. **Given** una codebase già indicizzata, **When** si rilancia l'indicizzazione, **Then** il sistema
   scarta l'indice precedente e lo ricostruisce da zero, senza chunk duplicati.
2. **Given** due esecuzioni consecutive su input invariato, **When** si confrontano gli esiti, **Then**
   numero di chunk e risultati alle stesse query coincidono.

### User Story 4 - Valutare la pertinenza del retrieval (Priority: P2)

Come maintainer, misuro la **qualità del retrieval** su un set di ground-truth (query → file attesi),
ottenendo metriche (hit-rate@k, MRR) per sapere se il motore è "fatto" e per confrontare provider.

**Why this priority**: una feature senza misura non è completata, è un prototipo (Principio V); la
misura è il criterio oggettivo di accettazione.

**Independent Test**: fornire un ground-truth e verificare che il sistema calcoli hit-rate@k (per k ∈
{1,3,5,10}) e MRR e ne riporti i valori.

**Acceptance Scenarios**:

1. **Given** un set di valutazione (query → file attesi), **When** si esegue la valutazione, **Then**
   il sistema calcola hit-rate@k e MRR e riporta i risultati.
2. **Given** un provider locale e uno cloud, **When** si valutano entrambi, **Then** i risultati sono
   confrontabili e si accetta una soglia ridotta per il provider locale.

### User Story 5 - Configurabilità del provider e selezione della modalità (Priority: P2)

Come operatore, seleziono il provider di embeddings via configurazione e attivo la **modalità
"baseline"** come una delle modalità RAG, senza influenzare le altre.

**Why this priority**: rende il motore configurabile e componibile nel core multi-modalità (Principi
II e VIII; CS-2).

**Independent Test**: cambiare provider via configurazione senza modifiche al codice; verificare che
l'attivazione della baseline non alteri il comportamento delle altre modalità.

**Acceptance Scenarios**:

1. **Given** la configurazione, **When** si seleziona un provider di embeddings, **Then** il motore lo
   usa senza modifiche al codice.
2. **Given** la modalità baseline attiva, **When** si interroga, **Then** il sistema usa **solo**
   retrieval per similarità vettoriale, senza invocare meccanismi ibridi/grafo/agentici.

### Edge Cases

- Query su indice inesistente → errore esplicito che invita a costruire l'indice (niente risultati vuoti silenziosi).
- Provider non disponibile in fase di query → errore esplicito, nessun risultato parziale/vuoto silenzioso.
- Corpus privo di codice e doc → indicizzazione completa con indice vuoto e avviso, senza errore.
- `k` maggiore dei chunk disponibili → restituisce tutti i risultati disponibili.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il sistema MUST accettare il path di una codebase e un provider di embeddings configurato
  e produrre un indice vettoriale persistente con tutti i chunk di codice e documentazione (usando il
  nucleo di FEAT-001).
- **FR-002**: Alla re-indicizzazione su una codebase già indicizzata, il sistema MUST scartare l'indice
  precedente e ricostruirlo da zero, senza chunk duplicati.
- **FR-003**: Al termine dell'indicizzazione, il sistema MUST riportare il numero di chunk indicizzati
  e la dimensione dell'embedding.
- **FR-004**: Se il provider di embeddings è non disponibile/in errore durante l'indicizzazione, il
  sistema MUST annullare l'operazione senza lasciare un indice parziale o corrotto.
- **FR-005**: Alla sottomissione di una query, il sistema MUST calcolare l'embedding con lo stesso
  provider dell'indicizzazione, eseguire una ricerca per similarità e restituire i top-k chunk.
- **FR-006**: Il sistema MUST includere, per ogni risultato, almeno: path del file, tipo (codice/doc),
  indice del chunk, punteggio di similarità, anteprima testuale.
- **FR-007**: Il sistema MUST accettare un `k` specificato dal chiamante; in assenza, usare un default.
- **FR-008**: Se l'indice del provider richiesto non esiste, il sistema MUST restituire un errore
  chiaro che invita a costruirlo prima di interrogare.
- **FR-009**: Il sistema MUST consentire di calcolare hit-rate@k (k ∈ {1,3,5,10}) e MRR su un
  ground-truth fornito e riportarne i risultati.
- **FR-010**: Il sistema MUST consentire la selezione del provider di embeddings via configurazione,
  senza modifiche al codice.
- **FR-011**: Il sistema MUST esporre la baseline come modalità selezionabile, identificata da un nome
  stabile, indipendente dalle altre modalità.
- **FR-012**: Quando la modalità baseline è attiva, il sistema MUST usare solo retrieval per similarità
  vettoriale, senza invocare meccanismi ibridi/grafo/agentici.
- **FR-013**: Il sistema MUST operare su qualunque codebase target indicata come path, senza assunzioni
  hardcoded su struttura, distribuzione dei linguaggi o dimensione del corpus.
- **FR-014**: Il sistema MUST essere coperto da test automatici per: indicizzazione, interrogazione
  (≥1 risultato), idempotenza del re-index, gestione degli errori (indice mancante, provider non
  disponibile).
- **FR-015**: Il sistema MUST emettere log strutturati a runtime in indicizzazione e interrogazione
  (operazione, provider, conteggi, tempi, errori).

### Key Entities

- **Indice vettoriale (baseline)**: collezione persistente dei chunk con i loro vettori, associata a
  un provider; ricostruibile in modo idempotente.
- **Query**: testo da cui si deriva un embedding per la ricerca per similarità.
- **Risultato (hit)**: path, tipo, indice del chunk, punteggio, anteprima.
- **Set di valutazione (ground-truth)**: mappa query → file attesi; input esterno per le metriche.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Il motore indicizza e rende interrogabile **≥2 codebase distinte** senza modifiche al
  codice.
- **SC-002**: Su un corpus campione con ground-truth, la pertinenza (hit-rate@k, MRR) è **misurata**;
  la soglia di accettazione è fissata in design con il prototipo come baseline, con soglia ridotta
  ammessa per il provider locale.
- **SC-003**: Due indicizzazioni consecutive sulla stessa codebase invariata producono un indice con
  lo **stesso** numero di chunk e gli stessi risultati alle medesime query (idempotenza).
- **SC-004**: Il motore funziona con **≥2 provider** di embeddings distinti (≥1 locale, ≥1 cloud) senza
  modifiche al codice.
- **SC-005**: L'attivazione/disattivazione della modalità baseline non altera il comportamento delle
  altre modalità.
- **SC-006**: Il **100%** delle run di indicizzazione e interrogazione emette log strutturati con i
  campi richiesti.

## Assumptions

- FEAT-001 (nucleo condiviso) espone un'interfaccia stabile per ingestione/chunking/embeddings/vector
  store; il motore la **consuma**, non la ridefinisce.
- Questa modalità **richiede** embeddings + vector store (è una modalità testuale).
- Il ground-truth per la valutazione è un artefatto esterno fornito dal chiamante; il motore non lo genera.
- Le soglie numeriche di pertinenza/performance si fissano in design (baseline = prototipo); il
  riferimento del prototipo è hit@5 ~0.80 cloud, ~0.67 locale.
- Generazione di risposta LLM, multi-tenant e ottimizzazioni avanzate della similarità sono fuori MVP.
