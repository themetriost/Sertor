# Epica — Backend di store e scala del retrieval

> Livello: **epica** — **estensione dell'epica primaria** [`../sertor-core/epic.md`](../sertor-core/epic.md).
> Allarga il **substrato** su cui poggiano i motori: nuovi **backend di vector store** (oltre Chroma/Azure
> AI Search) e la **scala** quando i corpora/collezioni/provider si moltiplicano. Le porte del core
> (`VectorStore`, `CodeGraph`) sono già il seam; qui si aggiungono adapter e si spinge il fan-out
> multi-collezione (feature 010) oltre il caso a 2 corpora. Si decompone in
> `requirements/backend-store-scala/<feature>/requirements.md` (EARS).

## 1. Visione e problema (perché)

Il motore ibrido è **store-agnostico via porte**, ma in pratica gli store reali sono due (Chroma locale,
Azure AI Search). Ospiti enterprise usano **PGVector** o **MongoDB/Atlas** su Azure: senza adapter, Sertor
non li raggiunge. In parallelo, la **scala** apre tre fronti già emersi ma orfani: indici **multi-provider
in parallelo** (più embedder/dimensioni che coesistono), **query federata su >2 corpora** (la feature 010
fa fan-out, ma il caso a N collezioni e il dedup cross-collezione restano da estendere), e il **code-graph
in-memory** (`networkx`) che non regge oltre ~50k nodi.

Il valore: rendere il retrieval **portabile su store cloud alternativi** e **capace di scalare** su corpora
grandi e su flotte di collezioni, riusando le porte invece di riscrivere i motori.

> Il *come* (schema adapter, store a grafo persistente, protocolli) è materia della **fase di design**.

## 2. Ambito

### In ambito
- **Nuovi adapter `VectorStore`** dietro la porta esistente: **PGVector** e **MongoDB/Atlas** su Azure
  (hybrid search nativo dove disponibile).
- **Indici multi-provider in parallelo**: più collezioni con embedder/dimensioni diverse che coesistono
  e si interrogano senza mescolarsi (oltre il namespacing `(corpus, provider)` odierno).
- **Query federata su >2 corpora / fan-out a N collezioni**: estende la feature 010 (oggi pensata per
  corpora disgiunti, taglio a pochi) con **dedup cross-collezione v2** e `search_docs` esteso al fan-out.
- **Scala del code-graph**: backend a grafo **persistente/oltre in-memory** (es. Neo4j opzionale) quando
  i nodi superano la soglia pratica del `networkx`.
- **Portabilità & isolamento dipendenze**: ogni nuovo backend è un **extra opzionale**, il core resta
  senza dipendenze obbligatorie nuove (Principio III).
- **Onestà sullo store cloud esistente**: la traccia **Azure AI Search** (`store_backend=azure`) è già
  cablata ma **a zero test**, con la **memoria semantica** latentemente rotta su questo path; va **testata
  o dichiarata *experimental*** — niente degradazione silenziosa (Principio XII). *(FEAT-007, ex A-11 del
  backlog SWOT 2026-07-02.)*

### Fuori ambito
- **Qualità** della pertinenza (metriche, HyDE, soglie): epica
  [`../retrieval-qualita/epic.md`](../retrieval-qualita/epic.md).
