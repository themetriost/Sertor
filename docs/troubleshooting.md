# Troubleshooting Sertor — common problems, cause, fix

A **static** companion to the agentic diagnosis. Before scanning this list, run the health check —
it inspects config, provider, index and MCP wiring in one shot and tells you *what* is wrong:

```powershell
uv run --project .sertor sertor-rag doctor
```

Add **`--online`** to also probe the embeddings provider for reachability, and **`--json`** for a
machine-readable report. Commands below are host-agnostic (Claude Code and GitHub Copilot CLI); where an
assistant differs it is called out.

---

## `sertor-rag: command not found` (or `which sertor-rag` fails)

**Symptom.** A bare `sertor-rag …` (or `which sertor-rag`) fails, suggesting the tool is missing.

**Cause.** After `install rag` the runtime CLIs (`sertor-rag`, `sertor-wiki-tools`) live in
`.sertor/.venv` and are **NOT on `PATH`**. "not on `PATH`" is **not** the same as "not installed".

**Fix.** Always invoke them through the `.sertor` runtime, which keeps your current directory so relative
paths resolve from the project root:

```powershell
uv run --project .sertor sertor-rag doctor
```

If `uv` itself is unavailable, call the venv executable directly: `.sertor/.venv/Scripts/sertor-rag.exe`
(Windows) or `.sertor/.venv/bin/sertor-rag` (POSIX).

---

## `index .` indexes `.sertor` itself instead of your repo

**Symptom.** After indexing, the corpus contains the runtime files under `.sertor/` rather than your
project sources.

**Cause.** The command used `--directory .sertor` instead of `--project .sertor`. `--directory` changes
the cwd to `.sertor`, so `index .` resolves to `.sertor` itself.

**Fix.** Use `--project` — it runs the `.sertor` runtime but **keeps your current directory**, so
`index .` indexes the project root:

```powershell
uv run --project .sertor sertor-rag index .
```

---

## Every search returns nothing, and there is no error

**Symptom.** `sertor-rag search` or the MCP tools return an empty result for every query — including
queries you know the corpus can answer. No error message: just nothing, which looks exactly like a
thin corpus.

**Cause.** The MCP server in `.mcp.json` is registered with `uv run --directory .sertor`, which moves
the working directory: the server resolves its index inside the runtime folder instead of your
project, and reads an empty one. Installations created before this was fixed carry that entry, and
older versions skipped the file on upgrade — so it survived.

**Diagnose.** `doctor` names it:

```powershell
uv run --project .sertor sertor-rag doctor
```

A registration that moves the working directory is reported as `mcp_invocation_moves_cwd`.

**Fix.** Upgrade — the `sertor-rag` entry is reconciled in place (your `SERTOR_CORPUS` and any other
MCP server in the file are preserved), then restart the MCP server:

```powershell
uvx --refresh --from "git+https://github.com/themetriost/Sertor.git#subdirectory=packages/sertor" sertor upgrade rag
```

You can also edit `.mcp.json` by hand, replacing `--directory` with `--project`.

---

## Windows: `ModuleNotFoundError: No module named 'pywin32_bootstrap'`

**Symptom.** Running `pip` / `python -m` prints
`ModuleNotFoundError: No module named 'pywin32_bootstrap'`.

**Cause.** A stale `pywin32` on the **system** Python interpreter. This is **noise from the system
Python, not a Sertor error** — Sertor's CLIs and MCP server run inside `.sertor/.venv` via `uv run`,
unaffected.

**Fix.** Do **not** use the system `pip show sertor-rag` to check the install (it cannot see the project
venv). Check health through the runtime instead:

```powershell
uv run --project .sertor sertor-rag doctor
```

---

## MCP server not answering / tool calls error on missing keys

**Symptom.** The `sertor-rag` MCP tools do not respond, or tool calls error out complaining about
missing credentials.

**Cause.** The configuration in `.sertor/.env` is incomplete — e.g. an Azure backend was selected but
`AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_API_KEY` are unset.

**Fix.** Run `doctor` to see exactly which area is failing, then fill the secrets (guided, masked, no
editor):

```powershell
uv run --project .sertor sertor-rag doctor
uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor configure --backend azure
```

Alternatively, avoid secrets entirely by using the zero-config `glove` embedder — configure with
`--backend local`, which needs nothing to fill.

---

## NO MCP tools at all, but `doctor` is green (`No module named 'mcp.server.fastmcp'`)

**Symptom.** Your assistant receives **none** of the `sertor-rag` tools — not some, none — while
`sertor-rag doctor` reports `PASS` on every area, including `mcp pass (registered=True)`. The CLI
works fine: `sertor-rag search` returns correct results.

**Cause.** The MCP SDK released **2.0.0** on 2026-07-28, and it **removed** the `mcp.server.fastmcp`
submodule that Sertor's server imports at the top of the module. Sertor's requirement was
`mcp>=1.2` with **no upper bound**, so a host that resolved its dependencies in that window pulled
2.0.0 and froze it in `.sertor/uv.lock`. The server process then dies on import, before serving
anything — hence "none" rather than "some". `doctor` stays green because its `mcp` check asks
whether the server is *registered* in `.mcp.json`, not whether it *starts*.

**Who is affected.** Only hosts whose `.sertor/uv.lock` was written between 2026-07-28 and the
release carrying the fix. A host that installed earlier is unaffected — its lock holds a 1.x — and
so is a host installing after the fix, which now resolves `mcp>=1.2,<2`.

**Confirm it in one command** (this is the check `doctor` does not do):

```powershell
uv run --project .sertor python -m sertor_mcp.server
```

