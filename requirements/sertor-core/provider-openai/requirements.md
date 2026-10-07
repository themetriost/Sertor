# Requisiti — Provider di embedding OpenAI (API diretta, compatibile OpenAI)

<!-- Deriva da: FEAT-012 (epica sertor-core) -->

## 1. Contesto e problema (perché)

Per indicizzare e interrogare un corpus Sertor serve un provider di embedding. Oggi i provider
selezionabili con `SERTOR_EMBED_PROVIDER` sono quattro (`src/sertor_core/composition.py:65`):
`glove` (default locale), `hash` (pavimento lessicale), `ollama` (modello locale) e `azure`
(**Azure OpenAI**). L'**API OpenAI diretta** (`api.openai.com`) **non è selezionabile**: chi ha una
chiave OpenAI ma non una sottoscrizione Azure non ha un provider cloud di qualità.

Il caso che la rende urgente è reale e attuale (2026-10-07): sul dogfood la chiave Azure risponde
`http 401` e il server MCP non serve più ricerche (`search_code`/`search_docs` in errore). Il ripiego
su `glove` funziona ma ha una semantica più debole (vettori statici di parole): la **qualità del
retrieval resa all'agente** — il fronte di valore della missione — scende. Un provider OpenAI diretto
ripristina un embedding di qualità con la sola chiave OpenAI, la credenziale cloud più diffusa.

Ancoraggio: l'adapter Azure (`src/sertor_core/adapters/embeddings/azure.py`) parla già il protocollo
`/embeddings` in forma OpenAI (`{"model", "input"}` → `data[].embedding`, `usage.total_tokens`); il
protocollo OpenAI differisce per URL di base e forma della credenziale. La selezione del provider, la
validazione statica dei campi richiesti (`Settings.validate_backend`, `config/settings.py:324`) e
l'area *provider* di `doctor` (`cli/__main__.py:632`, `_PROVIDER_ENV_KEYS`) oggi conoscono solo
`azure` come provider con credenziali.

## 2. Obiettivi e criteri di successo

- **CS-1:** con `SERTOR_EMBED_PROVIDER=openai` e una chiave valida, `sertor-rag index .` costruisce
  l'indice e `sertor-rag search` / i tool MCP `search_code`/`search_docs` restituiscono risultati,
  **senza alcuna variabile Azure** impostata.
- **CS-2:** il passaggio da/verso `openai` non contamina indici esistenti: l'indice `openai` vive in
  una collezione distinta da quelle `azure`/`glove`/`hash`/`ollama` dello stesso corpus (verificabile
  dal nome della collezione).
- **CS-3:** con la chiave mancante, `sertor-rag doctor` fallisce sull'area *provider* nominando
  `OPENAI_API_KEY`; con chiave rifiutata dal servizio, l'errore che arriva a CLI e client MCP nomina
  il provider e lo stato HTTP — mai il valore della chiave.
- **CS-4:** nessuna regressione sui provider esistenti: la suite `-m "not cloud"` resta verde e il
  comportamento di `azure` (URL, credenziale, `api-version`, retry, eventi) è invariato.
- **CS-5:** un utente che legge solo la documentazione utente (`docs/install.md`, `.env.example`) sa
  attivare il provider e conosce default di modello e costo indicativo.

## 3. Stakeholder e attori

- **Utente/ospite** con una chiave OpenAI (sviluppatore singolo, team senza Azure).
- **Agente** (Claude/Copilot) che consuma il retrieval via MCP/CLI: beneficia della qualità.
- **Manutentore di Sertor** (dogfood): oggi bloccato dalla chiave Azure scaduta.
- **Nodo Kaelen**: proprietario dell'installer congelato (vedi §7), da cui dipende il cablaggio nel
  wizard `sertor configure` e nel template `.env` installato.
- **Servizio OpenAI** (o servizio compatibile OpenAI) come sistema esterno.

## 4. Ambito

### In ambito
- Un nuovo valore `openai` di `SERTOR_EMBED_PROVIDER`, selezionabile accanto agli esistenti.
- Tre impostazioni: chiave API, modello di embedding (default `text-embedding-3-large`, decisione
  utente 2026-10-07), URL di base (default `https://api.openai.com/v1`; sovrascrivibile per servizi
  compatibili OpenAI).
