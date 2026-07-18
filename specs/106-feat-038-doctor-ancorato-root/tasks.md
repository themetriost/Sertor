# Tasks: `doctor` ancorato alla radice del progetto

**Branch**: `106-feat-038-doctor-ancorato-root` · **Plan**: `./plan.md`

Ordine dipendenza-consapevole. `[P]` = parallelizzabile con il precedente.

## T001 — `Settings.project_root` (risoluzione + campo)
`src/sertor_core/config/settings.py`. In `Settings.load`, dopo `resolved_index_dir`, calcola
`resolved_project_root` con precedenza: `CLAUDE_PROJECT_DIR` (dir esistente) → `resolved_index_dir.parent.parent`
se `resolved_index_dir.parent.name == ".sertor"` → `None`. Aggiungi il campo `project_root: Path | None`
alla dataclass e passalo in `cls(...)`. **Copre:** FR-001, FR-004, FR-005, FR-008.

## T002 [P] — Unit test derivazione root
`tests/unit/test_settings_project_root.py`. Casi: (a) layout `.sertor/.index` (via `SERTOR_INDEX_DIR` o
`.env` in `.sertor/`) → root = parent di `.sertor/`, assoluta, **indipendente dal cwd** (monkeypatch chdir su
sottocartella); (b) `CLAUDE_PROJECT_DIR` impostato → vince; (c) nessun `.sertor/` → `None`; (d) guard
host-agnostico: la risoluzione non contiene path hardcodati (asserzione sul comportamento, non sulla stringa).
**Copre:** SC-001(parziale), SC-005, FR-001/005/008.

## T003 — Wiring `_cmd_doctor`
`src/sertor_core/cli/__main__.py:574`. `root = Path.cwd()` → `root = settings.project_root`; se `None`
solleva un errore fail-loud (exit non-zero, messaggio azionabile) **prima** di assemblare/stampare i
verdetti. Resto invariato (sola lettura preservata). **Copre:** FR-002, FR-003, FR-006, FR-007.

## T004 — Test invarianza cwd + fail-loud + sola-lettura
`tests/unit/test_doctor_cwd_invariance.py` (o estensione dei test doctor esistenti). Costruisci un progetto
fittizio (`tmp_path`) con `.sertor/.index` + manifest reale + sorgenti; verifica: (a) le stat/il verdetto
`index` e `mcp` sono **identici** eseguiti da root e da sottocartella (SC-001, SC-002); (b) fuori da un
progetto risolvibile → fail-loud, exit non-zero, nessun verdetto (SC-003); (c) `doctor` non scrive file
(SC-004). **Copre:** SC-001/002/003/004, FR-003/006/007.

## T005 — Verifica finale (gate pre-merge locale)
`uv run pytest -m "not cloud"` **verde** + `uv run ruff check .` **pulito** (gate VINCOLANTE). Conferma
SC-006 (nessuna regressione: schema report, exit-code, evento, caso-dalla-radice invariati). Poi smoke
reale: `doctor` dalla root e da `src/` → stesso verdetto.

## Dipendenze
T001 → (T002 [P], T003) → T004 → T005. T002 può girare appena T001 è scritto.
