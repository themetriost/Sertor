---
title: Conoscenza-schema SQL come RAG — prior art e ipotesi per Sertor
type: synthesis
tags: [schema, database, sql, rag, code-graph, prior-art, semantic-layer, data-catalog, design]
created: 2026-06-15
updated: 2026-06-15
sources:
  - "https://docs.datahub.com/docs/features/feature-guides/mcp"
  - "https://github.com/Canner/WrenAI"
  - "https://github.com/vanna-ai/vanna"
  - "https://www.amazon.science/publications/rasl-retrieval-augmented-schema-linking-for-massive-database-text-to-sql"
  - "https://arxiv.org/pdf/2505.18363"
  - "https://timbr.ai/blog/why-enterprise-llms-need-sql-knowledge-graphs-for-accurate-nl2sql/"
---

# Conoscenza-schema SQL come RAG — prior art e ipotesi per Sertor

> **Cosa è questa pagina.** Ricognizione comparativa (giugno 2026) del panorama dei sistemi che
> permettono di **interrogare la conoscenza sullo schema di un database** — *dov'è un dato, com'è
> strutturato, quale tabella/vista/stored-procedure/query usare per accedervi* — e mappatura su come
> Sertor potrebbe ospitarla come capacità, fondendola col corpus esistente di codice + doc. È una
> **fonte di design**, non una feature decisa. Innescata dalla domanda utente del 2026-06-15.

## L'intento (cosa si cerca, cosa NON si cerca)

Si cerca un **knowledge layer consultabile sullo schema**: un agente (o una persona) interroga e
ottiene «per ottenere il *credit limit* del cliente attivo usa la tabella `Customers` + la vista
`v_ActiveCustomers`, oppure la SP `usp_GetCustomerCredit`». **Non** si cerca un esecutore Text-to-SQL
fine a sé (che *genera ed esegue* la query): quello è un consumatore a valle. Il valore è la
**conoscenza dei pattern d'accesso**, interrogabile e **fusa con gli altri corpus** di Sertor.

## La distinzione che separa tutto: schema statico ↔ pattern d'accesso

Il discrimine emerso da tutta la ricognizione:

- **Schema statico** — DDL, colonne, tipi, foreign key. Facile da estrarre (`INFORMATION_SCHEMA`,
  introspezione live). Dice *com'è fatto* il database.
- **Pattern d'accesso** — quale **stored procedure** esiste già, quale **vista** incapsula il join
  giusto, quale **query "buona"** risponde a una domanda ricorrente, da dove **arriva** (lineage) una
  colonna. È la *conoscenza tribale*, quella che vive nella testa delle persone o sepolta nel codice.
  Dice *come ci si accede in pratica*. **È questo il valore che si cerca**, ed è quello che pochi
  sistemi catturano in forma interrogabile.

## Il panorama, per categoria

### 1. Data catalog / metadata graph (struttura + lineage + query reali)
- **DataHub** (Apache 2.0, LinkedIn/Acryl) — il riferimento OSS più completo. Modella schema +
  **lineage column-level** + le **query reali come entità di prima classe** (`Query` con
  `querySubjects`, SP ingerite come `DataJob`). È **MCP-native**: i tool `get_dataset_queries` /
  `find_sql_context` permettono a un agente di chiedere «quali query/SP accedono al dataset X» e
  ricevere SQL reali con statistiche d'uso. È il sistema esistente più vicino all'intento.
- **OpenMetadata** (Apache 2.0) — simile, MCP server dalla v1.12 (2026); lineage da SP ancora in
  sviluppo.
- **Amundsen** (Apache 2.0) — cattura solo *popolarità* d'uso, non la struttura delle query; niente
  LLM/MCP nativo.
- **Apache Atlas** (Apache 2.0) — lineage limitato all'ecosistema Hadoop; in calo.
- **Commerciali:** **Alation** brilla qui col **Query Log Ingestion** (parsa i log SQL → ogni tabella
  sa quali query/SP la referenziano, con join e popolarità) ma **non ha MCP**; **Microsoft Purview**,
  **Unity Catalog**, **Collibra** hanno lineage automatico ma non espongono la query history
  strutturata come DataHub/Alation.

