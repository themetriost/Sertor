---
title: Epiche Sertor — Ristrutturazione (Core MVP + CLI Secondaria)
type: experiment
tags: [produzione, epiche, architettura, backlog]
created: 2026-05-30
updated: 2026-05-30
sources: [requirements/sertor-core/epic.md, requirements/sertor-cli/epic.md]
---

# Ristrutturazione Epiche: Sertor Core (Primaria) + Sertor CLI (Secondaria)

Questo record fissa la **ristrutturazione delle epiche** di Sertor: il [[retrieval-core|Sertor Core]]
(capacità RAG + Wiki) diventa l'epica **primaria** e la CLI l'epica **secondaria** (canale di distribuzione).

## Razionale della ristrutturazione

La **visione di prodotto** è stata ridefinita: il valore core di Sertor non risiede nella CLI
(pur importante), ma nelle **capacità sottostanti**:
1. **Creare RAG** (motori retrieval, vettoriale/ibrido/grafico/agentico, production-grade)
2. **Creare e gestire l'LLM Wiki** (skill di manutenzione, indicizzazione, arricchimento bidirezionale)

La **CLI è il veicolo** per distribuire e usare queste capacità (installazione, configurazione,
orchestrazione).

Questa separazione consente:
- Sviluppo delle **capacità decoupled** dalla CLI.
- Possibilità futura di consumare il core via API/MCP senza passare per la CLI.
- Chiarezza di responsabilità: core = motore; CLI = interfaccia.

---

## Epica Primaria: Sertor Core (MVP)

**Sede:** `requirements/sertor-core/epic.md`

### Visione
Motori RAG production-grade (baseline vettoriale Must, ibrido/grafico/agentico Should) + skill di
creazione e manutenzione dell'LLM Wiki, conforme a uno standard locale e riproducibile.
Riscrittura degli elementi migliori del prototipo (4 approcci RAG, knowledge graph, corpus-aware)
a qualità di produzione; il prototipo rimane **riferimento via RAG di dogfooding** (`prototype/wiki/` congelato,
consultabile tramite MCP `sertor-rag`).

### Backlog (8 feature, sequenza logica)

| ID | Titolo | Priorità | Stato | Note |
|----|--------|----------|-------|-------|
| FEAT-001 | Nucleo di retrieval condiviso | Must | — | Config centralizzata, provider engine (OpenAI, Azure, Ollama), vector store selector (Chroma, Azure AI Search, Cosmos). Prerequisito di tutte le feature RAG. |
| FEAT-002 | Motore RAG baseline (vettoriale) | Must | — | Chunking, embeddings, similarity search + recall metrics. Riferimento minimale e fondazione per ibrido/grafico/agentico. |
| FEAT-003 | Skill LLM Wiki (crea/indicizza/mantieni) | Must | — | Creazione struttura wiki (YAML frontmatter, backlink, cross-ref), indicizzazione in vector store, spider/lint periodico (FEAT-007), integrazione con FEAT-001. |
| FEAT-004 | Motore RAG ibrido + reranking | Should | — | BM25 + dense retrieval, semantic/cross-encoder reranking. Variante Azure AI Search (integrato). |
| FEAT-005 | Motore RAG su knowledge graph | Should | — | AST/symbol graph building, graphrag packet o custom schema. Query su grafo semantico. |
| FEAT-006 | Motore RAG agentico | Should | — | Multi-step retrieval, query planning, AutoGen o Semantic Kernel. |
| FEAT-007 | Manutenzione wiki: spider/lint | Should | — | Verifica integrità (backlink orfani, YAML mancante), deduplicazione voce log, consistency checks. Eseguibile periodico. |
| FEAT-008 | Arricchimento bidirezionale Wiki ↔ RAG | Could | — | Wiki genera contesto per agenti, risultati RAG arricchiscono Wiki (nuove pagine, sintesi). Lungo termine. |

### Criteri di successo (7)
1. Baseline RAG eseguibile in locale (Ollama) e su Azure (Azure OpenAI + AI Search).
2. Indicizzazione wiki automatica; query su wiki via FEAT-003 + FEAT-001.
3. Ibrido + reranking funzionante (Should); alternativa local fallback (cross-encoder).
4. Grafo + query su grafo (Should); symbol extraction da Python funciona.
5. Agentico con planning (Should); integrazione AutoGen/Semantic Kernel.
6. Spider wiki eseguibile; rapporto su contraddizioni/orfani (FEAT-007).
7. Nessuna dipendenza hard da Azure (tutto deve funzionare in locale con Ollama/Chroma).

### Requisiti trasversali EARS (6)
- **Effectiveness:** core supporta ≥4 approcci RAG, metriche recall/MRR/NDCG.
- **Availability:** local-first, failover a OpenAI se Ollama non disponibile.
- **Reliability:** indicizzazione idempotente, grafo rebuild deterministico, config versioning.
- **Scalability:** chunking configurabile, batch embedding, lazy loading indici.
- **Performance:** latenza query <1s (baseline), <2s (ibrido), threshold TBD (agentico).
- **Security:** env `.env`, niente segreti in repo, RBAC wiki (future, Could).

