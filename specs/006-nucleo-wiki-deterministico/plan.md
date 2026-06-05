# Implementation Plan: Nucleo wiki deterministico host-agnostico (FEAT-003-D)

**Branch**: `spec/006-nucleo-wiki-deterministico` | **Date**: 2026-06-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/006-nucleo-wiki-deterministico/spec.md`

## Summary

Nucleo **deterministico e host-agnostico** delle operazioni del LLM Wiki, dentro `sertor-core`: tutto il
*meccanico* (config-profilo, struttura, convenzioni/frontmatter, scan mtime, lint strutturale, enumerazione,
registri idempotenti, orchestrazione indicizzazione a collezioni separate) con **zero LLM**. Guidato da un file di
configurazione dell'ospite (`wiki.config.toml`): lo stesso codice gira su qualsiasi progetto cambiando solo la
config (Principio X). Espone una CLI che emette **contratti JSON versionati** consumati da hook/skill sottili e dalla
metà LLM (FEAT-003-N), che vi costruisce sopra (DRY).

## Technical Context

**Language/Version**: Python ≥ 3.11

**Primary Dependencies**: **solo stdlib** per il nucleo (`tomllib`, `pathlib`, `re`, `json`, `dataclasses`,
`datetime`) — **nessuna nuova dipendenza di terze parti**. Riusa `sertor_core` esistente: `config/` (Settings),
`domain/errors`, `observability/logging`. La sola operazione di *indicizzazione* (US5) riusa il
facade/indexer esistente di `sertor_core` (Chroma via adapter già presente) — import **lazy**, non richiesto dalle
altre operazioni.

**Storage**: filesystem (i file Markdown del wiki). Per la sola US5: il vector store esistente (Chroma in locale) via
gli adapter di `sertor-core`.

**Testing**: `pytest` (unit, marker `not cloud`), repo finto in `tmp_path`, riuso di `tests/fixtures/` e
`tests/conftest.py`. Nuova fixture: un **ospite finto `doc-only`** per provare SC-001.

**Target Platform**: cross-platform (Windows + Linux), esecuzione **locale**.

**Project Type**: libreria + CLI sottile, **dentro** il pacchetto `sertor-core` (nuovo sottopacchetto `wiki_tools`).

**Performance Goals**: operazioni **lineari** nel numero di file Markdown; completano **in locale, senza rete**, in
tempi trascurabili per wiki tipici (centinaia di pagine). Nessun obiettivo di throughput di rete (non applicabile).

**Constraints**: **zero LLM / offline** (SC-005); **host-agnostico** (Principio X, SC-001); **idempotente e
non-distruttivo** (SC-002/006); errori espliciti; log strutturati.

**Scale/Scope**: wiki fino a migliaia di file Markdown (scaling lineare, coerente con RNF-007 del consolidato).

## Constitution Check

*GATE: superato prima di Phase 0 e ri-verificato dopo Phase 1.* Costituzione v1.1.0 (10 principi).

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** `wiki_tools` è *policy*; dipende solo da
  `config/`, `domain/errors`, `observability/`; **non** importa SDK di provider né la CLI; l'unico aggancio al
  vector store (US5) passa per il facade/adapter esistente (astrazione del core), import lazy. Testabile con repo finto
  senza cloud/CLI. **PASS**
- [x] **II — Boundary & local-first:** nessuna nuova dipendenza esterna; tutto gira in locale; il vector store serve
  **solo** all'operazione di indicizzazione (US5), dietro l'astrazione esistente. **PASS**
- [x] **III — YAGNI & unità piccole:** stdlib + `tomllib` nativo, frontmatter via regex (no lib esterne); un modulo
  piccolo per operazione (SRP); nessuna astrazione speculativa. **PASS**
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** `ConfigError` su config assente/malformata; indice/registro
  mancante → errore esplicito o avviso+skip documentato; **niente** `None` silenzioso né stato parziale. **PASS**
- [x] **V — Testabilità & misure:** unit F.I.R.S.T. con repo finto in `tmp_path`, offline; "misura" della feature =
  SC-004 (lint rileva il 100% dei difetti iniettati, 0 falsi positivi) e SC-001/002. La misura di *qualità retrieval*
  (hit@k/MRR) resta del motore esistente riusato in US5, non reintrodotta qui. **PASS**
- [x] **VI — Idempotenza & non-distruttività:** operazioni read-only idempotenti per costruzione; init struttura non
  sovrascrive; registri/index idempotenti; **id stabile = path relativo**. **PASS**
- [x] **VII — Leggibilità:** naming di dominio (`profile`, `scan`, `lint`, `collect`, `structure`, `registry`). **PASS**
- [x] **VIII — Configurabilità centralizzata:** tutta la specificità dell'ospite in **una** config (`wiki.config.toml`
  → `WikiProfile`); nessun default hardcoded nei componenti (il profilo di default è *dato esterno* sostituibile).
  `wiki.config.toml` è **complementare** a `Settings` (che resta per provider/backend del RAG), non duplicato: assi
  diversi (struttura-ospite vs operatività-RAG). **PASS**
- [x] **IX — Osservabilità:** ogni operazione emette log strutturati (operazione, profilo, conteggi, esiti, errori)
  via `observability.logging`; nessun segreto. **PASS**
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** è la ragion d'essere della feature — nessuna assunzione dell'ospite nel
  corpo; tutto da config; **prova SC-001** (stesso nucleo su ospite `code+doc` e `doc-only` cambiando solo la config).
  Il default = profilo Sertor è un file esterno, non una costante. **PASS**

**Esito gate (pre-Phase 0 e post-Phase 1): ✅ PASS su tutti e 10 i principi (incl. i NON-NEGOZIABILI I, IV, X).
Nessuna violazione → "Complexity Tracking" non compilato.**

## Project Structure

### Documentation (this feature)

```text
specs/006-nucleo-wiki-deterministico/
├── plan.md              # questo file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/           # Phase 1 (CLI + contratti JSON)
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
src/sertor_core/wiki_tools/        # NUOVO sottopacchetto (dipende solo da config/, domain/errors, observability/)
├── __init__.py                    # riesporta le funzioni/operazioni pubbliche
├── profile.py                     # WikiProfile: carica/valida wiki.config.toml (tomllib); default = profilo Sertor
├── frontmatter.py                 # parse/validate frontmatter via regex; estrazione wikilink
├── structure.py                   # init struttura wiki (idempotente, non-distruttiva)
├── scan.py                        # ricerca lavoro pendente (mtime vs ultima voce di log)
├── lint.py                        # lint meccanico: link rotti, orfani, frontmatter mancante
├── collect.py                     # enumerazione pagine + metadati (mappa, senza corpo)
├── registry.py                    # mechanics index/log idempotenti; id stabile = path relativo
├── indexing.py                    # orchestrazione indicizzazione a collezioni separate (riusa facade/indexer)
├── contracts.py                   # dataclass dei contratti JSON versionati
└── __main__.py                    # CLI: python -m sertor_core.wiki_tools <op> --config ... --json

