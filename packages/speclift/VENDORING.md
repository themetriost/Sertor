# Provenienza del vendoring — `packages/speclift`

| Campo | Valore |
|-------|--------|
| `upstream_repo` | https://github.com/themetriost/Sinthari |
| `upstream_commit` | `5ee6fc13350b615225ffb34619e1cb55e089b1fc` (`master`, PR #7 — "Merge pull request #7 from themetriost/feat/speclift-pluggable-locator") |
| `upstream_version` | `0.1.0` |
| `vendored_at` | 2026-07-01 |
| `handoff` | first-party, stessa organizzazione GitHub `themetriost`; `5ee6fc1` è il recepimento upstream del nostro feedback di dogfooding (CLI→MCP, Adapter B pluggable) |
| `upstream_license` | **ASSENTE** a `5ee6fc1` (nessun file `LICENSE*` nel repo Sinthari, verificato). **Titolarità confermata (2026-07-02):** `themetriost/Sinthari` e `themetriost/Sertor` hanno lo **stesso titolare legale** → l'MIT di questa copia (`LICENSE` in questa cartella) è un **atto legittimo del titolare** (first-party), non una rilicenza di codice di terzi. **Azione residua tracciata (A-02, audit SWOT):** committare una `LICENSE` MIT **a monte nel repo Sinthari** e ri-pinnare, così anche i vendoring futuri dallo stesso repo (es. SpecAudit, [[FEAT-003]]) ereditano la licenza alla sorgente invece di apporla a valle. Non bloccante per il dogfood; belt-and-suspenders legale. |

## Cosa è vendorato verbatim (zero modifiche di codice)

- `src/speclift/**` — dominio, **entrambi** gli adapter (`adapters/rag_sertor.py` Adapter A
  CLI-vehicle, dormiente nel self-host Sertor; `adapters/provided_locator.py` Adapter B,
  usato dal self-host), stadi, CLI, config, serializzazione.
- `tests/{contract,integration,unit}/**` — suite completa (122 test: 8 contract, 17
  integration, 97 unit), inclusi `test_provided_locator.py`(8)/`test_query_keys.py`(5)/
  `test_three_gear_flow.py`(3, Adapter B) e `test_rag_sertor.py`(8, Adapter A, runner mockato).
- `skills/speclift/SKILL.md` — la skill upstream (Procedura A/B); copiata anche in
  `.claude/skills/speclift/SKILL.md` per il dogfood (feature 084, US8).
- `specs/001-speclift-mvp/contracts/**` (`cli.md`, `ears-author-port.md`,
  `evidence-locator-port.md`, `evidence-bundle.schema.json`, `output.schema.json`) +
  `specs/001-speclift-mvp/quickstart.md` (citato dal `readme` del `pyproject.toml`).
- `README.md` — README del repo upstream, copiato verbatim per completezza di provenienza.

## Divergenze (SOLO di packaging — nessuna divergenza di codice `src/**`)

| # | Campo | Upstream | Vendorato | Motivo |
|---|-------|----------|-----------|--------|
| 1 | `[project.dependencies]` | `["jsonschema>=4.0"]` | `[]` | `jsonschema` è usata **solo** nei test di contratto (verificato: zero import in `src/`); runtime resta stdlib-only (D-2, RNF-2) |
| 2 | `[project.optional-dependencies].dev` | `["pytest>=8.0","ruff>=0.6"]` | `+= "jsonschema>=4.0"` | sposta la dipendenza da (1) qui |
| 3 | `requires-python` | `>=3.12` | `>=3.11` | riconciliazione col pavimento del workspace Sertor (D-4), **condizionata** alla verifica empirica su 3.11 (vedi `tasks.md` Fase 8/US10 — se irriducibile, questo campo E questa riga tornano a `>=3.12` con la discrepanza dichiarata sotto) |
| 4 | `[tool.ruff] target-version` | `py312` | `py311` | coerente col punto 3 |
| 5 | `LICENSE` | assente | MIT (Sertor) | D-7; titolarità comune confermata 2026-07-02 (riga `upstream_license` sopra) → atto del titolare, non rilicenza di terzi; azione residua A-02 = LICENSE a monte + re-pin |

Tutto il resto del `pyproject.toml` (nome, versione statica `0.1.0`, descrizione, `readme`,
`project.scripts`, `build-system`, `tool.hatch.build.targets.wheel`,
`tool.pytest.ini_options`, `tool.ruff` per il resto, `tool.ruff.lint.select` — l'upstream ha
**già** `SIM`/110 righe) resta **byte-identico** all'upstream.

## Esito verifica Python 3.11 (Fase 8/US10 di `tasks.md`)

Verificato **verde** su Python 3.11 il 2026-07-01 — `122 passed` (8 contract + 17 integration
+ 97 unit) con `uv run --python 3.11 pytest packages/speclift/tests -m "not cloud"`. Il pin
`requires-python = ">=3.11"` è quindi **confermato empiricamente**: nessun costrutto
genuinamente 3.12-only nel codice vendorato (`StrEnum` è 3.11+). Piano B non necessario.

## Aggiornare questa nota (invariante FR-003)

A ogni re-vendoring futuro: aggiorna `upstream_commit`/`upstream_version`/`vendored_at`,
ripeti il diff dei 5 punti sopra sul nuovo `pyproject.toml` upstream, e verifica che nessuna
nuova dipendenza runtime sia comparsa silenziosamente. Non lasciare questa nota stantia.
