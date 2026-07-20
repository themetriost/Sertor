# Changelog

All notable, user-facing changes to Sertor are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and Sertor aims to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Note on distribution.** Sertor is still pre-1.0 and is distributed **interim** by
> installing straight from the source repository (`git+url`) — there is **no PyPI package
> yet**. The version below reflects the capabilities available today on the `master` branch.

## [Unreleased]

_Changes land here before the next version bump._

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
