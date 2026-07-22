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

**Forced declaration (anti-silent-skip).** The closure of every significant step MUST emit an explicit
declaration — `Ritual: record <verdict> · distill: <verdict> · lint: <verdict>` — with a verdict for each
judgment step; "not needed" is fine but MUST be **declared, never omitted** (a silent skip is the failure
this prevents). To keep candidate *discovery* off memory, run `sertor-wiki-tools ritual-check` first: it
lists the step's distill/drift candidates (via git diff) + a declaration scaffold — the **tool finds, you
judge** (read-only, zero-LLM).

**Daily distill floor (enforced at merge).** A day that logged work MUST also log a `distill` — a real
distillation OR a reasoned "no" recorded as a distill entry that NAMES the candidates considered — before
you may **merge** to the mainline. A `PreToolUse` hook BLOCKS a delivery merge (`git merge <branch>` /
`gh pr merge`) when today's log has no `distill` entry: it is a hard gate, not a nudge. To satisfy it,
perform the distill (or run `sertor-wiki-tools append-log --entry-op distill --title "no: <why>"`), then
merge. The `distill-audit` operation lists candidate entities (referenced from ≥k points, no page) as a
deterministic hint attached to the block — the tool finds, you judge.

**Delegation.** That these actions happen is the main flow's responsibility; executing or delegating them
is merely a choice to avoid blocking. The `record` (structured transcription) is delegatable to the
`wiki-curator` agent; distillation and semantic lint, being judgment, stay in the main flow.
To manually trigger a consolidation, invoke the wiki capability of your assistant (main flow)
or delegate to `wiki-curator` (background).

**When to record:** at the same moment as the step commit. The log entry is
not deferrable: a step is not closed until both the commit **and** the log entry are done.

**Definition of Done — host-agnostic assets.** Touching a distributable asset (a skill, agent,
command, instruction block, or its support payload) requires verifying **parity across assistants**:
the body must stay host-agnostic (no literal assistant paths, no slash-command invocations, payload
referenced by name) so the SAME body works on every assistant. A step that edits such an asset is not
done until that parity holds (a parity guard enforces it where available).

For the full list of wiki operations (`record`/`distill`/`ingest`/`query`/`lint`/`reorg`/`generate`/
`rag-sync`/`structure`), the page conventions (frontmatter, wikilink backlinks, kebab-case naming) and
the log-entry format, see `wiki-playbook.md` — the single source of truth bundled with the wiki
capability, read on demand.
