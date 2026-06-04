---
description: "Task list — LLM Wiki end-to-end (FEAT-010)"
---

# Tasks: LLM Wiki end-to-end (FEAT-010)

**Input**: design da `specs/005-llm-wiki/` (spec, plan, research, data-model, contracts, quickstart).
**Riuso**: FEAT-001 (nucleo), FEAT-002 (baseline), FEAT-003 (wiki: create_wiki/record/distill/index_wiki/
conventions). **Tests**: inclusi, su wiki sandbox con **LLM scriptato** + **FakeGit** (nessuna rete).
**Vincoli**: Principio I (GitPort, gate fuori dal dominio, generazione = servizio distinto invocato dal
versioning), III (no duplicazione), VI (manual_edited mai modificato, idempotenza, gate revisionabile).

## Format: `[ID] [P?] [Story] Descrizione (file)`

---

## Phase 1: Setup
- [X] T001 Verifica i pacchetti esistenti `src/sertor_core/wiki/`, `src/sertor_cli/`, `src/sertor_mcp/`; nessun nuovo package.

## Phase 2: Foundational (blocca tutte le storie)
- [X] T002 [P] Definisci `GitPort` (Protocol) in `src/sertor_core/domain/ports.py`: `changed_paths(scope, watermark=None)`, `head_commit()`, `renamed_paths()`.
- [X] T003 [P] Implementa `SubprocessGitAdapter(GitPort)` in `src/sertor_core/adapters/git/subprocess_git.py` (+ `__init__.py`); best-effort (errori → `[]`/`None`).
- [X] T004 [P] Aggiungi `FakeGit` deterministico in `tests/fixtures/mocks.py` (changed/head/renames preconfigurati, scope-aware).
- [X] T005 [P] Estendi `src/sertor_core/wiki/conventions.py`: costanti aree `manual_edited/` e `ingested_sources/`; provenance `generated|manual` (read/mark non distruttivo); cartella di stato `.sertor/` (watermark) esclusa dalla scoperta pagine.
- [X] T006 [P] Helper `entity_page_map(root) -> dict[str, set[str]]` (derivato da frontmatter `sources:`/wikilink) in `conventions.py` (o `wiki/_mapping.py`).
- [X] T007 [P] Estendi `src/sertor_core/config/settings.py`: insieme **fonti-input** configurabile, **soglia gate**, **gerarchia di autorità**, nomi delle **collezioni separate** (wiki/codice).

**Checkpoint**: porta+adapter+fake, convenzioni aree/provenance/mappa, Settings pronti.

---

## Phase 3: US2 — Generazione al commit (P1/Must) 🎯 MVP
**Test indipendente**: con FakeGit+ScriptedLLM, baseline vs incrementale generano set di pagine diversi; `manual_edited/` mai modificato; idempotenza.
### Tests
- [X] T008 [P] [US2] Test `tests/unit/test_wiki_generation.py`: baseline (no watermark → tutte), incrementale (changeset → solo pagine collegate via EntityPageMap), no-op; `mode`/`fallbacks`; `manual_edited/` compilato ma **file invariato**; fallback `stale-index` segnalato.
- [X] T009 [P] [US2] Test idempotenza: re-run con input invariato → stesso esito strutturale (id = path relativo).
### Implementation
- [X] T010 [US2] Entità `GenerationReport` (mode/pages_written/pages_total/llm_calls/fallbacks) in `src/sertor_core/wiki/generation.py`.
- [X] T011 [US2] `generate(root, llm, *, sources, git=None, scope="since_watermark", facade=None, max_pages=None) -> GenerationReport`: legge le fonti-input, compila concetti/sintesi via LLM, incrementale sul changeset; riusa `record`/`distill`/`conventions`; non modifica `manual_edited/`; fallback re-index segnalato.

**Checkpoint**: generazione eseguibile (baseline + incrementale) con FakeGit.

---

## Phase 4: US4 — Retrieval su collezioni separate (P1/Must) 🎯 MVP
**Test indipendente**: indicizzato solo il wiki generato; input assenti dai risultati; refresh indipendente.
### Tests
- [X] T012 [P] [US4] Test `tests/unit/test_wiki_index_separated.py`: indicizza **solo** wiki generato (collezione separata); `manual_edited/`/`ingested_sources/` **non** indicizzati; riferimenti non indicizzati; query congiunta col codice restituisce entrambi (mock store).
### Implementation
- [X] T013 [US4] `index_wiki_generated(root, settings) -> IndexReport` in `src/sertor_core/wiki/indexing.py`: indicizza il solo wiki generato in **collezione separata**; esclude le aree di input e la cartella di stato; refresh indipendente (no rebuild della collezione codice).
- [X] T014 [US4] Estendi la facade/composition per la **query congiunta** wiki+codice (collezioni separate) con peso paritario.

**Checkpoint**: MVP retrieval verde (US2+US4).

---

## Phase 5: US1 — Setup `sertor wiki init` (P1/Must) 🎯 MVP
**Test indipendente**: init crea struttura, installa il binding del trigger, esegue ingest iniziale opz.
### Tests
- [X] T015 [P] [US1] Test `tests/unit/test_wiki_setup.py`: `init_wiki` crea struttura (riusa `create_wiki`), registra/installa il binding del trigger (mock), ingest iniziale opzionale; idempotente.
### Implementation
- [X] T016 [US1] `init_wiki(root, *, install_binding=True, initial_ingest=None) -> SetupReport` in `src/sertor_core/services/wiki_setup.py` (riusa `create_wiki`; binding via porta/astrazione).
- [X] T017 [US1] CLI `sertor wiki init <root> [--ingest <path>]` in `src/sertor_cli/` (sottocomando + wiring).

