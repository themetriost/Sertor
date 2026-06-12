# Research — `sertor install rag`

Fase 0 del plan. Risolve i punti tecnici aperti ancorandoli al codice reale dell'installer sorella
(`packages/sertor/src/sertor_installer/`) e del core. Formato per decisione: **Decisione /
Razionale / Alternative scartate**.

## R1 — Fix di distribuzione: `sertor` standalone deve risolvere `sertor-core` (REQ-260..262)

**Problema.** `packages/sertor/pyproject.toml` dichiara `dependencies = ["sertor-core"]` senza
sorgente; la sorgente `sertor-core = { workspace = true }` è solo nel `pyproject.toml` di **root**.
Installato standalone (`uvx --from "git+url#subdirectory=packages/sertor" sertor`), uv legge il
pyproject del **member** come progetto radice, non scopre il workspace genitore nel checkout git, e
cerca `sertor-core` su PyPI (non pubblicato) → risoluzione fallita.

**Decisione.** Aggiungere al `pyproject.toml` del **member** una sorgente git esplicita per
`sertor-core`:

```toml
[tool.uv.sources]
sertor-core = { git = "https://github.com/themetriost/Sertor.git" }
```

In sviluppo la risoluzione resta governata dal **workspace** (il root dichiara
`[tool.uv.workspace] members=["packages/sertor"]` + `sertor-core = {workspace=true}`): operando dalla
root del monorepo, uv risolve `sertor-core` come membro editable locale. La sorgente git del member
viene consultata **solo** quando `packages/sertor` è il progetto radice senza contesto-workspace
(install standalone da git), che è esattamente il caso `uvx`.

**Validazione (OBBLIGATORIA, esplicitata come task):** il comportamento uv su *member-source vs
workspace-source* è il punto più incerto e va verificato in due modi, entrambi necessari:
1. **Dev non rotto (locale, senza rete):** dopo l'edit, `uv lock` / `uv sync --extra dev` dalla root
   continua a risolvere `sertor-core` dal sorgente locale (workspace), e `uv run pytest` resta verde.
2. **Standalone OK (richiede push):** `uvx` legge il git **remoto**, non il working tree → la
   verifica end-to-end di `uvx --from "git+url#subdirectory=packages/sertor" sertor --help`
   richiede che il fix sia **pushato**. Va eseguita dopo il merge/push, su ambiente pulito.

**Alternative scartate.**
- *Pubblicare `sertor-core` su PyPI:* risolverebbe alla radice ma è esplicitamente **Won't**
  dell'epica (DA-4: distribuzione interim `git+url`); rinviata.
- *Fondere l'installer in `sertor-core` come extra (`sertor-core[install]` + console-script):*
  eliminerebbe il secondo pacchetto e il problema, ma ribalta la decisione D1 di FEAT-012 (pacchetto
  `sertor` distinto, già consegnato) — fuori ambito.
- *Affidarsi alla workspace-discovery di uv dal subdirectory git:* non affidabile (uv tratta il
  subdirectory come radice); è proprio ciò che fallisce oggi.

**Pin della sorgente.** Per l'MVP la sorgente git punta al branch di default (`master`). Un pin a
tag/rev è un irrigidimento successivo (quando ci sarà un tag di release); annotato, non MVP.

> **⚠️ AGGIORNAMENTO EMPIRICO (in implementazione, 2026-06-12).** La decisione sopra è **SMENTITA
> dai fatti**: aggiungere `[tool.uv.sources] sertor-core = { git = … }` al member **rompe il
> workspace di sviluppo** — uv 0.11.12 rifiuta con *"`sertor-core` is included as a workspace member,
> but references a Git in `tool.uv.sources`. Workspace members must be declared as workspace
> sources"*. Un membro del workspace **non può** referenziare una sorgente git per un altro membro.
> Il fix è stato **revocato**; al suo posto una nota in `packages/sertor/pyproject.toml`. **Stato
> reale del "bug":** non è stato riprodotto end-to-end — è possibile che `uvx --from
> "git+url#subdirectory=packages/sertor"` **scopra già il workspace** dal checkout git e risolva
> `sertor-core` localmente (nessun fix necessario), oppure che fallisca (serve un fix diverso, es.
> pubblicare `sertor-core` o ristrutturare). **Determinabile SOLO con un push** (uvx legge il remoto).
> → FR-024 resta **aperto**, validazione differita a T023 post-push. Il resto della feature (il
> comando `install rag`) è **indipendente** da questo e completo.

