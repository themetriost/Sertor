# How to write a well-crafted log entry — anatomy of log-craft

> **Reference page (leaf).** Describes *what a good log entry looks like* — what belongs in it, what does not,
> how much, how. It is **linked from** whoever appends an entry: the playbook §6 (the *convention*: heading
> grammar + operation vocabulary) and every operation that closes with a log entry
> (`ops/record.md`, `ops/ingest.md`, `ops/lint.md`, `ops/reorg.md`, …). It is a **leaf**: it does not depend on
> other documents in the system — the operations reference it, not the other way around. It is the **twin** of
> [`page-craft.md`](page-craft.md): if that one says how to write a *page* (evergreen), this one says how to
> write a *log entry* (dated).
>
> **Host-agnostic (Principle X).** The principles apply on any host; what *varies* — the operation
> vocabulary, link syntax, the heading format — comes from the profile (`wiki.config.toml`) and
> from the playbook §6. The concrete examples (`[[wikilink]]`, `record`, `lint A`) are **illustrative**.

The log is the wiki's **append-only** artifact: it is never rewritten. With rotation it is **one file per day**
(`log/YYYY-MM-DD.md`); the entry is written by `append-log` — you compose the **curated body**, the deterministic core
**places it** in today's file. It is a *dated
diary*, not a page. A well-crafted entry has three qualities: it stands on the **right side of the
log↔page boundary**, has a predictable **anatomy**, and is **dense** (no drift toward dumps).

## 1. What an entry is — and what it is NOT (the log↔page boundary)

It is the **dual** of [`page-craft.md`](page-craft.md) §3. The page captures **distilled, reusable knowledge**
(*what remains*, evergreen); the log entry records the **dated event** (*what happened*, and where what remains now lives).

| Goes in the **log** (dated entry) | Goes in the **page** (evergreen) |
|---|---|
| *what* was done in this step and *when* | the *concept* / the method / the reusable rationale |
| the decision made + a **pointer** to the *why* | the extended *why*, the rejected alternatives |
| **where** the result lives (`[[page]]`, file, commit) | the actual content |
| the **outcome/verification** (tests, lint, hash) | anchored, timeless claim |

- **The entry points, it does not re-dump.** If a step created/updated a page, the entry says *which* page
  and *in one line* the gist, then links — **not** a copy of the page's content. Duplicated content
  ages in two places (the log is never updated: it is append-only → the copy immediately becomes stale).
- **The entry is a trace, not a backup.** It is not meant to reconstruct *everything* about the step: it is meant to tell,
  cold, *what* happened, *where* to look and *how it went*. Git already tracks the files and diffs: the entry is not
  the list of touched files.

## 2. Anatomy of an entry

```
## [YYYY-MM-DD] <operation> | <title>

<lead: 1–2 sentences — the why/context/trigger of the step>
- **<label>:** <salient fact, one line>
- **Verification:** <anchored outcome: lint A 0/0/0/0 · green tests · commit hash>
```

1. **Heading** — `## [date] <op> | <title>`. `<op>` from the **playbook §6 vocabulary**
   (`setup·record·distill·ingest·query·lint·reorg·generate·rag-sync`); `<title>` describes **one** thing,
   like the title of a page (no "misc", no two steps in one title).
2. **Lead (1–2 sentences)** — opens with the **why/context/trigger**, not with the first touched file. This is what is
   read at a glance when scrolling through the log. («Fixed a smell flagged by the owner: …», not
   «Page created: …»).
3. **Flat bullets with bold label** — `**What** · **Why** · **File** · **Verification** ·
   **Origin**`. Stable labels make the log scannable. **Maximum one level of nesting**: if you
   need a fourth level of indentation, you are putting *content* in the log (→ page) or doing a file dump
   (→ remove it).
4. **Outcome line** when applicable — the log is also proof that the step is *closed*: `lint A 0/0/0/0`,
   `6 green tests`, `commit c6930e9`. One line, anchored.

## 3. Granularity — when an entry, how many entries

- **One entry per operation.** The heading carries *one* `<op>`: if a step did things of different natures
  (a `record` **and** a `lint`), those are **two entries** with their own `<op>`. Operations of the **same** nature
  in the same step are **combined** into one entry.
- **The entry follows the significant step,** not the individual Edit. Five changes that implement *one*
  decision = *one* entry.
- **Anti-trivial rule (when NOT to log).** Purely mechanical or minor changes do not deserve
  an entry (it is the same *golden rule* as the wiki). Typical cases: `structure` that created nothing
  (everything `skipped_existing` → no entry, it is idempotent); typo refactoring; rename with no
  consequences. If the entry would only say «fixed typo», do not write it.

## 4. Density — anti-drift (the historical defect of the log)

The log degenerates when entries become **mini-pages**: deep nesting, content copied from
pages, exhaustive lists. Countermeasures:

- **Soft cap.** An entry normally fits in **~6–10 one-level bullets**. If it grows, it is usually because you are
  putting *content* in it (→ page) or *files* (→ git): remove, do not compress.
- **No exhaustive file lists.** Cite 1–2 **key** files inline; the complete list comes from `git` (delegated
  to the VCS role). A «Files touched» sub-list with all paths is noise.
- **No adjective-laden "Benefits".** Summary phrases like «more maintainable, cleaner, ready to scale»
  carry no information: cut them. If a benefit is real and reusable, it is a **page** claim.
- **No duplication of page content.** The gist in one line + `[[page]]`; the rest lives
  in the page (see §1).

## 5. Example — the same activity, written poorly → well

✗ **Drift** (mini-page in the log):
```
## [date] record | Wiki system consolidation
- **Page created:** syntheses/wiki-system-single-source.md documents:
  - Vision: wiki is Karpathy LLM Wiki; rules were duplicated → single source…
  - Single source: new file playbook.md (identity + taxonomy + 6 operations: record, ingest…)
    1. Skill: hyperlink to playbook…
    2. Command: brief + parameters…
- **Files touched:** New: …; Updated: SKILL.md, wiki.md, agent, settings.json, the host instruction file
- **Benefits:** Rules consolidated, unique taxonomy, less duplication, centralized maintenance. Ready to scale.
```
*— 4 levels of nesting, copies the page content, file dump (git tracks them), adjective-laden "Benefits".
The log does the page's job.*

✓ **Good** (trace + pointers + outcome):
```
## [date] record | Wiki system consolidation (single source + three interfaces)
Wiki rules were duplicated across skill/command/agent → consolidated into a single source with thin interfaces.
- **What:** new playbook as single source; skill/command/agent become wrappers that read it.
- **Where:** rationale and architecture in [[wiki-system-single-source]].
- **Key file:** `wiki-playbook.md` (new).
- **Verification:** lint A 0/0/0/0.
```
*— lead with the why, flat bullets, points to the page for content, closes with the outcome.*

## Quick checklist

| Criterion | Question to ask yourself |
|---|---|
| Boundary | Am I recording *what happened* (log) and not *the knowledge* (→ page)? |
| Heading | `<op>` from the §6 vocabulary, title on **one** thing? |
| Lead | Opens with the **why/trigger**, not the first file? |
| Bullets | Flat, labeled, **max 1 level**? |
| Pointers | Is the content **linked** to the page, not copied? |
| Noise | No exhaustive file list (git) and no adjective-laden "Benefits"? |
| Outcome | Is there a verification line (lint/tests/commit) if applicable? |
| Anti-trivial | Is it worth it? (mechanical/trivial → no entry) |
