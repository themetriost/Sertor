## Development method (SDLC) — always active

This project follows a spec-driven development method (SpecKit) with an explicit
constitution gate and disciplined version control. These rules are standing: apply
them on every significant change, without being asked.

### The SpecKit flow

Significant work flows through these phases, in order; each consumes the artifacts
of the previous one:

1. **requirements** — capture the need (EARS-style requirements) before designing.
2. **specify** — write the feature specification (`spec.md`): what and why, scope,
   out-of-scope, acceptance criteria.
3. **clarify** — resolve open questions in the spec before planning; never guess on
   a real design fork — ask, with context.
4. **plan** — produce the implementation plan (`plan.md`), data model, contracts,
   and research decisions.
5. **tasks** — decompose the plan into ordered, dependency-aware tasks (`tasks.md`).
6. **analyze** — cross-check spec ↔ plan ↔ tasks for consistency and coverage.
7. **implement** — execute the tasks in order, producing real code and tests.

The phases are driven by the SpecKit skills installed for your assistant (the `speckit-*` skills)
and the templates/scripts under `.specify/`.

### Constitution Check (gate)

The project constitution lives in `.specify/memory/constitution.md`. It is a **gate**,
not decoration:

- Re-check the constitution at `plan` time and again after design: list each
  principle and mark PASS / N/A, justifying any deviation explicitly.
- A change that violates a principle is reworked or its complexity is justified in
  writing — it does not ship silently.
- Amend the constitution through its own flow (semantic versioning), never by drift.

### Error discipline — fix, don't suppress

When something errors, remove the cause. **Never disable, mute, or route around a
capability just to silence its error** — early, visible feedback is a value. Graceful
degradation is acceptable only when it *reports* the failure (a warning/finding);
silent suppression, or turning a feature off to dodge its error, is not. Disabling a
capability is a deliberate, recorded decision, never a reflex. (Constitution: *Fail
Loud, Fix the Cause*.)

### Version control discipline (owner of git/commit rules)

This block is the **owner** of git and commit discipline for the project.

- **Branch + PR workflow.** Significant work happens on a feature branch and merges
  via pull request. **No direct pushes to the default branch** (`main`/`master`).
- **Conventional Commits.** Commit messages follow `type(scope): summary`; the body
  explains the *why*; one commit per significant step.
- **Never commit secrets or regenerable artifacts.** `.env`, key files, virtual
  environments, caches, build output, logs, and indexes stay out of version control
  (covered by `.gitignore`).
- **Facing a conflict, ask what is actually MISSING — not how to resolve it.** A conflict shows you
  two versions in collision; it does not tell you how much of it is real. Compare the branch against
  the target first: content that reached the target by another route produces a conflict with
  *nothing to reconcile*. Measure before you reach for a rebase, a merge strategy, or a reset — the
  answer is often that a large conflict is missing one line, and finding that out costs two commands.
- **"Modified" has two meanings — pick the one you mean.** `git status` answers *"does this appear
  modified?"*; `git diff` answers *"did the content change?"*. They diverge on line endings, mode
  bits, and whitespace: a file can be listed as modified with zero lines added or removed. Anything
  that decides **whether work happened** must ask the second question, or it will report work where
  there is none.
- **Delegate git operations to the `configuration-manager` agent.** All version
  control actions (staging, commit, branch, merge, tag, push, pull) are delegated to
  the `configuration-manager` agent rather than performed inline, so the main flow is
  never blocked on bookkeeping. Pass it a self-contained brief (what was done, which
  files, why, the requested operation). Destructive/irreversible operations
  (`push --force`, `reset --hard`, history rewrite, `branch -D`, `clean -fd`) run
  **only when explicitly requested** in the brief; otherwise the agent stops and
  reports.
