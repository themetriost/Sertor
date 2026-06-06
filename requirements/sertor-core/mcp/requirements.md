# Requisiti — Server MCP di produzione (`sertor_mcp`)

<!-- Deriva da: FEAT-MCP (epica sertor-core, §8) -->

---

## Stato

**Stato: in progress** (elicitazione iniziale 2026-06-06).

> **Nota di provenienza.** Esiste già un'implementazione di riferimento del server su un branch non
> mergiato (`feat/mcp-sertor-core`, commit `53b8e43`: `src/sertor_mcp/server.py` +
> `tests/unit/test_mcp_server.py`), pulita, testata e compatibile con `master`. È **riferimento**, non
> prodotto: questa feature segue il flusso SpecKit completo (requirements → spec → plan → tasks →
> implement). Il merge dei soli sorgenti, senza requisiti/spec a monte, è esattamente ciò che la fase
> di produzione evita (tracciabilità e riproducibilità).

---

## 1. Contesto e problema (perché)

Il valore del core (`sertor_core`) — creare e interrogare un RAG su una codebase — oggi è raggiungibile
solo come **libreria Python**. Manca la **superficie finale** che lo renda usabile **nativamente da un
agente LLM**: un server **MCP** (Model Context Protocol) che esponga il retrieval del core come **tool**
che un client MCP (es. Claude Code) orchestra autonomamente.

Esiste un server MCP nel **prototipo** (`prototype/04-agentic-rag/mcp_server.py`), ma poggia sul motore
del prototipo e punta al **corpus congelato** (FastAPI/prototipo). Il `.mcp.json` di `master` punta
ancora a quello: rispetto alla **produzione** è **rotto** (interroga il corpus sbagliato, non Sertor).

Questa feature colma il gap: un server MCP **production-grade** costruito sulla **facade di
`sertor_core`**, che sostituisce quello del prototipo come superficie attiva del repo.

**Perché ora (leva).** È l'**enabler** (roadmap, item 5a) di tre cose oggi bloccate:
1. il **probe-RAG del lint semantico** del wiki (FEAT-003-N / N5), che oggi degrada al fallback
   `Read`/`Grep` perché non c'è un RAG dell'ospite cablato;
2. il **dogfood di produzione** (interrogare Sertor su sé stesso: `src/`, `specs/`, `requirements/`,
   `wiki/`);
3. l'**entry-point dell'agente** (Azure) che consuma i tool di retrieval.

## 2. Obiettivi e criteri di successo

**Obiettivo.** Esporre il retrieval vettoriale del core come tool MCP, come **consumatore sottile**
(Principio I): i tool chiamano la facade, non reimplementano nulla; provider/backend/corpus dalla
configurazione centralizzata (Principio VIII/X).

Criteri di successo misurabili e tech-agnostici:

- **CS-1 (superficie nativa):** un client MCP che lancia il server vede **≥1** tool di retrieval
  registrato e può invocarlo, ottenendo risultati strutturati su una query nota.
- **CS-2 (tre tool baseline):** sono disponibili e distinti **3** tool — ricerca su *codice*, su
  *documentazione*, su *entrambi* — ciascuno con il proprio filtro/comportamento osservabile.
- **CS-3 (consumatore sottile):** i tool non duplicano la logica di retrieval; rimossa l'implementazione
  del core, i tool non funzionano (dipendono dalla facade). Verificabile per ispezione/test con facade mock.
- **CS-4 (host-agnostico):** lo stesso server, **senza modifiche al codice**, opera su corpus/backend/
  provider diversi cambiando **solo** la configurazione (`.env`/`Settings`).
- **CS-5 (dogfood):** con un indice del corpus di produzione costruito, una query nota su Sertor
  restituisce risultati pertinenti dai sorgenti **e** dalla documentazione del repo.
- **CS-6 (degrado pulito):** se l'indice del corpus configurato non esiste, l'invocazione di un tool
  **non fa crashare** il server e comunica la condizione in modo osservabile (nessun risultato + warning).
- **CS-7 (sostituzione):** dopo la feature, `.mcp.json` punta al server di produzione
  (`python -m sertor_mcp.server`) e **non** più al server del prototipo.
