---
title: Indice del Wiki — Produzione Sertor
type: index
tags: [produzione, wiki, index]
created: 2026-05-30
updated: 2026-06-06 (Doc lint C/reorg + split rituale↔retrospettiva + architettura-wiki-llm allineata + ricucito server-mcp)
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
| [`log.md`](log.md) | Registro append-only di tutto ciò che facciamo |

## Pagine

### Concepts (fondamenta e astrazioni)

- **[[retrieval-core]]** — Il **nucleo di retrieval** importabile (`sertor-core`), *il prodotto*: architettura Clean (domain/services/adapters/engines + porte `Protocol`), composition root guidato da `Settings`, backend `local`/`azure`, policy errori tollerante↔strict, collezioni namespaced per `(corpus, provider)`. CLI/MCP/wiki ne sono consumatori sottili.
- **[[costituzione-v1]]** — Ratifica Costituzione v1.0.0 (2026-05-31) → v1.1.0 (2026-06-05, aggiunto Principio X host-agnostico); 10 principi vincolanti, gate Constitution Check. Governa design e produzione.
- **[[missione-visione-host-agnosticita]]** — Mission/Vision canonizzate in README.md; Principio X come vincolo operativo; backlog: refactor host-agnostico di skill wiki/playbook/rituale.
- **[[ruolo-wiki-da-w1]]** — DA-W1 risolta: il wiki è CORPUS + SUPERFICIE; identità, autorità, confine MVP, ruoli 1–3.
- **[[rituale-step-e-allineamento-wiki]]** — Rituale di step (Definition of Done): a ogni step → record + lint di allineamento + azioni standing estendibili. Standing behavior vs automazione unattended; fonte unica = `CLAUDE.md`. *(Retrospettiva estratta in [[retrospettiva-interazione-2026-06-04]].)*

### Experiments (record di attività/step/feature)

