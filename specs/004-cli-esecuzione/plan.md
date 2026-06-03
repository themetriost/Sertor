# Implementation Plan: CLI — esecuzione delle capacità del core

**Branch**: `spec/004-cli-esecuzione` | **Date**: 2026-06-03 | **Spec**: [spec.md](spec.md)

**Input**: `specs/004-cli-esecuzione/spec.md` (deriva da `requirements/sertor-cli/esecuzione/requirements.md`).
Dipende da `sertor-core` (FEAT-001/002/003, in `master`).

## Summary

La CLI `sertor` è il **layer sottile** che rende eseguibili da terminale le capacità del core:
`index` (indicizza un repo), `search` (interroga), `wiki index` (indicizza un wiki), più
l'osservabilità a runtime (verbosity, JSON, `--log-config` per appender esterni). Non duplica il
core: ogni comando fa *parse argomenti → chiama il composition root → formatta l'output* (Principio I).

Tecnicamente è un nuovo pacchetto `src/sertor_cli/` con entry-point console-script `sertor`, costruito
con **argparse** (stdlib, nessuna dipendenza pesante — Principio III). Due piccole estensioni additive
al core completano l'osservabilità: **logging degli errori sui boundary** (REQ-053) e la
**documentazione dei campi di log** (REQ-054). I default vengono dal `Settings` del core (Principio
VIII); senza provider configurato le operazioni RAG sono bloccate (CS-5).

## Technical Context

**Language/Version**: Python ≥ 3.11.

**Primary Dependencies**: solo `sertor-core` (composition root + facce pubbliche) e la **stdlib**
(`argparse`, `logging`, `logging.config`, `json`). Per `--log-config` YAML serve un parser YAML:
`PyYAML` (già transitivo via chromadb; lo si dichiara). Nessuna dipendenza CLI pesante (no click/typer).

**Storage**: nessuno proprio; usa l'indice del core.

**Testing**: `pytest`. Comandi invocati via `main([...])` con `build_*` del core **monkeypatchati** a
mock (`FakeEmbedder`/`InMemoryStore`/`FakeLLM`): nessun cloud né rete (NFR-02). Verifica di output,
exit code, log emessi.

**Target Platform**: Linux + Windows (NFR-03).

**Project Type**: estensione del repo con un **secondo pacchetto** `src/sertor_cli/` che dipende da
`sertor_core`. Entry-point console-script `sertor`.

**Performance Goals**: nessuna soglia propria (la CLI è I/O sottile sul core).

**Constraints**: install ≠ run (nessun side-effect su import, REQ-060); non distruttività (REQ-013);
errori leggibili + exit code (REQ-003/NFR-04); segreti mai loggati/versionati (REQ-042/055).

**Scale/Scope**: comandi `index`/`search`/`wiki index` + opzioni di osservabilità; **fuori**:
distribuzione pubblica, install selettivo su altri repo, wizard config.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** la CLI dipende dal core (composition +
  facce pubbliche); il core **non** dipende dalla CLI. I comandi sono sottili (parse→chiama→formatta).
  Esercitabile con mock. → **PASS.**
- [x] **II — Boundary & local-first:** provider/backend scelti dalla config del core; la CLI non
  introduce nuovi boundary verso provider. → **PASS.**
- [x] **III — YAGNI & unità piccole:** `argparse` stdlib (niente click/typer); comandi piccoli a SRP;
  formatter JSON minimale interno (no dipendenza). → **PASS.**
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** le eccezioni di dominio del core sono mappate in
  messaggi leggibili + exit code non-zero; indice mancante → errore esplicito (REQ-022). Aggiunto il
  **logging degli errori** sui boundary del core (REQ-053). → **PASS.**
- [x] **V — Testabilità & misure:** ogni comando testato con mock via `main([...])`; output/exit/log
  verificati (NFR-02). → **PASS.**
- [x] **VI — Idempotenza & non-distruttività:** `index` non tocca i file utente; rebuild idempotente
  (ereditato dal core); install ≠ run (REQ-060). → **PASS.**
- [x] **VII — Leggibilità:** naming di dominio (`index`/`search`/`wiki`); comandi e opzioni espliciti. → **PASS.**
- [x] **VIII — Configurabilità centralizzata:** default da `Settings` del core (`default_k`, provider,
  corpus); nessun default duplicato nella CLI (REQ-021/040). → **PASS.**
- [x] **IX — Osservabilità:** la CLI configura il logging (verbosity/JSON/`--log-config`) rendendo
  visibili i log strutturati del core e collegabili ad appender esterni; errori loggati (REQ-050..055). → **PASS.**

**Esito gate (pre-Phase 0):** ✅ PASS su tutti i 9 principi. Complexity Tracking vuoto.

> **Evoluzione del core (additiva, non-breaking):** logging degli errori sui boundary
> (embeddings/store/index) + documentazione dei campi di log. Non cambia firme né comportamento.

## Project Structure

### Documentation (this feature)

```text
specs/004-cli-esecuzione/
├── plan.md · research.md · data-model.md · quickstart.md
├── contracts/cli-commands.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
src/sertor_cli/                 # NUOVO pacchetto — dipende da sertor_core
├── __init__.py
├── __main__.py                 # `python -m sertor_cli` → cli.main()
├── cli.py                      # parser argparse + dispatch + mapping errori→exit code
├── observability.py            # setup logging: -v/--verbose, --log-json (formatter), --log-config (dictConfig)
├── output.py                   # formattazione risultati: testo / JSON, anteprima troncata / --full
└── commands/
    ├── __init__.py
    ├── index_cmd.py            # `sertor index <path>` → build_indexer (REQ-010..014)
    ├── search_cmd.py           # `sertor search <query>` → build_facade/baseline (REQ-020..023)
    └── wiki_cmd.py             # `sertor wiki index <wiki>` → index_wiki (REQ-030/031)

src/sertor_core/                # estensioni additive (osservabilità)
├── observability/logging.py    # + helper per loggare errori (usato dai boundary)
└── adapters|services           # log dell'errore sui boundary prima del raise (REQ-053)

pyproject.toml                  # + [project.scripts] sertor = "sertor_cli.cli:main"; pkg sertor_cli; dep pyyaml

tests/
├── unit/
│   ├── test_cli_index.py       # US1
│   ├── test_cli_search.py      # US2
│   ├── test_cli_wiki.py        # US3
│   └── test_cli_observability.py  # US4 (verbosity/json/log-config + log errori)
└── fixtures/                   # riuso FakeEmbedder/InMemoryStore/FakeLLM
```

**Structure Decision**: secondo pacchetto `src/sertor_cli/` (la CLI è il *veicolo*, distinto dal core
che è la *libreria/prodotto*). Dipende da `sertor_core` e ne consuma il composition root. Entry-point
console-script `sertor`. La CLI resta sottile: nessuna logica RAG, solo orchestrazione+IO.

## Complexity Tracking

> Nessuna violazione del Constitution Check.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
