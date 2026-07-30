# Changelog

All notable, user-facing changes to Sertor are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and Sertor aims to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Note on distribution.** Sertor is still pre-1.0 and is distributed **interim** by
> installing straight from the source repository (`git+url`) — there is **no PyPI package
> yet**. The version below reflects the capabilities available today on the `master` branch.

## [Unreleased]

_Changes land here before the next version bump._

## [0.4.0] — 2026-07-30

The wiki recording now says **what it covers**, and two guards stop reporting the false. This is also
the first release we shipped after checking, on a throwaway host, that an **upgrade** actually
delivers it — rather than inferring that from the merge.

> **Upgrade.** `sertor upgrade wiki` and `sertor-flow upgrade` refresh the instruction blocks and
> hooks in place; the library changes travel with the `.sertor/` runtime (`uv sync --project .sertor
> --upgrade`). Nothing you configured is touched. **No action is required for existing journals** —
> see the compatibility note below.

### Changed

- **A recording is now honoured for what it COVERS, not for existing.** The wiki freshness gate used
  to clear its pending set as soon as today's journal partition appeared among the uncommitted
  changes. Writing the journal entry therefore *switched the gate off* for everything done
  afterwards — in the exact window in which the session-end check asks. It did not even require an
  entry: an empty file, or a blank line appended, satisfied it.

  Recordings written by `append-log` now carry a `sertor-covers/1` block declaring which work items
  they are about, and the gate compares that set against the work actually present. Identity is
  `(path, content)`, so a file that only differs by line endings is not counted as work.

  **Compatibility is deliberately narrow, and it expires by itself.** An entry written before this
  existed still counts — but only for **today's** partition, only while it has **not been
  delivered**, and the derogation is **declared** in the scan output (`legacy_coverage`) rather than
  applied silently. Read literally, "an entry with no coverage block covers everything" would blind
  the gate forever, because every journal holds pre-existing entries and one would be enough. Once
  that file is committed the anchor moves past it: real duration, one session. **You do not need to
  migrate anything.**

### Fixed

- **The lint no longer declares broken what exists.** `iter_pages` rightly excludes the index and the
  journal partitions — they are not content: no frontmatter, no orphan status — but the lint built
  its set of *linkable targets* from that same list, using "is it a page?" to answer "does it
  exist?". Links to the journal, to `[[log/index]]` and to **`[[index]]`** — the wiki's own index —
  were all reported broken. There is now a separate `iter_linkable_files`; pages register first, so
  on an alias collision the page wins. A genuinely dangling link still breaks, as it should.
- **The `wiki-curator` agent no longer stops on an asset that is present.** Its fail-loud guard was
  correct but fired on an existing file: the playbook was referenced **by name** while the next line
  declared *"you do not have the skill's context"* — a correct coordinate expressed in the wrong
  reader's frame of reference. It is now referenced by **stable path suffix** and located by search,
  with the guard kept and improved (it reports the pattern it looked for). The rule upstream that
  produced the defect — *"payload referenced by name"* — has been corrected too: host-agnostic is not
  the same as resolvable.

### Internal

- **Upgrades are now verified on a host that upgrades.** The end-to-end smoke installed onto a clean
  host, and every installer defect on record needs a **pre-existing older installation** to appear —
  so none of them could be seen, by construction. `scripts/smoke.{ps1,sh}` now accept a starting
  release: they install it on a throwaway host, run `upgrade`, and assert outcomes on the resulting
  **host state** — the pin moved, each hook is wired once and current, host configuration survives,
  the recorded invocation has the current shape, nothing was left stale, the reported version is
  derived from the runtime, and health is green **on an index built by the previous release**.
  Applied to the seven upgrade defects on record it covers six; the seventh is named in the workflow
  and in `docs/install.md` §10.2.1 rather than left implied. Runs automatically on one combination
  before a release; the full perimeter is a separate on-demand workflow and is **not** required to
  publish.

## [0.3.3] — 2026-07-28

A **trust** release for the wiki capability: the structural lint stops crying wolf, and the
instruction blocks now say what to *do* with what a guard reports.

