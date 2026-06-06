---
description: "Task list — Server MCP di produzione (sertor_mcp)"
---

# Tasks: Server MCP di produzione (`sertor_mcp`)

**Input**: design in `specs/007-mcp-sertor-core/` (plan.md, spec.md, research.md, data-model.md, contracts/)

**Tests**: inclusi (RNF-002 lo richiede; esiste un test di riferimento sul branch).

**Organization**: per user story (US1 P1 · US2 P2 · US3 P3), con setup e foundational a monte.

**Riferimento**: `feat/mcp-sertor-core` (commit `53b8e43`) — `src/sertor_mcp/server.py` + `__init__.py`
+ `tests/unit/test_mcp_server.py`. Si porta **solo** questo (no CLI/wiki dello stack morto), adattando
corpus e **aggiungendo** osservabilità + gestione errori.

## Format: `[ID] [P?] [Story] Descrizione`
- **[P]**: parallelizzabile (file diversi, nessuna dipendenza)
- Percorsi esatti inclusi.

---

## Phase 1: Setup (infrastruttura condivisa)

- [ ] T001 Creare il pacchetto `src/sertor_mcp/` con `__init__.py` (docstring di scopo: layer sottile
  sul core, Principio I) — partendo dal riferimento `feat/mcp-sertor-core:src/sertor_mcp/__init__.py`.
- [ ] T002 In `pyproject.toml`: aggiungere l'extra opzionale `mcp = ["mcp>=1.2"]` sotto
  `[project.optional-dependencies]` e aggiungere `"src/sertor_mcp"` a
  `[tool.hatch.build.targets.wheel].packages`. **NON** toccare lo script `sertor-wiki-tools` né altri
  pacchetti (no copia del pyproject del branch). *(REQ-060 / R7)*
- [ ] T003 `uv sync --extra mcp --extra dev` per installare l'SDK MCP isolato e i tool di test.

**Checkpoint**: pacchetto e dipendenze pronti.

---

## Phase 2: Foundational (prerequisiti bloccanti)

**⚠️ Blocca tutte le user story.**

- [ ] T004 In `src/sertor_mcp/server.py`: istanziare `FastMCP("sertor-rag", instructions=...)` con le
  istruzioni che guidano la scelta del tool e la citazione dei file. *(FR-014 / R1)*
- [ ] T005 Implementare l'aggancio al core: funzione memoizzata (`functools.lru_cache(maxsize=1)`) che
  costruisce la facade con `build_facade(Settings.load())`. *(FR-005/FR-006 / R3)*
- [ ] T006 Implementare il formattatore `_fmt(RetrievalResult) -> dict` con campi stabili
  `{path, source, chunk, score, preview}`, anteprima normalizzata e **troncata** a `_PREVIEW` con
  marcatore. *(FR-010/FR-011 / data-model)*
- [ ] T007 Configurare l'**osservabilità**: logger strutturato (riusare
  `sertor_core.observability.logging` se idoneo) per loggare ogni invocazione e i warning; nessun
  segreto. *(Principio IX / RNF-004 / R8 — GAP del riferimento da colmare)*

**Checkpoint**: facade, formato e logging pronti; i tool possono agganciarvisi.

---

## Phase 3: User Story 1 — L'agente interroga la codebase via tool MCP (P1) 🎯 MVP

**Goal**: tre tool di ricerca funzionanti che delegano alla facade e restituiscono risultati formattati.

**Independent Test**: con un indice presente, `list_tools()` mostra i 3 tool; ciascuno restituisce
risultati col formato atteso e il filtro corretto (code/doc/combined).

### Tests US1
- [ ] T008 [P] [US1] `tests/unit/test_mcp_server.py`: test "i 3 tool sono registrati" (`list_tools()`
  ⊇ `{search_code, search_docs, search_combined}`) — dal riferimento. *(SC-002)*
- [ ] T009 [P] [US1] Test "formato risultati": `_fmt`/tool restituisce dict con chiavi esattamente
  `{path, source, chunk, score, preview}`; con facade **mock** (`FakeEmbedder`/`InMemoryStore`).
  *(FR-010/SC-003)*
- [ ] T010 [P] [US1] Test "filtro per tipo": `search_code` → tutti `source=="code"`; `search_docs` →
  tutti `source=="doc"`. *(FR-003)*

### Implementazione US1
- [ ] T011 [US1] In `server.py`: tool `search_code(query, k=...)` → `_facade().search_code(query, k)`
  mappato via `_fmt`, con log (T007). *(FR-002/FR-003)*
- [ ] T012 [US1] Tool `search_docs(query, k=...)` analogo (filtro doc). *(FR-002/FR-003)*
- [ ] T013 [US1] Tool `search_combined(query, k=...)` analogo (code+doc). *(FR-002/FR-005)*
- [ ] T014 [US1] `main()` che avvia `mcp.run()` (stdio) + guardia `if __name__ == "__main__"`.
  *(FR-001/REQ-030)*

