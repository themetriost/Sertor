# Requisiti — CLI: installer `sertor install rag`
<!-- Deriva da: FEAT-002 (Installazione selettiva delle capacità del core su un repo target) -->
<!-- STATO: IN ELABORAZIONE — branch 015-sertor-install-rag. Taglio "rag" dell'installer, sorella di
     `sertor install wiki` (CONSEGNATA, requirements/sertor-cli/installer/, specs/012, PR #22). -->
<!-- Revisione 2026-06-12: prima stesura. Scope deciso dall'utente = "B bootstrap completo"
     (scaffold config + aggiunta dipendenze Python al target). -->

> **Nota di scope (DA-8 epica §9).** `sertor` è riservato all'installazione/setup; l'**esecuzione**
> del RAG vive nel console-script del core `sertor-rag` (`index`/`search`, già su master, feature
> `esecuzione`). Questa feature **non** esegue RAG: installa e configura ciò che serve perché
> l'utente poi lanci `sertor-rag index` con un comando esplicito.

---

## 1. Contesto e problema (perché)

Portare la **capacità RAG** del core su un progetto qualunque oggi richiede una sequenza di passi
manuali che presuppongono la conoscenza degli *internals* di Sertor (verificato in sessione,
2026-06-12, tentando l'installazione su un repo ospite reale):

1. trasformare il target in progetto `uv` (`uv init` se manca il `pyproject.toml`);
2. aggiungere la dipendenza con gli extra giusti (`uv add "sertor-core[azure,mcp,graph] @ git+url"`);
3. scrivere a mano un `.env` con le variabili del backend scelto;
4. scrivere a mano un `.mcp.json` per esporre il server `sertor-rag` al client (Claude Code);
5. aggiornare `.gitignore` per non versionare `.env` e l'indice.

Inoltre `sertor install rag` **oggi è uno stub**: `__main__.py` dichiara il sub-parser `rag` e
`_dispatch` solleva `CapabilityNotAvailableError` (`packages/sertor/src/sertor_installer/__main__.py:51,83`).

A monte di tutto c'è un **bug di distribuzione** che blocca persino l'esecuzione dell'installer
via `uvx`/standalone: il pacchetto `sertor` dipende da `sertor-core`, risolto in sviluppo come
`{ workspace = true }` (`pyproject.toml` root, `[tool.uv.sources]`); installato **standalone** da
`git+url` quella sorgente non esiste e `uv` cerca `sertor-core` su PyPI (non pubblicato) → la
risoluzione **fallisce**. Senza il fix, né `uvx … sertor install wiki` né `… install rag` partono.

**Obiettivo dichiarato dall'utente:** installare la capacità RAG **senza doversi preoccupare degli
internals** — idealmente un solo comando (`uvx --from "git+url" sertor install rag`) lascia il
progetto pronto a `sertor-rag index`.

*Ancora al repo (in `master` / branch corrente):*
- Pattern dell'installer da rispecchiare: `Artifact(kind, source, target_rel, strategy)` +
  `WriteStrategy` (`CREATE_IF_ABSENT`/`MERGE_DEDUP`/`APPEND_BLOCK`/`GENERATE_CONFIG`/`INIT_STRUCTURE`)
  + `Outcome` (`CREATED`/`SKIPPED`/`MERGED`/`BLOCK`/`ERROR`); orchestrazione `build_install_plan` →
  `execute_plan` (fail-fast, no rollback) → `InstallReport` (conteggi + exit 0/1, resa umana e
  `--json`). Vedi `install_wiki.py`, `report.py`, `config_gen.py`, `__main__.py`.
- `HostProfile` + euristica `source_dirs` (`config_gen.py`): l'unico punto in cui l'installer
  "guarda" l'ospite.
- Variabili di config del core (fonte di verità per il `.env`): `RAG_BACKEND`, `SERTOR_STORE_BACKEND`,
  `AZURE_OPENAI_ENDPOINT`/`_API_KEY`/`_EMBED_DEPLOYMENT`, `OLLAMA_HOST`, `SERTOR_CORPUS`,
  `SERTOR_ENGINE`, `SERTOR_GRAPH`, `SERTOR_INDEX_DIR` (vedi `docs/install.md` e `config/Settings`).
- Extra disponibili nel core (`pyproject.toml` root): `azure`, `mcp`, `rerank`, `graph`.
- Forma del `.mcp.json` di riferimento (server `sertor-rag` via `python -m sertor_mcp.server`):
  `docs/install.md` §4.

## 2. Obiettivi e criteri di successo

- **OB-1 — Un comando, capacità RAG pronta.** Dopo `sertor install rag` su un target, l'utente può
  lanciare `sertor-rag index .` senza ulteriori passi manuali di setup.
  - *SC-1 (misurabile):* su un repo target **senza** `pyproject.toml`, un'unica invocazione
    `uvx --from "git+url" sertor install rag --backend azure` lascia il progetto in uno stato in cui
    `uv run sertor-rag --help` funziona e `.env`/`.mcp.json`/`.gitignore` sono presenti e coerenti.
- **OB-2 — Install ≠ run.** L'installazione **non** avvia mai indicizzazione/ingestione.
  - *SC-2:* in 0 esecuzioni di `install rag` viene creato o popolato un indice/collezione; l'unica
    operazione di rete ammessa è il download dei pacchetti da parte di `uv`.
- **OB-3 — Non distruttività e idempotenza.** Nessun file utente sovrascritto silenziosamente; la
  riesecuzione converge allo stesso stato senza duplicati.
  - *SC-3:* due esecuzioni consecutive sullo stesso target producono lo **stesso** stato finale
    (file e contenuti) e zero duplicati in `.env`/`.mcp.json`/`.gitignore`; tutti gli esiti della
    seconda passata sono `skipped`/`merged` (nessun `created` che sovrascrive).
- **OB-4 — Segreti mai versionati.** Le chiavi segrete non vengono mai scritte con valore.
  - *SC-4:* il `.env` generato contiene le chiavi segrete (`*_API_KEY`) **vuote**; `.gitignore`
    include `.env` prima che l'utente possa committarlo.
- **OB-5 — uvx sbloccato.** L'installer è eseguibile standalone (`uvx`/`pip install` da `git+url`)
  senza che la risoluzione di `sertor-core` fallisca.
  - *SC-5:* `uvx --from "git+url#subdirectory=packages/sertor" sertor --help` ritorna 0 da una
    macchina pulita; la suite `uv run pytest` del workspace resta verde (risoluzione dev intatta).
- **OB-6 — Backend a scelta.** Supporta almeno un backend cloud (default) e l'opzione locale.
  - *SC-6:* `--backend azure` e `--backend local` generano ciascuno un `.env` con l'insieme di
    chiavi corretto per quel backend.

## 3. Stakeholder e attori

- **Owner/maintainer (utente):** installa la capacità RAG su un altro proprio repo via Claude Code.
- **Repository target:** progetto nuovo o esistente, Python o anche non-Python (vedi DA-1).
- **Client MCP (Claude Code):** consumatore del `.mcp.json` generato.
- **`sertor-core` (dipendenza a monte):** fornisce libreria, `sertor-rag`, server MCP ed extra.
- **`uv` (strumento esterno):** usato per il bootstrap delle dipendenze.

## 4. Ambito

### In ambito
- Implementazione del sottocomando `sertor install rag` (rimozione dello stub).
- **Scaffold dei file di config** sul target: `.env` (template per backend), `.mcp.json` (server
  `sertor-rag`), `.gitignore` (append di `.env`, `.index*`).
- **Bootstrap delle dipendenze** Python sul target via `uv`: `uv init --bare` se manca il
  `pyproject.toml`, poi `uv add` di `sertor-core` con gli extra derivati da backend/flag.
- **Selezione del backend e degli extra via flag** (no wizard interattivo).
- **Fix del `pyproject.toml`** del pacchetto `sertor` per la risoluzione standalone di `sertor-core`.
- Report per artefatto + exit code, rispecchiando `install wiki`.

### Fuori ambito
- **Esecuzione del RAG** (`index`/`search`): è `sertor-rag`, già consegnato (REQ-E2).
- **Wizard interattivo** di configurazione (FEAT-003, rinviato): qui solo flag.
- **`install governance`** (taglio separato) e l'evoluzione `install wiki`.
- **Superfici per assistenti diversi da Claude Code** (Copilot/Codex `.vscode/mcp.json`,
  `copilot-instructions.md`, …): è FEAT-007 dell'epica (distribuzione multi-assistente).
- **Pubblicazione su PyPI** (Won't dell'epica); il fix di distribuzione non deve precluderla.
- **Localizzazione** degli eventuali testi (tema lingua, tracciato altrove).

### Decisione di collocazione — runtime isolato in `.sertor/` (DA-1 risolta, 2026-06-12)

Il runtime del RAG vive in una **dotfolder isolata** `<target>/.sertor/` (pattern `.specify/` di
SpecKit, `.claude/`), separata dai sorgenti dell'host: vi stanno il **progetto Python**
(`pyproject.toml`, `uv.lock`, `.venv/`), l'**indice**/code-graph e il **`.env`**. Restano in
**radice host** solo ciò che i client devono vedere: il **`.mcp.json`** (ponte — lancia il server
con `uv run --directory .sertor …`) e — per il **wiki**, file `.md` tecnologicamente agnostici e
documentazione del progetto (DA-7) — `.claude/`, il blocco rituale nel `CLAUDE.md` e la cartella
`wiki/`. Il RAG indicizza i sorgenti host **escludendo** `.sertor/`. Conseguenza: i sorgenti
dell'host **non vengono "pythonizzati"**; disinstallare ≈ cancellare `.sertor/` (+ la voce in
`.mcp.json`). Lo **stesso ambiente** `.sertor/` fa girare sia `sertor-rag` sia `sertor-wiki-tools`.

## 5. Requisiti funzionali (EARS)

### Gruppo A — Comando, parsing, backbone
- **REQ-201 (Ubiquitous):** *The installer shall implement the `install rag` subcommand so that it
  performs the RAG setup instead of raising `CapabilityNotAvailableError`.*
- **REQ-202 (Ubiquitous):** *The `install rag` command shall accept a `--target` option (default:
  current working directory) identifying the host repository root.*
- **REQ-203 (Event-driven):** *When `--target` does not exist or is not a directory, the installer
  shall stop with a usage/domain error and a readable message, without modifying the target.*
- **REQ-204 (Ubiquitous):** *The command shall accept a `--backend` option with values `azure` and
  `local`, defaulting to the cloud backend (`azure`).*
- **REQ-205 (Optional):** *Where the user passes `--no-graph` and/or `--no-rerank`, the installer
  shall exclude the corresponding extras (`graph`, `rerank`) that are otherwise included by default
  (opt-out, DA-3).*
- **REQ-206 (Ubiquitous):** *The command shall accept a `--corpus` option naming the RAG corpus
  (`SERTOR_CORPUS`); absent, it shall default to the sanitized name of the target directory.*
- **REQ-207 (Optional):** *Where the user passes `--no-deps`, the installer shall perform only the
  config scaffold and skip the dependency bootstrap.*
- **REQ-208 (Optional):** *Where the user passes `--json`, the installer shall emit the report in
  the machine-readable JSON form (schema-versioned), matching the `install wiki` contract.*
- **REQ-209 (Ubiquitous):** *The command shall return exit code `0` on success (including a fully
  idempotent no-op run), `1` on a domain error, and `2` on a usage error.*

### Gruppo B — Bootstrap delle dipendenze (lo scopo "B")
- **REQ-210 (Unwanted):** *If the bootstrap step runs, then the installer shall not start any RAG
  indexing or ingestion as a side effect (install ≠ run): adding dependencies is permitted, indexing
  is not.*
- **REQ-211 (Event-driven):** *When the `.sertor/` runtime has no `pyproject.toml` and `--no-deps`
  is not set, the installer shall initialize a minimal uv project (`uv init --bare`) inside
  `<target>/.sertor/` before adding dependencies.*
- **REQ-212 (Event-driven):** *When the bootstrap step runs, the installer shall add `sertor-core`
  with the extras derived from `--backend` and the extra flags, sourced from the project's
  distribution URL (`git+url`), via `uv`, operating inside `<target>/.sertor/`.*
- **REQ-213 (Ubiquitous):** *By default the dependency specification shall include all capability
  extras — `mcp`, `graph`, `rerank` — plus the backend-specific extra (`azure` for `--backend
  azure`; none additional for `local`); `--no-graph`/`--no-rerank` remove the respective extras
  (DA-3). The `azure` extra is never forced on the `local` backend.*
- **REQ-214 (Unwanted):** *If `uv` is not available on the machine, then the installer shall stop
  the bootstrap step with a readable domain error stating the prerequisite, without leaving the
  target in a half-initialized project state where avoidable.*
- **REQ-215 (Unwanted):** *If `uv add` fails (e.g., dependency conflict, network error), then the
  installer shall report the failed step and stop (fail-fast), surfacing the underlying tool error.*
- **REQ-216 (State-driven):** *While adding dependencies, the installer shall only add (never remove
  or downgrade) entries in an existing `pyproject.toml`, preserving the user's declared dependencies.*

### Gruppo C — Scaffold `.env`
- **REQ-220 (Event-driven):** *When the `.env` file (`<target>/.sertor/.env`) is absent, the
  installer shall create it from a template containing the configuration keys required by the
  selected backend.*
- **REQ-221 (Ubiquitous):** *The generated `.env` shall leave secret values (e.g., `*_API_KEY`)
  empty, to be filled in by the user.*
- **REQ-222 (Event-driven):** *When the `.env` file already exists, the installer shall merge in
  only the keys that are missing, never overwriting an existing key's value (additive merge).*
- **REQ-223 (Ubiquitous):** *The `.env` template for `--backend azure` shall include
  `RAG_BACKEND=azure`, `SERTOR_STORE_BACKEND=local`, the Azure OpenAI endpoint/key/embed-deployment
  keys, and `SERTOR_CORPUS`; for `--backend local` it shall include `RAG_BACKEND=local`,
  `OLLAMA_HOST`, and `SERTOR_CORPUS`.*

### Gruppo D — Scaffold `.mcp.json`
- **REQ-230 (Event-driven):** *When the `.mcp.json` file (at the **host root**) is absent, the
  installer shall create it declaring the `sertor-rag` MCP server, invoking the core MCP server
  inside the `.sertor/` runtime (`uv run --directory .sertor …`) with the corpus environment.*
- **REQ-231 (Event-driven):** *When `.mcp.json` already exists, the installer shall merge the
  `sertor-rag` server entry additively, preserving any other servers already declared.*
- **REQ-232 (Unwanted):** *If `.mcp.json` already declares a `sertor-rag` server, then the installer
  shall not duplicate or silently overwrite it (idempotent: report `skipped`/`merged`).*

### Gruppo E — Scaffold `.gitignore`
- **REQ-240 (Event-driven):** *When the bootstrap completes, the installer shall ensure the host
  `.gitignore` contains entries for the regenerable runtime artifacts (`.sertor/.venv/`,
  `.sertor/.index*`, `.sertor/.env`), appending only the missing ones.*
- **REQ-241 (Unwanted):** *If an entry is already present in `.gitignore`, then the installer shall
  not append a duplicate.*

### Gruppo F — Report e osservabilità
- **REQ-250 (Ubiquitous):** *The installer shall produce a per-artifact report (created / skipped /
  merged / error) and a summary, reusing the `InstallReport` contract of `install wiki`.*
- **REQ-251 (Event-driven):** *When a step fails, the installer shall record the failed step and
  stop (fail-fast, no rollback), leaving already-written artifacts in place.*
- **REQ-252 (Ubiquitous):** *The report shall be the sole observability surface of the operation
  (no hidden side effects), available in human and JSON form.*

### Gruppo G — Distribuzione (fix `pyproject` / uvx)
- **REQ-260 (Ubiquitous):** *The `sertor` package shall resolve its `sertor-core` dependency from
  the monorepo git distribution when installed standalone (via `uvx`/`pip install` from `git+url`).*
- **REQ-261 (Unwanted):** *If the `sertor` package is installed standalone, then dependency
  resolution shall not attempt to fetch `sertor-core` from PyPI (where it is not published).*
- **REQ-262 (Ubiquitous):** *The fix shall not break workspace resolution in development: the
  in-repo `uv` workspace shall keep resolving `sertor-core` from the local source.*

### Gruppo H — Agnosticità e non distruttività (trasversali della feature)
- **REQ-270 (Ubiquitous):** *The installer shall complete on both a brand-new and an existing
  repository (host-agnostic), without overwriting user-modified files.*
- **REQ-271 (Ubiquitous):** *Re-running `install rag` on the same target shall be safe and
  idempotent: identical final state, zero duplicates.*

### Gruppo I — Collocazione (runtime isolato in `.sertor/`)
- **REQ-280 (Ubiquitous):** *The installer shall place the RAG runtime (Python project, virtual
  env, index/graph, `.env`) under an isolated `<target>/.sertor/` directory, never mixing it into
  the host source tree.*
- **REQ-281 (Ubiquitous):** *The `.mcp.json` shall be written at the host root (where MCP clients
  look) and shall invoke the server inside `.sertor/` (e.g., `uv run --directory .sertor`).*
- **REQ-282 (Ubiquitous):** *The RAG indexing shall target the host sources (the `.sertor/` parent)
  while excluding the `.sertor/` directory itself from the corpus.*
- **REQ-283 (Ubiquitous):** *Wiki artifacts (`.claude/`, the `CLAUDE.md` ritual block, the `wiki/`
  folder) shall remain at the host root and are out of scope of this command (handled by `install
  wiki`); only the shared Python runtime they rely on lives in `.sertor/`.*

## 6. Requisiti non funzionali
- **NFR-1 (isolamento dipendenze):** l'installer non deve importare SDK pesanti (azure/mcp/graph)
  per funzionare; orchestra `uv`, non esegue retrieval.
- **NFR-2 (osservabilità):** ogni artefatto e ogni comando esterno invocato deve essere riflesso nel
  report; il comando `uv` eseguito deve essere mostrato (trasparenza, non azione opaca).
- **NFR-3 (host-agnosticità, Principio X):** nessun riferimento a percorsi/dominio di Sertor negli
  artefatti generati sul target.
- **NFR-4 (sicurezza, REQ-E5):** nessun segreto scritto con valore né loggato.
- **NFR-5 (testabilità senza rete):** la logica di scaffold/merge/piano deve essere testabile senza
  invocare realmente `uv` né la rete (il subprocess `uv` va isolato dietro un confine mockabile).
- **NFR-6 (coerenza di superficie):** stessa grammatica di report, flag `--json`, exit code di
  `install wiki`.

## 7. Vincoli, assunzioni e dipendenze
- **Vincolo:** Python ≥ 3.11; distribuzione interim `git+url` (DA-4 epica).
- **Vincolo:** layer sottile (Principio I) — l'installer orchestra, il core fa il lavoro.
- **Assunzione:** il client MCP di riferimento è **Claude Code** (formato `.mcp.json`); altri
  assistenti sono FEAT-007.
- **Assunzione:** il gestore di pacchetti di riferimento è **`uv`** (preferito dall'epica); il
  fallback `pip` è oggetto di DA-1.
- **Assunzione (additività = non distruttività):** `uv add` è additivo sul `pyproject` esistente;
  lo consideriamo conforme a REQ-E6 senza conferma interattiva (vedi DA-2).
- **Dipendenza:** estende il pacchetto installer (`packages/sertor/`) e riusa `report.py`/
  `artifacts.py`/`config_gen.py`; il fix `pyproject` tocca `packages/sertor/pyproject.toml`.

## 8. Rischi
- **R-1 — Invasività del bootstrap:** `uv init`/`uv add` modificano il progetto target; mitigato da
  `--no-deps`, additività (REQ-216) e report trasparente (NFR-2).
- **R-2 — `uv` assente o versione incompatibile** sulla macchina (REQ-214).
- **R-3 — Conflitti di dipendenze** col progetto esistente (REQ-215, fail-fast).
- **R-4 — Target non-Python** (es. repo JS) trasformato in progetto uv: potenzialmente indesiderato
  (vedi DA-1).
- **R-5 — Disallineamento col core:** se gli extra o le variabili di config cambiano, il template
  `.env` e la spec dipendenze vanno riallineati (R-5 d'epica).

## 9. Prioritizzazione (MoSCoW)
- **Must:** REQ-201..204, REQ-209, REQ-210, REQ-211, REQ-212, REQ-213, REQ-220..223, REQ-230..232,
  REQ-240/241, REQ-250/251, REQ-260..262, REQ-270/271, **REQ-280..283 (collocazione `.sertor/`)**.
- **Should:** REQ-205 (opt-out `--no-graph`/`--no-rerank`), REQ-206 (`--corpus` con default), REQ-207 (`--no-deps`),
  REQ-208 (`--json`), REQ-214/215 (gestione errori `uv` esplicita), REQ-252, NFR-2/NFR-5.
- **Could:** fallback `pip` (se deciso in DA-1); rilevazione "target non-Python" con avviso (DA-1).
- **Won't (qui):** wizard interattivo; superfici multi-assistente; PyPI.

## 10. Domande aperte
- **[DA-1] ✅ RISOLTA (2026-06-12) — solo `uv`, runtime isolato in `.sertor/`.** L'installer usa solo
  `uv` (fail-fast con messaggio se `uv` è assente; `uv init --bare` quando manca il pyproject). Il
  problema "target non-Python / pythonizzazione" è risolto **alla radice** dalla collocazione: tutto
  il runtime Python vive in `<target>/.sertor/`, i sorgenti dell'host non vengono toccati (vedi
  *Decisione di collocazione* in §4 e Gruppo I). Niente guardia non-Python (non c'è nulla da
  proteggere) e niente fallback `pip` nell'MVP (eventuale Could).
- **[DA-2] Conferma prima di toccare un `pyproject.toml` esistente.** REQ-E6 d'epica vieta di
  sovrascrivere file utente senza conferma, ma il wizard interattivo è rinviato. `uv add` **modifica**
  (additivamente) il `pyproject` dell'utente. Procediamo senza conferma (additività = non distruttivo,
  REQ-216) confidando su `--no-deps` per chi vuole solo lo scaffold, oppure introduciamo una conferma
  esplicita / flag `--yes` per il passo dipendenze? *Raccomandazione: nessuna conferma interattiva
  (coerente con "wizard rinviato"); additività + `--no-deps` come valvola.*
- **[DA-3] ✅ RISOLTA (2026-06-12) — "metti tutto" (opt-out).** Default = tutti gli extra di
  capacità (`mcp` + `graph` + `rerank`) + l'extra del backend scelto (`azure` su `--backend azure`;
  nulla in più su `local`). Logica opt-out: `--no-graph`/`--no-rerank` per alleggerire. `azure`
  mai forzato sul backend `local`. (Decisione utente: massima capacità pronta all'uso.)
- **[DA-4] Default di `SERTOR_CORPUS`.** Va bene il nome (sanitizzato) della cartella target come
  default quando `--corpus` non è passato? *Raccomandazione: sì.*

---

### Commit proposto (da delegare al configuration-manager)
`docs(requirements): elicita la feature install-rag (taglio rag di FEAT-002, scope B bootstrap)`
