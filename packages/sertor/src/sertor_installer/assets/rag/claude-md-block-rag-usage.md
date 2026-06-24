## Sertor RAG — How to use it

This project has the **Sertor RAG** capability installed. When you need to search or retrieve from
the indexed corpus (code and documentation), use one of the provided **vehicles**:

- **CLI** — run `uv run --project .sertor sertor-rag` (e.g.
  `uv run --project .sertor sertor-rag search "<query>"`). It is the supported entry point — see
  "How to invoke Sertor's commands" below for why the bare command is NOT on `PATH`.
- **MCP tools** — the `sertor-rag` MCP server exposes search/navigation tools (`search_code`,
  `search_docs`, `search_combined`, `find_symbol`, `who_calls`, `get_context`).

## How to invoke Sertor's commands

Sertor ships at two levels — invoke each the right way:

- **The runtime CLIs `sertor-rag` and `sertor-wiki-tools`** are installed into the project's
  `.sertor/.venv` by `sertor install rag`. Invoke them through that venv with **`uv run --project .sertor`** —
  it runs the `.sertor` runtime but **keeps your current directory**, so a relative path like `.` is the
  project root as expected (the index and `.env` stay anchored inside `.sertor/` regardless of cwd):
  `uv run --project .sertor sertor-rag <args>` (e.g. `uv run --project .sertor sertor-rag doctor`, or
  `uv run --project .sertor sertor-rag index .`). Use `--project`, NOT `--directory`: `--directory`
  changes the working directory, so `sertor-rag index .` would index `.sertor` itself instead of your
  project. Do NOT call the bare command (`sertor-rag …`) either: after install it is in `.sertor/.venv`,
  not on `PATH`, so a bare call (or `which sertor-rag`) failing means "not on PATH", NOT "not installed".
  If `uv` is unavailable, fall back to the venv executable directly — `.sertor/.venv/Scripts/<cli>.exe`
  (Windows) or `.sertor/.venv/bin/<cli>` (POSIX), run from the project root. If neither resolves, STOP and
  report that the runtime is not installed (run `sertor install rag`) — never silently fall back to
  reading files by hand.
- **The installer `sertor`** is NOT a persistent command: run it ephemerally through `uvx` —
  `uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor <verb>`
  (e.g. `… sertor install rag`; add `--refresh` to force the latest build).

> **Windows note.** With the *system* Python 3.14 a stale `pywin32` may print
> `ModuleNotFoundError: No module named 'pywin32_bootstrap'` on `pip`/`python -m`. That is noise from
> the system interpreter, not a Sertor error — Sertor's CLIs and MCP server run inside `.sertor/.venv`
> via `uv run`, unaffected. Do not use the system `pip show sertor-rag` to check the install (it cannot
> see the project venv); use `uv run --project .sertor sertor-rag doctor`.

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
