---
name: eval-suite-author
description: "Assisted authoring of the retrieval evaluation suite (ground-truth). Using the project's RAG/MCP tools over the indexed corpus, the agent DERIVES candidate (query -> expected path) pairs, proposes them for approval, and persists ONLY the approved ones by invoking the CLI subcommand `eval add-case`. It never runs the evaluation (that is deterministic and does not depend on this skill); it never imports the core library."
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

## Prerequisite: the corpus must be indexed

Derivation reads the corpus through the RAG/MCP tools (code/doc search, symbol search). If the corpus
is not indexed those tools return empty or error: in that case STOP with an actionable message -

> "The corpus does not appear to be indexed. Index it first with `sertor-rag index .`, then re-run."

To deterministically check that a candidate path really exists in the index, use the vehicle:
`sertor-rag eval validate-path <path> [...]` (it always exits 0; it reports the missing/checked paths).

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
   `sertor-rag eval validate-path <path>`. If it is missing, fix the path or flag it to the user (a
   path outside the index can never be a hit).

4. Propose to the user. Present the candidates as a clear `query -> expected (kind)` list and ask which
   to approve. Briefly explain the rationale of each (why that file is expected).

5. Persist the approved ones only. For each approved case, invoke the vehicle:

   ```powershell
   sertor-rag eval add-case --query "<the query>" `
       --expected "<path/to/expected.ext>" --kind symbol
   ```

   If an expected path is not in the index, the command warns and requires `--confirm` before writing.
   Forward that to the user; do not force `--confirm` yourself. `add-case` is idempotent (a query
   already present is not duplicated) and non-destructive.

6. Close. Summarise which cases were added and remind the user that the suite is versioned project data:
   it must be committed. The evaluation is launched with `sertor-rag eval run` (deterministic,
   independent).

## What NOT to do

- Never write secrets into the suite (it is versioned data, diffable by hand).
- Do not invent paths: every `expected` must be a real file in the index (verified with
  `validate-path`).
- Do not run the evaluation on the user's behalf as if it were part of authoring: they are separate
  phases (authoring = assisted judgment; run = deterministic measure).