- **Uso collaborativo** di uno store condiviso (chi/quando rebuild, indice di team): epica
  [`../multiutente/epic.md`](../multiutente/epic.md) (qui si fornisce l'adapter, non il workflow).
- **Trasporti di rete del server MCP** (HTTP/SSE, auth): estensione di `FEAT-MCP` nel core (vedi nota lì).
- Definizione del *come* (schema, protocolli, deployment): fase di **design**.

## 3. Criteri di successo
- **CS-1 (nuovo store):** lo stesso corpus si indicizza e si interroga su ≥1 nuovo backend (PGVector o
  Mongo) **senza modifiche ai motori**, solo via config/extra.
- **CS-2 (isolamento):** installare/usare un nuovo backend **non** introduce dipendenze obbligatorie per
  chi resta su Chroma locale (extra opzionale, import lazy).
- **CS-3 (multi-provider):** due collezioni con provider/dimensioni diverse coesistono e si interrogano
  senza contaminarsi, in **0** casi di mismatch dimensionale silenzioso.
- **CS-4 (fan-out N):** una query federata su **N>2** collezioni restituisce risultati deduplicati e
  ordinati in modo deterministico, con fail-fast sui provider eterogenei (come la 010).
- **CS-5 (graph scale):** il code-graph regge un corpus oltre la soglia in-memory odierna senza degrado
  funzionale dei tool (`find_symbol`/`who_calls`), o dichiara esplicitamente il limite.

## 4. Stakeholder e attori
- **Owner/maintainer & team enterprise:** vogliono usare lo store cloud che già hanno.
- **Operatore di repo grandi:** ha bisogno che graph e fan-out reggano la scala.
- **Il core (porte `VectorStore`/`CodeGraph`):** il seam su cui questi adapter si innestano.
- **Epica `multiutente`:** consumatore a valle (store condiviso).

## 5. Vincoli, assunzioni e dipendenze
- **Porte invariate:** i nuovi backend implementano `VectorStore`/`CodeGraph` esistenti; i motori non cambiano.
- **Extra opzionali & lazy:** ogni backend è un extra (come `graph`/`rerank`/`azure`), import lazy in
  `composition.py`; default = comportamento odierno.
- **Riuso feature 010:** il fan-out multi-collezione esiste; qui si estende (N corpora, dedup v2), non si riscrive.
- **Segreti:** credenziali store mai versionate.
- **Local-first preservato:** nessun nuovo backend è obbligatorio per girare in locale.

## 6. Rischi
- **R-1 — Frammentazione adapter:** ogni store ha quirk (hybrid nativo, limiti di batch — vedi il cap
  Chroma già emerso); rischio di logica duplicata. Mitigare tenendo i motori store-agnostici.
- **R-2 — Mismatch dimensionale** tra provider in parallelo → risultati silenziosamente sbagliati;
  fail-fast obbligatorio (lezione della feature 010).
- **R-3 — Dipendenza pesante del grafo persistente** (Neo4j) → conflitti d'ambiente; tenerlo opzionale/isolato.
- **R-4 — Scope creep verso una piattaforma dati:** restare adapter sottili sulle porte, non un ORM.

## 7. Requisiti trasversali (EARS)
- **REQ-E1 (Optional):** *Where a new vector-store backend is configured, the system shall index and query
  through the existing `VectorStore` port without changes to the engines.*
- **REQ-E2 (Unwanted):** *If a new backend's dependencies are not installed, then the system shall not
  require them for the default local configuration (optional extra, lazy import).*
- **REQ-E3 (Unwanted):** *If collections use heterogeneous embedding providers/dimensions, then a federated
  query shall fail fast rather than mix incompatible vectors.*
- **REQ-E4 (Ubiquitous):** *The system shall keep local-first operation intact: no new backend is required
  to run locally.*

## 8. Backlog di feature

| ID | Feature | Valore / obiettivo | Priorità (MoSCoW) | Stato |
|----|---------|--------------------|-------------------|-------|
| FEAT-001 | **Adapter VectorStore PGVector (Azure)** dietro la porta esistente | Retrieval su Postgres/PGVector cloud | **Should** | da decomporre |
| FEAT-002 | **Adapter VectorStore MongoDB / Atlas (Azure)** (vector + eventuale Atlas Search ibrido) | Retrieval su Mongo/Cosmos cloud | **Could** | da decomporre |
| FEAT-003 | **Indici multi-provider in parallelo** — collezioni con embedder/dimensioni diverse coesistenti, interrogabili senza contaminazione | Convivenza locale↔Azure / modelli diversi | **Could** | da decomporre |
| FEAT-004 | **Query federata su >2 corpora / fan-out a N collezioni** — estende la feature 010 (fail-fast su provider eterogenei) | Scala del retrieval multi-corpus | **Could** | da decomporre |
| FEAT-005 | **`search_docs` esteso al fan-out + dedup cross-collezione v2** | Ricerca doc su più collezioni senza duplicati | **Could** | da decomporre |
| FEAT-006 | **Scala del code-graph oltre l'in-memory** — backend a grafo persistente (Neo4j opzionale) oltre la soglia ~50k nodi del `networkx` | Il grafo regge repo grandi | **Could** | da decomporre |
| FEAT-007 | **Azure AI Search: dichiarare *experimental* o testare** — la traccia store cloud odierna (`store_backend=azure`) è **a zero test**, e la **memoria semantica** è **latentemente rotta** su questo path (`SERTOR_MEMORY_SEMANTIC` + store Azure). O si copre con test reali (marker `cloud`) o si dichiara esplicitamente *experimental* nella doc/config, senza degradazione silenziosa (Principio XII) | Onestà sullo stato del backend online già esistente + memoria semantica non silenziosamente rotta | **Should** | da decomporre |

> **Nota sull'MVP:** il primo passo a valore è **FEAT-001** (PGVector): un secondo store cloud reale,
> dietro la porta, prova la portabilità del substrato. Il resto (multi-provider, fan-out N, graph scale)
> sono Could che si attivano quando un ospite reale li richiede.

## 9. Domande aperte
- **DA-B-a — Hybrid nativo vs delega:** [DA CHIARIRE: per Mongo/Atlas e PGVector, l'ibrido (lessicale+denso)
  si delega allo store nativo o resta l'RRF del motore? Default proposto: riusare l'RRF del motore, store
  solo per il denso, finché il nativo non dà un vantaggio misurato.]
- **DA-B-b — Soglia reale del grafo in-memory:** [DA CHIARIRE: la soglia ~50k è stimata; misurarla sul
  dogfood/un repo grande prima di scegliere un backend persistente.]
