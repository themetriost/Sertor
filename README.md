# Sertor

> A framework to give **any project** a **living, queryable, self-maintaining** knowledge of itself — indexing, RAG, and LLM Wiki, without lock-in.

## 🌅 Vision

Every software project — whether it is code, documentation, or both — should be able to
**know and query itself**. Knowledge of a codebase and its documents stops being scattered,
volatile, and rebuilt from scratch every session, and becomes a **living, persistent, self-maintaining
asset**. And this must be possible **anywhere and without lock-in**: portable from one project to
another, runnable locally, neutral with respect to the LLM and storage provider.

## 🎯 Mission

Sertor is an **installable framework** that equips **any project** — *code+doc*, *doc-only*, or
*code-only* — with three composable capabilities:

1. **Repo-agnostic indexing** of content (code and documents);
2. **RAG retrieval** with multiple engines, from local to Azure;
3. a **cumulative LLM Wiki** that grows with the work.

Each capability is **decoupled from the host's domain**: Sertor attaches to a project only
as a *consumer* — today applied to itself, instrumentally, via **dogfooding**. It is delivered as an
**importable library** (that is the product) — reproducible and suited to contexts of every scale,
**enterprise included** — while the CLI and MCP are thin vehicles on top.

## The three project profiles

Sertor makes no assumptions about the shape of the host. It installs and adapts to:

| Profile | Example | What it indexes |
|---------|---------|----------------|
| **code + doc** | an application repository with its `docs/` | sources *and* documentation |
| **doc-only** | a knowledge base, a wiki, a collection of PDF/MD | documents only |
| **code-only** | a library with no narrative documentation | sources only |

## The three capabilities

- **Indexing** — repo-agnostic ingestion, *code-aware* (multi-language) and *markdown-aware*
  chunking, multi-provider embeddings, abstract vector store.
- **RAG** — retrieval over that content; multiple engines: **hybrid** (lexical BM25 + vector, RRF —
  the default) with optional reranking, **vector baseline**, a structural **code graph**, and
  **agentic** retrieval (composite: MCP server + frontier agent).
- **LLM Wiki** — a project knowledge base that is written and maintained during the work
  ("LLM Wiki" pattern), itself queryable via RAG.

## Decoupling (why it matters)

Sertor's features and skills **must not know the host's business domain**. The fact that in this
repository they are applied to Sertor itself is **instrumental** (dogfooding), not a licence to
embed project-specific assumptions. This principle is binding: see the
[constitution](.specify/memory/constitution.md).

## Architecture at a glance

- **The library is the product.** The core lives in [`src/sertor_core/`](src/sertor_core/) in
  **Clean Architecture** (dependencies point inward; the `domain` does not import any SDK).
- **Local-first ↔ Azure**, swappable via configuration (`RAG_BACKEND=local|azure`), without
  touching the code. LLM/embeddings providers and vector store are behind abstract *ports*.
- **CLI and MCP** are thin consumers of the library.

## Status

**Actively under construction.** Available today on `master`:

- ✅ **`sertor-core`** — prod-ready retrieval library (ingestion, chunking, embeddings, facade).
- ✅ **RAG engines** — **hybrid** (BM25 + vector, RRF) as the default, **vector baseline** (with
  hit\@k / MRR evaluation), a structural **code graph**, and **agentic** retrieval (MCP + agent).
  Production hardening: embeddings content-hash cache, retry/backoff, optional confidence threshold.
- ✅ **MCP server** (`sertor_mcp`) — `search_code`/`search_docs`/`search_combined` + the 4 graph
  tools (`find_symbol`/`who_calls`/`related_docs`/`get_context`) for Claude Code and MCP clients.
- ✅ **`sertor-rag` execution CLI** — `index`/`search` from the terminal, runtime observability.
- ✅ **LLM Wiki** — deterministic core `sertor-wiki-tools` (scan/lint/structure/index/log/move/
  reconcile) + judgment operations as agentic skills.
- ✅ **Installers** — `sertor install wiki` (the wiki system) and `sertor install rag` (the RAG
  capability in an isolated `.sertor/` runtime), non-destructive and idempotent (`install ≠ run`).
- ✅ **`sertor-flow`** — the development method (SDLC) — SpecKit flow, requirements management, git
  delegation, a neutral constitution starter — as a **separate, standalone installer**, orthogonal to
  the RAG (no dependency on `sertor-core`). Built on the shared `sertor-install-kit` toolkit.
- ✅ **Conversation memory** (MVP) — local capture + episodic full-text search, privacy-by-default,
  feeding wiki distillation.
- ✅ **Observability** — persistent local event store, reports, and a TUI panel (`sertor-rag observe`).

In development / next: incremental index refresh (only changed files), multi-assistant distribution
(GitHub Copilot / Codex), semantic memory search, PyPI distribution.

## Installation on another repository

**Quick start — pick your assistant:**

- **[`docs/install-claude.md`](docs/install-claude.md)** — for **Claude Code** hosts.
- **[`docs/install-copilot.md`](docs/install-copilot.md)** — for **GitHub Copilot** hosts (VS Code & CLI).

Each is a concise, three-section guide — **RAG**, **Wiki**, **Governance (SDLC)** — covering
`sertor install rag`, `sertor install wiki`, and `sertor-flow install`. The full reference (every
flag, all config knobs, refresh & uninstall) is **[`docs/install.md`](docs/install.md)**.

For how to query a project once indexed — when to use **hybrid retrieval** vs the **code graph**
(the *discover → navigate* pattern) — see **[`docs/retrieval.md`](docs/retrieval.md)**.

## Development

Uses [`uv`](https://github.com/astral-sh/uv):

```bash
uv sync --extra dev          # environment with development dependencies
uv run pytest -m "not cloud" # suite without cloud services
uv run ruff check .          # lint
```

See [`CLAUDE.md`](CLAUDE.md) for the full operational guide.
