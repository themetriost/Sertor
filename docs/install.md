# Installing Sertor on another repository

> **Status.** Sertor is not yet on PyPI: the interim distribution is **`git+url`** (decision DA-4
> of the CLI epic). This guide covers all the installable capabilities: the **full RAG capability**
> (indexing + search + MCP server) and the guided **`sertor install rag`** (§6); the **deterministic
> wiki tooling** and the guided **`sertor install wiki`** that brings the entire wiki system to the
> host with one command (§5); and the **development method (SDLC)** via the separate, RAG-independent
> package **`sertor-flow`** (§8). Each is non-destructive and idempotent — **install ≠ run**.
>
> **Target assistant.** The installers accept **`--assistant`** (default `claude`) to choose which
> host AI assistant receives the surfaces: `claude` (`.claude/**` + `.mcp.json` + `CLAUDE.md`),
> `copilot` (GitHub Copilot **in VS Code**: `.github/**` + `.vscode/mcp.json`), or `copilot-cli`
> (GitHub **Copilot CLI**: `.github/**` + `.mcp.json` with the `mcpServers` root). The `sertor`
> installer supports all three; `sertor-flow` supports `claude|copilot`. See **§9**.

## Prerequisites

- **Python ≥ 3.11** and [`uv`](https://github.com/astral-sh/uv) (recommended; `pip` as an alternative).
- An **embeddings** provider, of your choice:
  - **local** — [Ollama](https://ollama.com) running (`ollama serve`) with an embedding model:
    `ollama pull nomic-embed-text`;
  - **cloud** — an **Azure OpenAI** deployment of `text-embedding-3-*`.

## 1. Package installation

In the target repository:

```bash
# base (local: Ollama + Chroma)
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

All operational choices are read from the centralised configuration (env and/or `.env`). Minimum
required:

**Local (default):**
```bash
RAG_BACKEND=local
OLLAMA_HOST=http://localhost:11434     # default, can be omitted
SERTOR_CORPUS=my-project              # collection namespace (recommended)
```

**Azure (cloud embeddings + local Chroma store — recommended combination):**
```bash
RAG_BACKEND=azure
SERTOR_STORE_BACKEND=local             # local Chroma vector store
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_EMBED_DEPLOYMENT=text-embedding-3-large
SERTOR_CORPUS=my-project
```

If the configuration for the chosen backend is incomplete, every command **stops before contacting
any service**, listing the missing variables. Useful optional settings: `SERTOR_INDEX_DIR` (index
directory, default `.index` — add it to the host's `.gitignore`), `SERTOR_EXCLUDE_PATTERNS`,
`DEFAULT_K`, `SERTOR_PREVIEW_CHARS`.

**Retrieval engine (FEAT-004):** the default is the **hybrid** engine (lexical BM25 + vector
fused with RRF) — significantly improves symbol/exact-term queries:

```bash
SERTOR_ENGINE=hybrid       # baseline | hybrid (default: hybrid)
SERTOR_RRF_C=60            # RRF fusion constant
SERTOR_RRF_POOL=30         # candidates per source before fusion
SERTOR_RERANK=false        # second-stage cross-encoder (requires the `rerank` extra)
SERTOR_RERANK_POOL=15      # fused pool passed to the reranker (~3×k)
```

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
re-embeds the whole corpus. Enable the content-hash cache so re-indexing an **unchanged** corpus
does not re-embed identical chunks — only changed/new chunks are sent to the provider:

```bash
SERTOR_EMBED_CACHE=true     # default: false (full re-embed on every rebuild)
```

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
uv run sertor install wiki --assistant copilot      # target GitHub Copilot instead of Claude (§9)
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
or `2` (wrong usage). Re-running is safe: identical state, zero duplicates. Prerequisite for the
session hook: PowerShell (`pwsh`) on the host; without it, the wiki remains fully usable (automatic
reminders do not fire).

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
uv run sertor install rag --backend local --no-rerank   # Ollama, without reranker
uv run sertor install rag --no-deps                      # config scaffold only (no uv add)
uv run sertor install rag --mcp-scope local              # no .mcp.json in the repo (registers in the client)
uv run sertor install rag --assistant copilot            # target GitHub Copilot: .vscode/mcp.json (§9)
uv run sertor install rag --target C:\path\repo --corpus myproject --json
```

What it does (all **without** indexing — install ≠ run):

| Artifact | Where | Behaviour if already present |
|---|---|---|
| Python project + dependencies (`uv init --bare` + `uv add sertor-core[azure,mcp,graph,rerank]`) | `<target>/.sertor/` | `uv add` idempotent; `uv init` skipped if already initialised |
| `.env` (backend template, **empty secrets** to fill in) | `<target>/.sertor/.env` | additive per-key merge (never overwrites your values) |
| `.mcp.json` (`sertor-rag` server via `uv run --directory .sertor`) — scope `project` (default) | **host root** | additive merge (preserves other MCP servers) |
| MCP registration in the client (`claude mcp add-json … --scope local`) — scope `local` | **outside the repo** (`~/.claude.json`) | idempotent (skip if already registered); fail-fast if `claude` is missing |
| `.gitignore` (`.sertor/.venv/`, `.sertor/.index*`, `.sertor/.env`) | **host root** | append dedup |

Default: `azure` backend, all extras (`mcp`+`graph`+`rerank`) plus the backend's own; `--no-graph`
/`--no-rerank` to reduce scope, `--no-deps` for scaffold only. Exit `0`/`1` (domain error,
fail-fast: `uv` absent or `uv add` failed)/`2` (wrong usage). Re-running is safe (identical state).

After installation (explicit separate step — fill in the secrets in `.sertor/.env` first):

```bash
uv run --directory .sertor sertor-rag index ..   # index host sources, excluding `.sertor/`
# then reload the MCP client: approve the `sertor-rag` server → search_code/docs/combined (+ graph)
```

> **Self-locating runtime.** `sertor-rag`/`sertor-wiki-tools` load `.sertor/.env` and keep the
> index and graph inside `.sertor/` **from any cwd**: if there is no `.env` in the cwd, the CLI
> uses the one next to its own venv (`.sertor/`). The `uv run --directory .sertor …` form remains
> recommended (the MCP server uses it), but you are no longer forced to launch from inside
> `.sertor/`. If no `.env` or `RAG_BACKEND` is found, it warns instead of silently falling back to
> `local`/Ollama.
> **Uninstall** ≈ delete `.sertor/` and the `sertor-rag` entry from `.mcp.json`.

> **Distribution note (interim).** Standalone execution via `uvx --from "git+…#subdirectory=packages/sertor"`
> is **verified**: `uv` resolves `sertor-core` by discovering the workspace from the git checkout
> (it builds it from the same repo, not from PyPI). When developing from the Sertor repo, use
> `uv run sertor install rag`.

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
sertor-flow install --assistant copilot       # target GitHub Copilot instead of Claude (§9)
sertor-flow install --json                    # machine-readable report
```

**SpecKit is launched, not vendored (feature 045).** `sertor-flow` no longer ships frozen copies of
the SpecKit commands/agents and `.specify/**`. Instead it **launches the official spec-kit
installer** for the target assistant, at a **pinned** upstream version:

```text
uvx --from git+https://github.com/github/spec-kit.git@v0.8.18 \
    specify init . --here --ai <claude|copilot> --script <ps|sh> --no-git --force
```

This deposits the per-assistant SpecKit layout (Claude `.claude/commands/speckit.*` · Copilot
`.github/prompts/speckit.*.prompt.md`) plus the shared `.specify/**` machinery. **Prerequisite
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

By default the installers write the **Claude Code** layout. Pass `--assistant` to target GitHub
Copilot instead. There are **two Copilot targets**, because the VS Code agent and the CLI read the
MCP server from **different files**:

- **`--assistant copilot`** — GitHub Copilot **in VS Code** (MCP in `.vscode/mcp.json`, root key `servers`).
- **`--assistant copilot-cli`** — GitHub **Copilot CLI** (MCP in `.mcp.json`, root key `mcpServers`).

Both reuse the same `.github/**` containers for instructions, prompts, agents and hooks (the CLI
reads those too). The *content* of every surface is reused; only the *container* (path, format, JSON
root key) is translated. Default is `claude`; an unknown value stops with an explicit error listing
the valid ones.

| Logical surface | Claude | Copilot (VS Code) | Copilot CLI |
|---|---|---|---|
| Instruction / ritual block | `CLAUDE.md` | `.github/copilot-instructions.md` | `.github/copilot-instructions.md` |
| MCP server (`sertor-rag`) | `.mcp.json` (`mcpServers`) | `.vscode/mcp.json` (`servers`) | `.mcp.json` (`mcpServers`) |
| Hook wiring | `.claude/settings.json` | `.github/hooks/sertor-hooks.json` | `.github/hooks/sertor-hooks.json` |
| Command / skill | `.claude/commands/<name>.md` | `.github/prompts/<name>.prompt.md` | `.github/prompts/<name>.prompt.md` |
| Agent persona | `.claude/agents/<name>.md` | `.github/agents/<name>.agent.md` | `.github/agents/<name>.agent.md` |

Commands are single-line so they work as-is in **PowerShell** and POSIX shells:

```powershell
# RAG for the GitHub Copilot CLI (MCP lands in .mcp.json with the mcpServers root):
uv run sertor install rag --assistant copilot-cli --backend azure
# RAG for Copilot in VS Code (MCP lands in .vscode/mcp.json):
uv run sertor install rag --assistant copilot --backend azure
# Wiki system for Copilot (instructions in .github/copilot-instructions.md):
uv run sertor install wiki --assistant copilot-cli
```

After installing for the **Copilot CLI**, reload its MCP config with `/mcp reload` (or restart the
CLI) and verify with `/mcp show`. The CLI discovers `.mcp.json` walking from the cwd up to the git
root (closest wins); `.github/mcp.json` and the user-level `~/.copilot/mcp-config.json` are also
read.

The same invariants hold for every assistant: **install ≠ run**, non-destructive (existing files are
never overwritten — merges are additive and per-file writes skip), idempotent, and secrets are never
written (the `.env` template ships with empty values).

> **Two Copilot surfaces, one cause.** The VS Code Copilot agent reads `.vscode/mcp.json` (`servers`
> root); the Copilot **CLI** removed support for that file and reads `.mcp.json`/`.github/mcp.json`
> with the `mcpServers` root. Use `--assistant copilot` for the former, `--assistant copilot-cli` for
> the latter. **Scope:** the `copilot-cli` target currently covers the **`sertor`** package
> (`install rag`/`install wiki`); the governance installer `sertor-flow` still targets
> `claude|copilot` only (SpecKit-side support for the CLI is a follow-up). A further assistant
> (`codex` → `AGENTS.md`) is planned but not yet implemented.
