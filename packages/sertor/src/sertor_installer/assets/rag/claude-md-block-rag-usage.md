## Sertor RAG — How to use it

This project has the **Sertor RAG** capability installed. When you need to search or retrieve from
the indexed corpus (code and documentation), use one of the provided **vehicles**:

- **CLI** — run `uv run --project .sertor sertor-rag` (e.g.
  `uv run --project .sertor sertor-rag search "<query>"`). It is the supported entry point: the bare
  command is NOT on `PATH` (it lives in `.sertor/.venv`), so always route it through `uv run --project
  .sertor`.
- **MCP tools** — the `sertor-rag` MCP server exposes search/navigation tools (`search_code`,
  `search_docs`, `search_combined`, `find_symbol`, `who_calls`, `get_context`).

For the full invocation reference — the two levels (runtime CLIs via `uv run`, installer via `uvx`),
the venv fallback, and the Windows setup notes — see `sertor-cli-reference.md` (deposited under
`.sertor/` by `sertor install rag`).

**Do NOT import `sertor_core` directly in your own scripts.** The library is meant to be consumed
through its vehicles (CLI / MCP), which wire in the cross-cutting concerns — configuration,
observability, error handling — for you. Importing `sertor_core` by hand bypasses them and is not a
supported way to use the capability.

### Search first, read second

When you need to understand code or docs in this corpus, **query the Sertor RAG before reading files
by hand**: run `uv run --project .sertor sertor-rag search` or use the MCP search/navigation tools,
let the results point you to the relevant files, then read those. It keeps your answers anchored to
what is actually indexed.

If a Sertor RAG tool returns an **error** (unreachable backend, missing or stale index), treat it as
a **signal**, not noise: say so instead of silently falling back to a blind file read. A broken
retrieval tool is worth surfacing, not burying.

### Conversation memory (optional)

This capability also ships **conversation memory** — a local, opt-in episodic archive of past
sessions. When it is enabled (`SERTOR_MEMORY=true` in `.sertor/.env`) you can recall earlier work:

- `uv run --project .sertor sertor-rag memory search "<query>"` — full-text search over archived
  sessions ("did we discuss X?").
- `uv run --project .sertor sertor-rag memory list` / `… memory show <key>` — browse and read an
  archived session.
- `uv run --project .sertor sertor-rag memory archive` — capture the current sessions (also runs
  automatically at session end).

Memory is **off by default** (privacy): the commands and the automatic capture do nothing until you
set `SERTOR_MEMORY=true`. Content is stored locally and scrubbed of secrets; nothing leaves the machine.

This is a **usage instruction**, not a constraint on your project: your own code and tests are
unaffected.
