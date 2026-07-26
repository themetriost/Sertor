# Project Constitution

> Starter constitution installed by `sertor-flow`. It encodes general engineering
> discipline, not any specific domain. Personalize it with `speckit-constitution`
> (`/speckit.constitution`): rename the project, adjust the principles to your
> context, and bump the version when you amend it. It is yours to edit.

## Core Principles

### I. Depend Toward Abstractions (NON-NEGOTIABLE)

Dependencies point inward, toward stable abstractions. The domain (entities,
ports/protocols, errors) MUST NOT import concrete SDKs, frameworks, or I/O.
Concrete providers live behind interfaces (ports) and are selected in a single
composition root, never chosen inside the domain or the services. This keeps the
core testable in isolation and replaceable without rippling changes.

### II. Replaceable Details / No Vendor Lock-In

External dependencies (databases, cloud vendors, model/LLM providers, brokers, file
systems) sit behind an interface YOU own; third-party types MUST NOT leak into the
domain or services. Choosing between implementations — local ↔ cloud, one vendor ↔
another — is a configuration change, not a rewrite. Prefer being able to run locally
and to substitute a fake in tests. Details are replaceable; policy is stable.

### III. Consume Through Stable Interfaces, Not Internals

Consumers — other modules, scripts, agents, automation — depend on a component's
PUBLIC interface (its API, CLI, or service), never on its internals. Internal
structure stays free to change without breaking callers. Cross-cutting concerns
(logging, configuration, error wrapping) are wired once at the public entry points;
reaching past them into internals silently bypasses that wiring. Tests are the
exception: they exercise units directly to verify them in isolation.

### IV. Test-First & Measurable (NON-NEGOTIABLE)

Code is testable by construction. Tests follow F.I.R.S.T. (Fast, Isolated,
Repeatable, Self-validating, Timely): they run without network or external
services, are deterministic, and assert behavior — not implementation. Collaborators
are mockable through the ports of Principle I (structural typing → no inheritance
required). New behavior comes with the tests that pin it.

### V. YAGNI & Small Units

Add an abstraction only when a real, present need requires it — never speculatively.
Prefer small units: short functions, narrow modules, single responsibility. Code
you do not need today is a liability, not an asset. Generalize on the second real
consumer, not the first imagined one.

### VI. Explicit Errors (NON-NEGOTIABLE)

Errors are explicit and typed. No silent `None`, no swallowed exceptions, no hidden
partial state. Fail fast at boundaries with a domain error that names what went
wrong; wrap third-party errors at the boundary so callers catch one error family.
The failed step is always identifiable.

### VII. Idempotence & Non-Destructiveness

Operations that touch user state are idempotent and non-destructive by default.
Re-running an operation yields the same result with zero changes; existing user
content is preserved (create-if-absent, additive merges, marker-delimited blocks).
Destructive actions are explicit, opt-in, and reversible where possible.

### VIII. Readability & Clean Code

Code is written to be read. Domain-meaningful naming, small functions, comments that
explain *why* not *what*. Prefer guard clauses and early returns over deep nesting —
multiple returns that *reduce* nesting are idiomatic, and single-exit (SESE) is NOT
required: the enemy is nesting depth, not return count. Match the style of the
surrounding code. Clean Code over cleverness.

### IX. Centralized Configuration

Defaults live in one place (a settings module / templates), never hard-coded across
the body of the code. Configuration is read once and injected; switching an option
(provider, backend, mode) is a configuration change, not a code edit.

### X. Observability

The system emits structured, leveled logs at meaningful operations and outcomes.
Logs NEVER contain secrets (keys, tokens, credentials are redacted). An operation's
report IS part of its observability: status is inspectable without side effects.

### XI. Fail Loud, Fix the Cause

When a capability fails, fix the root cause; do NOT disable, mute, or route around
it just to make the error go away. Early, visible feedback is a value, not noise —
failures surface early. Graceful degradation is allowed ONLY when the failure is
reported (a warning/finding); silent suppression is prohibited, and so is switching
a feature off to avoid confronting its error. Removing or gating a capability is
legitimate only as an explicit, recorded decision — never as a reflex to dodge an
error.

