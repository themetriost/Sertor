# Implementation Plan: Lint semantico del wiki (FEAT-007 — estensione)

**Branch**: `spec/005-wiki-manutenzione` | **Spec**: `specs/006-wiki-lint-semantico/spec.md`
**Date**: 2026-06-04 · **Updated**: 2026-06-04 (scope ampliato: US3 incrementale, US4-scrittura, US5 gate)

## Technical Context

- **Linguaggio**: Python ≥ 3.11. **Pacchetto**: estende `src/sertor_core/wiki/` + porta in `domain/ports.py`
  + adapter in `adapters/git/` + entrypoint gate nel layer CLI/services.
- **Dipendenze runtime**: solo core. LLM via porta `LLMProvider` (`composition.build_llm`); contesto codice
  via facade di retrieval (`composition.build_facade`, corpus `production`); **git via porta `GitPort`**
  (adapter `subprocess` fuori dal dominio — nuovo).
- **LLM-free?** No per la parte semantica (richiede LLM); **degrada senza errore** se assente.
- **Testing**: `pytest` su wiki sandbox; LLM **scriptato** (JSON deterministico); **`FakeGit`** (porta
  git fake deterministica) per l'incrementale; nessuna rete/cloud/repo reale nei test.

## Constitution Check (gate) — rivalutato col nuovo scope

| Principio | Esito | Nota (nuovo scope) |
|-----------|-------|--------------------|
| I — dipendenze verso il dominio | ✅ | git dietro **`GitPort`** (no `subprocess` nel dominio); gate fuori dal core (CLI/hook). |
| II — provider dietro confine, local-first | ✅ | LLM/git dietro porte; funziona con Ollama + git locale. |
| III — YAGNI/DRY | ✅ | incrementale = **wrapper** su `semantic_lint(pages=)`; mappa entità↔pagine **derivata** (no stato duplicato). |
| IV — errori espliciti | ✅ | fallback baseline e fallback working-tree **segnalati** in `report.fallbacks`; no troncamento/stantio silenzioso (REQ-091/097). |
| V — testabilità + misura | ✅ | LLM scriptato + `FakeGit`; report con `mode` e copertura misurata. |
| VI — idempotenza/non-distruttività | ✅ | scrittura **solo** su generated, **diff chirurgico** revisionabile; watermark non distruttivo; rilevazione sola lettura. |
| VII — leggibilità | ✅ | entità tipizzate, funzioni piccole, una responsabilità per funzione. |
| VIII — config centralizzata | ✅ | soglia, k, tetto pagine, **override**, watermark path da parametri/`Settings`. |
| IX — osservabilità | ✅ | log strutturati: `mode`, `fallbacks`, `llm_calls`, pagine selezionate, esito gate/override. |

**Esito: 9/9 ✅** — nessuna violazione. **Dipendenza dichiarata**: il re-index incrementale *reale*
(REQ-096) richiede **FEAT-009 non ancora costruita** → in questo ciclo vale **solo il fallback working
tree** (REQ-097), segnalato (decisione R12 in `research.md`).

## Architettura

```
DOMINIO (src/sertor_core/)
  domain/ports.py
    + GitPort (Protocol): changed_paths(scope) · head_commit() · renamed_paths() (opz.)
  wiki/semantic.py  (esistente, esteso)
    semantic_lint(...)                         # P1 (invariato) — accetta già pages=
    propose_fixes(report, root, llm)           # P1 (invariato) — proposta
    + semantic_lint_incremental(root, llm, facade, git, *, watermark_path, threshold, k_code, max_pages)
                                               # US3: selezione pagine via EntityPageMap + watermark + fallback
    + apply_fixes(proposals, root, *, dry_run=False) -> list[FixApplication]
                                               # US4-scrittura: solo generated, chirurgico, delete; rifiuta curated
    + _entity_page_map(root) -> EntityPageMap  # derivata da sources:/wikilink (REQ-090)
  wiki/conventions.py  (esteso)
    + read_watermark(root) -> str|None · write_watermark(root, sha)   # FR-018, .sertor/semantic-watermark

ADAPTER (fuori dal dominio)
  adapters/git/subprocess_git.py
    + SubprocessGitAdapter(GitPort)            # implementazione reale via subprocess

CONFINE (CLI/services) — il GATE vive qui, non nel core
  run_semantic_gate(root, llm, facade, git, *, threshold, override) -> GateOutcome
    incrementale → apply_fixes (generated) → valuta report.ok vs soglia
    → exit≠0 se blocked · warning sotto soglia · override esplicito registrato (REQ-094/095)
  (esposizione CLI: `sertor wiki semantic-gate`, trigger a monte del configuration-manager — REQ-092)
```

### Decisioni di design (estendono R1–R7 del P1; dettaglio in `research.md`)
- **R8 — `GitPort` nel dominio, adapter fuori** (Principio I, finding C1). Test con `FakeGit`.
- **R9 — `EntityPageMap` derivata** da `sources:`/wikilink, non persistita (Principio III, REQ-090).
- **R10 — Watermark** = `wiki/.sertor/semantic-watermark` (commit SHA), non distruttivo; `.sertor/` esclusa
  dalla scoperta pagine (FR-018, finding U2).
- **R11 — Incrementale = wrapper** su `semantic_lint(pages=...)`; `SemanticReport` esteso con
  `mode` (`baseline|incremental`) e `fallbacks: list[str]`.
- **R12 — Re-index reale rinviato a FEAT-009**; ora **solo fallback working tree** segnalato (REQ-096/097).
- **R13 — `apply_fixes` chirurgico**, solo generated, `delete_page`, `dry_run`, preserva `generated`
  (REQ-078/079/080/085); claim non trovata → `FixApplication(skipped)` (non errore).
- **R14 — Gate fuori dal dominio** (CLI/hook): `report.ok`→exit≠0, warning sotto soglia, override
  tracciato (finding A1/C1, REQ-092..095).

## Fasi
- **Fase P1 (già implementata, invariata)**: entità + `semantic_lint` (baseline) + provenienza +
  `propose_fixes` (proposta) + degrado + soglia/gate-report.
- **Fase P2 (questo ciclo — in implementazione)**:
  1. **`GitPort` + `SubprocessGitAdapter`** (porta + adapter) — US3 infrastruttura.
  2. **Watermark** (`read/write_watermark`, `.sertor/` esclusa) — US3.
  3. **`_entity_page_map` + `semantic_lint_incremental`** (baseline/incrementale/fallback/no-op, report
     esteso `mode`/`fallbacks`) — US3, fallback working tree (FEAT-009 assente).
  4. **`apply_fixes`** (scrittura chirurgica + delete, solo generated, dry_run) — US4-scrittura.
  5. **`run_semantic_gate` + esposizione CLI** (`sertor wiki semantic-gate`): orchestrazione, exit code,
     override tracciato — US5. Gate **fuori** dal dominio.
- **Fuori ambito**: re-index incrementale *reale* del corpus (FEAT-009), full re-index, installazione
  fisica dell'hook git nel repo dell'utente finale (cura della CLI/setup governance).

## Scope MVP vs successivo
Vedi `spec.md` §"Scope dell'implementazione". Re-index reale e wiring hook git = passi successivi
(FEAT-009 / setup governance). Tutto il resto di US3/US4-scrittura/US5 è in questo ciclo.