> **Upgrade.** The library fix travels with the `.sertor/` runtime; the instruction blocks are
> refreshed by `sertor upgrade wiki` and `sertor-flow upgrade` (they are replaced in place, not
> duplicated). Nothing you configured is touched.

### Fixed

- **The structural lint no longer reports links that are not broken.** `sertor-wiki-tools lint`
  extracted `[[...]]` targets from the **whole** page, including code. Two normal ways of writing
  Markdown were flagged as broken links:
  - `[[...]]`-shaped syntax **inside a code block or inline code span** — a TOML array-of-tables
    (`[[requirement]]`) in an example, or the wikilink form named literally while explaining it;
  - **aliased wikilinks inside a table** (`[[target\|alias]]`), where the pipe must be escaped or it
    would split the cell.

  On a real wiki this produced **21 false findings**. Because the same extractor feeds `collect`,
  `distill-audit` and `ritual-check`, those false links also polluted the **distill candidates**
  offered at the daily distill floor. A lint that reports the false teaches you to stop reading it —
  that is the defect being fixed here. Nothing was blocked by this: the affected tooling is advisory.

### Added

- **Boy scout rule** in the wiki instruction block — when a guard reports something broken in an area
  you are touching, fix it in the same pass, with three constraints: *first ask whether it is really
  broken* (a guard can be wrong, and then the fix belongs in the guard), *the remedy is per class*
  (the tool finds, you judge), and *never "resolve" by hiding* (excluding an area from a guard and
  leaving it disconnected are two ways of making it unreachable).
- **Where to start a semantic lint** — the same block now says that drift concentrates in the pages
  that **summarise** (index, status/roadmap pages, CHANGELOG, instruction blocks), because a summary
  is a copy whose source keeps moving and nothing compares the two. Detail pages drift far less.
  Checking the summarising surfaces first is the cheapest way to spend a lint pass.
- **Two git rules** in the SDLC block: *facing a conflict, ask what is actually **missing** rather
  than how to resolve it* (content that reached the target by another route produces a conflict with
  nothing to reconcile), and *"modified" has two meanings* — `git status` answers "does this appear
  modified?", `git diff` answers "did the content change?"; they diverge on line endings, so anything
  deciding **whether work happened** must ask the second question.

## [0.3.2] — 2026-07-27

A **repair** release for the wiki capability. If your assistant is held back at the end of a session
by *"the wiki was not updated for this session's work"* and you cannot see what is missing — or you
cannot get past it at all — this is the release you want.

> **Upgrade (name the capabilities explicitly).** The library fix travels with the `.sertor/` runtime,
> which is provisioned by the **rag** capability; the improved messages travel with the **wiki**
> assets. You need both:
>
> ```
> uvx --refresh --from "git+https://github.com/themetriost/Sertor.git@v0.3.2#subdirectory=packages/sertor" sertor upgrade rag wiki
> ```
>
> Then `uv run --project .sertor sertor-rag index .` and restart the MCP server.
>
> **If you pin your runtime, `sertor upgrade` still resets your pin** to the default branch — a
> separate, open defect (unchanged since 0.3.1). Re-apply the pin afterwards, or upgrade by editing
> `.sertor/pyproject.toml` and running `uv sync --project .sertor`.

### Fixed

- **The end-of-session wiki gate could become impossible to satisfy.** It decided whether your work
  was recorded by comparing **file modification times** against the wiki log. Merging a branch and
  pulling rewrites the merged files *and* the log together, so their order became arbitrary: the gate
  could block, and satisfying it meant writing to the wiki again — which produced more work to
  deliver, which reproduced the condition at the next merge. **A session could not close on its own
  last merge**, and the only way out was to leave work uncommitted. One project hit this seven times
  in a single day. The answer is now **derived from your repository history** (the last commit that
  touched the wiki log, plus what is still uncommitted), so it no longer depends on clocks.
- **Files your version control ignores no longer count as unrecorded work.** A scratch file left in
  the working directory could block the end of a session. Ignored files are now never considered —
  not filtered out, simply never collected.