### 2. Semantic layer (concetto di business → tabelle/join *dichiarati*)
**dbt Semantic Layer/MetricFlow** (Apache 2.0), **Cube.dev**, **LookML/Looker**, **WrenAI MDL**.
Mappano metriche/dimensioni a tabelle/join e fanno generare SQL corretto *per costruzione* (accuracy
~98-100% sulle metriche note vs ~84-90% del text-to-SQL grezzo). **Limite:** modellano solo ciò che è
stato **dichiarato esplicitamente** — niente SP, niente viste ad hoc, niente query storiche. Ottimi
per «interrogare correttamente una metrica nota», non per «quale SP/vista è usata per ottenere X in
produzione». Complementari, su un piano diverso.

### 3. Schema-RAG / store di contesto per LLM (il più vicino all'intento)
- **Vanna.ai** (MIT) — RAG per text-to-SQL: indicizza in un vector store **DDL + documentazione +
  Golden SQL** (coppie domanda↔query validate). Le *Golden SQL* **sono** la forma principale di
  «quale query usare per X». Limite: il vettore è accoppiato alla pipeline SQL, non esposto come RAG
  generico consultabile.
- **WrenAI** (AGPL-3.0) — semantic layer **MDL** (modelli logici, colonne descritte, **relazioni con
  join path espliciti**, campi calcolati) indicizzato in Qdrant; MCP-native. L'approccio più ricco per
  catturare «quale vista/join», ma non tratta SP né lineage.
- **Dataherald** (Apache 2.0) — *Context Store* esplicito (metadati + docs + Golden SQL) separato dalla
  generazione SQL.
- **Defog/SQLCoder** — LLM fine-tuned, niente RAG: contesto = DDL nel prompt. Solo schema grezzo.

### 4. MCP server per database (rilevante: Sertor è MCP-native)
Ecosistema oggi dominato dall'**introspezione live**: **Postgres MCP** (reference Anthropic),
**Postgres MCP Pro** (crystaldba, aggiunge `get_top_queries` da `pg_stat_statements`), **mcp-alchemy**
(multi-DB via SQLAlchemy), **MS SQL MCP** (Tadzesi, 38 tool: elenca SP/viste con definizione, genera
data dictionary in markdown ed ER in Mermaid **on-demand**), **mssqlMCP**, **Legion MCP**. Espongono la
struttura (e a volte la generano documentata) ma **nessuno costruisce un corpus RAG persistente
interrogabile** di pattern d'accesso curati.

### 5. Ricerca accademica/industriale (valida l'approccio "schema = corpus + grafo")
- **Spider 2.0** (ICLR 2025): su schemi reali ~800 colonne GPT-4 scende al 6% — il collo di bottiglia
  **non** è generare SQL, è il **recupero selettivo del contesto-schema**. Dare lo schema grezzo non
  scala.
- **RASL** (Amazon, 2025): decompone lo schema in *entity chunk* semantici indicizzati separatamente →
  retrieval selettivo. È schema-as-RAG.
- **SchemaGraphSQL** (2025) e **DCG-SQL** (ACL 2025): rappresentano lo schema come **grafo** (tabelle/
  colonne nodi, FK archi) + pathfinding per ridurre il search space.
- **AutoLink** (2024): schema linking come **esplorazione agentica iterativa** (l'agente espande il
  subset rilevante), 97.4% recall, scala a 3000+ colonne.
- **Descrizioni colonne sintetiche** (2024): arricchire le colonne con descrizioni NL generate da LLM
  migliora il retrieval — utile per *costruire da zero* un corpus schema.
- **Timbr.ai** (commerciale): **SQL knowledge graph** ontologico (16.7% → 54.2% accuracy con GPT-4 vs
  DDL grezzo). Prova che il grafo sullo schema funziona, ma è chiuso e non componibile.

## Quadro comparativo (cattura il *pattern d'accesso*?)

| Sistema | Pattern d'accesso (SP/vista/query per X) | Corpus persistente | Grafo | MCP/LLM | Licenza |
|---|---|---|---|---|---|
| **DataHub** | ✅ query reali + SP + lineage | ✅ | ✅ metadata graph | ✅ MCP | Apache 2.0 |
| **Alation** | ✅ Query Log Ingestion | ✅ catalog | parziale | ❌ no MCP | commerciale |
| **OpenMetadata** | parziale (SP in sviluppo) | ✅ | ✅ | ✅ MCP (v1.12) | Apache 2.0 |
| **Vanna.ai** | ✅ Golden SQL + docs | ✅ vector | ❌ | API | MIT |
| **WrenAI (MDL)** | ✅ relazioni/join (no SP) | ✅ Qdrant | parziale | ✅ MCP | AGPL-3.0 |
| **Dataherald** | ✅ Golden SQL + docs | ✅ vector | ❌ | API | Apache 2.0 |
| **Timbr.ai** | ✅ ontologia + misure | ✅ grafo SQL | ✅ | SDK/LangChain | commerciale |
| **dbt/Cube/LookML** | ❌ solo metriche dichiarate | ✅ | ❌ | ✅ | misto |
| **MCP DB (Postgres/MSSQL)** | ❌ (live, no corpus) | ❌ | ❌ | ✅ MCP | OSS vari |

