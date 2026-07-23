<!--
SYNC IMPACT REPORT — Sertor Constitution
========================================
Version: 1.4.0 → 1.5.0
Bump type: MINOR (new Principle XIII «Product Plane vs. Fixture Plane») + full English convergence

Changes in this amendment (2026-07-22):
  + Principle XIII — Product Plane vs. Fixture Plane (NON-NEGOTIABLE): in dogfooding (a product exercised
    against fixtures inside its own repo), the two planes — product vs fixture — stay distinct;
    product/behavior decisions are justified ONLY by the real-user case, never by fixture convenience; a
    repo-hygiene decision about dogfood byproducts never silently becomes product behavior. Heart clause: a
    fixture-plane workaround that papers over a product-plane gap is recorded as an OPEN PRODUCT QUESTION,
    never hidden (it is Principle XII «Fail Loud» applied to dogfooding). Ceremony scales with how much the
    product mutates the asset in place.
  ~ LANGUAGE CONVERGENCE (dogfood fidelity): the whole dogfood constitution is now in ENGLISH — the same
    language we RELEASE (the neutral starter shipped by `sertor-flow`). It was Italian: a divergence from
    what we ship, i.e. Principle XIII applied to ourselves (the dogfood must not differ from what we
    release). Meaning is unchanged; numbering (I–XIII) is preserved to keep the many «Principle X/XI/XII»
    cross-references (CLAUDE.md, wiki, templates, tests) intact. Sertor-specific personalization (RAG
    flavor, the extra principles X host-agnostic / XI vehicles, the mission section, requirement citations)
    is legitimate and kept.
  Dependent templates: plan-template.md — added the «XIII — Product Plane vs. Fixture Plane» gate.
  Distribution: also into the neutral starter of `sertor-flow` (as Principle XII — there XI = Fail Loud —
    starter bump 0.3.0 → 0.4.0), propagated to nodes by construction.
  Origin: proposal by the Sinthari node (2026-07-12, already adopted in-house at v0.4.0), accepted
    2026-07-14; E10-FEAT-030.

----- History (pre-convergence entries, kept as record) -----
v1.3.0 → v1.4.0 (2026-06-20, MINOR): + «Mission & North Star» section (Sertor's differentiator = code+doc
  fusion in one jointly-queryable corpus; binding north star: every capability/feature/decision MUST serve
  the mission and strengthen the code+doc fusion; on conflict the mission wins or is reconsidered
  explicitly) + a mission-alignment gate in the Constitution Check. Dependent: plan-template.md.
v1.2.0 → v1.3.0 (2026-06-20, MINOR): + Principle XII — Fail Loud, Fix the Cause (signal and remove the
  cause, do not suppress). Origin: the OTel episode (fix the collector, do not switch off the export).
v1.1.1 → v1.2.0 (2026-06-15, MINOR): + Principle XI — Consume through the vehicles (CLI/MCP), not the
  library at runtime (tests excepted). Origin: an observability gap (a re-index via `build_indexer().index()`
  was not traced in telemetry).
v1.1.0 → v1.1.1 (2026-06-14, PATCH): ~ Principle VII — clarified function style (small, low nesting; guard
  clauses / early returns over deep nesting; dogmatic single-exit / SESE is NOT required).
v1.0.0 → v1.1.0 (2026-06-05, MINOR): + Principle X — Host-agnostic capabilities (portability is a
  constraint, not an aspiration); intro scope widened from «core + CLI» to «all capabilities + vehicles».

Principles (13):
  I.    Core with dependencies pointing inward (the library is the product)
  II.   Interchangeable providers and backends behind boundaries; local-first
  III.  Justified simplicity (YAGNI) and small units
  IV.   Explicit error handling; no silent null
  V.    Testability and quality proven by measures
  VI.   Idempotence, determinism and non-destructiveness
  VII.  Readability as communication; leave the code cleaner
  VIII. Centralized configuration of the core
  IX.   Observability: every runtime operation is logged
  X.    Host-agnostic capabilities
  XI.   Consume through the vehicles (CLI/MCP), not the library at runtime
  XII.  Fail Loud, Fix the Cause — signal and remove the cause, do not suppress
  XIII. Product Plane vs. Fixture Plane — in dogfooding, product/fixture planes stay distinct; a
        product-plane gap papered over by a fixture-plane workaround = OPEN PRODUCT QUESTION, never hidden

