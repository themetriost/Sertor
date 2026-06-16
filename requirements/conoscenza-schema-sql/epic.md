# Epica — Conoscenza-schema SQL come corpus interrogabile

> Livello: **epica** — **estensione dell'epica primaria** [`../sertor-core/epic.md`](../sertor-core/epic.md).
> Porta nel corpus la **conoscenza-schema di un database** (DDL/FK, viste, stored procedure, query «buone»)
> **fusa col codice applicativo** che vi accede, così da rispondere a «dov'è un dato, quale tabella/vista/SP
> usare per accedervi». Nasce da una **ricognizione prior-art completata** ([[conoscenza-schema-sql-rag]]):
> nessun sistema esistente fonde schema + SP + query + codice in un endpoint unico — è lo spazio di Sertor.
> Si decompone in `requirements/conoscenza-schema-sql/<feature>/requirements.md` (EARS).

## 1. Visione e problema (perché)

Chi lavora su un sistema data-intensive ha una domanda ricorrente e mal servita: *«dove vive questo dato,
e qual è il modo giusto per leggerlo/scriverlo — quale tabella, quale vista, quale stored procedure, quale
query collaudata?»*. La risposta è sparsa tra **schema** (DDL/FK), **oggetti di programma** (viste, SP),
**pattern d'accesso** (query che funzionano) e **codice applicativo** che chiama il DB. La ricognizione
(DataHub/WrenAI/Vanna/RASL/SchemaGraphSQL) mostra che i sistemi esistenti coprono **pezzi** (data catalog,
semantic layer, schema-RAG, Text-to-SQL) ma **nessuno fonde** i quattro livelli — in particolare nessuno
unisce il **codice applicativo** alla conoscenza-schema.

Sertor ha l'angolo giusto: un **corpus unico** (codice+doc) + un **code-graph**. L'estensione naturale è un
**nuovo sorgente d'ingestione** (DDL/viste/SP nel corpus unico) + uno **schema-graph parallelo al
[[code-graph]]** che modella il lineage tabella↔vista↔SP↔query↔codice.

> Il *come* (parser SQL, modello del grafo schema, introspezione vs statico) è materia della **fase di
> design**. Qui solo *cosa* e *perché*.

## 2. Ambito

### In ambito
- **Ingestione della conoscenza-schema** nel corpus unico: DDL/FK, viste, stored procedure, e **query
  «buone»** documentate come pattern d'accesso (`doc_type` dedicato).
- **Schema-graph** parallelo al code-graph: entità (tabella/vista/SP/colonna) e relazioni (FK, «la SP X
  legge la tabella Y», «la query Z usa la vista W»), navigabile con la semantica di `who_calls`/`find_symbol`.
- **Fusione con il codice applicativo**: collegare l'accesso al DB nel codice (query/ORM) alle entità schema,
  così una query unica attraversa schema + SP + query buone + codice.
- **Interrogazione**: «dov'è il dato X», «come accedo a Y», «chi scrive sulla tabella Z» rispondibili dal RAG.

### Fuori ambito (per ora)
- **Text-to-SQL** / generazione di query nuove: confine dichiarato — qui si **recupera** conoscenza, non si
  genera SQL (eventuale fase successiva).
- **Introspezione live di un DB in esecuzione**: il primo taglio è **file-based** (DDL/SP come testo nel
  repo); l'introspezione runtime è una domanda di design aperta (§9).
- **Parsing sintattico di T-SQL/PL-SQL**: è il **prerequisito**, fornito dall'epica
  [`../ingestione-estesa/epic.md`](../ingestione-estesa/epic.md) (FEAT-003), non da qui.
- Definizione del *come* (parser, schema del grafo): fase di **design**.

## 3. Criteri di successo
- **CS-1 (schema nel corpus):** DDL/viste/SP di un progetto reale entrano nel corpus unico e sono
  recuperabili per significato (es. «la tabella degli ordini» trova lo schema giusto).
- **CS-2 (schema-graph):** è navigabile un grafo che collega tabella↔vista↔SP↔query↔codice; data una
  tabella si ottengono gli oggetti che la usano (analogo di `who_calls`).
- **CS-3 (fusione col codice):** una query restituisce **insieme** lo schema, la SP/vista pertinente e il
  punto del **codice applicativo** che vi accede — il valore unico identificato dalla ricognizione.
- **CS-4 (prerequisito):** poggia sul chunking sintattico T-SQL/PL-SQL (epica `ingestione-estesa`), con
  copertura dichiarata; senza, degrada onestamente al fallback testuale (mai errore silenzioso).

## 4. Stakeholder e attori
- **Dev/Owner su sistemi data-intensive:** la domanda «dove vive il dato / come accedervi».
- **Agente LLM:** consumatore — contesto schema+codice per ragionare sull'accesso ai dati.
- **Epica `ingestione-estesa`:** fornisce il parsing SQL (dipendenza a monte).
- **Il [[code-graph]] del core:** modello di riferimento per lo schema-graph (porta `CodeGraph` analoga).

