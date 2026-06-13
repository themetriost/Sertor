# Wiki-craft — what deserves a page and how the whole holds together

> **Reference page (leaf).** If [`page-craft.md`](page-craft.md) describes *what **one** page
> looks like*, **wiki-craft** describes the level above: *what deserves to be a page* and *how the whole holds
> together* — page archetypes, structure pages, the two navigation axes, graph-level hygiene. It is **linked
> from** whoever decides whether to create/move pages or judges the health of the graph (playbook §3,
> `ops/record.md`, `ops/ingest.md`, `ops/reorg.md`, `ops/lint.md` level C). It is a **leaf**: it does not
> depend on the playbook (the operations reference it, not the other way around).
>
> **Host-agnostic (Principle X).** The principles apply on any host; what *varies* — the **areas** of the
> taxonomy, the existence of tags/categories, of per-area hubs or of a home — comes from the profile
> (`wiki.config.toml`). The archetype mapping and examples below are **illustrative**.

## 1. When to create a page (the fundamental rule)

A thing becomes a page when it has **its own identity** and is **referenced from multiple points**. Two tests:

- **Link test** — if multiple pages need to link that concept, it is an **autonomous entity** →
  its own page. If only **one** page mentions it, it is a **paragraph** inside that page.
- **Name test** — if the thing has a **stable name** by which it is referred to («the Billing service»,
  «the onboarding procedure»), it is probably a page.

**Opposite error to avoid: fragmentation.** Many two-line micro-pages are worse than one well-structured page.
Create a page when the content **stands on its own** and is **referenced enough** to be useful elsewhere.
(The *how* to write it, once decided: [`page-craft.md`](page-craft.md).)

## 2. Page archetypes (what shape to give)

A healthy wiki is made of a few recurring **archetypes**. Recognizing them immediately tells you what shape to give what
you are writing — and this is the distinction of the **Diátaxis** framework: keeping these types separate prevents pages
from becoming unreadable stews. **Do not mix** a how-to with a philosophical explanation:
*link them*.

| Archetype | What it is | Example |
|---|---|---|
| **Entity / Concept** | describes something that exists: a component, a term, a service | «Payments Service», «idempotency» |
| **Procedure / How-to** | how to do something, step by step | «How to deploy to production» |
| **Reference** | data to look up, not narrative | «API endpoint table», «Environment variables» |
| **Explanation / Discussion** | the *why*, decisions, rationale | «Why Postgres», an ADR |
| **Index / Hub** | has no content of its own, orchestrates other pages | «Backend Index», «Onboarding» |

**Example mapping.** When taxonomy areas are *by nature* (`concepts`/`tech`/`experiments`/
`sources`/`syntheses`) they **cut across** archetypes: the archetype is the *form*, the area is the *home* (see
playbook §3). Mapping: Entity/Concept → `concepts`/`tech`; Explanation/rationale → `syntheses` (+ dated
rationale in `experiments` records); Reference → usually `tech` or a section, not an area of its own;
Hub → the only hub is the global `index.md`. A project may **not use** all archetypes (e.g. no operational
how-tos in the wiki, no per-area hubs). That is fine: use only the archetypes that are needed, do not force them.

### The product lens — which entities in a **codebase** deserve a page

The archetypes above are general; when the host is **code** the question «what deserves
a page?» (§1) specializes. Code constructs that have **their own identity** and are **referenced
from multiple points** become entity pages; the others remain paragraphs inside their container's page.

| Code construct | Archetype | Area (example) | Example |
|---|---|---|---|
| **Domain entity** (a model type) | Entity/Concept | `concepts` | `Document`, `Chunk`, `RetrievalResult` |
| **Port / contract** (Protocol, interface) | Entity/Concept | `concepts` | `EmbeddingProvider`, `VectorStore` |
| **Adapter / concrete implementation** | Entity/Concept | `tech` | Chroma adapter, Ollama provider |
| **Service / orchestrator** | Entity/Concept | `concepts` | chunking dispatcher, retrieval facade |
| **Architectural decision** (the *why* of a choice) | Explanation/ADR | `syntheses` (+ dated in `experiments`) | `_Node` wrapper, non-uniform error policy |
| **Technology / external library** | Entity/Concept | `tech` | `tree-sitter-language-pack` |

**Anti-fragmentation (doubly important for code).** *Not* a page for every class or function: the vast majority
of the code is implementation detail, not an entity. The filter remains §1 — a construct becomes a page only if
it has a **stable name** by which it is referred to and if **multiple pages** would need to link it. A
port yes (referenced by the entity, the adapter, the composition); a private method no.

