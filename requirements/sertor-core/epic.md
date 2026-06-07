# Epica — Sertor Core (capacità: motori RAG + skill LLM Wiki, production-grade)

> Livello: **epica PRIMARIA (MVP)**. È il **cuore** del prodotto: la possibilità di **creare** i RAG
> (vettoriale, ibrido, grafico, agentico) e le **skill** per **creare e gestire l'LLM Wiki**.
> La **distribuzione/uso via CLI** è un'epica **secondaria** ([`../sertor-cli/epic.md`](../sertor-cli/epic.md)),
> che si appoggia a questo core. Le feature (§8) si decompongono in
> `requirements/sertor-core/<feature>/requirements.md` (EARS).

## 1. Visione e problema (perché)

Il valore del prodotto **non** è "una CLI": è **la capacità stessa** di costruire conoscenza
recuperabile da una codebase. Il core è duplice:

1. **Creare un RAG** sul codice/documentazione di un progetto, in quattro modalità complementari —
   **vettoriale** (baseline), **ibrido** (dense + lessicale + reranking), **grafico** (code-graph /
   GraphRAG), **agentico** (retrieval iterativo/multi-step);
2. **Creare e gestire un LLM Wiki**: una base di conoscenza Markdown che indicizza il progetto,
   documenta in continuo, archivia/distilla le conversazioni e si mantiene viva nel tempo.

Queste capacità **esistono già nel prototipo** ([`../../prototype/`](../../prototype/)) ma a livello
**esplorativo, non production-grade**. Il core va quindi **riscritto** partendo dal prototipo come
**riferimento** (consultabile via il RAG di dogfooding `sertor-rag`), portandolo a qualità di
produzione: testato, configurabile, repo-agnostico, osservabile, riusabile come libreria/skill.

> Il *come* (stack, API, struttura del codice) è materia della **fase di design** a valle. Qui solo
> *cosa* e *perché*.

## 2. Ambito

### In ambito
- **Creazione di RAG** sul codice+doc di un progetto nelle quattro modalità (vettoriale, ibrido,
  grafico, agentico), production-grade e selezionabili.
- Un **nucleo di retrieval condiviso** su cui i motori si appoggiano: ingestione, chunking
  code-aware, embeddings multi-provider, astrazione del vector store, facade di retrieval.
- **Skill per l'LLM Wiki**: **creare/indicizzare** il wiki, **mantenerlo vivo** (spider/lint), e
  l'**arricchimento bidirezionale Wiki↔RAG**.
- **Configurabilità** delle capacità: provider LLM/embeddings, backend di retrieval (locale/cloud),
  senza modificare il codice.
