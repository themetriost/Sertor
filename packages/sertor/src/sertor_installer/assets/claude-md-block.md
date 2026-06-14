## Step Ritual / Definition of Done (LLM Wiki)

This project maintains a **local wiki** in `wiki/`, inspired by Karpathy's "LLM Wiki" pattern:
a persistent, cumulative artifact that grows with each session instead of rebuilding
knowledge from scratch every time. Configuration lives in `wiki.config.toml` (the single source of
host-specific settings: root, taxonomy, source folders, language).

> **Golden rule:** every significant thing that is done must be documented in the wiki — experiments, decisions,
> concepts/technologies explored, ingested sources. Do not wait for the user to ask.
> Purely mechanical, minor changes do not require a log entry.

A **step** is a meaningful unit of work (a feature, a fix, a decision, a research task,
an analysis). **At the end of each step**, the main flow executes — on its own initiative — this
checklist:

1. **Record** (`record`) — create/update the impacted pages, backlinks, and `index.md`, and append
   the log entry (today's file in `wiki/log/`). Structural work → delegatable to the
   `wiki-curator` agent.
2. **Distill entities** (`distill`) — identify the durable entities/concepts the step surfaced
   and, if they have their own identity and are referenced from multiple points, give each a
   dedicated page in `concepts/`/`tech/`; the dated record stays lean and points to them. This is **judgment** → stays
   in the main flow.
3. **Semantic lint** (`lint` level B) — verify that the wiki has not drifted away from the
   reality of the project (code, requirements, VCS state): flag every claim the repo contradicts,
   fix on confirmation. This is **judgment** → stays in the main flow.
4. **Plain-language summary (explainer)** — when a step develops or plans a **significant capability**
   (a requirement, a feature, a product capability), produce or update a **plain-language description**
   under `wiki/explainers/` (for non-technical readers): what it does and why, with an everyday analogy
   and no jargon, each pointing to the corresponding technical page. This is **judgment** → stays in the
   main flow. **Calibrate to value (optional):** only for capabilities worth explaining to a
   non-technical stakeholder — not for mechanical or tooling-only steps. It applies both to what is
   *done* and to what is *about to be built* (the page marks the status).

**Delegation.** That these actions happen is the main flow's responsibility; executing or delegating them
is merely a choice to avoid blocking. The `record` (structured transcription) is delegatable to the
`wiki-curator` agent; distillation and semantic lint, being judgment, stay in the main flow.
To manually trigger a consolidation use the `/wiki` command (main flow)
or delegate to `wiki-curator` (background).

**When to record:** at the same moment as the step commit. The log entry is
not deferrable: a step is not closed until both the commit **and** the log entry are done.

### Wiki operations

- **record** — records work/decisions: pages + backlinks + `index.md` + log entry.
- **distill** — extracts durable entities surfaced by a piece of work into dedicated pages.
- **ingest** — acquires an external source (file/PDF/URL) → summary in `sources/`, integrates into
  linked pages, flags contradictions.
- **query** — answers by citing pages; archives a valuable exploration as a new page.
- **lint** — consistency at three levels: A structural (frontmatter/broken wikilinks/orphans/naming), B
  semantic (claims vs. repo reality), C organizational (placement/atomicity/links).
- **reorg** — applies the organizational refactoring surfaced by lint C, on confirmation.
- **generate** — generates/updates the wiki from the repo (from-scratch or from-diff).
- **rag-sync** — re-indexes the wiki into the RAG (if enabled in `wiki.config.toml`).
- **structure** — idempotent bootstrap of the wiki structure.

### Conventions

- **YAML frontmatter** on every page: `title`, `type`, `tags`, `created`, `updated`, `sources`.
- **Backlinks** in wikilink style `[[page-name]]` (Obsidian-compatible).
- **File naming**: descriptive kebab-case (e.g. `azure-ai-search.md`).
- **Log entry format:** `## [YYYY-MM-DD] <operation> | <title>`.
- Create a new page for a new concept/entity; update the existing one otherwise.
- When a new source contradicts a page, explicitly flag the contradiction.
