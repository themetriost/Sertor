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
| FEAT-003 | **Skill: creare/indicizzare l'LLM Wiki** (indicizza il progetto in MD, documenta in continuo, archivia/distilla conversazioni) | Conoscenza persistente e cumulativa del progetto | **Must** | ✅ **COMPLETATA (2026-06-10)** — consolida FEAT-010 (e2e); D al 100% + tutte le operazioni N chiuse o riassegnate (N1/N2/N3/N4/N6/N8 ✅ · N5/N9 → FEAT-007 · N7 ⛔ by design) — [decomposta](wiki-creazione/requirements.md) |
| FEAT-004 | **Motore RAG ibrido + reranking** (dense + lessicale/BM25 + reranking) | Qualità di retrieval superiore al baseline | **Should** | ✅ **CONSEGNATA (2026-06-12, PR #24)** — motore di DEFAULT (`SERTOR_ENGINE=hybrid`), xfail storici chiusi strict — [decomposta](motore-ibrido/requirements.md) |
| FEAT-005 | **Motore RAG a grafo** (code-graph AST / GraphRAG) | Retrieval strutturale/relazionale; non richiede vector DB | **Should** | ✅ **CONSEGNATA (2026-06-12, PR #25)** — code-graph strutturale, i 4 tool MCP tornati (superficie a 7) — [decomposta](motore-grafo/requirements.md) |
| FEAT-006 | **Motore RAG agentico** (retrieval iterativo/multi-step, query planning) | Risposte composite su domande complesse | **Should** | ✅ **SODDISFATTA IN FORMA COMPOSITA (2026-06-13, decisione utente)**: la capacità agentic RAG **esiste** — l'agente è il client MCP (frontier) che pianifica, orchestra i 7 tool, itera e cita; nessun motore incorporato costruito né necessario (un loop con modello minore non migliorerebbe l'orchestratore frontier). L'**agenzia incorporata** (`ask` per CLI/script, digest MCP, porta LLMProvider) è **❌ ABBANDONATA by design (2026-06-16, decisione utente: «non ci serve»)**: i 36 REQ in [motore-agentico/](motore-agentico/requirements.md) restano elicitazione storica, non pianificata |
| FEAT-007 | **Skill: mantenere il wiki vivo** (manutenzione deterministica + tema lingua) | Tiene il wiki coerente e aggiornato (idempotente) | **Should** | [decomposta](manutenzione-wiki/requirements.md) **(2026-06-12, con gap analysis e D1..D4 risolte)** — perimetro asciugato: lint B (N5) e lint C/reorg (N9) GIÀ coperti come metodo nel playbook ed esercitati; **probe di freschezza ELIMINATO** (D1, decisione utente: falsi positivi sui `sources` larghi, il lint B del rituale lo batte). Restano 22 REQ: `move`-con-link, `reconcile` detection su `status: superseded` (risoluzione sempre su conferma), `collect`+status, seed `structure init` localizzati (tabella it/en), **tema lingua risolto** (D4: asset installer → INGLESE canonico, la `language` governa la lingua del contenuto — coordinamento FEAT-012) |
| FEAT-008 | **Arricchimento bidirezionale Wiki↔RAG** (wiki → parte documentale del RAG; sorgenti → parte codice del RAG + fondamenta del wiki) | Loop virtuoso doc/codice che migliora retrieval e documentazione | **Could** | ✅ **SODDISFATTA IN FORMA COMPOSITA (2026-06-16, verificata live)** — come FEAT-006: il loop esiste già dalla somma di **corpus unico** (D-21: il wiki è `doc_type=doc` nel corpus, `ingestion.py:84`; `search_docs` restituisce pagine wiki) + indexing sorgenti + skill `generate`/`distill` (sorgenti→wiki) + fusione codice↔doc dei tool code-graph (`get_context`/`related_docs` includono le pagine wiki) + re-index a fine step (loop chiuso). CS-6 **dimostrato** via MCP sul dogfood. **Residuo scorporato** (capacità nuova, non questa): *rilevamento ATTIVO dei gap di documentazione* (il RAG che segnala entità di codice non documentate) → roadmap *Nuove funzionalità* |
| FEAT-009 | **Manutenzione/refresh incrementale dell'indice RAG sui sorgenti** (aggiorna l'indice solo sui file cambiati, senza full re-index) | Tiene il RAG fresco su repo grandi senza ricostruire tutto; pendant per i sorgenti di FEAT-007 (wiki) | **Could** | **decomposta (2026-06-16)** → [`refresh-incrementale/requirements.md`](refresh-incrementale/requirements.md) (18 REQ EARS; decisioni utente **F1** vettore incrementale + BM25/code-graph ricostruiti dal ledger · **F2** incrementale **di default**, full su `--full`; prior art CocoIndex/LlamaIndex/LangChain: ledger mtime+hash, upsert/delete mirati, gestione cancellazioni, invalidazione su cambio-logica). **Mitigata operativamente (2026-06-10):** regola standing nel rituale di step (`CLAUDE.md`, punto 5 *Re-index dei corpora toccati*): full rebuild manuale a fine step / dopo merge. **Corollario di costo (2026-06-15):** [`refresh-incrementale/corollario-costo.md`](refresh-incrementale/corollario-costo.md) (discover+chunk+store+BM25+grafo full ogni volta; ~2,7 MB/s → ospiti grandi = minuti) |
| FEAT-010 | **Fonti di ingestione estese** — repository **remoti** (clone da URL) e formati **non-testo** (PDF/DOCX/notebook) oltre a codice+Markdown locale | Allarga il corpus oltre il filesystem testuale locale dell'MVP (FEAT-001) | **Could** | **promossa all'epica dedicata** [`ingestione-estesa`](../ingestione-estesa/epic.md) (FEAT-001/002), 2026-06-16 — vi confluiscono anche chunking PS/SQL/Bash e no-code-first |
| FEAT-011 | **Embedder locale deterministico per eval/CI (local-first)** — un backend di embeddings **offline, deterministico, zero-dipendenze** (selezionabile via config) che produce vettori stabili **senza cloud né Ollama**, così `sertor-rag eval`/`graph-eval` (e la futura CI) girano **senza rete** con metriche ripetibili. Onora il local-first (Principio II) | Rende il gate di non-regressione eseguibile in CI senza cloud — **prerequisito di [E10 FEAT-003 CI Linux]**; rafforza il local-first | **Should** | ✅ **CONSEGNATA (2026-06-21, merge `34b599a`)** → [`embedder-locale/requirements.md`](embedder-locale/requirements.md) (62 REQ EARS); pipeline SpecKit req→implement completa, Constitution 12/12, suite verde. Debito P2 residuo: TASK-D04 (flag installer `--backend`→`--provider`). Decisioni utente: due provider locali deterministici — `glove` (GloVe 6B 300d, PDDL, **nuovo default**, semantica NL locale) + `hash` (char-n-gram, stdlib, **pavimento** zero-download airgapped/CI); manopola dedicata `SERTOR_EMBED_PROVIDER`; download GloVe alla 1ª indicizzazione + cache utente condivisa + override path; fail-loud (Principio XII). Emersa dall'**audit RAG** + design CI |
| FEAT-MCP | **Server MCP di produzione** (`sertor_mcp`): espone il retrieval del core come tool MCP a un client (es. Claude Code); superficie sottile su `build_facade`, host-agnostica; sostituisce il server del prototipo | Superficie finale del core: rende il RAG usabile nativamente da un agente LLM; enabler del probe-RAG del lint wiki, del dogfood di produzione e dell'agente Azure | **Should** | [decomposta](mcp/requirements.md) |