- **CS-8 (isolamento dipendenze):** installare la libreria core **senza** l'extra del server MCP non
  installa l'SDK MCP; l'extra è isolato.

## 3. Stakeholder e attori

| Attore | Ruolo rispetto a questa feature |
|--------|--------------------------------|
| **Agente LLM (es. Claude Code)** | Attore non-umano **primario**: lancia il server via il proprio meccanismo MCP e **consuma** i tool come strumenti nativi, orchestrando lui il loop di retrieval. |
| **Owner/maintainer** | Configura il server (corpus/backend/provider via `.env`), costruisce l'indice di produzione, verifica il dogfood. |
| **Layer agentico del Wiki (lint semantico N5)** | Consumatore: usa i tool di retrieval come *probe-RAG* della ground truth, al posto del fallback `Read`/`Grep`. |
| **Epica `sertor-cli`** | Possibile consumatore a valle: la CLI può installare/avviare/configurare il server come una delle superfici del core. |
| **`sertor_core` (facade di retrieval)** | Dipendenza a monte: fornisce `build_facade`/`Settings` e i metodi `search_code`/`search_docs`/`search_combined`. |
| **Client MCP generici** | Qualunque altro client conforme a MCP che voglia usare i tool. |

## 4. Ambito

### In ambito

1. Un **server MCP** (trasporto **stdio**) che espone il retrieval vettoriale del core.
2. **Tre tool di ricerca** baseline: `search_code`, `search_docs`, `search_combined`.
3. **Formato risultati** strutturato e stabile per ciascun tool (path, tipo sorgente, id chunk, score,
   anteprima troncata).
4. **Layer sottile** sul core: i tool delegano alla facade (`build_facade(Settings.load())`).
5. **Configurazione host-agnostica**: corpus/backend/provider dalla configurazione centralizzata.
6. **Binding di avvio** documentato (`.mcp.json` → `python -m sertor_mcp.server`) e **sostituzione**
   del server del prototipo come superficie attiva del repo.
7. **Riconciliazione del naming del corpus** verso il corpus di prodotto **`sertor`**.
8. **Gestione esplicita** della condizione "indice mancante" (degrado pulito).
9. **Isolamento della dipendenza** SDK MCP come **extra opzionale** del pacchetto.
10. **Metadati/istruzioni** del server che guidano il client nella scelta del tool e nella citazione dei file.
11. **Estendibilità**: la struttura consente di aggiungere tool futuri senza toccare gli esistenti.

### Fuori ambito

- **Tool di navigazione del grafo** (`find_symbol`, `who_calls`, `related_docs`, `get_context`):
  tornano con il **motore GraphRAG (FEAT-005)**; non in questa feature.
- **Reranking ibrido vero** (`search_combined` con reranker): arriva con il **motore ibrido (FEAT-004)**;
  qui `search_combined` è la fusione baseline offerta dalla facade attuale.
- **Operazioni Wiki via MCP** (record/ingest/query/manutenzione): la superficie MCP delle operazioni
  wiki (FR-032 di `wiki-creazione`) è una **feature distinta**; qui si espone **solo il retrieval**.
- **Creazione/gestione dell'indice** (ingestione, refresh incrementale): è del **nucleo/CLI**
  (FEAT-001/FEAT-009); il server **consuma** un indice esistente, non lo costruisce.
- **Trasporti non-stdio** (HTTP/SSE, server remoto) e **autenticazione/autorizzazione** di rete.
- **Tool che mutano stato** (scrittura/cancellazione): il server è **sola lettura** (retrieval).
- **L'agente Azure in sé**: questa feature ne abilita l'entry-point, non lo implementa.

## 5. Requisiti funzionali (EARS)

### Gruppo A — Esposizione dei tool di retrieval

**REQ-001 (Ubiquitous)**
*The MCP server shall expose the core's vector retrieval as tools consumable by any MCP client.*

**REQ-002 (Ubiquitous)**
*The server shall register exactly three retrieval tools — `search_code`, `search_docs`, and
`search_combined` — each accepting a textual query and an optional result count `k`.*

