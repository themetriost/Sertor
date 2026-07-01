# Contratto — Integrazione nel workspace `uv`

**Feature**: speclift FEAT-001 (self-host) · **Branch**: `084-speclift-self-host`

Definisce lo stato atteso del workspace dopo il **vendoring puro** da Sinthari `5ee6fc1`. Non è un'API:
è il **contratto di non-regressione e non-ciclo** verificabile da comandi deterministici.

> **Vendoring PURO.** Il codice `packages/speclift/src/**` è copiato **verbatim** dallo stato upstream
> `5ee6fc1` (versione pluggable con **entrambi** gli adapter). Le uniche divergenze sono di *packaging/
> integrazione* (elencate in `VENDORING.md`), **non** di codice runtime: nessun file di `src/` è
> modificato, `rag_sertor.py` **resta**, `config.py` **resta** verbatim (con `SERTOR_RAG_VEHICLE`).

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
| I2 | `sertor-core` byte-identico | `git diff -- pyproject.toml src/sertor_core` = solo le 2 righe di workspace/ruff | CS-3, FR-012 |
| I3 | Zero import del core in speclift | `grep -rn "import sertor_core\|from sertor_core" packages/speclift/src` = 0 (le occorrenze sono i **commenti** upstream «mai `import sertor_core`» in `config.py`/`rag_sertor.py`) | CS-3, FR-012 |
| I3b | **Nessuna invocazione della CLI `sertor-rag` nel flow del dogfood** | il flow B (`changeset` + `bundle --changeset --located`) non spawna `sertor-rag`; l'Adapter A `rag_sertor.py` è **vendorato ma dormiente** | FR-004/REQ-007 |
| I4 | Suite speclift verde | `uv run pytest packages/speclift/tests -m "not cloud"` (suite **completa** upstream, ~122 test) | CS-4, FR-011 |
| I5 | Suite speclift verde su 3.11 | `uv run --python 3.11 pytest packages/speclift/tests -m "not cloud"` | FR-019 |
| I6 | Le altre suite invariate | step CI `Tests — sertor / -install-kit / -flow` verdi | RNF-3 |
| I7 | Lint di root verde | `uv run ruff check .` (speclift escluso) | D-5 |
| I8 | Provenienza presente | `packages/speclift/VENDORING.md` esiste, cita repo/commit `5ee6fc1`/versione + le divergenze di packaging | FR-002, CS-7 |
| I9 | Skill depositata, host-agnostica (forma) | `.claude/skills/speclift/SKILL.md` esiste, no path-assistente/slash/nome-modello, contiene la Procedura B (localizzazione via tool MCP) | FR-007/008 |
| I10 | Fail-loud evidenza malformata | `speclift bundle --changeset c.json --located <malformato>` → exit **5** (non exit 6), nessun bundle prodotto | FR-010/REQ-013 |

## Configurazione per-pacchetto (contratto anti-conflitto)

`packages/speclift/pyproject.toml` diverge dall'upstream **solo** su versione Python e collocazione di
`jsonschema`; il resto è verbatim:

```toml
[project]
requires-python = ">=3.11"     # riconciliato da ">=3.12" (D-4)
dependencies = []              # jsonschema spostata in dev (D-2); runtime stdlib-only

[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.6", "jsonschema>=4.0"]   # jsonschema: test-only (D-2)

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
- Il **retrieval MCP** (`search_code`) è esercitato dall'**agente** nella skill, **non** dal codice
  testato: le suite girano **offline** (il fail-loud MCP/indice vive nella skill; nel codice l'evidenza
  malformata cade nell'exit 5 upstream). L'Adapter A `rag_sertor.py` è testato offline da
  `test_rag_sertor.py` con un runner mockato — resta verde senza rete.
