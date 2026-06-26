---
name: eval-feedback
description: "Explicit relevance feedback that turns a user's verdict on search results into a refinement of the evaluation suite. Use it whenever someone judges retrieval quality. Triggers on 'this result is wrong/right', 'mark this as relevant', 'the expected file for this query should be X', 'tune the eval suite from these results', or reviewing what a search returned. The agent observes the results, receives the user's verdict (relevant / not relevant), and updates the `expected` of the matching case - always through the CLI vehicle `sertor-rag eval add-case`. No verdict is ever inferred or persisted without an explicit user action. It never imports the core library."
argument-hint: "The query whose results you are judging (or leave empty and start from a search you just ran)"
user-invocable: true
disable-model-invocation: false
---

## User Input

The text that invoked this capability is the query whose result relevance is being judged. If it is
empty, start from the last search performed or ask the user which query to consider.

## Purpose

This skill captures the user's explicit feedback on how relevant a retrieval was, and turns it into a
refinement of the evaluation suite (`eval/suite.toml`): if the user indicates that a certain file WAS
the right result for a query (or that the returned one was NOT), the suite is updated so that the
future measure (`eval run`) captures that judgment. It is the ground-truth improvement loop fed by real
usage.

## Hard boundary (no implicit judgment)

- Never infer, never persist without an explicit action. Every change to the suite requires an explicit
  confirmation from the user. There is no automatic mode: the agent does not deduce relevance from the
  scores nor writes on its own. It proposes; the user confirms; the agent writes.
- Vehicle only. Every write goes through the CLI subcommand `sertor-rag eval add-case`. Never access the
  core library directly.

> **How to invoke `sertor-rag`.** The runtime CLI is installed into the project's `.sertor/.venv` and
> is NOT on `PATH`. Invoke it via **`uv run`** from any cwd in the host repo:
> `uv run --project .sertor sertor-rag <args>` (e.g. `uv run --project .sertor sertor-rag eval add-case …`).
> A bare `sertor-rag …` (or `which sertor-rag`) failing means "not on PATH", NOT "not installed". If
> `uv` is unavailable, fall back to `.sertor/.venv/Scripts/sertor-rag.exe` (Windows) /
> `.sertor/.venv/bin/sertor-rag` (POSIX); if neither resolves, STOP and report that the runtime is not
> installed.

## Procedure

1. Observe the results. Consider the query and the results the retrieval returned (e.g. from
   `uv run --project .sertor sertor-rag search`). Show them to the user readably (path + why it might
   or might not be relevant).

2. Collect the explicit verdict. Ask the user, for the query, which file(s) is the truly expected
   (relevant) result. The verdict is the user's, not yours: do not assign it yourself.

3. Verify the paths. Check that the indicated paths exist in the index with
   `uv run --project .sertor sertor-rag eval validate-path <path>` (it always exits 0; it reports the
   missing paths). An expected path outside the index can never be a hit: flag it.

4. Update the suite, on confirmation.
   - Case already in the suite - if a case for that query exists, propose to update its `expected` with
     the paths the user confirmed as relevant; apply only after confirmation.
   - Case absent - if there is no case for that query, OFFER to create a new one with the approved
     paths; create only after confirmation.

   In both cases the write goes through the vehicle:

   ```powershell
   uv run --project .sertor sertor-rag eval add-case --query "<the query>" `
       --expected "<approved/path.ext>[,<another>]" --kind nl
   ```

   `add-case` is idempotent (a query already present is not duplicated) and non-destructive; if a path
   is not in the index the command requires `--confirm` - forward that request to the user, do not force
   it.

5. Close. Summarise what was updated and remind the user that the suite is versioned project data (it
   must be committed) and that the measure (`uv run --project .sertor sertor-rag eval run`) stays
   deterministic and independent of this skill.

## What NOT to do

- Do not deduce relevance from the similarity scores and write it autonomously.
- Do not have or use an automatic mode: every write goes through the user's confirmation and the CLI.
- Do not write secrets into the suite.
