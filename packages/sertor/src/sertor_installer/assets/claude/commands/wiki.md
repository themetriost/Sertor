---
description: Consolidates the session's work into the local wiki (record/distill/ingest/query/lint/reorg/generate/rag-sync)
argument-hint: "[operation and/or scope, e.g. 'lint', 'generate media', 'distill <conversation brief>', 'ingest https://...', 'rag-sync']"
---

Maintain the project's **LLM Wiki**. The requested scope/operation is whatever you were asked to do
(if none was specified, consider the relevant work done in this session → `record` operation).

**Single source of truth:** read the wiki playbook bundled with the `wiki-author` skill
(`wiki-playbook.md`) and **follow it**. It is the **index**
that defines host-agnosticism, taxonomy, conventions, and the D↔N boundary; the **procedure for each operation**
lives in an `ops/<operation>.md` module to `Read` on-demand (table in §5). Do not reinvent the rules here.

**Host-agnostic:** root, taxonomy, frontmatter, roles, and source folders come from
`wiki.config.toml`. The **mechanical** work (inventory, lint, scan, index) is handled by the `sertor-wiki-tools` CLI:
call it via Bash instead of manual Glob/Grep. **Judgment** (what to write, contradictions) remains with you.

Proceed as follows:

1. Read the **playbook** (index), then the wiki index and the tail of the log (file names from config) for current
   state; use `sertor-wiki-tools collect --json` for the mechanical page inventory.
2. **Determine the operation** from the request or from the session work, among:
   `record` · `distill` (durable entities from a step, backlog, or **brief of a full conversation**, even
   old/external — never the raw transcript: condense it first) · `ingest` · `query` · `lint` (levels A
   structural / B semantic / C organizational) ·
   `reorg` (applies the organizational refactoring from lint C, on confirmation) · `generate` (from-scratch on a host
   without a wiki, or incremental from-diff — the default; depth `light`/`medium`/`deep` as
   argument, default light) · `rag-sync`.
   Then `Read` **only the corresponding `ops/<operation>.md` module** (see table §5 of the playbook).
3. **Execute the corresponding procedure** from the module (input → steps → output), respecting its constraints —
   in particular: the main flow has **Bash** for heavy operations; `generate` from-diff delegates
   `git log/diff` to the VCS role (`[roles].vcs`), from-scratch does not require git; `rag-sync` launches
   `sertor-wiki-tools index`.
4. Update cross-references and the index, and append the log entry
   `## [YYYY-MM-DD] <operation> | <title>` (today's date).
5. Explicitly flag contradictions or orphan pages (`sertor-wiki-tools lint` finds orphans).

Keep pages concise and interlinked. Do not touch original sources or wikis excluded via `exclude`.
When done, summarize in 2-3 lines what you updated.