## R2 — Topologia del runtime `.sertor/` e indicizzazione che esclude sé stessa (FR-006/020, REQ-282)

**Problema.** Il runtime vive in `<target>/.sertor/` con `.env` in `<target>/.sertor/.env`. Il core
legge `.env` dalla **cwd** (python-dotenv) e l'`index_dir` di default è `.index` relativo alla cwd.
I default-excludes del core (`settings.py:_DEFAULT_EXCLUDES`) includono `.venv`, `.index`,
`__pycache__`, `.env` — **ma NON `.sertor`**. Serve una topologia coerente in cui: (a) il `.env` di
`.sertor/` venga caricato; (b) l'indice finisca dentro `.sertor/`; (c) i sorgenti dell'host vengano
indicizzati **escludendo** `.sertor/` stessa.

**Decisione (Topologia "cwd = `.sertor/`").** Tutte le invocazioni del runtime girano con cwd
`<target>/.sertor/` (per il server MCP: `uv run --directory .sertor python -m sertor_mcp.server`;
per l'indicizzazione: `uv run --directory .sertor sertor-rag index ..`). Conseguenze cablate nello
scaffold:
- `.env` in `<target>/.sertor/.env` → caricato (cwd = `.sertor/`).
- L'indice resta in `.sertor/` (`index_dir` default `.index` → `.sertor/.index`); nessuna variabile
  extra necessaria.
- **Esclusione di `.sertor/`:** il `.env` generato imposta `SERTOR_EXCLUDE_PATTERNS` con
  **l'intero set di default + `.sertor`** (il core *sostituisce* i default quando la variabile è
  presente — `settings.py:165` — quindi il template li ri-elenca per non perderli). Indicizzando
  `..` da dentro `.sertor/`, il pattern `.sertor` scarta la dotfolder del runtime.

**Implicazione documentata (quickstart):** il comando d'indicizzazione è
`uv run --directory .sertor sertor-rag index ..` (o lo si lancia col `.mcp.json`/server già cablato).
I path nei risultati sono relativi al root indicizzato (`..` = radice host). Questo è il prezzo
dell'isolamento; accettabile e trasparente.

**Alternative scartate.**
- *cwd = root host, `SERTOR_INDEX_DIR=.sertor/.index`:* metterebbe il `.env` alla radice host
  (contraddice la decisione `.sertor/.env`) e richiederebbe di puntare dotenv altrove (il core non
  espone un flag `--env-file`) → più attrito, rompe l'isolamento.
- *Aggiungere `.sertor` ai default-excludes del core:* tocca il core per un dettaglio dell'installer
  (viola la sottigliezza, Principio I/III); meglio configurarlo via `.env` generato.

**Nota:** nessun bisogno di modificare il core. Tutto si ottiene con cwx + `.env` generato. Se in
futuro si volesse evitare il ri-elenco dei default, sarebbe un'evoluzione del core (additività degli
excludes) — fuori ambito.

## R3 — Confine mockabile attorno a `uv` (NFR-5: testabile senza rete né uv reale)

**Decisione.** Introdurre nel package installer un **runner di comandi esterni** iniettabile: una
funzione/Protocol `CommandRunner` (es. `run(cmd: list[str], cwd: Path) -> CommandResult` con
`returncode`, `stdout`, `stderr`). L'implementazione reale (`SubprocessRunner`) usa
`subprocess.run`; i test iniettano un `FakeCommandRunner` che registra i comandi e restituisce esiti
predefiniti (successo / `uv` assente / `uv add` fallito). Il piano di bootstrap riceve il runner per
iniezione (default = subprocess), coerente con il pattern "composition root sceglie l'impl" del core.

**Razionale.** Mantiene la logica di scaffold/piano testabile senza rete né `uv` reale (FR di
US1/US2 verificabili con fake); isola l'unico side-effect non-deterministico; nessun import pesante.
`shutil.which("uv")` per il pre-check di disponibilità (FR-012) è anch'esso dietro il runner o un
piccolo `tool_available()` mockabile.

**Alternative scartate.** *Chiamare `subprocess` direttamente nei moduli di piano:* non mockabile
senza patchare `subprocess` globalmente (fragile, viola F.I.R.S.T.).

