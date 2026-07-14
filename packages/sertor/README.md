# sertor

The **installer** for Sertor's capabilities on a host repository — the `sertor` command-line entry
point. It deposits a capability of the retrieval core (`sertor-core`) onto any repo, **non-destructively
and idempotently**:

- `sertor install rag` — the RAG capability (`.sertor/` runtime + `.mcp.json` MCP server + usage/
  freshness hooks + eval/guided-setup skills).
- `sertor install wiki` — the LLM Wiki system (persistent, cumulative project knowledge).
- `sertor install governance` — points to the separate `sertor-flow` package.

Plus the lifecycle verbs `sertor upgrade` / `sertor uninstall` and the guided `sertor configure`.

**install ≠ run:** installing a capability never starts indexing — that is always a separate, explicit
command (`sertor-rag index .`). Multi-assistant: `--assistant claude,copilot-cli` (or `all`) installs
for several AI assistants in one invocation, into disjoint containers.

## Install

Interim distribution via `git+url` (a PyPI package is coming):

```powershell
uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor install rag
```

Full guides:
[getting-started](https://github.com/themetriost/Sertor/blob/master/docs/getting-started.md) ·
[install reference](https://github.com/themetriost/Sertor/blob/master/docs/install.md).

A thin consumer of `sertor-core`; the installer machinery lives in `sertor-install-kit`. MIT licensed.
