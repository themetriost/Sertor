# How to write a well-crafted page — anatomy of page-craft

> **Reference page (leaf).** Describes *what a good wiki page looks like* — structure,
> content, meaning, links. It is **linked from** whoever creates or rewrites pages (`ops/record.md`,
> `ops/ingest.md`, `ops/query.md`, and the judgment of `ops/lint.md` level C and `ops/reorg.md`). It is a
> **leaf**: it does not depend on other documents in the system — the operations reference it, not the other way around.
> For the level *above* — *what deserves to be a page* and how the whole holds together (archetypes,
> structure pages, the two axes, graph hygiene): the twin page [`wiki-craft.md`](wiki-craft.md).
>
> **Host-agnostic (Principle X).** The principles here apply on any host; what *varies* — frontmatter
> fields, link syntax, and the existence of constructs such as automatic TOC, tags, status/owner, redirects
> or parent/child hierarchies — comes from the host profile (`wiki.config.toml`) and from the
> host's capabilities. The concrete examples (`[[wikilink]]`, `concepts/`, `title/type/tags…`) are **illustrative**,
> not universal laws: on another project only the rendering changes, not the principles.

A well-crafted page has four qualities: a predictable **structure**, actionable **content**, the right
**level of meaning**, and dense **links**. The first two are form, meaning is substance, links are what
transforms a set of pages into a *wiki*.

## 1. Page structure (top to bottom)

1. **Unique title** — describes **one** thing. No vague titles ("Notes", "Misc") and no duplicates with other
   pages (kebab-case naming and uniqueness are mechanically verifiable, lint A).
2. **Lead (opening)** — in 1–3 lines answers «what is this page about?» **without assuming** that the
   reader has read anything else. It must stand on its own: it is often the only thing that gets read, and it is the first
   chunk the RAG retrieves *out of context*. Open with «**X is …**», not with «This concept was seen in…».
3. **Table of contents (TOC)** — *if the host generates it* (Obsidian, MediaWiki…) and the page exceeds ~3–4 sections. In
   markdown-only wikis it is optional.
4. **Body in sections** with **real hierarchical** headings (H2 for main sections, H3 for
   sub-sections): the hierarchy reflects the content, it is not decorative.
5. **"See also" / related** at the bottom — a navigation *supplement* (see §4: does not replace inline links).
6. **References / sources** if the page asserts verifiable facts (e.g. frontmatter field
   `sources`).
7. **Metadata** — the frontmatter with the fields expected by the profile (`frontmatter_required`/`_optional` in
   config; e.g. `title`, `type`, `tags`, `created`, `updated`, `sources`). Fields such as status
   (draft/in review/stable) or owner **only if** the host/profile provides them.

## 2. Content types

- **One page = one concept.** If you find yourself describing two distinct topics, those are **two pages**
  linked together, not one. Atomic pages link better, are reused in more contexts and **chunk
  cleanly** for RAG. Under the pressure of appending this is where things break down (duplicate sections, two state blocks):
  *stitch or split*, do not append. (*Whether* something deserves its own page — the split vs.
  anti-fragmentation criterion, and the *product lens* on which code entities to extract — is in
  [`wiki-craft.md`](wiki-craft.md) §1–§2.)
- **Inverted pyramid** — most important information first, then details, then edge cases. The
  reader must be able to stop halfway and have already understood the essentials.
- **Concrete and actionable** — examples, snippets, commands, tables. A procedure should be written as a **numbered
  list** of steps.
- **Self-contained but not redundant** — explain what is necessary, but for concepts that already have their own
  page **link, don't copy**: duplicated information ages in two different places (this is *Single
  Source of Truth* at graph level → [`wiki-craft.md`](wiki-craft.md) §5).
- **Code is not copied: it is described and cited.** A **snippet** is a *copy* of the code that diverges
  the moment the code changes → it is the **primary source of drift** (lint B finds it; in fat dumps it is almost always
  the snippet that is stale or fabricated). Describe the **interface** and the **behavior** and **cite the
  file** (`path`); use a snippet **only** to illustrate a *stable concept*, never the current implementation.
  This applies to file names, symbols and signatures too: **cite them, do not transcribe them by hand**.
- **Neutral and direct style** — short sentences, active voice, no walls of text; lists and tables when
  data is structured.
- **Maintainability** — information that changes (versions, owner, URLs) goes in **one place and clearly visible**.

## 3. The level of meaning — *what* to write, not just how

This is the substance, beyond the form. A page captures **distilled, reusable knowledge**, not the chronicle of
what happened (that goes in the log). Write so that a **future LLM**, retrieving it *cold* via RAG,
can act on it.

