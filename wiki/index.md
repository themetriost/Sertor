---
title: Indice del Wiki — Produzione Sertor
type: index
tags: [produzione, wiki, index]
created: 2026-05-30
updated: 2026-06-03
sources: ["requirements/sertor-core/epic.md", ".specify/memory/constitution.md", "specs/001-nucleo-retrieval/**", "specs/002-rag-baseline/**", "specs/003-wiki-creazione/**", "src/sertor_core/**"]
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

## 📌 Pagina viva

- **[[roadmap]]** — **Roadmap & Piano di prodotto**: stato di tutte le feature, roadmap per fasi e la
  sezione *Nuove funzionalità da discutere* (aggiornabile a mano). Tienila sempre aperta.

## Pagine

_(La produzione inizia ora: questa sezione cresce a ogni sessione.)_

### Experiments (attività e test di produzione)

- **[[dogfooding-produzione-cli]]** — Primo dogfooding CLI sul corpus di produzione (146 doc, 1192 chunk); 2 bug trovati e corretti (UnicodeEncodeError Windows, argparse parent flags). Lezione: dogfooding reale scopre bug che test mock non vedono.

### Syntheses (sintesi trasversali)

- **[[costituzione-v1]]** — Ratifica Costituzione v1.0.0 (governance, 9 principi vincolanti, gate Constitution Check). Governa design e produzione.
- **[[chiusura-prototipo-dogfooding]]** — Isolamento del prototipo, motore corpus-aware, RAG di dogfooding su se stesso, MCP ri-puntato.
- **[[epiche-sertor-core-e-cli]]** — Ristrutturazione: Sertor Core (MVP, capacità RAG + Wiki) primaria; Sertor CLI (distribuzione via CLI) secondaria. Questione aperta DA-W1 su ruolo wiki.
- **[[ruolo-wiki-da-w1]]** — DA-W1 risolta: il wiki è CORPUS + SUPERFICIE; identità, autorità, confine MVP, ruoli 1–3.
- **[[decomposizione-must-core]]** — Decomposizione dei 3 Must (FEAT-001/002/003); 6 decisioni di ambito MVP; nuova FEAT-009 su refresh incrementale.
- **[[piano-nucleo-retrieval]]** — Piano SpecKit FEAT-001: architettura Clean, decisioni R1–R8, Constitution Check ✅ (Principi I+IV), modello dati, contratti, scope MVP vs post-MVP.
- **[[implementazione-nucleo-retrieval]]** — Completamento FEAT-001: libreria `sertor-core` prod-ready, 53 test, chunking 14 lingue, embeddings multi-provider, facade retrieval, Constitution Check 9/9 ✅.
- **[[motore-baseline-feat002]]** — Implementazione FEAT-002: motore vettoriale baseline (ranking similarity + evaluation hit@k/MRR), 67 test, policy errore isolata, estensioni non-breaking al nucleo, Constitution Check 9/9 ✅.
- **[[skill-wiki-feat003]]** — Implementazione FEAT-003: skill LLM Wiki (creare/indicizzare), 84 test, operazioni strutturali LLM-free, indicizzazione riusa nucleo, idempotenza strutturale, Constitution Check 9/9 ✅.
- **[[cli-esecuzione-feat004]]** — Implementazione FEAT-CLI-004: CLI esecuzione (sottocomandi index/search/wiki), osservabilità configurabile, output flessibile, 17 task, 100 test, Constitution Check 9/9 ✅. Primo entry point eseguibile, abilita dogfooding produzione.
- **[[requisito-llm-wiki-e2e]]** — Requisito e2e dell'LLM Wiki (FEAT-010): elicitazione consolidata dai pattern Karpathy, 17 decisioni, 42 EARS, 10 SC. Consolida FEAT-003, assorbe FEAT-007; READY per design. Modello a due momenti (generazione Karpathy + indicizzazione RAG paritaria), due classi (input vs wiki generato), orchestrazione agentica al commit.

### Tech (tecnologie e infrastruttura)

- **[[hook-sessionstart-wiki]]** — Hook SessionStart di Claude Code: carica indice + log a inizio sessione. Ruolo 1 di DA-W1 (contesto iniettato).
- **[[tree-sitter-language-pack]]** — Binding Rust multilingua (305+ lingue), parser robusto, 14 lingue sintattico MVP + 3 fallback, wrapper `_Node` per API metodo-based.
