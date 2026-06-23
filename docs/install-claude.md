# Install Sertor — Claude Code

Get Sertor onto a repository whose AI assistant is **Claude Code**. Three capabilities, three
sections — install each on its own, or all three. Every installer is **non-destructive**,
**idempotent**, and **install ≠ run** (nothing is indexed until you ask).

> **Looking for GitHub Copilot?** See **[install-copilot.md](install-copilot.md)**.
> **All flags, every config knob, refresh & uninstall?** See the full reference **[install.md](install.md)**.

## Prerequisites

- **Python ≥ 3.11** and **[`uv`](https://github.com/astral-sh/uv)** (the supported install path).
- Network access to GitHub (Sertor ships via `git+url`, not PyPI yet).
- An **embeddings provider** for the RAG: **Azure OpenAI** (`text-embedding-3-*`) *or* local
  **[Ollama](https://ollama.com)** (`ollama pull nomic-embed-text`).

Run each command **in the root of the target repository**.

---

## 1. RAG — search your codebase by meaning

Bring the full retrieval capability (index + search + MCP server) into an isolated `.sertor/`
runtime. Your sources are never touched; works even on non-Python repos.

```powershell
# 1. install (Azure embeddings; use --backend local for Ollama)
uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor install rag --backend azure

# 2. edit .sertor/.env and fill the empty secrets:
#    AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY (skip for --backend local)

# 3. index the repo (explicit step — install never indexes)
uv run --directory .sertor sertor-rag index ..
```

Then **reload Claude Code** and approve the **`sertor-rag`** MCP server (added to `.mcp.json`): the
`search_code` / `search_docs` / `search_combined` tools now answer over your code and docs. Quick
check from the terminal: `uv run --directory .sertor sertor-rag search "how does X work?"`.

> **Invoking the CLIs.** After `install rag` the runtime CLIs (`sertor-rag`, `sertor-wiki-tools`) live
> in `.sertor/.venv` and are **NOT on `PATH`**. Always invoke them with
> **`uv run --directory .sertor <cli> …`** (works from any cwd; the same form the MCP server uses). A
> bare `sertor-rag …` (or `which sertor-rag`) failing means "not on `PATH`", **not** "not installed".

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
  `uv run --directory .sertor sertor-rag doctor`.

---

*Default assistant is `claude`, so no `--assistant` flag is needed above. Add `--target <path>` to
install onto a different directory. For upgrades and clean removal, see
[install.md §10](install.md#10-refresh-and-clean-uninstall).*