**REQ-003 (Event-driven)**
*When `search_code` is invoked, the system shall return results restricted to source-code documents.*

**REQ-004 (Event-driven)**
*When `search_docs` is invoked, the system shall return results restricted to documentation/Markdown
documents.*

**REQ-005 (Event-driven)**
*When `search_combined` is invoked, the system shall return results drawn from both code and
documentation together.*

**REQ-006 (Ubiquitous)**
*The server shall expose only read/retrieval tools and shall not expose any tool that mutates the
index, the corpus, or the filesystem.*

### Gruppo B — Consumatore sottile del core

**REQ-010 (Ubiquitous)**
*The server shall delegate all retrieval to the `sertor_core` facade and shall not re-implement
retrieval, ranking, or store/embeddings logic (thin consumer — Principle I).*

**REQ-011 (Ubiquitous)**
*The server shall build the facade once from the centralized configuration and reuse it across tool
invocations.*

### Gruppo C — Configurazione host-agnostica

**REQ-020 (Ubiquitous)**
*The server shall obtain the embeddings provider, the retrieval backend, and the corpus from the
centralized configuration (`Settings`/`.env`), and shall not hard-code any host-specific path or value
(Principle X).*

**REQ-021 (Ubiquitous)**
*The server shall target the product corpus `sertor` by default configuration, superseding the
prototype's legacy corpus value (`production`/`prototype`).*

**REQ-022 (Optional)**
*Where the configuration selects a different backend or corpus, the server shall operate against it
without any change to the server code.*

### Gruppo D — Avvio, trasporto e binding

**REQ-030 (Event-driven)**
*When launched as a module (`python -m sertor_mcp.server`), the system shall start an MCP server over
the stdio transport.*

**REQ-031 (Ubiquitous)**
*The repository's MCP client binding (`.mcp.json`) shall point to the production server and shall no
longer reference the prototype server.*

**REQ-032 (Ubiquitous)**
*The server shall provide descriptive metadata/instructions that guide the client in choosing among the
tools (code vs docs vs combined) and in citing source files in its answers.*

### Gruppo E — Formato dei risultati

**REQ-040 (Ubiquitous)**
*Each retrieval tool shall return a list of structured results, where each result carries at minimum:
the document path, the source type (code/doc), the chunk identifier, the relevance score, and a text
preview.*

**REQ-041 (Event-driven)**
*When a result's text exceeds the configured preview length, the system shall truncate the preview and
mark it as truncated, so the payload stays bounded.*

**REQ-042 (Ubiquitous)**
*The result field set shall be stable and identical across the three tools.*

### Gruppo F — Gestione errori e degrado

**REQ-050 (Unwanted behaviour)**
*If no index exists for the configured corpus, then the system shall return an empty result set and
emit a warning, without raising an unhandled error or terminating the server.*

**REQ-051 (Unwanted behaviour)**
*If a tool invocation fails inside the core, then the system shall surface a readable error to the
client and remain available for subsequent invocations (no partial/inconsistent state).*

### Gruppo G — Isolamento delle dipendenze ed estendibilità

**REQ-060 (Ubiquitous)**
*The MCP SDK dependency shall be packaged as an isolated optional extra, so that installing the core
library without that extra does not install the MCP server's dependencies (NFR dependency isolation).*

**REQ-061 (Optional)**
*Where new retrieval engines become available (graph — FEAT-005; hybrid rerank — FEAT-004), the server
shall allow registering additional tools without modifying or breaking the existing three tools.*

## 6. Requisiti non funzionali