**Checkpoint**: US1 funzionante e testabile da sola (MVP).

---

## Phase 4: User Story 2 — Degrado robusto su indice mancante / errore (P2)

**Goal**: nessun crash su indice assente; errori reali leggibili; server resta vivo.

**Independent Test**: avvio senza indice → tool restituisce `[]` + warning, nessuna eccezione; una
seconda invocazione funziona.

### Tests US2
- [ ] T015 [P] [US2] `tests/unit/test_mcp_server.py`: test "indice mancante → lista vuota + warning,
  nessuna eccezione" (facade/store mock che simula assenza indice). *(FR-012/REQ-050/SC-006)*
- [ ] T016 [P] [US2] Test "errore interno → errore leggibile, server ancora invocabile" (la chiamata
  successiva ritorna normalmente). *(FR-013/REQ-051)*

### Implementazione US2
- [ ] T017 [US2] Verificare/garantire che il percorso "indice mancante" passi dal comportamento
  tollerante della facade (`[]`) e che il server logghi un **warning** dedicato senza sollevare.
  *(FR-012)*
- [ ] T018 [US2] Garantire che un errore reale del motore sia propagato come errore di tool leggibile
  (l'SDK MCP lo serializza) senza lasciare stato; nessun `except` che inghiotta silenziosamente.
  *(FR-013/Principio IV)*

**Checkpoint**: US1 + US2 funzionano in modo indipendente.

---

## Phase 5: User Story 3 — Config host-agnostica e sostituzione del prototipo (P3)

**Goal**: corpus/backend da config; binding del repo → server di produzione, corpus `sertor`.

**Independent Test**: cambiare `SERTOR_CORPUS`/`RAG_BACKEND` cambia la destinazione senza toccare il
codice; `.mcp.json` avvia il server di produzione.

### Implementazione US3
- [ ] T019 [US3] Verificare (test o ispezione) che il server **non** contenga corpus/percorsi
  hardcoded: tutto da `Settings`. *(FR-007/FR-009/SC-004/Principio X)*
- [ ] T020 [US3] Aggiornare `.mcp.json` (radice): `command` al python del venv core, `args`
  `["-m","sertor_mcp.server"]`, `env { "SERTOR_CORPUS": "sertor" }`. Rimuovere il riferimento al
  server del prototipo. *(FR-008/FR-015/SC-007)*
- [ ] T021 [P] [US3] (opz.) Annotare in `.env.example` `SERTOR_CORPUS=sertor` per il dogfood di
  produzione. *(quickstart §2)*

**Checkpoint**: tutte le user story indipendentemente funzionali.

---

## Phase 6: Polish & validazione

- [ ] T022 [P] `uv run ruff check src/sertor_mcp tests/unit/test_mcp_server.py` (lint pulito) e
  `uv run pytest tests/unit/test_mcp_server.py` (verde, `not cloud`).
- [ ] T023 Eseguire la validazione del `quickstart.md` (passi 1–6): build extra, configurazione,
  avvio, verifica dei 3 tool (con e senza indice). *(SC-001/SC-006)*
- [ ] T024 [P] (dogfood, **precondizione di SC-005**, fuori dal codice della feature) costruire
  l'indice del corpus `sertor` sui sorgenti di produzione (`src/`, `specs/`, `requirements/`, `wiki/`)
  via il nucleo/CLI, e verificare manualmente che i 3 tool restituiscano risultati pertinenti. *(SC-005)*

---

## Dependencies & Execution Order

- **Setup (P1)** → **Foundational (P2)** → blocca le user story.
- **US1 (P3 fase)** dopo Foundational; è l'MVP.
- **US2** e **US3** dopo Foundational; indipendenti da US1 ma più naturali dopo (US2 usa i tool di US1
  per il test di degrado; US3 è config/binding).
- **Polish (P6)** dopo le user story desiderate.

### Parallel Opportunities
- T008/T009/T010 (test US1) in parallelo; T015/T016 (test US2) in parallelo.
- T021/T022/T024 marcati [P] (file diversi).

## Implementation Strategy

MVP = Setup + Foundational + US1 → STOP e valida i 3 tool. Poi US2 (robustezza), poi US3
(config/binding + sostituzione prototipo). T024 (dogfood) è esercizio d'accettazione, dipende dal
nucleo/CLI per la build dell'indice.

## Note
- Commit per gruppo logico (delegato al `configuration-manager`).
- Verificare che i test falliscano prima dell'implementazione dove applicabile.
- Non reintrodurre lo stack morto del branch (CLI/wiki): solo `sertor_mcp` + test.
