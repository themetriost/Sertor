---
title: Indice del Wiki — Produzione Sertor
type: index
tags: [produzione, wiki, index]
created: 2026-05-30
updated: 2026-06-05 (FEAT-003-D implementato + nucleo wiki deterministico registrato)
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

| Cartella | Contenuto |
|----------|-----------|
| `concepts/` | Concetti |
| `tech/` | Tecnologie e strumenti |
| `experiments/` | Una pagina per attività/esperimento di produzione |
| `sources/` | Riassunti di fonti esterne |
| `syntheses/` | Confronti e sintesi trasversali |
| [`log.md`](log.md) | Registro append-only di tutto ciò che facciamo |

## Pagine

_(La produzione inizia ora: questa sezione cresce a ogni sessione.)_

### Syntheses (sintesi trasversali)

- **[[nucleo-wiki-deterministico-feat003d]]** — Implementazione FEAT-003-D (metà deterministica del wiki LLM): 11 moduli, 8 test, zero LLM, host-agnostico (Principio X), guidato da `wiki.config.toml`, contratti JSON versionati. Constitution Check 10/10 ✅. Offline per costruzione.
- **[[rituale-step-e-allineamento-wiki]]** — Rituale di step (Definition of Done) per impedire la deriva wiki↔progetto: a ogni step → record + lint semantico di allineamento + azioni standing estendibili. Distinzione unattended vs standing behavior; retrospettiva onesta sull'interazione del 2026-06-04. Fonte unica = `CLAUDE.md` (plugin step-ritual cancellato, riesportazione a backlog).
- **[[sistema-wiki-fonte-unica]]** — Consolidamento del wiki (fonte unica playbook + tre interfacce sottili + automazione hook). Tassonomia consolidata; convenzioni esplicite; 6 operazioni (record, ingest, query, lint, generate-from-diff, rag-sync).
- **[[costituzione-v1]]** — Ratifica Costituzione v1.0.0 (2026-05-31) → v1.1.0 (2026-06-05, aggiunto Principio X host-agnostico); 10 principi vincolanti, gate Constitution Check. Governa design e produzione.
- **[[missione-visione-host-agnosticita]]** — Mission/Vision canonizzate in README.md; Principio X come vincolo operativo; backlog: refactor host-agnostico di skill wiki/playbook/rituale.
- **[[chiusura-prototipo-dogfooding]]** — Isolamento del prototipo, motore corpus-aware, RAG di dogfooding su se stesso, MCP ri-puntato.
- **[[epiche-sertor-core-e-cli]]** — Ristrutturazione: Sertor Core (MVP, capacità RAG + Wiki) primaria; Sertor CLI (distribuzione via CLI) secondaria. Questione aperta DA-W1 su ruolo wiki.
- **[[ruolo-wiki-da-w1]]** — DA-W1 risolta: il wiki è CORPUS + SUPERFICIE; identità, autorità, confine MVP, ruoli 1–3.
- **[[decomposizione-must-core]]** — Decomposizione dei 3 Must (FEAT-001/002/003); 6 decisioni di ambito MVP; nuova FEAT-009 su refresh incrementale.
- **[[piano-nucleo-retrieval]]** — Piano SpecKit FEAT-001: architettura Clean, decisioni R1–R8, Constitution Check ✅ (Principi I+IV), modello dati, contratti, scope MVP vs post-MVP.
- **[[implementazione-nucleo-retrieval]]** — Completamento FEAT-001: libreria `sertor-core` prod-ready, 53 test, chunking 14 lingue, embeddings multi-provider, facade retrieval, Constitution Check 9/9 ✅.
- **[[motore-baseline-feat002]]** — Implementazione FEAT-002: motore vettoriale baseline (ranking similarity + evaluation hit@k/MRR), 67 test, policy errore isolata, estensioni non-breaking al nucleo, Constitution Check 9/9 ✅.

### Tech (tecnologie e infrastruttura)

- **[[hook-sessionstart-wiki]]** — Hook SessionStart di Claude Code: carica indice + log a inizio sessione. Ruolo 1 di DA-W1 (contesto iniettato).
- **[[tree-sitter-language-pack]]** — Binding Rust multilingua (305+ lingue), parser robusto, 14 lingue sintattico MVP + 3 fallback, wrapper `_Node` per API metodo-based.
- **[[naming-corpora-indici]]** — Schema naming chiarificato (dal 2026-06-04): corpus `sertor` (prodotto, radice) vs `prototype` (prototipo, congelato); indici `.index-sertor` (radice) vs `.index-prototype` (prototipo).
- **[[pulizia-pycache-e-diagnosi-mcp]]** — Cleanup del 2026-06-05: rimossi 16 dir `__pycache__` fantasma, diagnosi architetturale che solo `sertor_core` vive su master (CLI/MCP/wiki su branch), decisione su `.mcp.json` rotto (aspetta merge `feat/mcp-sertor-core`).
