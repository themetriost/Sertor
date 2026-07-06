# How to invoke Sertor's commands

Sertor ships at two levels — invoke each the right way. This reference is the single source of truth
for command invocation; the always-on instruction blocks and the skills point here instead of
repeating it.

## The runtime CLIs (`sertor-rag` and `sertor-wiki-tools`)

The runtime CLIs are installed into the project's `.sertor/.venv` by `sertor install rag`. Invoke them
through that venv with **`uv run --project .sertor`** — it runs the `.sertor` runtime but **keeps your
current directory**, so a relative path like `.` is the project root as expected (the index and `.env`
stay anchored inside `.sertor/` regardless of cwd):

- `uv run --project .sertor sertor-rag <args>` (e.g. `uv run --project .sertor sertor-rag doctor`, or
  `uv run --project .sertor sertor-rag index .`).
- `uv run --project .sertor sertor-wiki-tools <op>` (e.g. `uv run --project .sertor sertor-wiki-tools
  lint --json`).

Use `--project`, NOT `--directory`: `--directory` changes the working directory, so
`sertor-rag index .` would index `.sertor` itself instead of your project. Do NOT call the bare command
(`sertor-rag …` / `sertor-wiki-tools …`) either: after install it lives in `.sertor/.venv`, not on
`PATH`, so a bare call (or `which sertor-rag`) failing means "not on `PATH`", NOT "not installed".

If `uv` is unavailable, fall back to the venv executable directly — `.sertor/.venv/Scripts/<cli>.exe`
(Windows) or `.sertor/.venv/bin/<cli>` (macOS/Linux), run from the project root. If neither resolves,
STOP and report that the runtime is not installed (run `sertor install rag`) — never silently fall back
to reading files by hand.

## The installer (`sertor`)

The installer is NOT a persistent command: run it ephemerally through `uvx` —
`uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor <verb>`
(e.g. `… sertor install rag`; add `--refresh` to force the latest build). The governance/SDLC apparatus
ships in a separate package:
`uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor-flow" sertor-flow <verb>`.

## Windows note

With the *system* Python 3.14+ a stale `pywin32` may print
`ModuleNotFoundError: No module named 'pywin32_bootstrap'` on `pip`/`python -m`. That is noise from the
system interpreter, not a Sertor error — Sertor's CLIs and MCP server run inside `.sertor/.venv` via
`uv run`, unaffected. Do not use the system `pip show sertor-rag` to check the install (it cannot see
the project venv); use `uv run --project .sertor sertor-rag doctor` instead.
