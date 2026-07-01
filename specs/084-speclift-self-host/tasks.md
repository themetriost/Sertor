# Tasks — Self-hosting / dogfooding di SpecLift su Sertor (speclift FEAT-001)

**Branch**: `084-speclift-self-host` · **Generato**: 2026-07-01
**Spec**: [`spec.md`](spec.md) · **Piano**: [`plan.md`](plan.md) · **Ricerca**: [`research.md`](research.md)
**Dati**: [`data-model.md`](data-model.md) · **Contratti**: [`contracts/evidence-locator-port.md`](contracts/evidence-locator-port.md),
[`contracts/workspace-integration.md`](contracts/workspace-integration.md) · **Quickstart**: [`quickstart.md`](quickstart.md)

> **Nota di processo.** `.specify/scripts/powershell/setup-tasks.ps1` e uno skill dedicato
> `speckit-tasks` **NON esistono** nel repo → parametri/struttura per convenzione dai `tasks.md`
> precedenti (forma da `075`/`082`/`083`); **nessun hook SpecKit eseguito**. Git **mai** qui: brief
> di commit al fondo per il `configuration-manager`. Comandi in **PowerShell** (Windows), dalla
> **root** del repo (`C:\Workspace\Git\Sertor`), salvo indicazione diversa.
>
> I task marcati `[P]` sono parallelizzabili nella stessa fase (file/percorsi disgiunti, nessuna
> dipendenza reciproca). Il suffisso `→ dipende da` lista i prerequisiti.

## Natura del cambiamento (vincolante, non riaprire)

**ADDITIVA / vendoring PURO, ZERO runtime di `sertor_core` (Principio XI).** Aggiunge un nuovo
membro del workspace `packages/speclift`, copiato **verbatim** da Sinthari `master @ 5ee6fc1`
(verificato: `git -C C:/Workspace/Git/ExternalRepos/Sinthari rev-parse HEAD` =
`5ee6fc13350b615225ffb34619e1cb55e089b1fc`). **Nessun file `src/**` è scritto da noi riga per
riga**: si copia, si configura il pacchetto (2 sole divergenze di packaging: Python 3.11,
`jsonschema` in dev) e si integra nel workspace/CI. Il dogfood usa l'**Adapter B** upstream
(`ProvidedEvidenceLocator`, three-gear flow `changeset → localizza via MCP → bundle --changeset/
--located → assemble`) — **mai** la CLI `sertor-rag`, **mai** `import sertor_core`. `sertor_core`
resta **byte-identico**.

## Strategia MVP/incrementale

- **Fase 0 (Setup)**: pre-flight — verifica ambiente/clone upstream/assenza destinazione.
- **Fase 1 (Foundational, blocca tutto)**: la copia verbatim (`src/`, `tests/`, skill sorgente,
  contratti) + `pyproject.toml`/`LICENSE`/`VENDORING.md` del pacchetto sono il prerequisito
  condiviso — senza di essi nessuna user story è verificabile.
- **Fase 2 (US3, Must)**: integrazione nel workspace `uv` (nessun ciclo, `sertor_core` invariato) —
  prerequisito per eseguire qualunque comando `uv run` sul pacchetto.
- **Fase 3 (US6, Must, dipende da Fase 2)**: la suite vendorata gira ed è verde nel workspace + step
  CI dedicato.
- **Fase 4 (US8, Must, [P] con Fase 2/3)**: deposito della skill dogfood — indipendente
  dall'integrazione workspace (tocca solo `.claude/`), può girare in parallelo.
- **Fase 5 (US1+US2, Must, dipende da Fase 2)**: il three-gear flow end-to-end su un commit reale di
  Sertor, con garanzia strutturale che il retrieval passa **solo** dall'MCP (Adapter B), mai dalla
  CLI.
- **Fase 6 (US4+US5, Must, dipende da Fase 5)**: verifica dei due fail-loud (MCP/indice giù;
  evidenza malformata).
- **Fase 7 (US9, Must)**: onestà documentale + conferma del recepimento a Sinthari (wiki).
- **Fase 8 (US10, Should, condizionale)**: verifica empirica su Python 3.11, con piano B se
  irriducibile.
- **Fase 9 (Polish)**: verifica trasversale finale (CS-1..7), lint completo, non-regressione ampia.

Sequenza vincolante: `TASK-S01` → `Fase 1` (tutti) → `Fase 2` → `{Fase 3 ‖ Fase 4}` → `Fase 5` →
`Fase 6` → `Fase 7` (può girare in parallelo da Fase 3 in poi, tocca solo `wiki/`) → `Fase 8` →
`Fase 9`.

---

## Fase 0 — Setup: pre-flight (1 task)

### TASK-S01 — Pre-flight: verifica ambiente, clone upstream e assenza destinazione

```powershell
cd C:\Workspace\Git\Sertor
git -C C:\Workspace\Git\ExternalRepos\Sinthari rev-parse HEAD
git -C C:\Workspace\Git\ExternalRepos\Sinthari log --oneline -3
```

- [ ] Verifica che il clone Sinthari sia su **`5ee6fc13350b615225ffb34619e1cb55e089b1fc`**
      (`master`, "Merge pull request #7 from themetriost/feat/speclift-pluggable-locator"). Se
      diverso: **fermati e segnala** — la copia deve essere pinnata esattamente a questo commit
      (D-1); non procedere su un commit diverso senza rigenerare research/data-model.
- [ ] Verifica che `packages/speclift/` **non esista già** nel repo Sertor:
      ```powershell
      Test-Path packages\speclift
      ```
      Atteso: `False`. Se `True`, ferma e segnala (possibile vendoring parziale precedente).
- [ ] Verifica che `.claude/skills/speclift/` **non esista già**:
      ```powershell
      Test-Path .claude\skills\speclift
      ```
      Atteso: `False`.
- [ ] Baseline pulita: `uv sync --all-packages --extra dev` completa senza errori (stato
      **pre**-vendoring, per confrontare dopo).
- [ ] Registra il conteggio di collection della suite root come baseline (nessun `ERROR` atteso):
      ```powershell
      uv run pytest --co -q -m "not cloud" 2>&1 | Select-String "ERROR"
      ```
- [ ] Verifica l'inventario upstream atteso (27 file test, ~122 funzioni `def test_`):
      ```powershell
      cd C:\Workspace\Git\ExternalRepos\Sinthari
      (Get-ChildItem -Path tests -Recurse -Filter "test_*.py").Count   # atteso: 27
      cd C:\Workspace\Git\Sertor
      ```

---

## Fase 1 — Foundational (blocca TUTTE le fasi successive): vendoring verbatim + provenienza (US7) (6 task)

> Prerequisiti: TASK-S01. Nessuna user story successiva è verificabile prima che il pacchetto
> `packages/speclift` esista con codice, test, skill sorgente e provenienza.

### TASK-F01 [P] — Copia verbatim `src/speclift/**`

→ dipende da: TASK-S01 · **Mappa**: FR-001 · US3 · data-model E1 · plan "Fasi di lavoro" §1

```powershell
$SINTHARI = "C:\Workspace\Git\ExternalRepos\Sinthari"
New-Item -ItemType Directory -Force -Path packages\speclift\src | Out-Null
Copy-Item -Path "$SINTHARI\src\speclift" -Destination packages\speclift\src\speclift -Recurse -Force
```

- [ ] Esegui la copia sopra. **Nessuna modifica di contenuto**: è una copia byte-per-byte.
- [ ] Verifica l'inventario copiato (attesi 24 file `.py`, come da `git ls-files src/speclift` su
      Sinthari): `cli.py`, `config.py`, `observability.py`, `pipeline.py`, `serialize.py`,
      `__init__.py`; `domain/{__init__,errors,models,ports,query_keys}.py`;
      `adapters/{__init__,anchor_fs,authored,ears_requirements,git_diff,provided_locator,
      rag_sertor}.py`; `stages/{__init__,bundle,filter_sources,ingest,lift,locate_evidence,
      parse_diff,render,verify}.py`.
      ```powershell
      (Get-ChildItem -Path packages\speclift\src\speclift -Recurse -Filter "*.py").Count   # atteso: 24
      ```