- **A change that only rewrites line endings no longer counts as work.** On hosts where git
  normalises line endings, a file with identical content could be reported as modified and hold the
  session open, with nothing to record.
- **You no longer have to commit to satisfy the gate.** A log entry written **today** counts as soon
  as it is on disk. An uncommitted entry from a *previous* day does not count — and is now **named**,
  so you can see why an apparently updated journal did not close the gate.

### Changed

- **The block now tells you WHICH files are unrecorded**, not just how many, and says when the list
  is truncated. Previously the number was all you got, and reconstructing the list was manual.
- **On a project that is not under version control**, the gate still works from modification times —
  but now **says so**, and gives the reason. On such a host the count can include files a version
  control system would have ignored: a stated limitation rather than a silent difference in
  behaviour.
- `sertor-wiki-tools scan --json` gained additive fields (`pending_paths`, `pending_truncated`,
  `anchor_kind`, `anchor_ref`, `anchor_fallback_reason`, `stale_recording`). The contract identifier
  is unchanged, so existing consumers keep working.
- **New documentation**: a *"the wiki gate blocks the end of the session and I cannot tell why"*
  section in `docs/troubleshooting.md`, and `sertor-wiki-tools` is now covered in `docs/reference.md`
  (it was missing entirely).

## [0.3.1] — 2026-07-26

A **repair** release for one defect in v0.3.0 — and it only ever hit the hosts that follow the
discipline we recommend. **Update if your runtime is pinned** to a tag, a commit or a branch: the
update notice printed at session start has been showing you a command that cannot be run.

> ```
> uvx --refresh --from "git+https://github.com/themetriost/Sertor.git@v0.3.1#subdirectory=packages/sertor" sertor upgrade
> uvx --refresh --from "git+https://github.com/themetriost/Sertor.git@v0.3.1#subdirectory=packages/sertor-flow" sertor-flow upgrade
> ```
>
> Then `uv run --project .sertor sertor-rag index .` and `… sertor-rag doctor`, and restart the MCP
> server. Full install steps for all three components: see the v0.3.0 notes.
>
> **If you pin your runtime, `sertor upgrade` still resets your pin** to the default branch — a
> separate, open defect. Re-apply the pin afterwards, or upgrade by editing `.sertor/pyproject.toml`
> and running `uv sync --project .sertor`.

### Fixed

- **The update notice now prints a command that works on a host that pins its runtime.** The command
  was built by string surgery on the runtime's `pyproject.toml`; on a source pinned to a `tag` that
  produced an unusable string (the rest of the TOML table leaked into the URL). It is now parsed with
  `tomllib`. The defect only ever appeared on hosts pinned to an immutable ref — never here, where the
  runtime tracks the default branch by design — so it was reported from outside.
- **A pinned host is now pointed at the NEW version, and is never silently unpinned.** When the pin
  names the installed version, the suggested command carries the *latest* one in the same style
  (`v0.3.0` / `0.3.0`). When the pin is a commit or a branch — which we cannot map to a new ref — the
  command is emitted without one and **the pin is named**, so the host moves it deliberately instead
  of being upgraded off it. Previously the suggestion carried no ref at all: following it discarded
  the pin.

## [0.3.0] — 2026-07-26

A **governance** release: a new binding principle — and, for the first time, a mechanism that carries
constitutional amendments to projects that already have a constitution of their own.

> **Installing all three components.** Order matters: only `install rag` provisions the `.sertor/`
> runtime, and that runtime provides **both** console scripts (`sertor-rag` *and* `sertor-wiki-tools`).
>
> ```
> uvx --from "git+https://github.com/themetriost/Sertor.git@v0.3.0#subdirectory=packages/sertor" sertor install rag
> uvx --from "git+https://github.com/themetriost/Sertor.git@v0.3.0#subdirectory=packages/sertor" sertor install wiki
> uvx --from "git+https://github.com/themetriost/Sertor.git@v0.3.0#subdirectory=packages/sertor-flow" sertor-flow install
> ```
>
> Then: `sertor configure`, `uv run --project .sertor sertor-rag index .`, `… sertor-rag doctor`.
> Already installed? Use `sertor upgrade` and `sertor-flow upgrade` instead, then re-index and
> **restart the MCP server**. The `#subdirectory=…` fragment is mandatory in every form.