## 5. Vincoli, assunzioni e dipendenze
- **Dipendenza dura da `ingestione-estesa` FEAT-003** (chunking T-SQL/PL-SQL): senza, lo schema entra solo
  come testo grezzo.
- **Riuso del corpus unico e del pattern code-graph:** lo schema-graph è un artefatto parallelo, non un
  motore nuovo; riusa ingestione/store/porte del core.
- **File-based prima dell'introspezione:** il primo taglio legge DDL/SP dai file del repo; l'introspezione
  live è opt-in/futura (R-1, §9).
- **Local-first & host-agnostico:** funziona su qualunque ospite con SQL nei sorgenti, senza un DB vivo.
- **Segreti:** eventuali stringhe di connessione mai versionate.

## 6. Rischi
- **R-1 — File statici vs realtà del DB:** DDL nel repo può divergere dallo schema reale in produzione;
  dichiarare la provenienza, valutare l'introspezione come opzione futura.
- **R-2 — Dialetti SQL:** T-SQL ≠ PL-SQL ≠ ANSI; copertura per-dialetto dichiarata, non assunta.
- **R-3 — Confine col Text-to-SQL:** facile scivolare nella generazione; tenere il taglio sul **recupero**.
- **R-4 — «Query buone» soggettive:** cosa è un buon pattern d'accesso richiede curatela; trattarle come
  doc con provenienza, non come verità assoluta.

## 7. Requisiti trasversali (EARS)
- **REQ-E1 (Optional):** *Where SQL schema sources (DDL/views/stored procedures) exist in the project, the
  system shall ingest them into the unified corpus as retrievable knowledge with a dedicated doc type.*
- **REQ-E2 (Optional):** *Where the schema-graph is built, the system shall expose relations linking
  tables↔views↔procedures↔queries↔application-code, navigable like the code-graph.*
- **REQ-E3 (Ubiquitous):** *The system shall answer data-access questions (where a datum lives, how to
  access it) by retrieving schema together with the relevant program objects and application code.*
- **REQ-E4 (Unwanted):** *If syntactic SQL parsing is unavailable, then the system shall degrade to text
  ingestion with a declared limitation rather than fail silently.*

## 8. Backlog di feature

| ID | Feature | Valore / obiettivo | Priorità (MoSCoW) | Stato |
|----|---------|--------------------|-------------------|-------|
| FEAT-001 | **Ingestione della conoscenza-schema nel corpus unico** — DDL/FK, viste, SP, query «buone» con `doc_type` dedicato | Lo schema diventa interrogabile per significato | **Should** | da decomporre — dipende da `ingestione-estesa` FEAT-003 |
| FEAT-002 | **Schema-graph parallelo al code-graph** — entità+relazioni tabella↔vista↔SP↔query, navigazione tipo `who_calls` | Lineage dei dati navigabile | **Could** | da decomporre |
| FEAT-003 | **Fusione schema ↔ codice applicativo** — collega l'accesso al DB nel codice alle entità schema | Il valore unico: una risposta che attraversa dati + codice | **Could** | da decomporre |

> **Nota sull'MVP & sequenza:** l'epica è **bloccata a monte** dal chunking SQL (`ingestione-estesa`
> FEAT-003). Sbloccato quello, il primo passo a valore è **FEAT-001** (schema nel corpus); lo schema-graph
> e la fusione col codice (Could) sono il salto che rende Sertor **unico** nel panorama (ricognizione §
> riferimenti), da affrontare se il caso d'uso data-intensive diventa prioritario.

## 9. Domande aperte
- **DA-S-a — Introspezione live vs parsing statico file-based:** [DA CHIARIRE: leggere lo schema dai file
  del repo (statico, portabile) o introspezionare un DB vivo (accurato, ma richiede connessione/segreti)?
  Default proposto: file-based nel primo taglio, introspezione come opt-in futuro.]
- **DA-S-b — Confine col Text-to-SQL:** confermato fuori scope la generazione; aperto se in futuro il
  recupero debba alimentare un generatore.
- **DA-S-c — Cattura dei «pattern d'accesso buoni»:** [DA CHIARIRE: da dove vengono le «query buone» —
  file curati, estrazione dai log, marcatura manuale? Default proposto: file curati con provenienza.]
- **DA-S-d — Modello dello schema-graph:** [DA CHIARIRE in design: riuso diretto della porta `CodeGraph`
  o una porta `SchemaGraph` sorella? Impatta il code-graph esistente.]

## 10. Riferimenti (prior art, non requisiti)
- Ricognizione completa in [[conoscenza-schema-sql-rag]]: DataHub (data catalog/MCP-native, il più vicino),
  WrenAI/Vanna (Text-to-SQL semantic layer), RASL/SchemaGraphSQL (schema-RAG accademico). Nessuno fonde
  schema + SP/viste + query buone + **codice applicativo** in un corpus unico — lo spazio di Sertor.
