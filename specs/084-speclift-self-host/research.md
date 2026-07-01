# Research — Self-hosting / dogfooding di SpecLift su Sertor (speclift FEAT-001)

**Branch**: `084-speclift-self-host` · **Data**: 2026-07-01 · **Fase**: 0 (Outline & Research)

> **Rigenerata dopo il cambio di decisione del proprietario: retrieval via il server MCP dentro una
> skill, NON via la CLI `sertor-rag`.** La vecchia D-3 («meccanismo di configurazione del vehicle CLI»)
> è **SUPERATA** e sostituita da una nuova D-3 (forma dell'interfaccia evidenza agente→SpecLift +
> esclusione fisica di `rag_sertor.py`). Il resto delle decisioni resta valido, riadattato.

**Input**: [`spec.md`](./spec.md), [`requirements/speclift/self-host/requirements.md`](../../requirements/speclift/self-host/requirements.md),
[`wiki/sources/input-other-agents/speclift-recon.md`](../../wiki/sources/input-other-agents/speclift-recon.md).

**Metodo di ancoraggio.** I fatti citano `file:riga` (verificati sul clone Sinthari
`C:/Workspace/Git/ExternalRepos/Sinthari`, `master @ be4da28`, o dal recon). Il codice Sertor è studiato
via il vehicle **MCP** `sertor-rag` (dogfooding, `search_code` — **nessun errore tool**, output = array
piatto `path`/`doc_type`/`chunk_id` confermato) e `Read`. Nessun hook SpecKit eseguito; git non eseguito.

---

## Sintesi delle decisioni

| # | Forca | Decisione | Motivo sintetico |
|---|-------|-----------|------------------|
| D-1 | Modalità di vendoring | **Copia versionata one-shot** pinnata a `be4da28` + `VENDORING.md` | SpecKit launch-installer non applicabile (SpecLift ha runtime proprio); YAGNI vs sync (III) |
| D-2 | `jsonschema` runtime→dev | **Sposta in `[dev]`**; runtime deps `[]` | Verificato test-only (import solo in `tests/`); azzera l'impronta runtime (RNF-2) |
| **D-3** | **Interfaccia evidenza agente→SpecLift + esclusione `rag_sertor.py`** | **Swap del solo locator:** rimuovi `rag_sertor.py`, aggiungi `AgentEvidenceLocator` (file-reader, forma `Symbol`/`TestRef`); candidati out via `bundle --candidates-out`, evidenza in via `bundle --evidence` | Retrieval via MCP nella skill (REQ-008); porta **alimentata** (REQ-009); zero schema nuovo; moat invariato |
| D-4 | Versione Python 3.12→3.11 | **Abbassa a `>=3.11`/`py311`**, verifica empirica su 3.11; piano B FR-020 | Nessuna sintassi 3.12-only (grep); `StrEnum` è 3.11+ (`domain/models.py:24`) |
| D-5 | Integrazione lint (ruff) | Root ruff **`extend-exclude += packages/speclift`** (precedente `prototype`); speclift tiene il proprio `[tool.ruff]` | `ruff check .` (gate CI) resta verde senza riformattare il vendorato |
| D-6 | Integrazione test (pytest) | **Modello per-pacchetto** + step CI dedicato `Tests — speclift` | Marker `contract`/`integration` nel pyproject di speclift → nessun conflitto col root |
| D-7 | Licenza / attribuzione | **Aggiungi `LICENSE` MIT** a `packages/speclift`; provenienza registra l'assenza upstream + stessa-org | Convenzione workspace; Sinthari non ha LICENSE (finding verificato) |
| D-8 | Versione del pacchetto | speclift tiene **`version = "0.1.0"` statica**, escluso dal test di packaging distribuibile | Fedeltà alla provenienza; dogfood-only (distribuzione = FEAT-002) |
| D-9 | Skill dogfood | **Copia + estensione** in `.claude/skills/speclift/SKILL.md`: aggiunge l'orchestrazione del retrieval via MCP `search_code` (assente upstream) | La skill upstream è già host-agnostica; il self-host le aggiunge i passi candidati→localizza→evidenza |