### Added

- **Constitution amendments now reach projects that already have one.** The starter is a seed: once
  you have a real constitution, install and upgrade leave it untouched — which meant a later
  amendment could never reach you, and nothing said so. `sertor-flow` now compares the starter
  version declared inside your file with the one shipped and, when yours is older, **says so** in the
  report, naming both versions and pointing at the new **`Amendments`** section of the starter, which
  lists every release and what it added. Still non-destructive: nothing is written — integrating an
  amendment is your judgment call.
- **Constitution starter 0.4.0 → 0.5.0** — new Principle XIII «Derived State, Not Declared»: when a
  fact lives in more than one place, one must be *derived* from the other; where derivation is
  impossible, a named reconciler must **report** the divergence. Preserving a stale copy can be
  correct; preserving it in silence is not.

## [0.2.1] — 2026-07-25

A **repair** release, built entirely from field reports. Four federation nodes independently
described the same class of defect — *an artifact declares one state, reality is another, and
nothing compares the two* — and two instances of it are fixed here. **Hosts whose searches return
nothing, or whose update notice never stops firing, should update.**

> **How to update** (the form with the subdirectory fragment is required):
>
> ```
> uvx --refresh --from "git+https://github.com/themetriost/Sertor.git@v0.2.1#subdirectory=packages/sertor" sertor upgrade
> ```
>
> Then re-index and verify: `uv run --project .sertor sertor-rag index .` and `… sertor-rag doctor`.
> **Restart your MCP server afterwards** — a re-wired `.mcp.json` only takes effect on restart.

### Fixed

- **The MCP server is registered with `--project`, not `--directory`.** The installer had always
  deposited an entry that *moves the working directory*, so the server resolved its index inside the
  `.sertor/` runtime instead of your project — and answered **nothing** to every query, with no
  error, indistinguishable from a thin corpus. One node ran a blind RAG for about a month. Our own
  documentation had warned against this form in five places while the installer shipped it.
- **A broken `.mcp.json` is now repaired by `sertor upgrade rag`.** The entry used to be skipped
  whenever a server named `sertor-rag` was already registered — identity by *presence* — so the
  mechanism meant to fix your host preserved the broken version instead. Upgrade now reconciles the
  entry **by content**, rewriting only the invocation: your `SERTOR_CORPUS` and any other MCP server
  in the file are preserved. `install` stays non-destructive, but now **reports** a divergent entry
  instead of silently calling it "already present".
- **`doctor` checks how the MCP server is invoked, not just that it is registered.** A
  working-directory-moving registration is reported as `mcp_invocation_moves_cwd`, with the remedy.
  Previously `doctor` said `mcp pass` for exactly the configuration that made every search empty.
- **The update notice no longer cries "behind" at hosts that are already current.** The installed
  version is now **derived from the runtime** (`.sertor/uv.lock`) instead of read from the
  install-time stamp, which records the version of the *installer that ran* — a different fact. A
  host consuming `sertor-core` via `uv` without the installer was told to update at every session,
  forever, by a command it could not even run. The stamp remains as a fallback, and both values are
  reported so a divergence between them stays visible.

## [0.2.0] — 2026-07-24

A **feature + repair** release. The code-graph now reaches the agent inside `search_combined` without
being asked, and — just as important — the **installer actually updates the runtime** and tells you the
truth about what it did. **All hosts are asked to update.**

> **⚠️ How to update (read this).** A previous notice suggested `uvx --refresh sertor`, which **does not
> work**: it resolves the root package, which does not provide the `sertor` command. Use the form with the
> subdirectory fragment:
>
> ```
> uvx --refresh --from "git+https://github.com/themetriost/Sertor.git@v0.2.0#subdirectory=packages/sertor" sertor upgrade
> ```
>
> If your runtime has been stuck at an old commit across earlier "successful" upgrades (see *Fixed*
> below), this release is the one that unsticks it — and the upgrade report now prints the exact
> `sertor-core X.Y.Z (commit)` you end up on, so you can see it moved.