- [ ] Verifica byte-identità (hash) contro la sorgente:
      ```powershell
      $src = Get-ChildItem -Path "$SINTHARI\src\speclift" -Recurse -File | Get-FileHash
      $dst = Get-ChildItem -Path packages\speclift\src\speclift -Recurse -File | Get-FileHash
      Compare-Object ($src | Select -Expand Hash) ($dst | Select -Expand Hash)
      ```
      Atteso: **nessuna differenza** (output vuoto).

### TASK-F02 [P] — Copia verbatim `tests/{contract,integration,unit}/**`

→ dipende da: TASK-S01 (nessuna dipendenza da TASK-F01, file disgiunti) · **Mappa**: FR-011 · US6 ·
data-model E8 · research D-6 · plan "Fasi di lavoro" §1

```powershell
$SINTHARI = "C:\Workspace\Git\ExternalRepos\Sinthari"
Copy-Item -Path "$SINTHARI\tests" -Destination packages\speclift\tests -Recurse -Force
```

- [ ] Esegui la copia sopra (verbatim, nessuna rimozione — **suite completa**, incluso
      `test_rag_sertor.py` dell'Adapter A dormiente e i 3 file nuovi dell'Adapter B
      `test_provided_locator.py`/`test_query_keys.py`/`test_three_gear_flow.py`).
- [ ] Verifica il conteggio file (atteso: **27** file `test_*.py` + `_gitfixture.py` + 4
      `__init__.py`):
      ```powershell
      (Get-ChildItem -Path packages\speclift\tests -Recurse -Filter "test_*.py").Count   # atteso: 27
      ```
- [ ] Verifica byte-identità (hash) contro la sorgente (stesso pattern di TASK-F01):
      ```powershell
      $src = Get-ChildItem -Path "$SINTHARI\tests" -Recurse -File | Get-FileHash
      $dst = Get-ChildItem -Path packages\speclift\tests -Recurse -File | Get-FileHash
      Compare-Object ($src | Select -Expand Hash) ($dst | Select -Expand Hash)
      ```
      Atteso: nessuna differenza.
