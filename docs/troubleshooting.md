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

*For the full reference — every flag, config knob, refresh and clean uninstall — see
[install.md](install.md).*