### Added

- **The code-graph enters `search_combined`.** Alongside the `docs` and `code` similarity flows, the
  combined search now returns a third labelled `graph` flow — definitions, callers, callees and linked
  docs, grouped per symbol — **without the agent having to call a graph tool**. Entry points are derived
  from the query **deterministically** (identifiers written in the query · lexical match against the
  symbol table), and a query that names no symbol never touches the graph, so the cost is proportional to
  relevance. Absence is **typed**: "not attempted" vs "empty" vs "unavailable" (with three distinct
  causes), so the agent never mistakes "the tool is unavailable" for "there are no callers". Toggle:
  `SERTOR_COMBINED_GRAPH` (**on by default**). (E5-FEAT-012)

### Changed

- **`search_combined` returns a third key, `graph`, by default.** A consumer that read only `docs`/`code`
  is unaffected (the two keys are unchanged); one that treats extra keys as an error should set
  `SERTOR_COMBINED_GRAPH=false` or handle the new key.
- **The search tools now declare the meaning of their `score`** in their description, worded for the
  active engine: under the default rank-fusion engine the score adds little beyond the list order, and it
  is never comparable across flows or across queries.

### Fixed

- **`upgrade` now moves the runtime pin.** On an already-installed host, `sertor upgrade` re-ran its
  dependency step, reported success, and left `sertor-core` at the commit it was first installed at —
  because the dependency it writes is unconstrained against a ref-less git source, which any existing lock
  already satisfies. It now forces the re-resolution, so "updated" means the runtime actually moved.
  Confirmed in the field by hosts stuck for a month across three "successful" upgrades. (E2)
- **The upgrade report tells you what you ended up on.** It now prints `sertor-core X.Y.Z (commit)` read
  from the runtime lock — or says plainly "unchanged, already current" / "version unknown" — instead of
  implying movement that may not have happened. (E2)
- **The update notice now prints a command that works.** It is derived from your own runtime's repository
  URL and includes the `#subdirectory=packages/sertor` fragment. (E2, reported by a federation node)
- **Observability wiring is idempotent by target, not by presence.** Re-wiring to a different store now
  re-points the handler instead of silently leaving events flowing to the previous one. (internal)

### Known limitations

- **`upgrade --dry-run` still does not project the dependency or settings/config steps** — it reports them
  as unchanged even when the real upgrade would change them. Trust the real `upgrade` output. (E10-FEAT-042)
- **The runtime dependency is still ref-less** (tracks the default branch, not a tag). This release
  unsticks it, but pinning the runtime to a tag for reproducibility is a separate, later decision.

## [0.1.5] — 2026-07-23

A **fix release** completing v0.1.4's wiki-guard: an `upgrade` now cleanly hands the `Stop` slot from the
old nudge to the guard, instead of leaving both wired. **Recommended for any host that upgrades the wiki
capability.** No breaking changes; lands on top of `0.1.4`.

### Fixed

- **`upgrade` no longer double-wires the `Stop` hook.** v0.1.4 shipped `wiki-guard` at `Stop` but, on an
  already-installed host, `sertor upgrade wiki` added it WITHOUT removing the superseded
  `wiki-pending-check` `Stop` entry (a different script stem) — so both fired at stop. The upgrade now
  strips that superseded Stop entry before the additive merge (its `SessionEnd` wiring is kept), leaving an
  upgrading host single-wired. Fresh installs were never affected. (E10-FEAT-041)

### Known limitations

- **`upgrade --dry-run` does not yet project settings/config merges** — it reports them as unchanged even
  when the real upgrade would change them (e.g. re-wiring a hook). Trust the real `upgrade` output, not the
  `--dry-run`, for settings changes until a follow-up lands. (E10-FEAT-042, surfaced by dogfooding v0.1.4.)

## [0.1.4] — 2026-07-23

A **wiki-governance release** that completes the pair started in `0.1.3`: where the daily distill floor
gates the *merge*, this release gates the *end of every turn*. **All hosts are asked to update to this
version** — the wiki-freshness net only takes effect once the wiki capability is installed/upgraded. No
breaking changes to your code; the enforcement arrives with `sertor install/upgrade wiki`. Lands on top
of `0.1.3`.

