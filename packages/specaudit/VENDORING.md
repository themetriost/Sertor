# Provenienza del vendoring — `packages/specaudit`

| Campo | Valore |
|-------|--------|
| `upstream_repo` | https://github.com/themetriost/Sinthari |
| `upstream_commit` | `e1bbdb2` (`e1bbdb2cec34b17495a29c7aecfa7761f016469f`, `origin/master` — contiene SpecAudit MVP PR #8 `91c5a45` + validazione T048 PR #10) |
| `upstream_version` | `0.1.0` |
| `vendored_at` | 2026-07-02 |
| `handoff` | first-party, stessa organizzazione GitHub `themetriost`; gemello di `packages/speclift` (SpecAudit consuma l'output di SpecLift per il verdetto per-requisito) |
| `upstream_license` | **ORA PRESENTE upstream.** A `e1bbdb2` il repo Sinthari non ha ancora un file `LICENSE`, ma il commit locale più recente `3e800a0` (successivo al pin, non ancora su `origin/master` al momento del vendoring) **aggiunge una `LICENSE` MIT a monte** ed elabora la nostra risposta di dogfooding. La **titolarità comune** (`themetriost/Sinthari` e `themetriost/Sertor`, stesso titolare legale) è quindi **confermata alla sorgente**: l'MIT di questa copia (`LICENSE` in questa cartella) è un **atto legittimo del titolare** (first-party), non una rilicenza di codice di terzi. Rispetto al vendoring di SpecLift (dove la LICENSE upstream era ancora assente e l'azione A-02 restava aperta), qui l'azione residua è **chiusa a monte**. |

## Cosa è vendorato verbatim (zero modifiche di codice)

- `src/specaudit/**` — dominio (`domain/{models,errors,ports}.py`), adapter
  (`adapters/{adjudication_file,requirements_fs,speclift_json}.py`), stadi
  (`stages/{resolve_source,ingest_speclift,prepare,render,assemble}.py`), CLI, config,
  serializzazione, observability, pipeline. **Solo standard library** nel core: consuma un
  `*.speclift.json` + una fonte `requirements/`, **non** importa `speclift`, **non** legge
  codice/test/CI, **non** dipende dal RAG (moat strutturale).
- `tests/specaudit/{contract,integration,unit}/**` — suite completa (3 contract, 1 integration,
  8 unit file), con `helpers.py` e i `__init__.py` di package. La **nidificazione
  `tests/specaudit/`** è preservata: i test fanno `from tests.specaudit.helpers import …` e
  appiattirla romperebbe gli import.
- `skills/specaudit/SKILL.md` — la skill upstream; copiata anche in
  `.claude/skills/specaudit/SKILL.md` per il dogfood (gemella di `.claude/skills/speclift/`).
- `specs/002-specaudit-mvp/contracts/**` (`adjudication.schema.json`, `adjudicator-port.md`,
  `audit-bundle.schema.json`, `cli.md`, `output.schema.json`) + `specs/002-specaudit-mvp/quickstart.md`
  (citato dal `readme` del `pyproject.toml`; i contratti sono caricati dai contract test via
  `conftest.py` con `parents[3]/"specs"/"002-specaudit-mvp"/"contracts"`).

## Divergenze (SOLO di packaging — nessuna divergenza di codice `src/**`)

| # | Campo | Upstream (monorepo Sinthari) | Vendorato | Motivo |
|---|-------|------------------------------|-----------|--------|
| 1 | `requires-python` | `>=3.12` | `>=3.11` | riconciliazione col pavimento del workspace Sertor; `StrEnum` (`domain/models.py`) è 3.11+ — verifica empirica sotto |
| 2 | `[tool.ruff] target-version` | `py312` | `py311` | coerente col punto 1 |
| 3 | `pyproject.toml` | **unico** per il monorepo, con **due** package (`speclift`+`specaudit`) e **due** console-script | **dedicato** a `specaudit` (un solo package, un solo script `specaudit = "specaudit.cli:main"`) | scorporo dal monorepo Sinthari: qui SpecLift e SpecAudit sono **membri `uv` distinti** (`packages/speclift`, `packages/specaudit`) |
| 4 | `LICENSE` | presente a monte da `3e800a0` (assente al pin `e1bbdb2`) | MIT (Sertor) | titolarità comune confermata alla sorgente; copia coerente con l'atto del titolare |

Nota su `jsonschema`: nel monorepo upstream `jsonschema>=4.0` è dichiarata come dipendenza
runtime del progetto `speclift`; per `specaudit` è usata **solo** nei test di contratto
(`tests/specaudit/contract/conftest.py`), zero import in `src/specaudit/` (verificato). Nel
`pyproject.toml` scorporato di questo pacchetto vive quindi correttamente sotto
`[project.optional-dependencies].dev` e il runtime resta **stdlib-only**. `referencing` (usata dal
`conftest.py` insieme a `jsonschema`) arriva transitiva con `jsonschema>=4.18`.

Tutto il resto (nome `specaudit`, versione statica `0.1.0`, descrizione, `readme`,
`project.scripts`, `build-system` hatchling, `tool.hatch.build.targets.wheel`,
`tool.pytest.ini_options`, `tool.ruff`/`tool.ruff.lint.select` — l'upstream ha già `SIM`/110
righe) resta **byte-identico** all'upstream, salvo l'harness dei test descritto sotto.

## Harness dei test (config, non logica)

Il monorepo upstream ha `pythonpath = ["src"]` perché la sua `tests/` è a radice del repo e
`tests.specaudit` è già importabile dalla root. Qui il pacchetto è scorporato, quindi:
- `[tool.pytest.ini_options].pythonpath = ["src", "."]` — il `"."` mette la root del pacchetto
  (`packages/specaudit`) sul path, così `from tests.specaudit.helpers import …` risolve;
- aggiunto `tests/__init__.py` **vuoto** (upstream non lo aveva a questo livello: la sua `tests/`
  radice non era un package) per rendere `tests.specaudit` un package importabile.

Questi due aggiustamenti toccano **solo l'harness/config**, non la logica dei test (invariata).

## Esito verifica Python 3.11

Verificato **verde** su Python 3.11 il 2026-07-02 — `59 passed` (in un venv 3.11 isolato:
CPython 3.11.15, `pytest` + `jsonschema`, `PYTHONPATH=src;.`). Il pin
`requires-python = ">=3.11"` è quindi **confermato empiricamente**: nessun costrutto
genuinamente 3.12-only nel codice vendorato (`StrEnum` è 3.11+). Suite anche verde su 3.12
(il default del workspace `.venv`): `59 passed`.

## Aggiornare questa nota (invariante di provenienza)

A ogni re-vendoring futuro: aggiorna `upstream_commit`/`upstream_version`/`vendored_at`,
ripeti il diff dei punti sopra sul nuovo `pyproject.toml` upstream, e verifica che nessuna
nuova dipendenza runtime sia comparsa silenziosamente. Non lasciare questa nota stantia.