- Validazione statica dei campi richiesti, diagnosi in `doctor`, errori fail-loud e scrubbing dei
  segreti, retry sui guasti transitori, segnale di costo in token, cache degli embedding: **paritetici
  al provider `azure`**.
- Documentazione utente (`docs/install.md`, `.env.example`) e config d'esempio.

### Fuori ambito
- **Cablaggio nell'installer** (`sertor configure --backend`, template `.env` depositato da
  `sertor install rag`): codice **congelato** e trasferito a Kaelen (CLAUDE.md, *Congelamento*). Si
  registra come debito di completamento verso Kaelen; nel frattempo il provider si attiva a mano o con
  `sertor configure --set` (che scrive chiavi arbitrarie).
- **Riduzione delle dimensioni** del vettore (parametro `dimensions` dei modelli `text-embedding-3-*`):
  capacità futura → da promuovere in roadmap.
- **Intestazioni organizzazione/progetto** OpenAI (`OpenAI-Organization`, `OpenAI-Project`): le chiavi
  di progetto bastano al primo taglio → da promuovere in roadmap se richiesto.
- Provider **LLM** (chat/completions): il core non chiama mai un LLM (confine D↔N).
- Migrazione automatica di un indice da un provider a un altro: il cambio provider richiede un
  re-index, come oggi.

## 5. Requisiti funzionali (EARS)

**Selezione e configurazione**
- **REQ-001 (Event-driven):** When `SERTOR_EMBED_PROVIDER` is `openai`, the system shall build the
  OpenAI embedding provider for both indexing and query paths.
- **REQ-002 (Unwanted):** If `SERTOR_EMBED_PROVIDER` holds an unknown value, then the system shall fail
  with a configuration error that lists `openai` among the allowed values.
- **REQ-003 (Ubiquitous):** The system shall read the API key from `OPENAI_API_KEY`, the model from
  `OPENAI_EMBED_MODEL` and the base URL from `OPENAI_BASE_URL`.
- **REQ-004 (Ubiquitous):** The system shall default `OPENAI_EMBED_MODEL` to `text-embedding-3-large`
  and `OPENAI_BASE_URL` to `https://api.openai.com/v1`, with these defaults defined only in the
  centralised settings.
- **REQ-005 (Ubiquitous):** The system shall select the provider exclusively through
  `SERTOR_EMBED_PROVIDER`; the presence of Azure or OpenAI variables shall not change the selection.

**Validazione e diagnosi**
- **REQ-006 (State-driven):** While the provider is `openai`, the static backend validation shall
  report `OPENAI_API_KEY` as missing when it is empty, without contacting any service.
- **REQ-007 (State-driven):** While the provider is `openai`, the static validation shall not require
  any `AZURE_OPENAI_*` variable.
- **REQ-008 (Event-driven):** When `doctor` runs with the provider `openai` and `OPENAI_API_KEY` empty,
  the system shall mark the *provider* area as failed and name the missing key.

**Chiamata al servizio**
- **REQ-009 (Ubiquitous):** The provider shall send texts in batches of at most the configured
  embedding batch size and return one vector per input text, in input order.
- **REQ-010 (Ubiquitous):** The provider shall authenticate with the API key as a bearer credential.
- **REQ-011 (Event-driven):** When the first batch is embedded, the provider shall record the vector
  dimension from the response.
- **REQ-012 (Event-driven):** When the service reports token usage, the provider shall emit the
  embeddings event with the total token count; when it does not, the field shall be omitted.

**Errori e resilienza**
- **REQ-013 (Unwanted):** If the service answers with an HTTP error status, then the provider shall
  raise an embedding error naming the provider and the status, marked retriable only for 429 and 5xx.
- **REQ-014 (Unwanted):** If the service is unreachable (network/timeout), then the provider shall
  raise a retriable embedding error naming the provider and the failure type.
- **REQ-015 (Event-driven):** When a retry policy with more than one attempt is configured, the
  provider shall retry retriable failures per batch, without re-embedding batches already succeeded.
- **REQ-016 (Unwanted):** If the API key, model or base URL is empty at construction, then the provider
  shall fail with a non-retriable error naming the missing fields.
- **REQ-017 (Ubiquitous):** The system shall never write the API key value to logs, events, error
  messages, `doctor` output or MCP tool errors.

