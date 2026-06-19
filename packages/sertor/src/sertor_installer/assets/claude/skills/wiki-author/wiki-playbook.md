# Wiki Playbook — single source of truth for the wiki system

> **This file is the source of truth for the "wiki system".** The `wiki-author` skill, the wiki
> command/capability and the `wiki-curator` agent do not duplicate these rules: they **read them here**
> and follow them. If you modify a convention or an operation, modify it **only** in this file (or in the
> operation's `ops/` module).
>
> **Structure (index + modules):** this file is the **index** with the **shared substrate** (host-agnosticity,
> identity, D↔N boundary, taxonomy, conventions, log entry, limits). The **specific procedure of each operation**
> lives in an `ops/<operation>.md` module (same folder as this file), to `Read` **on-demand** — see §5. This way
> invoking a single operation does not load the procedures of all the others (progressive disclosure), without
> duplicating the substrate (DRY) and remaining portable `.md` documents (Principle X — no host-specific constructs).
>
> It is **tooling**, not wiki content: it lives alongside your assistant's skill files, it should not be indexed or recorded in the wiki.

## 0. Host-agnostic: the host is configured, not assumed

The wiki capability is **decoupled from the host project** (Principle X of the constitution). Everything that
varies between projects lives in **`wiki.config.toml`** (in `wiki/` on the host) — **single source of host-specifics**:

| Config key | What it defines |
|---|---|
| `root`, `index_file`, `log_file`, `log_dir` | where the wiki and its special files live (`log_dir` ⇒ log rotation to one file per day) |
| `[[taxonomy]]` | the logical areas (folder → frontmatter type) |
| `frontmatter_required` / `_optional` | the expected frontmatter fields |
| `source_dirs`, `exclude` | where to read the host's work from and what to ignore |
| `[[audit]]` | what to submit to lint and of what `kind` (wiki/requirements/spec/tracker) — see op. `lint` |
| `[roles]` | agent names: `curator` (this wiki), `vcs` (git) |
| `[rag]`, `[strings]`, `language` | RAG corpus, localized messages, language |

**Do not assume `wiki/`, `src/`, folder names or agent names**: read them from the config. The concrete examples
below (`wiki/`, `concepts/`, `src/`…) are **examples from the host profile**, **not** universal laws. On another
project only the config file changes.

### Host-agnostic authoring (this file and its sibling assets)

This playbook and the skill/agent/command bodies that read it are **distributed to multiple
assistants**. The SAME body must work on each, so when you edit these assets keep them host-agnostic:

- **No literal assistant paths.** Do not hard-code an assistant-specific directory in a body: the
  payload lives in a different place on each host. Reference a bundled support file **by name**
  instead (e.g. "read the wiki playbook bundled with this skill (`wiki-playbook.md`)"). Internal links
  *between* the playbook and its sibling modules stay **relative** (`ops/<x>.md`, `../wiki-craft.md`) —
  those travel together in the same container.
- **No slash-command invocations.** Do not name a `/command` as the way to invoke a capability (slash
  commands are not universal): describe it in capability-neutral terms (e.g. "trigger the wiki
  capability of your assistant" / "run the `record` operation").
- **No assistant product names** in instructional, LLM-facing text.

These rules are enforced by a **parity guard** (renders the distributable plans for every assistant
and fails on a leaked assistant path, a slash-command, an assistant name, or a payload file referenced
but not deposited — *reference closure*). See [[assistant-targeting]] for the targeting mechanism.

## 1. Identity & philosophy

The wiki is an **LLM Wiki** in the Karpathy style: *Obsidian is the IDE, the LLM is the programmer, the wiki is the
codebase*. Knowledge is **compiled once** and kept up to date, instead of being rebuilt at every
session.

- **Dual role:** the wiki is both **corpus** (queryable via RAG) and **surface**
  (navigable index injected at session start).
- **Cumulative:** grows at every session; no starting from scratch.
- **Idempotent:** if a page is already accurate, **do not rewrite it**. No pointless edits.
- **Self-contained:** every page is written so that an agent can resume it without the chat context.
- **Coherent by construction (anti-self-inflicted-drift):** when a change (to the code, to the rules or
  to another page) makes a page **stale**, realigning it **is part of the same work** — it is not
  a separate operation to request. The drift that *you* introduce is corrected **in the same step**, by
  default and without an explicit request; drift that you merely *discover* as pre-existing can become a worklist for
  `lint`. *(The host can codify this in its own step ritual, in its instruction file.)*

## 2. Deterministic core vs judgment (the boundary)

**Mechanical** bookkeeping is host-agnostic code already available: the CLI **`sertor-wiki-tools`**.
**Use it instead of redoing the mechanical work by hand.**

| CLI operation | What it does (mechanical) | JSON contract |
|---|---|---|
| `scan` | counts files more recent than the last log entry (pending work) | `wiki.scan/1` |
| `structure init` | creates taxonomy folders + index + log (idempotent) | `wiki.structure/1` |
| `validate` | missing frontmatter + non-kebab-case naming | `wiki.lint/1` |
| `lint` | broken wikilinks + orphan pages + missing frontmatter | `wiki.lint/1` |
| `collect` | enumerates pages + metadata (path, area, type, title, tags, wikilinks) | `wiki.collect/1` |
| `index` | re-indexes the wiki in the RAG (corpus from `[rag]`) | `wiki.index/1` |
| `append-log` | places a log entry (body curated by the LLM) in today's file, idempotent | `wiki.append_log/1` |
| `migrate` | retroactively splits the monolithic log into daily partitions | `wiki.migrate/1` |
| `upsert-index` | inserts/updates the `- [[page]] — summary` line in the index (LLM-authored summary) | `wiki.upsert_index/1` |

Invocation: `sertor-wiki-tools <op> --config wiki/wiki.config.toml --root . [--json]` (or, from the
host root, just `sertor-wiki-tools <op>`: the CLI auto-discovers `wiki/wiki.config.toml`).
With `--json` you get the versioned contract; without it, a human-readable summary.

**JUDGMENT is left to you (LLM)**, which the CLI does not provide: *what* to write and *why*, whether a page is new
or needs updating, *which* backlinks make sense, whether two claims **contradict** each other, whether a claim is outdated.
The *where/how* (paths, formats, mechanical detection) comes from the deterministic core.

## 3. Taxonomy (from the config)

The areas are those in `[[taxonomy]]`. Example profile:

```
<root>/             (e.g. wiki/)
├─ <index_file>     global catalog (links + one-line summary). READ THIS FIRST.
├─ <log_dir>/       append-only log, one file per day (rotation; or <log_file> single file if off)
├─ concepts/        concepts (RAG, chunking, embeddings, ...)
├─ tech/            technologies and tools
├─ experiments/     one page per activity/experiment
├─ sources/         summaries of ingested external sources
└─ syntheses/       cross-cutting comparisons and syntheses
```

- The **only** areas are those in the config. Ingested external sources go in **`sources/`** (see
  `ingest`); do not invent folders not declared in the config.
- Folders may not exist yet: **create them on-demand** for the first page in that category (or
  all at once with `sertor-wiki-tools structure init`). Do not create empty folders or placeholders.
- Any **frozen/do-not-touch wikis** (e.g. an archived historical wiki) are **outside** the `root`
  and excluded via `exclude`: they are not modified; they can be consulted via RAG if needed.

### Placement — choosing the area from the nature of the page

The area is chosen from the **logical nature** of the content, **not** from the phase/project (phase folders —
`sprint-3/`, `phase-azure/` — age poorly): the folder just gives **a home**, the value lies in the
links. The *why* — «a wiki is a graph, not a tree» and the two navigation axes — is in
[`wiki-craft.md`](wiki-craft.md) §4. Area roles (on each host the analogous roles of its `[[taxonomy]]` apply):

- **concepts/** — abstractions, patterns, ideas (a RAG concept, a technique). Evergreen.
- **tech/** — a concrete technology/tool/infra (a library, a service). Evergreen.
- **experiments/** — the **dated record** of an activity/step/feature completed (the implementation of a
  feature, a spike, a session). It is the diary of a piece of work, not an abstraction.
- **sources/** — the summary of an **external source** ingested (paper, blog, PR, third-party docs).
- **syntheses/** — a **cross-cutting comparison** between multiple concepts/experiments (A-vs-B, a synthesis that
  spans pages). This is the **rarest** category, **not** the default.

**Anti-dumping rule:** if you do not know where to put a page, it is usually because it is **not atomic** (it covers
too many things) or because **a category is missing** — that is a *signal*, not a gap to fill with `syntheses/`.
No area should be used as `misc/`. When in doubt between two areas, choose the one most specific to the nature; a page
is `syntheses/` **only** if it is truly a comparison between multiple concepts, otherwise almost never.

**`type` reflects the nature, not just the folder.** The frontmatter `type` must describe **what the page
really is** and coincide with the area that hosts it. Note: folder and `type` can be
*consistent with each other but both false* with respect to the content (e.g. a record in `syntheses/` with
`type: synthesis`). This **nature↔placement** misalignment is invisible to mechanical lint (which only sees
the string) and is the target of **lint level C** (module [`ops/lint.md`](ops/lint.md)).

**Graph level → [`page-craft.md`](page-craft.md) (the single page) and [`wiki-craft.md`](wiki-craft.md)
(the whole).** *When* something deserves a page (link/name test), **page archetypes**, structure pages (home/hub/overview)
and the two navigation axes are in `wiki-craft.md` — the graph-level guide, twin of `page-craft.md`.

## 4. Conventions

**YAML frontmatter** on every page (except append-only files). The expected fields are in
`frontmatter_required`/`_optional`. Example:
```yaml
---
title: <readable title>
type: <concept|tech|experiment|source|synthesis|index>
tags: [<tag>, ...]
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: ["<path or URL>", ...]
---
```

- **Stub (node to create):** a forward-link to a page not yet written is realized as a **stub**, not
  as an empty `[[…]]` (which lint A flags as `broken`). Mechanism and rules in [`page-craft.md`](page-craft.md) §4.
- **Wikilinks** `[[page-name]]` (without `.md`); alias with `[[page-name|displayed text]]`. Keep
  cross-references updated: a new page must be linked from the index and from related pages.
- **File naming**: descriptive kebab-case (`azure-ai-search.md`). `validate` checks this for you.
  - **Name language (example convention):** **entity/concept** pages (`concepts/`, `tech/`) have
    **slug and title in English** (`retrieval-core`, `thin-consumer`), while the **discursive body** can remain in the host language.
    **Records** (`experiments/`) remain in descriptive host language (they are events, not entities). Existing pages with
    non-English slugs are renamed **opportunistically** (when touched), not in bulk.
- **New vs update:** create a new page for a new concept/entity; **update** the existing one otherwise.
  One page per real concept, no duplicates (use `collect` to check).
- **Contradictions:** when a source/code contradicts a page, **report it explicitly** — do not
  choose silently. If it involves a decision or an authoritative human source, **ask the user**.
- **No over-documentation:** do not document the trivial or mechanical changes. Calibrate to value.

**What a page looks like *inside* → [`page-craft.md`](page-craft.md).** The rules above are
the *format* (frontmatter, naming, wikilinks, when to create/update). **Page-craft** — atomicity,
self-containment, link discipline and especially the **level of meaning** (*what* to write, not just
how) — lives in the reference page `page-craft.md`, **linked from the operations** that create or
rewrite pages (`record`, `ingest`, lint **C**, `reorg`). It is a leaf: the operations reference it
without this file depending on them.

### Truth, authority and obsolescence

**There is no single source of truth**: authority depends on the **axis** of the claim —
on **behavior**, **code + tests** win; on **why**, **recorded decisions** win
(log, requirements, process decisions). The wiki is **derived**: in conflict the default hierarchy applies
(behavior → code/tests · why → recorded decision); a hierarchy configured by the host can replace it (optional).

**A page is stale when it contradicts its authority.** The answer is NOT to correct silently,
nor to delete: it is **explicit supersession** —

1. **frontmatter**: `status: superseded` (the `status` field is among the optional ones in the config);
2. **banner at the top** with date, *what* supersedes the page and the **link** to the current truth
   (`> ⚠️ **Superseded (YYYY-MM-DD):** <claim> is contradicted by <authority> → see [[current-page]]`);
3. the **content remains** (as testimony; deleted errors get repeated): the page is pruned or merged into
   its successor only in a confirmed `reorg`, never automatically.

For the **diary** (log, dated records) supersession is natural: the correction is a **new entry**,
never an edit. For the **graph** the convention above is the equivalent. **No numeric confidence scores**:
the evidence is the chain of links/proof of the anchored claim (see the critiques in
the false precision of numeric scores). Who *detects* the contradiction is
lint B (or anyone, while working); who *decides* the marking is the main flow **on confirmation**
when the case involves decisions/authoritative human sources (the "Contradictions" convention above).

**Append-only files** (the log): they do **not** carry `updated` in the frontmatter (it would always be stale); their
state is given by the last entry.

## 5. Operations — index (on-demand loading)

Each operation = **input → steps → output** (pages touched + ONE log entry) and follows the **shared
substrate** of this file (D↔N boundary §2, taxonomy §3, conventions §4, log entry §6, limits §7);
whoever creates or rewrites pages also follows the page-craft in [`page-craft.md`](page-craft.md).
The **specific procedure** of each operation lives in an **`ops/<operation>.md` module** (same
folder as this file): **`Read` only the module for the operation you need** — do not load them all
(progressive disclosure). Documentary operations (`record`, `ingest`, `query`, lint **A**) can also be
run by the `curator` in background; lint **B/C**, `distill`, `reorg`, `generate` and
`rag-sync` require the **main flow**.

| Operation | Module (`Read` on-demand) | What it does | Executor |
|---|---|---|---|
| `record` | [`ops/record.md`](ops/record.md) | records completed work/decisions | curator OK |
| `distill` | [`ops/distill.md`](ops/distill.md) | extracts durable entities/concepts into their own pages (inputs: step just completed · fat record from backlog · brief of an entire conversation, even an old one); slims down dated records | main flow only |
| `ingest` | [`ops/ingest.md`](ops/ingest.md) | acquires an external source → `sources/` | curator OK |
| `query` | [`ops/query.md`](ops/query.md) | answers a question about the wiki (archives if valuable) | curator OK |
| `lint` | [`ops/lint.md`](ops/lint.md) | consistency at 3 levels: A structural · B semantic · C organizational | A: curator · B/C: main flow only |
| `reorg` | [`ops/reorg.md`](ops/reorg.md) | applies the organizational refactoring from lint C (on confirmation) | main flow only |
| `generate` | [`ops/generate.md`](ops/generate.md) | generates the wiki from the repo: **from-scratch** (bootstrap on a host without a wiki) or **from-diff** (incremental: only the pages impacted by recent changes); reconnaissance depth preset (`light`/`medium`/`massive`, default light) | main flow only |
| `rag-sync` | [`ops/rag-sync.md`](ops/rag-sync.md) | re-indexes the wiki in the RAG (the "corpus" role) | main flow only |
| `structure` | [`ops/structure.md`](ops/structure.md) | idempotent bootstrap of the structure | curator/CLI |

> **Write-back log/index.** Both **wired into the CLI**: the **log** with `append-log` (the LLM
> composes the **curated body** §6, the CLI places it in today's file) and the **index** line with
> `upsert-index` (`--page` + `--summary` or stdin; insert/update/noop idempotent, summary
> **always LLM-authored**, empty/multiline rejected). Nuance on the index: the CLI writes the
> **flat** line `- [[page]] — summary`; if the host's index is *curated* (bold text, sections),
> deciding whether to adopt the flat format or continue authoring the line by hand is **judgment**.

## 6. Log entry

Append to the log, one entry per operation, with **today's date**. With **rotation** (`log_dir`) the entry goes
in the **day's file** (`<log_dir>/YYYY-MM-DD.md`) and the **placement** is done by `append-log` (CLI) to
which you pass the **curated body**; without `log_dir`, a single log file (back-compat). Format:
```
## [YYYY-MM-DD] <operation> | <title>
<lead: 1–2 sentences with the why/trigger of the step>
- **<label>:** <salient fact or pointer [[page]], one line>
```
`<operation>` ∈ `setup` · `structure` · `record` · `distill` · `ingest` · `query` · `lint` · `reorg` ·
`generate` · `rag-sync` — the full set of operations from §5 plus `setup` (generic session/governance bootstrap,
distinct from `structure` which is the bootstrap of the *wiki structure*). `structure`
leaves an entry **only if it created something** (`created` not empty); if everything is `skipped_existing`,
no entry (idempotent + anti-trivial rule). *Back-compatibility:* historical entries
`generate-from-diff` in logs remain valid (the log is append-only, never rewritten); from 2026-06-10 the
current vocabulary uses `generate`.

**What makes a good entry → [`log-craft.md`](log-craft.md).** The rules above are the *convention*
(heading grammar, operation vocabulary, anti-trivial rule). **Log-craft** — the log↔page boundary (what goes in the dated log vs. in the evergreen page), the anatomy of the entry (lead + flat bullets +
outcome line), **granularity** and **anti-drift** (no content dump, no file lists, no adjectives) —
lives in the leaf page twin of [`page-craft.md`](page-craft.md), linked from the operations that append
an entry (`record`, `ingest`, `lint`, `reorg`, …).

## 7. Limits & delegations

- **Git:** never execute it directly. All git operations (including reads for the `generate`
  from-diff) are **delegated to the VCS role** (`[roles].vcs`). The `curator` does not run git.
- **Sources & frozen wikis:** never touch the original sources given to `ingest`, nor the wikis excluded via
  `exclude`.
- **When NOT to document:** purely mechanical or minor changes do not deserve an entry.
- **Versioning:** when the user wants to version, delegate to the VCS role a commit `docs(wiki):
  <summary>` with selective staging of the wiki root.
