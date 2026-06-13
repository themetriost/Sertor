# Operation `ingest` — acquire an external source

> **Operation module.** Executor: **curator OK** (Haiku in background) or main flow.
> For the **shared substrate** (D↔N boundary §2, taxonomy §3, log entry §6) see the playbook
> `wiki-playbook.md`; for **how to write a page** [`../page-craft.md`](../page-craft.md), for **whether
> something deserves a page** (and which archetype) [`../wiki-craft.md`](../wiki-craft.md). Only the specific procedure is described here.

Input: a local path (file/PDF) or a URL.

1. Acquire the source: `Read` for local files/PDFs; `WebFetch` for remote URLs/PDFs. **Do not modify** the
   original source.
2. Write a summary in `sources/<slug>.md` with frontmatter (`sources:` = origin path/URL). Write it
   following [`../page-craft.md`](../page-craft.md) — in particular the **level of meaning**:
   distill the reusable theses/results from the source, do not paraphrase it linearly; capture *what it adds or
   contradicts* relative to what you already know.
3. Integrate/link the related concepts into the `concepts/`/`tech/` pages; **flag contradictions** with
   existing pages (judgment).
4. Update the index and append a log entry `ingest`.