Sections (1):
  «Mission & North Star» — binding orienting frame (added in v1.4.0)

Dependent templates:
  OK .specify/templates/plan-template.md  — gates for XI/XII/XIII + mission alignment; version ref → v1.5.0
  OK .specify/templates/spec-template.md  — no change needed
  OK .specify/templates/tasks-template.md — no change needed

Related artifacts:
  OK README.md (root) — Vision/Mission: source of Principle X and the «Mission & North Star» section
Traceability: each principle cites the Sertor requirements/criteria it encodes (REQ-E*, CS, OBJ, SC, REQ-*).
Inspiration: the «Clean Code» and «Clean Architecture» wikis (Transcriptio).
-->


# Sertor Constitution

Binding principles for building Sertor's **capabilities** (RAG engines, indexing, LLM-Wiki skills) and their
vehicles (**CLI**, **MCP**). Sertor is a framework **installable on any** host project: the principles hold
for every capability, not only the core (see Principle X). The keywords **MUST / SHOULD / MUST NOT** are used
in the RFC-2119 sense.

## Mission & North Star

Sertor is an **installable framework** that gives **any project** — *code+doc*, *doc-only*, *code-only* —
**queryable self-knowledge**, **portable and lock-in-free** (source of truth: [`README.md`](../../README.md);
synthesis: [[mission-vision]]). The **differentiator** is the **fusion of code and documents** (requirements,
specs, wiki) into **one jointly-queryable corpus**: the code says *what it does*, the documentation says
*why* — and the value is returning them **fused** to the agent. Generating and serving are **delegated by
design** (to the frontier agent and to MCP): the competitive front is NOT generate/serve, but the **quality
of what is returned to the agent** — precision/recall, confidence signal, freshness.

**North Star (binding):** every capability, feature and design decision MUST **serve this mission** and,
where it touches retrieval, **strengthen the code+doc fusion** rather than drift onto peripheral concerns.
This frame is the *end* the principles below serve; on conflict between a design and the mission, the mission
wins (or the mission is first reconsidered explicitly).

## Core Principles

### I. Core with dependencies pointing inward (the library is the product)

The Sertor **core** — the retrieval nucleus, the RAG engines (vector/hybrid/graph/agentic) and the LLM-Wiki
skills — is **policy** and MUST be usable and testable as a **standalone library**, without depending on the
CLI, a UI, or any live external service. Source-level dependencies MUST point **inward**: the core MUST NOT
import any concrete provider SDK (LLM, embeddings, vector store) nor the CLI package; concrete adapters and
the CLI depend on the core's **abstractions**, never the reverse. Wiring of the concrete implementations lives
only in a dedicated **main/configuration** component.

*Rationale:* Dependency Rule + Plugin/Screaming Architecture (Clean Architecture). It is the literal
expression of REQ-E1 and CS-5 (reusable as a library, repo-agnostic): if the core knew `click` or `chromadb`,
the product would be the CLI, not the capability. **Non-negotiable test:** every use case is exercisable with
mock providers, without the CLI and without cloud.

### II. Interchangeable providers and backends behind boundaries; local-first

Every external dependency (LLM, embeddings provider, vector store, graph store) MUST sit behind a
**Sertor-owned abstraction** (an Adapter at the boundary); third-party types MUST NOT leak into the core. The
choice among implementations (local ↔ cloud, one vendor ↔ another) MUST be **configuration-driven**, with no
code change. Every capability MUST be able to run **entirely locally** (no cloud); the cloud (Azure included)
is a **configurable default**, not a requirement. A vector store is required **only** for the modes that use
embeddings; the purely structural (graph) mode operates without one.

*Rationale:* "Details Are Replaceable" (Clean Architecture) + "Boundaries" (Clean Code); REQ-E2/E4/E7, CS-7.
Swapping a provider (OpenAI→Anthropic, Chroma→pgvector) is inevitable and MUST cost a configuration change,
not a re-architecture.