- **Distill, don't transcribe.** The page answers «what does someone resuming this need to know», not «what did we
  do step by step». The chronological diary is the log; the page is what *remains*.
- **Capture the *why* and the rejected alternatives.** A decision without rationale and without the
  rejected options will be **relitigated**. Write: what was decided · why · what was rejected and why.
- **Abstraction consistent with the area.** A `concept`/`tech` page is **evergreen**: the central claim is
  timeless, **no volatile state** (PR#, "in progress", counts) in the body — it ages and becomes drift
  (lint B). Dated state lives in `experiments`. The *why* generalizes; the situated *what* goes in the record.
- **Anchored truth.** Write only claims that are **true at the time of writing and anchorable** (code/tests/git/
  source). What you cannot ground is not content: it is a hypothesis → mark it as such (this is the active counterpart
  of lint B).
- **Density of meaning.** Every sentence carries information; cut the filler. *Compile once*: write
  so it does not need to be rewritten.

*Example — the same notion, written poorly → well:*
- ✗ «Today we discussed reranking at length and in the end, after various attempts, we decided to use the
  cross-encoder which seemed to perform better than the others in the tests.» — *diary, vague, not anchored, no
  reusable why.*
- ✓ «**Cross-encoder reranking** re-orders the top-k retrieval results by evaluating the (query, chunk) pair
  together: more accurate than the bi-encoder but costs O(k) inferences → applied **only to candidates**, not
  to the index. Preferred over BM25+rerank because [reason]; LLM-as-judge reranking was rejected for latency/cost
  disproportionate to the gain.» — *defines, gives the trade-off and the why, is timeless and anchorable.*

## 4. Link types

Links are what transforms a set of pages into a true wiki. Three useful categories, **distinct**:

- **Contextual internal links** — the **first time** you mention a concept that has its own page, link it
  **inline** in the text (e.g. `[[page-name]]`; alias with `[[page-name|displayed text]]`). Link
  the **first occurrence**, not all of them. This is where the value lies: the contextual link says *why* two pages
  are connected.
- **Structural navigation** — "See also", categories/tags, and — *where the host has hierarchies* — parent/child
  pages. In the **graph** model (not tree) of this wiki: wikilinks + taxonomy areas.
  Used to explore the neighborhood of a page. Do **not** replace contextual links: relegating all
  links to a final section instead of inline is an organizational *smell* (lint C).
- **External / references** — sources, official documentation, tickets, RFCs: in a **dedicated section** or
  as notes, **not** mixed with the text like internal links.

Practical link rules:
- **Link text describes the destination** («see the deploy guide»), never «click here».
- **No orphans or dead-ends:** every page should be reachable from at least one other and in turn
  point to something (orphans are found by lint A).
- **Forward-link → create a *stub*.** Linking forward to a node **not yet written** is a *feature* (marks
  a node to be created), but **do not** leave an empty `[[…]]`: lint A would flag it as **broken** (for
  the tool a non-existent target is indistinguishable from a typo). Instead realize the node as a **stub** —
  a **real file** in the right area, with complete frontmatter, `status: stub` and a placeholder body
  `> 🚧 STUB`. This way the link **resolves** (lint A green) and the node is *intentional*; conversely an empty `[[…]]` without
  a page or stub remains **broken** — this is how an **intentional node** is distinguished from a **typo**. The stub has
  ≥1 incoming link (the one that motivated it) → it is not an orphan; **fill it as soon as possible** (a stub
  left for a long time is a lint C *smell*). Lint A lists them in the **`stubs`** field (worklist of nodes
  to fill), separated from defects.
- **Do not over-link:** too many links make the text unreadable and drain value from the important ones
  (density ≠ quality). Prefer **specific** links to the right page, not to container pages.
- **No unnecessary circular links** nor — *where the host has redirects* — chained redirects.

## Quick checklist

| Criterion | Question to ask yourself |
|---|---|
| Title | Is it unique and does it describe one thing? |
| Lead | Do the first lines explain everything on their own? |
| Structure | Hierarchical headings (+ TOC if the host generates it)? |
| Scope | One concept per page? |
| Content | Concrete examples, inverted pyramid? |
| Meaning | Distills the *why* + alternatives; anchored and timeless claim? |
| Internal links | First occurrence linked, descriptive text? |
| Navigation | "See also" + categories/tags, without relegating inline links? |
| Sources | Do verifiable statements have references? |
| Maintenance | Status/owner/date visible (if provided)? No duplications? |