- **[[epiche-sertor-core-e-cli]]** — Ristrutturazione: Sertor Core (MVP, capacità RAG + Wiki) primaria; Sertor CLI (distribuzione via CLI) secondaria. Questione aperta DA-W1 su ruolo wiki.
- **[[decomposizione-must-core]]** — Decomposizione dei 3 Must (FEAT-001/002/003); 6 decisioni di ambito MVP; nuova FEAT-009 su refresh incrementale.
- **[[chiusura-prototipo-dogfooding]]** — Isolamento del prototipo, motore corpus-aware, RAG di dogfooding su se stesso, MCP ri-puntato.
- **[[piano-nucleo-retrieval]]** — Piano SpecKit FEAT-001: architettura Clean, decisioni R1–R8, Constitution Check ✅ (Principi I+IV), modello dati, contratti, scope MVP vs post-MVP.
- **[[implementazione-nucleo-retrieval]]** — Completamento FEAT-001: libreria `sertor-core` prod-ready, 53 test, chunking 14 lingue, embeddings multi-provider, facade retrieval, Constitution Check 9/9 ✅.
- **[[motore-baseline-feat002]]** — Implementazione FEAT-002: motore vettoriale baseline (ranking similarity + evaluation hit@k/MRR), 67 test, policy errore isolata, estensioni non-breaking al nucleo, Constitution Check 9/9 ✅.
- **[[nucleo-wiki-deterministico-feat003d]]** — Implementazione FEAT-003-D (metà deterministica del wiki LLM): 11 moduli, 8 test, zero LLM, host-agnostico (Principio X), guidato da `wiki.config.toml`, contratti JSON versionati. Constitution Check 10/10 ✅. Offline per costruzione.
- **[[ponte-d-n-host-agnostico]]** — Primo step FEAT-003-N (ponte D→N): il layer agentico (playbook + skill + comando + agente) reso host-agnostico (legge `wiki.config.toml`) e poggiato sulla CLI `sertor-wiki-tools` per il meccanico; all'LLM resta il giudizio. Rename coerente: `genera-wiki`→`wiki-author`, `playbook.md`→`wiki-playbook.md`, `wiki-keeper`→`wiki-curator` (+Bash). Tabella confine D↔N; scope leggero (zero codice).
- **[[server-mcp-produzione-feat-mcp]]** — ✅ **FEAT-MCP implementata** (Server MCP di produzione): flusso SpecKit completo (requirements→specify→clarify→plan→analyze→implement) finito 2026-06-06. 3 tool (`search_code`/`search_docs`/`search_combined`), facade memoizzata, 6 test verdi, Constitution Check 10/10. `.mcp.json` rimontato su server produzione, corpus `sertor`.
- **[[pulizia-pycache-e-diagnosi-mcp]]** — Record del 2026-06-05: rimossi 16 dir `__pycache__` fantasma + diagnosi architetturale di `.mcp.json`. ⚠️ **Diagnosi superata il 2026-06-06** (banner nella pagina): `sertor_mcp` (PR #15) e `wiki_tools`/FEAT-003-D (PR #13) sono su master, `.mcp.json` ri-puntato alla produzione. *(Spostata da `tech/` a `experiments/`: è un record datato, non una tecnologia.)*
- **[[retrospettiva-interazione-2026-06-04]]** — Retrospettiva onesta sull'interazione del 2026-06-04 (pattern di ostruzione percepito, radici plausibili, correttivo adottato); separata dal design del rituale per atomicità.

### Syntheses (viste d'insieme e sintesi trasversali)

- **[[architettura-wiki-llm]]** — 🗺️ **Vista d'insieme + roadmap.** Architettura del Wiki LLM dopo il ponte D→N: nucleo deterministico (`wiki_tools`) + layer agentico (4 entità host-agnostiche) + hook, separati dal confine D (meccanico) ↔ N (giudizio); una sola config. Schemi a strati, confine per operazione, lint a tre livelli (A strutturale / B semantico / C organizzativo). **Roadmap** con grafo di dipendenze e priorità. Pagina d'ingresso all'architettura.
- **[[sistema-wiki-fonte-unica]]** — Consolidamento del wiki (fonte unica playbook + tre interfacce sottili + automazione hook). Tassonomia consolidata; convenzioni esplicite; operazioni del playbook. **Modularizzato (2026-06-07):** playbook = indice + moduli `ops/*.md` caricati on-demand (progressive disclosure, resta DRY e portabile).
- **[[lint-semantico-host-agnostico]]** — 🔍 **Estensione del lint a audit globale.** 4 `kind` di artefatti (`wiki`/`requirements`/`spec`/`tracker`) dichiarati in config `[[audit]]` con profili universali nel playbook; per ogni `kind`, tassonomia di coerenza e procedura ripetibile. Host-agnostico: la rete di anti-deriva è globale, non solo wiki.
- **[[lint-organizzativo-e-reorg]]** — 🧭 **Lint livello C (organizzativo) + reorg.** La terza categoria di deriva (collocazione, atomicità, coerenza `type`↔natura, disciplina link) oltre igiene (A) e claim (B). Perché è tutto giudizio (cartella e `type` mentono insieme sul contenuto); principio "grafo non albero"; esercizio 2026-06-06 (`syntheses/` da 16/20 a 4/3/9/4, 0 link rotti).

### Tech (tecnologie e infrastruttura)

- **[[hook-sessionstart-wiki]]** — Hook SessionStart di Claude Code: carica indice + log a inizio sessione. Ruolo 1 di DA-W1 (contesto iniettato).
- **[[tree-sitter-language-pack]]** — Binding Rust multilingua (305+ lingue), parser robusto, set MVP 14 lingue (10 sintattico + 4 fallback: PowerShell, Bash, T-SQL, PL/SQL), wrapper `_Node` per API metodo-based.
- **[[naming-corpora-indici]]** — Schema naming chiarificato (dal 2026-06-04): corpus `sertor` (prodotto, radice) vs `prototype` (prototipo, congelato); indici `.index-sertor` (radice) vs `.index-prototype` (prototipo).