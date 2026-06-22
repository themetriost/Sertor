# Implementation Plan — Ricerca semantica opzionale sull'archivio (FEAT-004)

**Branch**: `072-ricerca-semantica-memoria` · **Data**: 2026-06-22 · **Epica**: memoria-conversazioni
**Spec**: [`spec.md`](spec.md) · **Requisiti**: `requirements/memoria-conversazioni/ricerca-semantica/requirements.md`

## Summary

Aggiunge alla memoria conversazioni un **percorso semantico opt-in** che ritrova le sessioni passate
**per significato** (non per parola), affiancando — senza sostituire — la full-text FEAT-002. È una
capacità **additiva** sopra una pipeline provata: riusa **solo le primitive** del core (`build_embedder`,
`build_store`, `collection_name`), **non** introduce un nuovo motore (DA-SS-1 = store dedicato), e a
leva spenta ha costo/comportamento identici a oggi (gate `build_*` → `None`). Granularità = **turno**;
incrementalità **append-only-aware via stato del vector store** (watermark = id stabili già nello store);
trigger **automatico a fine sessione**; superficie = `memory search --semantic` (+ `memory
index-semantic` per il backfill); opt-in ulteriore distinto `SERTOR_MEMORY_SEMANTIC` (default off);
on-machine col provider locale di default.

## Technical Context

- **Linguaggio:** Python ≥ 3.11. **Build/test:** `uv`, `pytest` (marker `not cloud`), `ruff`.
- **Riuso (no nuove dipendenze, RNF-3/NFR-006):** `EmbeddingProvider`/`VectorStore` (porte esistenti),
  `build_embedder`/`build_store`/`collection_name` (composition), `EmbeddedChunk`/`RetrievalResult`
  (entità), `MemoryArchive`/`MemoryArchiveService` (FEAT-001), `Settings`/`log_event`. SQLite/Chroma
  già presenti; **nessuna nuova dipendenza di terze parti**.
- **Determinismo/local-first:** provider locale di default (`glove`/`hash`, FEAT-011) → index+query
  offline. Nessun LLM nel percorso oltre l'embedder.
- **Accesso via vehicle (Principio XI):** la capacità si esercita via CLI `sertor-rag memory` /
  (futuro) MCP; mai importando `sertor_core` a runtime fuori dai test.
- **Ignoti residui:** nessun `NEEDS CLARIFICATION` — le forche DA-SS-2..5 sono risolte in `research.md`;
  NFR-003 fissata (< 1 s p95, archivio tipico, provider locale).

## Constitution Check — PRE-design

| # | Principio | Esito | Motivo |
|---|-----------|-------|--------|
| I | Core dipendenze verso l'interno | **PASS** | servizio nuovo in `services/`, dipende dalle porte; scelte concrete solo in `composition`; nessun SDK nel dominio |
| II | Provider/backend dietro boundary; local-first | **PASS** | riusa `build_embedder`/`build_store` (provider/store guidati da config); default locale, offline |
| III | YAGNI, unità piccole | **PASS** | NO nuova porta (single backend, come `MemoryArchive`/`EmbeddingCache`); NO chunking sub-turno; NO manifest separato (store = watermark) |
| IV | Errori espliciti, niente null silenzioso | **PASS** | `SemanticMemoryUnavailableError` azionabile; core non-fatale con warning espliciti; no fallback silenzioso (REQ-015) |
| V | Testabilità e misura | **PASS** | componente isolato con embedder/store mock (RNF-5/7); NFR-003 misurabile; SC-001 verificabile (semantica trova dove full-text no) |
| VI | Idempotenza/determinismo/non-distruttività | **PASS** | `chunk_id` stabili → `upsert` idempotente (REQ-006); indice derivato e ricostruibile (REQ-029); install≠run |
| VII | Leggibilità | **PASS** | vocabolario di dominio (embed/index/search); funzioni piccole, guard clause come `EpisodicSearch` |
| VIII | Config centralizzata | **PASS** | `memory_semantic_enabled`/`_limit` solo in `Settings`; provider = `SERTOR_EMBED_PROVIDER` esistente |
| IX | Osservabilità | **PASS** | eventi `memory_semantic_index`/`_search` metrics-only, query hashata (REQ-026/027) |
| X | Host-agnostico | **PASS** | opera su `memory.sqlite`, mai branch sull'assistente (REQ-024/025) |
| XI | Consumo via vehicles | **PASS** | esercitata via CLI `memory`; auto-index dentro `memory archive` (vehicle); MCP = FEAT-010 |
| XII | Fail loud, fix the cause | **PASS** | degradazione **segnalata** (warning su index/provider assenti); no soppressione silenziosa; cloud off-machine reso esplicito |
| — | **Allineamento alla missione** | **PASS** | serve la qualità del contesto reso all'agente nel tempo (auto-conoscenza portabile, on-machine); **riusa il motore di retrieval del core** invece di derivare su concern periferici |

**Esito PRE: PASS 12/12 + missione PASS.** Nessuna deroga.

## Project Structure (artefatti nuovi/toccati)

