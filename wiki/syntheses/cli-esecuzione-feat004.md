---
title: Implementazione CLI Esecuzione (FEAT-CLI-004)
type: synthesis
tags: [sertor-cli, cli, esecuzione, entry-point, osservabilità, observability]
created: 2026-06-03
updated: 2026-06-03
sources: ["src/sertor_cli/**", "requirements/sertor-cli/esecuzione/requirements.md", "specs/004-cli-esecuzione/plan.md", "specs/004-cli-esecuzione/tasks.md"]
---

# Implementazione CLI Esecuzione (FEAT-CLI-004)

**Stato:** ✅ **Completato (17/17 task)** | ruff clean | Constitution Check 9/9 ✅

Implementazione della feature "esecuzione" dell'epica **sertor-cli**: il primo **entry point eseguibile** del progetto. Comando `sertor` con sottocomandi per operazioni di retrieval e wiki, osservabilità configurabile, output flessibile, zero dipendenze cloud obbligatorie.

## Contesto

Sertor ha raggiunto la **chiusura del loop MVP di core** con FEAT-001/002/003 ([[implementazione-nucleo-retrieval]], [[motore-baseline-feat002]], [[skill-wiki-feat003]]). Ora abilita la **distribuzione e uso**: la feature "esecuzione" è il primo accesso pubblico via CLI.

**Significato strategico:** è il proof-of-concept per:
- **Dogfooding di produzione:** indicizzare `src/` + `specs/` + `wiki/` stesso in collezione `production`.
- **Validation del design:** composizione root, choice provider, configurabilità, osservabilità reale.
- **Estendibilità:** struttura `argparse` + composition root per future skill (FEAT-CLI-005/006/007).

## Architettura

### Pacchetto e dipendenze

Secondo pacchetto del workspace (primo è `sertor-core`):

```
src/sertor_cli/
├─ __init__.py
├─ __main__.py              # entry point for `python -m sertor_cli`
├─ cli.py                   # argument parser, dispatch sottocomandi
├─ commands/
│  ├─ __init__.py
│  ├─ index.py              # `sertor index <path> [--corpus] [--rebuild]`
│  ├─ search.py             # `sertor search <query> [--corpus] [--mode] [-k]`
│  └─ wiki.py               # `sertor wiki index <wiki_path>`
├─ observability.py         # logging, exit codes, config dictConfig YAML/JSON
└─ output.py                # formatter testo/JSON, anteprime troncate
```

**Console script:** `sertor` nel `pyproject.toml` della CLI (distribuzione fuori scope).

**Dipendenze aggiunte:** solo `sertor-core` (che ha già Chroma, httpx, tree-sitter, python-dotenv). Zero nuove dipendenze per la CLI; composizione root + imports lazy per `[azure]` opzionali dal core.

### Principio di design (Clean Architecture)

**Principio I (Core isolation, [[costituzione-v1]]):**
- Core (`sertor_core`) è immutato; CLI è un layer sottile.
- Nessun import nel domain del core (adapters, config, logging; tutto esterno).
- CLI è un **adapter**: argparse → composizione root del core → output.

**Principio IX (Osservabilità):**
- Logging strutturato stdlib + formatter JSON interno (zero dipendenze aggiuntive).
- Mapping eccezioni dominio → messaggi leggibili + exit code.
- Config logging non imposta: CLI passa il file dictConfig YAML/JSON al core via `configure()`.

## Funzionalità

### Sottocomandi

#### 1. `sertor index <path>`
Indicizza un percorso (file/directory) nel vector store.

**Opzioni:**
- `--corpus <name>` — collezione di destinazione (default: `default`). Abilita namespacing per provenienza (es. `prototype`, `production`).
- `--rebuild` — rebuild completo (drop collezione, re-embed, re-index).
- `-v/--verbose` — level INFO (default: WARNING).

**Uscita:**
- Testo: `Indexed <N> files, <M> chunks into corpus '<corpus>'.`
- JSON (`--json`): `{ "operation": "index", "corpus": "...", "files": N, "chunks": M }`

#### 2. `sertor search <query>`
Ricerca nel vector store.

**Opzioni:**
- `--corpus <name>` — collezione origine (default: `default`).
- `-k <int>` — top-k risultati (default: ereditato dal core = 5).
- `--mode {both,semantic}` — modalità (default: `both`, ereditato dal core).
- `-v/--verbose` — level INFO.
- `--full` — testo completo dei risultati (default: anteprime troncate a 200 char per economia token).