### Added

- **Wiki freshness guard — stopping is gated on a recorded wiki.** A new host-facing hook (`wiki-guard`,
  `Stop`/`agentStop`) BLOCKS the end of a turn when the session changed indexed files
  (`src`/`specs`/`requirements`/`.claude`) that are **not yet recorded in the wiki**, telling the agent to
  close the step ritual first — record the work, distill durable entities, and run the semantic lint —
  then stop again. It reuses `sertor-wiki-tools scan` for detection (no reinvention), never traps a turn
  (anti-loop via `stop_hook_active`; fails open with no wiki config or an unreachable scan; read-only /
  question sessions close normally), and ships with full **Claude / Copilot parity** (`Stop` /
  `agentStop`, both `{"decision":"block","reason":…}`). It is the stop-time sibling of the merge-time
  distill floor, and replaces the non-blocking `Stop` nudge of `wiki-pending-check` (which stays on
  `SessionEnd`). Distributed via `sertor install/upgrade wiki` (E10-FEAT-040).

### Known limitations

- On an **already-installed** host, `upgrade` does not yet remove the superseded non-blocking `Stop`
  entry of `wiki-pending-check`, so both the guard and the old nudge may fire at stop until a follow-up
  (E10-FEAT-041) lands. **Fresh installs are unaffected.**

## [0.1.3] — 2026-07-22

A **wiki-governance release**: the `distill` step of the wiki ritual — turning the day's scattered
knowledge into durable pages instead of leaving it buried in the dated log — now has a **hard floor**.
No breaking changes to your code; the new enforcement arrives only when you install/upgrade the wiki
capability. Everything here lands on top of `0.1.2`.

### Added

- **Daily distill floor — the merge is gated on a distill.** A new host-facing hook (`distill-floor`,
  `PreToolUse`) BLOCKS a delivery merge (`git merge <branch>` / `gh pr merge`) when today's wiki log
  has no `distill` entry: a day that logged work must also log a distillation — a real one, or a
  reasoned "no" that names the candidates considered — before it can ship. The gate reads today's dated
  log partition from `wiki.config.toml` (host-agnostic), never deadlocks (distilling needs no merge),
  leaves mainline-update merges (`git merge master`) untouched, and fails open when the floor cannot be
  determined (no config / single-file log). Distributed with Claude/Copilot parity via
  `sertor install/upgrade wiki` (E10-FEAT-039).
- **`distill-audit` — find undistilled entities across the whole wiki.** A new deterministic
  `sertor-wiki-tools distill-audit` (contract `wiki.distill_audit/1`, zero-LLM, read-only) scans the
  whole corpus for entities referenced from many points that still have no page (dangling wikilinks +
  compound backtick identifiers), with a debt count. It is an **advisory hint** attached to the floor's
  block message — the tool finds, the agent judges — never itself a gate.

## [0.1.2] — 2026-07-21

A **conversation-memory release**: the agent can now reach its session memory through the native MCP
surface — both full-text and by-meaning — and the automatic end-of-session capture that had quietly
stopped working is fixed. Conversation memory stays **off by default** (opt-in). No breaking changes;
update is a drop-in refresh. Everything here lands on top of `0.1.1`.

### Added

