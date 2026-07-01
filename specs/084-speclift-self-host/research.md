# Research — Self-hosting / dogfooding di SpecLift su Sertor (speclift FEAT-001)

**Branch**: `084-speclift-self-host` · **Data**: 2026-07-01 · **Fase**: 0 (Outline & Research)

> **Rigenerata dopo che Sinthari ha recepito il nostro feedback.** Upstream ha mergiato su `master`
> (`5ee6fc1`, PR #7) una versione **PLUGGABLE** dell'`EvidenceLocator`: al posto del nostro «swap del
> locator» (design inventato — `AgentEvidenceLocator`, `--candidates-out`/`--evidence`, `EvidenceInputError`
> exit 6) **adottiamo il loro codice reale**. La feature diventa **vendoring PURO** (zero fork del
> codice runtime). La vecchia D-3 («swap») è **superata** e sostituita da una nuova D-3 («adozione
> dell'Adapter B pluggable»).

**Input**: [`spec.md`](./spec.md), [`requirements/speclift/self-host/requirements.md`](../../requirements/speclift/self-host/requirements.md),
[`wiki/sources/input-other-agents/speclift-recon-pluggable.md`](../../wiki/sources/input-other-agents/speclift-recon-pluggable.md) (fonte primaria del flow reale),
[`wiki/sources/input-other-agents/speclift-recon.md`](../../wiki/sources/input-other-agents/speclift-recon.md) (feasibility/packaging).

**Metodo di ancoraggio.** I fatti citano `file:riga` del clone Sinthari
`C:/Workspace/Git/ExternalRepos/Sinthari` **`master @ 5ee6fc1`** (`git rev-parse HEAD` verificato). Il
codice Sertor è studiato via il vehicle **MCP** `sertor-rag` (dogfooding, `search_code` — **nessun errore
tool**) e `Read`. Nessun hook SpecKit eseguito; git non eseguito.

---

## Sintesi delle decisioni

| # | Forca | Decisione | Motivo sintetico |
|---|-------|-----------|------------------|
| D-1 | Modalità di vendoring | **Copia versionata one-shot** pinnata a `5ee6fc1` + `VENDORING.md` | SpecKit launch-installer non applicabile (SpecLift ha runtime proprio); YAGNI vs sync (III) |
| D-2 | `jsonschema` runtime→dev | **Sposta in `[dev]`**; runtime deps `[]` | Verificato test-only (import solo in `tests/`); azzera l'impronta runtime (RNF-2) |
| **D-3** | **Meccanismo di localizzazione via MCP** | **Adozione dell'Adapter B pluggable upstream** (`ProvidedEvidenceLocator` + three-gear flow); **entrambi** gli adapter restano; niente swap, niente codice nostro | Upstream ha recepito il feedback → vendoring puro; il dogfood usa l'Adapter B; moat/porta/exit-code loro |
| D-4 | Versione Python 3.12→3.11 | **Abbassa a `>=3.11`/`py311`**, verifica empirica su 3.11; piano B FR-020 | Nessuna sintassi 3.12-only (grep); `StrEnum` è 3.11+ (`domain/models.py:24`) |
| D-5 | Integrazione lint (ruff) | Root ruff **`extend-exclude += packages/speclift`** (precedente `prototype`); speclift tiene il proprio `[tool.ruff]` | `ruff check .` (gate CI) resta verde senza riformattare il vendorato |
| D-6 | Integrazione test (pytest) | **Modello per-pacchetto** + step CI dedicato `Tests — speclift` | Marker `contract`/`integration` nel pyproject di speclift → nessun conflitto col root; suite **completa** (~122) |
| D-7 | Licenza / attribuzione | **Aggiungi `LICENSE` MIT** a `packages/speclift`; provenienza registra l'assenza upstream + stessa-org | Convenzione workspace; Sinthari non ha LICENSE a `5ee6fc1` (finding verificato) |
| D-8 | Versione del pacchetto | speclift tiene **`version = "0.1.0"` statica**, escluso dal test di packaging distribuibile | Fedeltà alla provenienza; dogfood-only (distribuzione = FEAT-002) |
| D-9 | Skill dogfood | **Copia verbatim** in `.claude/skills/speclift/SKILL.md`: upstream ha già Procedura A/B host-agnostica; il dogfood usa la **Procedura B** | La skill upstream contiene già la localizzazione via tool MCP — nulla da estendere |

Nessuna decisione richiede una **deroga costituzionale** (Complexity Tracking vuoto). La **deviazione dal
sandwich** (l'agente tocca 2 stadi con l'Adapter B) è ora una **scelta upstream dichiarata**
(`evidence-locator-port.md:41-46`), non una nostra estensione — vedi D-3/§Constitution Check del plan.

---

## D-1 — Modalità di vendoring: copia one-shot vs sync

**Decisione:** **copia versionata one-shot**, pinnata a **`5ee6fc1`**, importata sotto
`packages/speclift/` come nuovo membro del workspace, con nota di provenienza
`packages/speclift/VENDORING.md`.

**Razionale.**
- Il precedente Sertor più vicino — SpecKit in `sertor-flow` — ha **abbandonato** il vendoring a favore
  di un *launch-installer* (`specify init` a runtime); ma quel pattern **non si applica**: SpecKit
  distribuisce *template/istruzioni*, mentre **SpecLift ha codice runtime Python proprio** (la CLI, la
  pipeline a 7 stadi). Vendoring del sorgente è l'unica via.
- Un **meccanismo di sync** sarebbe **YAGNI** (III): A-005 dà un MVP stabile senza cadenza di
  aggiornamenti.
- **Vendoring PURO (novità rispetto al design precedente):** adottando la versione pluggable upstream,
  la copia di `src/**` è **verbatim** — non modifichiamo alcun file di runtime. Le divergenze di
  `VENDORING.md` sono **solo di packaging** (D-2/D-4/D-7 + integrazione workspace), non di codice: il
  re-vendoring futuro è **più economico** che nel design «swap» (che toccava 5+ file di codice), perché
  convergiamo con l'upstream (ottimo per DRY/manutenzione, Principio III).

**Alternative scartate.** *Sync automatico* (YAGNI + no cadenza upstream). *git submodule* (serve
comunque un `pyproject.toml`/`LICENSE`/`VENDORING.md` propri + le divergenze di packaging D-2/D-4 →
incompatibile con un submodule read-only, e nasconderebbe la provenienza al lettore del repo).

---

## D-2 — `jsonschema`: da dipendenza runtime a dev

**Decisione:** spostare `jsonschema>=4.0` da `dependencies` a `[project.optional-dependencies].dev`;
`dependencies = []` (runtime **stdlib-only**).

**Verifica (ancorata a `5ee6fc1`).** `grep -rln jsonschema src tests` → import **solo** in
`tests/contract/conftest.py`, `tests/unit/test_bundle.py`, `tests/unit/test_render_json.py` (test di
contratto/serializzazione), **zero** in `src/speclift/`. Conferma il recon
(`speclift-recon.md:131-134`).

**Razionale.** Azzera l'impronta runtime (RNF-2) senza perdere copertura. **Divergenza dal
`pyproject.toml` upstream** → documentata in `VENDORING.md` e verificata (nessun import runtime residuo).
Coerente con `sertor-install-kit` (runtime deps `[]`). È una divergenza di *packaging*, non di codice.

---

## D-3 — Adozione dell'Adapter B pluggable upstream (LA forca centrale, riscritta)

**Decisione:** **adottare tale-e-quale** la versione pluggable mergiata da Sinthari (`5ee6fc1`).
Concretamente:
1. **Vendorare entrambi gli adapter** dietro la porta `EvidenceLocator`: `SertorRagLocator`
   (`adapters/rag_sertor.py`, Adapter A, CLI-vehicle) **e** `ProvidedEvidenceLocator`
   (`adapters/provided_locator.py`, Adapter B, agente+MCP). **Non rimuovere `rag_sertor.py`** (era il
   nostro fork; ora convergiamo): resta **dormiente** nel nostro uso.
2. **Il self-host usa l'Adapter B** tramite il **three-gear flow reale**: `speclift changeset <ref>
   --out` (candidati) → l'agente localizza coi tool MCP e scrive `located.json` → `speclift bundle
   --changeset … --located …` → `assemble`.
3. **Adottare l'interfaccia reale**: `located.json` con `symbols` chiavati `"<file_path>::<query>"` e
   `tests` chiavati per nome-simbolo; `domain/query_keys.build_identifier_queries` (G6 condivisa); exit
   code upstream (malformato → **5**, flag-misuse → **2**, chiave assente → `[]` onesto). **Nessun**
   `EvidenceInputError`/exit 6 nostro.

### Cosa cambia rispetto al design «swap» (superato)

| Nostro plan 084 precedente (inventato) | Upstream reale `5ee6fc1` — adottato |
|---|---|
| **Swap:** rimuovi `rag_sertor.py`, aggiungi `AgentEvidenceLocator` | **Pluggable:** `rag_sertor.py` **resta**; `ProvidedEvidenceLocator` presente; entrambi dietro la porta |
| Flag `bundle --candidates-out cand.json` | Comando separato **`speclift changeset <ref> --out`** (marcia 0) |
| Flag `bundle --evidence evidence.json` | **`bundle --changeset … --located …`** (alternativo a `<ref>`) |
| `evidence.json`: `symbols` per `file_path` + `changeset_ref` top-level | `located.json`: `symbols` per **`"<file_path>::<query>"`**, **senza** `changeset_ref` |
| candidati: forma ad-hoc | changeset completo via `changeset_to_dict`: hunk con `candidate_identifiers` **e** `lines` |
| Nuovo `EvidenceInputError` (**exit 6**), validazione al `__init__` | **Nessun** errore nuovo: malformato → **exit 5** upstream; flag-misuse → **exit 2** |
| G6 duplicata | **`domain/query_keys.py`** condiviso dai due adapter |
| `pipeline`: `emit_candidates()` + swap `default_components` | `pipeline`: `build_changeset()` + `build_bundle_from_changeset()` (seam upstream) |
| `contracts/agent-evidence-interface.md` (nostro) | `contracts/evidence-locator-port.md` (loro) — **riferito**, non reinventato |

**Conseguenza:** la nostra intera modifica al codice vendorato **sparisce**. Il vendoring diventa puro
(§D-1) — è la manifestazione del Principio III (minima divergenza, convergenza con upstream).

### Contesto ancorato (chi tocca cosa, `5ee6fc1`)

- **La porta** `EvidenceLocator` (`domain/ports.py`) ha due metodi: `locate_symbols(file_path,
  identifiers, snippet) -> list[Symbol]`, `locate_tests(symbol) -> list[TestRef]`. Strutturale
  (`Protocol`) → i due adapter la soddisfano senza ereditarietà.
- **`ProvidedEvidenceLocator`** (`provided_locator.py:25-52`): `__init__(payload, *, config)` legge
  `payload["symbols"]`/`["tests"]`, **nessuna validazione al costruttore** (chiave assente → `[]`,
  `:14-15`); `locate_symbols` deriva le query con `build_identifier_queries` (G6) e fa lookup su
  `_key(file_path, query) = f"{file_path}::{query}"`; `locate_tests` fa lookup per `symbol.name`. Riusa
  i modelli `Symbol`/`TestRef` via `_symbol_from`/`_test_from` (`:55-72`).
- **Il seam della pipeline** (`pipeline.py`): `build_changeset(options, diff_source)` (ingest→parse→
  filtro, **no locator**, `:117-142`) + `build_bundle_from_changeset(changeset, locator)` (locate→bundle,
  `:145-158`). `default_components` (`:43-55`) costruisce **`SertorRagLocator`** (Adapter A) — il default
  upstream. **`build_bundle_from_changeset` accetta qualunque `EvidenceLocator`** → passandogli un
  `ProvidedEvidenceLocator` si ottiene lo stesso bundle.
- **La CLI** (`cli.py`): `speclift changeset` (`_cmd_changeset`, `:119-168`) usa **solo** `.diff_source`
  da `default_components` (il locator è costruito ma **inerte** — non invocato). `speclift bundle
  --changeset --located` (`_cmd_bundle`, `:213-230`) costruisce `ProvidedEvidenceLocator(located_payload)`
  e chiama `build_bundle_from_changeset` — **non passa** da `default_components` → `SertorRagLocator` non
  è nemmeno istanziato in questo ramo.
- **Lo stadio `locate_evidence`** (`stages/locate_evidence.py`) è **invariato**: chiama solo la porta.
- **Precedente di test del flow B**: `tests/integration/test_three_gear_flow.py` (3 test) esercita
  changeset→located(scritto a mano)→bundle→assemble su git-fixture locale, con un `_UnusedLocator` che
  **fallisce rumoroso** se la marcia 0 tocca il locator (`:30-37`) — **offline**, nessun RAG.

### Come garantiamo l'Adapter B (no CLI) nel dogfood — Principio XI

Tre garanzie sovrapposte (dettaglio in `contracts/evidence-locator-port.md`):
1. **Procedurale:** la skill dogfood seleziona la **Procedura B** (l'host Sertor espone i tool MCP, non
   una CLI-vehicle `sertor-rag` invocabile da subprocess).
2. **Strutturale:** il code path del flow B (`changeset` + `bundle --changeset --located`) costruisce
   `ProvidedEvidenceLocator` e **non invoca mai** `SertorRagLocator.locate_*` — l'unico punto in cui
   l'Adapter A spawnerebbe il subprocess `sertor-rag`. Il monolitico `speclift <ref>` e `bundle <ref>`
   (Adapter A) semplicemente **non si usano**.
3. **Verificabile (tripwire):** il flow B non spawna alcun `sertor-rag`; e la root di Sertor non ha un
   progetto `.sertor/`, quindi un uso erroneo dell'Adapter A fallirebbe *loud* (`RagUnavailableError`,
   exit 3), mai in silenzio.

Il retrieval passa dunque dal tool **MCP `search_code`** (vehicle legittimo per gli agenti), **mai** dalla
CLI `sertor-rag`, **mai** da `import sertor_core`, **mai** da un SDK MCP nel codice (l'MCP è nell'agente).

### Dove vive il fail-loud MCP/indice (REQ-012)

**Nella skill/agente, non nel codice deterministico.** Poiché nel flow B SpecLift non tocca il RAG, il
fallimento «MCP/indice giù» emerge quando l'**agente** esegue `search_code` e riceve un errore: la skill
(Procedura B) istruisce l'agente a **fermarsi e segnalare** (componente + rimedio `sertor-rag index .`),
mai a proseguire con evidenza parziale/fabbricata (FR-009). Questo è coerente con l'upstream: nel flow B
non c'è più l'exit 3 nel codice (quello è dell'Adapter A). L'evidenza **malformata** cade invece nell'exit
**5** upstream (`cli.py:227-229`) — fail-loud nel codice (FR-010), **senza** il nostro exit 6.

---

## D-4 — Riconciliazione versione Python 3.12 → 3.11

**Decisione:** abbassare `requires-python = ">=3.11"` e `[tool.ruff] target-version = "py311"` nel
pyproject vendorato; **condizione di accettazione** = suite verde su un interprete **3.11** (FR-019).
**Piano B** (FR-020): costrutto genuinamente 3.12-only → il pin **non** si abbassa in silenzio, si
dichiara la discrepanza e l'impatto sul pavimento del workspace.

**Perché è probabilmente riducibile.** Grep del recon: **nessuna** sintassi 3.12-only (PEP 695,
`itertools.batched`). Il costrutto «più recente» è `StrEnum` (`domain/models.py:24`) → **3.11+**.

**Perché conta.** Tutti i membri Sertor pinnano `>=3.11`. Un membro `>=3.12` **alza il pavimento
effettivo** di `uv sync --all-packages`. La CI usa 3.12 (`ci.yml:33-37`) → resterebbe verde comunque, ma
il **contratto dichiarato** `>=3.11` va preservato. La verifica su 3.11 è un passo di **tasks**
(`uv run --python 3.11 pytest`), non di design. È una divergenza di *packaging*, non di codice — il grep
negativo rende improbabile un edit di codice.

---

## D-5 — Integrazione lint (ruff)

**Decisione:** `packages/speclift` nell'`extend-exclude` del ruff di **root** (oggi `["prototype"]`);
speclift tiene il proprio `[tool.ruff]` (line-length 110, `select += SIM`, `target-version = "py311"`
dopo D-4).

**Contesto.** Root ruff: 100 / py311 / `select E,F,I,UP,B` (**no `SIM`**), `src = [membri]`; gate CI =
`ruff check .` (`ci.yml:39-40`). SpecLift upstream: 110 / py312 / `select += SIM`.

**Razionale.** Se `packages/speclift/src` entrasse nel `src` di root, `ruff check .` imporrebbe
100/no-`SIM` sul vendorato → churn su codice fedele all'upstream, ri-applicato a ogni re-vendoring.
**Escluderlo è precedentato** (`prototype` congelato). Con il **vendoring puro** questo è ancora più
netto: non introduciamo **alcun** file nuovo sotto `packages/speclift/src` da lintare col nostro stile.
Step CI opzionale `Lint — speclift` in tasks.

---

## D-6 — Integrazione test (pytest)

**Decisione:** **modello per-pacchetto**. `packages/speclift/pyproject.toml` dichiara il proprio
`[tool.pytest.ini_options]` (`testpaths=["tests"]`, `pythonpath=["src"]`, `markers=[contract,
integration]`). Step CI dedicato `Tests — speclift`: `uv run pytest packages/speclift/tests -m "not
cloud"`. **Nessuna** modifica al pytest di root.

**Perché nessun conflitto.** Il pytest di root ha `testpaths=["tests"]` → **non** colleziona
`packages/speclift/tests`. Invocando `uv run pytest packages/speclift/tests`, pytest risale all'inifile
`packages/speclift/pyproject.toml` → usa i marker di speclift → nessun warning. È il modello con cui
girano già `sertor`/`sertor-install-kit`/`sertor-flow` (`ci.yml:49-56`).

**Conteggio suite (ancorato a `5ee6fc1`, vendoring PURO).** `grep -rc "def test" tests` = **~123**
funzioni (il commit pluggable dichiara **122** verdi; la differenza sono conteggi di helper/parametrize).
Con il vendoring puro **non c'è delta**: si copiano **tutti** i test, inclusi `test_provided_locator.py`
(8), `test_query_keys.py` (5), `test_three_gear_flow.py` (3) — **nuovi** dell'Adapter B — **e**
`test_rag_sertor.py` (8, Adapter A, runner mockato offline). Esito richiesto = **suite completa verde**.
Il numero esatto va verificato a implement; FR-011 va letto sulla **suite completa** (~122), non sui 104
letterali dell'handoff originale.

**Struttura (ancorata).** `tests/{contract(2 file, 8 test), integration(6 file, ~17 test), unit(19
file, ~98 test)}`. Integration **offline** (git-fixture locale `_gitfixture.py`) → gira in CI senza rete.
Gli integration e2e (`test_e2e_us1`, `test_two_gear_flow`, `test_three_gear_flow`) usano
`FakeLocator`/`_UnusedLocator`/`ProvidedEvidenceLocator` alimentati da dati inline → **non** invocano il
RAG. `test_rag_sertor.py` usa un runner mockato → offline, resta verde senza rete.

---

## D-7 — Licenza e attribuzione (finding, Principio XII)

**Finding (segnalato, non sepolto).** Il repo **Sinthari NON ha `LICENSE`** a `5ee6fc1` (`ls LICENSE*` →
`NO LICENSE FILE`, verificato). Vendorare codice senza licenza è ambiguo.

**Mitigante.** Sinthari (`github.com/themetriost/Sinthari`) è della **stessa organizzazione** di Sertor
(`github.com/themetriost/Sertor`): handoff **first-party**, non codice di terzi — l'handoff è
l'autorizzazione. Di più: `5ee6fc1` è la **risposta upstream al nostro feedback** (recepimento), segno
di collaborazione attiva.

**Decisione.** Aggiungere `packages/speclift/LICENSE` = **MIT** (coerente con tutti i membri +
precedente NOTICE/MIT del vendoring SpecKit). `VENDORING.md` registra: repo, commit `5ee6fc1`, versione
`0.1.0`, data, **assenza LICENSE upstream** al vendoring, natura **stessa-org**. Finding da confermare
col proprietario upstream; la natura first-party ne consente il proseguimento.

---

## D-8 — Versione del pacchetto e test di packaging

**Decisione:** speclift tiene **`version = "0.1.0"` statica** (upstream), **non** `dynamic`-da-`/VERSION`.
**Escluso** dal test di packaging distribuibile (`tests/integration/test_packaging.py`, `@integration`)
perché **non distribuito** (distribuzione = FEAT-002).

**Razionale.** La versione statica preserva la provenienza; evita di accoppiare speclift al ciclo di
versione del monorepo prima della distribuzione. (Coincidenza: `/VERSION` di root è anch'esso `0.1.0`.)

---

## D-9 — Skill dogfood (copia verbatim, upstream ha già Procedura A/B)

**Decisione:** depositare `.claude/skills/speclift/SKILL.md` come **copia verbatim** della skill upstream
`5ee6fc1`. **Non estendiamo nulla:** upstream ha già scritto la **Procedura B** (agente + tool MCP) come
risposta al nostro feedback. Il dogfood di Sertor usa la Procedura B.

**Verifica (ancorata a `5ee6fc1`).** La skill upstream (`skills/speclift/SKILL.md`) ora ha **due
procedure** con selezione a monte (`:34-43`): **Procedura A** (CLI-vehicle, default) e **Procedura B**
(agente + tool MCP `search_code`/`find_symbol`/`who_calls`, per host senza CLI-vehicle — il caso del
dogfooding di Sertor). La Procedura B (`:128-181`): (1) `speclift changeset <ref> --out`; (2) «Localizza
TU, coi tuoi tool MCP» con la regola G6, scrivendo `located.json`; (3) `speclift bundle --changeset …
--located …`, poi prosegue con autoring+assemble di Procedura A.

**Host-agnosticità nella FORMA vs targeting Sertor nel CONTENUTO (Principio X — dichiarato con onestà).**
La skill upstream è **già host-agnostica** (verificato: nessun path `.claude/`/`.github/`, nessuno
slash-command, nessun nome-modello — `evidence-locator-port.md:79-80` lo dichiara esplicitamente). I passi
della Procedura B **nominano** i tool MCP di Sertor (`search_code`/…): è un tool **di Sertor**, non un
dettaglio del progetto *ospite* — Principio X vieta di presumere l'**ospite**, non di nominare i **vehicle
di Sertor** (il framework che si consuma). Il corpo resta host-agnostico nella **forma** e Sertor-targeted
nel **contenuto** del retrieval — inevitabile e corretto. La generalizzazione host-facing (installer,
IT→EN) è **FEAT-002/E12**. **Nota:** la scelta A vs B è già host-agnostica upstream (la skill sceglie in
base a cosa l'host espone), quindi il deposito è distribuibile anche fuori dal dogfood senza modifiche.

**Fail-loud nella skill (REQ-012).** La Procedura B istruisce già: se `search_code` erra (MCP/indice giù),
**fermati e segnala** (componente + rimedio), mai proseguire con evidenza fabbricata.

### Dichiarazione di onestà doc↔codice (Gruppo H — FR-016/REQ-019)

> **Il legame runtime del self-host con Sertor = il tool MCP `search_code`**, orchestrato dall'agente
> nella skill (Procedura B). A differenza del design precedente, **non è più una divergenza dal codice
> vendorato**: l'Adapter B è **prima classe upstream** (`5ee6fc1`), e la skill upstream **nomina già** il
> retrieval MCP. Il self-host **adotta** il percorso che Sinthari ha reso di prima classe **in risposta al
> nostro feedback**. Resta un **gap più piccolo e spostato**: `search_code` è **ricerca semantica**, non
> **navigazione del code-graph** (`find_symbol`/`who_calls`/`get_context`); la skill nomina anche i tool di
> navigazione, ma il dogfood può realisticamente usare la sola `search_code` — la verifica delle àncore
> resta **deterministica sul filesystem** (`anchor_fs.py`), mai via RAG. **FR-017 (feedback a Sinthari) è
> di fatto già chiuso**: il commit `5ee6fc1` **è** il recepimento del nostro feedback CLI→MCP; resta da
> registrare una voce di *ringraziamento/conferma dell'adozione* su `input-other-agents` (non più un
> feedback di divergenza da aprire).

---

## Compatibilità del contratto MCP (verifica dell'assunzione A-004)

**Verificato (MCP `search_code`, nessun errore tool).** Il tool `search_code` del server `sertor-rag`
risponde con un array di hit (il server istruisce di citare `path#chunk`) — sufficiente a mappare
`Symbol` (`path` reale, `chunk` → `provenance`) e a giudicare i test (path `test_*`/`/tests/`). Il gap
noto (A-004): il server MCP espone anche `find_symbol`/`who_calls` (navigazione code-graph), che il
dogfood può usare o meno; l'onestà del Gruppo H copre entrambi i casi.

---

## Note di processo e ambiente

- `.specify/scripts/powershell/setup-plan.ps1` e `.claude/skills/speckit-plan/SKILL.md` **ASSENTI** →
  parametri per convenzione dal branch `084-speclift-self-host` (forma dai plan `074`–`083`). Nessun hook
  SpecKit eseguito. Git **non** eseguito (delega a `configuration-manager`).
- MCP `sertor-rag` interrogato in apertura (`search_code`): **nessun errore tool**.
- Il codice SpecLift è ancorato al clone Sinthari **`5ee6fc1`** (`git rev-parse HEAD` verificato) via
  `Read`/`Glob`/`Grep`; il codice Sertor via MCP + `Read`.
