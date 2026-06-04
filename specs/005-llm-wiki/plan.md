# Implementation Plan: LLM Wiki end-to-end (FEAT-010)

**Branch**: `spec/005-llm-wiki` | **Spec**: `specs/005-llm-wiki/spec.md`
**Requisito**: `requirements/sertor-core/llm-wiki/requirements.md` (D-1..D-17, FR-001..042)
**Date**: 2026-06-04

## Technical Context

- **Linguaggio**: Python ≥ 3.11. **Pacchetto**: estende `src/sertor_core/` (riusa FEAT-001 nucleo,
  FEAT-002 baseline, FEAT-003 wiki). **CLI**: `src/sertor_cli/`. **MCP**: `src/sertor_mcp/`.
- **Riuso (Principio III)**: `wiki.structure.create_wiki`, `wiki.operations.record`, `wiki.distill`,
  `wiki.indexing.index_wiki`, `wiki.conventions`, `composition.build_llm/build_facade`, `IndexingService`.
- **Dipendenze**: LLM via porta `LLMProvider`; codice/changeset via **nuova porta `GitPort`** (adapter
  subprocess fuori dal dominio); retrieval via facade. Re-index incrementale = **dipendenza FEAT-009**
  (fallback se assente).
- **Testing**: `pytest` su wiki sandbox; **LLM scriptato** + **FakeGit** deterministici; nessuna
  rete/cloud nei test.

## Constitution Check (gate)

| Principio | Esito | Nota |
|-----------|-------|------|
| I — dipendenze verso il dominio | ✅ | git dietro **`GitPort`**; generazione = **servizio distinto**; **gate fuori dal dominio** (CLI/hook). Il config-manager **invoca**, non assorbe. |
| II — provider dietro confine, local-first | ✅ | LLM/git dietro porte; funziona con Ollama + git locale; vale anche senza codice. |
| III — YAGNI/DRY | ✅ | riusa create_wiki/record/distill/index_wiki/conventions e il nucleo; nessuna logica duplicata. |
| IV — errori espliciti | ✅ | human-in-the-loop sui conflitti `manual_edited`; fallback **async** (commit follow-up) e fallback **re-index** segnalati; degrado senza LLM. |
| V — testabilità + misura | ✅ | LLM scriptato + FakeGit; report manutenzione misurato; idempotenza verificabile. |
| VI — idempotenza/non-distruttività | ✅ | `manual_edited/` **mai** modificato; idempotenza strutturale (id=path); gate **revisionabile** (no auto-fix silenzioso). |
| VII — leggibilità/SRP | ✅ | generazione, manutenzione, gate, adapter git = moduli separati a singola responsabilità. |
| VIII — config centralizzata | ✅ | `Settings`: insieme fonti-input, soglia gate, gerarchia di autorità, path aree, nomi collezioni. |
| IX — osservabilità | ✅ | log strutturati: changeset, pagine generate/verificate, esito gate/override, fallback. |

**Esito: 9/9 ✅.** Dipendenza dichiarata: re-index incrementale reale = **FEAT-009** (fallback finché assente).

## Architettura

```
DOMINIO (src/sertor_core/)
  domain/ports.py
    + GitPort (Protocol): changed_paths(scope) · head_commit() · renamed_paths()
  wiki/conventions.py (esteso)
    + aree manual_edited/ , ingested_sources/ ; provenance; watermark/stato; entity↔page map helper
  wiki/generation.py (NUOVO)                      # momento (a)
    generate(root, llm, *, sources, git=None, scope, ...) -> GenerationReport
      legge fonti-input configurabili → compila concetti/sintesi (LLM) → scrive pagine generate
      incrementale: changeset (GitPort) → entità→pagine → solo pagine collegate
  wiki/ingest_sources.py (NUOVO o esteso da operations) # ingest -> ingested_sources/ (import, no compile)
  wiki/maintenance.py (NUOVO)                     # lint strutturale + verifica di freschezza (LLM)
    lint(root) -> LintReport ; freshness(root, llm, facade, git) -> FreshnessReport
  wiki/indexing.py (esteso)                       # collezioni SEPARATE: solo wiki generato (no input)

ADAPTER (fuori dal dominio)
  adapters/git/subprocess_git.py  : SubprocessGitAdapter(GitPort)

CONFINE (services/CLI/MCP) — orchestrazione e gate
  services/wiki_gate.py : run_commit_gate(...) -> GateOutcome   # blocca/avvisa/propone/override
  services/wiki_setup.py : init_wiki(...)                       # struttura + binding trigger + ingest iniziale
  sertor_cli: `sertor wiki init|generate|ingest|lint|gate|index`  (+ search esistente per query)
  sertor_mcp: tool wiki (ingest/generate/lint/query)
  BINDING TRIGGER: il configuration-manager (o equivalente del client) chiama il gate/generazione al commit
```

### Decisioni di design (research.md per il dettaglio)
- **R1 — `GitPort` + adapter** (Principio I): changeset del commit dietro porta; test con FakeGit.
- **R2 — Generazione = servizio distinto** invocato dal versioning (SRP): il config-manager non genera.
- **R3 — Due momenti**: generazione (a) scrive pagine; retrieval (b) indicizza **solo** wiki generato +
  codice in **collezioni separate** (refresh indipendente; input non indicizzati).
- **R4 — Mappa entità→pagine derivata** da frontmatter `sources:`/wikilink (no indice persistito) → scope
  incrementale.
- **R5 — `manual_edited/` immutabile + compilato**; `ingested_sources/` input non versionato popolato
  dall'ingest (import ≠ compile).
- **R6 — Verità stratificata** + gerarchia (default+configurabile); conflitti `manual_edited` =
  human-in-the-loop.
- **R7 — Manutenzione**: lint strutturale (LLM-free) + freschezza (LLM, vs codice/decisione); trigger
  incrementale@commit/on-demand/periodico.
- **R8 — Gate al commit fuori dal dominio**: il core produce report; il gate (blocco/avviso/proposte/
  override tracciato) vive nel confine; trigger contract portabile, config-manager = binding.
- **R9 — Setup `sertor wiki init`**: struttura + **installa il binding** del trigger + ingest iniziale.
- **R10 — Re-index incrementale = FEAT-009** (fallback working-tree/rigenerazione più ampia se assente).

## Fasi
- **Fase 1 — Foundational**: `GitPort` + adapter + FakeGit; estensioni `conventions` (aree
  manual_edited/ingested_sources, provenance, stato/watermark, entity↔page map); `Settings` (fonti-input,
  soglia, gerarchia, collezioni).
- **Fase 2 — Generazione (US2, Must)**: `generation.py` (baseline full + incrementale sul changeset).
- **Fase 3 — Retrieval (US4, Must)**: indicizzazione **collezioni separate** (wiki generato), query
  congiunta via facade; input esclusi.
- **Fase 4 — Setup (US1, Must)**: `wiki_setup.init_wiki` + CLI `sertor wiki init`.
- **Fase 5 — Ingest (US3, Should)**: `ingest -> ingested_sources/` (import) + superfici.
- **Fase 6 — Manutenzione + Gate (US5, Should)**: lint + freschezza + `wiki_gate.run_commit_gate`.
- **Fase 7 — Superfici (US6, Should)**: CLI completa + tool MCP.
- **Fase 8 — No-code + polish (US7, Could)**: percorso senza codice; periodico; gerarchia configurabile.

## Scope MVP vs successivo
Vedi `spec.md` §Scope/MoSCoW. Re-index incrementale reale = FEAT-009; superficie wiki-nativa,
arricchimento bidirezionale, full re-index = fuori scope.
