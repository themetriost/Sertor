# Install Sertor — GitHub Copilot

Get Sertor onto a repository whose AI assistant is **GitHub Copilot**. Three capabilities, three
sections. Every installer is **non-destructive**, **idempotent**, and **install ≠ run** (nothing is
indexed until you ask).

> **Using Claude Code?** See **[install-claude.md](install-claude.md)**.
> **All flags, every config knob, refresh & uninstall?** See the full reference **[install.md](install.md)**.

## The Copilot target

Sertor supports **one** Copilot target: the **Copilot CLI**, selected with `--assistant copilot-cli`.
It writes the MCP server to `.mcp.json` (`mcpServers` root, where the CLI looks) and reuses the
`.github/**` containers for instructions, agents and hooks. Use `copilot-cli` in every command below.

> **Coming from the old VS Code target (`copilot`)?** See **[Migrating from the VS Code target](#migrating-from-the-vs-code-target)** at the bottom.

## Prerequisites

- **Python ≥ 3.11** and **[`uv`](https://github.com/astral-sh/uv)** (the supported install path).
- Network access to GitHub (Sertor ships via `git+url`, not PyPI yet).
- An **embeddings provider** for the RAG. The **default is `glove`** — local static word vectors,
  **no credentials**, downloaded once per machine (~822 MB) on the first index. Alternatives:
  **Azure OpenAI** (`text-embedding-3-*`, cloud, billable), local **[Ollama](https://ollama.com)**
  (`ollama pull nomic-embed-text`), or **`hash`** (zero-download lexical floor, for airgapped/CI).

Run each command **in the root of the target repository**.

---

## 1. RAG — search your codebase by meaning

Bring the full retrieval capability (index + search + MCP server) into an isolated `.sertor/`
runtime. Your sources are never touched; works even on non-Python repos.

```powershell
# 1. install — default local embeddings (provider `glove`, no credentials needed)
uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor install rag --assistant copilot-cli --backend local

# 2. index the repo (explicit step — install never indexes).
#    The first index downloads the GloVe vectors once (~822 MB, cached per machine).
uv run --project .sertor sertor-rag index .
```

> **Cloud embeddings instead?** Add `--backend azure` to step 1, then fill `AZURE_OPENAI_ENDPOINT`
> and `AZURE_OPENAI_API_KEY` in `.sertor/.env` **before** indexing. For another local engine set
> `SERTOR_EMBED_PROVIDER=ollama` (or `hash`) in `.sertor/.env`. The default `glove` needs no `.env` editing.

Then load the MCP server: in the **Copilot CLI** run `/mcp reload` (or restart) and verify with
`/mcp show`. The `search_code` / `search_docs` / `search_combined` tools now answer over your code
and docs. Quick check: `uv run --project .sertor sertor-rag search "how does X work?"`.

### Staying fresh automatically (E10-FEAT-011)

`install rag` wires the corpus to stay fresh on its own. A **SessionEnd** hook
(`.github/hooks/rag-freshness.ps1`) re-indexes (incremental — near-free when nothing changed) and runs
`doctor` at the end of each session, recording the verdict in `.sertor/.rag-health.json`. On the
Copilot CLI the **SessionStart** signal is a **static startup prompt** (not a script) that, if the last
verdict was `degraded`, asks the agent to re-index / reconnect the MCP server before working. Needs
`pwsh`; no LLM is invoked by the hook and it never blocks the session. Manual re-index any time:
`uv run --project .sertor sertor-rag index .`. Details: [install.md §10.1](install.md#101-refresh).

There is also an **update notice** (E2-FEAT-013): a **SessionEnd** hook
(`.github/hooks/version-check.ps1`) checks the remote `/VERSION` at most ~once a day, and on the
Copilot CLI the **SessionStart** signal is a **static startup prompt** that **warns** you if you're
behind, pointing to `sertor upgrade` / `uvx --refresh`. It is **only a notice, never an auto-upgrade**
(you decide when to update). Details: [install.md §10.1](install.md#101-refresh).

### Refreshing to the latest Sertor build

`uvx` caches the built installer **per git revision**, so a plain re-run can reuse a **stale build**
after Sertor's `master` moves. Force a fresh build with **`--refresh`**, then re-run the install
(idempotent — it never overwrites your `.env` edits and updates the `.sertor/` runtime via `uv add`):

```powershell
# pull the latest Sertor and refresh the install (assets + runtime)
uvx --refresh --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor install rag --assistant copilot-cli --backend local

# re-index with the updated runtime
uv run --project .sertor sertor-rag index .
```

The same `--refresh` applies to `install wiki` and `sertor-flow install`. To also **remove** assets a
new version dropped (not just refresh changed ones), use the `upgrade` verb — see
[install.md §10](install.md#10-refresh-and-clean-uninstall).

## 2. Wiki — the project's living knowledge base

Install the **LLM Wiki** system: a cumulative, local knowledge base the assistant maintains as you
work.

```powershell
uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor install wiki --assistant copilot-cli
```

Adds (each skipped if already present): the wiki authoring command/skill rendered as custom-agents
under `.github/agents/`, session hooks, a `wiki.config.toml`, the `wiki/` structure, and a
`SERTOR:WIKI-RITUAL` block in `.github/copilot-instructions.md` (the rest of the file is left intact).

## 3. Governance — the development method (SDLC)

Install **`sertor-flow`**: the SpecKit flow, requirements management, git delegation, a neutral
constitution starter, and the SDLC ritual block. It is a **separate package, orthogonal to the RAG**
(no dependency on `sertor-core`).

```powershell
uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor-flow" sertor-flow install --assistant copilot-cli
```

Adds the SpecKit prompts/agents (launched from the pinned upstream installer — needs network at
install time), the `requirements` skill rendered as a custom-agent (`.github/agents/requirements.agent.md`)
+ `requirements-analyst`/`configuration-manager` agents, the constitution starter, and a
`SERTOR:SDLC-RITUAL` block in `.github/copilot-instructions.md`.

> **Note:** all three capabilities (RAG, Wiki, Governance) support the same targets:
> **`claude` and `copilot-cli`**.

## Invoking the agent capabilities (no slash-commands)

Copilot CLI has **no slash-commands** for custom capabilities (that is a Claude/VS Code paradigm — so
`/wiki` does *not* exist here). The Wiki and Governance capabilities are installed as **custom agents**
under `.github/agents/`, and you invoke them with the **`--agent`** flag:

```powershell
copilot --agent wiki          # then give it a brief, e.g. "record this session"
copilot --agent requirements  # the requirements / elicitation capability
```

Other installed agents use the same `copilot --agent <name>` form: `wiki-author`, `wiki-curator`,
`requirements-analyst`, `configuration-manager`. The **RAG** tools, instead, are exposed via the **MCP
server** (section 1) and used by the model automatically once loaded — no agent flag needed.

---

## Migrating from the VS Code target

Earlier releases offered a second Copilot target, **`--assistant copilot`**, for Copilot **in
VS Code** (MCP in `.vscode/mcp.json` with a `servers` root, commands as `.github/prompts/*.prompt.md`).
That target has been **consolidated into `copilot-cli`** — `copilot` is no longer a valid value
(passing it now fails with an explicit error naming `copilot-cli`).

**To update an existing VS Code install:**

1. **Re-install with the CLI target** on the same repo — non-destructive and idempotent:

   ```powershell
   uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor install rag --assistant copilot-cli --backend local
   uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor install wiki --assistant copilot-cli
   uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor-flow" sertor-flow install --assistant copilot-cli
   ```

2. **Remove the leftover VS Code artifacts manually** — there is no automatic cleanup:
   - delete `.vscode/mcp.json` (or just its `servers.sertor-rag` entry, if you keep other servers);
   - delete the Sertor `.github/prompts/*.prompt.md` files (the CLI uses `.github/agents/*.agent.md`);
   - the marker blocks (`SERTOR:WIKI-RITUAL`, `SERTOR:SDLC-RITUAL`, `SERTOR:RAG-USAGE`) in
     `.github/copilot-instructions.md` are reused as-is — no change needed.

*Add `--target <path>` to install onto a different directory. For upgrades and clean removal, see
[install.md §10](install.md#10-refresh-and-clean-uninstall).*