**Distillation (operation `distill`).** Extracting these entities from the dated record of a piece of work — instead of
leaving them buried in the session diary — is the job of the `distill` operation (`ops/distill.md`, part of the
step ritual): the `experiment` record remains the **event** (what, when, outcome, pointers), the entities live
in their own pages.

**What to put — and what not — per archetype (two recurring cuts on a codebase):**
- **`tech` page (external technology):** captures *how the host uses it* — the binding, the wrapper, the version/config
  choices — **not** the generic tutorial of the technology (that is in its official docs:
  **link it**, do not copy it). The copied tutorial is filler that bloats and ages, and is not what someone resuming
  *your* project needs.
- **`experiment` record (feature/activity):** is **event + outcome + pointers**, not a treatise. It does not duplicate
  the **process artifacts** that live elsewhere (e.g. `specs/`/`requirements/` — task/risk/decision tables,
  git hashes): it **cites** them. The outcome goes in one line (test · check ·
  merge); *what it is* goes in the entity pages, not in the diary.

## 3. Structure pages (the scaffolding)

They do not describe content: they **hold the network together**.

- **Home** — an *entry point*, not a container. It answers in a few seconds «where am I? what is here? where do I start?»:
  a sentence of purpose, the 4–6 main entry points, the most used pages. Not long, not full of knowledge that ages.
- **Hub / index** — one per major area; groups and orders the pages in that area. Intermediate level between
  Home and leaves.
- **Overview** — when an area is complex: *tells* the domain and then links to the detail. Difference
  from a hub: the hub is **navigation** (list of links), the overview **explains** and then links.
- **Glossary** — the anchor for atomic and recurring concepts, so you do not re-explain them everywhere.
- **Categories / tags** — **cross-cutting** navigation that cuts across the hierarchy (e.g. all «deprecated», all
  «security»).

**Example.** `index.md` can serve as both **home + global hub** (catalog with a per-page summary); the `tags`
in the frontmatter are the **cross-cutting categories**. If there are no per-area hubs/overviews yet (the
taxonomy is flat) and an area grows significantly, an overview in `syntheses/` is the natural move.

## 4. The two navigation axes (they coexist)

A good wiki always has **two axes**, not one:

1. **Hierarchy (tree)** — Home → Hub → Page. Gives the sense of **position** («where am I»). Ideal depth
   **2–3 levels**, rarely more: at 5 levels you get lost.
2. **Network (horizontal links)** — **contextual** connections between pages. Give the sense of **relation**
   («what does this have to do with that»).

The classic error is to have **only one**: only tree (rigid, you need to already know where something is) or only network
(you get lost, no fixed point).

**Example.** A **deliberately flat** tree — one level of areas + `index.md` as home/hub — puts the bulk
of the value in the **network** of `[[wikilinks]]`. This is the meaning of «a wiki is a graph, not a tree»: the
folder gives only *a home*, the links give the *meaning* (**placement** by nature — which home — is in
the playbook §3). The nuance here: even a flat tree is an axis — it serves as a fixed point, it should not be
abolished, only kept shallow.

## 5. Wiki-level hygiene

- **One canonical page per concept** (Single Source of Truth). If the same thing is explained in two
  places, they will eventually diverge: the others **link, not copy**.
- **No orphans or dead-ends** — every node must be in the network; the **link discipline** that ensures this
  is at page level → [`page-craft.md`](page-craft.md) §4 (orphans are found by lint A).
- **Consistent and predictable naming** — stable conventions on titles/slugs, so you can guess where something
  is and how to link it (e.g. kebab-case; entities/concepts in English — see playbook §4).
- **Consistency > completeness** — better a few live and updated pages than a hundred dead ones: an **obsolete**
  page is worse than a missing one because it betrays trust (this is what [`page-craft.md`](page-craft.md) calls
  *anchored truth* and what lint B defends).
- **Growth through refactoring, not accumulation** — when a page becomes too large, split it into
  *entity + hub*; when there are too many micro-pages, **merge** them. The structure is alive, prune it like a
  garden (this is the `reorg` operation).

## The mental model

Think of the wiki as a **graph with scaffolding**:

- **Content nodes** (entities, how-tos, references, explanations) = the knowledge → one per concept, of the right type.
- **Structure nodes** (home, hub, overview, glossary, categories) = the scaffolding that makes the knowledge
  *findable*.
- **Links** = the connective tissue, on two axes: **hierarchy** (where am I) + **network** (what does it relate to).
- **The golden rule for *when*:** create a page when something has a **stable name** and is
  **referenced from multiple points**.
