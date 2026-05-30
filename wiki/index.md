---
title: Indice del Wiki — Produzione Sertor
type: index
tags: [produzione, wiki, index]
created: 2026-05-30
updated: 2026-05-30
sources: []
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

- **[[chiusura-prototipo-dogfooding]]** — Isolamento del prototipo, motore corpus-aware, RAG di dogfooding su se stesso, MCP ri-puntato.
- **[[epiche-sertor-core-e-cli]]** — Ristrutturazione: Sertor Core (MVP, capacità RAG + Wiki) primaria; Sertor CLI (distribuzione via CLI) secondaria. Questione aperta DA-W1 su ruolo wiki.