## R4 — Nuovi tipi di artefatto e riuso del backbone (FR-006..023)

**Decisione.** Estendere `ArtifactKind`/`WriteStrategy` (in `artifacts.py`) con i nuovi tipi e
aggiungere un **piano RAG** parallelo a `build_install_plan`/`execute_plan`, riusando
`Artifact`/`ArtifactOutcome`/`InstallReport` invariati:

| Nuovo `ArtifactKind` | `WriteStrategy` | Comportamento | Riusa |
|---|---|---|---|
| `DEPENDENCIES` | `BOOTSTRAP_DEPS` | `uv init --bare` (se manca pyproject in `.sertor/`) + `uv add sertor-core[extras] @ git+url` dentro `.sertor/`, via `CommandRunner` | runner R3 |
| `ENV_MERGE` | `MERGE_ENV` | `.sertor/.env` da template per backend; merge additivo per-chiave, segreti vuoti | template asset |
| `MCP_MERGE` | `MERGE_JSON` | `.mcp.json` in **radice host**; merge additivo del server `sertor-rag` preservando gli altri | pattern `settings_merge.py` |
| `GITIGNORE_APPEND` | `APPEND_LINES` | `.gitignore` in radice; append dedup di `.sertor/.venv/`, `.sertor/.index*`, `.sertor/.env` | nuovo, banale |

**Razionale.** `Artifact` resta un value object con `target_rel` validato (no path-traversal);
`execute_plan` resta fail-fast no-rollback; `InstallReport` (conteggi, exit 0/1, `--json`) invariato
→ coerenza di superficie con `install wiki` (NFR-6). Il dispatch in `execute_plan` aggiunge i nuovi
`kind`. Nota: `.mcp.json`/`.gitignore` hanno `target_rel` in **radice host** (non sotto `.sertor/`):
la validazione di `Artifact` ammette qualsiasi relativo non-risalente — ok.

**Asset nuovi (package-data, via `resources.py`):** `assets/rag/env.azure.tmpl`,
`assets/rag/env.local.tmpl`, `assets/rag/mcp.server.json.tmpl` (frammento del server `sertor-rag`).
Letti con `importlib.resources` come gli asset wiki (funziona da editable e da wheel).

## R5 — Backend → set di extra, e composizione della spec dipendenze (FR-009/REQ-213)

**Decisione.** Mappa pura backend→extra, con opt-out:
- `--backend azure` → `sertor-core[azure,mcp,graph,rerank]`;
- `--backend local` → `sertor-core[mcp,graph,rerank]` (mai `azure`);
- `--no-graph` rimuove `graph`; `--no-rerank` rimuove `rerank`; `mcp` resta sempre.
La stringa risultante alimenta `uv add "<spec> @ git+url"`. Funzione pura `compose_extras(backend,
no_graph, no_rerank) -> list[str]` (testabile senza rete).

## R6 — Sicurezza e install ≠ run (REQ-210/221, Principi IV/VI/IX)

**Decisioni.**
- I template `.env` contengono le chiavi ma **valori segreti vuoti** (`AZURE_OPENAI_API_KEY=`); il
  merge additivo non scrive mai valori segreti né li logga (NFR-4).
- Nessun passo del piano lancia indicizzazione/`sertor-rag index`/embedding (install ≠ run); l'unica
  attività di rete è `uv add` (download pacchetti).
- Fail-fast no-rollback: al primo `ERROR` `execute_plan` si ferma, `InstallReport.failed_step`
  valorizzato; gli artefatti già scritti restano (idempotenza al re-run li troverà e farà
  `skipped`/`merged`).
- Errori di dominio dedicati: `uv` assente → eccezione di dominio leggibile col prerequisito
  (riusa lo stile di `CapabilityNotAvailableError`/`ConfigError`); `uv add` fallito → `ERROR`
  nel report con stderr del tool.

## Riepilogo punti aperti residui per `/speckit-tasks`

- Nessun `NEEDS CLARIFICATION` di scope (tutte le DA chiuse).
- Due **rischi di validazione** (non bloccanti il design, ma task espliciti):
  R1-validazione `uvx` end-to-end (richiede push) e R2 verifica dell'esclusione `.sertor` su un
  re-index reale del dogfood.
