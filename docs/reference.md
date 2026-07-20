# User reference: commands & configuration knobs

A quick lookup for the commands you run and the settings you can tune. This is the **short** reference;
for every flag, edge case, refresh and uninstall detail, see the full **[install.md](install.md)**.

Everything here is host-agnostic (Claude Code and GitHub Copilot CLI). Assistant-specific differences are
noted inline or in the per-assistant guides ([Claude](install-claude.md) · [Copilot](install-copilot.md)).

## Two levels of command

Sertor is used through two entry points — know which is which:

| Level | How you invoke it | What it's for |
|---|---|---|
| **Installer** | `uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor …` | install / upgrade / configure the capability |
| **Runtime CLI** | `uv run --project .sertor sertor-rag …` | index, search, and operate an installed project |

The runtime CLIs (`sertor-rag`, `sertor-wiki-tools`) live in `.sertor/.venv` and are **not on your
`PATH`** — always route them through `uv run --project .sertor`. A bare `sertor-rag …` failing means
"not on `PATH`", **not** "not installed".

## Installer commands (`sertor` / `sertor-flow`)

Run from the **root of the target repository**. Add `--assistant copilot-cli` for a Copilot host
(default is `claude`); add `--target <path>` to install onto another directory.

| Command | What it does |
|---|---|
| `sertor install rag [--backend local\|azure]` | install the RAG capability into an isolated `.sertor/` runtime |
| `sertor install wiki` | install the LLM Wiki system |
| `sertor configure [--backend azure]` | fill `.sertor/.env` secrets guided (no editor) |
| `sertor upgrade` / `sertor uninstall` | refresh, or cleanly remove, an installed capability |
| `sertor-flow install` | install the SDLC / SpecKit development method (separate package) |

> Distribution is **interim via `git+url`** (not PyPI yet). To pull the latest build after Sertor's
> `master` moves, add `--refresh` to the `uvx` command (it caches per git revision).

## Runtime CLI — `sertor-rag`

Invoke as `uv run --project .sertor sertor-rag <command>`:

| Command | What it does |
|---|---|
| `index .` | index the repository (incremental by default) |
| `search "<question>"` | query the index, top-k results by meaning, with sources |
| `doctor [--online] [--json]` | deterministic health check (env / provider / index / MCP) — *"did it work?"* |
| `eval` / `graph-eval` | ground-truth evaluation of retrieval / code-graph quality + non-regression gate |
| `memory <archive\|search\|list\|show>` | local episodic conversation memory (opt-in) |
| `observe` | open the live observability panel (TUI) |

The **MCP server** (`sertor-rag`, added to `.mcp.json`) exposes the same retrieval to your assistant:
`search_code` / `search_docs` / `search_combined` + the graph tools `find_symbol` / `who_calls` /
`related_docs` / `get_context` + — when conversation memory is enabled (`SERTOR_MEMORY=true`, opt-in) —
the read-only memory tools `memory_search` / `memory_list` / `memory_show` (same data as the `memory`
CLI commands; they return `{"status": "disabled"}` when memory is off). See
[searching a project](retrieval.md) for when to use which.

## Configuration knobs (`.sertor/.env`)

Settings live in `.sertor/.env` (never committed). The most common ones:

| Knob | Values / default | What it selects |
|---|---|---|
| `SERTOR_EMBED_PROVIDER` | `glove` (default) · `hash` · `ollama` · `azure` | the embeddings provider — `glove` is zero-config & offline |
| `SERTOR_STORE_BACKEND` | `local` (default) · `azure` | the vector store — independent from the embedder |
| `SERTOR_ENGINE` | `hybrid` (default) · `baseline` | the retrieval engine (hybrid = BM25 + vector, RRF) |
| `SERTOR_GRAPH` | `true` (default) · `false` | build the structural code graph inside `index()` |
| `SERTOR_MEMORY` | `false` (default) · `true` | enable conversation memory (opt-in, privacy-by-default) |
| `SERTOR_MEMORY_SEMANTIC` | `false` (default) · `true` | add semantic search over the memory archive (a second opt-in) |
| `SERTOR_OBSERVABILITY` | `false` (default) · `true` | record local runtime events (opt-in) |

**Azure** (only when a knob is set to `azure`): `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`
(embeddings); `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_API_KEY` (store). **Ollama**: `OLLAMA_HOST`. Fill
secrets with `sertor configure` rather than editing by hand — they are prompted masked and never printed.

> This is the common set. The **full list** of knobs (chunking, RRF/reranking tuning, code-graph limits,
> memory retention, observability/OTel export, eval thresholds) is in **[install.md](install.md)**.

## See also

- [Getting started](getting-started.md) — the single path from nothing to first value.
- [Troubleshooting](troubleshooting.md) — common problems → cause → fix.
- [install.md](install.md) — the exhaustive reference for every flag and knob.
