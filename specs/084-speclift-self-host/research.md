# Research — Self-hosting / dogfooding di SpecLift su Sertor (speclift FEAT-001)

**Branch**: `084-speclift-self-host` · **Data**: 2026-07-01 · **Fase**: 0 (Outline & Research)

**Input**: [`spec.md`](./spec.md), [`requirements/speclift/self-host/requirements.md`](../../requirements/speclift/self-host/requirements.md),
[`wiki/sources/input-other-agents/speclift-recon.md`](../../wiki/sources/input-other-agents/speclift-recon.md).

**Metodo di ancoraggio.** I fatti citano `file:riga` (verificati o dal recon). Il codice SpecLift è
letto dal clone Sinthari (`C:/Workspace/Git/ExternalRepos/Sinthari`, `master @ be4da28`). Il codice
Sertor è studiato via il vehicle MCP `sertor-rag` (dogfooding) e `Read`. **Nessun errore MCP**
(`search_code`/`search_docs` hanno risposto — l'unico legame runtime con Sertor resta comunque un
solo comando CLI, come da onestà doc↔codice §G).

---

## Sintesi delle decisioni

| # | Forca | Decisione | Motivo sintetico |
|---|-------|-----------|------------------|
| D-1 | Modalità di vendoring | **Copia versionata one-shot** pinnata a `be4da28` + nota di provenienza | SpecKit launch-installer non applicabile (SpecLift ha runtime proprio); YAGNI vs sync (III) |
| D-2 | `jsonschema` runtime→dev | **Sposta in `[dev]`**; runtime deps `[]` | Verificato test-only (zero import in `src/`); azzera l'impronta runtime (RNF-2) |
| D-3 | Meccanismo vehicle RAG | **(a) patch della costante** `SERTOR_RAG_VEHICLE` nella copia vendorata | Zero-config per il self-host (FR-006), divergenza minima (III), env-var → FEAT-002 |
| D-4 | Versione Python 3.12→3.11 | **Abbassa a `>=3.11`/`py311`**, verifica empirica su 3.11; piano B FR-019 | Nessuna sintassi 3.12-only (grep); `StrEnum` è 3.11+ (`domain/models.py:24`) |
| D-5 | Integrazione lint (ruff) | Root ruff **`extend-exclude += packages/speclift`** (precedente `prototype`); speclift tiene il proprio `[tool.ruff]` | `ruff check .` (gate CI) resta verde senza riformattare il vendorato |
| D-6 | Integrazione test (pytest) | **Modello per-pacchetto** (come gli altri membri) + step CI dedicato `Tests — speclift` | Marker `contract`/`integration` dichiarati nel pyproject di speclift → nessun conflitto |
| D-7 | Licenza / attribuzione | **Aggiungi `LICENSE` MIT** a `packages/speclift`; provenienza registra l'assenza upstream + stessa-org | Convenzione workspace (ogni membro ha LICENSE); Sinthari non ha LICENSE (finding) |
| D-8 | Versione del pacchetto | speclift tiene **`version = "0.1.0"` statica** (upstream), non `dynamic`-da-`/VERSION` | Fedeltà alla provenienza; speclift è dogfood-only, escluso dal test di packaging (FEAT-002) |
| D-9 | Skill dogfood | **Copia fedele** in `.claude/skills/speclift/SKILL.md`; onestà Gruppo H nei doc/wiki, non nella skill | La skill upstream **non** cita `find_symbol`/`who_calls` (già onesta e host-agnostica) |

Nessuna decisione richiede una deroga costituzionale (Complexity Tracking vuoto). La tensione **III↔X**
sul vehicle (D-3) è risolta senza deroga (§D-3).

---

## D-1 — Modalità di vendoring: copia one-shot vs meccanismo di sync

**Decisione:** **copia versionata one-shot**, pinnata al commit `be4da28`, importata sotto
`packages/speclift/` come nuovo membro del workspace, con una **nota di provenienza** esplicita
(`packages/speclift/VENDORING.md`).

**Razionale.**
- Il precedente Sertor più vicino — SpecKit in `sertor-flow` — ha **abbandonato** il vendoring a favore
  di un *launch-installer* (`specify init` a runtime) per evitare la divergenza; ma quel pattern **non
  si applica**: SpecKit distribuisce *template/istruzioni* invocabili da un installer upstream, mentre
  **SpecLift ha codice runtime Python proprio eseguibile** (la CLI `speclift`, la pipeline a 7 stadi).
  Non esiste un "SpecLift upstream" da invocare a install-time senza portarsi dietro l'intero pacchetto.
  Vendoring del sorgente è l'unica via.