### III. Justified simplicity (YAGNI) and small units

No abstraction, dependency or layer is added without **present evidence** of need (a real use case today).
Functions and modules MUST be small and **single-responsibility** (SRP), kept at one level of abstraction;
logic MUST NOT be duplicated (DRY) — shared retrieval/chunking/embeddings logic lives in the nucleus, not
copied across engines. Heavy or conflicting dependencies (e.g. the graph engine) MUST be **isolatable** to
avoid environment conflicts.

*Rationale:* Clean Code (small functions, SRP, DRY, smell G5) + the "no over-engineering" rule; the
modular/selective vision, REQ-E2/E7.

### IV. Explicit error handling; no silent null

Error handling MUST be **exception-based** with **context-rich**, domain exceptions; third-party errors MUST
be **wrapped** in Sertor exception types at the boundary. Operations MUST NOT return or propagate
`null`/`None` to signal an absence silently, nor leave partial/corrupt state: a missing index, an unavailable
provider, an unreachable RAG or an empty wiki MUST fail **explicitly**, with a clear, actionable message and
**without** side effects on existing state.

*Rationale:* Clean Code Ch.7 (exceptions over return codes, provide context, don't return/pass null);
FEAT-002 REQ-004 (abort, no partial index), FEAT-003 REQ-043.

### V. Testability and quality proven by measures

Every capability MUST have automated **F.I.R.S.T.** tests (Fast, Independent, Repeatable, Self-validating,
Timely); the core MUST be testable with **mock providers**, with no live cloud. Retrieval quality MUST be
**measured** on a sample corpus with ground-truth (hit@k, MRR), with the **prototype as baseline** and the
acceptance thresholds set at design time — a feature without a measure is **not "done"**, it is a prototype.
**TDD** (the three laws) is SHOULD (recommended as a practice), not imposed.

*Rationale:* Clean Code Ch.9 (F.I.R.S.T., tests as a safety net) + the "measure first" decision
(baseline = prototype); CS-1/CS-4, OBJ-2/OBJ-6.

### VI. Idempotence, determinism and non-destructiveness

Re-running an operation (indexing, wiki record/ingest/index) on the **same input** MUST produce a **stable**
result: no duplicated chunks/pages/log entries, stable identifiers derived from relative paths.
**Installation ≠ execution**: installing or adding a capability MUST NOT start an expensive ingestion by
itself. Operating on an existing repository MUST be **non-destructive** (no silent overwrite of the user's
files). The **cost/latency** of LLM calls MUST be weighed before invoking them (prefer the cheapest adequate
deterministic paths).

*Rationale:* REQ-E6 (idempotence), CLI CS-2/REQ-E2 (install≠run), CS-4 (non-destructiveness), FEAT-001
REQ-004/010, FEAT-003 SC-3b.

### VII. Readability as communication; leave the code cleaner

Code is written **for its reader**. Names MUST be intention-revealing and use the retrieval **domain
vocabulary** (retrieve, rank, fuse, rerank, synthesize, index) instead of generic verbs (process, execute,
handle). Comments are reserved for the intent the code cannot express; commented-out code and redundant
comments are removed. Every change leaves the touched code **at least as clean as it found it** (Boy Scout
Rule).

Functions MUST be **small and shallow in nesting**: **guard clauses / early returns** are preferred over deep
condition nesting, and a named helper is extracted when a block grows or nests. **Dogmatic single-exit (SESE)
is NOT required**: the problem to avoid is **nesting depth**, **not** the number of `return`s. *(Clarification
v1.1.1: Dijkstra's structured programming banned **GOTO**, not multiple `return`s; multiple returns that
*reduce* nesting are idiomatic and preferred. A single exit is legitimate when it makes the flow clearer, but
must not be imposed at the cost of readability or of consistency with the surrounding guard-clause code.)*

*Rationale:* Clean Code Ch.1/2/4 (small functions, low nesting, intention-revealing names). RAG domains are
easily obscured by vague naming and nested conditions: clarity and low depth are the cheapest quality lever.

### VIII. Centralized configuration of the core

All operational choices of the core — LLM/embeddings provider, retrieval/vector-store backend, paths, chunking
parameters (size, overlap, language set), retrieval `k`, batch size, exclusion patterns — MUST be governed by a
**single centralized configuration**, readable from a file and/or environment variables, **without editing the
code** and **with no hard-coded defaults** in the individual components. Changing environment (local ↔ cloud),
provider or parameters MUST be an act of **configuration**, not of coding.

*Rationale:* Clean Architecture (config is a "detail" confined to the Main Component; policy is independent of
details) + REQ-030 (FEAT-001) and CS-4 (configurable without touching the code). It makes Principles I and II
real: without centralized configuration, interchangeability is theoretical.

### IX. Observability: every runtime operation is logged

Every runtime operation MUST emit **structured logs** sufficient to diagnose a failure without reading the
source code. In particular, **both embeddings creation/indexing and retrieval (querying)** MUST record at
least: the operation, the provider/backend used, the number of documents/chunks processed, the embedding
dimension, execution times and any errors. Logs MUST NOT contain secrets. Observability is part of the
definition of "production-grade", not an extra.

*Rationale:* Clean Code (error handling with context) + Clean Architecture (Humble Object: observable logic
separated from glue); FEAT-001 REQ-031, FEAT-002 NFR-007, FEAT-003 RNF-004.

### X. Host-agnostic capabilities (portability is a constraint, not an aspiration)

Every Sertor capability — the retrieval nucleus, the RAG engines, indexing, the LLM-Wiki skills and the tools
that orchestrate them — MUST be **decoupled from the host project's domain and structure**. The host is a
**consumer**: it is **configured**, not **assumed**. A capability's body MUST NOT embed project-specific
assumptions (fixed paths, domain names, the host's folder structure); what varies across hosts MUST live in
**configuration/instantiation**, not in the capability's code. **Dogfooding** (Sertor applied to itself) is
instrumental and MUST NOT be used as a license to violate this boundary. **Non-negotiable test:** a capability
MUST be able to operate on a different host project (code+doc, doc-only, code-only) with no change to its body
— only by changing configuration.

*Rationale:* it is the operational translation of the **mission** (Sertor installable on any project) and
**generalizes Principle I** — so far scoped to the core library alone ("the library is the product,
repo-agnostic") — to **all** capabilities, skills and the LLM Wiki included. Without this principle, dogfooding
would tend to sediment Sertor-specific assumptions inside capabilities that must stay portable. Sources: README
(Vision/Mission), REQ-E1/CS-5.

### XI. Consume through the vehicles (CLI/MCP), not the library at runtime

**Runtime** consumers — the LLM agent, scripts, any host or automation — MUST access Sertor's capabilities
**only** through its **vehicles**: the **CLI** (`sertor-rag`, `sertor-wiki-tools`) or the **MCP server**. They
MUST NOT import and invoke the `sertor_core` library directly at runtime (e.g. `build_indexer().index(...)`).
**Sole exception: unit/integration tests**, which exercise the library and functions directly — this is how
Principles I and V guarantee testability in isolation.

*Rationale:* the vehicles wire the cross-cutting behaviors **uniformly** — observability
(`enable_observability`), centralized configuration (Principle VIII), error wrapping at the boundary (Principle
IV), secret redaction. Direct library access **silently bypasses** them: a real case, a re-index via
`build_indexer().index()` is not traced in telemetry because it skips `enable_observability` (wired only in the
vehicles). Confining consumption to the vehicles makes every operation observable and consistently configured;
tests are the exception because they verify the isolated unit. *Note:* this does not contradict Principle I (the
library remains the product, architecturally standalone and importable) — this principle governs **who consumes
at runtime**, not the dependency structure.

### XII. Fail Loud, Fix the Cause — signal and remove the cause, do not suppress

When a capability fails, **remove the cause**; MUST NOT disable, mute or route around the capability just to
**make the error go away**. **Early, visible feedback is a value**, not noise: failures MUST **surface early**
(early feedback). Graceful degradation is allowed **only if the failure is reported** (warning/finding) — **silent
suppression is prohibited**, and so is switching a feature off to avoid confronting its error. Removing or gating
a capability is legitimate **only as an explicit, recorded decision**, never as a reflex to dodge an error.

*Rationale:* an error seen early costs less; switching off the failing feature **destroys the signal** and pushes
the defect further downstream. It generalizes to every capability and vehicle the standing rule «errors = signal,
not noise» (today specific to MCP/dogfooding). It does not contradict Principle IV (explicit error handling) nor
the *intended error policy* (tolerant core with warnings ↔ strict baseline engine): degradation that **reports**
is compliant; what the principle forbids is **silence** or **switching off to avoid seeing**. Origin: the OTel
episode (2026-06-20) — the correct move was to fix the collector, not to switch off the export.

### XIII. Product Plane vs. Fixture Plane (NON-NEGOTIABLE)

<!-- CANONICAL text: identical to what we release in the `sertor-flow` starter (there it is Principle XII).
     Kept verbatim from the ratified text; the only adaptation is the numeric cross-reference («Principle XII»,
     because here Fail Loud is XII, not XI). -->

When a product is exercised against fixtures inside its own repository (dogfooding), keep two planes distinct.
The **product plane** is how the product behaves for a real user on a real asset: where its state lives, how two
assets are isolated from each other, the lifecycle and ownership of what it produces. The **fixture plane** is
the in-repo test fixtures and the state a dogfood session writes onto them. Product and behavior decisions are
justified ONLY by the general real-asset case, NEVER by fixture convenience; and a repo-hygiene decision about
dogfood byproducts (version them, ignore them) NEVER silently becomes product behavior — decisions carry the
provenance of their plane. Above all: when a fixture-plane workaround compensates for a product-plane gap, that
gap is recorded as an OPEN PRODUCT QUESTION, never hidden by the workaround (this is Principle XII applied to
dogfooding — the papered-over gap must surface). The ceremony scales with how much the product mutates the asset
in place: a product that only reads the asset and emits an external artifact needs almost none; a product that
writes state INTO the asset it operates on needs it acutely.

*Rationale:* it is **Principle XII «Fail Loud, Fix the Cause» applied to dogfooding** — a product gap papered
over by a test workaround **must surface**, not stay hidden; it rhymes with Principle VI
(idempotence/non-destructiveness). It encodes a trap we have already lived (speclift/specaudit as in-repo
fixtures, dogfood vs real corpus, epic E15). **Proposed and already practiced by the Sinthari node** (v0.4.0,
2026-07-12), accepted 2026-07-14; E10-FEAT-030. Source:
`input-other-agents/processed/sinthari-proposta-principio-xii-product-vs-fixture-plane-2026-07-12.md`.

## Security, Secrets and Provenance

Secrets (API keys, credentials) MUST NOT be written into versioned files; they travel only via environment
variables or an uncommitted `.env`. Regenerable artifacts (indexes, vector stores, caches, logs, virtualenvs,
vendored corpora) MUST be git-ignored. Ingestion MUST keep the corpus clean (configurable exclusion of
binaries/artifacts/secrets).

*Rationale:* REQ-E5 + the workspace `.gitignore` discipline.

## Governance

This constitution **prevails** over ad-hoc decisions; on conflict between a design/plan and a principle, the
principle wins (or the principle is first amended).

- **Production workflow:** after ratification, work happens on **branch + PR** — no direct pushes to
  `main`/`master` (the prototype-phase exception ends at ratification).
- **Constitution Check:** every `plan.md` MUST pass a Constitution Check gate **before** research (Phase 0) and
  **after** design (Phase 1); a design that violates a non-negotiable principle (in particular I and IV) MUST be
  reworked, or the principle amended. The check includes the **mission-alignment** gate: does the design serve
  the mission (portable self-knowledge; **code+doc fusion**; quality of the retrieval returned to the agent) and
  not drift onto peripheral concerns? Mark PASS / N/A with a reason.
- **Amendments:** via a PR that documents the change and the rationale; versioned with **semantic versioning**
  (MAJOR: removal/redefinition of a principle; MINOR: a new principle/section; PATCH: clarifications).
- **Compliance:** the dogfooding RAG over the prototype is the reference of "what good looks like"; new
  capabilities are reviewed against these principles.

**Version**: 1.5.0 | **Ratified**: 2026-05-31 | **Last Amended**: 2026-07-22
