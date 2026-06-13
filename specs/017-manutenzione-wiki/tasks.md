---
description: "Task list — feature 017 manutenzione wiki deterministica"
---

# Tasks: Manutenzione wiki deterministica (move · reconcile · collect+status)

**Input**: Design da `specs/017-manutenzione-wiki/` (plan, spec, research, data-model, contracts, quickstart)

**Tests**: inclusi (Principio V; la suite `wiki_tools` è test-first). Tutti offline, senza LLM.

**Organization**: per user story (P1 → P2 → P3), ciascuna indipendentemente testabile.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizzabile (file diversi, nessuna dipendenza non risolta)
- Path: `src/sertor_core/wiki_tools/` (codice) · `tests/unit/` (test)

---

## Phase 1: Setup

- [ ] T001 Baseline verde: `uv run pytest tests/unit -q -k wiki_tools` e `uv run ruff check src tests` puliti (nessuna nuova dipendenza in questa feature — solo stdlib).

---

## Phase 2: Foundational (prerequisito condiviso)

- [ ] T002 [P] Estendere `src/sertor_core/wiki_tools/collect.py` (`_page_meta`) col campo `"status"` (D8, REQ-021/FR-007): `str(fields.get("status", ""))`, additivo e forward-compatible (`CollectResult`/`wiki.collect/1` invariato di struttura). Test in `tests/unit/test_wiki_tools_collect.py` (nuovo o esteso): pagina con/ senza `status`; consumatore che conosce solo `schema` legge senza errori.

**Checkpoint**: l'inventario espone `status`; le due story possono procedere.

---

## Phase 3: User Story 1 — `move`-con-link (Priority: P1) 🎯 MVP

**Goal**: spostare/rinominare una pagina riscrivendo tutti i link entranti, in sicurezza.

**Independent Test**: su un wiki tmp con pagine interconnesse, `move` sposta il file e riscrive
wikilink (`[[a]]`/`[[concepts/a]]`/`[[a|alias]]`) e link relativi entranti; `lint` post-move = 0
broken aggiuntivi; `--dry-run` 0 modifiche.

- [ ] T003 [US1] In `src/sertor_core/wiki_tools/contracts.py`: aggiungere `MoveResult` (`wiki.move/1`): `source`, `destination`, `rewritten: list[dict]`, `moved: bool`, `dry_run: bool` (data-model §1; `to_dict`/`to_json`).
- [ ] T004 [US1] Nuovo `src/sertor_core/wiki_tools/move.py` — `move(profile, src, dest, dry_run=False) -> MoveResult` (FR-001..006): risoluzione `src`/`dest` relativi alla radice wiki (`.md`); errori espliciti (sorgente assente; collisione dest+src REQ-013; path fuori radice); mappa old→new sulle 3 forme di `lint._link_targets` (form-preserving D1) con riscrittura wikilink (regex coerente con `_WIKILINK`, preserva `|alias`/`#anchor`) + link relativi Markdown (`posixpath.relpath`, D2); file processati = `iter_pages` + `index_path`, **non** le partizioni di log (D3); ordine **rewrite-then-move** + recovery da stato parziale (D5, idempotente); `log_event`. `--dry-run` non scrive nulla (FR-003).
- [ ] T005 [US1] In `src/sertor_core/wiki_tools/__main__.py`: `move` in `_OPS`; secondo positional `dest` (`nargs="?"`); flag `--dry-run`; dispatch in `_run` (valida src+dest presenti → `ConfigError`); riga in `_human` (`moved=… dry_run=… rewritten=… occurrences=…`); errori → `wiki.error/1` (path esistente).
- [ ] T006 [P] [US1] Test `tests/unit/test_wiki_tools_move.py`: riscrive `[[a]]`, `[[concepts/a]]`, `[[concepts/a.md]]`, `[[a|alias]]` (alias preservato) e link relativo `](../concepts/a.md)`; `--dry-run` → 0 file modificati + piano riportato; collisione dest+src → errore, 0 modifiche; sorgente assente → errore; recovery: interruzione simulata (file già spostato, link non tutti riscritti) → rieseguito = stato finale identico; spostamento **senza rename** non tocca i link a stem; post-move `lint` non riporta broken aggiuntivi.

**Checkpoint**: `move` completo e sicuro (MVP consegnabile).

---

## Phase 4: User Story 2 — `reconcile` detection (Priority: P2)

**Goal**: elencare (sola lettura) le pagine `status: superseded` per la riconciliazione.