- Un **meccanismo di sync** (analogo a `sync.py`/`generate.py` di `sertor-flow`) sarebbe
  **over-engineering** (Principio III / YAGNI): quei sync riallineano asset *dentro* il repo
  (dogfood `.claude/` ↔ `assets/`), non da un upstream esterno; non c'è oggi una cadenza di
  aggiornamento upstream che giustifichi automazione. Un solo vendoring, aggiornamenti futuri manuali
  ed espliciti.
- La **nota di provenienza è il registro** di *da quale stato upstream* la copia deriva **e** di *quali
  divergenze intenzionali* porta (D-2, D-3, D-4, D-7): è ciò che va ri-applicato a ogni eventuale
  re-vendoring (FR-003/REQ-003). Vive in `packages/speclift/VENDORING.md` — leggibile senza lookup
  esterno (FR-002/REQ-002).

**Alternative scartate.**
- *Sync automatico dall'upstream:* respinto per YAGNI + assenza di cadenza upstream (A-005: MVP stabile).
- *git submodule:* respinto — il codice deve essere un membro del workspace `uv` risolvibile e
  ri-configurabile (patch del vehicle, riconciliazione Python), incompatibile con un submodule read-only.

---

## D-2 — `jsonschema`: da dipendenza runtime a dev

**Decisione:** spostare `jsonschema>=4.0` da `dependencies` a `[project.optional-dependencies].dev`;
`dependencies = []` (runtime **stdlib-only**).

**Verifica (ancorata).**
- `grep "import jsonschema|from jsonschema"` su `src/speclift/` → **zero occorrenze** (nessun import
  runtime nascosto).
- In `tests/`: usato **solo** in `tests/contract/conftest.py`, `tests/unit/test_render_json.py`,
  `tests/unit/test_bundle.py` — cioè **solo test di contratto/serializzazione**.
- Conferma il recon (`speclift-recon.md:131-134`): il core è stdlib-only; `git`/`sertor-rag` via
  subprocess.

**Razionale.** Azzerare l'impronta runtime (RNF-2/NFR-2) senza perdere copertura. È una **divergenza
dal `pyproject.toml` upstream** (che dichiara `jsonschema` runtime) → va **documentata** nella nota di
provenienza (FR-005/REQ-008) e verificata (nessun import runtime residuo — sopra). Coerente con
`sertor-install-kit` (runtime deps `[]`, tutto stdlib).

---

## D-3 — Meccanismo di configurazione del vehicle RAG (la tensione III↔X)

**Decisione:** **opzione (a)** — **patchare la costante** del vehicle nella copia vendorata:

```python
# packages/speclift/src/speclift/config.py (DIVERGENZA Sertor-self-host, vedi VENDORING.md)
SERTOR_RAG_VEHICLE = ("uv", "run", "sertor-rag")   # upstream: (…, "--project", ".sertor", …)
```

**Contesto ancorato.** Oggi il vehicle è un default hardcodato di `Config`
(`config.py:27` = `("uv","run","--project",".sertor","sertor-rag")`), esposto come costante
module-level `DEFAULT_CONFIG` (`config.py:55`) e letto dall'entry CLI (`cli.py:23,89,133`);
`SertorRagLocator.__init__` usa `config.sertor_rag_vehicle` (`rag_sertor.py:40`). **Non esiste** oggi
un flag CLI né una variabile d'ambiente di override. Nel repo Sertor il RAG vive a **root**
(`uv run sertor-rag`, entry point `sertor-core` in `pyproject.toml:22`), non in `.sertor/`.

**Perché (a) e non (b)/(c).**
- **(b) env var `SPECLIFT_RAG_VEHICLE` letta da `config.py`** è più host-agnostica e riusabile da un
  ospite futuro — **ma è la generalizzazione di FEAT-002**, dove l'ospite è un consumatore configurabile
  reale. Introdurla ora è **YAGNI** (Principio III): per il self-host non serve variare il vehicle. E,
  soprattutto, **violerebbe FR-006/REQ-009** ("senza flag/env ad-hoc a ogni chiamata"): un env var va
  comunque *impostato* (shell/`.env`), mentre patchare il default rende il self-host **zero-config**
  (funziona invocando `speclift` dalla root).
- **(c) wrapper/composition locale** che costruisce `Config` programmaticamente bypassa l'entry-point
  console `speclift`, cambiando l'esperienza CLI (più invasivo, contro RNF-6 determinismo/superficie).

