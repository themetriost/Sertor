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

### II. Test-First & Measurable (NON-NEGOTIABLE)

Code is testable by construction. Tests follow F.I.R.S.T. (Fast, Isolated,
Repeatable, Self-validating, Timely): they run without network or external
services, are deterministic, and assert behavior — not implementation. Collaborators
are mockable through the ports of Principle I (structural typing → no inheritance
required). New behavior comes with the tests that pin it.

### III. YAGNI & Small Units

Add an abstraction only when a real, present need requires it — never speculatively.
Prefer small units: short functions, narrow modules, single responsibility. Code
you do not need today is a liability, not an asset. Generalize on the second real
consumer, not the first imagined one.

### IV. Explicit Errors (NON-NEGOTIABLE)

Errors are explicit and typed. No silent `None`, no swallowed exceptions, no hidden
partial state. Fail fast at boundaries with a domain error that names what went
wrong; wrap third-party errors at the boundary so callers catch one error family.
The failed step is always identifiable.

### V. Idempotence & Non-Destructiveness

Operations that touch user state are idempotent and non-destructive by default.
Re-running an operation yields the same result with zero changes; existing user
content is preserved (create-if-absent, additive merges, marker-delimited blocks).
Destructive actions are explicit, opt-in, and reversible where possible.

### VI. Readability & Clean Code

Code is written to be read. Domain-meaningful naming, guard clauses over deep
nesting, small functions, comments that explain *why* not *what*. Match the style
of the surrounding code. Clean Code over cleverness.

### VII. Centralized Configuration

Defaults live in one place (a settings module / templates), never hard-coded across
the body of the code. Configuration is read once and injected; switching an option
(provider, backend, mode) is a configuration change, not a code edit.

### VIII. Observability

The system emits structured, leveled logs at meaningful operations and outcomes.
Logs NEVER contain secrets (keys, tokens, credentials are redacted). An operation's
report IS part of its observability: status is inspectable without side effects.

## Security & Secrets

- Secrets (API keys, tokens, credentials) live ONLY in environment files (e.g.
  `.env`) and are NEVER committed to version control.
- `.gitignore` excludes secrets, virtual environments, caches, and regenerable
  artifacts (build output, logs, indexes).
- No secret ever appears in logs, error messages, reports, or committed files.

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

**Version**: 0.1.0 | **Ratified**: TODO | **Last Amended**: TODO