- [ ] **Non** eseguire ancora la suite (richiede il `pyproject.toml` del pacchetto — TASK-F04 — e
      l'integrazione workspace — Fase 2). Questo task è solo la copia.

### TASK-F03 [P] — Copia verbatim skill sorgente + contratti upstream + quickstart

→ dipende da: TASK-S01 · **Mappa**: FR-007 · US8 · data-model E6 · research D-9 · plan "Fasi di
lavoro" §1

**Scoperta in fase di generazione dei task:** il `pyproject.toml` upstream ha `readme =
"specs/001-speclift-mvp/quickstart.md"` — se non vendoriamo anche `quickstart.md`, il
`pyproject.toml` del pacchetto (TASK-F04) referenzierebbe un file assente, rischiando un errore di
build metadata di `hatchling` a `uv sync`/build. Per restare **fedeli all'upstream senza inventare
una terza divergenza** (oltre a D-2/D-4), si vendora anche questo file — zero costo, zero
divergenza di codice, coerente con "verbatim".

```powershell
$SINTHARI = "C:\Workspace\Git\ExternalRepos\Sinthari"

# Skill sorgente (poi copiata anche in .claude/skills/speclift/ — Fase 4, US8)
New-Item -ItemType Directory -Force -Path packages\speclift\skills\speclift | Out-Null
Copy-Item -Path "$SINTHARI\skills\speclift\SKILL.md" `
          -Destination packages\speclift\skills\speclift\SKILL.md -Force

# Contratti autoritativi (fonte di verità per contracts/evidence-locator-port.md, che li RIFERISCE)
New-Item -ItemType Directory -Force -Path packages\speclift\specs\001-speclift-mvp\contracts | Out-Null
Copy-Item -Path "$SINTHARI\specs\001-speclift-mvp\contracts\*" `
          -Destination packages\speclift\specs\001-speclift-mvp\contracts\ -Recurse -Force

# quickstart.md (referenziato dal campo `readme` del pyproject upstream, TASK-F04)
Copy-Item -Path "$SINTHARI\specs\001-speclift-mvp\quickstart.md" `
          -Destination packages\speclift\specs\001-speclift-mvp\quickstart.md -Force
```

- [ ] Esegui le copie sopra.
- [ ] Verifica presenza dei 4 file di contratto: `cli.md`, `ears-author-port.md`,
      `evidence-locator-port.md`, `evidence-bundle.schema.json`, `output.schema.json` (5 file totali
      in `contracts/`).
- [ ] Verifica byte-identità (hash) di tutti e 6 i file copiati (skill + 5 contratti + quickstart)
      contro la sorgente Sinthari.

### TASK-F04 — `packages/speclift/pyproject.toml` (le UNICHE 2 divergenze di packaging)

→ dipende da: TASK-F01, TASK-F02, TASK-F03 (referenzia `readme`/`packages`/`testpaths` sui percorsi
appena copiati) · **Mappa**: FR-002/018/019/020 · CS-3/CS-5 · US10 · data-model E1 · research D-2/D-4

**Le UNICHE divergenze rispetto al `pyproject.toml` upstream** (verificato riga per riga):
`requires-python`/`target-version` (`3.12`→`3.11`, D-4, **provvisorio**: la Fase 8/US10 lo
riconferma empiricamente o lo fa retrocedere) e collocazione di `jsonschema`
(`dependencies`→`dev`, D-2). **Tutto il resto resta byte-identico** (nome, versione statica `0.1.0`,
descrizione, `readme`, `project.scripts`, `build-system`, `tool.hatch.build.targets.wheel`,
`tool.pytest.ini_options`, `tool.ruff` per il resto, `tool.ruff.lint.select` — l'upstream ha **già**
`SIM` e line-length 110, non sono divergenze nostre).

- [ ] Crea `packages/speclift/pyproject.toml`:
      ```toml
      [project]
      name = "speclift"
      version = "0.1.0"
      description = "SpecLift — generatore diff → requisiti EARS ancorati (MVP)"
      readme = "specs/001-speclift-mvp/quickstart.md"
      requires-python = ">=3.11"
      dependencies = [
          # Solo standard library nel core. `git` è invocato via subprocess (nessuna dipendenza libgit).
          # Sertor RAG è consumato via vehicle MCP dall'agente nella skill, mai importato (Adapter B);
          # l'Adapter A (rag_sertor.py, CLI-vehicle) resta vendorato ma dormiente nel self-host Sertor.
      ]

      [project.optional-dependencies]
      dev = [
          "pytest>=8.0",
          "ruff>=0.6",
          # jsonschema: SOLO test di contratto (tests/contract/conftest.py, test_bundle.py,
          # test_render_json.py) — verificato, zero import in src/speclift/ (D-2, RNF-2).
          "jsonschema>=4.0",
      ]

      [project.scripts]
      speclift = "speclift.cli:main"

      [build-system]
      requires = ["hatchling"]
      build-backend = "hatchling.build"

      [tool.hatch.build.targets.wheel]
      packages = ["src/speclift"]

      [tool.pytest.ini_options]
      testpaths = ["tests"]
      pythonpath = ["src"]
      markers = [
          "contract: contract tests against JSON schemas / port contracts",
          "integration: end-to-end tests on real git fixtures",
      ]

      [tool.ruff]
      src = ["src", "tests"]
      line-length = 110
      target-version = "py311"

      [tool.ruff.lint]
      select = ["E", "F", "I", "UP", "B", "SIM"]
      ```
- [ ] Verifica al volo (parse TOML valido, campi attesi):
      ```powershell
      uv run python -c "
      import tomllib
      d = tomllib.load(open('packages/speclift/pyproject.toml','rb'))
      assert d['project']['requires-python'] == '>=3.11'
      assert d['project']['dependencies'] == []
      assert 'jsonschema>=4.0' in d['project']['optional-dependencies']['dev']
      assert d['tool']['ruff']['target-version'] == 'py311'
      print('ok')
      "
      ```

### TASK-F05 [P] — `packages/speclift/LICENSE` (MIT, D-7)

→ dipende da: TASK-S01 · **Mappa**: FR-002 · US7 · data-model E2 · research D-7

**Finding (segnalato, non sepolto):** Sinthari **non ha `LICENSE`** a `5ee6fc1` (verificato:
`Get-ChildItem "$SINTHARI\LICENSE*"` → nessun file). Handoff first-party stessa organizzazione
(`themetriost`) → si integra sotto la MIT di Sertor, come gli altri 3 membri del workspace.

- [ ] Crea `packages/speclift/LICENSE` con lo **stesso testo** del `LICENSE` di radice (copia dal
      pattern già usato da `packages/sertor`/`packages/sertor-install-kit`/`packages/sertor-flow`):
      ```powershell
      Copy-Item -Path LICENSE -Destination packages\speclift\LICENSE -Force
      ```
- [ ] Verifica: `Get-Content packages\speclift\LICENSE -Raw` contiene `MIT License` e
      `Copyright (c) 2026 Sertor` (identico a `LICENSE` di radice).

### TASK-F06 — `packages/speclift/VENDORING.md` (nota di provenienza)

→ dipende da: TASK-F01, TASK-F02, TASK-F03, TASK-F04, TASK-F05 (descrive lo stato finale della
copia) · **Mappa**: FR-002/003 · CS-7 · US7 · data-model E2 · research D-1/D-7

- [ ] Crea `packages/speclift/VENDORING.md`:
      ```markdown
      # Provenienza del vendoring — `packages/speclift`

      | Campo | Valore |
      |-------|--------|
      | `upstream_repo` | https://github.com/themetriost/Sinthari |
      | `upstream_commit` | `5ee6fc13350b615225ffb34619e1cb55e089b1fc` (`master`, PR #7 — "Merge pull request #7 from themetriost/feat/speclift-pluggable-locator") |
      | `upstream_version` | `0.1.0` |
      | `vendored_at` | 2026-07-01 |
      | `handoff` | first-party, stessa organizzazione GitHub `themetriost`; `5ee6fc1` è il recepimento upstream del nostro feedback di dogfooding (CLI→MCP, Adapter B pluggable) |
      | `upstream_license` | **ASSENTE** a `5ee6fc1` (nessun file `LICENSE*` nel repo Sinthari, verificato) — questa copia è integrata sotto la licenza MIT di Sertor (`LICENSE` in questa cartella); da confermare col proprietario upstream (stessa-org, non bloccante) |

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

      ## Divergenze (SOLO di packaging — nessuna divergenza di codice `src/**`)

      | # | Campo | Upstream | Vendorato | Motivo |
      |---|-------|----------|-----------|--------|
      | 1 | `[project.dependencies]` | `["jsonschema>=4.0"]` | `[]` | `jsonschema` è usata **solo** nei test di contratto (verificato: zero import in `src/`); runtime resta stdlib-only (D-2, RNF-2) |
      | 2 | `[project.optional-dependencies].dev` | `["pytest>=8.0","ruff>=0.6"]` | `+= "jsonschema>=4.0"` | sposta la dipendenza da (1) qui |
      | 3 | `requires-python` | `>=3.12` | `>=3.11` | riconciliazione col pavimento del workspace Sertor (D-4), **condizionata** alla verifica empirica su 3.11 (vedi `tasks.md` Fase 8/US10 — se irriducibile, questo campo E questa riga tornano a `>=3.12` con la discrepanza dichiarata sotto) |
      | 4 | `[tool.ruff] target-version` | `py312` | `py311` | coerente col punto 3 |
      | 5 | `LICENSE` | assente | MIT (Sertor) | D-7, finding registrato sopra |

      Tutto il resto del `pyproject.toml` (nome, versione statica `0.1.0`, descrizione, `readme`,
      `project.scripts`, `build-system`, `tool.hatch.build.targets.wheel`,
      `tool.pytest.ini_options`, `tool.ruff` per il resto, `tool.ruff.lint.select` — l'upstream ha
      **già** `SIM`/110 righe) resta **byte-identico** all'upstream.

      ## Esito verifica Python 3.11 (Fase 8/US10 di `tasks.md`)

      <!-- Compilare a valle di TASK-US10-01/02: "verificato verde su 3.11 il <data>" oppure,
           se irriducibile, il costrutto 3.12-only + l'impatto sul pavimento del workspace
           (FR-020, piano B). Non lasciare questa sezione vuota/stantia. -->

      ## Aggiornare questa nota (invariante FR-003)

      A ogni re-vendoring futuro: aggiorna `upstream_commit`/`upstream_version`/`vendored_at`,
      ripeti il diff dei 5 punti sopra sul nuovo `pyproject.toml` upstream, e verifica che nessuna
      nuova dipendenza runtime sia comparsa silenziosamente. Non lasciare questa nota stantia.
      ```
- [ ] Verifica: il file esiste, cita `5ee6fc1`, `0.1.0`, e i 5 punti di divergenza.

**Verifica di chiusura Fase 1 (blocca la Fase 2):**

- [ ] Struttura attesa presente:
      ```powershell
      Test-Path packages\speclift\pyproject.toml, packages\speclift\LICENSE, `
                packages\speclift\VENDORING.md, packages\speclift\src\speclift\cli.py, `
                packages\speclift\tests\unit\test_provided_locator.py, `
                packages\speclift\skills\speclift\SKILL.md, `
                packages\speclift\specs\001-speclift-mvp\contracts\evidence-locator-port.md
      ```
      Atteso: tutti `True`.
- [ ] Grep di onestà (I3 del contratto workspace): **zero** import reali di `sertor_core`, le uniche
      occorrenze della stringa sono i 2 commenti upstream che **dichiarano** di non farlo:
      ```powershell
      Get-ChildItem -Path packages\speclift\src -Recurse -Filter "*.py" | Select-String "sertor_core"
      ```
      Atteso: **esattamente 2** righe — `config.py:26` (`#: Comando-vehicle... mai import
      sertor_core`) e `adapters/rag_sertor.py:3` (docstring "**Mai** `import sertor_core`") —
      **zero** istruzioni `import`/`from ... import` reali.

---

## Fase 2 — US3 (P1, Must): integrazione nel workspace `uv`, nessun ciclo (3 task)

> Prerequisiti: Fase 1 completa. Blocca Fase 3/5/6/8 (tutte richiedono `uv run` sul pacchetto).

### TASK-US3-01 — Root `pyproject.toml`: `members += "packages/speclift"`

→ dipende da: Fase 1 completa · **Mappa**: FR-001/013 · CS-3/5 · US3 · contratto
workspace-integration §"Membri del workspace" · data-model §"Modifiche ai file di configurazione"

- [ ] In `pyproject.toml` (root), sostituisci il blocco `[tool.uv.workspace]`:
      ```toml
      [tool.uv.workspace]
      # Monorepo uv (FEAT-012/037, D1): la root è `sertor-core`; i membri sono `packages/sertor`
      # (installer wiki/rag, consumatore di sertor-core), `packages/sertor-install-kit` (motore di
      # installazione condiviso, stdlib-only), `packages/sertor-flow` (installer governance/SDLC) e
      # `packages/speclift` (SpecLift vendorato per il self-host, feature 084 — zero dipendenze
      # dagli altri membri: `speclift -> ∅`, nessun `[tool.uv.sources]` necessario per esso).
      members = ["packages/sertor", "packages/sertor-install-kit", "packages/sertor-flow", "packages/speclift"]
      ```
- [ ] **Non** aggiungere alcuna voce `[tool.uv.sources]` per `speclift` (non dipende da nessun
      membro workspace — a differenza di `sertor`/`sertor-flow` che dipendono da `sertor-core`/
      `sertor-install-kit`).

### TASK-US3-02 [P] — Root `pyproject.toml`: `ruff extend-exclude += "packages/speclift"`

→ dipende da: Fase 1 completa (file disgiunto da TASK-US3-01, stesso file ma sezione diversa —
marcato `[P]` concettualmente, applicare in sequenza sullo stesso file) · **Mappa**: FR-013 · D-5 ·
contratto workspace-integration §"Configurazione per-pacchetto"

- [ ] Nello stesso `pyproject.toml` (root), sezione `[tool.ruff]`, aggiorna `extend-exclude`:
      ```toml
      [tool.ruff]
      line-length = 100
      target-version = "py311"
      # The exploration prototype is FROZEN/read-only by design (see CLAUDE.md): out of lint scope.
      # packages/speclift is VENDORED verbatim from Sinthari (feature 084): it keeps its own
      # [tool.ruff] (110/py311/+SIM) and MUST NOT be reformatted to Sertor's style on re-vendoring.
      extend-exclude = ["prototype", "packages/speclift"]
      src = [
          "src", "tests",
          "packages/sertor/src", "packages/sertor/tests",
          "packages/sertor-install-kit/src", "packages/sertor-install-kit/tests",
          "packages/sertor-flow/src", "packages/sertor-flow/tests",
      ]
      ```
      **Non** aggiungere `packages/speclift/src`/`tests` alla lista `src` (contraddirebbe
      l'esclusione — stesso precedente di `prototype`, che non vi compare).
- [ ] **Non** toccare `[tool.pytest.ini_options]` di root: `testpaths = ["tests"]` **non**
      colleziona `packages/speclift/tests` di per sé (D-6) — nessuna modifica necessaria lì.

### TASK-US3-03 — `uv sync --all-packages` e verifica non-ciclo/non-regressione

→ dipende da: TASK-US3-01, TASK-US3-02 · **Mappa**: FR-001/012/013 · CS-3/5 · US3 · contratto
workspace-integration I1/I2

```powershell
uv sync --all-packages --extra dev
```

- [ ] Esegui il comando sopra: risoluzione **senza errori** (I1). Questo rigenera `uv.lock`.
- [ ] Verifica il grafo di dipendenza dei membri (nessun ciclo, `speclift -> ∅`):
      ```powershell
      uv tree --package speclift
      ```
      Atteso: nessuna dipendenza da altri membri workspace (`sertor-core`/`sertor-install-kit`/
      `sertor`/`sertor-flow` assenti dall'albero di `speclift`).
- [ ] Verifica **`sertor_core` invariato** (I2, CS-3): `git diff` limitato al core e alla riga di
      workspace, deve mostrare **solo** le 2 righe attese (members + extend-exclude) su
      `pyproject.toml`, **zero** modifiche a `src/sertor_core`:
      ```powershell
      git diff -- src/sertor_core
      git diff -- pyproject.toml
      ```
      Atteso: il primo comando produce **output vuoto**; il secondo mostra **solo** le 2 righe
      modificate (members list + extend-exclude), nessun'altra riga.
- [ ] Conferma `uv.lock` è stato rigenerato (contiene una voce `speclift`):
      ```powershell
      Select-String -Path uv.lock -Pattern "^name = ""speclift""" -Context 0,3
      ```

**Verifica di chiusura Fase 2:**

- [ ] `uv sync --all-packages --extra dev` (ri-eseguito) resta idempotente/pulito.

---

## Fase 3 — US6 (P1, Must): suite di test vendorata verde nel workspace (4 task)

> Prerequisiti: Fase 2 completa (serve `uv sync` con `packages/speclift` risolto). `[P]` con Fase 4.

### TASK-US6-01 — Esegui la suite vendorata (attesi 122 test verdi)

→ dipende da: Fase 2 · **Mappa**: FR-011 · CS-4 · US6 · contratto workspace-integration I4 ·
data-model E8

```powershell
uv run pytest packages/speclift/tests -m "not cloud" -v
```

- [ ] Esegui il comando: **tutti i test passano** (atteso: **122 passed** — 8 contract + 17
      integration + 97 unit; se il conteggio reale diverge leggermente, verifica che sia comunque
      **completa** — nessun test upstream escluso — prima di procedere).
- [ ] Verifica il conteggio di collection esatto:
      ```powershell
      uv run pytest packages/speclift/tests --co -q -m "not cloud" | Select-String "tests collected"
      ```
- [ ] Verifica specificamente i 3 gruppi di test dell'Adapter B + il test dell'Adapter A dormiente
      (tutti offline, nessuna rete/RAG reale):
      ```powershell
      uv run pytest packages/speclift/tests/unit/test_provided_locator.py `
                    packages/speclift/tests/unit/test_query_keys.py `
                    packages/speclift/tests/integration/test_three_gear_flow.py `
                    packages/speclift/tests/unit/test_rag_sertor.py -v
      ```
      Atteso: `8 + 5 + 3 + 8 = 24 passed`.

### TASK-US6-02 [P] — Step CI dedicato `Tests — speclift`

→ dipende da: Fase 2 (non da TASK-US6-01 — file disgiunto, `.github/workflows/ci.yml`) · **Mappa**:
FR-011 · D-6 · contratto workspace-integration §"CI (dopo)"

- [ ] In `.github/workflows/ci.yml`, aggiungi lo step dopo `"Tests — sertor-flow (governance
      installer)"` (job `test`):
      ```yaml
        - name: Tests — speclift (vendored self-host)
          run: uv run pytest packages/speclift/tests -m "not cloud"
      ```
- [ ] **Opzionale (D-5, non bloccante per il gate):** aggiungi anche lo step di lint dedicato, subito
      dopo:
      ```yaml
        - name: Lint — speclift (vendored, own ruff config)
          run: uv run ruff check packages/speclift
      ```
- [ ] Verifica che il job `test` non richieda altre modifiche (la matrice OS/Python 3.12 esistente
      già copre il nuovo step; la verifica su Python 3.11 di US10 **non** entra nella matrice CI —
      resta un passo manuale/di release, coerente col research D-4).

### TASK-US6-03 — Non-regressione sulle altre suite del workspace

→ dipende da: TASK-US3-03 · **Mappa**: RNF-3 · CS-4 · US6 · contratto workspace-integration I6

```powershell
uv run pytest -m "not cloud and not integration"
uv run pytest packages/sertor/tests -m "not cloud and not integration"
uv run pytest packages/sertor-install-kit/tests -m "not cloud and not integration"
uv run pytest packages/sertor-flow/tests -m "not cloud and not integration"
```

- [ ] Tutti e 4 i comandi restano **verdi**, con lo **stesso** numero di test raccolti di prima del
      vendoring (nessuna regressione di collezione dovuta al nuovo membro).

### TASK-US6-04 — Lint completo (root escluso speclift + speclift col proprio stile)

→ dipende da: TASK-US3-02 · **Mappa**: D-5 · contratto workspace-integration I7

```powershell
uv run ruff check .
uv run ruff check packages/speclift
```

- [ ] `uv run ruff check .` (root) è **verde** — `packages/speclift` è escluso, nessun churn di
      stile sul codice vendorato.
- [ ] `uv run ruff check packages/speclift` (stile proprio 110/`SIM`/py311) è **verde** by
      construction (codice verbatim, già verde upstream salvo `target-version` — verificare che il
      solo cambio py312→py311 non introduca nuovi warning `UP`; se sì, **non** correggere il codice
      vendorato — è un segnale per Fase 8/US10, non per questo task).

**Verifica di chiusura Fase 3:** suite speclift verde (122), altre suite invariate, lint verde su
entrambi i perimetri.

---

## Fase 4 — US8 (P1, Must): skill del dogfood depositata, host-agnostica [P con Fase 2/3] (2 task)

> Prerequisiti: Fase 1 (TASK-F03, skill sorgente già copiata in `packages/speclift/skills/`).
> Indipendente da Fase 2/3 (tocca solo `.claude/`) → parallelizzabile.

### TASK-US8-01 — Deposita `.claude/skills/speclift/SKILL.md` (copia verbatim)

→ dipende da: TASK-F03 · **Mappa**: FR-007 · US8 · data-model E6 · research D-9

```powershell
New-Item -ItemType Directory -Force -Path .claude\skills\speclift | Out-Null
Copy-Item -Path packages\speclift\skills\speclift\SKILL.md `
          -Destination .claude\skills\speclift\SKILL.md -Force
```

- [ ] Esegui la copia sopra (dalla copia già vendorata in `packages/speclift/skills/`, fonte unica
      interna al repo — stesso contenuto della sorgente Sinthari).
- [ ] Verifica byte-identità: `(Get-FileHash packages\speclift\skills\speclift\SKILL.md).Hash -eq
      (Get-FileHash .claude\skills\speclift\SKILL.md).Hash` → `True`.

### TASK-US8-02 — Verifica host-agnosticità (forma) + presenza Procedura B

→ dipende da: TASK-US8-01 · **Mappa**: FR-008 · US8 · research D-9 · Constitution Check Principio X

- [ ] Verifica **assenza** di path-assistente/slash-command/nomi-modello (forma host-agnostica):
      ```powershell
      Select-String -Path .claude\skills\speclift\SKILL.md `
        -Pattern "\.claude/|\.github/|^/\w+|Claude Code|GPT-|\bOpus\b|\bSonnet\b|\bHaiku\b"
      ```
      Atteso: **zero match** (i tool MCP `search_code`/`find_symbol`/`who_calls` citati sono
      vehicle **di Sertor**, non un dettaglio dell'assistente ospite — ammessi per Principio X,
      research D-9).
- [ ] Verifica presenza della **Procedura B** (three-gear flow via MCP):
      ```powershell
      Select-String -Path .claude\skills\speclift\SKILL.md -Pattern "search_code|located\.json|changeset"
      ```
      Atteso: match presenti (la Procedura B nomina `search_code`, il file `located.json`, il
      comando `changeset`).
- [ ] Verifica presenza dell'istruzione di fail-loud (US4, FR-009) nel corpo della Procedura B:
      ```powershell
      Select-String -Path .claude\skills\speclift\SKILL.md -Pattern "ferma|fermati|arrestat"
      ```
      Atteso: almeno un match nella sezione Procedura B (istruzione a fermarsi su MCP/indice giù).

**Verifica di chiusura Fase 4:** skill scopribile in `.claude/skills/speclift/SKILL.md`,
host-agnostica nella forma, Procedura B presente con fail-loud istruito.

---

## Fase 5 — US1+US2 (P1, Must): three-gear flow end-to-end via Adapter B, mai via CLI (7 task)

> Prerequisiti: Fase 2 completa (`speclift` eseguibile via `uv run`); indice RAG di Sertor
> costruito e fresco; server MCP `sertor-rag` registrato (`.mcp.json`, già presente nel repo).
> Sequenziale (ogni marcia consuma l'output della precedente).

### TASK-US12-01 — Prerequisiti: indice fresco + server MCP attivo

→ dipende da: Fase 2 · **Mappa**: A-003 · NFR-4 · US1

```powershell
uv run sertor-rag index .
uv run sertor-rag doctor
```

- [ ] `sertor-rag index .` completa senza errori (indice del corpus `sertor` fresco).
- [ ] `sertor-rag doctor` riporta l'area `index` **sana** (non stantia) e l'area `mcp` registrata.
- [ ] Verifica che il server MCP `sertor-rag` sia effettivamente **riavviato** se già in esecuzione
      (il server legge l'indice da disco ma serve codice/indice nuovi solo dopo un riavvio — nota
      standing del rituale di step, punto 8).

### TASK-US12-02 — Marcia 0: `speclift changeset` su un commit reale di Sertor

→ dipende da: TASK-US12-01 · **Mappa**: FR-014 · CS-1 · US1 · quickstart §"Marcia 0" · contratto
evidence-locator-port.md §"three-gear flow" punto 1

```powershell
uv run speclift changeset <REF> --out $env:TEMP\speclift-changeset
```

- [ ] Scegli `<REF>` = un commit reale del repo Sertor che tocchi file `src/`/`packages/*/src`
      (esempio ancorato: `040eaf4` — "test(installer): parity guard esteso + budget altitude
      blocchi CLAUDE.md (E10-FEAT-024)", tocca `packages/sertor/src/...`/test; sostituibile con
      qualunque commit reale equivalente al momento dell'esecuzione, es. `git log --oneline -20 --
      src packages/*/src`).
- [ ] Verifica che `$env:TEMP\speclift-changeset.changeset.json` sia prodotto, **non vuoto**, e
      contenga hunk con `candidate_identifiers` **e** `lines` per i file toccati dal commit.
- [ ] Verifica che questa marcia **non tocchi il RAG** (funziona anche a indice assente — NFR-4):
      ripeti il comando con l'MCP non necessario per questo passo specifico (la marcia 0 è
      puramente `ingest → parse_diff → filter_sources`, nessuna localizzazione).

### TASK-US12-03 — Passo agente: localizza l'evidenza via MCP `search_code`, scrivi `located.json`

→ dipende da: TASK-US12-02 · **Mappa**: FR-005/006 · CS-1 · US1/US2 · quickstart §"Passo agente"

**Questo task è un passo di GIUDIZIO dell'agente che esegue l'implement**, non uno script
deterministico — segui `quickstart.md` §"Passo agente — Localizza l'evidenza via MCP" alla lettera:

- [ ] Per ogni hunk emesso dalla marcia 0, deriva le query con la regola **G6**
      (`build_identifier_queries`: identificatori deduplicati, cap `max_queries_per_symbol`,
      fallback alla prima riga snippet solo se identificatore singolo).
- [ ] Interroga il tool MCP **`search_code`** (e, dove utile, `find_symbol`/`who_calls`) per
      proporre simboli candidati e i test che li coprono.
- [ ] Scrivi `$env:TEMP\speclift-located.json` con chiavi **composite**
      `"<file_path>::<query>"` per `symbols` e nome-simbolo per `tests` (schema esatto in
      `quickstart.md`). **Non inventare** un simbolo/test per una query senza risultati: ometti la
      chiave o usa `[]`.
- [ ] **Se `search_code` erra** (MCP/indice giù) durante questo passo → **non proseguire**: questo è
      esattamente lo scenario di US4 (Fase 6, TASK-US45-01) — fermati, segnala, e riprendi da lì
      invece che da qui.

### TASK-US12-04 — Marcia 1: `speclift bundle --changeset --located` (Adapter B)

→ dipende da: TASK-US12-03 · **Mappa**: FR-004/005/006/014 · CS-1 · US1/US2 · quickstart §"Marcia
1" · contratto evidence-locator-port.md §"three-gear flow" punto 3

```powershell
uv run speclift bundle `
  --changeset $env:TEMP\speclift-changeset.changeset.json `
  --located   $env:TEMP\speclift-located.json `
  --out       $env:TEMP\speclift-evidence
```

- [ ] Esegui il comando: produce `$env:TEMP\speclift-evidence.bundle.json`, **non vuoto**.
- [ ] Verifica che le voci del bundle referenzino **path Sertor reali** (esistenti sul filesystem) e,
      dove risolvibili, simboli reali (nomi presenti nel codice indicato).
- [ ] Verifica che il comando **non** abbia invocato `default_components()` (l'Adapter A/
      `SertorRagLocator` non è nemmeno istanziato su questo ramo — `cli.py:213-230`, verificabile
      per lettura del codice vendorato, nessuna istrumentazione runtime necessaria).

### TASK-US12-05 — Passo agente: scrivi le frasi EARS (`speclift-authored.json`)

→ dipende da: TASK-US12-04 · **Mappa**: RNF-6 · US1 · quickstart §"Passo agente — Scrivi le frasi
EARS"

- [ ] Leggi `$env:TEMP\speclift-evidence.bundle.json`; per ogni item scrivi almeno una frase EARS
      (quota `user_capability`/`behaviour`/`implementation`), agganciata **per indice** (mai
      un'àncora nuova/inventata).
- [ ] Scrivi `$env:TEMP\speclift-authored.json` con `changeset_ref` uguale a quello del bundle
      (schema esatto in `quickstart.md`).

### TASK-US12-06 — Marcia 2: `speclift assemble` (il "moat", identico al percorso di default)

→ dipende da: TASK-US12-05 · **Mappa**: FR-015 · CS-2 · US1 · quickstart §"Marcia 2"

```powershell
uv run speclift assemble `
  --bundle   $env:TEMP\speclift-evidence.bundle.json `
  --authored $env:TEMP\speclift-authored.json `
  --repo     . `
  --out      $env:TEMP\speclift-report
```

- [ ] Esegui il comando: produce `$env:TEMP\speclift-report.speclift.json` +
      `$env:TEMP\speclift-report.speclift.md`.
- [ ] Apri il report JSON: verifica che ogni àncora sia stata **riverificata sul filesystem** di
      Sertor (non solo assunta valida dal bundle).
- [ ] Se un'àncora non regge (es. un simbolo proposto dall'agente che in realtà non esiste a quella
      posizione), verifica che compaia sotto `excluded` **con motivo** — mai scartata in silenzio,
      mai tenuta come valida (CS-2, US1 AC3).

### TASK-US12-07 — Verifica strutturale: Adapter B usato, Adapter A dormiente, nessuna CLI/import

→ dipende da: TASK-US12-04 · **Mappa**: FR-004 · CS-1/3 · US2 · contratto workspace-integration
I3/I3b · contratto evidence-locator-port.md §"Come il self-host garantisce l'Adapter B"

- [ ] **Tripwire strutturale:** conferma che la root di Sertor **non ha** un progetto `.sertor/`
      (l'Adapter A, se invocato per errore, spawnerebbe `uv run --project .sertor sertor-rag` e
      fallirebbe *loud* con `RagUnavailableError`, exit 3 — mai in silenzio):
      ```powershell
      Test-Path .sertor
      ```
      Atteso: `False`.
- [ ] Conferma che il flusso TASK-US12-02..06 **non ha generato** alcun processo figlio
      `sertor-rag` (nessun errore/output riconducibile a un tentativo di subprocess CLI durante la
      marcia 1/2 — il flow B non lo invoca per costruzione, `cli.py:213-230`).
- [ ] Grep di onestà sul path di localizzazione: nessun import reale di `sertor_core` (già
      verificato in Fase 1, ri-confermato qui come parte della garanzia US2):
      ```powershell
      Get-ChildItem -Path packages\speclift\src -Recurse -Filter "*.py" | `
        Select-String "^\s*(import sertor_core|from sertor_core)"
      ```
      Atteso: **zero match** (nessuna istruzione `import` reale — solo i 2 commenti già noti,
      esclusi da questo pattern più stretto).

**Verifica di chiusura Fase 5 (CS-1/CS-2 soddisfatti):** bundle non vuoto su path Sertor reali,
report riverificato con `excluded` esplicito, Adapter B confermato come unico path usato.

---

## Fase 6 — US4+US5 (P1, Must): fail-loud su MCP/indice giù e su evidenza malformata (2 task)

> Prerequisiti: Fase 5 (riusa gli artefatti `speclift-changeset.changeset.json` prodotti lì).

### TASK-US45-01 — Verifica US4: MCP/indice giù → la skill si ferma e segnala

→ dipende da: Fase 5, TASK-US8-02 (la skill istruisce già il fail-loud) · **Mappa**: FR-009 · CS-6 ·
US4 · quickstart §"Nota di onestà" · edge case "MCP/indice RAG stantio/assente"

**Verifica procedurale (non uno script deterministico — US4 vive nella skill/agente):**

- [ ] Simula l'indisponibilità: rinomina temporaneamente `.mcp.json` (es. `.mcp.json.bak`) o ferma
      il server MCP `sertor-rag` attivo.
- [ ] Ripeti il passo agente (TASK-US12-03) su un nuovo hunk: l'agente, guidato dalla skill, deve
      **fermarsi** al primo errore di `search_code`, **nominare il componente non disponibile**
      (MCP/indice) e **raccomandare il rimedio** (`sertor-rag index .` o riavvio server) — **senza**
      produrre un `located.json` con evidenza parziale/vuota/fabbricata.
- [ ] Verifica che **nessun** `bundle.json` sia stato prodotto a valle di questo tentativo fallito
      (il flusso si ferma prima della marcia 1).
- [ ] Ripristina `.mcp.json` (rinomina indietro) / riavvia il server MCP prima di procedere.

### TASK-US45-02 — Verifica US5: evidenza malformata → exit 5 (non exit 6)

→ dipende da: Fase 5 (riusa `speclift-changeset.changeset.json`) · **Mappa**: FR-010 · CS-6 · US5 ·
contratto evidence-locator-port.md §"Vincoli fail-loud" · data-model U5

```powershell
# (a) located.json non-JSON / illeggibile
"questo non è JSON" | Out-File -Encoding utf8 $env:TEMP\speclift-located-bad1.json
uv run speclift bundle --changeset $env:TEMP\speclift-changeset.changeset.json `
  --located $env:TEMP\speclift-located-bad1.json --out $env:TEMP\speclift-evidence-bad1
Write-Output "exit code: $LASTEXITCODE"

# (b) located.json JSON valido ma con valore malformato (es. "symbols" non è un dict)
'{"symbols": "not-a-dict", "tests": {}}' | Out-File -Encoding utf8 $env:TEMP\speclift-located-bad2.json
uv run speclift bundle --changeset $env:TEMP\speclift-changeset.changeset.json `
  --located $env:TEMP\speclift-located-bad2.json --out $env:TEMP\speclift-evidence-bad2
Write-Output "exit code: $LASTEXITCODE"

# (c) flag-misuse: --changeset senza --located
uv run speclift bundle --changeset $env:TEMP\speclift-changeset.changeset.json `
  --out $env:TEMP\speclift-evidence-bad3
Write-Output "exit code: $LASTEXITCODE"
```

- [ ] Caso (a): exit code **5**, nessun `speclift-evidence-bad1.bundle.json` prodotto.
- [ ] Caso (b): exit code **5**, nessun `speclift-evidence-bad2.bundle.json` prodotto.
- [ ] Caso (c): exit code **2** (flag-misuse — `--changeset` senza `--located`, non un errore di
      contenuto).
- [ ] Conferma che **nessuno** dei tre casi produce un'evidenza vuota/di default accettata in
      silenzio (Principio IV/XII) — e che **non esiste** un exit code 6 nel comportamento osservato
      (era il nostro design superato, non adottato).

**Verifica di chiusura Fase 6 (CS-6 soddisfatto):** entrambi i fail-loud sono azionabili — MCP/
indice giù ferma la skill con causa nominata; evidenza malformata fallisce exit 5 nel codice
deterministico, mai un ripiego silenzioso.

---

## Fase 7 — US9 (P1, Must): onestà sul retrieval MCP + conferma del recepimento a Sinthari (3 task)

> Prerequisiti: nessuno strutturale (documentazione) — può girare in parallelo dalla Fase 3 in poi.
> Tocca solo `wiki/`.

### TASK-US9-01 — Verifica che i design doc dichiarino già l'adozione + il gap residuo

→ dipende da: nessuno (verifica di sola lettura) · **Mappa**: FR-016 · US9 · Gruppo H

- [ ] Conferma (nessuna modifica attesa — sono già stati rigenerati in questo ciclo di design) che
      `plan.md`, `research.md` (§D-9, "Dichiarazione di onestà doc↔codice — Gruppo H"),
      `data-model.md` (§"Legame RAG reale") e `quickstart.md` (§"Nota di onestà") dichiarino
      esplicitamente: (a) il self-host usa il tool MCP `search_code` orchestrato dall'agente
      (Adapter B pluggable, già presente upstream a `5ee6fc1`); (b) resta un gap rispetto alla
      navigazione del code-graph (`find_symbol`/`who_calls`) — `search_code` è ricerca semantica,
      non navigazione del grafo.
- [ ] Se una qualunque di queste 4 fonti **non** contenesse la dichiarazione (drift), correggila
      immediatamente (regola standing "Correggi il drift senza giustificarti") prima di procedere.

### TASK-US9-02 — Aggiorna lo stato stantio in `sinthari-reply-speclift-locator-pluggable.md`

→ dipende da: TASK-S01 (verifica ambientale già fatta) · **Mappa**: FR-017 · US9

**Scoperta in fase di generazione dei task:** il file `wiki/sources/input-other-agents/
sinthari-reply-speclift-locator-pluggable.md` (già presente, ricevuto 2026-07-01) porta nel
frontmatter `status: implementato lato Sinthari, non ancora mergiato in master — in attesa di
re-vendoring da parte vostra`. Questo è **ora stantio**: `5ee6fc1` **è** mergiato su `master`
Sinthari (verificato TASK-S01) e questa feature lo vendora. Corregge il drift (non lo lascia
appeso).

- [ ] Aggiorna il frontmatter di `wiki/sources/input-other-agents/
      sinthari-reply-speclift-locator-pluggable.md`:
      ```yaml
      status: mergiato upstream su master (5ee6fc1, PR #7) — vendorato in packages/speclift (feature 084)
      updated: 2026-07-01
      ```
- [ ] Non modificare il corpo del documento (è la voce **ricevuta** da Sinthari, non nostra) — solo
      il campo di stato che descrive **il nostro** avanzamento verso di esso.

### TASK-US9-03 — Registra la conferma/ringraziamento a Sinthari (FR-017)

→ dipende da: TASK-US9-02, Fase 5 completa (la conferma cita l'esito reale del vendoring) ·
**Mappa**: FR-017 · CS-7 · US9 · Gruppo H

**Scoperta in fase di generazione dei task:** `sinthari-reply-speclift-locator-pluggable.md` cita
come fonte `wiki/sources/input-other-agents/sertor-feedback-speclift-cli-to-mcp.md` — questo file
**non risulta mai esistito** nella storia git di Sertor (`git log --all --diff-filter=A -- "*sertor-
feedback-speclift-cli-to-mcp*"` → nessun risultato). Il feedback originale è stato evidentemente
scambiato in modo conversazionale/non persistito come voce separata. **Non fabbricare
retroattivamente** quel file (ricostruirne un contenuto "come se" fosse stato scritto allora sarebbe
falsificare la cronologia) — dichiara onestamente la lacuna nella nuova voce.

- [ ] Crea `wiki/sources/input-other-agents/sertor-confirms-speclift-adapter-b-vendored.md`:
      ```markdown
      ---
      title: "Conferma Sertor — Adapter B pluggable adottato e vendorato (feature 084)"
      type: feedback
      tags: [feedback, speclift, sinthari, mcp, adapter-b, vendoring, plan-084]
      from: Sertor
      to: Sinthari
      created: 2026-07-01
      status: chiuso — Adapter B vendorato e in uso nel self-host
      sources:
        - "wiki/sources/input-other-agents/sinthari-reply-speclift-locator-pluggable.md (la loro risposta)"
        - "wiki/sources/input-other-agents/speclift-recon-pluggable.md (la nostra ricognizione ancorata)"
        - "specs/084-speclift-self-host/ (piano/ricerca/tasks di questa feature)"
      ---

      # Conferma: adottato l'Adapter B pluggable, self-host completato

      **Da:** Sertor · **A:** Sinthari · **Data:** 2026-07-01

      Grazie per l'`ProvidedEvidenceLocator` (Adapter B) e il three-gear flow (`changeset` →
      localizzazione via agente/MCP → `bundle --changeset/--located` → `assemble`). Confermiamo:

      - Il commit `5ee6fc1` (`master`, PR #7) è stato **vendorato verbatim** in
        `packages/speclift/` del repo Sertor (feature `084-speclift-self-host`), incluse **entrambe**
        le implementazioni della porta `EvidenceLocator` (`rag_sertor.py` Adapter A, dormiente nel
        nostro self-host; `provided_locator.py` Adapter B, quello che usiamo).
      - Il self-host esegue il three-gear flow reale su changeset di Sertor stesso, con la
        localizzazione dell'evidenza affidata al nostro agente via il tool MCP `search_code` (e,
        dove utile, `find_symbol`/`who_calls`), scrivendo `located.json` nello schema che avete
        definito (`"<file_path>::<query>"`).
      - I 122 test della vostra suite (inclusi i vostri `test_provided_locator.py`/
        `test_query_keys.py`/`test_three_gear_flow.py`) girano verdi nel nostro workspace `uv`.

      ## Una lacuna che segnaliamo (onestà, non un problema bloccante)

      La vostra risposta (`sinthari-reply-speclift-locator-pluggable.md`) cita come fonte un nostro
      file `wiki/sources/input-other-agents/sertor-feedback-speclift-cli-to-mcp.md`: quel file
      **non risulta mai stato creato/committato** nel repo Sertor — il feedback originale
      "CLI→MCP" è stato scambiato in una forma che non abbiamo persistito come voce separata.
      Lo segnaliamo per completezza dell'archivio, non per contestare il contenuto (che la vostra
      risposta riassume comunque fedelmente).

      ## Gap residuo dichiarato (non chiuso qui)

      Il nostro self-host usa `search_code` (ricerca semantica), non la navigazione del code-graph
      (`find_symbol`/`who_calls`) in modo sistematico — restiamo aperti a usarli quando utile, ma
      la garanzia forte del vostro "moat" (verifica delle àncore sul filesystem) rende questo gap
      non bloccante: nessun'àncora localizzata "a caso" sopravvive al report finale.

      Distribuzione su ospiti esterni (oltre il nostro dogfood) resta una feature nostra separata
      (FEAT-002), non in ambito qui.
      ```
- [ ] Verifica: il file esiste, cita `5ee6fc1`, dichiara la lacuna sulla fonte mancante, dichiara il
      gap code-graph.

**Verifica di chiusura Fase 7:** documentazione onesta confermata (nessun drift residuo), stato
della risposta Sinthari aggiornato, conferma del recepimento registrata (FR-017 chiuso).

---

## Fase 8 — US10 (P2, Should, condizionale): riconciliazione Python 3.11 (2 task)

> Prerequisiti: Fase 3 completa (suite verde sulla Python di CI, 3.12, come baseline prima di
> testare 3.11).

### TASK-US10-01 — Verifica empirica su interprete Python 3.11

→ dipende da: Fase 3 · **Mappa**: FR-019 · US10 · research D-4 · contratto workspace-integration I5

```powershell
uv python install 3.11
uv run --python 3.11 pytest packages/speclift/tests -m "not cloud" -v
```

- [ ] Se **verde** (atteso, in base al grep negativo di sintassi 3.12-only nel research — l'unico
      costrutto rilevante, `StrEnum`, è 3.11+): il pin `requires-python = ">=3.11"` già impostato in
      TASK-F04 è **confermato** — nessuna ulteriore modifica al `pyproject.toml` del pacchetto.
      Aggiorna `packages/speclift/VENDORING.md` §"Esito verifica Python 3.11" con: "verificato verde
      su Python 3.11 il `<data>` — `N passed`".

### TASK-US10-02 — Piano B (condizionale): se rosso, NON abbassare in silenzio

→ dipende da: TASK-US10-01 (solo se rosso) · **Mappa**: FR-020 · US10 · edge case "Costrutto
3.12-only irriducibile"

**Eseguire SOLO se TASK-US10-01 fallisce con un errore riconducibile a un costrutto Python
genuinamente 3.12-only** (non un problema d'ambiente/dipendenza):

- [ ] Identifica il costrutto esatto (file:riga) che richiede 3.12+.
- [ ] Riporta `packages/speclift/pyproject.toml` a `requires-python = ">=3.12"` e
      `[tool.ruff] target-version = "py312"` (**non** lasciare `>=3.11` dichiarato ma falso).
- [ ] Documenta in `packages/speclift/VENDORING.md` §"Esito verifica Python 3.11": il costrutto
      trovato, perché è irriducibile, e l'**impatto sul pavimento effettivo del workspace** (il
      pavimento dichiarato di Sertor resta `>=3.11` per gli altri membri; `speclift` diventa
      un'eccezione esplicita, non un abbassamento nascosto del contratto workspace).
- [ ] Ri-esegui `uv sync --all-packages --extra dev` per confermare che la risoluzione resta pulita
      con `speclift` a `>=3.12` mentre gli altri membri restano `>=3.11` (uv risolve al massimo tra
      i vincoli members — verificare che non introduca un innalzamento silenzioso del pavimento
      effettivo per CHI installa il workspace).

---

## Fase 9 — Polish/cross-cutting: verifica trasversale finale (3 task)

> Prerequisiti: tutte le fasi precedenti complete.

### TASK-P01 — Tabella di chiusura CS-1..CS-7 / invarianti I1..I10

→ dipende da: tutte le fasi precedenti · **Mappa**: tutti i CS · contratto workspace-integration
§"Invarianti verificabili"

- [ ] Ripercorri e spunta **ogni** invariante `I1`..`I10` di `contracts/workspace-integration.md` e
      **ogni** criterio `CS-1`..`CS-7` di `spec.md`, uno per uno, con l'evidenza raccolta nelle fasi
      precedenti (nessuna ri-esecuzione necessaria se già verificato sopra — è una checklist di
      chiusura, non un nuovo lavoro).
- [ ] Verifica in particolare **I10** (fail-loud evidenza malformata, TASK-US45-02) e **I3b**
      (nessuna invocazione CLI nel flow, TASK-US12-07) perché sono le due garanzie strutturali più
      delicate della feature (Adapter B senza deroghe).

### TASK-P02 — Lint + sync finali, ripetibilità

→ dipende da: TASK-P01 · **Mappa**: RNF-3 · CS-4/5

```powershell
uv sync --all-packages --extra dev
uv run ruff check .
uv run pytest -m "not cloud and not integration"
uv run pytest packages/sertor/tests packages/sertor-install-kit/tests packages/sertor-flow/tests `
  -m "not cloud and not integration"
uv run pytest packages/speclift/tests -m "not cloud"
```

- [ ] Tutti i comandi sopra sono **verdi** in un singolo passaggio finale (non solo nei task
      individuali) — conferma che l'ordine di esecuzione non ha introdotto stato residuo.

### TASK-P03 — Verifica finale del brief di scope (nessun rinvio sepolto)

→ dipende da: TASK-P01 · **Mappa**: spec.md §"Tracciamento dello scope"

- [ ] Conferma che nessun rinvio reale di questa feature sia rimasto **solo** dentro
      `specs/084-speclift-self-host/`: distribuzione ospiti esterni → **FEAT-002** (backlog epica
      `speclift`, già citata in `requirements/speclift/`); traduzione IT→EN → **E12**; SpecAudit/
      Debrief/Guida al test → **FEAT-003/004/005** (stesso backlog); recepimento feedback CLI→MCP →
      **registrato** (Fase 7, non un debito interno).
- [ ] Se **una qualunque** di queste FEAT non esistesse ancora come riga nel backlog dell'epica
      `speclift` (`requirements/speclift/epic.md` o equivalente), **crearla ora** — non lasciarla
      solo citata in prosa qui.

---

## Nota finale (non un task numerato — rituale di step standing)

A chiusura dell'implementazione: il rituale di step del `CLAUDE.md` di radice (registra → distilla
→ lint semantico → executive summary roadmap → re-index del corpus `sertor` — **ora** che
`packages/speclift/**` esiste e và indicizzato come parte del corpus → smoke test RAG) si applica
come per ogni feature significativa. Non è un task di questo `tasks.md` (è responsabilità del
flusso principale, non della checklist SpecKit), ma **non va saltato**: in particolare il re-index
(`uv run sertor-rag index .`) deve girare **dopo** che `packages/speclift/` è stato aggiunto, così
il RAG di dogfooding può eventualmente restituire anche il codice/doc di SpecLift stesso in
`search_code`/`search_docs` su query pertinenti.

---

## Brief di commit (per `configuration-manager`)

- **Messaggio:** `feat(speclift): vendora SpecLift (Adapter B pluggable, 5ee6fc1) per il self-host (FEAT-001)`
- **Corpo (perché):** Vendoring puro del pacchetto `speclift` da Sinthari `master @ 5ee6fc1`
  (versione pluggable, 122 test) come nuovo membro del workspace `packages/speclift`, per generare
  requisiti EARS ancorati dai changeset reali di Sertor (dogfooding). Il retrieval passa
  esclusivamente dal tool MCP `search_code` orchestrato dall'agente (Adapter B,
  `ProvidedEvidenceLocator`, three-gear flow `changeset → located.json → bundle → assemble`); la
  CLI `sertor-rag` e `import sertor_core` **non** sono mai coinvolti (Adapter A `rag_sertor.py`
  vendorato ma dormiente). Uniche divergenze di packaging: Python `>=3.11` (riconciliato da
  `>=3.12`, verificato empiricamente) e `jsonschema` spostata a dev-only. `sertor_core` invariato.
  Constitution PASS 12/12 + missione PASS (indiretto, dichiarato), nessuna deroga.
- **File da includere:**
  - `packages/speclift/**` (intero pacchetto vendorato: `src/`, `tests/`, `skills/`, `specs/`,
    `pyproject.toml`, `LICENSE`, `VENDORING.md`)
  - `.claude/skills/speclift/SKILL.md` (copia dogfood)
  - `pyproject.toml` (root — solo le 2 righe: `members` + `extend-exclude`)
  - `uv.lock` (rigenerato)
  - `.github/workflows/ci.yml` (step `Tests — speclift` + opzionale `Lint — speclift`)
  - `wiki/sources/input-other-agents/sinthari-reply-speclift-locator-pluggable.md` (aggiornamento
    campo `status`)
  - `wiki/sources/input-other-agents/sertor-confirms-speclift-adapter-b-vendored.md` (nuovo)
  - Eventuali artefatti prodotti dalla verifica e2e (`$env:TEMP\speclift-*`) **non** vanno
    committati (sono in `%TEMP%`, fuori dal repo per costruzione).
- **NON includere:** nessun `.env`/segreto; nessun file sotto `raw/`; nessuna modifica a
  `src/sertor_core/**` (deve restare assente dal diff).
- **Hook SpecKit:** non eseguire `EXECUTE_COMMAND`/hook git.
