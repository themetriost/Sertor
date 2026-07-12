# Tutorial: from nothing to your first fused answer

A hands-on, end-to-end walkthrough. By the end you'll have Sertor installed on a project, indexed, and
answering a real question with **code and documentation together**. It is host-agnostic — every command
shows both the **Claude Code** and the **GitHub Copilot CLI** variant where they differ.

If you just want the terse checklist, use the [getting-started guide](getting-started.md); this page is
the guided version that explains *what happens* at each step and *what you should see*.

## What you need

- **Python ≥ 3.11** and **[`uv`](https://github.com/astral-sh/uv)**.
- A repository to try it on — your own, or any project you have locally. Sertor never modifies your
  sources; it only reads them.
- Nothing else: the default embedder (`glove`) is zero-config and runs offline after a one-time download.

Open a terminal **in the root of that repository** and follow along.

## Step 1 — Install the RAG capability

This drops an isolated `.sertor/` runtime into the repo (your files are untouched):

```powershell
# Claude Code
uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor install rag --backend local

# GitHub Copilot CLI
uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor install rag --assistant copilot-cli --backend local
```

`--backend local` picks the zero-config `glove` embedder — **no API keys needed**. You should see a short
report of what was written (an `.mcp.json` entry, the `.sertor/` runtime, a few hooks). Nothing has been
indexed yet — **install ≠ run**.

> **Want cloud-quality embeddings instead?** Use `--backend azure`, then run
> `uvx --from "…/packages/sertor" sertor configure --backend azure` to fill `AZURE_OPENAI_ENDPOINT` /
> `AZURE_OPENAI_API_KEY` (masked prompts). Everything else in this tutorial is identical.

## Step 2 — Index the project

Indexing is the explicit step where Sertor reads and organizes everything:

```powershell
uv run --project .sertor sertor-rag index .
```

The first run downloads the GloVe vectors once (~822 MB, cached per machine, offline afterwards), then
reports how much it indexed — something like:

```text
mode=full  documents=428  chunks=5170  embedding_dim=300  elapsed_ms=...
```

> **Why `uv run --project .sertor`?** The runtime CLIs live inside `.sertor/.venv` and are **not on your
> `PATH`**. `uv run --project .sertor <cli>` runs that runtime but keeps your current directory, so
> `index .` indexes the project root. Use `--project`, **not** `--directory` (which would `cd` into
> `.sertor` and index the runtime itself).

## Step 3 — Check it's healthy

Before querying, confirm everything is wired up:

```powershell
uv run --project .sertor sertor-rag doctor
```

`doctor` checks four areas (environment, provider, index, MCP) and prints `pass`/`warn`/`fail` with a
cause and a remedy for anything that isn't green. A clean run means you're ready. (Add `--online` to also
probe the embeddings provider, or `--json` for machine-readable output.)

## Step 4 — Your first query from the terminal

Ask the project something in plain language:

```powershell
uv run --project .sertor sertor-rag search "how does configuration loading work?"
```

You get back the most relevant chunks — by *meaning*, not just keywords — each with its `path#chunk`
source so you can verify it. Try a few questions about your project; there's no wrong query.

## Step 5 — The payoff: code and docs, fused

Now the point of Sertor. Load the MCP server so your assistant can use the tools:

```powershell
# Claude Code:  reload Claude Code and approve the `sertor-rag` server added to .mcp.json
# Copilot CLI:  run  /mcp reload  (or restart), then verify with  /mcp show
```

Inside your assistant, ask a "how does X work?" question. Behind the scenes it calls **`search_combined`**,
which returns two labelled flows for the same question — `docs` (the *why*) and `code` (the *what*).
Illustrative shape (paths are placeholders for *your* repo):

```text
search_combined("how does authentication work?")
{
  "docs": [ "docs/architecture/auth.md#3   — why: sessions are signed, tokens rotate every 24h" ],
  "code": [ "src/auth/session.py#2         — what: verify_session() checks signature and expiry" ]
}
```

Your assistant now answers with **the rule and the reason in one lookup** — the handler that enforces
auth *and* the document that explains why. That fusion is the whole point: neither the code nor the docs
alone would have answered as completely.

## What you learned

- **Install ≠ run**: installing drops an isolated runtime; you index explicitly when ready.
- Always invoke the runtime CLIs through **`uv run --project .sertor …`**.
- **`doctor`** tells you, in one command, whether it worked.
- The differentiator is **`search_combined`**: code *and* documentation, fused, with sources.

## Where to go next

- **Search well:** when to use hybrid retrieval vs the code graph (the *discover → navigate* pattern) —
  [searching a project](retrieval.md).
- **Every flag and knob**, refresh, and clean uninstall — [the full reference](install.md).
- **Something not working?** — [troubleshooting](troubleshooting.md).
- **Add the Wiki and the SDLC method** — the per-assistant guides
  ([Claude](install-claude.md) · [Copilot](install-copilot.md)), sections *Wiki* and *Governance*.