**Uscita:**
- Testo: lista risultati con score, path, preview.
- JSON: array risultati con metadati.

#### 3. `sertor wiki index <wiki_path>`
Indicizza il wiki (cartella).

**Opzioni:**
- `-v/--verbose`
- `--corpus <name>` — collezione per il wiki (utile per dogfooding, es. `production`).

**Uscita:**
- Testo: `Indexed wiki '<wiki_path>' into corpus '<corpus>': <N> pages, <M> chunks.`
- JSON: metadata del wiki (frontmatter consolidato, struttura).

### Osservabilità

#### `observability.py`
- **Logging configurabile:** `configure(log_config_path: str | None, verbose: bool = False)`.
  - Se `log_config_path` → carica dictConfig YAML/JSON (permette appender esterni: file, syslog, Splunk, ELK senza toccare codice).
  - Se `verbose` → stdlib level INFO (debug dettagliato).
  - Default: WARNING + console stderr.
- **Mapping eccezioni dominio → exit code:**
  - `IndexNotFoundError` → 2 (index missing, richiede `--rebuild`).
  - `LLMNotConfiguredError` (FEAT-003) → 3 (credenziali mancanti).
  - `ValidationError` (schema, chunking) → 4 (input invalido).
  - `RuntimeError`, altri → 1 (errore generico).
  - Success (normalizzato) → 0.
- **Log strutturato core:** eccezioni sollevate nel core includono `log_error(operation, exc, **fields)` prima del raise (estensione additiva, Principio IX). Campi schema:
  - `operation` ∈ {index, search, wiki_create, wiki_index, …}.
  - `exception_type`, `message`, `traceback` (solo verbose).
  - `context` dict (corpus, path, query, ecc.) dipende operazione.

#### `output.py`
- **Formatter testo leggibile (default):** include path, score (0–1 normalizzato), anteprima.
- **JSON (`--json`):** output strutturato per agenti/piping.
- **Anteprime troncate (`PREVIEW_CHARS=200`):** economia token quando consumato da RAG/agente. Flag `--full` per testo intero.

## Decisioni applicate

| Codice | Titolo | Decisione | Implementazione |
|--------|--------|-----------|-----------------|
| **DA-C1** | Entry point pubblico | Console script `sertor` fuori scope; `python -m sertor_cli` e `sertor` (post-distribuzione) equivalenti. | `__main__.py` + argparse dispatcher |
| **DA-C2** | Collezioni namespaced | `--corpus <name>` per provenienza (prototipo/produzione). | Passato a `build_indexer()` del core; collections namespaced in Chroma |
| **DA-C3** | Config logging esterno | `--log-config <file>` YAML/JSON dictConfig stdlib. | `observability.configure(log_config_path)` + `logging.config.dictConfig()` |
| **DA-C4** | Output: testo + JSON | Testo di default; `--json` per agenti. Anteprime troncate (200 char). | `output.py` formatter context-aware; `--full` per intero |
| **DA-C5** | Zero cloud obbligatorie | RAG_BACKEND=local via config; Ollama + Chroma di default. | Import lazy Azure SDK del core; test con FakeEmbeddings Chroma |

## Stack tecnologico realizzato

| Componente | Scelta |
|-----------|--------|
| Parsing argomenti | **argparse** (stdlib, zero dipendenze) |
| Logging | **stdlib + formatter JSON interno** (zero dipendenze) |
| Composizione | **Reuse del core** (`build_indexer()`, `build_facade()`, `build_wiki()`) |
| LLM (wiki) | **Ollama + Azure OpenAI** (configurabile dal core via `RAG_BACKEND`) |
| Vector store | **Chroma default** + Azure Search opzionale (dal core) |
| Embedding | **Ollama `nomic-embed-text`** default + Azure OpenAI 3-large opzionale |

## Test suite

**File aggiunti:** `tests/test_cli_*.py` (4 file: index, search, wiki, observability).

**Copertura:** 100 passed + 2 xfail (soglie baseline, non critiche per CLI).