wiki.config.toml                   # (radice) profilo host di Sertor (dogfooding)

tests/
├── fixtures/
│   ├── sample_repo/               # esistente (riuso)
│   └── doc_only_host/             # NUOVA fixture: ospite finto solo-doc per SC-001
└── unit/
    ├── test_wiki_tools_profile.py
    ├── test_wiki_tools_frontmatter.py
    ├── test_wiki_tools_structure.py
    ├── test_wiki_tools_scan.py
    ├── test_wiki_tools_lint.py
    ├── test_wiki_tools_collect.py
    └── test_wiki_tools_registry.py

pyproject.toml                     # + [project.scripts] sertor-wiki-tools = "sertor_core.wiki_tools.__main__:main"
```

**Structure Decision**: sottopacchetto **`src/sertor_core/wiki_tools/`** isolato per dipendenze (solo
`config/`+`domain/errors`+`observability/`, mai un modulo `wiki/` LLM) — così è la base meccanica condivisa, riusabile
dalla metà LLM (FEAT-003-N) e candidata per V3, senza accoppiarsi al giudizio. Il `.claude/hooks/wiki-pending-check.ps1`
diventerà un **thin wrapper** sulla CLI `scan` (refactor lato hook, fuori dal pacchetto Python — incluso nei task).

## Complexity Tracking

> Nessuna violazione del Constitution Check → tabella non compilata.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
