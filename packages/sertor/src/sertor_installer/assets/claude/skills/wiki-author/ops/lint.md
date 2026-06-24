# Operation `lint` — consistency check

> **Operation module.** Executor: **A** = curator OK · **B/C** = main flow only.
> For the **shared substrate** (D↔N boundary §2, taxonomy §3, log entry §6) see the playbook
> `wiki-playbook.md`; lint **C** judges against **how a page should look**
> ([`../page-craft.md`](../page-craft.md)) and **how the whole should look** ([`../wiki-craft.md`](../wiki-craft.md)).
> Only the specific procedure is described here.

Lint has **three levels**: **A** structural (mechanical, CLI: hygiene), **B** semantic (judgment, LLM:
*claim ↔ repo reality*) and **C** organizational (judgment, LLM: *placement/atomicity/links*). A is the
baseline; B and C are orthogonal (you can run them together or separately). **Do not auto-correct** by default:
produce a **report with severity** and correct **only on confirmation** (or if the brief requires it); applying
organizational refactoring is the `reorg` operation (`ops/reorg.md`). Log entry `lint` (optional but
recommended if you correct).

**Scope: what to lint (`[[audit]]`).** Lint **not** only the wiki: it covers the targets declared in
`[[audit]]` (config). Each target = `paths` (host glob) + `kind` (universal profile below).
**First matching rule wins** (more specific `paths` go first): so `TODO.md`/`tasks.md`/
`checklists` fall into `tracker` even if they are under `requirements/`/`specs/`. The `kind` determines
**which levels** apply and **what counts as drift** — this is what avoids false positives (do not treat
*intent* as *state*; authority hierarchy: code/tests = behavior, requirements/spec = why).

| `kind` | Level A (structural) | Level B (semantic) — what is "drift" | Default action |
|---|---|---|---|
| `wiki` | **yes** (CLI: wikilinks/frontmatter/orphans/naming) | descriptive claim contradicted by code/tests · contradictions between pages · coverage · stale summary | report |
| `requirements` | no (no wikilinks/frontmatter) | **only STATUS claims** (implemented/merged/counts/IDs); a "*shall X*" not yet in code = **backlog, NOT drift** | report |
| `spec` | no | like `requirements` + consistency with code **if** state declares "implemented" | report |
| `tracker` | no | **status tables/checkboxes** ("DONE/to do", `[x]`/`[ ]`) contradicted by reality = **direct drift** | report |

**A) Structural lint — 100% mechanical (CLI).** Run `uv run --project .sertor sertor-wiki-tools lint --json` **and**
`… validate --json`; interpret the `wiki.lint/1` contracts (broken wikilinks, orphans, missing frontmatter,
naming). **Do not** redo Glob/Grep manually. It is authoritative on links: if the CLI says 0 broken, the links are fine.
Note on **forward-links**: a `[[…]]` toward a node yet to be created **must not** be left dangling (it would be `broken`,
indistinguishable from a typo) → create a **stub** page (`status: stub`, see `../page-craft.md`), so the
link resolves. Therefore: target with file (even stub) = ok; target without file = `broken` (typo to fix).
The `lint` exposes stubs in the **`stubs`** field of the contract (worklist of *nodes to fill*), distinct from
defects: a stub is not an error, it is a deliberate node awaiting content.

**B) Semantic lint — judgment (LLM, main flow).** Verify that the **artifacts declared in
`[[audit]]`** (not only the wiki: also `requirements`/`spec`/`tracker`) **are not drifted** from the
reality of the project, applying the **profile of the `kind`** (table above). This is **judgment**: it stays with the LLM and **normally with the main flow**, which has
context; **the judgment part is not delegated to the `curator`** (see index §7 and the host's step ritual).
Repeatable procedure:

1. **Baseline** = the report from (A).
2. **Extract verifiable claims** from the pages (use `collect` for the inventory): counts (tests, modules,
   languages…), states (`merged`, `in progress`, branch/PR/commit), versions, dates, paths/symbols cited as
   existing, entity names. *(For fan-out over many pages you can delegate EXTRACTION to a reader; judgment stays yours.)*
3. **Retrieve ground truth from the repo** — rely on **already available tools**, do not reinvent them:
   - **git** (state/PR/branch/commit) → **delegate to the VCS role** (`[roles].vcs`); git operations are not executed here.
   - **file/symbol existence, values in code** → the **host's RAG** if configured (MCP server of the code corpus:
     `search_code`/`find_symbol`/`search_docs`); **otherwise** direct inspection (`Read`/`Grep`).
   - **build/test counts** → the host's tool (e.g. `pytest --collect-only -q`).