- **Read your conversation memory from the MCP server.** The `sertor-rag` MCP server now exposes three
  read-only memory tools — `memory_search` (full-text over past turns — "have we talked about X?"),
  `memory_list` (recent archived sessions) and `memory_show` (one session's turns) — so an agent can
  recall past work over its native MCP surface instead of shelling out to the CLI. Same data as the
  `sertor-rag memory` CLI commands, same opt-in gate (`SERTOR_MEMORY`, off by default); when memory is
  off each returns an explicit `disabled` state, never a misleading empty result (E4-FEAT-010).
- **Semantic conversation-memory search from the MCP server.** The `memory_search` MCP tool now takes
  `semantic=true` to search past sessions **by meaning** rather than by keyword — the MCP mirror of
  `sertor-rag memory search --semantic`, so an agent can do semantic recall over the native MCP surface
  instead of shelling out to the CLI. It stays behind the same two opt-ins (`SERTOR_MEMORY` +
  `SERTOR_MEMORY_SEMANTIC`); with the semantic layer off it returns an explicit `disabled` state naming
  that knob, never a silent fall back to full-text (E4-FEAT-013).

### Fixed

- **Memory search no longer chokes on punctuation.** A query containing a version number (`0.1.1`),
  a path (`a/b.py`), a `tipo:esito`-style tag or a hyphenated word used to hit FTS5's query syntax
  and fail — and the failure was **masked as "no results"**, so you'd conclude "we never discussed
  this" when the search had not even run. The free-text query is now sanitized (each token matched
  as a literal) before it reaches FTS5, so ordinary input just works; this covers both the CLI
  `memory search` and the `memory_search` MCP tool. *(Reported by the Acta node, verified against the
  code and the live archive.)*
- **Automatic conversation-memory capture actually runs.** The end-of-session capture hook checked
  its privacy gate against the process environment, but the `SERTOR_MEMORY` switch lives in
  `.sertor/.env` (read by the CLI, not exported into the hook) — so on every host that enables
  memory via the file, auto-capture silently never fired. The hook now reads the switch from the
  same `.env` the CLI does, so enabling memory in `.sertor/.env` is enough for sessions to be
  captured at session end (manual `sertor-rag memory archive` was, and remains, unaffected). Memory
  stays **off by default**; nothing is captured unless you opt in (E4-FEAT-012).

## [0.1.1] — 2026-07-20

A **reliability release**: correctness fixes across the parts of Sertor a host actually touches —
the installed **hooks**, the **`doctor`** health check, the **freshness** loop, conversation
**memory** capture, and the **installer** report. No breaking changes; update is a drop-in refresh
(see the "How to update" note in the release announcement). Everything here lands on top of `0.1.0`.

### Fixed

- **Trustworthy index-freshness alarm.** The end-of-session freshness hook now **re-indexes first,
  then measures health**, and records that post-repair verdict — so the routine case (a stale index
  the re-index fixes) no longer raises a spurious `degraded` alarm at the next session start. The
  alarm now appears only when a problem **survives** the repair, and lists **every** degraded area
  instead of just the first (E10-FEAT-034).
- **Self-healing index lock.** If the background re-index worker is ever killed mid-run, the index
  lock it leaves behind no longer blocks every future `sertor-rag index` — the next run detects the
  dead owner and reclaims the stale lock automatically (a live indexing run is still respected), with
  no manual clean-up (E10-FEAT-035).
- **`doctor` verdict no longer depends on your working directory.** `sertor-rag doctor` could report
  `index: pass` from the project root and `index: warn` from a subfolder (same index). It now anchors
  to the project root, so the health verdict is the same from anywhere (E10-FEAT-038).
- **Installed hooks work from any working directory.** Hooks were wired with a path relative to the
  script, so if the agent changed directory they failed before running — on `PreToolUse` this could
  block `Bash`/`Write`/`Edit`. They are now anchored to the project root (E10-FEAT-031).
- **Hook updates actually reach hosts that upgrade.** A changed hook could be duplicated (leaving the
  old, broken copy active) or silently dropped on `upgrade`. A hook's identity is now the script
  itself, so `sertor upgrade` delivers hook changes cleanly — no duplicates, no stale copies
  (E10-FEAT-032).
- **`ritual-check` works on `main`-default repositories.** It assumed the default branch was `master`
  and errored on hosts whose default is `main`; it now detects the default branch at runtime
  (E10-FEAT-033).
- **Conversation-memory capture on paths containing spaces.** The session-path encoding didn't match
  the assistant's, so on a project path with spaces **no** sessions were archived — silently. Fixed,
  and it now warns out loud when the capture source is absent instead of failing quietly
  (E4-FEAT-011).

### Changed

