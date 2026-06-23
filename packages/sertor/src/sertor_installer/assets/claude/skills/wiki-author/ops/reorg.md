# Operation `reorg` — apply organizational refactoring

> **Operation module.** Executor: **main flow only** (NOT the curator).
> For the **shared substrate** (D↔N boundary §2, taxonomy §3, log entry §6) see the playbook
> `wiki-playbook.md`; the target state of a page (placement, atomicity, links) is
> [`../page-craft.md`](../page-craft.md); *growth by refactoring* of the graph (split into entities+hub,
> merge micro-pages) is [`../wiki-craft.md`](../wiki-craft.md). Only the specific procedure is described here.

Applies, **on explicit user confirmation**, the proposals from **lint level C** (`ops/lint.md`). It is **more
destructive** than claim correction (moves files, rewrites links) → **never automatic, never blocking, one
increment at a time**. It is **judgment** (what to move/where/whether to split) + mechanical work via `Read`/`Edit`:
**not delegated to the `curator`**.

1. Start from the lint level C report and **agree with the user** on the pages to handle.
2. For each page: **move it** to the correct area (new path), **fix the `type`** in the frontmatter, and
   **update all incoming wikilinks** (from the backlinks computed in lint C) because area/slug change; update
   the index (line `- **[[slug]]** — summary` in the correct section). If splitting or rewriting, the resulting page
   must comply with [`../page-craft.md`](../page-craft.md) (atomicity, self-containment, links).
3. **Verify hygiene after the move:** `uv run --directory .sertor sertor-wiki-tools lint --json` **and** `… validate --json` →
   expected **0 broken links / 0 orphans / 0 naming**. If not, fix before continuing.
4. Append a log entry `reorg` (pages moved from→to, corrected `type` values).

> **Backlog (deterministic mechanics):** a `move`-with-link-update command in the CLI
> would make step 2 less fragile than manual `Edit` — to be done **only if** the manual approach
> proves noisy. **Detection** (level C) remains judgment, not deterministic.
