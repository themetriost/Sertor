# Tasks — Distribuzione della memoria via installer (FEAT-009)

**Branch**: `071-distribuzione-memoria-installer` · Ordinati per dipendenze. `[P]` = parallelizzabile.

## Fase 1 — Asset (fondamenta)
- **T001 [P]** Nuovo asset `assets/rag/hooks/memory-capture.ps1` = byte-copy di
  `.claude/hooks/memory-capture.ps1` (corpo invariato). *(FR-010/015)*
- **T002 [P]** Nuovo asset `assets/rag/settings.memory-capture.json` = frammento Claude `SessionEnd` che
  invoca `.claude/hooks/memory-capture.ps1` (shape gemella di `settings.hooks.json`). *(FR-012)*
- **T003 [P]** `assets/rag/env.local.tmpl`: sezione «Conversation memory» con le 8 manopole,
  `SERTOR_MEMORY` off/commentata, commenti d'uso/privacy. *(FR-001/002/003/004)*
- **T004 [P]** `assets/rag/env.azure.tmpl`: stessa sezione memoria. *(FR-002)*
- **T005 [P]** `assets/rag/claude-md-block-rag-usage.md`: sezione «Conversation memory (optional)» coi
  comandi `sertor-rag memory` + condizione `SERTOR_MEMORY=true`. *(FR-020/021)*

## Fase 2 — Plan-builder (`install_rag.py`)
- **T010** Costanti memoria (`_MEMORY_HOOK_ASSET/_TARGET/_TARGET_COPILOT`, `_MEMORY_CAPTURE_SETTINGS`,
  `_COPILOT_MEMORY_WIRING_SENTINEL`) + `_copilot_memory_hook_specs()`.
- **T011** `build_rag_plan`: appende FILE(memory hook) + SETTINGS_MERGE(wiring) per-assistente dopo le
  eval-skill. *(FR-010/012/014)*
- **T012** `_rag_hook_fragment(art)`: ramo `_COPILOT_MEMORY_WIRING_SENTINEL`. *(FR-014)*
- **T013** Uninstall SETTINGS_MERGE → `_rag_hook_fragment(art)` (art-aware); rimuovi
  `_rag_settings_fragment`. *(FR-040)*
- **T014** `sertor_owned_paths`: aggiungi il memory hook target a `owned_files`. *(FR-042)*

## Fase 3 — Test
- **T020** Aggiorna `tests/test_install_rag_usage.py::test_plan_contains_rag_usage_artifacts` (≥1
  SETTINGS_MERGE; rag-usage presente).
- **T021 [P]** Nuovo `tests/test_install_rag_memory.py`: plan (Claude+Copilot), deposito hook, wiring
  `SessionEnd` dedup (preserva utente, coesiste con rag-usage), idempotenza, uninstall, copilot generato,
  cenno md, privacy off. *(FR-010..043)*
- **T022 [P]** Nuovo `tests/unit/test_env_template_memory.py`: i due template contengono le 8 chiavi con
  `SERTOR_MEMORY` off (anti-drift R-4). *(FR-001/002/003)*

## Fase 4 — Verifica & chiusura
- **T030** `uv run pytest packages/sertor` (+ kit) — suite verde; `uv run ruff check .`.
- **T031** Non-regressione: `plan ⊆ owned` (`tests/unit/test_owned_paths.py`) verde; schema copilot
  (`test_schema_copilot_hooks.py`) verde.
- **T032** Rituale di step: record wiki + roadmap + commit (delegati) + re-index/smoke a chiusura.

## Criteri di test indipendenti
- Ogni FR ha ≥1 asserzione (mappatura in `spec.md` §Requirements).
- Tutto offline (runner mock), nessuna rete (RNF-5).