### XII. Product Plane vs. Fixture Plane (NON-NEGOTIABLE)

When a product is exercised against fixtures inside its own repository (dogfooding),
keep two planes distinct. The **product plane** is how the product behaves for a real
user on a real asset: where its state lives, how two assets are isolated from each
other, the lifecycle and ownership of what it produces. The **fixture plane** is the
in-repo test fixtures and the state a dogfood session writes onto them. Product and
behavior decisions are justified ONLY by the general real-asset case, NEVER by fixture
convenience; and a repo-hygiene decision about dogfood byproducts (version them, ignore
them) NEVER silently becomes product behavior — decisions carry the provenance of their
plane. Above all: when a fixture-plane workaround compensates for a product-plane gap,
that gap is recorded as an OPEN PRODUCT QUESTION, never hidden by the workaround (this
is Principle XI applied to dogfooding — the papered-over gap must surface). The ceremony
scales with how much the product mutates the asset in place: a product that only reads
the asset and emits an external artifact needs almost none; a product that writes state
INTO the asset it operates on needs it acutely.

### XIII. Derived State, Not Declared (NON-NEGOTIABLE)

When a fact exists in more than one place, one of them MUST be **derived** from the
other. A value that is *copied* into a second location — a version stamp, a dependency
pin, a cached verdict, a hardcoded list mirroring a runtime fact, prose describing a
behavior — diverges from its source the moment either changes, and nothing notices.

Where derivation is genuinely impossible (a user file you MUST NOT overwrite, a cache
that exists to save cost, an artifact produced by another tool), the duplication is
permitted ONLY if something **reconciles** the two and **reports** the divergence.
Preserving a stale copy can be correct; preserving it **in silence** is not. "It will
be kept in sync by discipline" is not a reconciler.

The signature of this failure is constant: **a no-op that reports success** — and it
strikes precisely the mechanism meant to update, which becomes the keeper of the old
version. It is related to but distinct from two other principles: Principle VII governs
whether re-running is *safe*, this one governs **on what identity** "already done" is
decided; Principle XI governs an error already raised, this one governs a value that
quietly stops being true.

**Gate (at planning time).** For every new capability: *does it introduce a value that
duplicates an existing source of truth?* If yes, derive it. If it cannot be derived,
name the **reconciler** and the **report** that surfaces the divergence.

## Security & Secrets

- Secrets (API keys, tokens, credentials) live ONLY in environment files (e.g.
  `.env`) and are NEVER committed to version control.
- `.gitignore` excludes secrets, virtual environments, caches, and regenerable
  artifacts (build output, logs, indexes).
- No secret ever appears in logs, error messages, reports, or committed files.

## Amendments

Each release of this starter is listed here so that a project holding an older copy can
see **everything it has missed**, not only the latest change. Integrate them into your
own constitution when you choose — this file is yours, and nothing overwrites it.

- **0.5.0** — added Principle XIII «Derived State, Not Declared»: a fact living in two
  places must be derived, not copied; where it cannot be derived, a named reconciler
  must report the divergence.
- **0.4.0** — added Principle XII «Product Plane vs. Fixture Plane».
- **0.3.0** — added Principle XI «Fail Loud, Fix the Cause».
- **0.2.0** — refined the neutral principles (I–X).
- **0.1.0** — first neutral starter.

## Governance

- This constitution supersedes ad-hoc practices. Amendments are documented and
  approved before they take effect.
- Work proceeds on feature branches and merges via pull request — no direct pushes
  to the default branch (`main`/`master`).
- Every change passes a **Constitution Check** gate: a PR/review verifies compliance
  with these principles; complexity that violates a principle must be justified
  explicitly (or the change is reworked).
- The constitution is versioned with semantic versioning: MAJOR for a
  backward-incompatible principle change, MINOR for a new principle/section, PATCH
  for clarifications. Record the version and dates below on every amendment.

**Version**: 0.5.0 | **Ratified**: TODO | **Last Amended**: TODO