## Il buco che nessuno riempie (lo spazio di Sertor)

**Nessun sistema esistente** indicizza *congiuntamente* in un unico endpoint interrogabile:
**(a)** struttura schema (DDL + FK), **(b)** stored procedure / viste come unità semantiche
**documentate**, **(c)** query "buone" esistenti come pattern d'accesso, **(d)** il **codice
applicativo** che accede al DB. I data catalog fanno (a)+(b)+lineage ma sono prodotti separati e non
vedono il codice; gli schema-RAG fanno (b)+(c) ma non il grafo né il codice; gli MCP DB fanno solo
introspezione live. **Il codice applicativo che usa il DB è proprio il corpus che Sertor già
indicizza** — ed è qui che Sertor ha un angolo unico: unire la conoscenza-schema al codice che la
consuma, nello stesso retrieval.

## Mappatura su Sertor (come ci si innesterebbe)

L'intento mappa bene sull'architettura esistente — non è un mondo a parte:

1. **Nuovo sorgente di ingestione nel corpus unico.** Schema (DDL/`INFORMATION_SCHEMA`), definizioni di
   viste e SP, e *golden query* documentate entrano come documenti (`doc_type`) nel modello a **corpus
   unico** già in uso ([[indexing-and-retrieval]]). La ricerca **ibrida** ([[hybrid-retrieval]]) dà
   subito «chiedi in naturale → trova la tabella/SP pertinente», **fusa con codice e doc per
   costruzione**.
2. **Uno schema-graph parallelo al code-graph.** Il [[code-graph]] (porta `CodeGraph`:
   `find_symbol`/`who_calls`/`related_docs`/`get_context`) ha l'analogo perfetto sullo schema —
   convalidato dalla ricerca (SchemaGraphSQL, DCG-SQL): nodi = tabella/colonna/SP/vista, archi = FK +
   read/write. `who_calls` → **lineage** («quali SP scrivono questa tabella»), `related_docs` → collega
   alla documentazione di dominio, `get_context` → fonde struttura ↔ doc ↔ codice. Stesso pattern
   *scopri (ibrida) → naviga (grafo)* di [[retrieval-vs-graph]], applicato ai dati.
3. **Prerequisito noto: parsing sintattico di T-SQL/PL-SQL.** Oggi sono **deliberatamente esclusi** dal
   chunking sintattico (decisione R-N2, [[chunking-dispatch]]) e finiscono nel fallback dimensionale.
   Senza parsing si ha solo retrieval testuale (utile ma "piatto"); col parsing si estrae il grafo di
   lineage. La roadmap ha già l'idea *«promuovere PowerShell/T-SQL/PL-SQL da fallback a chunking
   sintattico»*: questa capacità le darebbe una ragione concreta.
4. **Coerenza costituzionale.** Resterebbe deterministico dove possibile (estrazione schema/grafo =
   meccanica, [[deterministic-vs-judgment]]), local-first e host-agnostico (Principio X: l'adapter di
   introspezione è host-specifico dietro porta, come `TranscriptCaptureAdapter`).

## Riferimenti tecnici da tenere se si procede

- **Modello a tre livelli di DataHub** (schema → lineage → query history come entità) è il riferimento
  architetturale per «cosa modellare».
- **WrenAI MDL + Golden SQL alla Vanna** è il riferimento per «come catturare il pattern d'accesso» in
  forma componibile e open.
- **RASL + SchemaGraphSQL** sono i paper che trattano lo schema come corpus RAG-able + grafo: la base
  teorica del nostro schema-graph.
- **AutoLink** è il riferimento per l'eventuale modalità agentica (esplorazione iterativa dello schema).

## Domande di design aperte (da sciogliere prima di una spec)

- **Sorgente del grafo:** introspezione **live** del DB (richiede connessione/credenziali host) vs
  parsing **statico** di file `.sql`/migration/SP nel repo (coerente col local-first e col fatto che
  Sertor indicizza file, non si connette a DB). Probabile **ibrido**: file statici di default,
  introspezione come adapter opzionale.