**Checkpoint**: MVP completo (US1+US2+US4) — il wiki si inizializza e si genera al commit.

---

## Phase 6: US3 — Ingest in `ingested_sources/` (P2/Should)
### Tests
- [ ] T018 [P] [US3] Test `tests/unit/test_wiki_ingest_sources.py`: import in `ingested_sources/` (creazione/on-demand/update); **import ≠ compile** (nessuna pagina-riassunto); binari non leggibili esclusi.
### Implementation
- [ ] T019 [US3] `ingest_sources(root, items, *, dry_run=False) -> IngestReport` in `src/sertor_core/wiki/ingest_sources.py` (import only).
- [ ] T020 [P] [US3] CLI `sertor wiki ingest <root> <path…>` + [P] tool MCP `wiki_ingest` in `src/sertor_mcp/`.

**Checkpoint**: ingest disponibile dalle superfici.

---

## Phase 7: US5 — Manutenzione + Gate al commit (P2/Should)
**Test indipendente**: lint rileva link/orfani; freschezza rileva obsoleto vs codice/decisione; gate blocca/avvisa/propone/override.
### Tests
- [ ] T021 [P] [US5] Test `tests/unit/test_wiki_maintenance.py`: `lint` (link rotti, orfani, copertura/cross-ref) LLM-free; `freshness` (ScriptedLLM) obsoleto vs codice/test o vs decisione; incrementale sul changeset (FakeGit) vs full.
- [ ] T022 [P] [US5] Test `tests/unit/test_wiki_gate.py`: `run_commit_gate` → `blocked` sopra soglia con **≥1 proposta** incl. "ignora e committa"; `warning` sotto soglia; `override=True` → procede e **registra**; CLI `gate` blocked → **exit≠0**.
### Implementation
- [ ] T023 [US5] `lint(root) -> LintReport` e `freshness(root, llm, facade, git=None, *, scope, authority) -> FreshnessReport` in `src/sertor_core/wiki/maintenance.py` (riusa/estende le funzioni del wiki; LLM-free per il lint).
- [ ] T024 [US5] `run_commit_gate(root, llm, facade, git, *, threshold, authority, override=False, override_reason=None) -> GateOutcome` in `src/sertor_core/services/wiki_gate.py` (FUORI dal dominio: blocca/avvisa/propone soluzioni, override tracciato, human-in-the-loop).
- [ ] T025 [US5] CLI `sertor wiki lint|gate` (gate: `blocked`→exit≠0, `--override --reason`) + tool MCP `wiki_lint`/`wiki_gate`.

**Checkpoint**: manutenzione + gate al commit operativi.

---

## Phase 8: US6 — Superfici (P2/Should)
### Tests
- [ ] T026 [P] [US6] Test `tests/unit/test_wiki_surfaces.py`: parità funzionale skill/CLI/MCP per le operazioni on-demand (generate/ingest/lint/gate/index); query via RAG.
### Implementation
- [ ] T027 [US6] Completa CLI `sertor wiki generate|index` in `src/sertor_cli/` (wiring sui servizi).
- [ ] T028 [P] [US6] Completa i tool MCP `wiki_generate` in `src/sertor_mcp/` (allineati alla CLI).

**Checkpoint**: tre superfici allineate.

---

## Phase 9: US7 — No-code + Polish (P3/Could + polish)
- [ ] T029 [US7] Percorso **senza codice**: generazione/retrieval/manutenzione operano con le sole fonti documentali (codice = fonte opzionale); test dedicato `tests/unit/test_wiki_no_code.py`.
- [ ] T030 [P] [US7] Trigger **periodico** (full) per lint+freschezza (entrypoint/scheduling-friendly).
- [ ] T031 [P] [US7] **Gerarchia di autorità configurabile** (Settings) applicata in `freshness`/gate.
- [ ] T032 [P] Run full suite + ruff; verifica idempotenza/non-distruttività e **Constitution Check 9/9**.
- [ ] T033 [P] Aggiorna `src/sertor_core/README.md`: sezione "LLM Wiki end-to-end".
- [ ] T034 Dogfood (opzionale, **non in questo ciclo**, passo manuale): `sertor wiki init` + commit su Sertor stesso; registra esito.

---

## Dependencies
- **Foundational (Ph2)** blocca tutto: T002..T007 prima delle storie.
- **MVP**: US2 (Ph3) + US4 (Ph4) + US1 (Ph5) = il cuore (generazione + retrieval + setup).
- US3 (Ph6) usa le convenzioni (T005). US5 (Ph7) usa generazione/changeset (T011) + facade. US6 (Ph8) dopo che i servizi esistono. US7/polish (Ph9) per ultimo.
- Dentro una storia: i test [P] in parallelo; l'implementazione che tocca lo stesso file serializza.

## Parallel execution (esempi)
- Foundational: `T002`/`T003`/`T004`/`T005`/`T006`/`T007` in parallelo (file distinti).
- Test [P]: `T008`/`T012`/`T015`/`T018`/`T021`/`T022`/`T026` scrivibili in parallelo.

## Mapping US→FR/SC
- US1=FR-101/040/028 (SC-008) · US2=FR-102/103/104/113 (SC-001/006) · US3=FR-103/105/030/031/022 (SC-010) ·
  US4=FR-106/107/010/011/023/024 (SC-002/003) · US5=FR-108/109/110/017/035..038/041/042 (SC-004/009) ·
  US6=FR-111/032/033 (SC-007) · US7=FR-112/029 (SC-005).

## MVP
**US1 + US2 + US4** (setup + generazione al commit + retrieval collezioni separate): il wiki si
inizializza, si genera incrementalmente al commit ed è interrogabile insieme al codice.