**Isolamento degli indici**
- **REQ-018 (Ubiquitous):** The provider's identity shall include the model, so that indexes built
  with `openai` live in a collection distinct from those of other providers and other OpenAI models.
- **REQ-019 (Where):** Where the embedding cache is enabled, cached vectors shall be keyed by the
  provider identity, so that `openai` vectors are never served for another provider or model.

**Non-regressione**
- **REQ-020 (Ubiquitous):** The `azure` provider shall keep its current behaviour: URL, `api-key`
  credential, `api-version` handling for non-v1 endpoints, error classification, retry and events.

**Documentazione**
- **REQ-021 (Ubiquitous):** The user documentation shall describe how to enable the `openai` provider,
  its three variables with defaults, and that changing provider requires a re-index.
- **REQ-022 (Ubiquitous):** The `.env.example` template of the repository shall list the three
  variables, commented, under a section for the `openai` provider.

## 6. Requisiti non funzionali

- **NFR-01 (testabilità):** il provider è verificabile **senza rete** con un client HTTP iniettabile;
  i test contro il servizio reale sono marcati `cloud`.
- **NFR-02 (isolamento dipendenze):** nessuna dipendenza nuova; caricamento lazy come gli altri
  provider (nessun import al livello del modulo di composizione).
- **NFR-03 (sicurezza):** chiave mai persistita fuori da `.env`; scrubbing esistente (`sk-…`, `Bearer`)
  copre i formati OpenAI.
- **NFR-04 (costo):** il segnale in token permette di stimare il costo di un re-index;
  ordine di grandezza documentato (modello `large`: ~0,13 $/milione di token).
- **NFR-05 (osservabilità):** eventi `embeddings`/`embeddings_error` con lo stesso schema del provider
  `azure`, così report e telemetria non cambiano.

## 7. Vincoli, assunzioni e dipendenze

- **Vincolo — congelamento installer (2026-09-18):** nessuna modifica a `packages/sertor-install-kit/`
  né a `sertor_installer/`. Conseguenza: per la regola 1 del CLAUDE.md la capacità resta
  **incompleta su ospite tramite il wizard** finché Kaelen non la cabla; il debito va **tracciato** e
  **affisso in bacheca** a Kaelen. La capacità di libreria/CLI viaggia comunque col pacchetto
  `sertor-core` ed è attivabile scrivendo le variabili nel `.env` dell'ospite.
- **Vincolo — Principio XI:** l'attivazione e la verifica passano dai vehicles (CLI/MCP).
- **Assunzione:** il servizio espone `POST {base}/embeddings` con il formato OpenAI standard; i servizi
  «compatibili OpenAI» che lo rispettano funzionano senza modifiche.
- **Assunzione:** il nome `OPENAI_API_KEY` è quello convenzionale; condividerlo con altri strumenti
  della stessa shell è accettabile (e atteso).
- **Dipendenza:** porta `EmbeddingProvider` (`domain/ports.py`), politica di retry esistente
  (`adapters/embeddings/_retry.py`), cache degli embedding.

## 8. Rischi

- **R-1 — Divergenza Azure/OpenAI:** due adapter con logica HTTP duplicata divergerebbero nel tempo
  (retry, classificazione errori). Mitigazione da decidere in design.
- **R-2 — Regressione su `azure`:** un'eventuale fattorizzazione comune tocca un provider in uso.
  Mitigazione: REQ-020 + test esistenti dell'adapter Azure invariati.
- **R-3 — Costo inatteso:** re-index completi automatici (hook di freschezza) su provider a pagamento.
  Mitigazione: cache degli embedding già esistente; costo documentato.
- **R-4 — Limiti di input del servizio:** batch troppo grandi o testi troppo lunghi rifiutati (400).
  Mitigazione: errore fail-loud con stato; batch size configurabile.

## 9. Prioritizzazione (MoSCoW)

- **Must:** REQ-001…REQ-018, REQ-020, REQ-021, REQ-022.
- **Should:** REQ-019 (la cache esiste già ed è indicizzata per nome provider: va solo verificata).
- **Won't (questo taglio):** riduzione dimensioni, intestazioni org/progetto, cablaggio wizard
  (→ Kaelen).

## 10. Domande aperte

Nessuna bloccante. Decisioni già prese dall'utente (2026-10-07): processo SpecKit completo; modello
di default `text-embedding-3-large`.
