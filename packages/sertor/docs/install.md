# `sertor install` — capabilities and target assistant

`sertor install <capability>` deposits a Sertor capability into a host repository in a
non-destructive, idempotent way (install ≠ run: nothing is indexed automatically).

## Capabilities

| Capability | Command | What it installs |
|---|---|---|
| RAG | `sertor install rag` | `.sertor/` runtime + MCP server config + RAG-usage instruction block + anti-bypass hook + **RAG-freshness hooks** (SessionEnd re-index + `doctor` → `.sertor/.rag-health.json`; SessionStart induces a fix if degraded — E10-FEAT-011) + **version-check hooks** (SessionEnd GET `/VERSION` ~1/day → `.sertor/.version-check.json`; SessionStart warns if behind, never auto-upgrades — E2-FEAT-013) |
| wiki | `sertor install wiki` | wiki commands/skill, agent, hooks, instruction block + `wiki/` scaffold |
| governance | `sertor install governance` | pointer to the separate `sertor-flow` package |

## `--assistant` (target assistant)

Both `install wiki` and `install rag` accept `--assistant <claude|copilot-cli>`:

```bash
sertor install rag  --assistant copilot-cli
sertor install wiki --assistant copilot-cli
```

- `--assistant` is optional; absent → default **`claude`** (documented).
- An unknown value (e.g. `codex`) → explicit error (exit 1) listing the valid values.
- The legacy VS Code value `copilot` was consolidated into `copilot-cli` and is no longer accepted
  (see the migration note in [install-copilot.md](../../docs/install-copilot.md#migrating-from-the-vs-code-target)).
- The execution CLIs (`sertor-rag`, `sertor-wiki-tools`) are **assistant-agnostic**: no per-assistant
  variant.

### Surface mapping (where artifacts land)

| Surface | `claude` | `copilot-cli` |
|---|---|---|
| Instruction block | `CLAUDE.md` | `.github/copilot-instructions.md` |
| MCP server | `.mcp.json` (`mcpServers`) | `.mcp.json` (`mcpServers`) |
| Commands/skill | `.claude/commands/*`, `.claude/skills/*` | `.github/agents/*.agent.md` (custom-agent) |
| Agent | `.claude/agents/*.md` | `.github/agents/*.agent.md` |
| Hook wiring | `.claude/settings.json` | `.github/hooks/sertor-*.json` |
| Hook script | `.claude/hooks/*.ps1` | `.github/hooks/*.ps1` (same script, reused) |

The instruction-block text, the command/skill body, the agent persona and the hook script are a
**single source** (the canonical Claude asset); the Copilot CLI artifacts are derived by translating
only the container (path/frontmatter). A guard test fails on divergence (anti-drift).

The report declares the **target assistant** and the outcome of every surface in scope; a surface
without a rendering on the chosen assistant is reported as an explicit **gap**, never omitted.

### Operability / notes (per surface)

| Surface | Operability / notes |
|---|---|
| MCP server, instruction block, skill, agent | Operational on **all OSes and targets** — do not depend on `pwsh`. |
| Hook scripts (`.ps1`) | **Require `pwsh` (PowerShell Core) on macOS/Linux.** On Windows: operational via `powershell` (Claude) or `pwsh` (Copilot CLI). Without `pwsh` on macOS/Linux they are installed but **non-operational**; the install report says so in a note (E10-FEAT-018). |
| `memory-capture` (Copilot CLI) | Wired and deposited, but requires **`SERTOR_MEMORY=true` + `SERTOR_MEMORY_ADAPTER=copilot-cli`** to capture Copilot CLI sessions; with defaults it fires but captures nothing useful. The install report declares this; out-of-the-box completion is planned (FEAT-009). |

> The table above states **operability**, not parity: where a surface is operational only with extra
> configuration it is marked as such. For the `pwsh` prerequisite and the per-target operability
> matrix see [`docs/install.md` Prerequisites](../../docs/install.md#prerequisites); for the
> `memory-capture` adapter configuration see
> [`docs/install-copilot.md`](../../docs/install-copilot.md).

## Verifying the install

### RAG (MCP) — Copilot CLI

After `sertor install rag --assistant copilot-cli`:

1. `.mcp.json` contains the `sertor-rag` server under the `mcpServers` key (where the Copilot CLI
   looks); no `.vscode/mcp.json` is written.
2. From the Copilot CLI, reload with `/mcp reload` (or restart) — the `sertor-rag` server appears
   **connected** and its tools are available (`search_code`/`search_docs`/`search_combined`).
3. The provider secrets stay empty in the template — compile them in `.sertor/.env` (never
   versioned).

### RAG (MCP) — Claude

`.mcp.json` in the host root contains the `sertor-rag` server under `mcpServers`; Claude Code picks
it up automatically.

## Idempotence & coexistence

- Re-running the same command → everything `skipped`/`block already present`, no duplication.
- Installing for both `--assistant claude` and `--assistant copilot-cli` on the same repo → the two
  configurations coexist (`.github/**` for Copilot CLI, `.claude/**`+`CLAUDE.md` for Claude) without
  conflicts or a double instruction block.

## Execution (separate step)

```bash
sertor-rag index .
sertor-rag search "how chunking works"
```
