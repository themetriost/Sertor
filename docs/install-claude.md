# Install Sertor — Claude Code

Get Sertor onto a repository whose AI assistant is **Claude Code**. Three capabilities, three
sections — install each on its own, or all three. Every installer is **non-destructive**,
**idempotent**, and **install ≠ run** (nothing is indexed until you ask).

> **Looking for GitHub Copilot?** See **[install-copilot.md](install-copilot.md)**.
> **All flags, every config knob, refresh & uninstall?** See the full reference **[install.md](install.md)**.

## Prerequisites

- **Python ≥ 3.11** and **[`uv`](https://github.com/astral-sh/uv)** (the supported install path).
- Network access to GitHub (Sertor ships via `git+url`, not PyPI yet).
- An **embeddings provider** for the RAG. The default **`glove`** is **zero-config** (static GloVe
  vectors, downloaded once per machine, offline afterwards) — **nothing to install or run**. Opt into
  **Azure OpenAI** (`text-embedding-3-*`, best quality, needs credentials) or a local
  **[Ollama](https://ollama.com)** server explicitly.

Run each command **in the root of the target repository**.

---

## 1. RAG — search your codebase by meaning

Bring the full retrieval capability (index + search + MCP server) into an isolated `.sertor/`
runtime. Your sources are never touched; works even on non-Python repos.

```powershell
# 1. install (Azure embeddings; use --backend local for the zero-config `glove` embedder)
uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor install rag --backend azure

# 2. fill the secrets in .sertor/.env — guided (no editor) or by hand:
uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor configure --backend azure
#    prompts for AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY (masked).
#    Skip this step entirely with --backend local: `glove` needs no secrets.

# 3. index the repo (explicit step — install never indexes)
uv run --project .sertor sertor-rag index .
```

Then **reload Claude Code** and approve the **`sertor-rag`** MCP server (added to `.mcp.json`): the
`search_code` / `search_docs` / `search_combined` tools now answer over your code and docs. Quick
check from the terminal: `uv run --project .sertor sertor-rag search "how does X work?"`.

> **Invoking the CLIs.** After `install rag` the runtime CLIs (`sertor-rag`, `sertor-wiki-tools`) live
> in `.sertor/.venv` and are **NOT on `PATH`**. Always invoke them with
> **`uv run --project .sertor <cli> …`** — it runs the `.sertor` runtime but keeps your current
> directory, so relative paths like `index .` resolve from the project root (use `--project`, NOT
> `--directory`: `--directory` would change the cwd to `.sertor`, making `index .` index `.sertor`
> itself). A bare `sertor-rag …` (or `which sertor-rag`) failing means "not on `PATH`", **not** "not
> installed".

> **Stays fresh automatically (E10-FEAT-011).** `install rag` also wires two hooks so you don't have to
> remember to re-index: a **SessionEnd** hook (`.claude/hooks/rag-freshness.py`) that re-indexes
> (incremental — near-free when nothing changed) and runs `doctor` at the end of each session, writing
> the verdict to `.sertor/.rag-health.json`; and a **SessionStart** hook
> (`.claude/hooks/rag-freshness-start.py`) that, if that verdict was `degraded`, nudges Claude to
> re-index / reconnect the MCP server before working. The hooks are portable Python (run via
> `uv run --no-project python`, no PowerShell); they invoke no LLM and never block the session. You can
> still re-index manually with
> `uv run --project .sertor sertor-rag index .`. Details: [install.md §10.1](install.md#101-refresh).

> **Update notice too (E2-FEAT-013).** `install rag` also wires a pair of hooks that **tell you when a
> newer Sertor is available**: a **SessionEnd** hook (`.claude/hooks/version-check.py`) checks the
> remote `/VERSION` at most ~once a day, and a **SessionStart** hook
> (`.claude/hooks/version-check-start.py`) **warns** you at startup if you're behind — pointing to
> `sertor upgrade` / `uvx --refresh`. It is **only a notice, never an auto-upgrade** (you decide when
> to update); it invokes no LLM and skips silently offline. Details:
> [install.md §10.1](install.md#101-refresh).

## 2. Wiki — the project's living knowledge base

Install the **LLM Wiki** system: a cumulative, local knowledge base the assistant maintains as you
work.

```powershell
uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor install wiki
```

Adds (each skipped if already present): the `wiki-author` skill, the `/wiki` command, the
`wiki-curator` agent, session hooks, a `wiki.config.toml`, the `wiki/` structure, and a
`SERTOR:WIKI-RITUAL` block in `CLAUDE.md` (the rest of the file is left intact).

## 3. Governance — the development method (SDLC)

Install **`sertor-flow`**: the SpecKit flow, requirements management, git delegation, a neutral
constitution starter, and the SDLC ritual block. It is a **separate package, orthogonal to the
RAG** (no dependency on `sertor-core`).

```powershell
uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor-flow" sertor-flow install
```

Adds the SpecKit commands/agents (launched from the pinned upstream installer — needs network at
install time), the `requirements` skill + `requirements-analyst`/`configuration-manager` agents, the
constitution starter, and a `SERTOR:SDLC-RITUAL` block in `CLAUDE.md` (coexists with the wiki block).

---

## Known environment notes

- **Windows + system Python 3.14 / `pywin32`.** A stale `pywin32` on the *system* interpreter may print
  `ModuleNotFoundError: No module named 'pywin32_bootstrap'` on `pip`/`python -m`. This is noise from the
  system Python, **not a Sertor error** — Sertor's CLIs and MCP server run inside `.sertor/.venv` via
  `uv run`, unaffected. Do not use the system `pip show sertor-rag` to check the install; use
  `uv run --project .sertor sertor-rag doctor`.

---

*Default assistant is `claude`, so no `--assistant` flag is needed above. Add `--target <path>` to
install onto a different directory. For upgrades and clean removal, see
[install.md §10](install.md#10-refresh-and-clean-uninstall).*