A `ModuleNotFoundError: No module named 'mcp.server.fastmcp'` confirms this exact case.

**Fix.** Re-resolve the runtime so it picks up the upper bound, then verify:

```powershell
uv sync --project .sertor --upgrade
uv run --project .sertor python -c "import sertor_mcp.server; print('server imports OK')"
```

Then reload your MCP client (restart Claude Code, or `/mcp reload` on the Copilot CLI). If your
runtime is pinned to a release that predates the fix, pin the SDK locally in the meantime by adding
`"mcp<2"` to the `dependencies` of `.sertor/pyproject.toml` and re-running `uv sync --project
.sertor`.

---

## First index is very slow / triggers a large download

**Symptom.** The first `index .` run stalls for a while and downloads a large file (~822 MB).

**Cause.** The default `glove` embedder downloads the static GloVe vectors **once per machine** on the
first index. This is expected, not an error.

**Fix.** Let the first index complete — the vectors are cached per machine and the corpus is offline
afterwards. Subsequent indexes reuse the cache:

```powershell
uv run --project .sertor sertor-rag index .
```

---

## `uvx` reuses a stale build after Sertor's `master` moves

**Symptom.** A plain re-run of the installer keeps behaving like an older version even though Sertor's
`master` has advanced.

**Cause.** `uvx` caches the built installer **per git revision**, so a plain re-run can reuse a stale
build.

**Fix.** Force a fresh build with **`--refresh`**, then re-index with the updated runtime (the install is
idempotent and never overwrites your `.env` edits):

```powershell
# Claude Code (add --assistant copilot-cli on Copilot):
uvx --refresh --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor install rag --backend local
uv run --project .sertor sertor-rag index .
```

---

## Copilot CLI: conversation memory captures nothing

**Symptom.** On a GitHub Copilot CLI host, the `memory-capture` hook fires but nothing useful is
captured from sessions.

**Cause.** Capturing Copilot CLI sessions requires **both** knobs set explicitly — with the default
values the hook captures nothing useful.

**Fix.** Set both in `.sertor/.env`:

```
SERTOR_MEMORY=true
SERTOR_MEMORY_ADAPTER=copilot-cli
```

---

## Copilot host: wrong layout / files land in the wrong place

**Symptom.** On a GitHub Copilot host, installed assets end up in the wrong containers (e.g. MCP wiring
or agent files not where Copilot looks for them).

**Cause.** The install command ran with the default `claude` target instead of the Copilot target.

**Fix.** Pass **`--assistant copilot-cli`** to every install command:

```powershell
uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor install rag --assistant copilot-cli --backend local
```

---

## General health check — "did it actually work?"

**Symptom.** Retrieval feels off and you are not sure whether config, provider, index or MCP wiring is
the culprit.

**Cause.** Any one of several areas can be misconfigured; you need a single deterministic verdict.

**Fix.** Run `doctor`. Add `--online` to probe the provider for reachability, and `--json` for machine
output:

```powershell
uv run --project .sertor sertor-rag doctor --online --json
```

---

## "What did the installer actually do?" — the install log

**Symptom.** After `sertor install rag` you are not sure what was created, left untouched, or skipped —
or the summary line mentions `present-divergent` and you want to know which file.

**Cause.** The on-screen report is a summary; you want the per-artifact truth.

**Fix.** The RAG install appends an inspectable, append-only log — one JSON line per artifact — to
`.sertor/.install-log.jsonl`. Each line records the operation, capability, target, outcome, and a
reason (schema `install.event/1`). Read it to see exactly what happened:

```powershell
Get-Content .sertor/.install-log.jsonl
```

An outcome of **`present_divergent`** means a file Sertor owns already existed on your host with
**different content** — it was **left untouched** (non-destructive), not overwritten. That is by
design: your customization wins. If you want Sertor's version instead, move your file aside and
re-run, or use `upgrade`.

## The wiki gate blocks the end of the session and I cannot tell why

**Symptom.** Your assistant tries to stop and is blocked with *"the wiki was not updated for this
session's work"*. You updated the wiki, or you cannot see what is missing.

**Cause.** The gate compares your source files (`src`, `specs`, `requirements`, …) against the most
recent **recording** — the latest entry in the wiki log. It blocks when work is not covered by one.

**Fix.** Ask it directly; the answer names the files:

```powershell
uv run --project .sertor sertor-wiki-tools scan
```

Read the reply top to bottom:

- **`pending=N` plus a file list** — those are the files not covered by a recording. Record them
  (or, for genuinely mechanical changes, note that in the entry) and stop again.
- **`kind=git`** — the answer is **derived** from your repository history: the anchor is the last
  commit that touched the wiki log. Files your VCS **ignores never count**, so a scratch file left in
  the working directory will not block you.
- **`kind=mtime`** — your project is **not a git repository** (or history is unreadable), so the
  answer is an **estimate** based on file modification times, and the reply says why. On such a host
  the count can include files a VCS would have ignored. This is a declared limitation, not a bug.
- **`note: uncommitted log entry … is not today's`** — you have an unsaved entry from a **previous
  day**. It does not close the gate: write today's entry.

**You do not need to commit to satisfy the gate.** An entry written today counts as soon as it is on
disk — the gate asks whether you recorded, not whether you committed.

**Still blocked with nothing pending?** The gate fails open when it cannot determine the answer, so a
persistent block means it *did* find something. Check `.sertor/.last-hook-error` for a breadcrumb.

---

*For the full reference — every flag, config knob, refresh and clean uninstall — see
[install.md](install.md).*
