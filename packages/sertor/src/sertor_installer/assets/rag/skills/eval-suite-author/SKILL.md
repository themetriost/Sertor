---
name: eval-suite-author
description: "Assisted authoring of the evaluation suite (ground-truth): retrieval cases (query -> expected path) and code-graph navigation cases (relation + symbol -> expected set of refs). Using the project's RAG/MCP tools over the indexed corpus, the agent DERIVES candidates, proposes them for approval, and persists ONLY the approved ones by invoking the CLI subcommands `eval add-case` / `graph-eval add-case`. It never runs the evaluation (that is deterministic and does not depend on this skill); it never imports the core library."
argument-hint: "Describe the corpus area/capability you want evaluation cases for (e.g. 'retrieval over the domain symbols')"
user-invocable: true
disable-model-invocation: false
---

## User Input

The text that invoked this capability IS the corpus area to derive evaluation cases for (e.g. "the
public symbols of the core", "the architectural queries about composition"). If it is empty, ask the
user to describe the area or the goal of the suite.

## Purpose

This skill helps BUILD the evaluation suite (`eval/suite.toml`) - the set of (query -> expected paths)
pairs used to measure retrieval relevance (hit-rate@k / MRR). It is ASSISTED authoring: the agent
proposes, the user approves, and only the approved cases are written. The measurement itself
(`eval run`) is DETERMINISTIC and DOES NOT depend on this skill or on any LLM: here you only curate the
DATA (the suite), not the run.

## Hard boundary (deterministic vs judgment)

- No execution, no library import. This skill does NOT evaluate and does NOT import the core. Every
  write goes through the CLI vehicle only: `sertor-rag eval add-case`. Never access the library
  directly nor the `build_*` factories. Access Sertor through a vehicle (CLI or MCP).
- Approved cases only. No candidate is persisted without an explicit approval from the user. The agent
  proposes; the user decides; the agent writes the accepted ones.

> **How to invoke `sertor-rag`.** The runtime CLI is installed into the project's `.sertor/.venv` and
> is NOT on `PATH`. Invoke it via **`uv run`** from any cwd in the host repo:
> `uv run --directory .sertor sertor-rag <args>` (e.g. `uv run --directory .sertor sertor-rag eval add-case …`).
> A bare `sertor-rag …` (or `which sertor-rag`) failing means "not on PATH", NOT "not installed". If
> `uv` is unavailable, fall back to `.sertor/.venv/Scripts/sertor-rag.exe` (Windows) /
> `.sertor/.venv/bin/sertor-rag` (POSIX); if neither resolves, STOP and report that the runtime is not
> installed.

## Prerequisite: the corpus must be indexed

Derivation reads the corpus through the RAG/MCP tools (code/doc search, symbol search). If the corpus
is not indexed those tools return empty or error: in that case STOP with an actionable message -

> "The corpus does not appear to be indexed. Index it first with
> `uv run --directory .sertor sertor-rag index .`, then re-run."

To deterministically check that a candidate path really exists in the index, use the vehicle:
`uv run --directory .sertor sertor-rag eval validate-path <path> [...]` (it always exits 0; it reports
the missing/checked paths).

## Procedure

1. Frame the area. From the input, identify the corpus area/capability to create cases for (specific
   symbols, architectural files, behaviours).

2. Derive candidates with the RAG/MCP tools. For each candidate, write a realistic query (as a user or
   agent would write it) and identify the expected path - the file that SHOULD appear among the
   results. Mix two types (the optional but recommended `kind` field):
   - `symbol` - exact-symbol query (a class/function/error name). Use the graph symbol search to find
     where it is defined.
   - `nl` - architectural natural-language query (a concept/behaviour). Use the combined code+doc
     search.

3. Verify the candidate paths. For each `expected`, check that it is present in the index with
   `uv run --directory .sertor sertor-rag eval validate-path <path>`. If it is missing, fix the path or
   flag it to the user (a path outside the index can never be a hit).

4. Propose to the user. Present the candidates as a clear `query -> expected (kind)` list and ask which
   to approve. Briefly explain the rationale of each (why that file is expected).

5. Persist the approved ones only. For each approved case, invoke the vehicle:

   ```powershell
   uv run --directory .sertor sertor-rag eval add-case --query "<the query>" `
       --expected "<path/to/expected.ext>" --kind symbol
   ```

   If an expected path is not in the index, the command warns and requires `--confirm` before writing.
   Forward that to the user; do not force `--confirm` yourself. `add-case` is idempotent (a query
   already present is not duplicated) and non-destructive.

6. Close. Summarise which cases were added and remind the user that the suite is versioned project data:
   it must be committed. The evaluation is launched with `uv run --directory .sertor sertor-rag eval run`
   (deterministic, independent).

## Authoring code-graph navigation cases (`[[graph_case]]`)

Beyond retrieval cases, the suite can hold code-graph NAVIGATION cases: a case = relation + target
symbol -> expected SET of `ref` (`path#qualname`). The metric is set-based (precision/recall/F1), not
rank. MVP relations: `who_calls` (callers of the symbol) and `defines` (where it is defined). Here too
authoring is assisted: the agent proposes a DETERMINISTIC snapshot, the user approves, and only the
approved cases are written.

1. Navigate the current graph state (deterministic snapshot). For the requested relation+symbol, get
   the candidate set of refs by invoking the deterministic vehicle:

   ```powershell
   uv run --directory .sertor sertor-rag graph-eval validate-ref --relation who_calls --target build_facade --json
   ```

   The JSON output reports `checked`/`unverifiable`/`graph_available`. To DISCOVER the current set
   (snapshot), pass the refs you expect and read which are `unverifiable`, or derive the real refs from
   the RAG/MCP tools (symbol / who-calls search) and compare. The candidate set is what the graph
   returns NOW, not the agent's autonomous judgment.

2. Propose the set to the user. Present the candidate set of refs as a proposal to approve (it is a
   snapshot: "these are the callers of `X` today"). Explain that the set becomes the case's expected
   value and that the gate measures its non-regression.

3. Persist only after explicit approval. For each approved case:

   ```powershell
   uv run --directory .sertor sertor-rag graph-eval add-case --relation who_calls --target build_facade `
       --expected "path/to/a.py#A,path/to/b.py#B" --confirm
   ```

   - Never an implicit or automatic write: the user must approve the set first.
   - If the check reports `unverifiable` refs (non-empty): name them to the user and offer to drop them
     or proceed with `--confirm`. Do not force `--confirm` yourself.
   - `add-case` is idempotent on `(relation, target)` and non-destructive (it preserves the retrieval
     `[[case]]` and the other `[[graph_case]]`).
   - A case with an EMPTY expected set is legitimate (expected "no callers"): use `--expected ""`.

4. Re-authoring an existing snapshot. If the correct set changed and the user approves it, update the
   case with `uv run --directory .sertor sertor-rag graph-eval amend-case --relation R --target T --expected "..."`.
   It is the deterministic path to re-freeze the snapshot; the decision stays the user's.

5. If the graph is not built (`graph_available=false`): STOP with an actionable message - "The code
   graph does not appear to be built. Index the project first with
   `uv run --directory .sertor sertor-rag index .`, then re-run."

Hard boundary (deterministic vs judgment, here too). The deterministic run
(`uv run --directory .sertor sertor-rag graph-eval run`) DOES NOT depend on this skill or on any LLM:
the skill is the judgment surface (propose/approve
the sets), the run is the deterministic measure in the core. Every access to the graph goes ONLY
through the `graph-eval validate-ref`/`add-case`/`amend-case` subcommands (vehicle): the skill never
imports the core library.

## What NOT to do

- Never write secrets into the suite (it is versioned data, diffable by hand).
- Do not invent paths/refs: every `expected` must be real (verified with `validate-path` for retrieval
  cases, with `graph-eval validate-ref` for navigation cases).
- Do not run the evaluation on the user's behalf as if it were part of authoring: they are separate
  phases (authoring = assisted judgment; run = deterministic measure).
