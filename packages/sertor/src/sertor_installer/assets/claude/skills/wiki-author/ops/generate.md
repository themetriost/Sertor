# Operation `generate` — generate the wiki from the repo (from-scratch) or update it from changes (from-diff)

> **Operation module.** Executor: **main flow only** — the page plan and content
> are judgment. For the **shared substrate** (D↔N boundary §2, taxonomy §3, conventions §4, log entry
> §6) see the playbook `wiki-playbook.md`; for **whether/what deserves a page**
> [`../wiki-craft.md`](../wiki-craft.md) (link/name test §1, archetypes and product lens §2, structure
> pages §3), for **how to write it** [`../page-craft.md`](../page-craft.md). Only the procedure is described here.

Generation is **one capability, two inputs** (natural-language content to linked concepts,
*incrementally updatable*). **Selector:** if the host **does not have** `wiki.config.toml`, or the
wiki root does not exist/is empty → **from-scratch** (bootstrap); otherwise → **from-diff** (the default of
the `generate` operation).

## Reconnaissance depth (parameter, default `light`)

How deeply to read the sources is an explicit choice, not an implicit judgment: depth is
stated at invocation (e.g. `generate medium`) and must be **recorded in the log entry** — so the wiki
knows at what depth it was born and a future lint B can distinguish "lean page by choice" from drift. These are
**named reading presets** ("calibrate to value" made into a parameter): the boundaries remain judgment on
the concrete case, not rigid rules.

| Level | What it reads (step 2) | Page plan (step 3) | When |
|---|---|---|---|
| **light** (default) | README + repo structure (map, not mirror) | 6–12 correct but lean pages | standard bootstrap |
| **medium** | + primary documentation sources **in full** (methodology, reference, dedicated doc) | 10–18 pages, thickened | host with rich doc to truly distill |
| **massive** | + code (entry points, public contracts, tests) across all `source_dirs`, in multiple passes | in passes, no hard cap | host with sparse doc: the wiki *is* the documentation |

Levels **compose with the cumulative model**, they do not replace it: a `medium` run on a wiki born at
`light` is the standard way to thicken it (enrichment flows through the applicable input — from-scratch
if restarting, from-diff/`distill` if integrating). *(Future surface: a `--depth` option for an
install command.)*

## Input A — from-scratch (bootstrap on a repo without a wiki)

All CLI calls use `--config <host config>`: paths resolve relative to the config file's folder, so the
operation works on a host different from the cwd. **Every write (pages, log, index) happens in the host's
wiki** — never in the executor's wiki.

0. **Host config (judgment — prerequisite).** If `wiki.config.toml` is missing (searched in root and in `wiki/`) on the host,
   **author a minimal one** by inspecting the repo, without assumptions: `language` (the language of the host's doc —
   the wiki is written in that language; ask if ambiguous), `root`/`index_file`/`log_file`/`log_dir`,
   `[[taxonomy]]` (the 5 areas of the standard profile as a base, adapted to the host's nature),
   `source_dirs` (doc, code, tests, specs **if they exist**: verify this), `exclude` (VCS, build,
   dependencies, media), `[rag] enabled=false` if the host has no RAG infrastructure, `[roles]` only if
   the host has agents. *This step is the judgment placeholder for the bootstrap of the config: when an
   install command generates it, the mechanical part becomes its responsibility.*
1. **Structure (D).** `uv run --directory .sertor sertor-wiki-tools structure init --config <config> --json`
   — idempotent: creates taxonomy folders + index + log, overwrites nothing.
2. **Source reconnaissance (D+N).** `collect --json` for the inventory (at bootstrap it is empty; on the
   second run it is the anti-duplication check). Reading order for input sources: **README** → **dedicated doc** →
   **specs/requirements** if they exist → **code structure** (tree, entry points, public contracts —
   *optional* input: skipped on a doc-only host) → **tests** (the
   behavior). **Breadth is decided by the declared depth** (table above); at every level:
   the **map** is what matters, not the mirror — read to understand, not to copy.
3. **Bounded page plan (N — the distinctive step).** Enumerate candidates with the link/name test
   (wiki-craft §1) and the product lens (§2 if the host is code); apply **anti-fragmentation**
   (few living pages). **Propose the plan before writing** — list `page → area → purpose in one line` —
   and submit it to the user if the flow is interactive. **Size according to depth**
   (table above; for `light`: 6–12 pages — below that the domain core is missing, above is fragmentation:
   the wiki is cumulative, the rest comes with subsequent runs). Include the required structure pages (the home coincides with the `index_file`;
   an overview only if the domain requires it — wiki-craft §3).
4. **Writing (N).** Pages compliant with page-craft: definition at the top, the *why*, relationships with
   neighbors, claims anchored to sources — **link the source, do not copy it** (neither doc nor code in snippets).
   Weave the `[[wikilink]]` network; an index line per page (`upsert-index`, or curated by hand if the
   host's index is curated — judgment).
5. **Log (D).** **ONE** log entry `generate` via `append-log --config <config>` — in the **host's
   wiki** — with lead "from-scratch bootstrap" and the essentials (**depth used**, page count, sources
   read). The first entry also serves as a temporal anchor for future from-diff/`scan` runs. This input **does not require git**.
6. **Verification (D).** `lint --json` + `validate --json` on the host: zero broken links, zero orphans,
   complete frontmatter. **Idempotency:** a second invocation on an already accurate wiki rewrites
   nothing — `structure init` reports everything as `skipped_existing`, `collect` shows existing pages, and
   without a delta there is no second pass and no new log entry (anti-trivial rule, playbook §6).

## Input B — from-diff (update from recent changes)

Avoids re-reading the entire repo: updates only what changed. Trigger = manually invoking the wiki
capability; scope = changeset of the last commit. Lint/freshness here are **non-blocking**.

1. Anchor the starting point with `uv run --directory .sertor sertor-wiki-tools scan --json` (pending files via mtime) and/or
   **delegate to the VCS role** (`[roles].vcs`) a read-only brief "`git log` + `git diff` from point X".
   X = date of the last log entry (or the last commit that touches the wiki). *(Git operations are
   delegated; if the host has no VCS role configured, ask the user how to obtain the diff.)*
2. With the received diff, update **only** the impacted pages (judgment).
3. Update the index and append a log entry `generate` citing the commit range.