**Tensione III↔X risolta senza deroga.** Patchare il default *sembra* incorporare un'assunzione
d'ospite (Principio X). Non è così: il vehicle vive **in `config.py`**, cioè nel **locus di
configurazione centralizzata** (Principio VIII), **non** nel corpo della capacità; la **skill resta
host-agnostica** (nessun path/comando Sertor-specifico nel suo corpo — verificato, D-9). Impostare il
*default di configurazione* per **questo** ospite è esattamente ciò che la config è deputata a fare. La
**piena host-configurabilità** (env var / config all'install) è la casa di **FEAT-002**. La divergenza
puntuale è **tracciata** nella nota di provenienza (FR-005) → non è un edit locale non tracciato.

**Interazione con FR-008/REQ-013 (messaggio azionabile — Should).** Il **Must** (FR-007: fail-loud exit
3 + messaggio esplicito) è già soddisfatto **senza modifiche** dall'upstream (`rag_sertor.py:87-99,120-124`
→ `RagUnavailableError` → exit 3, mappato in `cli.py:8-10`). Il **Should** (raccomandare
`sertor-rag index .`) è una **piccola divergenza Sertor-specifica** nel messaggio d'errore vendorato
(`rag_sertor.py`, ai due siti di `RagUnavailableError`), registrata in provenienza insieme al vehicle
(stessa classe: "divergenza self-host"). Non può vivere nella skill (sarebbe un comando Sertor-specifico
in un corpo host-agnostico — D-9).

---

## D-4 — Riconciliazione versione Python 3.12 → 3.11

**Decisione:** abbassare `requires-python = ">=3.11"` e `[tool.ruff] target-version = "py311"` nel
pyproject vendorato; **condizione di accettazione** = la suite gira **verde su un interprete 3.11**
(FR-018/REQ-005). **Piano B** (FR-019/REQ-006): se emergesse un costrutto genuinamente 3.12-only, il pin
**non** si abbassa in silenzio — si dichiara la discrepanza e l'impatto sul pavimento del workspace.

**Perché il pin è probabilmente riducibile.**
- Grep del recon: **nessuna** sintassi 3.12-only (PEP 695 `type X =`/`def f[T]`/`class C[T]`,
  `itertools.batched`).
- Il costrutto "più recente" è `StrEnum` (`domain/models.py:24`, `from enum import StrEnum`) →
  **disponibile da Python 3.11**.

**Perché conta (impatto reale).** Tutti i membri Sertor pinnano `>=3.11`
(`pyproject.toml:6` + `packages/*/pyproject.toml:5`). Un membro `>=3.12` **alza il pavimento effettivo**
di `uv sync --all-packages`: un dev su 3.11 non potrebbe più sincronizzare. La CI oggi **usa 3.12**
(`.github/workflows/ci.yml:33-37` — `uv python install 3.12` + `uv sync … --python 3.12`), quindi la
CI resterebbe verde comunque; ma il **contratto dichiarato** del workspace è `>=3.11` e va preservato.
La verifica empirica su 3.11 è un passo di **plan/tasks** (`uv run --python 3.11 pytest` nel pacchetto),
non di design.

---

## D-5 — Integrazione lint (ruff): differenze di stile

**Decisione:** aggiungere `packages/speclift` all'`extend-exclude` del ruff **di root**
(`pyproject.toml:110`, oggi `["prototype"]`); **speclift tiene il proprio `[tool.ruff]`** nel suo
pyproject (line-length 110, regola `SIM`, `target-version = "py311"` dopo D-4).

**Contesto ancorato.**
- Root ruff: `line-length = 100`, `target-version = "py311"`, `select = ["E","F","I","UP","B"]`
  (**no `SIM`**), `src = [enumera i membri]` (`pyproject.toml:105-119`). Il gate CI è
  `uv run ruff check .` (`ci.yml:39-40`).
- SpecLift upstream: `line-length = 110`, `target-version = "py312"`, `select += "SIM"`
  (`Sinthari/pyproject.toml:37-43`).

**Razionale.** Se `packages/speclift/src` entrasse nel `src` di root, `ruff check .` imporrebbe
100/no-`SIM` sul codice vendorato → riformattazioni (E501) e potenziale rimozione di idiomi `SIM`, cioè
**churn su codice fedele all'upstream**, ri-applicato a ogni re-vendoring. **Escluderlo dal ruff di
root** è **precedentato** (il `prototype` congelato è escluso per la stessa ragione: tenere `ruff check .`
verde sul codice mantenuto senza toccare codice non-di-nostra-cura). Speclift resta lintabile **coi
suoi criteri** (`cd packages/speclift && uv run ruff check`, oppure `uv run ruff check packages/speclift`
che risolve il `[tool.ruff]` annidato). Uno step CI opzionale `Lint — speclift` può essere aggiunto in
tasks; non è richiesto per la verde del gate di root.

