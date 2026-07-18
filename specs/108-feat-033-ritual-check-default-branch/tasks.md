# Tasks: `ritual-check` rileva il default branch

**Branch**: `108-feat-033-ritual-check-default-branch` · **Plan**: `./plan.md`

## T001 — Rilevamento del default + `_resolve_base` riscritta
`src/sertor_core/wiki_tools/ritual_check.py`. Nuovo helper `_default_base_candidates(config_dir) -> list[str]`
(origin/HEAD via `symbolic-ref --short` → poi ref esistenti `origin/main`/`origin/master`/`main`/`master`,
dedup). `_resolve_base`: `--base` invariato → itera i candidati, ritorna il **primo** con merge-base →
altrimenti `ConfigError` fail-loud (messaggio che nomina i ref tentati). **Copre:** FR-001..007.

## T002 [P] — Test
`tests/unit/test_ritual_check.py`. Costruisci repo tmp con default **`main`** → base risolta senza `--base`
(SC-001/005); repo **`master`** → invariato (SC-002); **`--base`** esplicito onorato (SC-003); repo senza
default/merge-base → fail-loud, 0 candidati (SC-004). Verifica/adegua i test esistenti che assumono `master`.

## T003 — Verifica finale (gate)
`uv run pytest -m "not cloud"` verde + `uv run ruff check .` pulito. Conferma SC-006 (contratto invariato).
Smoke reale: `ritual-check` sul dogfood (default `master`) invariato.

## Dipendenze
T001 → (T002 [P]) → T003.
