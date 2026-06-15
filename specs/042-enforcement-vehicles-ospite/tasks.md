# Tasks: Enforcement lato ospite (Gruppi B+C, Principio XI)

**Feature**: 042-enforcement-vehicles-ospite · **Branch**: `042-enforcement-vehicles-ospite`
**Input**: [plan.md](plan.md) (D1-D4) · [spec.md](spec.md). Constitution PASS 11/11.

## Tasks
- [x] T001 [B] Asset `assets/rag/claude-md-block-rag-usage.md` (EN): istruzione d'uso (usa
  `sertor-rag`/MCP, non importare `sertor_core`).
- [x] T002 [B] `build_rag_plan` += `MARKER_BLOCK` → `CLAUDE.md`; `execute_rag_plan` ramo che usa
  `write_marker_block` del kit con marker distinti `SERTOR:RAG-USAGE`.
- [x] T003 [C] Asset hook `assets/rag/hooks/sertor-rag-usage-check.ps1` (PreToolUse): rileva
  `import/from sertor_core` fuori da test → warning non bloccante, exit 0 sempre, fail-open.
- [x] T004 [C] Asset `assets/rag/settings.rag-usage.json` (voce hook PreToolUse) + `build_rag_plan` +=
  `FILE`(hook) + `SETTINGS_MERGE`; `execute_rag_plan` rami FILE/SETTINGS_MERGE (riuso kit).
- [x] T005 Generalizzato `settings_merge` del kit per supportare eventi hook arbitrari (PreToolUse),
  dedup-by-command, retrocompatibile (37 test kit verdi).
- [x] T006 Test `test_install_rag_usage.py` (18): piano, marker distinti, idempotenza, coesistenza col
  blocco wiki, preservazione contenuto utente, hook create-if-absent, settings merge additivo, smoke
  hook (warn/test-exclusion/fail-open via pwsh). + aggiornati `test_install_rag.py`.
- [x] T007 Gate: `packages/sertor` 104 · kit 37 · sertor-flow 106 verdi; ruff pulito.
- [ ] T008 Post-merge: nessun re-index necessario (cambio installer, non tocca il corpus indicizzato).

## Note
- `block` (Could) fuori MVP (default warn/fail-open).
- FR-011 (installabilità): blocco RAG-USAGE cablato in `sertor install rag` (host-facing, viaggia con
  l'installer).