```
src/sertor_core/
  services/memory_semantic.py        # NUOVO: SemanticMemoryQuery/Hit/Results, SemanticIndexReport,
                                      #        MemorySemanticIndex (index_session/index_all/search)
  services/memory_archive.py         # TOCCATO: archive_all accetta MemorySemanticIndex | None (auto-index)
  config/settings.py                 # TOCCATO: memory_semantic_enabled, memory_semantic_limit (+ load)
  composition.py                     # TOCCATO: build_memory_semantic_index() gated → None; iniezione in
                                      #          build_memory_archiver
  domain/errors.py                   # TOCCATO: SemanticMemoryUnavailableError
  cli/__main__.py                    # TOCCATO: memory search --semantic; nuovo memory index-semantic
  cli/output.py                      # TOCCATO: format_semantic_results / format_semantic_index_report
tests/unit/test_memory_semantic.py   # NUOVO: search/index/incrementalità/non-fatale/isolamento (mock)
tests/unit/test_cli_memory*.py       # TOCCATO: --semantic routing, gate→errore, backfill
specs/072-ricerca-semantica-memoria/ # spec, research, data-model, contracts, quickstart, plan, tasks
```

`sertor-core` **invariato** fuori dai punti elencati (porte/engine/adapter esistenti intatti).

## Phase 0 — Research

Vedi [`research.md`](research.md). Decisioni: **DA-SS-2** turno (no chunking sub-turno; NFR-003 < 1 s
p95) · **DA-SS-3** `memory search --semantic` + `memory index-semantic` · **DA-SS-4** watermark =
stato dello store (Opzione 3; rebuild REQ-032 implicito via `collection_name`) · **DA-SS-5**
`SERTOR_MEMORY_SEMANTIC` (+ `_LIMIT`).

## Phase 1 — Design

- [`data-model.md`](data-model.md): entità additive, identità `session_key#turn_index`, collezione
  isolata, manopole, errore di dominio, componente `MemorySemanticIndex` (no porta).
- [`contracts/memory-semantic.md`](contracts/memory-semantic.md): contratto `memory.semantic/1`
  (servizio + vehicle CLI + invarianti).
- [`quickstart.md`](quickstart.md): percorso opt-in, indicizzazione, ricerca, privacy/rebuild.

## Phase 2 — Implementazione (ordine, per `/speckit-tasks`)

1. **Settings** — 2 campi + `load` (`SERTOR_MEMORY_SEMANTIC`, `SERTOR_MEMORY_SEMANTIC_LIMIT`).
2. **Errore di dominio** — `SemanticMemoryUnavailableError` (azionabile, nomina le manopole + backfill).
3. **Servizio** `services/memory_semantic.py` — entità + `MemorySemanticIndex` (embed query → store.query
   → filtro temporale → limit; index_session con skip-by-id; index_all backfill; eventi metrics-only;
   degradazione non-fatale).
4. **Composition** — `build_memory_semantic_index()` gated su `memory_enabled AND
   memory_semantic_enabled` → `None`; iniezione opzionale in `build_memory_archiver` (auto-index).
5. **Aggancio auto-index** — `MemoryArchiveService.archive_all` chiama `index_session` non-fatale.
6. **CLI** — `memory search --semantic` (routing + gate→errore); `memory index-semantic` (backfill);
   resa umana + JSON in `cli/output.py`.
7. **Test** — unit componente (mock) + CLI; offline, `not cloud`.

## Consumatori / punti toccati (enumerati)

1. `config/settings.py` — 2 campi + 2 letture env in `load()`.
2. `domain/errors.py` — 1 nuovo errore.
3. `services/memory_semantic.py` — **nuovo** (entità + componente).
4. `services/memory_archive.py` — firma `archive_all` / `__init__` per ricevere l'indice semantico.
5. `composition.py` — nuova factory `build_memory_semantic_index` + iniezione in `build_memory_archiver`.
6. `cli/__main__.py` — flag `--semantic` su `memory search` + handler; nuovo sub `memory index-semantic`.
7. `cli/output.py` — 2 funzioni di resa (semantic results + index report).
8. `tests/unit/` — nuovo test componente + estensioni ai test CLI memoria.
9. **Debito di completamento (NON in questa feature, promosso):** distribuzione installer manopole/asset
   → **FEAT-009** (DA-SS-6); parità MCP `--semantic` → **FEAT-010**. Entrambi già nel backlog d'epica.

## Constitution Check — POST-design

Rivalutato dopo Phase 1: nessun nuovo accoppiamento introdotto. La factory gated preserva
l'additività (I/III/RNF-005); il watermark-via-store evita stato duplicato (III/VI); l'errore
azionabile preserva IV/XII; gli eventi restano metrics-only (IX); il riuso delle sole primitive
preserva la missione (no nuovo motore — SC-008). Isolamento della collezione verificato dal namespacing
(REQ-017/SC-009).

**Esito POST: PASS 12/12 + missione PASS.** Nessuna deroga, nessun Complexity Tracking necessario.

## Note di processo

- `setup-plan.ps1` e `.claude/skills/speckit-plan/SKILL.md` **ASSENTI** nel repo → parametri ricavati
  per convenzione dal branch (forma da `071`/`070`). Nessun hook eseguito; nessun comando git.
- MCP `sertor-rag` interrogato per l'ancoraggio (`search_code`, `find_symbol`): **nessun errore tool**.
- Riferimento al piano aggiornato in `CLAUDE.md` tra i marker `<!-- SPECKIT START/END -->`.
