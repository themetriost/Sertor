---
name: wiki-author
description: Generates/updates the project LLM Wiki by reading the repo and writing pages. Use it when the user says "generate the wiki", "update the wiki", "document the project in the wiki". Karpathy pattern: the agent reads the sources and writes the .md files.
---

# Generate the LLM Wiki (author)

You are the **author** of the project's LLM Wiki: you read the repo and write/update wiki pages.

**Single source of truth:** read the wiki playbook bundled with this skill (`wiki-playbook.md`, same
folder) and **follow it**. It is the **index** with identity, taxonomy, conventions and the D↔N boundary;
the **procedure for each operation** lives in an `ops/<operation>.md` module to `Read` on-demand (see §5
of the playbook). For this skill the typical operation is `record` → load `ops/record.md`. Do not
duplicate those rules here.

**Host-agnostic:** wiki root, taxonomy, frontmatter fields, roles and source folders come from
`wiki.config.toml` (in `wiki/` on the host) — do not assume them. For the *mechanical* work (inventory, lint) use the
CLI `sertor-wiki-tools` instead of Glob/Grep by hand (see playbook).

## Specific to this skill (operation `record` from the repo)

1. **Read the playbook first**, then the wiki index (catalog) to know what already exists; run
   `uv run --project .sertor sertor-wiki-tools collect --json` for the mechanical inventory of pages.
2. Determine the **scope**:
   - if the user specifies an area/feature, **limit yourself to that**;
   - otherwise cover the relevant parts of the repo starting from the **`source_dirs`** in the config (code and
     tests → the *what/how*; specs/requirements → the *why*).
3. Apply the `record` operation from the playbook: create/update pages (one per concept, idempotent),
   update backlinks and the index, append the log entry.
4. Report contradictions instead of resolving them silently (see playbook).

To ingest an external source, lint for consistency, generate the wiki from the repo or update it from
the git diff (operation `generate`, inputs from-scratch/from-diff) or re-index in the RAG, use the
corresponding operations in the playbook (trigger the wiki capability of your assistant for the chosen
operation).

## Versioning (optional)
At the end of generation, if the user wants to version, **delegate to the VCS role** (`[roles].vcs` in config; never direct git):
commit `docs(wiki): generate/update pages` with selective staging of the wiki root.
