# Installing Sertor on another repository

> **Just want to get started?** Use the concise per-assistant quick starts instead:
> **[install-claude.md](install-claude.md)** (Claude Code) · **[install-copilot.md](install-copilot.md)**
> (GitHub Copilot). This page is the **complete reference** — every flag, all configuration knobs, the
> MCP server, host-root hygiene, and refresh/uninstall (§10).

> **Status.** Sertor is not yet on PyPI: the interim distribution is **`git+url`** (decision DA-4
> of the CLI epic). This guide covers all the installable capabilities: the **full RAG capability**
> (indexing + search + MCP server) and the guided **`sertor install rag`** (§6); the **deterministic
> wiki tooling** and the guided **`sertor install wiki`** that brings the entire wiki system to the
> host with one command (§5); and the **development method (SDLC)** via the separate, RAG-independent
> package **`sertor-flow`** (§8). Each is non-destructive and idempotent — **install ≠ run**.
>
> **Target assistant.** The installers accept **`--assistant`** (default `claude`) to choose which
> host AI assistant receives the surfaces: `claude` (`.claude/**` + `.mcp.json` + `CLAUDE.md`) or
> `copilot-cli` (GitHub **Copilot CLI**: `.github/**` + `.mcp.json` with the `mcpServers` root). All
> three capabilities (`sertor` RAG/Wiki and `sertor-flow` governance) support **`claude|copilot-cli`**.
> The legacy VS Code value `copilot` was consolidated into `copilot-cli` (see the migration note in
> **[install-copilot.md](install-copilot.md#migrating-from-the-vs-code-target)**). See **§9**.

## 0. Interim distribution (`git+url`)

Sertor is **not on PyPI** (public publishing is out of scope — see *PyPI boundary* below): the current
distribution channel is an **unpinned `git+url`** against the GitHub repository. Two packages are meant
to be **installed directly** (user-facing) — `sertor` (the wiki/RAG installer) and `sertor-flow` (the
governance/SDLC installer). The other two — `sertor-core` (the retrieval library/CLI) and
`sertor-install-kit` (the shared install engine) — are **internal dependencies**: they are resolved
**automatically from the workspace in the git checkout** and are **not** installed directly.

**Prerequisites.** Python ≥ 3.11; `uv` (recommended); network access to GitHub; **no PyPI account**.

### Primary path — `uv`/`uvx` (the supported gate)

```powershell
# wiki/RAG installer (sertor):
uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor --help
# governance/SDLC installer (sertor-flow):
uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor-flow" sertor-flow --help
```

`uv` resolves the internal dependencies (`sertor-core`, `sertor-install-kit`) by **discovering the uv
workspace from the git checkout** — not from PyPI. The entry points (`sertor`/`sertor-flow`, and after
install the `sertor-rag`/`sertor-wiki-tools` console scripts of `sertor-core`) become invocable with a
single command.

### Secondary path — `pip` (best-effort, documented limitation)

```powershell
pip install "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor"
```

> **Limitation (known).** `pip` does **not** understand the uv *workspace*: when it resolves the
> internal dependencies (`sertor-core`, `sertor-install-kit`) of `sertor`, it does not discover them
> from the checkout the way `uv` does, and — since they are not on PyPI — the resolution is **not
> guaranteed**. Use `uv`/`uvx` for the one-command install. Full `pip` ergonomics (workspace
> resolution) is deferred to **FEAT-010**.

> **Version.** The product version is a single source of truth in `/VERSION` at the repo root; all four
> packages read it dynamically, so they are aligned by construction (bump = edit `/VERSION`).

> **PyPI boundary.** Public publishing (PyPI/TestPyPI) and supply-chain hardening (signing/provenance/
> SBOM) are **out of scope** here — tracked as **FEAT-006**. `git+url` is the current interim channel.

## Prerequisites

- **Python ≥ 3.11** and [`uv`](https://github.com/astral-sh/uv) (recommended; `pip` as an alternative).
- An **embeddings** provider. The default is **zero-config**:
  - **`glove` (default)** — static GloVe 6B word vectors, **local-first with nothing to run**;
    downloaded once per machine (~822 MB) and offline afterwards.
  - **`azure`** (opt-in, best quality) — an **Azure OpenAI** deployment of `text-embedding-3-*`
    (needs credentials; fill them with `sertor configure` — see *Filling `.sertor/.env`* under §6).
  - **`ollama`** (opt-in) — a local [Ollama](https://ollama.com) server (`ollama serve` +
    `ollama pull nomic-embed-text`), selected explicitly with `SERTOR_EMBED_PROVIDER=ollama`.
  - **`hash`** — a zero-download lexical floor for airgapped/CI.
  See the **Embedding providers** table below. *(The default used to imply Ollama; it is
  now `glove` — Ollama and Azure are selected explicitly.)*
- **No PowerShell / `pwsh` needed — the hooks are portable.** The lifecycle hooks distributed by
  `sertor install` are **portable Python** scripts, invoked as `uv run --no-project python <hook>.py`.
  They work identically on **Windows, macOS and Linux** with **no PowerShell dependency**. `uv` is
  already the package prerequisite (above); `--no-project` isolates the hook from the host's own
  `pyproject.toml`, so it runs anywhere without touching the host's environment.

### Operatività per target (which surfaces are operational after `sertor install`)

Every distributed surface — the MCP server, the instruction block (`CLAUDE.md`/
`.github/copilot-instructions.md`), the skills, the agents and the **lifecycle hooks** — works on
**every OS and target**. Since the hooks are portable Python (run via `uv run --no-project python`),
there is no OS-conditional surface and no PowerShell requirement:

| Target | Fully operational after install | Needs extra configuration |
|---|---|---|
| Claude on any OS | MCP, `CLAUDE.md` block, hooks, skills, agents | — |
| Copilot CLI on any OS | MCP, instruction block, hooks, skills, agents | `memory-capture`: requires `SERTOR_MEMORY=true` + `SERTOR_MEMORY_ADAPTER=copilot-cli` to capture Copilot CLI sessions |

## 1. Package installation

In the target repository:

```bash
# base (local-first: glove embeddings + Chroma store, zero-config)
uv add "sertor-core @ git+https://github.com/themetriost/Sertor"

# with cloud extras and/or MCP server
uv add "sertor-core[azure,mcp] @ git+https://github.com/themetriost/Sertor"
```

With `pip`: `pip install "sertor-core @ git+https://github.com/themetriost/Sertor"`.

The installation brings **three things**: the `sertor_core` library (importable) and two console
scripts — **`sertor-rag`** (RAG execution) and **`sertor-wiki-tools`** (deterministic wiki core).

> **install ≠ run**: installing or importing never starts any indexing — every operation requires
> an explicit command.

## 2. Configuration (`.env` in the target repo, never committed)

All operational choices are read from the centralised configuration (env and/or `.env`). The
embedding **provider** (`SERTOR_EMBED_PROVIDER`) and the vector **store** (`SERTOR_STORE_BACKEND`)
are two independent knobs.

**Embedding providers (`SERTOR_EMBED_PROVIDER`):**

| Value | Description | Credentials | Cost |
|-------|-------------|-------------|------|
| `glove` (default) | static GloVe 6B 300d word vectors, local NL semantics; downloaded once per machine (~822 MB, [PDDL / public domain](https://opendatacommons.org/licenses/pddl/)) | none | free |
| `hash` | char-n-gram lexical floor, airgapped/CI, zero-download; lexical only (limited NL) | none | free |
| `ollama` | local embedding model (requires `ollama serve`) | none | free |
| `azure` | Azure OpenAI cloud embeddings | Azure OpenAI | billable |

**Local, zero-credentials (default):**
```bash
SERTOR_EMBED_PROVIDER=glove            # default; downloads GloVe once on the first index
SERTOR_CORPUS=my-project              # collection namespace (recommended)
```

**Airgapped / offline:** use the lexical provider (no download), or point `glove` at a local file:
```bash
SERTOR_EMBED_PROVIDER=hash             # zero-download lexical floor
# or:
SERTOR_EMBED_PROVIDER=glove
SERTOR_GLOVE_PATH=/path/to/glove.6B.300d.txt   # skips the download
```

**Azure (cloud embeddings + local Chroma store — recommended combination):**
```bash
SERTOR_EMBED_PROVIDER=azure
SERTOR_STORE_BACKEND=local             # local Chroma vector store
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_EMBED_DEPLOYMENT=text-embedding-3-large
SERTOR_CORPUS=my-project
```

> **Migration note (`RAG_BACKEND` removed).** `RAG_BACKEND` is **no longer honoured**: select the
> embedding provider with `SERTOR_EMBED_PROVIDER` and the vector store with `SERTOR_STORE_BACKEND`.
> A residual `RAG_BACKEND` in your `.env` triggers a warning and is ignored (no silent migration).
> The **default has changed**: local-first used to imply Ollama; it is now `glove` (static vectors).
> Ollama and Azure must be selected explicitly.

If the configuration for the chosen provider/store is incomplete, every command **stops before
contacting any service**, listing the missing variables. Useful optional settings:
`SERTOR_INDEX_DIR` (index directory, default `.index` — add it to the host's `.gitignore`),
`SERTOR_EXCLUDE_PATTERNS`, `DEFAULT_K`, `SERTOR_PREVIEW_CHARS`.

**Retrieval engine (FEAT-004):** the default is the **hybrid** engine (lexical BM25 + vector
fused with RRF) — significantly improves symbol/exact-term queries:

```bash
SERTOR_ENGINE=hybrid       # baseline | hybrid (default: hybrid)
SERTOR_RRF_C=60            # RRF fusion constant
SERTOR_RRF_POOL=30         # candidates per source before fusion
SERTOR_RERANK=false        # second-stage cross-encoder (requires the `rerank` extra)
SERTOR_RERANK_POOL=15      # fused pool passed to the reranker (~3×k)
SERTOR_DEDUP=true          # drop near-duplicate results before the top-k cut (default on)
```

> **Result dedup (`SERTOR_DEDUP`, default on).** When the same content lives in several files (a
> shared `CLAUDE.md`/wiki block, a vendored copy), those near-duplicates can crowd the top-k and bury
> the canonical page. The dedup keeps the highest-ranked instance of each near-duplicate group before
> the cut, so distinct content fills the results. It is a **no-op** on already-distinct results and
> adds no dependency (a content-overlap test, no LLM); set `SERTOR_DEDUP=false` to disable.

> **Migration:** a corpus indexed **before** the hybrid engine continues to work (degrades to
> vector-only with a log warning); a **re-index** (`sertor-rag index .`) also builds the lexical
> index and enables the hybrid engine. For optional reranking: install the extra
> (`uv add "sertor-core[rerank] @ git+…"`) and set `SERTOR_RERANK=true` — without the extra,
> `SERTOR_RERANK=true` produces an explicit error with the installation instruction.

**Structural code-graph (FEAT-005):** every `sertor-rag index .` also builds the **code graph**
(module/class/function/method/doc nodes; contains/calls/imports/inherits/mentions edges),
persisted to `<index_dir>/graph/<corpus>.json` — the build requires no extra dependencies. To
**navigate it** (the 4 MCP tools `find_symbol` / `who_calls` / `related_docs` / `get_context`) the
extra is needed:

```bash
uv add "sertor-core[graph] @ git+https://github.com/themetriost/Sertor"   # networkx
```

```bash
SERTOR_GRAPH=true               # graph build inside index() (default)
SERTOR_GRAPH_AMBIGUITY=2        # names more ambiguous than this do not generate calls edges
SERTOR_GRAPH_LIMIT_DEFS=10      # limits per section of get_context
SERTOR_GRAPH_LIMIT_RELS=8
SERTOR_GRAPH_LIMIT_DOCS=8
```

Missing symbol → empty lists; graph not built → error telling you to index; extra not installed →
error with the installation instruction. Edge coverage per language is **declared**: nodes and
hierarchy for all 10 syntactic languages, calls for all, imports/inheritance for Python.

**Embedding cache (hardening, REQ-H4):** with a paid provider (Azure) every `sertor-rag index .`
would re-embed identical content. The content-hash cache reuses embeddings for **unchanged** chunks —
only changed/new chunks are sent to the provider. It is **on by default** (A-08 security review):

```bash
SERTOR_EMBED_CACHE=false    # default: true — disable to force a full re-embed on every rebuild
```

> **Recurring cost note (SessionEnd re-index).** The **RAG-freshness** hook re-indexes at the end of
> **every** agent session (see §10.1). On a **paid** provider this means recurring, automatic
> embedding calls — the embedding cache above (default on) plus the incremental indexer (only changed
> files are embedded) keep that near-zero when nothing changed, but the egress is real: budget for it,
> or switch the runtime to the local `glove` provider (free) if you don't want any cloud calls.

The cache lives at `<index_dir>/embed_cache.sqlite` (git-ignored), keyed by `(model, content-hash)`
so a provider/model change never serves stale vectors. It is safe to delete at any time (causes at
most a re-embed). The embedding log event reports the provider token count (`tokens`) as a cost
signal when the provider exposes it (REQ-H5), independent of the cache.

**Observability persistence (feature 020):** Sertor already emits rich structured events (index,
embeddings, cache hits/misses, retrieve, …) but they are ephemeral (stderr). Enable persistence to
keep them in a local store so historical reports become possible:

```bash
SERTOR_OBSERVABILITY=true     # default: false (ephemeral logging only)
```

The store is `<index_dir>/observability.sqlite` (git-ignored), queryable by operation and time. It is
**privacy-by-default**: only metrics/metadata are kept (secrets redacted, never query text). It is
**non-intrusive**: a store failure never fails an operation (only a warning), and it is safe to
delete.

**Live panel (feature 022, TUI):** open a terminal dashboard with the current state (last index,
cache hit/miss + estimated savings, token cost, recent events), auto-refreshing. It requires the
optional `tui` extra and reads the persisted data:

```bash
uv add "sertor-core[tui] @ git+https://github.com/themetriost/Sertor"   # textual (one-off)
sertor-rag observe                                                       # open the live panel
```

The panel is **tabbed**: **Live** (current state) plus **Cache / Cost / Corpus** browsable reports
(hit/miss over time, tokens per provider/day, corpus health + freshness). Press **`t`** to cycle the
time range (all → 7 days → 24 hours). Refresh interval via `SERTOR_OBSERVABILITY_REFRESH` (default 2s).
Without the extra, the command prints an actionable install hint; with persistence off, the panel
shows an honest "no data — enable SERTOR_OBSERVABILITY" state. The panel is read-only.

## 3. First commands

```bash
uv run sertor-rag index .                          # index the repository (full rebuild)
uv run sertor-rag search "how does X work?"        # top-k with path, type, score, preview
uv run sertor-rag search "build pipeline" -k 10 --type code --json   # for scripts/agents
uv run sertor-rag index . -v                       # with structured logs visible
```

Exit code: `0` success · `1` domain error (human-readable message on stderr) · `2` wrong usage.
Full CLI guide: [`specs/011-cli-esecuzione-rag/quickstart.md`](../specs/011-cli-esecuzione-rag/quickstart.md).

## 4. MCP server (for Claude Code and other MCP clients)

With the `mcp` extra installed, add a `.mcp.json` to the target repo:

```json
{
  "mcpServers": {
    "sertor-rag": {
      "command": "uv",
      "args": ["run", "python", "-m", "sertor_mcp.server"],
      "env": { "SERTOR_CORPUS": "my-project" }
    }
  }
}
```

The server exposes `search_code` / `search_docs` / `search_combined` over the same index as the
CLI (identical results given the same configuration).

## 5. Full wiki system: `sertor install wiki`

With the installer package (`sertor`, provided by the workspace — included in the `git+url` install),
a single command brings the entire wiki system to the host:

```bash
uv run sertor install wiki                          # in the root of the target repo
uv run sertor install wiki --target C:\path\repo    # or on an explicit path
uv run sertor install wiki --language it --source-dirs src,docs   # override defaults
uv run sertor install wiki --assistant copilot-cli  # target the GitHub Copilot CLI instead of Claude (§9)
```

What it installs (all **without** starting any indexing, LLM, or network — install ≠ run):

| Artifact | Behaviour if already present |
|---|---|
| `wiki-author` skill (playbook + ops modules), `/wiki` command, `wiki-curator` agent, session hooks | skip **file-by-file** (never overwritten) |
| Hook entries in `.claude/settings.json` | **additive merge** with deduplication (your hooks stay) |
| *Step ritual* section in `CLAUDE.md` | inserted in a **marker block** `SERTOR:WIKI-RITUAL`; the rest of the file is untouched |
| `wiki.config.toml` | generated with inferred defaults (language `en`, `source_dirs` from standard folders present); never overwritten |
| `wiki/` structure (taxonomy, index, log) | `structure init` idempotent |

The command prints a **report** per artifact (`created`/`skipped`/`merged`/`block`) and exits with
`0` (success), `1` (domain error, fail-fast with explicit partial state — re-running fills the gaps),
or `2` (wrong usage). Re-running is safe: identical state, zero duplicates. The session hooks are
**portable Python** (run via `uv run --no-project python`), so they work on Windows, macOS and Linux
with **no PowerShell dependency**.

### Deterministic wiki tooling (already included in the core package)

`sertor-wiki-tools` (scan/lint/structure/collect/index/append-log/…) works on any host from the
**`wiki.config.toml`** (the one generated by the installer, or written by hand using Sertor's own
as an example). The `install governance` subcommand is planned but not yet available.

**Wiki maintenance (feature 017):**
- `sertor-wiki-tools move <src> <dest> [--dry-run]` — moves/renames a page and **rewrites all
  incoming links** (wikilinks `[[...]]` and relative links), without breaking them; `--dry-run`
  shows the plan without modifying anything; fails if the destination already exists.
- `sertor-wiki-tools reconcile [--json]` — lists (read-only) pages marked
  `status: superseded` (with the optional `superseded_by`), as an obsolescence check; never
  modifies anything. For a **periodic** report, schedule the command with the host environment
  (cron / Task Scheduler / CI hook), e.g. `sertor-wiki-tools reconcile --json > reports/wiki-obsolete.json` —
  the product does not include a built-in scheduler.

## 6. RAG capability with one command: `sertor install rag`

`sertor install rag` brings the full RAG capability to a host repo — **even non-Python ones** (e.g. .NET):
the Python runtime lives **isolated** in a `.sertor/` dotfolder (your sources are not touched);
only the `.mcp.json` (the bridge to Claude/MCP clients) and the updated `.gitignore` remain in the
root.

```bash
# from a machine with `uv`, in the root of the target repo (Azure embeddings):
uv run sertor install rag --backend azure
# variants:
uv run sertor install rag --backend local --no-rerank   # local-first (glove), without reranker
uv run sertor install rag --no-deps                      # config scaffold only (no uv add)
uv run sertor install rag --mcp-scope local              # no .mcp.json in the repo (registers in the client)
uv run sertor install rag --assistant copilot-cli        # target the GitHub Copilot CLI: .mcp.json (§9)
uv run sertor install rag --target C:\path\repo --corpus myproject --json
```

What it does (all **without** indexing — install ≠ run):

| Artifact | Where | Behaviour if already present |
|---|---|---|
| Python project + dependencies (`uv init --bare` + `uv add sertor-core[azure,mcp,graph,rerank]`) | `<target>/.sertor/` | `uv add` idempotent; `uv init` skipped if already initialised |
| `.env` (backend template, **empty secrets** to fill in) | `<target>/.sertor/.env` | additive per-key merge (never overwrites your values) |
| `.mcp.json` (`sertor-rag` server via `uv run --directory .sertor`) — scope `project` (default) | **host root** | additive merge (preserves other MCP servers) |
| MCP registration in the client (`claude mcp add-json … --scope local`) — scope `local` | **outside the repo** (`~/.claude.json`) | idempotent (skip if already registered); fail-fast if `claude` is missing |
| **RAG-freshness hooks** (E10-FEAT-011): `rag-freshness.py` (**SessionEnd**: re-index + `doctor` → writes `.sertor/.rag-health.json`) + `rag-freshness-start.py` (**SessionStart**, Claude: induces a fix if the last verdict was `degraded`) + their wiring | `.claude/hooks/**` + `.claude/settings.json` (Claude) · `.github/hooks/**` + `.github/hooks/sertor-hooks.json` (Copilot CLI) | per-file skip; wiring is an additive dedup merge |
| **Version-check hooks** (E2-FEAT-013): `version-check.py` (**SessionEnd**: GET `/VERSION` ~1/day → writes `.sertor/.version-check.json`) + `version-check-start.py` (**SessionStart**, Claude; static startup prompt on Copilot CLI: warns if behind — never auto-upgrades) + their wiring; plus the install-time stamp `.sertor/.sertor-version` | `.claude/hooks/**` + `.claude/settings.json` (Claude) · `.github/hooks/**` + `.github/hooks/sertor-hooks.json` (Copilot CLI) | per-file skip; wiring is an additive dedup merge |
| `.gitignore` (`.sertor/.venv/`, `.sertor/.index*`, `.sertor/.env`, `.sertor/.rag-health.json`, `.sertor/.version-check.json`, `.sertor/.sertor-version`) | **host root** | append dedup |
| `.gitattributes` (`* text=auto eol=lf` — normalizes text files to LF so the install produces a clean, review-able diff on Windows instead of a CRLF line-ending churn) | **host root** | **create-if-absent** (a host that already has a `.gitattributes` keeps its own — never overwritten) |

Default: `azure` backend, all extras (`mcp`+`graph`+`rerank`) plus the backend's own; `--no-graph`
/`--no-rerank` to reduce scope, `--no-deps` for scaffold only. Exit `0`/`1` (domain error,
fail-fast: `uv` absent or `uv add` failed)/`2` (wrong usage). Re-running is safe (identical state).

### Filling `.sertor/.env`: `sertor configure`

`sertor install rag` deposits a `.sertor/.env` with **empty secrets** (install ≠ configure). You can
edit that file by hand, or use the guided command **`sertor configure`**, which brings it from
"empty secrets" to "ready" without opening an editor:

```bash
uv run sertor configure                       # interactive: prompts only for the fields the backend needs
uv run sertor configure --backend local       # local-first (glove): no secrets needed — nothing to fill
uv run sertor configure --backend azure        # prompts for AZURE_OPENAI_ENDPOINT / _API_KEY (masked)
uv run sertor configure --set AZURE_OPENAI_ENDPOINT=https://x.openai.azure.com --non-interactive  # CI-safe
```

- **`--backend {azure,local}`** (default `azure`) → sets `SERTOR_EMBED_PROVIDER` (`azure`→`azure`,
  `local`→`glove`). **`glove` needs no secrets**, so with `--backend local` there is nothing to fill.
- **`--store {local,azure}`** (default = backend) → `SERTOR_STORE_BACKEND` (embeddings and store are
  independent knobs; e.g. Azure embeddings + local Chroma store).
- **`--set KEY=VALUE`** (repeatable) — explicit value for a known field; combine with
  **`--non-interactive`** for CI (never prompts; a missing required field is a named error, not a
  silent partial write).
- **`--overwrite`** — allow replacing values already present (default is **additive, non-destructive**:
  existing values are kept). Secrets are entered via a hidden prompt and **masked** in all output.
- **`--check`** (opt-in) — live-probe the provider through the `sertor-rag` vehicle *(Should / deferred:
  degrades honestly today)*. **`--json`** — machine-readable report.

Resolution per field: `flag/--set → existing .env or environment → prompt (if a TTY) → template
default`. After configuring, verify with `uv run --project .sertor sertor-rag doctor`.

After installation (explicit separate step — fill in the secrets in `.sertor/.env` first, e.g. with
`sertor configure` above):

```bash
uv run --project .sertor sertor-rag index .   # index host sources (keeps cwd; `.sertor/` is index/.env only)
# then reload the MCP client: approve the `sertor-rag` server → search_code/docs/combined (+ graph)
```

> **Staying fresh is automatic from now on (E10-FEAT-011).** Besides the one-off index above, the
> installer wires a **RAG-freshness** hook: at the end of each agent session it re-indexes
> (incremental — near-free when nothing changed) and runs `doctor`, recording the verdict in
> `.sertor/.rag-health.json`; at the next session start, if that verdict was `degraded`, the agent is
> prompted to re-index / reconnect the MCP server before working on possibly stale context. You can
> still re-index manually any time. Details in **§10.1**.

> **Self-locating runtime.** `sertor-rag`/`sertor-wiki-tools` load `.sertor/.env` and keep the
> index and graph inside `.sertor/` **from any cwd**: if there is no `.env` in the cwd, the CLI
> uses the one next to its own venv (`.sertor/`). The recommended form is **`uv run --project .sertor …`**
> — it runs the `.sertor` runtime but keeps your current directory, so relative paths like `index .`
> resolve from the project root (use `--project`, NOT `--directory`: `--directory` would change the cwd
> to `.sertor`, making `index .` index `.sertor` itself). If no `.env` is found, it warns instead of
> silently falling back to the defaults (provider `glove`, store `local`).
> **Uninstall** ≈ delete `.sertor/` and the `sertor-rag` entry from `.mcp.json`.

> **Distribution note (interim).** Standalone execution via `uvx --from "git+…#subdirectory=packages/sertor"`
> is **verified**: `uv` resolves `sertor-core` by discovering the workspace from the git checkout
> (it builds it from the same repo, not from PyPI). When developing from the Sertor repo, use
> `uv run sertor install rag`.

### Invoking the CLIs (the rule)

After `install rag` the runtime CLIs (`sertor-rag`, `sertor-wiki-tools`) live in the project's
`.sertor/.venv` — they are **NOT on `PATH`**. The canonical way to run them is
**`uv run --project .sertor <cli> …`** — it runs the `.sertor` runtime but keeps your current
directory, so relative paths like `index .` resolve from the project root. Use `--project`, NOT
`--directory`: `--directory` changes the cwd to `.sertor`, so `sertor-rag index .` would index
`.sertor` itself instead of your project.

```powershell
uv run --project .sertor sertor-rag doctor          # health check (config/provider/index/mcp)
uv run --project .sertor sertor-rag index .          # index host sources from the project root
uv run --project .sertor sertor-wiki-tools lint --json
```

A bare `sertor-rag …` (or `which sertor-rag`) failing means **"not on `PATH`", not "not installed"** —
do not conclude the tool is missing. If `uv` is unavailable, call the venv executable directly:
`.sertor/.venv/Scripts/<cli>.exe` (Windows) or `.sertor/.venv/bin/<cli>` (POSIX). The **installer**
`sertor` itself is not a persistent command: run it ephemerally with
`uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor <verb>`.

### Known environment notes

- **Windows + system Python 3.14 / `pywin32`.** A stale `pywin32` on the *system* interpreter may print
  `ModuleNotFoundError: No module named 'pywin32_bootstrap'` on `pip`/`python -m`. This is noise from the
  system Python, **not a Sertor error** — Sertor's CLIs and MCP server run inside `.sertor/.venv` via
  `uv run`, unaffected. Do **not** use the system `pip show sertor-rag` to check the install (it cannot
  see the project venv); use `uv run --project .sertor sertor-rag doctor` instead.

## 7. Host root hygiene: what stays and why

The installer keeps the **host root minimal and predictable**. After `install wiki`/`install rag`,
only these residents remain in the root, each for a reason:

| Resident | Why it is in the root |
|---|---|
| `.claude/`, `CLAUDE.md` | read by the client (Claude Code) there; position not configurable |
| `wiki/` | project documentation, by design; **contains** `wiki/wiki.config.toml` (wiki config is no longer scattered in the root) |
| `.gitignore` | append of runtime entries |
| `.sertor/` | **sole** home of the RAG runtime (project, `.venv`, index, `.env`): nothing from the runtime ends up in the root |
| `.mcp.json` | **only** with `--mcp-scope project` (default): Claude Code's project scope MUST reside in the root. With `--mcp-scope local` there is no MCP file in the repo |

**Wiki config in `wiki/`.** Tools locate it with `--config wiki/wiki.config.toml
--root .` or, from the host root, without flags (auto-discovery: `sertor-wiki-tools <op>` looks for
`./wiki.config.toml` and then `./wiki/wiki.config.toml`).

> **Migration of already-installed hosts**: out of scope. On a host with an old
> `wiki.config.toml` in the root, the installer does not move or remove it; to adopt the new layout
> move the file to `wiki/` manually (the internal paths — `root = "wiki"` — remain valid with `--root .`).

## 8. Development method (SDLC) with one command: `sertor-flow`

The Sertor **development method** — the SpecKit flow, requirements management, git delegation, a
constitution starter, and the `CLAUDE.md` SDLC ritual block — ships as a **separate, standalone
package `sertor-flow`**. It is **orthogonal to the RAG**: it has **no dependency on `sertor-core`**,
so a host can adopt the method without ever pulling in the retrieval stack (and vice versa). For
this reason `sertor install governance` is only a **pointer**: it tells you that governance lives in
`sertor-flow` and how to run it — `sertor` does not bundle it.

```bash
# from a machine with `uv`, in the root of the target repo:
uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor-flow" sertor-flow install
# variants:
sertor-flow install --target C:\path\repo     # explicit target (default: cwd)
sertor-flow install --assistant copilot-cli   # target the GitHub Copilot CLI instead of Claude (§9)
sertor-flow install --json                    # machine-readable report
```

**SpecKit is launched, not vendored (feature 045).** `sertor-flow` no longer ships frozen copies of
the SpecKit commands/agents and `.specify/**`. Instead it **launches the official spec-kit
installer** for the target assistant, at a **pinned** upstream version:

```text
uvx --from git+https://github.com/github/spec-kit.git@v0.8.18 \
    specify init . --here --ai <claude|copilot> --script <ps|sh> --no-git --force
```

Our `--assistant copilot-cli` maps to spec-kit's `--ai copilot` (spec-kit 0.8.18 has no
`copilot-cli`). This deposits the per-assistant SpecKit layout (Claude `.claude/commands/speckit.*` ·
Copilot `.github/prompts/speckit.*.prompt.md`) plus the shared `.specify/**` machinery. **Prerequisite
(fail-fast):** `uvx` must be on `PATH` **and the spec-kit release must be reachable at install
time** (network) — if the launcher is absent or `specify init` fails, the command stops with an
actionable error and applies nothing. This is a deliberate trade-off (a tracked deviation from the
otherwise offline/zero-network installer): the method tracks the assistants spec-kit supports
upstream, with no triple-vendoring to maintain.

On top of the launched SpecKit, `sertor-flow` deposits its **own** Sertor-authored surfaces (all
**without** starting any phase — **install ≠ run**), routed to the target assistant's containers:

| Artifact | Where (Claude · Copilot) | Behaviour if already present |
|---|---|---|
| SpecKit commands/agents + `.specify/**` | launched via `specify init` (see above) | layout present → launch **skipped** (not relaunched) |
| `requirements-analyst` + `configuration-manager` agents | `.claude/agents/*.md` · `.github/agents/*.agent.md` | per-file skip if present (non-destructive) |
| `requirements` skill | `.claude/skills/requirements/SKILL.md` · `.github/prompts/requirements.prompt.md` | per-file skip if present |
| Constitution **starter** (neutral, host-agnostic, assistant-agnostic) | `.specify/memory/constitution.md` | skip if present (never overwrites your constitution) |
| Per-host `init-options.json` / `integration.json` / manifests (generated from the profile) | `.specify/**` | skip if present |
| `SERTOR:SDLC-RITUAL` block | `CLAUDE.md` · `.github/copilot-instructions.md` | idempotent marker block; coexists with the wiki block |

The Sertor-authored agents/skill are rendered for Copilot from the **same canonical source** as
Claude (the body is reused verbatim, only the frontmatter/container is translated — anti-drift).

**install ≠ run.** The command only deposits the method bundle (and launches `specify init` to
obtain SpecKit) — it never creates a feature, runs a git command, or indexes anything. Re-running is
safe: the SpecKit launch is skipped when its layout is already on disk and every other artifact is
reported `skipped`.

**Coexistence with the wiki.** The SDLC ritual block uses its own markers
(`SERTOR:SDLC-RITUAL`), distinct from the wiki's `SERTOR:WIKI-RITUAL`: both blocks live in the same
instruction file (`CLAUDE.md` for Claude, `.github/copilot-instructions.md` for Copilot), each
idempotent on its own markers.

**Cross-platform.** The chosen script flavor is inferred from the host OS (`ps` on Windows, `sh`
elsewhere) and passed to `specify init --script`; the generated `init-options.json` records it. It
runs identically on Windows and POSIX (integration tests use platform-agnostic temp dirs).

**Independence from the core.** `sertor-flow` depends only on the shared installer toolkit
(`sertor-install-kit`), never on `sertor-core`. You can install the method on a repo that has no RAG,
and install the RAG on a repo that has no method — the two capabilities do not constrain each other.

Exit `0` success (even if everything was skipped) · `1` domain error (fail-fast: the failed step is
named — including an unreachable spec-kit launch — and already-written artifacts remain) · `2` wrong
usage.

## 9. Targeting another assistant: GitHub Copilot (`--assistant`)

By default the installers write the **Claude Code** layout. Pass `--assistant copilot-cli` to target
the **GitHub Copilot CLI** instead. The CLI reads the MCP server from `.mcp.json` (root key
`mcpServers`) and reuses the `.github/**` containers for instructions, agents and hooks. The
*content* of every surface is reused; only the *container* (path, format, JSON root key) is
translated. Default is `claude`; an unknown value stops with an explicit error listing the valid
ones (`claude`, `copilot-cli`).

> **The VS Code target (`copilot`) was removed.** Earlier releases also offered `--assistant copilot`
> for Copilot **in VS Code** (`.vscode/mcp.json` with a `servers` root, commands as
> `.github/prompts/*.prompt.md`). It has been **consolidated into `copilot-cli`** — `copilot` is no
> longer accepted. To update an existing VS Code install, see the **migration note** in
> **[install-copilot.md](install-copilot.md#migrating-from-the-vs-code-target)** (re-install with
> `copilot-cli`, then remove the leftover `.vscode/mcp.json` and `.github/prompts/*.prompt.md`
> manually — there is no automatic cleanup).

| Logical surface | Claude | Copilot CLI |
|---|---|---|
| Instruction / ritual block | `CLAUDE.md` | `.github/copilot-instructions.md` |
| MCP server (`sertor-rag`) | `.mcp.json` (`mcpServers`) | `.mcp.json` (`mcpServers`) |
| Hook wiring | `.claude/settings.json` | `.github/hooks/sertor-hooks.json` |
| Command / skill | `.claude/commands/<name>.md` | `.github/agents/<name>.agent.md` (custom-agent) |
| Agent persona | `.claude/agents/<name>.md` | `.github/agents/<name>.agent.md` |

On the CLI, commands/skills are rendered as **custom-agents** (`.github/agents/*.agent.md`) — the
only CLI-invocable form (a prompt-file is not invocable from the CLI). Commands are single-line so
they work as-is in **PowerShell** and POSIX shells:

```powershell
# RAG for the GitHub Copilot CLI (MCP lands in .mcp.json with the mcpServers root):
uv run sertor install rag --assistant copilot-cli --backend azure
# Wiki system for Copilot (instructions in .github/copilot-instructions.md):
uv run sertor install wiki --assistant copilot-cli
# Governance (SpecKit + Sertor-authored surfaces) for the Copilot CLI:
sertor-flow install --assistant copilot-cli
```

After installing for the **Copilot CLI**, reload its MCP config with `/mcp reload` (or restart the
CLI) and verify with `/mcp show`. The CLI discovers `.mcp.json` walking from the cwd up to the git
root (closest wins); `.github/mcp.json` and the user-level `~/.copilot/mcp-config.json` are also
read.

The same invariants hold for every assistant: **install ≠ run**, non-destructive (existing files are
never overwritten — merges are additive and per-file writes skip), idempotent, and secrets are never
written (the `.env` template ships with empty values).

> **Scope.** All three capabilities — `sertor` (`install rag`/`install wiki`) and `sertor-flow`
> governance — support `claude|copilot-cli`. For governance, our `copilot-cli` maps to spec-kit's
> `--ai copilot` (spec-kit 0.8.18 has no `copilot-cli`). A further assistant (`codex` → `AGENTS.md`)
> is planned but not yet implemented.

## 10. Refresh and clean uninstall

### 10.1 Refresh

There are **three** independent kinds of "refresh": keeping the **index** in sync with your sources
(now largely **automatic**), being **notified** when a newer **Sertor version** is available (also
automatic — but only a notice), and pulling the latest **Sertor build** onto the host (the action you
take).

#### Keeping the index fresh — automatic (E10-FEAT-011)

Since FEAT-011, `sertor install rag` wires two host hooks so the corpus stays fresh **without relying
on anyone remembering to re-index**:

- **SessionEnd — `rag-freshness.py`**: at the end of every agent session it returns **immediately**
  (it does **not** stall the session close, even on a large repo — E10-FEAT-016) by launching a
  **detached background worker**. The worker, through the CLI vehicles only (it never imports the
  library), runs `sertor-rag doctor` → writes the verdict to **`.sertor/.rag-health.json`** (schema
  `rag.health/1`; `healthy` when `doctor` passes, otherwise `degraded` with the reason) → then an
  **unconditional** `sertor-rag index .`. The re-index is incremental (FEAT-009 manifest + embedding
  cache), so when nothing changed it is **near-free**; there is deliberately no change-detection
  inside the hook. Because the work runs in the background, the recorded verdict can be **at most one
  session behind**. The hook is **non-fatal** (always exits 0) and **invokes no LLM**.
- **SessionStart — `rag-freshness-start.py`** (Claude; on the Copilot CLI it is a static startup
  prompt instead of a script): it re-reads `.sertor/.rag-health.json` and, **only if the last verdict
  was `degraded`**, tells the agent to run `sertor-rag index .` and/or reconnect the MCP server
  **before** working — so it never reasons on stale context. A `healthy` verdict is a silent no-op.

This moves the mechanical "re-index + health check" steps from the agent's discretion to a
deterministic harness (the agent keeps the judgment; the hook does the mechanics). The hooks are
**portable Python**, run via `uv run --no-project python`, so they work on Windows, macOS and Linux
with **no PowerShell dependency** (`uv` is already the package prerequisite). The state file
`.sertor/.rag-health.json` is **git-ignored** (regenerable, never versioned).

> **Manual re-index is still available** any time — right after a large change:
> `uv run --project .sertor sertor-rag index .`, and `uv run --project .sertor sertor-rag
> doctor` to check health on demand.

#### Update notice — you're on an old Sertor (E2-FEAT-013)

This is a **third**, distinct kind of "refresh": being **told** when a newer Sertor build is
available. It is **not** the index freshness above (that keeps the *corpus* in sync with your
sources) and **not** the manual *Pulling the latest Sertor build* below (the action you take) — it is
just the **notice about the Sertor version**. Like the index-freshness hooks, `sertor install rag`
wires it as two host hooks (parity Claude / Copilot CLI):

- **SessionEnd — `version-check.py`**: at most **~once per day** (cached) it does a single `GET` of
  the `/VERSION` file on `master` (the public raw URL; override with the env var
  **`SERTOR_VERSION_CHECK_URL`**) and compares it to the version that was stamped **at install time**
  into `.sertor/.sertor-version`. It writes the result to **`.sertor/.version-check.json`** (schema
  `version.check/1`). It is **non-fatal** (always exits 0), **invokes no LLM** and runs **no Python**
  (it reads the install-time stamp, never `importlib.metadata`). **Offline → silent skip.** Privacy:
  the only network egress is the `GET` of the public `/VERSION`; no project content or secret is sent,
  and the state file holds only public version numbers.
- **SessionStart — `version-check-start.py`** (Claude; on the Copilot CLI it is a **static startup
  prompt** instead of a script): if the installed version is **behind**, it **warns** you and points
  to the update command (`sertor upgrade`, or `uvx --refresh …` — see *Pulling the latest Sertor build*
  below). It is **only a notice — never an auto-upgrade**: you decide when to update.

Like the RAG-freshness hooks, these are **portable Python** (run via `uv run --no-project python`)
and need **no PowerShell**. The state file `.sertor/.version-check.json` and the stamp
`.sertor/.sertor-version` are **git-ignored** (regenerable, never versioned).

#### Pulling the latest Sertor build onto a host

The interim distribution is an **unpinned `git+url`**, and `uvx` **caches** the built tool per
resolved revision. After Sertor's `master` moves, a plain `uvx … sertor install …` may reuse a
**stale build** (e.g. an installer without a new `--assistant` value, or with an old MCP layout). Force
a rebuild from the latest `master` with `--refresh`:

```powershell
# Rebuild the installer from the latest master, then re-run the install (idempotent):
uvx --refresh --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor install rag --assistant copilot-cli --backend azure
# Sanity check you are on the fresh build (the error lists the valid assistants, incl. copilot-cli):
uvx --refresh --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor install rag --assistant bogus
```

Then refresh the **index** (the runtime package itself is updated inside `.sertor/` by re-running
the install, which does `uv add` again):

```powershell
uv run --project .sertor sertor-rag index .   # rebuild the corpus with the new code
```

> `sertor install` is **idempotent and non-destructive**: re-running never overwrites your edits and
> never *removes* a previously written artifact. To refresh asset content that Sertor authored (a
> renamed hook, an updated instruction block) **and** remove artifacts that a new version dropped
> from the bundle, use the dedicated **`sertor upgrade`** verb (below) — it updates changed
> Sertor-owned files/blocks and prunes obsolete ones, while leaving your content alone.

### 10.2 Lifecycle commands: `upgrade` and `uninstall` (recommended)

Since FEAT-008 the installer has first-class **`upgrade`** and **`uninstall`** verbs (on both
`sertor` and `sertor-flow`). They are the **primary** way to maintain a host — use them instead of
the manual procedure in §10.3. All are **idempotent, non-destructive on shared files** (only Sertor's
own marker blocks / hook entries / `.gitignore` lines are touched, byte-for-byte elsewhere),
`--dry-run`-able, and never start an index/run (install ≠ run).

```powershell
# Upgrade everything installed (refresh changed assets/blocks, remove obsoletes):
uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor upgrade
# Or a single capability, projecting first:
sertor upgrade rag --dry-run
sertor upgrade rag                       # refresh the installed assistant(s), in place

# Uninstall (per capability or all-in-one). The wiki/ dir is PRESERVED by default:
sertor uninstall rag                     # remove the RAG runtime + shared edits + MCP entry
sertor uninstall                         # all installed capabilities + a pointer for governance
sertor uninstall wiki --purge-wiki --yes # also delete wiki/ (opt-in, needs --yes or a TTY)

# Governance (separate package, symmetric verbs):
sertor-flow upgrade
sertor-flow uninstall
```

**Auto-detection (a bare verb operates on what is actually installed).** `sertor upgrade` /
`sertor uninstall` with no capability and no `--assistant` resolve to the capabilities and
assistants **actually present** on the host: they never bootstrap a capability the host didn't
have, and — with **both** Claude and Copilot installed — a bare `upgrade` refreshes **both** and
strips **neither**. Pass a capability (`upgrade rag`) or `--assistant <name>` only to narrow the
scope on purpose.

**Switching assistant is a consented, non-silent action.** An **explicit** `sertor upgrade rag
--assistant copilot-cli` on a host that *also* has Claude installed is an **assistant switch**: it
removes the coexisting Claude surfaces. Because that is destructive, it is never silent — on a TTY
it prompts `[y/N]`; non-interactively it requires **`--yes`**; otherwise it stops with an actionable
usage error (exit 2) that names what would be removed. To upgrade both instead, omit `--assistant`.

Notes on `--purge-wiki` (decision D4, CI-safe): without it the `wiki/` directory is kept; with
`--yes` it is removed (after printing a page/byte count); on a TTY without `--yes` it prompts; with
**no** TTY and no `--yes` it is **preserved** (a safe default for pipelines, with an actionable
warning); `--purge-wiki --dry-run` is a **usage error** (exit 2). Exit codes: `0` success (even when
everything is `skipped`), `1` domain error (fail-fast, the failed step is named), `2` usage error.
`sertor uninstall rag` with a local-scope MCP de-registers the server via `claude mcp remove`; if
`claude` is absent the command stops with the manual fallback command.

### 10.3 Manual uninstall (fallback / historical)

> **Prefer §10.2.** The manual procedure below is a **fallback** for environments without the
> packaged commands and a reference for *what* Sertor writes. It is hand-maintained and **may drift**
> from the installer — the `sertor uninstall` / `sertor-flow uninstall` commands are the source of
> truth. Sertor writes in four kinds of places — handle each accordingly:

| Kind | What | How to remove |
|---|---|---|
| **A. Isolated runtime** | `.sertor/` — the venv, `.env`, the **Chroma** vector store, the **SQLite** files (`embed_cache.sqlite`, `observability.sqlite`, `memory.sqlite`), the code graph, `pyproject.toml`/`uv.lock` | **delete the whole folder** |
| **B. Standalone assets** | `wiki/` (incl. `wiki/wiki.config.toml`), `.specify/` (incl. `memory/constitution.md`), the Sertor files under `.claude/**` or `.github/**` | delete folders/files |
| **C. Shared files Sertor merged into** | marker blocks in `CLAUDE.md`/`.github/copilot-instructions.md`; hook entries in `.claude/settings.json`/`.github/hooks/sertor-hooks.json`; the appended lines in `.gitignore` | **edit out only Sertor's parts** (do not delete the whole file) |
| **D. Client-side registration** | local-scope MCP (`claude mcp add-json … --scope local`); Copilot CLI user config `~/.copilot/mcp-config.json` | unregister in the client |

**Inventory of what to remove** (per assistant):

- **Runtime (A):** `.sertor/`
- **MCP config (B/C):** `.mcp.json` (Claude / Copilot CLI — remove the `sertor-rag` entry, or delete
  the file if it held only that server) · `.vscode/mcp.json` (Copilot in VS Code) · `.github/mcp.json`
  (Copilot CLI alternative location, if used)
- **Wiki (B):** `wiki/`
- **Governance (B):** `.specify/`
- **Claude assets (B):** `.claude/skills/wiki-author/`, `.claude/skills/requirements/`,
  `.claude/commands/wiki.md`, `.claude/commands/speckit.*.md`, `.claude/agents/wiki-curator.md`,
  `.claude/agents/requirements-analyst.md`, `.claude/agents/configuration-manager.md`,
  `.claude/hooks/wiki-pending-check.py`, `.claude/hooks/sertor-rag-usage-check.py`,
  `.claude/hooks/_hooklib.py`
- **Copilot CLI assets (B):** `.github/agents/wiki.agent.md`, `.github/agents/wiki-author.agent.md`,
  `.github/agents/wiki-curator.agent.md`, `.github/agents/requirements.agent.md`,
  `.github/agents/requirements-analyst.agent.md`, `.github/agents/configuration-manager.agent.md`,
  `.github/prompts/speckit.*.prompt.md` (these SpecKit prompts come from the upstream installer),
  `.github/hooks/wiki-pending-check.py`, `.github/hooks/sertor-rag-usage-check.py`,
  `.github/hooks/_hooklib.py`,
  `.github/hooks/sertor-hooks.json`. **Legacy VS Code residue** (if you ever installed the removed
  `copilot` target): `.vscode/mcp.json` and `.github/prompts/{wiki,wiki-author,requirements}.prompt.md`
  — see the migration note in [install-copilot.md](install-copilot.md#migrating-from-the-vs-code-target).
- **Shared (C):** in `CLAUDE.md`/`.github/copilot-instructions.md` delete the three marker blocks
  `SERTOR:WIKI-RITUAL`, `SERTOR:RAG-USAGE`, `SERTOR:SDLC-RITUAL` (markers included); in
  `.claude/settings.json` remove the Sertor hook entries (or delete `.github/hooks/sertor-hooks.json`
  if Sertor-only); in `.gitignore` remove the lines `.sertor/.venv/`, `.sertor/.index*`, `.sertor/.env`
- **Client (D):** `claude mcp remove sertor-rag` (only if you installed with `--mcp-scope local`); for
  the Copilot CLI, drop `sertor-rag` from `~/.copilot/mcp-config.json` if you registered it there

**Helper script (PowerShell).** Run from the **host repo root**. It deletes A/B, strips the marker
blocks and `.gitignore` lines (C), unregisters the local MCP (D), and finally greps for any leftover
reference. Review before running — it is **destructive**.

```powershell
# 0. Close VS Code / the Copilot CLI / Claude first (so files are not locked).
# 1. A — isolated runtime (Chroma + all SQLite + venv + .env + graph):
Remove-Item -Recurse -Force .sertor -ErrorAction SilentlyContinue
# 2. B — standalone assets:
Remove-Item -Recurse -Force wiki, .specify -ErrorAction SilentlyContinue
Remove-Item -Force .claude\commands\wiki.md, .claude\agents\wiki-curator.md, .claude\agents\requirements-analyst.md, .claude\agents\configuration-manager.md, .claude\hooks\wiki-pending-check.py, .claude\hooks\sertor-rag-usage-check.py, .claude\hooks\_hooklib.py -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .claude\skills\wiki-author, .claude\skills\requirements -ErrorAction SilentlyContinue
Get-ChildItem .claude\commands\speckit.*.md -ErrorAction SilentlyContinue | Remove-Item -Force
# Copilot CLI layout (if you installed for copilot-cli) — delete ONLY Sertor's files, not the
# whole .github/{agents,hooks} dirs (they may hold your own content):
Remove-Item -Force .github\agents\wiki.agent.md, .github\agents\wiki-author.agent.md, .github\agents\wiki-curator.agent.md, .github\agents\requirements.agent.md, .github\agents\requirements-analyst.agent.md, .github\agents\configuration-manager.agent.md, .github\hooks\wiki-pending-check.py, .github\hooks\sertor-rag-usage-check.py, .github\hooks\_hooklib.py, .github\hooks\sertor-hooks.json -ErrorAction SilentlyContinue
Get-ChildItem .github\prompts\speckit.*.prompt.md -ErrorAction SilentlyContinue | Remove-Item -Force
# Legacy VS Code residue (if you ever used the removed `copilot` target):
Remove-Item -Force .github\prompts\wiki.prompt.md, .github\prompts\wiki-author.prompt.md, .github\prompts\requirements.prompt.md -ErrorAction SilentlyContinue
# 3. MCP config files (delete if Sertor was the only server; otherwise edit out the sertor-rag entry):
Remove-Item -Force .mcp.json, .vscode\mcp.json, .github\mcp.json -ErrorAction SilentlyContinue
# 4. C — strip Sertor marker blocks + .gitignore lines from SHARED files (kept, only edited):
foreach ($f in @("CLAUDE.md", ".github\copilot-instructions.md")) {
  if (Test-Path $f) {
    $t = Get-Content $f -Raw
    foreach ($m in @("WIKI-RITUAL","RAG-USAGE","SDLC-RITUAL")) {
      $t = [regex]::Replace($t, "(?s)<!-- SERTOR:$m START -->.*?<!-- SERTOR:$m END -->\r?\n?", "")
    }
    Set-Content $f $t -NoNewline
  }
}
if (Test-Path .gitignore) {
  (Get-Content .gitignore) | Where-Object { $_ -notin @(".sertor/.venv/", ".sertor/.index*", ".sertor/.env") } | Set-Content .gitignore
}
# Review .claude\settings.json by hand: remove the entries whose command mentions sertor/wiki-pending/rag-usage.
# 5. D — client-side MCP registration (local scope), ignore error if not present:
claude mcp remove sertor-rag 2>$null
# 6. Verify nothing is left:
Get-ChildItem -Recurse -File | Select-String -Pattern "sertor" -List | Select-Object Path
```

> **What survives on purpose.** This removes Sertor from the *host*. It does **not** touch the global
> `uvx` tool cache — clear that separately with `uv cache clean` if you want to drop the cached
> Sertor builds too. And it does not delete your own content that happened to live under `wiki/`
> (back it up first if the wiki accumulated real documentation you want to keep).