**Alternativa scartata.** Riconciliare il codice a 100/py311/no-`SIM`: uniformità a prezzo di
riformattazione del vendorato + divergenza di contenuto ampia da mantenere → respinta (III).

---

## D-6 — Integrazione test (pytest): marker e invocazione

**Decisione:** **modello per-pacchetto**, identico agli altri membri. `packages/speclift/pyproject.toml`
dichiara il **proprio** `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `pythonpath = ["src"]`,
`markers = [contract, integration]`). La suite gira via uno **step CI dedicato**
`Tests — speclift`: `uv run pytest packages/speclift/tests -m "not cloud"` (nessun marker `cloud` in
speclift → gira tutto, incl. gli e2e su git-fixture locali). **Nessuna modifica al pytest di root.**

**Perché non c'è conflitto di marker (R-5).** Il pytest di root dichiara `cloud`/`integration`
(`pyproject.toml:130-133`) e `testpaths = ["tests"]` → **non colleziona** `packages/speclift/tests`.
Quando la CI invoca `uv run pytest packages/speclift/tests`, pytest risale dall'argomento e trova
**`packages/speclift/pyproject.toml`** come inifile (nearest con `[tool.pytest.ini_options]`) → usa i
marker di speclift → **nessun warning di marker sconosciuto**. È **esattamente** il modello con cui
girano oggi `sertor`/`sertor-install-kit`/`sertor-flow` (`ci.yml:49-56`, step separati per-pacchetto,
conteggi distinti "sertor 292 · kit 131 · flow 134").

**Conseguenza su FR-011/US5.** "Gira in `uv run pytest` nel workspace **accanto** alle altre suite" = lo
**stesso modello di invocazione** dei membri esistenti (uno step per pacchetto), non un unico comando
magico che collezioni tutto da root. I 104 test girano nell'infrastruttura CI del workspace, verdi,
senza toccare le altre suite (RNF-3).

**Struttura suite (ancorata).** `tests/{contract,integration,unit}` (28 file):
contract (2, usano `jsonschema` via `conftest.py`), integration (5, e2e su git-fixture locale
`_gitfixture.py` — **offline**), unit (18). Gli integration sono **offline-safe** (git locale) → gireranno
in CI senza rete.

---

## D-7 — Licenza e attribuzione (finding)

**Finding (segnalato, non sepolto — Principio XII).** Il repo **Sinthari NON ha un file `LICENSE`** a
`be4da28` (`glob LICENSE*` → nessun file). Vendorare codice di terzi senza licenza è ambiguo.

**Mitigante di contesto.** Sinthari (`github.com/themetriost/Sinthari`) è della **stessa
organizzazione** di Sertor (`github.com/themetriost/Sertor`, cfr. `sertor-flow/pyproject.toml:21`):
è un **handoff first-party**, non codice di terzi acquisito, e l'handoff stesso è l'autorizzazione.

**Decisione.**
- Aggiungere `packages/speclift/LICENSE` = **MIT** (Sertor), coerente con **tutti** i membri del
  workspace (`license = "MIT"` + `license-files = ["LICENSE"]` in `sertor-core`/`sertor-flow`/
  `sertor-install-kit`) e col precedente di attribuzione vendoring (sertor-flow bundla SpecKit con
  NOTICE + MIT, REQ-025 — `wiki/tech/sertor-flow.md#11`).
- La **nota di provenienza registra**: repo upstream, commit `be4da28`, versione `0.1.0`, data,
  **assenza di LICENSE upstream al momento del vendoring**, natura **stessa-org** dell'handoff. È un
  finding da confermare col proprietario upstream, ma la natura first-party ne consente il proseguimento.

---

## D-8 — Versione del pacchetto e test di packaging

**Decisione:** speclift tiene la **versione statica `0.1.0`** (upstream), **non** `dynamic`-da-`../../VERSION`
come gli altri membri. È **escluso dal test di packaging distribuibile** (`tests/integration/test_packaging.py`,
`@integration`, saltato nel job CI principale) perché **non è un artefatto distribuito** (distribuzione =
**FEAT-002**).

