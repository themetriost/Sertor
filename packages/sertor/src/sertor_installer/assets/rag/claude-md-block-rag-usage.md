## Sertor RAG — How to use it

This project has the **Sertor RAG** capability installed. When you need to search or retrieve from
the indexed corpus (code and documentation), use one of the provided **vehicles**:

- **CLI** — run `sertor-rag` (e.g. `sertor-rag search "<query>"`). It is the supported entry point.
- **MCP tools** — the `sertor-rag` MCP server exposes search/navigation tools (`search_code`,
  `search_docs`, `search_combined`, `find_symbol`, `who_calls`, `get_context`).

**Do NOT import `sertor_core` directly in your own scripts.** The library is meant to be consumed
through its vehicles (CLI / MCP), which wire in the cross-cutting concerns — configuration,
observability, error handling — for you. Importing `sertor_core` by hand bypasses them and is not a
supported way to use the capability.

### Search first, read second

When you need to understand code or docs in this corpus, **query the Sertor RAG before reading files
by hand**: run `sertor-rag search` or use the MCP search/navigation tools, let the results point you
to the relevant files, then read those. It keeps your answers anchored to what is actually indexed.

If a Sertor RAG tool returns an **error** (unreachable backend, missing or stale index), treat it as
a **signal**, not noise: say so instead of silently falling back to a blind file read. A broken
retrieval tool is worth surfacing, not burying.

This is a **usage instruction**, not a constraint on your project: your own code and tests are
unaffected.
