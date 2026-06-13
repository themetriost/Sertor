# Operation `distill` — extract durable entities, slim down records

> **Operation module.** Executor: **main flow only (Opus)** — this is judgment (what counts as an entity, how to
> abstract it), not transcription: it is not delegated to the `curator` (Haiku), like lint B/C and `reorg`. For the
> **shared substrate** (taxonomy §3, log entry §6) see `wiki-playbook.md`; for **whether/what deserves a
> page** [`../wiki-craft.md`](../wiki-craft.md) (§1 + the *product lens* §2), for **how to write the entity page**
> [`../page-craft.md`](../page-craft.md). Only the specific procedure is described here.

Distillation is the **dual** of `record`: where `record` captures the **dated event**, `distill` extracts the
**durable knowledge** into dedicated entity pages, so it does not remain buried in the session diary. Three
**inputs**, same judgment:

- **step-driven** (the typical case): second step of the ritual (immediately after `record`, see the host ritual,
  e.g. in `CLAUDE.md`) — a **newly implemented feature**: the record is born *lean by design*
  (event + outcome + pointers), entities go into pages;
- **from backlog**, on request: an old fat record to be slimmed down;
- **from conversation**: the **condensed brief** of an entire conversation/session
  — even an old one, never recorded in real time, or that happened elsewhere — to be poured into the graph.
  **Never the raw transcript**: the caller condenses first (input arrives already pre-processed).
  This is the *safety net* for when the ritual was absent. If the brief also contains **events** not in the diary
  (completed work never recorded), a contextual `record` captures them: `distill` writes the durable into the
  graph, it does not write chronicles.

1. **Source material.** The work just completed (touched code + the `experiment` record just written), or — in
   backlog mode — an existing fat page to distill, or — in conversation mode — the condensed brief of a session
   (decisions, concepts, outcomes). `collect --json` to find out which entities already have a page (anti-duplication).
2. **Enumerate entity candidates.** From the material, list constructs with **their own identity**: domain
   entities, ports/contracts, adapters, services, architectural decisions, technologies (the *product lens*
   in [`../wiki-craft.md`](../wiki-craft.md) §2).
3. **Filter (test from [`../wiki-craft.md`](../wiki-craft.md) §1).** Keep only candidates with a **stable name**
   and **referenced from multiple points**; discard implementation detail (a private method is not a page).
   **Anti-fragmentation:** few living pages, not one micro-page per class.
4. **Create/enrich the page** for each surviving candidate, in the right area (taxonomy §3), following
   [`../page-craft.md`](../page-craft.md): **definition at the top** ("X is…"), the *why*, **relationships
   with neighbors** (entity→port→adapter→service), anchored **evergreen** claim. If the page already exists and is
   already rich, **do not duplicate** (idempotency).
5. **Slim down the source.** Remove the migrated entity knowledge from the record/fat page and replace it
   with **pointers** `[[entity]]`. The `experiment` record stays **event + outcome + links**, not a treatise —
   the same boundary as [`../log-craft.md`](../log-craft.md) §1 (log↔page), applied to record↔entity. Do not
   duplicate **process artifacts** that live elsewhere (spec/plan/tasks/Constitution Check, risk/decision tables,
   git hashes): **cite them**, do not copy them — the outcome fits in one line. And do not transcribe **code**
   into snippets (this is the primary source of drift): describe and cite the file (see [`../page-craft.md`](../page-craft.md)).
6. **Backlinks + index + log entry.** Link the new pages from the index and from related pages; append ONE log
   entry `distill` (format: playbook §6; how to write it: [`../log-craft.md`](../log-craft.md)).