**Razionale.** La versione statica preserva la provenienza (0.1.0 = stato vendorato) ed evita di
accoppiare speclift al ciclo di versione del monorepo prima che sia distribuito. Coincidenza utile:
`/VERSION` di root è anch'esso `0.1.0` oggi. Se una futura distribuzione lo richiederà, il passaggio a
`dynamic`-da-`/VERSION` sarà una decisione di **FEAT-002**.

---

## D-9 — Skill dogfood e onestà Gruppo H

**Decisione:** depositare `.claude/skills/speclift/SKILL.md` come **copia fedele** della skill upstream
(`Sinthari/skills/speclift/SKILL.md`), che è **già host-agnostica** e **già onesta**.

**Verifica (ancorata).** La skill upstream **non** cita `find_symbol`/`who_calls`/code-graph: invoca solo
`speclift bundle`/`assemble` e dice "se il progetto la espone via un runner, es. `uv run speclift …`"
(`SKILL.md:31`). Nessun path `.claude/`/`.github/`, nessuno slash-command, nessun nome-modello →
host-agnostica (FR-010/REQ-011). **La correzione di onestà del Gruppo H NON riguarda la skill**: la
discrepanza doc↔codice (l'handoff/wiki Sinthari attribuiscono a SpecLift il code-graph MCP che il codice
non usa — `rag_sertor.py:4-7`, `speclift-recon.md:109-116`) vive nella **documentazione derivata** (questo
`research.md` §sotto, il `plan.md`, e la pagina wiki di distillazione). FR-016/REQ-019 è soddisfatto qui e
nei doc, non modificando la skill.

**Sorgente e copia dogfood.** Il sorgente vendorato fedele vive in
`packages/speclift/skills/speclift/SKILL.md`; la **copia dogfood** in `.claude/skills/speclift/SKILL.md`
è ciò che l'agente ospite scopre. La sincronizzazione tra le due è **manuale/one-shot** (coerente con
D-1); una guardia di sync bundlato↔dogfood è **territorio di FEAT-002** (dove vive la macchina
installer/asset), non di questa feature.

### Dichiarazione di onestà doc↔codice (Gruppo H, FR-016/REQ-019)

> **Il legame runtime reale di SpecLift con Sertor è un SOLO comando CLI:**
> `sertor-rag search --type code --json -k 5` (via subprocess, `cwd=repo`), in
> `adapters/rag_sertor.py:86`. **NON** usa i tool MCP di navigazione del code-graph
> (`find_symbol`/`who_calls`/`get_context`/`search_docs`) che l'handoff e la wiki Sinthari
> (`speclift-handoff.md:52-54`, `concepts/speclift.md:64`) descrivono. La docstring dell'adapter lo
> dichiara esplicitamente (`rag_sertor.py:4-7`). Nessun agente del dogfood deve aspettarsi da SpecLift
> una navigazione del code-graph: la localizzazione è **solo** `search --type code`; la verifica delle
> àncore è **deterministica sul filesystem** (`anchor_fs.py:26-62`), non via RAG. La discrepanza si
> **dichiara** lato Sertor, non si corregge a monte (fuori ambito).

---

## Compatibilità del contratto RAG (verifica dell'assunzione A-004)

**Verificato (MCP `search_code` + `Read`).** `sertor-rag search` accetta `query`, `-k`,
`--type {code,doc,both}`, `--json` (`src/sertor_core/cli/__main__.py:124-131`). Con `--json --type code`
l'output è un **array piatto** di dict con `path`, `doc_type`, `chunk_id`, `score`, `preview`
(`cli/output.py:95-109`). SpecLift legge `path` e `chunk_id` (`rag_sertor.py:50-58,66-72`) → **combacia**.
Il breaking change di `--type both` (feature 070, `{"docs":[…],"code":[…]}`) **non** impatta `--type code`
(resta array piatto — confermato da `tests/unit/test_cli_search.py`). Il legame è **stabile**.

---

## Note di processo e ambiente

- `.specify/scripts/powershell/setup-plan.ps1` e `.claude/skills/speckit-plan/SKILL.md` **ASSENTI** →
  parametri per convenzione dal branch `084-speclift-self-host` (forma dai plan `074`–`083`). Nessun
  hook SpecKit eseguito. Git **non** eseguito (delega a `configuration-manager`).
- MCP `sertor-rag` interrogato (`search_code` sull'output CLI, `search_docs` sul precedente vendoring):
  **nessun errore tool**.
- Il resto dei fatti è ancorato via `Read`/`Glob`/`Grep` sul clone Sinthari e sul repo Sertor.
