# Feature Specification: Disaccoppiamento store ↔ provider di embeddings

**Feature Branch**: `spec/009-store-backend-disaccoppiato`

**Created**: 2026-06-09

**Status**: Draft

**Input**: Esigenza emersa costruendo l'indice di dogfooding del corpus di produzione `sertor`: servono
**embeddings Azure** (`text-embedding-3-large`) con **store Chroma locale**, combinazione oggi non
esprimibile perché lo store è accoppiato a `RAG_BACKEND`. Estende il nucleo `sertor-core` (FEAT-001).

## User Scenarios & Testing *(mandatory)*

Gli "utenti" sono i consumatori del core (server MCP, futura CLI, test) che cablano retrieval/indicizzazione
dalla configurazione centralizzata, e l'operatore che configura l'ambiente via `.env`.

### User Story 1 - Embeddings cloud con store locale (Priority: P1)

Un operatore vuole indicizzare un corpus usando un provider di embeddings cloud (Azure OpenAI, per qualità e
per HW locale inaffidabile) ma tenere il **vector store in locale** (Chroma), senza dover provisionare Azure
AI Search. Configura `RAG_BACKEND=azure` e `SERTOR_STORE_BACKEND=local` e il sistema usa l'embedder Azure con
lo store Chroma.

**Why this priority**: è il blocco diretto alla costruzione dell'indice dogfood `sertor` e la traduzione
operativa del Principio II (local-first, dettagli rimpiazzabili in modo indipendente).

**Independent Test**: con `backend=azure` + `store_backend=local`, il composition root costruisce un
`AzureEmbedder` e un `ChromaStore`; nessun client Azure AI Search viene istanziato.

**Acceptance Scenarios**:

1. **Given** `RAG_BACKEND=azure` e `SERTOR_STORE_BACKEND=local`, **When** si costruiscono i componenti,
   **Then** l'embedder è Azure e lo store è Chroma locale.
2. **Given** nessun `SERTOR_STORE_BACKEND` impostato, **When** si carica la configurazione,
   **Then** lo `store_backend` eredita il valore di `RAG_BACKEND` (retro-compatibilità: nessun cambio di
   comportamento per chi non usa la nuova variabile).
3. **Given** `store_backend=local`, **When** si calcola il nome della collezione, **Then** i vincoli di
   naming di Azure AI Search (lowercase, niente cifra iniziale) **non** vengono applicati.

---

### User Story 2 - Embeddings Azure sull'endpoint v1 (Priority: P1)

Un operatore configura un endpoint Azure OpenAI della **superficie v1** (`.../openai/v1`). L'embedder deve
funzionare senza inviare il parametro `api-version` (che la superficie v1 rifiuta con HTTP 400).

**Why this priority**: senza questa correzione l'indicizzazione con embeddings Azure sull'endpoint reale del
progetto fallisce immediatamente; è prerequisito della User Story 1 nel contesto attuale.

**Independent Test**: con endpoint contenente `/openai/v1` l'`AzureEmbedder` esegue la POST **senza**
`api-version`; con endpoint classico lo invia.

**Acceptance Scenarios**:

1. **Given** un endpoint `.../openai/v1`, **When** si richiede un embedding, **Then** la richiesta non porta
   il query param `api-version`.
2. **Given** un endpoint classico (senza `/openai/v1`), **When** si richiede un embedding, **Then** la
   richiesta porta `api-version`.

## Requirements *(mandatory)*

- **FR-001**: La configurazione MUST esporre un selettore del backend di vector store
  (`SERTOR_STORE_BACKEND`) **distinto** dal selettore del provider di embeddings (`RAG_BACKEND`).
- **FR-002**: In assenza di `SERTOR_STORE_BACKEND`, lo store backend MUST ereditare `RAG_BACKEND`
  (retro-compatibile).
- **FR-003**: La costruzione dello store e il naming della collezione MUST dipendere da `store_backend`,
  non da `backend`.
- **FR-004**: L'`AzureEmbedder` MUST omettere `api-version` quando l'endpoint è la superficie v1
  (`/openai/v1`) e inviarlo altrimenti.
- **FR-005**: Nessuna nuova dipendenza; il comportamento local-only resta invariato (Principio II).

### Out of scope

- `build_llm`/porta LLM per la distillazione wiki (feature separata).
- Provisioning o test di Azure AI Search come store.

## Success Criteria *(mandatory)*

- **SC-001**: Con `RAG_BACKEND=azure` + `SERTOR_STORE_BACKEND=local` l'indice del corpus `sertor` si
  costruisce su Chroma locale con embeddings Azure (`embedding_dim=3072`), e `search_*` ritorna risultati.
- **SC-002**: La suite `pytest -m "not cloud"` resta verde e `ruff check src tests` pulito.
- **SC-003**: Nessun cambio di comportamento per configurazioni che non impostano `SERTOR_STORE_BACKEND`.
