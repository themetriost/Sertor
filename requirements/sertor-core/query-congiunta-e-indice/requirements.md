# Requisiti — Query congiunta multi-collezione & `upsert-index` in CLI

<!-- Deriva da: FEAT-003 (Skill: creare/indicizzare l'LLM Wiki) — i due pezzi codice **deterministici (D)** residui -->

> **Una sola feature, due capacità.** Sono raggruppate qui perché entrambe **deterministiche** e
> decise come **un unico flusso SpecKit completo** (requirements→specify→clarify→plan→tasks→analyze→implement).
> Non condividono requisiti funzionali: la sezione 5 le tiene in **due gruppi distinti** (A e B).

## 1. Contesto e problema (perché)

La visione di prodotto è **«una sola verità interrogabile»**: i sorgenti (il *come*) e la
documentazione/wiki (il *perché*) devono essere interrogabili **insieme**. Oggi questo non è
realizzato fino in fondo, per due lacune deterministiche residue della feature Wiki (FEAT-003):

- **A — Query congiunta mancante.** Wiki e codice sono indicizzati in **collezioni RAG separate**
  (namespacing per `(corpus, provider)` via `collection_name()`; il wiki ha un proprio corpus,
  `index_wiki` in `src/sertor_core/wiki_tools/indexing.py`). Ma `RetrievalFacade`
  (`src/sertor_core/services/retrieval.py`) tiene **una sola** `collection` e `search_combined()` si
  limita a passare `doc_type="both"`: discrimina per tipo di documento **dentro una collezione**, non
  **fonde due collezioni**. Chi vuole «una sola verità interrogabile» (es. un agente, il server MCP)
  oggi non può cercare in codice + wiki in un'unica chiamata e ottenere i risultati migliori dei due.

- **B — `upsert-index` non esposto in CLI.** La scrittura idempotente di una riga
  link+sommario nell'indice del wiki esiste già come funzione pura `upsert_index(profile, page, summary)`
  (`src/sertor_core/wiki_tools/registry.py`), ma **non è cablata** nella CLI
  `sertor-wiki-tools` (`src/sertor_core/wiki_tools/__main__.py`: assente da `_OPS`, dal parser, da
  `_run`, da `_human`). Il flusso wiki deve quindi modificare `index.md` a mano, fuori dal nucleo
  deterministico, perdendo idempotenza e tracciabilità. Manca **solo l'esposizione**: la logica c'è.

Entrambe sono lavoro **meccanico** (zero LLM): rientrano nella metà **D** del confine D↔N del wiki.

## 2. Obiettivi e criteri di successo

| ID | Criterio di successo (misurabile, tech-agnostico) |
|----|----------------------------------------------------|
| SC-1 | Una singola invocazione di ricerca combinata restituisce risultati provenienti **sia** dalla collezione del codice **sia** da quella del wiki, ordinati per pertinenza, con al più `k` elementi complessivi. |
| SC-2 | Quando una delle due collezioni è assente/vuota, la ricerca combinata restituisce comunque i risultati dell'altra, senza errore (degradazione morbida, coerente con la policy tollerante della facade). |
| SC-3 | La ricerca combinata su **singola** collezione produce risultati identici al comportamento odierno (nessuna regressione per chi non usa due collezioni). |
| SC-4 | La CLI `sertor-wiki-tools` espone un sottocomando che, dato `page` e `summary`, inserisce/aggiorna la riga d'indice in modo **idempotente** (seconda invocazione identica → nessuna scrittura, esito «noop»). |
| SC-5 | Il sottocomando CLI **non genera** alcun sommario: lo riceve come input (argomento o stdin) e si limita a scriverlo — il contenuto resta autorato esternamente (dall'LLM). |
| SC-6 | Entrambe le capacità restano **host-agnostiche** (Principio X): nessun percorso/identità del progetto Sertor cablato; tutto deriva da `Settings`/`wiki.config.toml`. |
| SC-7 | Suite di test verde (`not cloud`) e `ruff` pulito; ogni nuova capacità coperta da test deterministici con mock/fixtures (nessuna rete). |

## 3. Stakeholder e attori

- **Consumatori del retrieval** (server MCP, motori RAG, futura CLI, agenti): beneficiari della query
  congiunta — interrogano codice+wiki insieme via la facade/porte.
- **Flusso di curazione del wiki** (LLM nel loop + `wiki-curator`): usa `upsert-index` per scrivere la
  riga d'indice dopo aver autorato il sommario.
- **Manutentori del nucleo `sertor-core`**: estendono facade/porte e CLI restando dentro la Clean
  Architecture e la costituzione v1.1.0.

## 4. Ambito

### In ambito
- **A.** Estendere il retrieval per **fondere i top-k di due (o più) collezioni** in un unico risultato
  ordinato per pertinenza, esposto come capacità della facade (e, se necessario, della porta
  `VectorStore`), restando dietro le porte (Principio I).
- **A.** Comportamento tollerante: collezione assente → contributo vuoto, niente eccezione (coerente con
  `search_combined` odierno).
- **B.** Cablare `upsert_index` come **nuovo sottocomando** della CLI `sertor-wiki-tools`, sul modello
  di `append-log`: parsing degli argomenti → funzione pura → output umano/JSON; il sommario arriva come
  argomento o da **stdin**.
- **B.** Esito strutturato del sottocomando (scritto/non-scritto, inserito/aggiornato) coerente con i
  contratti JSON versionati esistenti.

### Fuori ambito
- **Generazione** del sommario o decisione di *quali* pagine indicizzare (è giudizio LLM, parte **N**).
- Reranking semantico/cross-encoder, fusione lessicale/BM25 (è **FEAT-004**, motore ibrido).
- Query su **>2** corpora arbitrari come caso d'uso di prodotto (il design può generalizzare a N, ma il
  driver è codice+wiki).
- Esposizione della query congiunta come **nuovo tool MCP** o sottocomando CLI top-level `sertor`
  (quest'ultima è epica `sertor-cli`); qui la capacità vive nel **nucleo**. L'eventuale cablaggio nel
  server MCP è una decisione a valle.
- Re-indicizzazione o cambi allo schema di indicizzazione delle collezioni.

## 5. Requisiti funzionali (EARS)

### Gruppo A — Query congiunta multi-collezione

- **REQ-A1** — The retrieval facade shall expose a combined-search capability that retrieves results
  from **both** the code-corpus collection **and** the wiki-corpus collection for a single query.
- **REQ-A2** — When a combined search is requested with a result limit `k`, the system shall return **at
  most `k`** results in total, ordered by relevance (descending) across the two collections.
- **REQ-A3** — While merging results from multiple collections, the system shall order them by their
  similarity **score** (already carried by `RetrievalResult.score`).
- **REQ-A4** — If one of the target collections is absent or empty, then the system shall return the
  results of the remaining collection(s) **without raising an exception** (soft degradation, consistent
  with the current tolerant facade policy).
- **REQ-A5** — If **all** target collections are absent or empty, then the system shall return an empty
  result list and emit a warning (no exception).
- **REQ-A6** — Where only a single collection is configured/targeted, the system shall behave **identically**
  to today's `search_combined` (no regression).
- **REQ-A7** — The combined-search capability shall be reachable by consumers **through the existing
  composition root** (`build_facade`) without the consumer knowing store/embeddings details (Principio I,
  thin-consumer).
- **REQ-A8** — The system shall emit a structured retrieval log event for the combined search, reporting
  the collections queried, the requested `k`, and the number of merged results (osservabilità, coerente
  con `log_event("retrieve", …)`).
- **REQ-A9** — Where the two collections are not directly comparable (see DA-1), the system shall apply
  a **defined, documented** merge policy rather than silently mixing incomparable scores. *(La policy
  esatta è materia di `clarify`/`plan`; il requisito impone che esista e sia esplicita.)*

### Gruppo B — `upsert-index` in CLI

- **REQ-B1** — The `sertor-wiki-tools` CLI shall provide a new operation that writes/updates a single
  index line (`- [[page]] — summary`) by delegating to the existing pure function `upsert_index`.
- **REQ-B2** — When the operation is invoked, the system shall accept the **page identifier** and the
  **summary text** as inputs, the summary provided either as an argument **or** via **stdin** (modello
  `append-log`).
- **REQ-B3** — The system shall perform the index write **idempotently**: re-invoking with an identical
  `(page, summary)` shall result in **no write** and report a no-op outcome (SC-002 del nucleo).
- **REQ-B4** — When the summary for an existing page differs from the stored one, the system shall
  **update** that page's index line in place (not append a duplicate).
- **REQ-B5** — The CLI operation shall **not** generate, infer, or rewrite the summary; it shall write
  exactly the provided text (confine D↔N: la CLI fa il piazzamento, l'LLM fornisce il contenuto).
- **REQ-B6** — If the wiki index file does not exist, then the system shall fail with an explicit error
  (`ConfigError`) and a non-zero exit code, instructing to initialize the structure (comportamento già
  proprio di `upsert_index`).
- **REQ-B7** — The operation shall return a **structured result** (JSON via `--json`, sintesi umana
  altrimenti) indicating whether a write happened and whether it was an insert or an update, coerente
  con gli altri esiti della CLI.
- **REQ-B8** — The system shall read the summary from stdin using **UTF-8**, coerente col trattamento
  già adottato per il corpo di `append-log` (evita mojibake su console non-UTF-8).

## 6. Requisiti non funzionali

- **RNF-1 (Host-agnosticità, Principio X — NON NEGOZIABILE).** Nessuna identità/percorso del progetto
  Sertor hardcodato; A deriva tutto da `Settings`, B da `wiki.config.toml`/`WikiProfile`.
- **RNF-2 (Thin-consumer, Principio I).** La logica vive nel nucleo dietro le porte; CLI/MCP/agenti
  restano gusci sottili che cablano dalle factory `build_*`. Nessuna logica di merge reimplementata nei
  consumatori.
- **RNF-3 (Determinismo & assenza LLM).** Entrambe le capacità sono pure-meccaniche: nessuna chiamata
  LLM, output deterministico a input costante.
- **RNF-4 (Isolamento dipendenze).** Nessun nuovo import pesante nel `domain`; gli SDK restano negli
  adapter con import lazy (coerente con NFR isolamento del core).
- **RNF-5 (Osservabilità).** Log strutturati per la query congiunta (REQ-A8) e per l'esito di
  `upsert-index` (già emesso da `upsert_index`).
- **RNF-6 (Compatibilità).** Nessuna regressione per i consumatori esistenti di `search_combined` e per
  gli altri sottocomandi CLI; le firme pubbliche restano retro-compatibili (estensione, non breaking).
- **RNF-7 (Testabilità).** Coperto da unit test con mock delle porte e fixtures wiki; la suite
  `not cloud` resta verde senza rete.

## 7. Vincoli, assunzioni e dipendenze

**Vincoli**
- Clean Architecture del nucleo: il `domain` non importa SDK; la scelta degli adapter resta in
  `composition.py`; le porte (`domain/ports.py`) sono il confine.
- Costituzione **v1.1.0** (10 principi) + **Constitution Check** a gate del piano.
- La CLI è un entry-point **sottile** (parsing → funzioni pure → output), come da `__main__.py` attuale.

**Assunzioni**
- `RetrievalResult` espone già `score: float` → il merge per pertinenza è realizzabile senza nuovi campi
  di dominio (**verificato** in `domain/entities.py`).
- Nel setup di dogfooding reale, codice e wiki sono indicizzati **con lo stesso provider di embeddings**
  (Azure `text-embedding-3-large`), quindi nello **stesso spazio vettoriale** → score comparabili
  (**verificato**: `index_wiki` riusa `build_indexer` cambiando solo il `corpus`). L'incomparabilità è un
  rischio solo con provider eterogenei tra i due corpora (vedi DA-1).
- L'identità di una riga d'indice è il **path relativo POSIX** della pagina; quella di una voce di log,
  il suo heading — convenzioni già stabilite dal nucleo wiki.

**Dipendenze**
- FEAT-001 (nucleo retrieval, facade/porte) e FEAT-003-D (`wiki_tools`, `upsert_index`) — entrambe su
  `master`.
- Indici dogfood già esistenti per esercitare A end-to-end (corpus `sertor` costruito; corpus wiki via
  `rag-sync`).

## 8. Rischi

| ID | Rischio | Mitigazione |
|----|---------|-------------|
| R-1 | **Score non comparabili** tra collezioni con provider/spazi vettoriali diversi → merge fuorviante. | Vincolare/normalizzare/documentare la policy di merge (REQ-A9); decidere in `clarify`/`plan` se imporre stesso provider o normalizzare (vedi DA-1). |
| R-2 | **Topologia dello store**: le due collezioni potrebbero risiedere in `persist_dir` diversi (`index_dir` è una manopola separata da `corpus`) → un solo `VectorStore` non le vede entrambe. | Chiarire la topologia (DA-2); il design può richiedere fan-out su più store, non solo più nomi-collezione. |
| R-3 | **Scope creep** verso reranking/fusione avanzata (territorio FEAT-004). | Tenere A al solo merge per score; rimandare il reranking. |
| R-4 | Estensione della **porta `VectorStore`** che rompe adapter/mock esistenti. | Preferire estensione non-breaking (nuovo metodo o orchestrazione in facade); coprire con i mock esistenti (`tests/fixtures/mocks.py`). |
| R-5 | La CLI `upsert-index` viene usata per **generare** sommari (sconfina nella parte N). | REQ-B5 esplicito; documentare nel help della CLI che il testo è fornito, non generato. |

## 9. Prioritizzazione (MoSCoW)

**Must**
- A: REQ-A1, A2, A3, A4, A6, A7 (la capacità di query congiunta tollerante, dietro le porte).
- B: REQ-B1, B2, B3, B4, B5, B6 (il sottocomando idempotente, summary fornito, errore esplicito).

**Should**
- A: REQ-A5 (warning su tutte vuote), A8 (log strutturato), A9 (policy di merge esplicita).
- B: REQ-B7 (esito strutturato insert/update), B8 (stdin UTF-8).

**Could**
- Generalizzazione del fan-out a **N collezioni** arbitrarie (oltre codice+wiki).
- Esposizione della query congiunta come tool MCP / sottocomando (decisione a valle).

**Won't (ora)**
- Reranking, fusione lessicale/BM25, normalizzazione cross-provider sofisticata.
- Generazione del sommario lato codice.

## 10. Domande aperte

- **DA-1 (nodo principale, A).** Policy di merge quando i due corpora **non** condividono provider di
  embeddings (score non direttamente comparabili): (a) **vincolare** la query congiunta a corpora con lo
  stesso provider e fallire/avvertire altrimenti; (b) **normalizzare** gli score per collezione prima del
  merge; (c) **interleaving** indipendente dallo score (round-robin sui top-k). Default proposto: **(a)**,
  perché nel setup reale i due corpora usano lo stesso provider e (b)/(c) introducono complessità da
  FEAT-004. → da sciogliere in `clarify`.
- **DA-2 (A).** **Topologia dello store**: le collezioni codice e wiki vivono nello **stesso**
  `persist_dir` (un solo `VectorStore` le interroga entrambe per nome) o in `persist_dir` distinti
  (servono due store / due facce)? Da accertare sul setup dogfood reale in `plan`.
- **DA-3 (A).** Dove vive il fan-out: **estendere la porta `VectorStore.query`** ad accettare più
  collezioni, **o** orchestrare il merge nella `RetrievalFacade` chiamando `query` per collezione? (La
  seconda è meno invasiva sugli adapter — vedi R-4.) → materia di `plan`.
- **DA-4 (A).** Come la facade **conosce** la seconda collezione: deriva da `Settings`/config (es. una
  lista di corpora/collezioni da interrogare) o è passata esplicitamente dal consumatore? → `clarify`/`plan`.
- **DA-5 (B).** Nome del sottocomando e degli argomenti: `upsert-index` con `--page`/`--summary`
  (e summary da stdin) sembra il più coerente con `append-log` — confermare la nomenclatura in `specify`.
- **DA-6 (B).** L'esito va modellato come **nuovo contratto** `UpsertIndexResult` (oggi `upsert_index`
  ritorna `bool`) per uniformità con `AppendLogResult`/`--json`? → `plan`.

---

### Nota per il design a valle
Confine **D↔N** confermato: tutto qui è **D** (meccanico, testabile, zero LLM). La query congiunta è
infrastruttura di retrieval; l'`upsert-index` è solo il **write idempotente** — il *cosa* scrivere
(pagina, sommario) resta **N** (giudizio LLM nel loop). Prossima fase: `/speckit-specify`.