### Questione di prodotto aperta: DA-W1 (Ruolo del Wiki)

**Status:** Non ancora risolto. Impatta decomposizione FEAT-003 (Crea/Indicizza/Mantieni Wiki).

**Domanda centrale:** qual è il ruolo profondo dell'LLM Wiki per il team/per gli utenti?

**Opzioni in discussione:**
1. **Fonte di contesto per agenti/developer** — il wiki popola il contesto (system prompt, background,
   decisioni architetturali, lezioni imparate) degli agenti IA che sviluppano il prodotto o risolvono issue.
2. **Luogo di query precise e knowledge retrieval** — gli utenti/team interrogano il wiki per risposte
   strutturate, facendo affidamento su cross-ref e tag, con risultati meglio organizzati di una ricerca
   full-text.
3. **Fonte di ingestion per il RAG, oltre all'MCP** — il wiki non è solo indirizzabile via query ma
   contribuisce attivamente al corpus del RAG, come sorgente di verità parallela al codice/doc (e con
   priorità diversa in retrieval).

**Impatto:** la scelta di quale ruolo scegliere (1/2/3 o combinazione) determina:
- La struttura delle feature di wiki (separazione indexing ↔ query vs arricchimento bidirezionale).
- Il design di FEAT-008 (arricchimento bidirezionale).
- La scelta di tags/metadata nel frontmatter wiki (per supportare filtering, fonte-priorità, ecc.).

**Azione richiesta:** affrontare DA-W1 a livello di prodotto PRIMA di decomporre le user story
di FEAT-003, FEAT-007, FEAT-008. Coinvolgere team/stakeholder.

---

## Epica Secondaria: Sertor CLI (Riscritta)

**Sede:** `requirements/sertor-cli/epic.md`

### Visione
Distribuzione e uso delle capacità del core via command line. La CLI è il **veicolo installabile**
(uv/pip, PyPI), **non il generatore di capacità**. Dipende dal core; ha responsabilità limitata:
installazione, selezione feature, configurazione, esecuzione RAG e wiki.

### Backlog (6 feature)

| ID | Titolo | Priorità | Stato | Note |
|----|--------|----------|-------|-------|
| FEAT-001 | CLI installabile (uv/pip/PyPI) | Must | — | Entry point `sertor` con subcommand (rag, wiki, config, …). Setup dev/prod con isolamento dipendenze. |
| FEAT-002 | Installazione selettiva capacità core | Must | — | Flag/feature set per scegliere cosa installare (es. `--with-graphrag`, `--with-wiki-spider`). Dipende da FEAT-001 core. |
| FEAT-003 | Configurazione (env/file YAML) | Should | — | Gestione `.env`, `sertor.yaml`, switch provider/backend (RAG_BACKEND=local|azure). CLI tool `sertor config set/get`. |
| FEAT-004 | Comando creazione/esecuzione RAG | Should | — | `sertor rag create --corpus corpus-fastapi --backend local` (crea indice). `sertor rag query "…"` (interroga). |
| FEAT-005 | Setup governance (SpecKit, .claude, .specify) | Should | — | Template governance, hook SessionStart, agent skill delegation. |
| FEAT-006 | Distribuzione PyPI | Won't | — | Rimandato a post-MVP. Condizioni: CLI stabile, doc completa, automation CI/CD. |

### Decisioni DA-1…DA-6 (valide a livello CLI)

Rimangono rilevanti e inalte:
- **DA-1:** naming `sertor` (nome del package/CLI).
- **DA-2:** git + URL remoto standard (vedi requirement doc).
- **DA-3:** vector DB condizionale (Chroma locale default, Azure AI Search opt-in).
- **DA-4:** provider LLM scegibile via config (OpenAI/Ollama/Azure).
- **DA-5, DA-6:** future (ci/governance, distribuzione).

---

## Superamento della pagina storica

La pagina `prototype/wiki/epica-sertor-cli.md` (dal prototipo, congelata) è **superata** da questa
sintesi e dalle pagine di epic a `requirements/`. Non va modificata (è frozen); è consultabile
via RAG dogfooding se necessario come riferimento storico.

---

## Stato della ristrutturazione (2026-05-30)

- **FEAT-001 (core):** spec completata in `requirements/sertor-core/epic.md`, backlog pronto.
- **FEAT-002 (baseline):** spec pronta; riscrittura da `prototype/01-baseline/` avviabile.
- **FEAT-003 (wiki skill):** spec presente; **blocco su DA-W1** (ruolo wiki non definito).
- **Altre feature core:** spec presenti; priorità post-MVP.
- **Epica CLI:** completamente riscritta in `requirements/sertor-cli/epic.md`.

**Prossimo step:** risolvere DA-W1, poi decomporre FEAT-003 in user story.

---

## Backlink

- [[chiusura-prototipo-dogfooding]] — isolamento prototipo e RAG dogfooding che supporta la visione di riscrittura.
