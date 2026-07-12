# Sertor

> Give **any project** a living, queryable knowledge of itself — where **code and documentation answer
> as one**. Portable, local-first, no lock-in.

## Why Sertor: code and docs, fused

Every other tool makes your assistant read **either** the code **or** the docs. Sertor's differentiator
is that it returns them **together**, for the same question: **the code says *what it does*, the
documentation says *why*.** That fusion — code, requirements, specs, and wiki in **one queryable
corpus** — is what turns "search" into understanding.

Ask *"how does authentication work?"* and your assistant gets both flows at once:

```text
search_combined("how does authentication work?")
{
  "docs": [ "docs/architecture/auth.md   — why: sessions are signed, tokens rotate every 24h" ],
  "code": [ "src/auth/session.py         — what: verify_session() checks signature and expiry" ]
}
```

The rule **and** the reason, in a single retrieval — neither the code nor the docs alone would have
answered as completely. Everything else Sertor does (indexing, multiple RAG engines, a self-maintaining
wiki) serves that one goal: **the highest-quality, freshest context handed to the agent.**

## What it is

Sertor is an **installable framework** that equips any project — *code+doc*, *doc-only*, or *code-only* —
with three composable, host-agnostic capabilities:

- **Repo-agnostic indexing** — *code-aware* (multi-language) and *markdown-aware* chunking,
  multi-provider embeddings, an abstract vector store.
- **RAG retrieval** — multiple engines: **hybrid** (lexical BM25 + vector, RRF — the default) with
  optional reranking, a **vector baseline**, a structural **code graph**, and **agentic** retrieval
  (MCP server + frontier agent).
- **A cumulative LLM Wiki** — a project knowledge base written and maintained *during the work*
  ("LLM Wiki" pattern), itself queryable via RAG.

Sertor attaches to a project only as a *consumer* — it makes **no assumptions about the host's business
domain**. The **library is the product**; the CLI and MCP server are thin vehicles on top.

## Fits any project

| Profile | Example | What it indexes |
|---------|---------|----------------|
| **code + doc** | an application repo with its `docs/` | sources *and* documentation |
| **doc-only** | a knowledge base, a wiki, a set of PDF/MD | documents only |
| **code-only** | a library with no narrative docs | sources only |

## Portable, local-first, no lock-in

- **Local-first ↔ Azure**, swappable via configuration: the embedding provider
  (`SERTOR_EMBED_PROVIDER=glove|hash|ollama|azure`, default `glove` — zero-config, offline) and the
  vector store (`SERTOR_STORE_BACKEND=local|azure`) are **independent knobs**, no code changes.
- **The library is the product.** The core lives in [`src/sertor_core/`](src/sertor_core/) in **Clean
  Architecture** (dependencies point inward; the `domain` imports no SDK). Providers and stores sit
  behind abstract *ports*. This decoupling is binding — see the
  [constitution](.specify/memory/constitution.md).

## Get started

**One path, from nothing to your first retrieval:** **[docs/getting-started.md](docs/getting-started.md)**
— prerequisites → install → index → a first query that shows the code+doc fusion. It is host-agnostic
(Claude Code **and** GitHub Copilot CLI).

**New to the idea?** The plain-language *"what it is and why"* — no jargon, no code — is
**[docs/why-sertor.md](docs/why-sertor.md)**.

For everything else — a worked [tutorial](docs/tutorial.md), the per-assistant guides
([Claude](docs/install-claude.md) · [Copilot](docs/install-copilot.md)), the full
[reference](docs/install.md), how to [search well](docs/retrieval.md), and
[troubleshooting](docs/troubleshooting.md) — see the **[documentation index](docs/README.md)**. What
changed is in the **[changelog](CHANGELOG.md)**.

## Status

**Actively under construction.** Available today on `master`:

- ✅ **`sertor-core`** — prod-ready retrieval library (ingestion, chunking, embeddings, facade).
- ✅ **RAG engines** — **hybrid** (BM25 + vector, RRF) as the default, **vector baseline** (with
  hit\@k / MRR evaluation), a structural **code graph**, and **agentic** retrieval (MCP + agent).
  Production hardening: embeddings content-hash cache, retry/backoff, optional confidence threshold.
- ✅ **MCP server** (`sertor_mcp`) — `search_code`/`search_docs`/`search_combined` + the 4 graph tools
  (`find_symbol`/`who_calls`/`related_docs`/`get_context`) for Claude Code and MCP clients.
- ✅ **`sertor-rag` execution CLI** — `index`/`search` from the terminal, runtime observability.
- ✅ **LLM Wiki** — deterministic core `sertor-wiki-tools` (scan/lint/structure/index/log/move/reconcile)
  + judgment operations as agentic skills.
- ✅ **Installers** — `sertor install wiki` (the wiki system) and `sertor install rag` (the RAG capability
  in an isolated `.sertor/` runtime), non-destructive and idempotent (`install ≠ run`).
- ✅ **`sertor-flow`** — the development method (SDLC): SpecKit flow, requirements management, git
  delegation, a neutral constitution starter — a **separate, standalone installer**, orthogonal to the
  RAG (no dependency on `sertor-core`).
- ✅ **Conversation memory** (MVP) — local capture + episodic full-text search, privacy-by-default,
  feeding wiki distillation.
- ✅ **Observability** — persistent local event store, reports, and a TUI panel (`sertor-rag observe`).

In development / next: multi-assistant distribution (Codex), PyPI distribution.

## Development

Uses [`uv`](https://github.com/astral-sh/uv):

```powershell
uv sync --all-packages --extra dev  # single venv: workspace members + dev + MCP server + code-graph
                                    # (add --extra azure for the Azure dogfood; azure is an opt-in heavy extra)
uv run pytest -m "not cloud"        # suite without cloud services
uv run ruff check .                 # lint
```

See [`CLAUDE.md`](CLAUDE.md) for the full operational guide.