- **Repo-agnosticità**: le capacità si applicano a un progetto qualunque (il dogfooding sul prototipo
  ne è l'acceptance test).
- Riusabilità come **libreria/skill** indipendentemente dal veicolo di distribuzione (la CLI).

### Fuori ambito
- **Confezionamento/installazione/distribuzione** (pacchetto `uv`/`pip`, comando `sertor`, setup su
  repo target): è l'epica **secondaria** `sertor-cli`.
- Definizione del *come* (stack interno, API, schema dati, struttura del codice): fase di **design**.
- Creazione dei *contenuti* RAG/Wiki di uno specifico progetto: è **uso** dello strumento.
- GUI/web: il core è capacità + skill, non interfaccia.

## 3. Criteri di successo
<!-- misurabili e tech-agnostici -->
- **CS-1 (creare RAG, baseline):** data una codebase, il sistema costruisce un indice **vettoriale**
  interrogabile e restituisce risultati pertinenti su query note (verificabile su un corpus campione).
- **CS-2 (quattro modalità):** sono disponibili e selezionabili **4** modalità di RAG (vettoriale,
  ibrido, grafico, agentico); ciascuna è interrogabile e copre il proprio caso d'uso.
- **CS-3 (skill wiki):** il sistema può **creare/indicizzare** un LLM Wiki da un progetto e
  **mantenerlo** (rigenerazione indice + validazione link) in modo **idempotente** (re-run senza divergenze).
- **CS-4 (production-grade):** ogni capacità ha **test automatici**, è **configurabile** (provider/backend
  via config, senza toccare il codice) e **non** dipende da un singolo provider cloud per funzionare.
- **CS-5 (repo-agnostico):** le capacità funzionano su **≥2** codebase diverse senza modifiche al codice
  (es. il prototipo stesso + un secondo repo), a dimostrazione della portabilità.
- **CS-6 (arricchimento):** un aggiornamento del RAG può usare **sia** i sorgenti **sia** il wiki come
  input, in modo dimostrabile (entrambe le sorgenti contribuiscono al risultato).
- **CS-7 (LLM configurabile):** il sistema funziona con **≥1 provider cloud** (default) **e** con
  un'opzione **locale**; senza un LLM configurato le operazioni che lo richiedono sono bloccate.

## 4. Stakeholder e attori
- **Owner/maintainer (tu):** progetta e usa le capacità del core.
- **Team interno (futuro):** riusa i motori RAG e le skill wiki su altri progetti.
- **Agente LLM (es. Claude Code):** attore non umano primario — **consuma** il RAG e il wiki come
  contesto/strumenti (è il principale "utente" delle capacità).
- **Epica `sertor-cli` (consumatore a valle):** installa/configura/esegue queste capacità.
- **Codebase target:** il progetto su cui si crea il RAG e il wiki.

## 5. Vincoli, assunzioni e dipendenze
- **Punto di partenza:** il **prototipo** (`prototype/`) è il **riferimento** funzionale, consultabile
  via il RAG di dogfooding `sertor-rag`. Il core è una **riscrittura production-grade**, non un
  refactor in-place del prototipo.
- **Production-grade:** testabilità, configurazione centralizzata, osservabilità minima, gestione
  errori esplicita; niente over-engineering.
- **LLM/embeddings:** un target LLM è **obbligatorio** dove serve; **default = provider cloud**,
  con opzione **locale** supportata. (Set provider: vedi epica CLI per la configurazione.)
- **Retrieval/vector store:** astratto; **vector DB condizionale** — necessario per le modalità
  testuali (vettoriale/ibrido), **non** per la modalità puramente strutturale/grafico.
- **Local-first supportato** (non default): ogni capacità deve poter girare in locale.
- **Segreti:** mai persistiti in file versionati.
- **Dipendenze pesanti** (es. motore grafico/GraphRAG) **isolabili** per evitare conflitti.

## 6. Rischi
- **R-1 — Qualità retrieval insufficiente:** un RAG production-grade richiede valutazione della
  pertinenza; senza metriche, la qualità regredisce.
- **R-2 — Drift Wiki↔codice:** se la manutenzione (spider/lint) non è robusta/idempotente, il wiki
  diverge dal progetto e degrada il RAG documentale.
- **R-3 — Conflitti di dipendenze** tra modalità (es. grafico) → ambienti non risolvibili.
- **R-4 — Riscrittura sotto-stimata:** "rendere production-like" il prototipo può nascondere debito;
  rischio di reimplementare 1:1 l'esplorativo senza alzarne la qualità.
- **R-5 — Ruolo del wiki** (chiarito: §9, DA-W1 risolta il 2026-05-31 — identità corpus+superficie,
  MVP = creazione/indicizzazione). Rischio residuo: tenere la decomposizione di FEAT-003/007/008
  allineata a questo modello a due assi.

## 7. Requisiti trasversali (EARS)
<!-- solo i pochi requisiti davvero trasversali a tutta l'epica -->
- **REQ-E1 (Ubiquitous):** *The system shall expose its RAG-creation and wiki capabilities as reusable
  components, independent of any installation/CLI layer.*
- **REQ-E2 (Optional):** *Where a RAG modality requires text embeddings, the system shall require a
  configured embeddings provider and a vector store; for the purely structural (graph) modality it
  shall operate without a vector store.*
- **REQ-E3 (Ubiquitous):** *The system shall require a configured LLM target before performing any
  operation that needs generation/agentic reasoning.*
- **REQ-E4 (Optional):** *Where a local-only configuration is selected, the system shall operate
  without requiring any cloud service.*
- **REQ-E5 (Unwanted):** *If a configuration value is a secret, then the system shall not persist it
  in a version-controlled file.*
- **REQ-E6 (Event-driven):** *When the wiki maintenance (spider/lint) runs more than once on an
  unchanged project, the system shall produce a stable result (idempotence).*

## 8. Backlog di feature

| ID | Feature | Valore / obiettivo | Priorità (MoSCoW) | Stato |
|----|---------|--------------------|-------------------|-------|
| FEAT-001 | **Nucleo di retrieval condiviso** (ingestione repo-agnostica, chunking code-aware, embeddings multi-provider, astrazione vector store, facade di retrieval) | Fondazione production-grade su cui poggiano tutti i motori | **Must** | [decomposta](nucleo-retrieval/requirements.md) |
| FEAT-002 | **Motore RAG vettoriale (baseline)** production-grade | La capacità minima di "creare un RAG" interrogabile | **Must** | [decomposta](rag-baseline/requirements.md) |
| FEAT-003 | **Skill: creare/indicizzare l'LLM Wiki** (indicizza il progetto in MD, documenta in continuo, archivia/distilla conversazioni) | Conoscenza persistente e cumulativa del progetto | **Must** | consolida FEAT-010 (e2e); **in progress** (vince 010) — [decomposta](wiki-creazione/requirements.md) |
| FEAT-004 | **Motore RAG ibrido + reranking** (dense + lessicale/BM25 + reranking) | Qualità di retrieval superiore al baseline | **Should** | da decomporre |
| FEAT-005 | **Motore RAG a grafo** (code-graph AST / GraphRAG) | Retrieval strutturale/relazionale; non richiede vector DB | **Should** | da decomporre |
| FEAT-006 | **Motore RAG agentico** (retrieval iterativo/multi-step, query planning) | Risposte composite su domande complesse | **Should** | da decomporre |
| FEAT-007 | **Skill: mantenere il wiki vivo** (spider/lint: rigenera indice, valida link, rileva orfani/contraddizioni, distilla raw→concept) | Tiene il wiki coerente e aggiornato (idempotente) | **Should** | da decomporre |
| FEAT-008 | **Arricchimento bidirezionale Wiki↔RAG** (wiki → parte documentale del RAG; sorgenti → parte codice del RAG + fondamenta del wiki) | Loop virtuoso doc/codice che migliora retrieval e documentazione | **Could** | da decomporre |
| FEAT-009 | **Manutenzione/refresh incrementale dell'indice RAG sui sorgenti** (aggiorna l'indice solo sui file cambiati, senza full re-index) | Tiene il RAG fresco su repo grandi senza ricostruire tutto; pendant per i sorgenti di FEAT-007 (wiki) | **Could** | da decomporre |
| FEAT-MCP | **Server MCP di produzione** (`sertor_mcp`): espone il retrieval del core come tool MCP a un client (es. Claude Code); superficie sottile su `build_facade`, host-agnostica; sostituisce il server del prototipo | Superficie finale del core: rende il RAG usabile nativamente da un agente LLM; enabler del probe-RAG del lint wiki, del dogfood di produzione e dell'agente Azure | **Should** | [decomposta](mcp/requirements.md) |