- **Confine col Text-to-SQL:** Sertor fornisce la *conoscenza* (quale SP/tabella); l'esecuzione resta
  fuori ambito o diventa un consumatore a valle?
- **Cattura dei "pattern d'accesso":** da dove? SP/viste nel repo (parsing) · query log (à la Alation,
  ma è runtime, fuori dal modello file-based) · golden query curate a mano (distillazione nel wiki).
- **Multi-dialetto:** T-SQL / PL-SQL / PostgreSQL hanno grammatiche diverse; quale copertura dichiarata
  per prime (coerente con la COVERAGE per-linguaggio del code-graph).

## Fonti

DataHub: [MCP](https://docs.datahub.com/docs/features/feature-guides/mcp) ·
[query entity](https://docs.datahub.com/docs/generated/metamodel/entities/query) ·
[AI blog](https://datahub.com/blog/ai-assisted-data-catalogs-an-llm-powered-by-knowledge-graphs-for-metadata-discovery/).
OpenMetadata: [home](https://open-metadata.org/) · [column lineage](https://docs.open-metadata.org/v1.12.x/how-to-guides/data-lineage/column).
Amundsen: [Atlan](https://atlan.com/amundsen-data-catalog/). Apache Atlas: [home](https://atlas.apache.org/).
Alation QLI: [docs](https://docs.alation.com/en/latest/OpenConnectorFramework/DiscoverMetadata/ConfigureQueryLogIngestion.html).
Purview: [lineage](https://learn.microsoft.com/en-us/purview/data-gov-classic-lineage-user-guide).
Unity Catalog: [governing AI agents](https://www.databricks.com/blog/governing-ai-agents-scale-unity-catalog).
dbt SL: [vs text-to-SQL](https://docs.getdbt.com/blog/semantic-layer-vs-text-to-sql-2026) ·
[MetricFlow OSS](https://www.getdbt.com/blog/open-source-metricflow-governed-metrics).
Cube: [AI API](https://cube.dev/blog/a-practical-guide-to-getting-started-with-cubes-ai-api).
LookML: [semantic layer AI](https://cloud.google.com/blog/products/business-intelligence/how-lookers-semantic-layer-enhances-gen-ai-trustworthiness).
Vanna.ai: [GitHub (MIT)](https://github.com/vanna-ai/vanna) · [+Qdrant](https://qdrant.tech/documentation/frameworks/vanna-ai/).
WrenAI: [GitHub (AGPL)](https://github.com/Canner/WrenAI) ·
[MDL design](https://www.getwren.ai/post/how-we-design-our-semantic-engine-for-llms-the-backbone-of-the-semantic-layer-for-llm-architecture).
Dataherald: [Context Store](https://dataherald.readthedocs.io/en/latest/context_store.html) ·
[GitHub (Apache)](https://github.com/Dataherald/dataherald).
Defog SQLCoder: [GitHub](https://github.com/defog-ai/sqlcoder).
Benchmark: [Spider 2.0 (ICLR 2025)](https://openreview.net/pdf/a580c1b9fa846501c4bbf06e874bca1e2f3bc1d0.pdf).
MCP DB: [Postgres (reference)](https://mcp.so/server/postgres/modelcontextprotocol) ·
[Postgres MCP Pro](https://github.com/crystaldba/postgres-mcp) ·
[mcp-alchemy](https://github.com/runekaagaard/mcp-alchemy) ·
[MS SQL MCP (38 tool)](https://github.com/Tadzesi/MS_SQL_MCP_Server) ·
[mssqlMCP](https://github.com/MCPRUNNER/mssqlMCP) · [Legion MCP](https://mcpservers.org/servers/TheRaLabs/legion-mcp).
Ricerca: [RASL (Amazon)](https://www.amazon.science/publications/rasl-retrieval-augmented-schema-linking-for-massive-database-text-to-sql) ·
[SchemaGraphSQL](https://arxiv.org/pdf/2505.18363) · [DCG-SQL (ACL 2025)](https://aclanthology.org/2025.acl-long.748.pdf) ·
[AutoLink](https://arxiv.org/abs/2511.17190) · [descrizioni colonne sintetiche](https://arxiv.org/pdf/2408.04691).
Knowledge graph SQL: [Timbr.ai](https://timbr.ai/blog/why-enterprise-llms-need-sql-knowledge-graphs-for-accurate-nl2sql/) ·
[Atlan: catalog come LLM KB](https://atlan.com/know/data-catalog-as-llm-knowledge-base/).