> **Nota sull'MVP (Must):** la prima release del core deve dimostrare **(1)** la creazione di un RAG
> **vettoriale** funzionante poggiato sul **nucleo condiviso**, e **(2)** la **creazione di un LLM Wiki**.
> Ibrido/grafo/agentico e la manutenzione/arricchimento del wiki seguono come incrementi (Should/Could),
> riusando il nucleo. Le quattro modalità RAG restano tutte parte del **core** della visione.

> **Epiche-estensione del core (2026-06-16, dal [backlog audit](../../wiki/syntheses/backlog-audit-2026-06-15.md)):**
> il materiale di retrieval avanzato finora orfano è stato promosso a **epiche dedicate** che estendono
> questo core (riusando porte/motori): [`retrieval-qualita`](../retrieval-qualita/epic.md) (misura+leve di
> qualità; vi confluiscono i Could H7/H8/H11 di [`hardening-produzione`](hardening-produzione/)),
> [`backend-store-scala`](../backend-store-scala/epic.md) (nuovi store + scala multi-corpus/grafo),
> [`ingestione-estesa`](../ingestione-estesa/epic.md) (FEAT-010 + chunking PS/SQL + no-code),
> [`conoscenza-schema-sql`](../conoscenza-schema-sql/epic.md). **Leak ancora dentro questo core:** i
> **trasporti MCP non-stdio** (HTTP/SSE + auth) e un **tool `health`/`status`** (corpus+indice) sono
> un'estensione di **FEAT-MCP** (da promuovere a riga propria quando si decompone).

> **Decomposizione di FEAT-003 (2026-06-05) — refactor host-agnostico lungo il confine meccanico↔giudizio:**
> - **FEAT-003-D — Nucleo wiki deterministico host-agnostico** (config `wiki.config.toml` + `wiki_tools`:
>   profile/structure/scan/collect/lint-meccanico/index-log mechanics/idempotenza — REQ-001..006, REQ-011/012,
>   REQ-050/051, FR-006-meccanico, FR-009/010/011). **Zero LLM.** → portata avanti via **SpecKit**
>   (branch+PR, Constitution Check, gate **Principio X**).
> - **FEAT-003-N — Operazioni wiki assistite da LLM** (record-contenuto, distill, generazione, ingest-compile,
>   lint semantico, giudizio verità/obsolescenza, gate al commit human-in-the-loop). → tracciata come
>   **TODO collaborativo** in [`wiki-llm/TODO.md`](wiki-llm/TODO.md), affrontata passo-passo (non SpecKit).
> - **Pezzi D residui (2026-06-10)** — due capacità deterministiche rimaste (query congiunta
>   multi-collezione + esposizione di `upsert-index` in CLI), requisiti in
>   [`query-congiunta-e-indice/requirements.md`](query-congiunta-e-indice/requirements.md). → un unico
>   flusso **SpecKit completo**.

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