> **Nota sull'MVP (Must):** la prima release del core deve dimostrare **(1)** la creazione di un RAG
> **vettoriale** funzionante poggiato sul **nucleo condiviso**, e **(2)** la **creazione di un LLM Wiki**.
> Ibrido/grafo/agentico e la manutenzione/arricchimento del wiki seguono come incrementi (Should/Could),
> riusando il nucleo. Le quattro modalità RAG restano tutte parte del **core** della visione.

> **Decomposizione di FEAT-003 (2026-06-05) — refactor host-agnostico lungo il confine meccanico↔giudizio:**
> - **FEAT-003-D — Nucleo wiki deterministico host-agnostico** (config `wiki.config.toml` + `wiki_tools`:
>   profile/structure/scan/collect/lint-meccanico/index-log mechanics/idempotenza — REQ-001..006, REQ-011/012,
>   REQ-050/051, FR-006-meccanico, FR-009/010/011). **Zero LLM.** → portata avanti via **SpecKit**
>   (branch+PR, Constitution Check, gate **Principio X**).
> - **FEAT-003-N — Operazioni wiki assistite da LLM** (record-contenuto, distill, generazione, ingest-compile,
>   lint semantico, giudizio verità/obsolescenza, gate al commit human-in-the-loop). → tracciata come
>   **TODO collaborativo** in [`wiki-llm/TODO.md`](wiki-llm/TODO.md), affrontata passo-passo (non SpecKit).

## 9. Decisioni risolte

### DA-W1 (risolta 2026-05-31) — Ruolo di prodotto dell'LLM Wiki

Modello a **due assi ortogonali**: **corpus** (*cosa* è indicizzato/conosciuto) × **superficie** (*come*
vi si accede e che forma hanno i risultati). Il wiki si colloca su **entrambi**.

| Tema | Decisione |
|------|-----------|
| **Identità** | Il wiki è **corpus + superficie** (entrambi): **ingerito nel RAG** *e* **navigabile per struttura** (indice → pagina → backlink). Le due porte restano aperte. |
| **Autorità nel ranking** | **Paritario** sull'asse corpus: un chunk di wiki pesa come uno di codice (nessun boost). L'autorevolezza del wiki deriva dalla **superficie strutturata** (*come* vi si accede), **non** dal ranking semantico. |
| **Tre ruoli** | (1) **contesto iniettato** [push; usa la superficie strutturata]; (2) **query precisa** [pull strutturato; superficie wiki-nativa]; (3) **ingestion nel RAG** [asse corpus — **già attivo** nel dogfood: `search_docs` restituisce pagine del wiki]. |
| **Confine MVP** | L'MVP del core (FEAT-003, **Must**) = **creare + indicizzare nel RAG** (ruolo 3). La superficie wiki-nativa (ruoli 1 e 2), lo spider/lint (FEAT-007) e l'arricchimento (FEAT-008) sono **post-MVP**. |
| **Ruolo 1 (contesto iniettato)** | **Competenza dell'host** (es. hook `SessionStart` di Claude Code, già funzionante), **non** capacità di prodotto nell'MVP. Sertor **espone** il wiki (indice/pagine); l'host decide *cosa/quando* iniettare. Non preclude un futuro "context payload" generato da sertor. |

> Approfondimento del modello **corpus × superficie** e della meccanica dell'**hook SessionStart** (la
> prova vivente del ruolo 1): nel wiki di produzione, `wiki/concepts/wiki-role-da-w1.md` e
> `wiki/tech/sessionstart-hook.md`.

### DA-2 (risolta 2026-05-31) — Confine "Must" del wiki

Confermato: l'MVP del wiki è la **sola creazione/indicizzazione** (ruolo 3, ingestion nel RAG); niente
spider. "Mantenere" (spider/lint, **FEAT-007**) resta **Should**, post-MVP.
