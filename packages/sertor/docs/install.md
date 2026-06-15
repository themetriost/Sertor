# `sertor install` — capabilities and target assistant

`sertor install <capability>` deposits a Sertor capability into a host repository in a
non-destructive, idempotent way (install ≠ run: nothing is indexed automatically).

## Capabilities

| Capability | Command | What it installs |
|---|---|---|
| RAG | `sertor install rag` | `.sertor/` runtime + MCP server config + RAG-usage instruction block + anti-bypass hook |
| wiki | `sertor install wiki` | wiki commands/skill, agent, hooks, instruction block + `wiki/` scaffold |
| governance | `sertor install governance` | pointer to the separate `sertor-flow` package |

## `--assistant` (target assistant)

Both `install wiki` and `install rag` accept `--assistant <claude|copilot>`:

```bash
sertor install rag  --assistant copilot
sertor install wiki --assistant copilot
```

- `--assistant` is optional; absent → default **`claude`** (documented).
- An unknown value (e.g. `codex`) → explicit error (exit 1) listing the valid values.
- The execution CLIs (`sertor-rag`, `sertor-wiki-tools`) are **assistant-agnostic**: no per-assistant
  variant.

### Surface mapping (where artifacts land)

| Surface | `claude` | `copilot` |
|---|---|---|
| Instruction block | `CLAUDE.md` | `.github/copilot-instructions.md` |
| MCP server | `.mcp.json` (`mcpServers`) | `.vscode/mcp.json` (`servers`) |
| Commands/skill | `.claude/commands/*`, `.claude/skills/*` | `.github/prompts/*.prompt.md` |
| Agent | `.claude/agents/*.md` | `.github/agents/*.agent.md` |
| Hook wiring | `.claude/settings.json` | `.github/hooks/sertor-*.json` |
| Hook script | `.claude/hooks/*.ps1` | `.github/hooks/*.ps1` (same script, reused) |

The instruction-block text, the command/skill body, the agent persona and the hook script are a
**single source** (the canonical Claude asset); the Copilot artifacts are derived by translating
only the container (path/frontmatter). A guard test fails on divergence (anti-drift).

The report declares the **target assistant** and the outcome of every surface in scope; a surface
without a rendering on the chosen assistant is reported as an explicit **gap**, never omitted.

## Verifying the install

### RAG (MCP) — Copilot

After `sertor install rag --assistant copilot`:

1. `.vscode/mcp.json` contains the `sertor-rag` server under the `servers` key.
2. From the Copilot client (VS Code agent mode), the `sertor-rag` server appears **connected** and
   its tools are available (`search_code`/`search_docs`/`search_combined`). No manual editing is
   required.
3. The provider secrets stay empty in the template — compile them in `.sertor/.env` (never
   versioned).

### RAG (MCP) — Claude

`.mcp.json` in the host root contains the `sertor-rag` server under `mcpServers`; Claude Code picks
it up automatically.

## Idempotence & coexistence

- Re-running the same command → everything `skipped`/`block already present`, no duplication.
- Installing for both `--assistant claude` and `--assistant copilot` on the same repo → the two
  configurations coexist (`.github/**` for Copilot, `.claude/**`+`CLAUDE.md` for Claude) without
  conflicts or a double instruction block.

## Execution (separate step)

```bash
sertor-rag index .
sertor-rag search "how chunking works"
```