**Independent Test**: su un wiki tmp con pagine superseded e non, `reconcile` elenca tutte e sole le
superseded (path/updated/superseded_by/reason) senza modificare nulla; nessuna → `clean:true`.

- [ ] T007 [US2] In `contracts.py`: aggiungere `ReconcileResult` (`wiki.reconcile/1`): `candidates: list[dict]` (`path`/`status`/`updated`/`superseded_by`/`reason`), `clean: bool` (data-model §1).
- [ ] T008 [US2] Nuovo `src/sertor_core/wiki_tools/reconcile.py` — `reconcile(profile) -> ReconcileResult` (FR-008..012): itera `iter_pages`, `parse_frontmatter`, filtra `status == "superseded"`; per ciascuna estrae `updated`, `superseded_by` (D6: solo frontmatter), `reason="status: superseded"`; `clean=True` se nessuna; **read-only** (mai scrive); `log_event`.
- [ ] T009 [US2] In `__main__.py`: `reconcile` in `_OPS`; dispatch in `_run`; riga in `_human` (`candidates=… clean=…`).
- [ ] T010 [P] [US2] Test `tests/unit/test_wiki_tools_reconcile.py`: elenca solo le superseded con i campi attesi (incl. `superseded_by`); pagine normali escluse; nessuna superata → `candidates=[] clean=true`; **read-only** (snapshot del filesystem prima/dopo identico); contratto `wiki.reconcile/1` forward-compatible.

**Checkpoint**: `reconcile` + `collect`/status completi.

---

## Phase 5: User Story 3 — trigger periodico (Priority: P3 · Could)

**Goal**: documentare la schedulazione, senza scheduler nel prodotto.

- [ ] T011 [US3] In `docs/install.md` (o sezione wiki): nota su come invocare `sertor-wiki-tools reconcile --json` da uno scheduler dell'ambiente ospite (cron / Task Scheduler / hook CI) verso un file di report (FR-013, D9). **Solo documentazione**; nessun codice.

---

## Phase 6: Polish & Cross-Cutting

- [ ] T012 [P] `docs/install.md`: aggiungere `move`/`reconcile` all'elenco delle operazioni `sertor-wiki-tools` (riferimento utente). *(Integrazione di move/reconcile nel playbook/skill agentici = follow-up separato, fuori da questa feature.)*
- [ ] T013 Suite completa + ruff: `uv run pytest tests -q -m "not cloud"` (+ `packages/sertor` se toccato) e `uv run ruff check src tests` puliti.
- [ ] T014 Re-index del corpus `sertor` (regola standing) — **dopo il merge** su master.

---

## Dependencies & Execution Order

- Setup (T001) → Foundational (T002) → US1 / US2 / US3.
- US1: T003 prima di T004; T004 prima di T005; T006 dopo T004/T005.
- US2: T007 prima di T008; T008 prima di T009; T010 dopo T008/T009. (T002 prerequisito di REQ-021, ma `reconcile` legge il frontmatter direttamente → US2 indipendente da US1.)
- US3 (T011) e Polish (T012) indipendenti; T013 dopo il codice; T014 post-merge.
- **Nota file condiviso:** `contracts.py` (T003, T007) e `__main__.py` (T005, T009) sono editati da entrambe le story → fare quei task in serie (non `[P]` tra loro), additivi.

## Parallel Opportunities

- T002 ∥ (dopo, dentro US1) T006 dopo il codice; T010 dopo il codice US2.
- US1 e US2 lavorabili in parallelo dopo il Foundational, attenzione ai due file condivisi (contracts/__main__): sezioni additive distinte.

## Coverage FR

FR-001..006 → T004/T006 · FR-007 → T002 · FR-008..012 → T008/T010 · FR-013 → T011 ·
FR-014 (forward-compat) → T003/T007/T002 · FR-015 (host-agnostico) → inerente + test.

## Implementation Strategy

- **MVP** = US1 (`move`): Setup + Foundational + Phase 3 → stop & validate.
- Incrementale: +US2 (`reconcile`+`collect`/status) → +US3 (doc) → polish.

## Notes

- Tutto deterministico/offline (Principio V); `reconcile` read-only (Principio VI); `move` tocca solo i file coinvolti + `--dry-run`.
- Coerenza `move`↔`lint`: stessa logica di target (`_link_targets`).
- Commit dopo ogni story o gruppo logico; re-index (T014) obbligato dopo il merge su master.
