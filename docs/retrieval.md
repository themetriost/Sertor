# Searching a project: hybrid retrieval vs the code graph

Sertor exposes **two orthogonal ways to interrogate a project**, not two alternatives you pick up
front: **hybrid retrieval** (a *relevance* engine) and the **code graph** (a *structural* map of the
code). They answer different kinds of question, and the point is to **combine** them: retrieval
**discovers** (finds things by meaning when you don't know their name), the graph **navigates** (given
a name, it gives exact facts about definitions and relationships).

Both run locally and are served by the same `sertor-rag` MCP server — **7 tools = 3 search + 4 graph**.

> **Not installed yet?** Get to a working RAG first with the single *"from nothing to first value"* path:
> **[getting-started.md](getting-started.md)**. This page is about querying *well* once it is running.

## The two surfaces

### Hybrid retrieval — "find by meaning"
Dense (embeddings) + lexical (BM25) fused with RRF, optional reranking. It is the **default** engine
behind `search_code` / `search_docs` / `search_combined` (CLI: `sertor-rag search`; MCP: the search
tools). Tolerant of fuzzy, natural-language queries; returns the chunks most **relevant** by meaning
*and* keywords. Query cost: **one embedding** (the query itself) — the chunks are already indexed.

### Code graph — "navigate by structure"
A **deterministic** AST graph (nodes: symbols/docs; edges: `calls`, `contains`, `imports`,
`inherits`, `mentions`). It backs the four MCP tools `find_symbol` / `who_calls` / `related_docs` /
`get_context`. Answers are **exact and relational**, not similarity-based. Query cost: **zero tokens**
(no embedding at query time).

## The rule of thumb: discover → navigate

| Your question | Surface | Tool |
|---|---|---|
| "find something about a topic" (you don't know the name) | **hybrid** | `search_code` |
| "explain / where is X discussed" (a concept) | **hybrid** | `search_docs` / `search_combined` |
| "where is X defined" (you know the name) | **graph** | `find_symbol` |
| "who uses X / what breaks if I change it" | **graph** | `who_calls` |
| "which docs explain X" | **graph** | `related_docs` |
| "full context of X (code + docs)" | **graph** | `get_context` |

The typical flow:

1. **Discover with hybrid retrieval** — you don't know where a capability lives → `search_code "session
   retrieval from the archive"` takes you to the right file/symbol *by meaning*.
2. **Navigate with the graph** — now that you have the **name** → `who_calls <symbol>` for its callers
   (impact analysis), `get_context <symbol>` for the full code↔doc picture.

Avoid the two mismatches: using hybrid retrieval for **structural** questions ("who calls X" — a
similarity score can't answer an exact relationship), or using the graph for **conceptual** questions
("how does chunking work") before you know which symbol to start from.

## Why orthogonal, not alternatives
The search engine (`SERTOR_ENGINE`: `baseline` | `hybrid`, default `hybrid`) decides **how relevance
search works**; the graph (`SERTOR_GRAPH`, default on) is a **separate** capability, built inside the
same `index()` and queried by its four tools regardless of the engine. You do not choose one over the
other — you use retrieval to find, then the graph to follow the connections.

See also: [`install.md`](install.md) for setting up the `sertor-rag` server on a host.
