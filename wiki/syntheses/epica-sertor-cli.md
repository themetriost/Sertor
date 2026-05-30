---
title: Epica Sertor CLI — requisiti di alto livello e backlog
type: synthesis
tags: [sertor, cli, requirements, epic, governance, rag-installation]
created: 2026-05-30
updated: 2026-05-30
sources: [requirements/sertor-cli/epic.md]
---

# Epica Sertor CLI — Requisiti di Alto Livello e Backlog

Sintesi della visione, decisioni di ambito e backlog di feature per il progetto **Sertor CLI** (toolkit installabile per RAG + governance + LLM Wiki). L'epica è stata elicitata nella fase [[requirements-engineering]] via skill `/requirements` a livello epico.

## Visione e Problema

Oggi la conoscenza maturata in questo workspace — i 4 motori RAG (baseline vettoriale, hybrid, graph, agentico), configurazione di agenti/skill, e il pattern dell'**LLM Wiki** — vive dentro un singolo repository e va ricostruita a mano ogni volta che la si vuole portare altrove.

**L'epica introduce un pacchetto installabile** (via `uv` o `pip`) che espone una **command line**. Il CLI permette di **scegliere e installare in modo selettivo** le capacità (motori RAG, configurazione di governance, LLM Wiki) su un repository — **nuovo o esistente** — e di configurarle (provider LLM, vector DB) **senza far partire automaticamente la creazione/ingestione del RAG**.

Obiettivo finale: trasformare l'esperienza del prototipo in uno **strumento riusabile e repo-agnostico**, riutilizzabile in contesto enterprise.

## Decisioni di Ambito (Deliberate dalla Discussione)

### In Ambito
- Pacchetto installabile (`uv`/`pip`) con CLI come punto di ingresso unico.
- Setup **selettivo** — l'utente sceglie cosa installare; nulla parte da solo.
- Installazione dei 4 motori RAG (baseline vettoriale, hybrid/reranking, graph, agentico) selezionabili indipendentemente.
- Configurazione del RAG: provider LLM (obbligatorio) e vector DB (opzionale, locale o cloud).
- **Comando separato** per creazione/esecuzione del RAG (ingestione/indicizzazione), distinto dall'installazione.
- LLM Wiki: setup, spider/lint (rigenera indice, valida link), e arricchimento bidirezionale Wiki↔RAG.
- Setup di configurazione di governance (skill/agenti per fasi di progetto + gestione requisiti).
- Funzionamento **agnostico al repository**: applicabile su progetto nuovo o esistente.

### Fuori Ambito (per ora)
- Pubblicazione pubblica su PyPI → design **non deve precludere** futuro lancio pubblico.
- Creazione dei contenuti RAG/Wiki specifici (è **uso** dello strumento, non costruzione).
- Interfaccia grafica/web (il deliverable è CLI).

## Requisiti Trasversali (EARS)

Sei requisiti che attraversano l'intera epica:

| ID | Requisito | Formato EARS |
|----|-----------| -------------|
| REQ-E1 | Setup selettivo | *Optional:* l'utente seleziona quali capacità installare e ottiene solo quelle. |
| REQ-E2 | Install ≠ Run | *Unwanted:* l'installazione di un componente **non** avvia automaticamente ingestione RAG. |
| REQ-E3 | LLM obbligatorio | *Ubiquitous:* il sistema richiede un LLM configurato prima di ogni operazione RAG. |
| REQ-E4 | Local-only supportato | *Optional:* l'utente può scegliere una config senza cloud (Ollama + Chroma). |
| REQ-E5 | Segreti mai versionati | *Unwanted:* API key/secret non persistono in file versionati. |
| REQ-E6 | No clobber repo | *Event-driven:* setup su repo esistente non sovrascrive file modificati senza conferma. |

## Backlog di Feature (MoSCoW)

| ID | Feature | Valore | Priorità | Stato |
|----|---------| -------|----------|-------|
| FEAT-001 | **CLI installabile** | Spina dorsale: senza CLI nessuna capacità è raggiungibile | **Must** | da decomporre |
| FEAT-002 | **Installazione selettiva motori RAG** (4 approcci) | Portare i 4 motori su un repo, a scelta, senza eseguirli | **Must** | da decomporre |
| FEAT-003 | **LLM Wiki — setup & gestione** | Conoscenza persistente/cumulativa del progetto | **Must** | da decomporre |
| FEAT-004 | **Wiki Spider / Lint** (idempotente) | Mantiene wiki vivo e coerente | **Must** | da decomporre |
| FEAT-005 | **Configurazione RAG** (LLM + vector DB) | Adatta RAG all'ambiente senza toccare codice | **Should** | da decomporre |
| FEAT-006 | **Comando creazione/esecuzione RAG** | Costruire/aggiornare indici su richiesta esplicita | **Should** | da decomporre |
| FEAT-007 | **Setup governance** (skill/agenti + requisiti) | Replicare config di lavoro su altri repo | **Should** | da decomporre |
| FEAT-008 | **Arricchimento bidirezionale Wiki↔RAG** | Loop virtuoso doc/codice migliora retrieval | **Could** | da decomporre |
| FEAT-009 | **Distribuzione PyPI pubblica** | Apertura a utenti esterni | **Won't (per ora)** | rinviata |

