# Operation `record` — record completed work/decisions

> **Operation module.** Executor: **curator OK** (background) or main flow.
> For the **shared substrate** (D↔N boundary §2, taxonomy §3, log entry §6) see the playbook
> `wiki-playbook.md`; for **how to write a page** [`../page-craft.md`](../page-craft.md), for **whether
> something deserves a page** (and which archetype) [`../wiki-craft.md`](../wiki-craft.md). Only the specific procedure is described here.
>
> **Boundary with `distill`.** This record captures the **dated event**; the **durable entities** that the work
> surfaces (domain entities, ports, adapters, services, decisions, technologies) **are not** buried
> here — they are extracted into dedicated pages with [`distill.md`](distill.md) (step ritual, point 2). The record
> stays lean and *points to* them.

1. Mechanical inventory: `uv run --project .sertor sertor-wiki-tools collect --json` (what already exists) + read the wiki
   index (`index.md`).
2. **Write/update the page(s) — content judgment.** Decide *new-vs-update* (the `collect` from
   step 1 serves to avoid duplicating a concept already present); for *whether* it deserves its own page apply the
   link/name tests from [`../wiki-craft.md`](../wiki-craft.md) (do not fragment). Choose the area from the **nature** of the page
   (taxonomy: playbook §3) and write it following [`../page-craft.md`](../page-craft.md) — in
   particular the **level of meaning**: distill the *why* of the step (not the diary, which is the log),
   capture decisions with **discarded alternatives**, keep the claim at the **abstraction level of the area**
   (evergreen in `concepts/`/`tech/`, dated state in `experiments/`). **Judgment:** what is reusable knowledge vs chronicle, and *which* backlinks say **why** two pages connect.
3. Update backlinks and the index (link + one-line summary).
4. Append a log entry `record`: **compose the curated body** (format: playbook §6; how to write it:
   [`../log-craft.md`](../log-craft.md)) and have it **placed** by `append-log` (CLI) in the
   day's file; without rotation, append to the single log.