| ID | Categoria | Requisito |
|----|-----------|-----------|
| RNF-001 | **Portabilità** | Il server opera su qualunque repository/ambiente senza percorsi hard-coded e senza dipendere dall'OS; tutta la specificità dell'ospite passa dalla configurazione (Principio X). |
| RNF-002 | **Testabilità** | I tool sono verificabili automaticamente con una facade/store **mock**, senza rete né indici reali (registrazione tool, formato risultati, filtro per tipo). |
| RNF-003 | **Isolamento dipendenze** | L'SDK MCP non è dipendenza del core: vive in un extra opzionale, non confligge con gli altri motori. |
| RNF-004 | **Osservabilità** | Ogni invocazione di tool e ogni condizione anomala (indice mancante, errore del core) producono log strutturati diagnosticabili senza leggere il codice (Principio IX). |
| RNF-005 | **Gestione errori esplicita** | Le condizioni prevedibili (indice mancante, corpus non configurato, provider non disponibile) producono messaggi leggibili; nessun crash silenzioso (Principio IV). |
| RNF-006 | **Latenza** | L'overhead del layer MCP è trascurabile rispetto al retrieval del core (il server non aggiunge elaborazione oltre la formattazione del risultato). |
| RNF-007 | **Payload limitato** | L'anteprima testuale di ciascun risultato è troncata a una soglia configurabile per non gonfiare il contesto del client. |
| RNF-008 | **Sicurezza** | Il server è **sola lettura**; nessun segreto è persistito in file versionati (transita da `.env`); nessuna esecuzione di comandi arbitrari via tool. |

## 7. Vincoli, assunzioni e dipendenze

### Vincoli