- **The installer reports the ACTION, not just the precondition.** The report said `skipped` both
  when an artifact was already identical and when it was present-but-**different**. A new
  `present-divergent` outcome now names the divergence (and leaves your file untouched), dependency
  steps report honestly, and `sertor install rag` writes an inspectable `.sertor/.install-log.jsonl`
  (E2-FEAT-018).

## [0.1.0] — 2026-07-13

The **first public release** of Sertor: an installable, portable, local-first framework that gives any
project a queryable knowledge of itself, fusing **code and documentation** into a single corpus.
Published as a **GitHub release** (tag `v0.1.0`) on the now-public repository; installable today via
`git+url` (pin `@v0.1.0` for this exact version). A **PyPI package** (`pip install sertor`) is coming
next. Everything below is available in this release.

### Indexing

- **Repo-agnostic indexing** of any project — *code+doc*, *doc-only*, or *code-only*. Chunking
  is **code-aware** (multi-language) and **markdown-aware**, so sources and documentation are
  indexed the way they are meant to be read.
- **Multi-provider embeddings**, selectable via `SERTOR_EMBED_PROVIDER`:
  - `glove` — the **default**: zero-config, fully **offline**, no account or key required.
  - `hash` — a dependency-free fallback.
  - `ollama` — local models via a running Ollama service.
  - `azure` — Azure OpenAI embeddings.
- **Incremental index refresh** — re-indexing after edits updates only what changed instead of
  rebuilding from scratch.

### Retrieval (RAG)

- **Hybrid engine (default)** — combines lexical **BM25** and **vector** search with reciprocal
  rank fusion (RRF), with **optional reranking** for higher precision.
- **Vector baseline** — a simpler pure-vector engine.
- **Structural code graph** — navigate the code by relationship: find a symbol, see who calls it,
  and pull the docs related to it.
- **Agentic retrieval** — iterative, multi-step retrieval driven by a frontier agent through the
  MCP server.
- **`search_combined`** returns the two flows together — *the code says what it does, the docs say
  why* — for a single question.
- **Production hardening** — a content-hash **embeddings cache** (avoid recomputing), automatic
  **retry/backoff** on transient failures, and an optional **confidence threshold** to suppress
  weak matches.

### MCP server (`sertor-rag`)

- Search tools `search_code`, `search_docs`, `search_combined` plus **four graph tools**
  (`find_symbol`, `who_calls`, `related_docs`, `get_context`).
- Works with **Claude Code** and **GitHub Copilot CLI**.

### `sertor-rag` CLI

- `index`, `search`, `doctor` (health check), and `eval` (retrieval quality: hit@k / MRR).
- **Runtime observability** built in, plus an `observe` **TUI panel** to watch activity live.

### LLM Wiki (`sertor install wiki`)

- A **cumulative project knowledge base**, written and maintained *during the work* — a persistent
  artifact that grows each session instead of being rebuilt from scratch, and itself queryable via
  RAG.

### Installers & lifecycle

- **`sertor install rag`** and **`sertor install wiki`** — install into an **isolated `.sertor/`
  runtime**; **non-destructive**, **idempotent**, and **`install ≠ run`** (installing never runs
  your project).
- **Lifecycle** commands — `upgrade` and `uninstall`.
- **`configure`** — a wizard to set up providers and options.
- **`doctor`** — a health check that fails loud when something is misconfigured.
- **Guided setup** — an assisted path from an unconfigured repo to a verified, working RAG.

### `sertor-flow`

- The **SDLC / SpecKit development method** — spec-driven flow, requirements management, and a
  neutral constitution starter — packaged as a **separate, standalone installer**, independent of
  the RAG capability.

### Conversation memory (opt-in)

- **Privacy-by-default**, off unless you enable it: local capture of past sessions with **full-text**
  search and **optional semantic** search over what you worked on before. Content stays on your
  machine.

### Observability (opt-in)

- A **local event store**, human-readable **reports**, and **OpenTelemetry (OTel) export** for
  integration with your own tooling.

### Compatibility & automation

- **Multi-assistant** — supported on **Claude Code** and **GitHub Copilot CLI**.
- **Auto-update notice** — tells you when a newer Sertor is available.
- **RAG freshness hooks** — keep the index up to date automatically as your project changes.
