# Getting started with Sertor — from nothing to first value

This is the **single path** from an unconfigured repository to your **first working retrieval** — and to
*seeing* what makes Sertor different: a query that hands your assistant **code and documentation
together**. One linear journey, four steps: **prerequisites → install the RAG → index → first query**.

It is **host-agnostic**: it works whether your assistant is **Claude Code** or **GitHub Copilot CLI**.
Where a command differs by assistant, both variants are shown side by side, and the deeper per-assistant
detail is linked — not repeated.

> **Just want the "why" first?** The one-screen pitch is the [`README`](../README.md).
> **Want every flag and knob?** The full reference is [`docs/install.md`](install.md).

---

## 1. Prerequisites

- **Python ≥ 3.11** and **[`uv`](https://github.com/astral-sh/uv)** — the supported install path.
- **Network access to GitHub** — Sertor ships via `git+url` (not PyPI yet).
- **An embeddings provider** for the RAG. The default **`glove`** is **zero-config** (static GloVe
  vectors, downloaded once per machine — ~822 MB on the first index — then offline): nothing to install
  or run. You can opt into **Azure OpenAI** (`text-embedding-3-*`, best quality, needs credentials), a
  local **[Ollama](https://ollama.com)** server, or **`hash`** (a zero-download lexical floor for
  airgapped/CI).

Run every command below **in the root of your target repository**. Every installer is
**non-destructive**, **idempotent**, and **install ≠ run** — nothing is indexed until you ask.

---

## 2. Install the RAG

Bring the retrieval capability (index + search + MCP server) into an isolated `.sertor/` runtime. Your
sources are never touched; it works even on non-Python repos.

**Claude Code** (the `claude` assistant is the default, so no `--assistant` flag):

```powershell
uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor install rag --backend local
```

**GitHub Copilot CLI** (pass `--assistant copilot-cli`):

```powershell
uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor install rag --assistant copilot-cli --backend local
```

`--backend local` selects the zero-config `glove` embedder — **no secrets needed**. To use **Azure**
embeddings instead, pass `--backend azure` and then fill the credentials (guided, no editor):

```powershell
# Claude Code                                                                          (add --assistant copilot-cli on Copilot)
uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor configure --backend azure
# prompts for AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY (masked). Skip entirely with --backend local.
```

> **Per-assistant details** (what lands where, hooks, migration notes) live in the concise per-assistant
> guides — read them only if you need the specifics:
> **[install-claude.md](install-claude.md)** · **[install-copilot.md](install-copilot.md)**.

---

## 3. Index your repository

Indexing is an **explicit step** — install never indexes. The first run on `--backend local` downloads
the GloVe vectors once (~822 MB, cached per machine):

```powershell
uv run --project .sertor sertor-rag index .
```

> **Why `uv run --project .sertor`?** After `install rag` the runtime CLIs (`sertor-rag`,
> `sertor-wiki-tools`) live in `.sertor/.venv` and are **not on `PATH`**. `uv run --project .sertor`
> runs that runtime **but keeps your current directory**, so `index .` indexes the project root — use
> `--project`, **not** `--directory` (which would change the cwd to `.sertor` and index `.sertor`
> itself). A bare `sertor-rag …` failing means "not on `PATH`", **not** "not installed".

Then load the MCP server so your assistant can use the tools:

```powershell
# Claude Code:  reload Claude Code, then approve the `sertor-rag` server added to .mcp.json
# Copilot CLI:  run  /mcp reload  (or restart), then verify with  /mcp show
```

---

## 4. First query — code and documentation, fused

This is the payoff. Sertor's differentiator is that it returns **code *and* documentation together** in
one answer: *the code says what it does, the documentation says why.* The `search_combined` surface
returns two labelled flows — `docs` (the *why*) and `code` (the *what*) — for the same question.

Quick check from the terminal (works on any assistant):

```powershell
uv run --project .sertor sertor-rag search "how does authentication work?"
```

Inside your assistant, the same question through the **`search_combined`** MCP tool returns both flows at
once. Illustrative shape (on *your* repo — paths are placeholders for your own files):

```text
search_combined("how does authentication work?")
{
  "docs": [
    "docs/architecture/auth.md#3   — why: sessions are signed, tokens rotate every 24h, the rationale",
    "docs/adr/0007-oauth.md#1      — why: the decision to use OAuth2 over basic auth"
  ],
  "code": [
    "src/auth/session.py#2         — what: verify_session() checks the signature and expiry",
    "src/auth/oauth.py#1           — what: the OAuth2 handler that issues and refreshes tokens"
  ]
}
```

Your assistant now has, in a single retrieval, **the rule and the reason** — the handler that enforces
auth *and* the document that explains why it works that way. That fusion is the whole point: neither the
code alone nor the docs alone would have answered "how does authentication work?" as completely.

---

## Where to go next

- **Search well:** when to use **hybrid retrieval** (find by meaning) vs the **code graph** (navigate by
  structure) — the *discover → navigate* pattern — is explained in
  **[docs/retrieval.md](retrieval.md)**.
- **Every flag and knob**, refresh, and clean uninstall: the full reference
  **[docs/install.md](install.md)**.
- **Add the Wiki and the SDLC method** (two more, orthogonal capabilities): see the per-assistant guides
  (**[install-claude.md](install-claude.md)** · **[install-copilot.md](install-copilot.md)**), sections
  *Wiki* and *Governance*.
