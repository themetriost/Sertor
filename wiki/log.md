---
title: Log del Wiki — Produzione Sertor
type: log
created: 2026-05-30
updated: 2026-05-30
---

# Registro di Produzione (append-only)

Voci in ordine cronologico. Formato: `## [YYYY-MM-DD] <operazione> | <titolo>`
(operazione ∈ setup/ingest/record/query/lint).

## [2026-05-30] setup | Apertura del wiki di produzione (chiusura del prototipo)

- **Isolamento prototipo:** codice `01–04`, `shared/`, `tests/`, corpus FastAPI (`raw/`),
  documentazione (`README/DEMOS/ESEMPI`) e il wiki storico spostati in **`prototype/`**
  (stesso repo). Il wiki del prototipo è ora **congelato** (sola lettura) in `prototype/wiki/`.
- **RAG di dogfooding:** motore reso *corpus-aware* (env `SERTOR_CORPUS`); nuovo indice separato
  `prototype/01-baseline/.index-sertor` il cui corpus è il **prototipo stesso** (codice + doc + wiki).
  L'indice FastAPI esistente **non è stato toccato**.
- **MCP ri-puntato:** `.mcp.json` → `prototype/04-agentic-rag/mcp_server.py` con
  `PYTHONPATH=prototype`, `SERTOR_CORPUS=sertor`. Ogni riferimento al prototipo passa ora dal RAG.
- **Questo `wiki/` di root** è il nuovo wiki di **produzione**; hook `SessionStart`, agente
  `wiki-keeper` e skill `.claude/` restano invariati (continuano a puntare a `wiki/`).

## [2026-05-30] record | Chiusura prototipo + RAG dogfooding + MCP ri-puntato

- **Pagina creata:** `syntheses/chiusura-prototipo-dogfooding.md` documenta in dettaglio:
  - **Motivazione:** confine netto prototipo (exploration) ↔ produzione (CLI `sertor-rag`).
  - **Isolamento fisico:** prototipo sotto `prototype/` (snapshot congelato), produzione
    a livello alto (requirements, wiki, nuovi moduli).
  - **Motore corpus-aware:** `SERTOR_CORPUS` (`fastapi` | `sertor`) in `config.py` e `loaders.py`;
    fix critico del filtro `mentions` in `build_graph.py` (era hardcoded, ora dinamico).
  - **Indici namespaced:** `.index` (FastAPI) vs `.index-sertor` (dogfooding).
  - **RAG di dogfooding:** indice Chroma `.index-sertor` su prototipo stesso.
    Corpus = 57 doc, 670 chunk (dim 3072); grafo = 240 nodi, 835 archi (415 mentions, 26 doc).
  - **MCP ri-puntato:** `.mcp.json` → `prototype/04-agentic-rag/mcp_server.py`
    (`SERTOR_CORPUS=sertor`). Tutti i tool (`find_symbol`, `search_code`, etc.) testati e funzionanti.
  - **Conseguenze operative:** sviluppo isolato da prototipo; accesso via MCP; wiki prototipo
    congelato; corpus dogfooding come acceptance test.
- **Index aggiornato:** sezione "Syntheses" con link a `[[chiusura-prototipo-dogfooding]]`.
- **Branch/commit:** `chore/isolamento-prototipo` (commit `104e666`), pagina aggiunta in questo record.

## [2026-05-30] record | Ristrutturazione epiche: sertor-core (primaria/MVP) + sertor-cli (secondaria)

- **Nuova pagina:** `syntheses/epiche-sertor-core-e-cli.md` documenta la ristrutturazione di visione:
  - **Razionale:** il valore core non è la CLI ma le capacità (creare RAG production-grade + skill
    LLM Wiki). CLI è il veicolo di distribuzione/uso.
  - **Epica primaria (sertor-core, `requirements/sertor-core/epic.md`):** 8 feature, sequenza logica.
    FEAT-001/002/003 Must (nucleo retrieval, baseline, wiki skill); FEAT-004/005/006/007 Should
    (ibrido, grafo, agentico, spider/lint); FEAT-008 Could (arricchimento bidirezionale). 7 success
    criteria, 6 requisiti EARS.
  - **Epica secondaria (sertor-cli, `requirements/sertor-cli/epic.md`):** 6 feature, CLI instalabile
    + selezione capacità + config + RAG/wiki command. Decisioni DA-1…DA-6 (naming, git, vector DB,
    provider) rimangono valide.
  - **Questione aperta DA-W1:** ruolo profondo del wiki non ancora definito (fonte di contesto per
    agenti? luogo di query precise? fonte di ingestion per RAG?). Blocca decomposizione FEAT-003
    wiki. Richiede decisione di prodotto PRIMA di user story.
- **Index aggiornato:** sezione Syntheses con link a nuova pagina.
- **Pagina storica superata:** `prototype/wiki/epica-sertor-cli.md` (congelata, consultabile via RAG).

## [2026-05-31] record | DA-W1 risolta (ruolo wiki: corpus×superficie) + hook SessionStart documentato

- **Pagina creata:** `syntheses/ruolo-wiki-da-w1.md` documenta il modello concettuale risolutivo:
  - **Due assi ortogonali:** corpus (wiki vs codice) × superficie (RAG semantica vs wiki-nativa).
  - **Identità:** wiki = CORPUS + SUPERFICIE entrambi; già ingerito nel RAG, navigabile per struttura.
  - **Tre ruoli:** (1) contesto iniettato (push, host); (2) query precisa (pull strutturato); (3) ingestion nel RAG (già attivo).
  - **Decisioni chiave:** MVP Must = creare+indicizzare (ruolo 3); post-MVP = superficie nativa (ruoli 1–2) + spider/lint/arricchimento.
  - **Confine MVP risolto:** chiude DA-W1 e DA-2 (wiki = solo creazione/indicizzazione, niente spider automatico).
  - **Sblocca FEAT-003 decomposizione** e inquadra FEAT-007/008 (post-MVP).
- **Pagina creata:** `tech/hook-sessionstart-wiki.md` documenta il meccanismo concreto di ruolo 1:
  - **Hook `SessionStart`:** PowerShell inline in `.claude/settings.json`, attiva a inizio sessione/resume/compact.
  - **Payload:** indice wiki intero + ultime 20 righe di log, iniettate in contesto (sola lettura).
  - **Rilevanza DA-W1:** prova empirica di ruolo 1 (contesto iniettato); competenza dell'host, non MVP Sertor.
- **Index aggiornato:** sezione Syntheses con `[[ruolo-wiki-da-w1]]`; nuova sezione Tech con `[[hook-sessionstart-wiki]]`.
- **Epica sertor-core `epic.md`:** §9 (DA-W1, DA-2 risolte) e §6 (R-5 mitigato).