4. **Compare claim ↔ ground truth → judge.** A claim is **drift** if the repo contradicts it. Taxonomy
   of checks: *outdated git/PR/branch state* · *numbers inconsistent with code* · *cited but absent files/symbols*
   · *old dates/versions* · *contradictions between pages* · *claims older than `sources`* · *coverage* (real
   things in the project not yet documented).
5. **Report with severity** (High/Medium/Low/Info) + proposed correction for each finding. **Discard false
   positives** (e.g. a reader flagging "missing" links already disproved by the CLI).
6. **Correct on confirmation.** Update **only active pages** (current state); **do not rewrite** the historical
   log or dated artifacts. Append a log entry `lint`.
7. **When the finding is a superseded page** (not a typo to fix: the page as a whole is
   contradicted by the authority — code/tests on behavior, recorded decision on why), apply the
   **explicit supersession** from playbook §4 (*Truth, authority and obsolescence*): `status: superseded` +
   dated banner with link to current truth. **Never delete by default**: the page is pruned/merged only
   in a confirmed `reorg`. The hierarchy used to judge the conflict is that of the same section of playbook §4.

**Host-agnostic (degradation by profile).** Available probes depend on the host: on a **doc-only** host
there are no code tests/symbols → skip code probes and keep date/contradiction/coverage checks;
on a **code-only** host skip doc-specific checks. git is almost always available; RAG is an **accelerator when
present**, never a prerequisite (fallback on `Read`/`Grep`). Do not assume `pytest`/`src/`: derive them from `source_dirs`/profile.

**At commit (target behavior: A + incremental B).** At commit run level **A** (structural, on
`wiki` targets) **and** level **B** **only on changeset artifacts** (incremental, never the entire repo),
for each `kind`; outcome = **report + NON-blocking warning** (never blocking, never auto-fix — lesson: the value is in
detection, not in automatic correction). **Automation caveat:** A at commit is mechanical
(hook/CLI); **B at commit is LLM judgment** → its automatic execution depends on the orchestration/trigger
(deterministic side, cf. `ops/generate.md` and the trigger-contract, not wired today). Until it is wired:
the warning at commit covers A and **reminds you to run incremental B** (the `lint` operation on the changeset).

**C) Organizational lint — judgment (LLM, main flow).** Verify that the wiki is a **well-organized
graph** (criteria in [`../wiki-craft.md`](../wiki-craft.md): archetypes, structure pages, two axes,
SSoT, no fragmentation), not just hygienically sound. This is **all judgment**: placement and nature of a page **are
not deterministic** — folder and `type` can agree with each other and **both lie** about the content,
so no mechanical check catches them. Stays with the main flow, **not** with the `curator`. Applied to the `wiki` `kind` only, **on-demand** (not at commit). Starting inventory: `collect`
(rel_path/area/`type`/tags/wikilinks); **backlinks are not exposed** by the CLI → **compute them by inverting** the
`wikilinks` from `collect`. Checks:

1. **Placement vs nature** — the real nature of the page does not match the area hosting it (e.g. a
   feature record in `syntheses/`). Reference: the placement heuristic in playbook §3.
2. **Semantically false `type`** — `type` consistent with the folder but not with the content (nature↔placement
   drift).
3. **Collapsed taxonomy** — one area used as a dumping ground (disproportionate share of pages, especially in
   a "rare" area like `syntheses/`) while other declared areas remain empty even though content exists that would fill them.
4. **Atomicity** — pages with multiple focuses or duplicated sections (candidates for splitting; see `page-craft.md` §1).
5. **Link discipline** — links relegated to "see also" instead of inline; central pages but weakly
   connected (few backlinks). See `page-craft.md` §3.

Outcome = **report with severity + proposal** per finding (move to `<area>` · fix `type` · split ·
add inline links), **no auto-fix**. Applying on confirmation is the `reorg` operation (`ops/reorg.md`).
