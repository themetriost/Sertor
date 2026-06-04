# Implementation Plan: Lint semantico del wiki (FEAT-007 — estensione)

**Branch**: `spec/005-wiki-manutenzione` | **Spec**: `specs/006-wiki-lint-semantico/spec.md`
**Date**: 2026-06-04

## Technical Context

- **Linguaggio**: Python ≥ 3.11. **Pacchetto**: estende `src/sertor_core/wiki/`.
- **Dipendenze runtime**: solo core. LLM via porta `LLMProvider` (Ollama/Azure, `composition.build_llm`);
  contesto codice via facade di retrieval (`composition.build_facade`, corpus `production`). Git via
  `subprocess`/porta dedicata (solo per US3/US5, fase successiva).
- **LLM-free?** No per la parte semantica (richiede LLM); **degrada senza errore** se assente.
- **Testing**: `pytest` su wiki sandbox; LLM **scriptato** (mock che ritorna JSON deterministico);
  nessuna rete/cloud nei test.

## Constitution Check (gate)

| Principio | Esito | Nota |
|-----------|-------|------|
| I — dipendenze verso il dominio | ✅ | la logica vive in `wiki/`, usa le porte `LLMProvider`/retrieval; nessuna infra nel dominio. |
| II — provider dietro confine, local-first | ✅ | LLM dietro porta; funziona con **Ollama** locale, non solo Azure (NFR-10). |
| III — YAGNI/DRY | ✅ | riusa `maintenance._pages`, `conventions`, la facade; nessuna logica duplicata. |
| IV — errori espliciti | ✅ | degrado senza LLM = report `skipped` esplicito; errori di parsing JSON espliciti e isolati. |
| V — testabilità + misura | ✅ | LLM scriptato; report con copertura misurata (coperto/saltato). |
| VI — idempotenza/non-distruttività | ✅ | rilevazione **sola lettura**; proposte non scrivono; provenienza marcata solo sulle pagine generate. |
| VII — leggibilità | ✅ | entità tipizzate, funzioni piccole. |
| VIII — config centralizzata | ✅ | soglia severità, k contesto, tetto pagine da parametri/`Settings`. |
| IX — osservabilità | ✅ | log strutturati con conteggio chiamate LLM e copertura. |

**Esito: 9/9 ✅** — nessuna violazione.

## Architettura

Nuovo modulo `src/sertor_core/wiki/semantic.py` (rilevazione + report + proposte), che **affianca**
`maintenance.py` (strutturale). Estensioni a `conventions.py` per la **provenienza**. La facade di
retrieval fornisce il contesto codice (verità "codice"); l'LLM giudica per-claim.

```
semantic_lint(root, llm, facade, *, threshold, k_code, max_pages, pages=None) -> SemanticReport
   ├─ _pages(root)                        # riusa maintenance
   ├─ per pagina: contesto codice = facade.search_code(query) (REQ-075/096-fallback)
   ├─ llm.generate(prompt struttura JSON) # issue per-claim (REQ-071..074/098)
   ├─ parse → SemanticIssue[]             # robusto, errori isolati
   └─ SemanticReport(issues, threshold)   # ok pass/fail + copertura (REQ-082/083)

provenance:  read_provenance(text)->Provenance ; mark_provenance(text, value)->text   (REQ-076/077)
propose_fixes(report, root, llm) -> FixProposal[]   # solo pagine generated (REQ-078/080), proposta
```

### Decisioni di design
- **R1 — Granularità claim via un'unica chiamata per pagina** che ritorna issue per-frase (REQ-098):
  bilancia precisione e costo; il numero di chiamate = numero di pagine verificate (bound da `max_pages`).
- **R2 — Contesto codice dal retrieval** (corpus `production`); in modalità incrementale futura si
  leggerà il change set dalla working tree (REQ-096/097). Per il primo run = **baseline completo**.
- **R3 — Output LLM = JSON** parsato in modo difensivo (estrazione array, skip di voci malformate con
  log), così un LLM rumoroso non rompe il lint.
- **R4 — Provenienza nel frontmatter** (`provenance: generated|curated`), letta per regex; **default
  curated** se assente. `distill_artifact` marca `generated`.
- **R5 — Severità** ordinale {info < low < medium < high < critical}; soglia di default `high`.
- **R6 — Degrado**: `llm=None` → `SemanticReport(skipped=True, issues=[])` (nessun errore).
- **R7 — Idempotenza della rilevazione**: con LLM deterministico (temp 0 / scriptato) stesso input →
  stesse issue; il test usa un LLM scriptato (REQ-084).

## Fasi
- **Fase P1 (questo ciclo, completo + test)**: entità + `semantic_lint` (baseline) + provenienza +
  `propose_fixes` (proposta) + degrado + soglia/gate. Eseguibile sul wiki reale.
- **Fase P2 (successiva, dichiarata nei task)**: incrementale git-driven + watermark + mappa
  entità↔pagine (US3), applicazione su working tree + cancellazione (US4 scrittura), hook
  pre-commit/pre-push + override (US5), re-index incrementale (US3/FR-014, sinergia FEAT-009).

## Scope MVP vs successivo
Vedi `spec.md` §"Scope dell'implementazione". Il run sul wiki attuale usa la **Fase P1** in baseline.