**Strategie:**
- Mock `build_indexer()`, `build_facade()`, `build_wiki()` del core → comportamento deterministico.
- Fixture autouse `reset_logging` in conftest: ripristina logger `sertor_core` tra i test (isola mutazione globale di `observability.configure()`).
- Parametrizzati: corpuses, modalità search, opzioni output.
- Error path: IndexNotFoundError, LLMNotConfiguredError, input validation.

## Conformità governance

### Constitution Check: 9/9 ✅

| Principio | Conformità | Note |
|-----------|-----------|------|
| **I** Core isolation | ✅ PASS | CLI = adapter sottile, zero mutazione core. Reuse composizione root. |
| **II** Provider intercambiabili | ✅ PASS | Flag `--corpus` isola collezioni; core già multi-provider via `RAG_BACKEND`. |
| **III** Semplicità YAGNI | ✅ PASS | argparse (no click), zero config built-in (è nei file). Sottocomandi essenziali. |
| **IV** Gestione errori esplicita | ✅ PASS | Mapping eccezioni dominio → exit code, log strutturato, messaggio leggibile. |
| **V** Testabilità | ✅ PASS | 100% test; mock composizione; parametrizzati; no I/O effettivo. |
| **VI** Idempotenza | ✅ PASS | `--rebuild` flag per re-index; `index_wiki()` idempotente (FEAT-003); cli stateless. |
| **VII** Leggibilità | ✅ PASS | Nomi funzioni/variabili chiari; docstring su commands; no magic. |
| **VIII** Config centralizzata | ✅ PASS | Settings del core + `--log-config` per dictConfig; env vars via `.env`. |
| **IX** Osservabilità | ✅ PASS | Logging strutturato, formatter JSON, mapping eccezioni, config esterno. |

### Speckit Analyze: **FR 14/14 ✅, 0 critical, Complexity ∅**

## Artefatti

- **Codice:** `src/sertor_cli/` (3 file command, 2 file utility).
- **Speckit:** `specs/004-cli-esecuzione/` (plan, tasks, research notes).
- **Test:** `tests/test_cli_index.py`, `test_cli_search.py`, `test_cli_wiki.py`, `test_cli_observability.py`.
- **Documentazione:** requisiti EARS in `requirements/sertor-cli/esecuzione/requirements.md` (26 REQ).

## Significato: primo entry point eseguibile

Questa feature abilita:

1. **Dogfooding di produzione:** indicizzare source, specs, wiki di Sertor stesso in collezione `production`, usando i comandi `sertor index` e `sertor wiki index`.
   - Prerequisito: provider di embedding reale (Ollama o Azure OpenAI).
   - Use case: RAG interno sul codebase/design per decision support durante sviluppo.

2. **Validazione architettura:** il composition root del core + layer CLI sottile imbastisce il design Clean Architecture; questo è proof-of-concept che funziona.

3. **Estendibilità:** la struttura `argparse` + commands faccia a faccia con composizione root è pattern per future skill (FEAT-CLI-005/006/007 gestione edge per ibrido/grafo/agentico).

## Linkage

- **Dipende da:** [[implementazione-nucleo-retrieval]] (FEAT-001), [[motore-baseline-feat002]] (FEAT-002), [[skill-wiki-feat003]] (FEAT-003).
- **Abilita:** dogfooding di produzione (deciso per prossima sessione).
- **Precede:** FEAT-CLI-005 (ricerca ibrida), FEAT-CLI-006 (grafo), FEAT-CLI-007 (agentico).

## Processo

- **Branch:** `spec/004-cli-esecuzione` da master (FEAT-001/002/003 già mergiati).
- **Fase requisiti (EARS):** 26 REQ definite; commit 8faf767, 1831ac0.
- **Fase spec (SpecKit):** piano + decisioni DA-C1..C5; commit ef00c4d.
- **Fase planning:** task list 17 item; commit 980d323.
- **Fase implementation + test:** 17/17 task completati, 100% test coverage.
- **Prossimo:** merge a master, release candidata 0.1.0-rc1 (o alpha a seconda roadmap).

## Domande aperte

- **Q1: Release planning** — quando/come distribuire (PyPI, uv install, conda)?
- **Q2: Selezione skill CLI** — FEAT-CLI-005/006/007 sono obbligatori nel MVP o post-release?
- **Q3: Dogfooding priorità** — se risorse limitate, indicizzare production corpus ora (FEAT-CLI-004 ready) o posticipare?
