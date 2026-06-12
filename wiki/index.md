---
title: Indice del Wiki — Produzione Sertor
type: index
tags: [produzione, wiki, index]
created: 2026-05-30
updated: 2026-06-12 (+ [[hybrid-retrieval]] — seconda modalità RAG e nuovo default, feature 013/PR #24; [[ports-adapters]] a cinque porte; troubleshooting in [[mcp-server]], PR #23)
sources: ["requirements/sertor-core/epic.md", ".specify/memory/constitution.md", "specs/001-nucleo-retrieval/**", "specs/002-rag-baseline/**", "src/sertor_core/**", "CLAUDE.md"]
---

# Wiki di Produzione — Sertor

Wiki della **fase di produzione** (costruzione del CLI `sertor`, vedi
[`../requirements/sertor-cli/epic.md`](../requirements/sertor-cli/epic.md)). È **nuovo** e
cumulativo: cresce a ogni sessione secondo lo schema in [`../CLAUDE.md`](../CLAUDE.md)
(sezione *Wiki & documentazione*), ispirato al pattern "LLM Wiki" di Karpathy.

> **Il wiki del prototipo è altrove e congelato.** I 4 motori RAG su FastAPI, il loro codice e il
> wiki storico vivono ora in [`../prototype/`](../prototype/) come **snapshot di sola lettura**.
> Quel wiki (`../prototype/wiki/`) è indicizzato nel **RAG di dogfooding**: per consultare il
> prototipo si interroga il server MCP **`sertor-rag`** (tool `search_code` / `search_docs` /
> `get_context` / `find_symbol` / …), non si modifica più a mano.

## 🧭 Da dove cominciare (percorsi di lettura)

Quattro porte d'ingresso, per intento — ogni percorso parte da una pagina-overview e scende al dettaglio:

| Vuoi… | Percorso |
|---|---|
| **Sapere dove siamo e cosa fare adesso** | [[roadmap]] (executive summary in testa, poi mappa feature × stato reale) |
| **Capire il prodotto (il nucleo di retrieval)** | [[retrieval-core]] → le 4 entità: [[domain-model]] · [[ports-adapters]] · [[chunking-dispatch]] · [[indexing-and-retrieval]] → le modalità RAG: [[vector-retrieval]] · [[hybrid-retrieval]] (default) → le superfici: [[thin-consumer]] · [[mcp-server]] |
| **Capire il sistema-wiki (questo wiki)** | [[architettura-wiki-llm]] → la metà deterministica [[wiki-tools]] → il principio che li separa [[deterministic-vs-judgment]] → la disciplina d'uso [[step-ritual]] |
| **Conoscere le regole del gioco** | [[constitution]] (10 principi vincolanti) · [[mission-vision]] (il perché) · [[dogfooding]] (come ci usiamo) |

La **storia** (cosa è successo, quando) sta nei record di *Experiments* qui sotto e nel
[registro giornaliero](log/index.md).

## Come è organizzato

L'area si sceglie dalla **natura** della pagina (non dalla fase): vedi l'euristica di collocazione nel
playbook (`.claude/skills/wiki-author/wiki-playbook.md`, §3).

| Cartella | Contenuto |
|----------|-----------|
| `concepts/` | Astrazioni, fondamenta, principi (evergreen) |
| `tech/` | Tecnologie, strumenti, infrastruttura (evergreen) |
| `experiments/` | Record datati di un'attività/step/feature svolta |
| `sources/` | Riassunti di fonti esterne ingerite |
| `syntheses/` | Viste d'insieme e confronti trasversali (la categoria più rara) |
| [`log/`](log/index.md) | Registro append-only, **un file per giorno** (rotazione, FEAT-008) |

## Pagine

> 🗺️ **[[roadmap]] — Roadmap & stato di prodotto (pagina viva).** Punto d'ingresso per "dove siamo":
> mappa delle feature (epica `sertor-core`/`sertor-cli`), cosa è su `master` vs su branch, lavori
> abilitanti mergiati, fasi e backlog. Tienila aperta come quadro d'insieme.

### Concepts (fondamenta e astrazioni)

- **[[retrieval-core]]** — Il **nucleo di retrieval** importabile (`sertor-core`), *il prodotto*: architettura Clean (domain/services/adapters/engines + porte `Protocol`), composition root guidato da `Settings`, backend `local`/`azure`, policy errori tollerante↔strict, collezioni namespaced per `(corpus, provider)`. CLI/MCP/wiki ne sono consumatori sottili. *Scomposto nelle 4 pagine-entità sotto.*
- **[[domain-model]]** — Le **entità dati pure** del nucleo (`Document`, `Chunk`/`ChunkMetadata`, `EmbeddedChunk`, `RetrievalResult`, `IndexReport`; enum `DocType`/`ChunkerKind`): nessun SDK nel dominio, id stabili (path POSIX, `doc_id#index`) → idempotenza del rebuild.
- **[[ports-adapters]]** — Le due **porte** `Protocol` (`EmbeddingProvider`, `VectorStore`) e gli **adapter** che le implementano (Ollama/Azure · Chroma/Azure Search); il composition root sceglie da `Settings` con import lazy. Structural typing → mockabili.
- **[[chunking-dispatch]]** — Il **chunking** `Document`→`Chunk`: dispatch per tipo/lingua (markdown / sintattico tree-sitter / fallback dimensionale), 10 linguaggi sintattici, esclusione deliberata R-N2 di PowerShell/SQL, id stabile `doc_id#index`.
- **[[indexing-and-retrieval]]** — Le **due pipeline**: indicizzazione (ingest→chunk→embed→store, atomicità del rebuild) e la **facade** `search_code/docs/combined`, tollerante su indice assente (`[]`+warning). Punto d'ingresso dei consumatori via `build_facade()`.
- **[[vector-retrieval]]** — La **prima modalità RAG**: retrieval vettoriale (embed query → similarity top-k) realizzato dal motore baseline; policy errore *strict* (`IndexNotFoundError`) + valutazione hit-rate@k/MRR@10. Dal 2026-06-12 non è più il default (→ [[hybrid-retrieval]]) ma resta la baseline di confronto, selezionabile con `SERTOR_ENGINE=baseline`.
- **[[hybrid-retrieval]]** — La **seconda modalità RAG e nuovo default** (FEAT-004, PR #24): BM25 lessicale (porta `LexicalIndex`, sidecar atomico) + via densa fusi con RRF deterministico; degradazione onesta sui corpora pre-ibrido (warning, mai errore); reranking FlashRank come extra opzionale; consumatori invariati via strategia iniettata. Qualità: simboli hit@5 0→1.00, xfail storici chiusi strict.
- **[[thin-consumer]]** — Il pattern per cui le interfacce (CLI, server MCP, tool) espongono il [[retrieval-core]] importandolo e cablandolo dalle factory `build_*`, **senza reimplementare logica**: il prodotto è la libreria, l'interfaccia è un guscio sottile (host-agnostico, Principio X). Esempio realizzato: il server MCP.
- **[[dogfooding]]** — Interrogare il progetto stesso col proprio RAG: Sertor indicizza il proprio codice/doc come corpus e li consulta coi suoi tool (server MCP `sertor-rag`) invece di leggerli a mano. Validazione continua + contesto ancorato.
- **[[deterministic-vs-judgment]]** — Il confine **meccanico** (codice, zero LLM, testabile) ↔ **giudizio** (LLM: cosa scrivere, è una contraddizione?). Principio trasversale: massimizza il deterministico, riserva all'LLM solo il giudizio; guida anche la delega.
- **[[diary-vs-graph]]** — Le **due memorie** del wiki: il **diario** (log + record datati, append-only, «cosa è successo») vs il **grafo** (pagine-entità aggiornate in place, «cosa è vero adesso»); i tre strati scrivano/cronaca/travaso (`append-log` · `record` · `distill`) e i tre ingressi della distillazione (step · backlog · conversazione intera).
- **[[constitution]]** — Ratifica Costituzione v1.0.0 (2026-05-31) → v1.1.0 (2026-06-05, aggiunto Principio X host-agnostico); 10 principi vincolanti, gate Constitution Check. Governa design e produzione.
- **[[mission-vision]]** — Mission/Vision canonizzate in README.md; Principio X come vincolo operativo; backlog: refactor host-agnostico di skill wiki/playbook/rituale.
- **[[wiki-role-da-w1]]** — DA-W1 risolta: il wiki è CORPUS + SUPERFICIE; identità, autorità, confine MVP, ruoli 1–3.
- **[[step-ritual]]** — Rituale di step (Definition of Done): a ogni step → record + lint di allineamento + azioni standing estendibili. Standing behavior vs automazione unattended; fonte unica = `CLAUDE.md`. *(Retrospettiva estratta in [[retrospettiva-interazione-2026-06-04]].)*

### Experiments (record di attività/step/feature)

- **[[epiche-sertor-core-e-cli]]** — Ristrutturazione: Sertor Core (MVP, capacità RAG + Wiki) primaria; Sertor CLI (distribuzione via CLI) secondaria. Questione aperta DA-W1 su ruolo wiki.
- **[[decomposizione-must-core]]** — Decomposizione dei 3 Must (FEAT-001/002/003); 6 decisioni di ambito MVP; nuova FEAT-009 su refresh incrementale.
- **[[chiusura-prototipo-dogfooding]]** — Isolamento del prototipo, motore corpus-aware, RAG di dogfooding su se stesso, MCP ri-puntato.
- **[[piano-nucleo-retrieval]]** — Piano SpecKit FEAT-001: architettura Clean, decisioni R1–R8, Constitution Check ✅ (Principi I+IV), modello dati, contratti, scope MVP vs post-MVP.
- **[[implementazione-nucleo-retrieval]]** — Record datato del completamento FEAT-001 (2026-06-03): 53 test, ruff clean, Constitution Check 9/9 ✅. **Distillato** (2026-06-08): l'architettura è migrata nelle 4 pagine-entità del nucleo; qui resta l'evento + esito.
- **[[motore-baseline-feat002]]** — Record FEAT-002 (2026-06-03): 67 test, Constitution 9/9 ✅, estensioni non-breaking al nucleo. **Distillato** (2026-06-08): entità in [[vector-retrieval]]/[[indexing-and-retrieval]].
- **[[nucleo-wiki-deterministico-feat003d]]** — Record FEAT-003-D (2026-06-05, PR #13): 11 moduli, 44 test, Constitution 10/10 ✅, SC-001 host-agnosticità dimostrata. **Distillato** (2026-06-08): entità in [[wiki-tools]].
- **[[ponte-d-n-host-agnostico]]** — Primo step FEAT-003-N (ponte D→N): il layer agentico (playbook + skill + comando + agente) reso host-agnostico (legge `wiki.config.toml`) e poggiato sulla CLI `sertor-wiki-tools` per il meccanico; all'LLM resta il giudizio. Rename coerente: `genera-wiki`→`wiki-author`, `playbook.md`→`wiki-playbook.md`, `wiki-keeper`→`wiki-curator` (+Bash). Tabella confine D↔N; scope leggero (zero codice).
- **[[server-mcp-produzione-feat-mcp]]** — Record FEAT-MCP (2026-06-06, PR #15): SpecKit completo, 6 test, Constitution 10/10 ✅, `.mcp.json` ri-puntato alla produzione (corpus `sertor`). **Distillato** (2026-06-08): entità in [[mcp-server]].
- **[[meccanica-log-feat008]]** — Record FEAT-008 (2026-06-08, PR #18): meccanica del log di [[wiki-tools]] — rotazione a un file/giorno, `append-log` curato in CLI, `migrate` dello storico. SpecKit completo, 22 test, Constitution 10/10 ✅. Attivazione su Sertor deferita post-merge.
- **[[store-backend-disaccoppiato-feat009]]** — Record FEAT-009 (2026-06-09): `store_backend` disaccoppiato dal provider di embeddings + `AzureEmbedder` su endpoint v1. Abilita embeddings Azure + store Chroma locale → **costruito il primo indice dogfood del corpus `sertor`** (191 doc / 1578 chunk). Distillato in [[ports-adapters]]/[[corpus-index-naming]].
- **[[spec-010-query-congiunta-e-upsert-index]]** — Feature 010 (`specs/010`, 2026-06-10): i pezzi D residui di FEAT-003 (query congiunta multi-collezione + `upsert-index` CLI) portati da requirements a **implementazione** in un SpecKit completo in giornata; 4 decisioni clarify (fail-fast su provider eterogenei, corpora da Settings, multilinea → errore, fan-out solo `search_combined`); 159 test verdi, validata live sul dogfood; PR #20.
- **[[pulizia-pycache-e-diagnosi-mcp]]** — Record del 2026-06-05: rimossi 16 dir `__pycache__` fantasma + diagnosi architetturale di `.mcp.json`. ⚠️ **Diagnosi superata il 2026-06-06** (banner nella pagina): `sertor_mcp` (PR #15) e `wiki_tools`/FEAT-003-D (PR #13) sono su master, `.mcp.json` ri-puntato alla produzione. *(Spostata da `tech/` a `experiments/`: è un record datato, non una tecnologia.)*
- **[[retrospettiva-interazione-2026-06-04]]** — Retrospettiva onesta sull'interazione del 2026-06-04 (pattern di ostruzione percepito, radici plausibili, correttivo adottato); separata dal design del rituale per atomicità.

### Sources (riassunti di fonti esterne ingerite)

- **[[karpathy-llm-wiki]]** — La **fonte fondativa** del sistema-wiki: gist originale di Karpathy (aprile 2026) — tre strati (raw/wiki/schema), tre operazioni, indice+log, il claim "sotto ~50-100k token il contesto batte il RAG" (tensione segnalata in [[wiki-role-da-w1]]), radice nel Memex di Bush.
- **[[llm-wiki-v2-agentmemory]]** — Estensione "grassa" del pattern: memory lifecycle (confidence/supersession/decay), typed knowledge graph, hybrid search con RRF, automazione event-driven + le critiche dei commentatori. Input di design per N6 e FEAT-004/005.

### Syntheses (viste d'insieme e sintesi trasversali)

- **[[roadmap]]** — 🗺️ **Roadmap & stato di prodotto (pagina viva).** Mappa feature epica × stato reale (master/branch), lavori abilitanti mergiati (incl. FEAT-009 indice dogfood), fasi, backlog e idee da discutere. Reconcilia le due numerazioni (epica `FEAT-NNN` ≠ `specs/NNN`).
- **[[architettura-wiki-llm]]** — 🗺️ **Vista d'insieme + roadmap.** Architettura del Wiki LLM dopo il ponte D→N: nucleo deterministico (`wiki_tools`) + layer agentico (4 entità host-agnostiche) + hook, separati dal confine D (meccanico) ↔ N (giudizio); una sola config. Schemi a strati, confine per operazione, lint a tre livelli (A strutturale / B semantico / C organizzativo). **Roadmap** con grafo di dipendenze e priorità. Pagina d'ingresso all'architettura.
- **[[sistema-wiki-fonte-unica]]** — Consolidamento del wiki (fonte unica playbook + tre interfacce sottili + automazione hook). Tassonomia consolidata; convenzioni esplicite; operazioni del playbook. **Modularizzato (2026-06-07):** playbook = indice + moduli `ops/*.md` caricati on-demand (progressive disclosure, resta DRY e portabile).
- **[[lint-semantico-host-agnostico]]** — 🔍 **Estensione del lint a audit globale.** 4 `kind` di artefatti (`wiki`/`requirements`/`spec`/`tracker`) dichiarati in config `[[audit]]` con profili universali nel playbook; per ogni `kind`, tassonomia di coerenza e procedura ripetibile. Host-agnostico: la rete di anti-deriva è globale, non solo wiki.
- **[[lint-organizzativo-e-reorg]]** — 🧭 **Lint livello C (organizzativo) + reorg.** La terza categoria di deriva (collocazione, atomicità, coerenza `type`↔natura, disciplina link) oltre igiene (A) e claim (B). Perché è tutto giudizio (cartella e `type` mentono insieme sul contenuto); principio "grafo non albero"; esercizio 2026-06-06 (`syntheses/` da 16/20 a 4/3/9/4, 0 link rotti).

### Tech (tecnologie e infrastruttura)

- **[[sessionstart-hook]]** — Hook SessionStart di Claude Code: carica indice + log a inizio sessione. Ruolo 1 di DA-W1 (contesto iniettato).
- **[[tree-sitter-language-pack]]** — Il binding Python (wheel precompilato) delle grammatiche tree-sitter, base del [[chunking-dispatch|chunking sintattico]]: API **a metodi** (non attributi) avvolta dal wrapper `_Node`, byte-range UTF-8, righe 0→1-based. *(Distillato 2026-06-08, allineato a `code.py`.)*
- **[[wiki-tools]]** — Il nucleo **deterministico** del wiki (`sertor-wiki-tools`): `scan`/`lint`/`validate`/`collect`/`structure`/`index` + `append-log`/`migrate` (rotazione del log a un file/giorno, FEAT-008), contratti JSON versionati, host-agnostico via `wiki.config.toml`, zero LLM/rete (stdlib). È la metà **D** del confine D↔N.
- **[[mcp-server]]** — Il server MCP `sertor-rag` (`sertor_mcp`): la superficie che espone la facade del core come 3 tool (`search_code/docs/combined`), facade memoizzata, formato citabile `path#chunk`, trasporto stdio. Esempio canonico di [[thin-consumer]].
- **[[sertor-rag-cli]]** — La CLI di esecuzione RAG `sertor-rag` (feature 011, PR #21): `index`/`search` dal terminale, exit code per scripting, anteprime troncate (`preview_chars`), osservabilità `-v`/`--log-json`/`--log-config`, validazione statica del backend (`validate_backend`). Secondo esempio realizzato di [[thin-consumer]]; comandi spartiti per DA-8 (`sertor`=installer, core=esecuzione).
- **[[sertor-installer]]** — Il pacchetto/comando installer `sertor` (feature 012, PR #22): `sertor install wiki` porta il sistema-wiki su un ospite (skill+agente+hook+rituale a marker+config inferita+struttura), non distruttivo per artefatto, idempotente, install≠run; assets **package-data** come fonte canonica (`.claude/` del repo = derivato + test di guardia). Aperto: tema lingua degli asset.
- **[[corpus-index-naming]]** — Schema naming chiarificato (dal 2026-06-04): corpus `sertor` (prodotto, radice) vs `prototype` (prototipo, congelato); indici `.index-sertor` (radice) vs `.index-prototype` (prototipo).