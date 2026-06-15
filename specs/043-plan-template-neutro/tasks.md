# Tasks: Plan-template neutro nel bundle (Gruppo D, Principio XI)

**Feature**: 043-plan-template-neutro · **Branch**: `043-plan-template-neutro`
**Input**: [plan.md](plan.md) · [spec.md](spec.md). Constitution PASS 11/11.

## Tasks
- [x] T001 Bundle asset `packages/sertor-flow/.../assets/specify/templates/plan-template.md` ← copia
  byte-esatta dell'upstream generico (placeholder `[Gates determined based on constitution file]`).
- [x] T002 Kit `sync_subtree` += parametro `exclude: tuple[str, ...]` (backward-compatible; salta i
  rel_path elencati).
- [x] T003 `sertor_flow/sync.py`: `_SUBTREE_EXCLUDE` → il subtree `templates` esclude
  `plan-template.md` dal sync/confronto.
- [x] T004 Guard test `test_assets_sync.py`: escluso `plan-template.md` dal confronto; nuovi test
  `test_plan_template_is_neutral_not_sertor_gated` e `test_plan_template_excluded_from_sync`.
- [x] T005 Gate: kit 37 · sertor-flow 107 verdi; ruff pulito.

## Note
- Il dogfood `.specify/templates/plan-template.md` di Sertor resta gated (invariato).
- Generazione dinamica dei gate dalla costituzione ospite (oltre il placeholder) = fuori ambito.
