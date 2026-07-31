# Inventario file-per-file — destinazione di ogni artefatto

> **Perché esiste.** Il `migration-plan.md` classificava le aree **in aggregato** (per cartella, con
> euristiche sui nomi). Su richiesta dell'utente (2026-07-31) la classificazione è rifatta **file per
> file**, leggendo il contenuto dove il nome non basta. **Alla prima area verificata l'aggregato si è
> rivelato sbagliato in 2 punti su 3** — vedi §1.
>
> **Stato:** in costruzione. Aree completate: `prototype/` (90) · `wiki/concepts/` (44). **Totale
> verificato: 134 su 1.695 file tracciati.**

## Legenda destinazioni

`SER` Sertor (RAG) · `THE` Thesmion (wiki) · `SUL` Sulcimen (metodo) · `PRO` ProtoSertor ·
`KAE` Kaelen (motore d'installazione) · `SIN` Sinthari (SpecLift/SpecAudit, D3) ·
`TRA` trasversale (copiata nei nodi che la applicano, D4) · `—` resta dov'è

---

## 1. `prototype/` — 90 file · **VERIFICATO e MIGRATO** ✅

> **Chiuso il 2026-07-31.** I 90 file hanno lasciato Sertor: **81** sono partiti col nodo
> **ProtoSertor** (repo privato proprio, 35 commit di storia), **9** sono stati **ricollocati** nel
> wiki di Sertor con `git mv` — 3 come pagine di prodotto, 6 *in transito verso Sulcimen* con la
> destinazione dichiarata in testa a ciascuna. La cartella è stata eliminata dal disco (**1,4 GB**)
> dopo aver verificato con `comm` che il corpus fosse integralmente presente nell'altro nodo.
> **ProtoSertor da qui in poi è un nodo autonomo: non gestiamo il suo repo.**

### 1.1 Ciò che l'aggregato aveva sbagliato

| Affermazione del piano | Verifica file-per-file |
|---|---|
| «i 20 file del wiki del prototipo viaggiano con lui» | **falso**: 11 a `PRO`, 6 a `SUL`, 3 a `SER` |
| «4 riferimenti operativi da ripulire» | **5** — il quinto (`.claude/commands/derive-entity-types.md`) **è già rotto dal 30/05** |
| «zero import verso il core» | ✅ confermato |

### 1.2 Codice ed esecuzione → `PRO` (70 file, verificati uno per uno)

| Gruppo | File | Dest | Nota |
|---|---|---|---|
| `01-baseline/` | README · chunking.py · eval_queries.json · evaluate.py · index.py · search.py (6) | `PRO` | motore vettoriale del prototipo |
| `02-hybrid-reranking/` | README · eval_queries.json · evaluate.py · hybrid.py · rerank.py (5) | `PRO` | |
| `03-graphrag/` | README · build_graph.py · check_config.py · compare_runs.py · evaluate.py · graph_query.py · summarize.py · settings.yaml · **13 prompt** in `grag/prompts/` (21) | `PRO` | i prompt sono di Microsoft GraphRAG |
| `04-agentic-rag/` | README · ESEMPI-agentic.md · FUSIONE.md · agent.py · autogen_app.py · compare_fusion.py · eval_results.json · eval_tasks.json · evaluate.py · langgraph_app.py · **mcp_server.py** · orchestrator.py · sk_app.py · tools.py (15) | `PRO` | `mcp_server.py` è l'**antenato** del server MCP di produzione, ma il codice è del prototipo (già reimplementato in `src/sertor_mcp/`) |
| `shared/` | `__init__` · check_embeddings · chunking_code · config · **derive_entity_types** · embeddings · llm · loaders · retrieval (9) | `PRO` | `derive_entity_types.py` è invocato da un comando di produzione **già rotto** → §1.5 |
| `tests/` | conftest + 7 test (8) | `PRO` | testano i 4 motori del prototipo |
| radice | `.env.example` · DEMOS.md · ESEMPI.md · README.md · requirements.txt · `raw/README.md` (6) | `PRO` | il README dichiara «workspace di esplorazione e apprendimento» |

### 1.3 Il wiki del prototipo — 20 file, **9 NON vanno a ProtoSertor**

| File | Titolo reale | Dest | Perché |
|---|---|---|---|
| `concepts/rag-overview.md` | Panoramica RAG e approcci | `PRO` | descrive i 4 approcci del prototipo |
| `experiments/01-baseline.md` … `04-agentic-rag.md` + README (5) | record dei 4 esperimenti | `PRO` | cronaca del prototipo |
| `index.md` · `log.md` | indice e log del wiki-prototipo | `PRO` | |
| `sources/fastapi.md` | Fonte — fastapi/fastapi (corpus campione) | `PRO` | è il corpus del prototipo |
| `syntheses/esempi-query-risposta.md` | Vetrina di esempi query→risposta per motore | `PRO` | |
| `tech/stack.md` | Stack del workspace | `PRO` | stack dell'esplorazione (azure/langchain) |
| **`concepts/ears-methodology.md`** | EARS — Easy Approach to Requirements Syntax | **`SUL`** | metodo dei requisiti, non del RAG |
| **`tech/requirements-engineering.md`** | Requirements Engineering — fase a monte del design | **`SUL`** | metodo |
| **`tech/speckit.md`** | SpecKit — governance e orchestrazione | **`SUL`** | metodo |
| **`sources/requirements-tooling-landscape.md`** | Panorama strumenti Requirements Engineering | **`SUL`** | fonte di metodo |
| **`syntheses/flusso-requisiti-implementazione.md`** | Flusso end-to-end epica → implementazione | **`SUL`** | metodo |
| **`syntheses/costituzione-produzione-proposta.md`** | Costituzione per la fase produzione — **proposta** | **`SUL`** | **antenato della costituzione ratificata** |
| **`syntheses/architettura-attuale.md`** | Architettura as-built — Sertor RAG toolset | **`SER`** | tag `produzione`: descrive il prodotto |
| **`syntheses/architettura-target.md`** | Architettura target — dual-RAG codice + doc | **`SER`** | disegno del prodotto |
| **`syntheses/epica-sertor-cli.md`** | Epica Sertor CLI — requisiti e backlog | **`SER`** | **antenato di `requirements/sertor-cli/`** |

### 1.4 La storia git: una scoperta che cambia il comando `filter-repo`

Il commit di isolamento `104e666` (2026-05-30) è una **rinomina**: `{01-baseline => prototype/01-baseline}`,
`{shared => prototype/shared}`, `{wiki => prototype/wiki}`, `{tests => prototype/tests}`, `README.md =>
prototype/README.md`, …

Conseguenza: `filter-repo --path prototype/` preserverebbe **3 commit soltanto**. La storia vera —
**36 commit** — sta sotto i **path in radice** (`01-baseline/`, `shared/`, `04-agentic-rag/`, …).

**Ma tre di quei path collidono con Sertor di oggi:** `wiki/` (547 commit, prototipo + produzione),
`tests/` (139), `README.md`. Includerli porterebbe in ProtoSertor pezzi di produzione.

> **Decisione operativa — CONFERMATA dall'utente il 2026-07-31.** Includere in `filter-repo` i path
> **non collidenti** ed **escludere** i collidenti, accettando per questi ultimi una storia che parte
> dall'isolamento. Resa: **36 commit** invece di 3, senza contaminazione.

**Verifica di collisione, path per path, contro la radice di oggi** *(fatta prima di eseguire — e ha
trovato una quarta collisione che l'elenco iniziale non aveva)*:

| Path | Esiste oggi in radice? | Decisione |
|---|---|---|
| `prototype/` | — (è la cartella da estrarre) | **includi** |
| `01-baseline/` · `02-hybrid-reranking/` · `03-graphrag/` · `04-agentic-rag/` | no | **includi** (storia pre-isolamento) |
| `shared/` · `raw/` | no | **includi** |
| `DEMOS.md` · `ESEMPI.md` · `requirements.txt` | no | **includi** |
| `wiki/` | **SÌ** — 547 commit, prototipo **+** produzione | **escludi** |
| `tests/` | **SÌ** — 139 commit di produzione | **escludi** |
| `README.md` | **SÌ** — è il README di Sertor | **escludi** |
| **`.env.example`** | **SÌ** — è il template delle manopole di produzione | **escludi** ⚠️ *quarta collisione, trovata verificando* |

I file esclusi **arrivano comunque** in ProtoSertor attraverso `--path prototype/` (oggi vivono in
`prototype/wiki/`, `prototype/tests/`, `prototype/README.md`, `prototype/.env.example`): a mancare è
solo la loro storia **anteriore** al 30/05. È il compromesso, ed è dichiarato.

### 1.5 Riferimenti a `prototype` fuori dalla cartella — 71 file

| Tipo | Quanti | File | Azione |
|---|---:|---|---|
| **Operativi** | **5** | `.gitignore` (righe 47-66) · `pyproject.toml` (riga 133, esclusione lint) · `CLAUDE.md` (10 occorrenze — **già corretta** la sezione falsa sul RAG) · **`.claude/commands/derive-entity-types.md` riga 23** · 1 test di `sertor-flow` | ripulire 4; il test resta valido com'è |
| **Narrativi** | 66 | `specs/**` · `requirements/**` · `wiki/**` · `.specify/memory/constitution.md` | **non si toccano**: sono storia e restano veri |

> ⚠️ **`.claude/commands/derive-entity-types.md` è rotto da due mesi.** Invoca
> `shared/derive_entity_types.py`, path che **non esiste dal 30/05** (l'isolamento lo ha spostato in
> `prototype/shared/`). Nessuno se n'è accorto perché nessuno ha invocato il comando. Va corretto
> **ora** (puntando a `prototype/`) e **di nuovo** dopo F1 (puntando a ProtoSertor), oppure il comando
> va ritirato se la capacità non serve più.

---

## 2. `wiki/concepts/` — 44 file · **VERIFICATO** (titolo letto per tutti; contenuto per gli ambigui)

| Pagina | Dest | Motivo |
|---|---|---|
| `retrieval-core` · `domain-model` · `ports-adapters` · `chunking-dispatch` · `indexing-and-retrieval` · `vector-retrieval` · `hybrid-retrieval` · `retrieval-confidence` · `retrieval-vs-graph` · `code-graph` · `dedup-risultati` · `llm-facing-retrieval-contract` · `valutazione-e-non-regressione` · `memoria-conversazioni` · `osservabilita` · `auto-heal-staleness` · `thin-consumer` (17) | `SER` | entità del prodotto RAG |
| `dogfooding` (18) | `SER` | *verificato leggendo*: «in Sertor è la pratica di interrogare il progetto **col proprio RAG**» |
| `mission-vision` (19) | `SER` | *verificato*: «la missione e la visione **di Sertor**». ⚠️ dopo la separazione ogni nodo avrà la sua → da riscrivere in F5 |
| `daily-distill-floor` · `diary-vs-graph` · `ritual-check` · `step-ritual` · `wiki-guard` · `wiki-role-da-w1` (6) | `THE` | entità del sistema-wiki |
| `constitution` · `fail-loud-fix-cause` (XII) · `product-plane-vs-fixture-plane` (XIII) (3) | `SUL` | *verificato*: sono **principi costituzionali**, e la costituzione va a Sulcimen |
| `speclift` · `specaudit` (2) | `SIN` | D3: il codice è di Sinthari; le pagine lo seguono |
| `dogfood-fidelity` · `esito-sull-host-vs-forma-dell-asset` · `identita-per-presenza-o-per-contenuto`* · `host-agnostico-non-e-risolvibile`* (4) | `KAE` | riguardano **installazione e consegna**, che dopo D1 vivono in Kaelen |
| `audit-codice-morto` · `confine-di-prodotto-misurato` · `default-masked-defect` · `deterministic-vs-judgment` · `guardia-verde-non-e-una-misura` · `il-rimedio-ricade-nel-difetto` · `potere-retrospettivo-di-una-guardia` · `pratica-standing-vs-pratica-distribuita` · `riassunto-invecchia-senza-riconciliatore` · `riuso-che-eredita-il-presupposto` (10) | `TRA` | lezioni di ingegneria: copiate nei nodi che le applicano |

\* **Casi discutibili, dichiarati:** `identita-per-presenza-o-per-contenuto` e
`host-agnostico-non-e-risolvibile` sono lezioni **generali** (idempotenza; risolvibilità di un
riferimento) le cui **istanze** sono d'installazione. Assegnate a `KAE` perché è lì che servono
operativamente; in alternativa `TRA`. *Da confermare.*

---

## 3. Aree ancora da verificare file-per-file

| Area | File | Stato |
|---|---:|---|
| `specs/` | 601 (81 feature) | ⏳ — la destinazione si decide **per feature**, leggendo lo `spec.md` di ciascuna |
| `wiki/` (log · experiments · sources · tech · syntheses · explainers) | 161 | ⏳ |
| `packages/` | 340 | ⏳ |
| `tests/` (root) | 174 | ⏳ |
| `requirements/` | 105 | ⏳ — **le epiche trasversali vanno riga per riga**, non per file |
| `src/` | 102 | ⏳ |
| `.claude/` | 40 | ⏳ |
| `docs/` + radice | 22 | ⏳ |
| **Totale residuo** | **1.545** | |
