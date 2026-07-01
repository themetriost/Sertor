# Contratto — Integrazione nel workspace `uv`

**Feature**: speclift FEAT-001 (self-host) · **Branch**: `084-speclift-self-host`

Definisce lo stato atteso del workspace dopo il vendoring. Non è un'API: è il **contratto di
non-regressione e non-ciclo** verificabile da comandi deterministici.

## Membri del workspace (dopo)

```toml
# pyproject.toml (root = sertor-core)
[tool.uv.workspace]
members = ["packages/sertor", "packages/sertor-install-kit", "packages/sertor-flow", "packages/speclift"]
```

- `packages/speclift` è aggiunto. **Nessun** `[tool.uv.sources]` per speclift (non dipende da alcun
  membro workspace).
- Grafo di dipendenza dei membri (dopo): `sertor → {sertor-core, sertor-install-kit}`,
  `sertor-flow → sertor-install-kit`, `sertor-install-kit → ∅`, `sertor-core → ∅`, **`speclift → ∅`**.
  → **nessun ciclo** (FR-013/REQ-016, CS-5).

## Invarianti verificabili (deterministici)

| # | Invariante | Comando di verifica | Riferimento |
|---|-----------|---------------------|-------------|
| I1 | `uv sync --all-packages` risolve senza errori | `uv sync --all-packages --extra dev` | CS-5 |
| I2 | `sertor-core` byte-identico | `git diff -- pyproject.toml src/sertor_core` = vuoto | CS-3, FR-012 |
| I3 | Zero import del core in speclift | `grep -rn "import sertor_core\|from sertor_core" packages/speclift/src` = 0 (fuori dai commenti dichiarativi) | CS-3, FR-012 |
| I4 | Suite speclift verde | `uv run pytest packages/speclift/tests -m "not cloud"` | CS-4, FR-011 |
| I5 | Suite speclift verde su 3.11 | `uv run --python 3.11 pytest packages/speclift/tests -m "not cloud"` | FR-018 |
| I6 | Le altre suite invariate | step CI `Tests — sertor / -install-kit / -flow` verdi | RNF-3 |
| I7 | Lint di root verde | `uv run ruff check .` (speclift escluso) | D-5 |
| I8 | Provenienza presente | `packages/speclift/VENDORING.md` esiste, cita repo/commit/versione | FR-002, CS-7 |
| I9 | Skill depositata e host-agnostica | `.claude/skills/speclift/SKILL.md` esiste, no path-assistente/slash/nome-modello | FR-009/010 |

## Configurazione per-pacchetto (contratto anti-conflitto)

`packages/speclift/pyproject.toml` DICHIARA il **proprio**:

```toml
[tool.ruff]
src = ["src", "tests"]
line-length = 110
target-version = "py311"       # riconciliato da py312 (D-4)
[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
markers = [
    "contract: contract tests against JSON schemas / port contracts",
    "integration: end-to-end tests on real git fixtures",
]
```

E il ruff di **root** aggiunge `packages/speclift` all'`extend-exclude` (accanto a `prototype`), così
`ruff check .` non impone lo stile Sertor (100/no-`SIM`) sul vendorato. Il pytest di root resta
`testpaths = ["tests"]` (non colleziona speclift → nessun warning di marker).

## CI (dopo)

Nuovo step nel job `test` (dopo `Tests — sertor-flow`):

```yaml
- name: Tests — speclift (vendored self-host)
  run: uv run pytest packages/speclift/tests -m "not cloud"
```

(Opzionale, tasks) step `Lint — speclift`: `uv run ruff check packages/speclift`.

## Fuori dal contratto

- Il **test di packaging distribuibile** (`tests/integration/test_packaging.py`) **non** include
  speclift: è dogfood-only, non distribuito (distribuzione = **FEAT-002**). Versione statica `0.1.0`.
- Nessuna guardia di sync bundlato↔dogfood per la skill (territorio FEAT-002).