Nessuna decisione richiede una **deroga costituzionale** (Complexity Tracking vuoto). La **deviazione dal
sandwich** (l'agente tocca 2 stadi) è una **nota di design dichiarata**, non una deroga (§D-3, RNF-6).

---

## D-1 — Modalità di vendoring: copia one-shot vs sync

**Decisione:** **copia versionata one-shot**, pinnata a `be4da28`, importata sotto `packages/speclift/`
come nuovo membro del workspace, con nota di provenienza `packages/speclift/VENDORING.md`.

**Razionale.**
- Il precedente Sertor più vicino — SpecKit in `sertor-flow` — ha **abbandonato** il vendoring a favore
  di un *launch-installer* (`specify init` a runtime); ma quel pattern **non si applica**: SpecKit
  distribuisce *template/istruzioni*, mentre **SpecLift ha codice runtime Python proprio** (la CLI, la
  pipeline a 7 stadi). Non esiste un "SpecLift upstream" invocabile a install-time senza portare l'intero
  pacchetto. Vendoring del sorgente è l'unica via.
- Un **meccanismo di sync** sarebbe **YAGNI** (III): i sync di `sertor-flow` riallineano asset *dentro*
  il repo, non da un upstream esterno; A-005 dà un MVP stabile senza cadenza di aggiornamenti.
- La **nota di provenienza è il registro** di *da quale stato upstream* la copia deriva **e** di *quali
  divergenze intenzionali* porta (D-2/D-3/D-4/D-7): è ciò che va ri-applicato a ogni re-vendoring
  (FR-003). **Nota (interazione con D-3):** il design MCP aumenta le divergenze vendorate (più file
  toccati che nel design CLI, che patchava una sola costante) → il re-vendoring è più costoso, ma **tutte**
  le divergenze sono elencate in `VENDORING.md` (nessuna silente).

**Alternative scartate.** *Sync automatico* (YAGNI + no cadenza upstream). *git submodule* (il codice va
modificato — rimozione `rag_sertor.py`, riconciliazione Python — incompatibile con un submodule read-only).

---

## D-2 — `jsonschema`: da dipendenza runtime a dev

**Decisione:** spostare `jsonschema>=4.0` da `dependencies` a `[project.optional-dependencies].dev`;
`dependencies = []` (runtime **stdlib-only**).

**Verifica (ancorata).** `grep jsonschema src tests` → import **solo** in `tests/contract/conftest.py`,
`tests/unit/test_bundle.py`, `tests/unit/test_render_json.py` (test di contratto/serializzazione), **zero**
in `src/speclift/`. Conferma il recon (`speclift-recon.md:131-134`).

**Razionale.** Azzera l'impronta runtime (RNF-2) senza perdere copertura. **Divergenza dal `pyproject.toml`
upstream** → documentata in `VENDORING.md` e verificata (nessun import runtime residuo). Coerente con
`sertor-install-kit` (runtime deps `[]`).

---

## D-3 — Interfaccia evidenza agente→SpecLift ed esclusione fisica di `rag_sertor.py` (LA forca centrale)

**Decisione (swap del solo locator — ports&adapters).**
1. **Rimuovere fisicamente** `adapters/rag_sertor.py` (l'adapter CLI `SertorRagLocator`) dalla copia
   vendorata, e con esso il costrutto di config morto `SERTOR_RAG_VEHICLE`/`Config.sertor_rag_vehicle`.
2. **Aggiungere** `adapters/agent_evidence.py` con `AgentEvidenceLocator`, che implementa la porta
   `EvidenceLocator` leggendo un **artefatto JSON prodotto dall'agente** (evidenza già localizzata via
   MCP `search_code`), invece di eseguire query live.
3. **Candidati in uscita** da `parse_diff` via `speclift bundle <ref> --candidates-out <PATH>`; **evidenza
   in ingresso** via `speclift bundle <ref> --evidence <PATH>`. Forma esatta = contratto
   `contracts/agent-evidence-interface.md`.

### Contesto ancorato (chi tocca cosa)

- **La porta** `EvidenceLocator` (`domain/ports.py:31-41`) ha due metodi:
  `locate_symbols(file_path, identifiers, snippet) -> list[Symbol]` e
  `locate_tests(symbol) -> list[TestRef]`. È **strutturale** (`@runtime_checkable Protocol`) → un nuovo
  adapter la soddisfa senza ereditarietà.
- **Chi importa `rag_sertor.py`** (grep verificato): **solo** `pipeline.py:48,52` (`default_components`
  costruisce `SertorRagLocator`) e `tests/unit/test_rag_sertor.py` (8 test dell'adapter). `config.py:27,48`
  **definisce** il vehicle ma nessun altro lo consuma. → Escludere il file richiede: (a) rewire
  `default_components`; (b) rimuovere `test_rag_sertor.py`; (c) togliere il vehicle morto da `config.py`.
  **Nessun altro punto** del dominio/stadi tocca il RAG (`locate_evidence.py` chiama solo la **porta**).
- **Lo stadio `locate_evidence`** (`stages/locate_evidence.py`) è **invariante**: chiama
  `locator.locate_symbols(...)`/`locate_tests(...)` sulla porta astratta. Sostituire l'implementazione
  concreta (RAG→file-reader) **non lo tocca**.
- **Il precedente «alimentato»**: `FakeLocator` in `tests/unit/test_locate_evidence.py:9-20` implementa la
  porta restituendo dati precostituiti (`self._symbols.get(file_path, [])`, `self._tests.get(name, [])`).
  L'`AgentEvidenceLocator` di produzione **ricalca esattamente** questa forma, leggendo i dati da un file
  invece che cablati in un test → i **8 test di `locate_evidence` restano verdi** con l'adapter reale.

### Forma dell'interfaccia (le due sotto-decisioni di DA-D-3)

**(a) Forma dell'artefatto di evidenza = riuso di `Symbol`/`TestRef`, JSON.** Raccomandazione della spec
accolta: un JSON con `symbols` chiavati per `file_path` (lista di `Symbol`) e `tests` chiavati per nome
simbolo (lista di `TestRef`), **identico** alla forma del `FakeLocator`. Riusa la de-serializzazione
esistente `serialize._symbol_from`/`_test_from` (`serialize.py:130-149`) → **zero schema nuovo** da
inventare. Vive come file temporaneo accanto agli altri artefatti del sandwich (es.
`<TMP>/speclift-evidence-input.json`). *Scartato:* un formato più grezzo che un adapter traduce → aggiunge
vocabolario senza guadagno (i modelli di dominio già bastano).

**Come escono i candidati (l'altro lato dell'interfaccia).** L'agente deve sapere **cosa** localizzare: gli
identificatori candidati per file/hunk (`Hunk.candidate_identifiers`, popolati da `parse_diff`). Serve un
**emit deterministico** — l'agente **non** deve re-derivarli (duplicherebbe `parse_diff`, contro DRY/III).
Decisione: un flag `--candidates-out <PATH>` su `speclift bundle` che esegue `ingest → parse_diff →
filter_sources` e serializza la *localization request* (contratto, Lato 1), poi si ferma **prima** di
`locate`. Richiede una piccola funzione additiva in `pipeline.py` (`emit_candidates`, riusa gli stadi
esistenti) + un serializzatore (`changeset_to_candidates_dict`). **Scartato** il sotto-caso «`bundle`
senza `--evidence` emette i candidati» (mode-switch implicito sull'assenza del flag): output ambiguo,
contro «esplicita e ispezionabile» (REQ-009). Due flag espliciti sono più chiari.

**(b) Esclusione fisica vs vendorato-ma-morto.** Raccomandazione della spec accolta: **escludere
fisicamente** `rag_sertor.py`. Un ospite/manutentore che ispeziona `packages/speclift` **non** deve
trovare codice morto che finge d'essere usato (coerente con Principio XII e con la pulizia del contesto
reso al lettore). La rimozione impone il rewire di `default_components` (sopra), che è **necessario e
tracciato** in `VENDORING.md`.

### Superficie CLI risultante (a due marce preservata + un flag)

- `speclift bundle <ref> --candidates-out cand.json` → *localization request* (marcia 1a, deterministica,
  non tocca il RAG, funziona a indice assente — RNF-4).
- `speclift bundle <ref> --evidence evidence.json [--out bundle.json]` → *evidence bundle* (marcia 1b:
  `AgentEvidenceLocator` iniettato, `locate_evidence` invariato → `bundle`).
- `speclift bundle <ref>` (nessuno dei due) → **fail-loud usage** che nomina entrambi i flag (il RAG-locator
  è rimosso → non c'è più un default che localizzi da sé). Nessun silenzio.
- `speclift assemble …` → **invariato** (lift → verify[moat] → render).

Le due marce `bundle`/`assemble` restano; il retrieval è delegato all'agente **tra** i due passi di
`bundle`. È la manifestazione strutturale della **deviazione dal sandwich** (l'agente tocca 2 stadi).

### Fail-loud sull'evidenza malformata (nuovo modo di fallire)

Nuovo errore di dominio **`EvidenceInputError(SpecLiftError)`** con **`exit_code = 6`** (i codici 1–5 sono
occupati, `domain/errors.py`). `AgentEvidenceLocator.__init__` valida l'artefatto all'ingresso (file
assente/illeggibile → exit 6; chiavi/tipi non conformi via `_symbol_from`/`_test_from` → exit 6), **mai**
ripiegando su evidenza vuota o àncora fabbricata (FR-010/REQ-013, Principio XII). È il guasto «più subdolo»
del design MCP (R-3): non c'è più un unico comando CLI che fallisce in modo osservabile → si valida forte.

### Dove vive il fail-loud MCP/indice (REQ-012)

**Nella skill/agente, non nel codice deterministico.** Poiché SpecLift non tocca più il RAG, il fallimento
«MCP/indice giù» emerge quando l'**agente** esegue `search_code` e riceve un errore: la skill istruisce
l'agente a **fermarsi e segnalare** (nominando il componente + rimedio `sertor-rag index .`), mai a
proseguire con evidenza parziale/fabbricata. Questo **sposta** un fail-loud che l'upstream aveva nel
codice (exit 3) verso la skill — conseguenza diretta del design, dichiarata (FR-009).

### Perché questa forma, e non alternative

- *Adapter che shella la CLI (upstream)*: **respinto** dalla decisione del proprietario — l'MCP è il
  contratto d'integrazione per gli agenti, la CLI è consumatore interno (REQ-E1).
- *Porta che esegue query MCP live da sé*: **impossibile/indesiderato** — il core deterministico non deve
  chiamare un LLM/tool agente (confine D↔N, RNF-6); l'evidenza la produce l'agente e la *consegna*.
- *Riuso di `Symbol`/`TestRef`*: massimizza la fedeltà upstream (`locate_evidence` invariato, test verdi)
  e minimizza il vocabolario nuovo (III).

---

## D-4 — Riconciliazione versione Python 3.12 → 3.11

**Decisione:** abbassare `requires-python = ">=3.11"` e `[tool.ruff] target-version = "py311"` nel pyproject
vendorato; **condizione di accettazione** = suite verde su un interprete **3.11** (FR-019). **Piano B**
(FR-020): costrutto genuinamente 3.12-only → il pin **non** si abbassa in silenzio, si dichiara la
discrepanza e l'impatto sul pavimento del workspace.

**Perché è probabilmente riducibile.** Grep del recon: **nessuna** sintassi 3.12-only (PEP 695,
`itertools.batched`). Il costrutto «più recente» è `StrEnum` (`domain/models.py:24`) → **3.11+**.

**Perché conta.** Tutti i membri Sertor pinnano `>=3.11` (`pyproject.toml:6` + membri). Un membro `>=3.12`
**alza il pavimento effettivo** di `uv sync --all-packages`. La CI usa 3.12 (`ci.yml:33-37`) → resterebbe
verde comunque, ma il **contratto dichiarato** `>=3.11` va preservato. La verifica su 3.11 è un passo di
**tasks** (`uv run --python 3.11 pytest`), non di design.

---

## D-5 — Integrazione lint (ruff)

**Decisione:** `packages/speclift` nell'`extend-exclude` del ruff di **root** (`pyproject.toml:110`, oggi
`["prototype"]`); speclift tiene il proprio `[tool.ruff]` (line-length 110, `select += SIM`,
`target-version = "py311"` dopo D-4).

**Contesto.** Root ruff: 100 / py311 / `select E,F,I,UP,B` (**no `SIM`**), `src = [membri]`; gate CI =
`ruff check .` (`ci.yml:39-40`). SpecLift upstream: 110 / py312 / `select += SIM`
(`Sinthari/pyproject.toml:37-43`).

**Razionale.** Se `packages/speclift/src` entrasse nel `src` di root, `ruff check .` imporrebbe 100/no-`SIM`
sul vendorato → churn su codice fedele all'upstream, ri-applicato a ogni re-vendoring. **Escluderlo è
precedentato** (`prototype` congelato). Speclift resta lintabile coi suoi criteri
(`ruff check packages/speclift`). Step CI opzionale `Lint — speclift` in tasks. **Nota:** i file *nuovi*
di questa feature (`agent_evidence.py`, `test_agent_evidence.py`, patch `cli.py`/`pipeline.py`) vivono
sotto `packages/speclift` → seguono lo stile speclift (110/SIM), non quello di root.

---

## D-6 — Integrazione test (pytest)

**Decisione:** **modello per-pacchetto**. `packages/speclift/pyproject.toml` dichiara il proprio
`[tool.pytest.ini_options]` (`testpaths=["tests"]`, `pythonpath=["src"]`, `markers=[contract,
integration]`). Step CI dedicato `Tests — speclift`: `uv run pytest packages/speclift/tests -m "not cloud"`.
**Nessuna** modifica al pytest di root.

**Perché nessun conflitto (R-5).** Il pytest di root ha `testpaths=["tests"]` → **non** colleziona
`packages/speclift/tests`. Invocando `uv run pytest packages/speclift/tests`, pytest risale all'inifile
`packages/speclift/pyproject.toml` → usa i marker di speclift → nessun warning. È il modello con cui
girano già `sertor`/`sertor-install-kit`/`sertor-flow` (`ci.yml:49-56`).

**Conteggio suite (ancorato, con la divergenza D-3).** Upstream: **106** test collezionati
(`grep -rc "def test" tests` → 106; l'handoff cita ~104). Con D-3: **−8** (`test_rag_sertor.py` rimosso col
suo adapter) **+N** (`test_agent_evidence.py` nuovo: costruzione da file valido, dedup per-file, fail-loud
su file assente/malformato, contratto con `locate_evidence`). Esito richiesto = **suite netta verde**; il
numero esatto va verificato a implement e la divergenza (−test RAG / +test evidenza) registrata in
`VENDORING.md`. FR-011 va letto sul **netto** post-swap, non sui 104 letterali.

**Struttura (ancorata).** `tests/{contract(2),integration(5),unit(19→ −test_rag_sertor +test_agent_evidence)}`.
Integration **offline** (git-fixture locale `_gitfixture.py`) → gira in CI senza rete. Gli integration e2e
(`test_e2e_us1`, `test_two_gear_flow`) usano un `FakeLocator`/componenti iniettati → **non** invocano il
RAG e restano validi (verificare che nessuno importi `rag_sertor` — grep confermato: solo `test_rag_sertor`).

---

## D-7 — Licenza e attribuzione (finding, Principio XII)

**Finding (segnalato, non sepolto).** Il repo **Sinthari NON ha `LICENSE`** a `be4da28` (`ls LICENSE*` →
nessun file). Vendorare codice senza licenza è ambiguo.

**Mitigante.** Sinthari (`github.com/themetriost/Sinthari`) è della **stessa organizzazione** di Sertor
(`github.com/themetriost/Sertor`, cfr. `sertor-flow/pyproject.toml`): handoff **first-party**, non codice
di terzi — l'handoff è l'autorizzazione.

**Decisione.** Aggiungere `packages/speclift/LICENSE` = **MIT** (coerente con tutti i membri +
precedente NOTICE/MIT del vendoring SpecKit). `VENDORING.md` registra: repo, commit `be4da28`, versione
`0.1.0`, data, **assenza LICENSE upstream** al vendoring, natura **stessa-org**. Finding da confermare col
proprietario upstream; la natura first-party ne consente il proseguimento.

---

## D-8 — Versione del pacchetto e test di packaging

**Decisione:** speclift tiene **`version = "0.1.0"` statica** (upstream), **non** `dynamic`-da-`/VERSION`.
**Escluso** dal test di packaging distribuibile (`tests/integration/test_packaging.py`, `@integration`)
perché **non distribuito** (distribuzione = FEAT-002).

**Razionale.** La versione statica preserva la provenienza; evita di accoppiare speclift al ciclo di
versione del monorepo prima della distribuzione. (Coincidenza: `/VERSION` di root è anch'esso `0.1.0`.)

---

## D-9 — Skill dogfood ed estensione dell'orchestrazione del retrieval

**Decisione:** depositare `.claude/skills/speclift/SKILL.md` come copia della skill upstream **estesa** per
il self-host: aggiunge i passi «emetti candidati → localizza via MCP `search_code` → scrivi l'evidenza →
`bundle --evidence`» **prima** dei passi upstream (autoring EARS → assemble).

**Verifica (ancorata).** La skill upstream (`Sinthari/skills/speclift/SKILL.md`) è **già host-agnostica**
(nessun path `.claude/`/`.github/`, nessuno slash-command, nessun nome-modello — `SKILL.md` verificata) e
**già onesta** (non cita `find_symbol`/`who_calls`). MA l'upstream esegue la localizzazione **dentro la
CLI** (`speclift bundle` chiama `SertorRagLocator`): non c'è nulla da orchestrare per l'agente. Il self-host
**sposta** la localizzazione all'agente → la skill **deve** guadagnare i nuovi passi (assenti upstream).

**Host-agnosticità nella FORMA vs targeting Sertor nel CONTENUTO (Principio X — dichiarato con onestà).** I
nuovi passi nominano il tool MCP **`search_code`**: è un tool **di Sertor**, non un dettaglio del progetto
*ospite*. Il corpo resta host-agnostico nella **forma** (nessun path-assistente, nessuno slash-command,
nessun nome-modello: `search_code` è un tool MCP invocabile allo stesso modo su ogni assistente); è
**Sertor-targeted** nel **contenuto** del retrieval — ed è **inevitabile e corretto**: la capacità
*localizza l'evidenza tramite il retrieval di Sertor*, quindi nominarne il tool non è «presumere l'ospite»
(Principio X vieta di presumere il progetto **ospite**, non di nominare i **vehicle di Sertor**, che sono il
framework che si sta consumando). La generalizzazione host-facing (installer, IT→EN) è **FEAT-002/E12**.

**Fail-loud nella skill (REQ-012).** I nuovi passi istruiscono: se `search_code` erra (MCP/indice giù),
**fermati e segnala** (componente + rimedio `sertor-rag index .`), mai proseguire con evidenza fabbricata.
È l'unico posto dove quel fail-loud vive ora (SpecLift non tocca più il RAG).

### Dichiarazione di onestà doc↔codice (Gruppo H, INVERTITO — FR-016/REQ-019)

> **Il legame runtime del self-host con Sertor = il tool MCP `search_code`**, orchestrato dall'agente nella
> skill — in **divergenza intenzionale** dal **codice vendorato/upstream Sinthari**, che raggiunge Sertor
> **solo** via la CLI `sertor-rag search --type code --json` (`adapters/rag_sertor.py:86`, ora **rimosso**
> dalla copia). Questa adozione **avvicina** il self-host alla narrativa upstream (handoff/wiki Sinthari
> parlano di integrazione MCP) ma **non la realizza del tutto**: `search_code` è **ricerca semantica**, non
> **navigazione del code-graph** (`find_symbol`/`who_calls`/`get_context`) — resta un gap doc↔meccanismo
> **più piccolo e spostato**. Nessun agente del dogfood deve aspettarsi navigazione del grafo; la verifica
> delle àncore resta **deterministica sul filesystem** (`anchor_fs.py:26-62`), mai via RAG. La divergenza
> dal codice vendorato è **registrata come feedback a Sinthari** su `wiki/sources/input-other-agents/`
> (FR-017/REQ-020), per un'eventuale convergenza upstream verso il retrieval MCP.

---

## Compatibilità del contratto MCP (verifica dell'assunzione A-004)

**Verificato (MCP `search_code`, nessun errore tool).** Il tool `search_code` del server `sertor-rag`
risponde con un array di hit `{path, source, chunk, score, preview}` (il server istruisce di citare
`path#chunk`) — sufficiente a mappare `Symbol` (`path` reale, `chunk` → `provenance`) e a giudicare i test
(path `test_*`/`/tests/`). La CLI `sertor-rag search --type code --json` (`cli/__main__.py:124-131`,
`cli/output.py:95-109`) resta un vehicle valido ma **non usato** dal self-host. Il gap noto (A-004): il
server MCP espone `find_symbol`/`who_calls` (navigazione code-graph), **ma il self-host usa solo
`search_code`** (ricerca semantica) — coerente con l'onestà del Gruppo H, non una navigazione del grafo.

---

## Note di processo e ambiente

- `.specify/scripts/powershell/setup-plan.ps1` e `.claude/skills/speckit-plan/SKILL.md` **ASSENTI** →
  parametri per convenzione dal branch `084-speclift-self-host` (forma dai plan `074`–`083`). Nessun hook
  SpecKit eseguito. Git **non** eseguito (delega a `configuration-manager`).
- MCP `sertor-rag` interrogato (`search_code` sull'output CLI + shape degli hit): **nessun errore tool**.
- Il codice SpecLift è ancorato al clone Sinthari `be4da28` via `Read`/`Glob`/`Grep`; il codice Sertor via
  MCP + `Read`.