> **Nota MVP:** il primo taglio (Must) installa i motori RAG e mette in piedi il wiki vivo (setup + spider). La **configurazione** (FEAT-005) e l'**esecuzione** (FEAT-006) completano il ciclo subito dopo (Should). Confine affrontato dalla domanda DA-2.

## Criteri di Successo (Misurabili)

| ID | Criterio | Descrizione |
|----|----------|------------|
| CS-1 | **Installabilità** | Un utente installa il pacchetto (`uv`/`pip`) su macchina pulita, CLI disponibile a riga di comando, zero passi manuali. |
| CS-2 | **Install ≠ Run** | Zero casi dove installazione avvia automaticamente ingestione RAG; serve sempre comando esplicito separato. |
| CS-3 | **Selettività** | L'utente installa qualsiasi sottoinsieme di capacità e ottiene solo quelle. |
| CS-4 | **Agnosticità** | CLI completato con successo su repo nuovo **e** repo esistente (≥2 scenari verificati); no sovrascrittura silenziosa. |
| CS-5 | **Configurabilità LLM** | Supporta ≥1 provider cloud (default) **e** opzione locale (Ollama); LLM configurato obbligatorio. |
| CS-6 | **Vector DB a scelta** | Consente scelta tra ≥2 opzioni (locale vs cloud) o di ometterlo. |
| CS-7 | **Wiki vivo** | Spider/lint rieseguibile in modo idempotente senza divergenze; indice rigenerato, link validi. |
| CS-8 | **Arricchimento** | Una sessione RAG usa sia sorgenti sia wiki come input, dimostrabilmente (entrambe contribuiscono). |

## Decisioni Risolte (2026-05-30)

| DA | Domanda | Decisione |
|----| --------|-----------|
| DA-1 | Nome pacchetto/comando CLI | **Risolto:** pacchetto e comando = `sertor` |
| DA-2 | Confine install/config/run | **Risolto:** MVP installa i motori RAG (Must, FEAT-001/002) e wiki (Must, FEAT-003/004); configurazione (FEAT-005) ed esecuzione (FEAT-006) restano Should — il RAG non è ancora eseguibile end-to-end nel primo taglio |
| DA-3 | Governance (FEAT-007) | **Risolto:** rimane Should, fuori dall'MVP |
| DA-4 | Distribuzione interim | **Risolto:** `git+url` per distribuzione interna, prima dell'eventuale PyPI pubblico |
| DA-5 | Vector DB opzionale vs condizionato | **Risolto (con nuova richiesta trasversale REQ-E7):** Vector DB è **opzionale in generale**, obbligatorio **solo se il motore selezionato lo richiede**. Un setup solo-graph può ometterlo. Nel prototipo: retrieval graph/strutturale (`03-graphrag/graph_query.py`, CodeGraph su networkx/GraphML) gira **senza** vector DB; retrieval testuale dense/hybrid dipende da Chroma anche solo come deposito documenti. |
| DA-6 | Provider LLM primo taglio | **Risolto:** OpenAI, Anthropic, Azure OpenAI/Foundry, GitHub Copilot, Ollama (locale). Aggiuntivi proposti (max 3, da confermare): Google Gemini/Vertex AI, AWS Bedrock, Mistral AI |

## Nota di Conoscenza: Vector DB Condizionale

**Scoperta verificata** (architettura attuale, codice prototipo):  
Non tutti i motori RAG dell'epica richiedono un vector DB. La **modalità graph/strutturale** (retrieval su grafo del codice, `03-graphrag/`) fa completamente a meno di vector DB — usa invece `networkx` in-memoria o GraphML su disco. La **modalità testuale** (dense retrieval, hybrid search, `01-baseline/`, `02-hybrid-reranking/`) invece dipende da Chroma, anche solo come deposito documenti — è un accoppiamento di implementazione, non una necessità logica di BM25.

**Requisito trasversale nuovo:** **REQ-E7** — *Conditional:* se l'utente seleziona un motore di retrieval testuale (baseline, hybrid, agentico con dense branch), allora vector DB è obbligatorio; se seleziona solo graph, vector DB è ometibile.

Implicazione per FEAT-005 (configurazione RAG): il CLI chiede il vector DB **solo se rilevante** al motore scelto, e non presenta la domanda per setup puri da grafo.

## Link Correlati

- **Artefatto di origine:** [[requirements-engineering]] / `requirements/sertor-cli/epic.md`
- **Metodologia:** [[ears-methodology]] — requisiti in formato EARS
- **Flusso end-to-end:** [[flusso-requisiti-implementazione]] — come epica→feature→EARS fluiscono in implementazione
- **Governance progetto:** [[costituzione-produzione-proposta]] — principi di progetto applicati
- **Stack RAG:** [[rag-overview]] — i 4 motori da installare (baseline, hybrid, graph, agentico)
- **Governance/skill:** [[speckit]] — framework orchestrazione fase-gate con 9 agenti, utilizzato dal CLI

## Note di Decomposizione

Ogni feature nel backlog (FEAT-001…008) andrà decomposta in una propria pagina `requirements/sertor-cli/<feature>/requirements.md` con:
- Requisiti EARS atomici e testabili
- Scenari di accettazione (Gherkin o descrittivi)
- Dipendenze da altre feature
- Rischi/mitigation
- Trace verso architettura (design doc a valle)

La decomposizione mantiene **bidirezionalità** con questo documento: ogni feature rimanda qui per contesto epico.
