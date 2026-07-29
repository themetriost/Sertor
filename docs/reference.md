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

> Distribution is **via `git+url`**; there is no PyPI package. To pull the latest build after Sertor's
> default branch moves, add `--refresh` to the `uvx` command (it caches per git revision) — or pin a
> release tag with `@<tag>` for a reproducible setup.

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
CLI commands; they return `{"status": "disabled"}` when memory is off). `memory_search` accepts
`semantic=true` (search by meaning; needs `SERTOR_MEMORY_SEMANTIC` too), mirroring `memory search
--semantic`. See
[searching a project](retrieval.md) for when to use which.

## Runtime CLI — `sertor-wiki-tools`

The deterministic half of the wiki capability (zero LLM, offline). Invoke as
`uv run --project .sertor sertor-wiki-tools <command>`. The most useful ones day to day:

| Command | What it does |
|---|---|
| `scan` | is there work not yet recorded in the wiki? Names the files (see below) |
| `lint` / `validate` | structural checks: broken wikilinks, orphans, frontmatter, naming |
| `append-log` | append a dated log entry (body from a file or stdin) |
| `ritual-check` | list this step's distill/drift candidates + a declaration scaffold |
| `distill-audit` | candidate entities referenced from several places but with no page |
| `structure init` | create the wiki folder structure (idempotent) |

### How `scan` decides — and why it tells you

`scan` compares your source directories against the last **recording** (the most recent wiki log
entry) and reports what is not covered. **It says how it reached that answer**, because the two ways
are not equally reliable:

| `anchor_kind` | Meaning | Consequences |
|---|---|---|
| `git` | **derived** from history — the anchor is the last commit that touched the wiki log | survives merge/pull/rebase/clone; files your VCS **ignores never count** |
| `mtime` | an **estimate** from file modification times, with the reason stated | used when the project is not a repository (or history is unreadable); may count files a VCS would ignore |

A log entry counts as a recording as soon as it is on disk — **you do not have to commit** to satisfy
the wiki gate. An uncommitted entry from a *previous* day does **not** count, and `scan` names it so
the situation is diagnosable rather than puzzling.

**What an entry covers.** A recording is honoured for the work it was written about, not for the rest
of the day. When you run `append-log`, it records — inside the entry, as an HTML comment — which files
were pending at that moment:

```
<!-- sertor-covers/1
src/some/file.py@<content id>
-->
```

So if you record, then keep working, the new work shows up as pending again: the gate stays useful for
the whole session instead of switching off at the first entry. Editing a file that was already covered
also brings it back — coverage is about the *content* that was recorded, not the file name. You never
write that block by hand, and you should not edit it: a wrong coverage is corrected by a new entry
(the journal is append-only).

**When `scan` could not look.** `determination` is `ok` or `failed`. A `pending: 0` means "nothing to
record" **only** with `determination: "ok"`; with `"failed"` (for example, a concurrent git operation
holding the index) it means "I could not look", and `determination_reason` says why. The session hooks
do **not** block in that case — a broken environment must not make a session unclosable — but they
leave a note in `.sertor/.last-hook-error` instead of reporting a clean verdict.

`scan --json` emits the `wiki.scan/1` contract: `pending`, `pending_paths`, `pending_truncated`,
`anchor`, `anchor_kind`, `anchor_ref`, `anchor_fallback_reason`, `stale_recording`, `determination`,
`determination_reason`, `legacy_coverage` (how many pre-existing entries are being honoured for
compatibility — normally `0`).

### Wiki knobs (`wiki.config.toml`)

Host-specific settings live in `wiki.config.toml` (wiki root, taxonomy, source dirs, language). Two
optional `[ritual]` knobs:

| Knob | Default | Effect |
|---|---|---|
| `pending_paths_limit` | `10` | how many file names `scan` lists (the **count** is always exact) |
| `hub_threshold` | `8` | above this many outgoing links a page counts as a hub in `ritual-check` |

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