- **Consumatore sottile (Principio I):** il server non reimplementa retrieval; usa `build_facade`/`Settings`.
- **Host-agnostico (Principio X, NON-NEGOZIABILE):** nessuna assunzione dell'ospite hardcoded.
- **Trasporto stdio:** il server è avviato dal client MCP; non è un servizio di rete (MVP).
- **Sola lettura:** nessun tool di scrittura/mutazione in questa feature.
- **Segreti:** mai in file versionati (REQ-E5 dell'epica).

### Assunzioni

- È installato un **SDK MCP** Python (extra opzionale `mcp`).
- Esiste (o sarà costruito separatamente) un **indice** per il corpus configurato; la **costruzione**
  dell'indice è del nucleo/CLI, non di questa feature.
- La facade del core espone `search_code`/`search_docs`/`search_combined` con risultati che portano
  `text`/`path`/`chunk_id`/`score`/`doc_type` (verificato su `master`).
- Il client MCP gestisce il ciclo di vita del processo del server (avvio/arresto via stdio).

### Dipendenze

| Dipendenza | Tipo | Note |
|------------|------|------|
| **FEAT-001** (nucleo retrieval) + **FEAT-002** (baseline) | Funzionale (a monte) | Forniscono la facade e i metodi di ricerca esposti dai tool. |
| **Indice del corpus `sertor`** | Runtime condizionale | Necessario perché i tool restituiscano risultati (dogfood di produzione); la sua creazione è di FEAT-001/CLI/FEAT-009. |
| **SDK MCP (extra `mcp`)** | Runtime | Dipendenza del solo server, isolata in un extra. |
| **Provider di embeddings + backend store configurati** | Runtime | Coerenti con `Settings` (local→Ollama/Chroma · azure→Azure OpenAI/Azure AI Search). |
| **FEAT-004 / FEAT-005** | Abilitante (futuro) | Sbloccano i tool ibridi/grafo, registrabili in modo non-breaking (REQ-061). |

## 8. Rischi

| ID | Rischio | Prob | Impatto | Mitigazione |
|----|---------|------|---------|-------------|
| R-01 | **Indice assente/non aggiornato** → tool che restituiscono vuoto, percepiti come "rotti". | Media | Medio | REQ-050 (degrado pulito + warning); CS-5/CS-6; documentare la build dell'indice nel quickstart. |
| R-02 | **Disallineamento naming corpus** (`production` legacy vs `sertor`) → si interroga il corpus sbagliato. | Media | Alto | REQ-021 (riconciliazione esplicita a `sertor`); CS-7. |
| R-03 | **Aspettativa sui tool di grafo** (l'utente cerca `find_symbol` e non c'è). | Media | Basso | Fuori ambito dichiarato; metadati/istruzioni del server chiariscono i tool disponibili (REQ-032). |
| R-04 | **Dipendenza MCP che inquina il core** se non isolata. | Bassa | Medio | REQ-060 (extra opzionale); CS-8. |
| R-05 | **Divergenza dalla facade del core** se le firme cambiano. | Bassa | Medio | Layer sottile (REQ-010): un solo punto d'aggancio; test con facade mock (RNF-002). |
| R-06 | **Payload eccessivo** nel contesto del client (testi lunghi). | Bassa | Basso | REQ-041/RNF-007 (anteprima troncata, soglia configurabile). |

## 9. Prioritizzazione (MoSCoW)

| Gruppo di requisiti | ID | MoSCoW | Motivazione |
|---|---|---|---|
| A — Esposizione tool (3 search) | REQ-001..006 | **Must** | È la capacità stessa della feature. |
| B — Consumatore sottile | REQ-010..011 | **Must** | Principio I; senza, si duplica il core. |
| C — Config host-agnostica + corpus `sertor` | REQ-020..022 | **Must** | Principio X; corpus corretto = dogfood reale. |
| D — Avvio/trasporto + binding `.mcp.json` | REQ-030..032 | **Must** | Senza binding il server non è raggiungibile; sostituzione del prototipo. |
| E — Formato risultati | REQ-040..042 | **Must** | I risultati devono essere consumabili e citabili. |
| F — Gestione errori/degrado | REQ-050..051 | **Must** | CS-6; un server che crasha su indice mancante è inusabile. |
| G — Isolamento dipendenze | REQ-060 | **Must** | NFR core; CS-8. |
| G — Estendibilità tool futuri | REQ-061 | **Should** | Valore architetturale; non blocca l'MVP. |
| RNF osservabilità/latenza/payload | RNF-004/006/007 | **Should** | Alzano la qualità; il valore base esiste anche senza. |

> **Sequenza consigliata per l'MVP:** B (aggancio facade) → A (3 tool) → E (formato) → C (config/corpus)
> → F (degrado) → D (binding `.mcp.json` + sostituzione prototipo) → G (extra isolato). L'indice di
> produzione (dogfood) è precondizione di CS-5, costruito via nucleo/CLI in parallelo.

## 10. Domande aperte

| ID | Domanda | Priorità | Default assunto |
|----|---------|---------|-----------------|
| DA-MCP1 | **Naming corpus definitivo**: il default di `Settings.corpus` è `"default"`; il prodotto usa `"sertor"`. Si imposta `sertor` solo via `.env`/`.mcp.json`, o si cambia anche il default di `Settings`? | Media | Impostare `sertor` via configurazione (`.mcp.json`/`.env`), senza toccare il default del core in questa feature. |
| DA-MCP2 | **Tool di stato/health**: esporre un tool che riporti corpus configurato + presenza indice, per rendere osservabile la condizione "indice mancante" lato client? | Bassa | Non nell'MVP; il warning di REQ-050 + i log (RNF-004) bastano. |
| DA-MCP3 | **Cap su `k`**: imporre un massimo a `k` per limitare il payload? | Bassa | Nessun cap rigido nell'MVP; default di `k` dalla facade; anteprima già troncata (REQ-041). |
| DA-MCP4 | **Tre tool vs tool unico parametrico**: tenere 3 tool distinti (DX migliore per l'agente) o un solo `search(scope=...)`? | Bassa | Tre tool distinti (coerente col riferimento e con la chiarezza per l'agente). |

---

## 11. Tracciabilità verso l'epica e i criteri di successo del core

| Criterio epica (sertor-core §3) | Collegamento |
|---|---|
| CS-1 (creare RAG baseline interrogabile) | L'MCP è una **superficie d'interrogazione** del RAG baseline. |
| CS-4 (production-grade, configurabile, no single-provider) | REQ-020/022, RNF-001..008. |
| CS-5 (repo-agnostico ≥2 codebase) | RNF-001, REQ-020 (host-agnostico). |
| REQ-E1 (capacità riusabili indipendenti dalla CLI) | Il server è una superficie del core, indipendente dalla CLI. |
| REQ-E3 (LLM target dove serve) | Non si applica: il retrieval baseline non richiede generazione (solo embeddings). |
| REQ-E5 (segreti non versionati) | RNF-008. |
