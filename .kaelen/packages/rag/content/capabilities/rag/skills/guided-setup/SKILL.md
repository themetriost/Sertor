---
name: guided-setup
description: "Guides the user from a freshly installed Sertor RAG capability to a verified RAG (a green
  `sertor-rag doctor`). Use it whenever someone wants to get Sertor working. Triggers on
  'set up Sertor', 'configure the RAG', 'get the RAG running', 'why is the RAG not working', or any
  first-time setup/onboarding request. Detects current state, recommends an embedding provider from
  context (with confirmation), fills `.sertor/.env` (never handling secrets), announces the one-time
  GloVe download, and verifies fail-loud via `doctor`, orchestrating only the deterministic vehicles
  (`sertor-rag doctor`/`index`, through the capability's launcher). Read-only checks run freely;
  every host mutation/download runs only after explicit confirmation. It never reimplements a
  command and never imports the core."
user-invocable: true
disable-model-invocation: false
---

## User Input / When to use

The intent "set up Sertor / configure the RAG on this repo / get the RAG working" triggers this
skill. The text that invoked it IS the goal. If it is empty, ask the user to describe the objective
(configure the RAG on this repository) before proceeding.

This skill carries the *how* of bringing Sertor from "installed, not configured" to "RAG verified". It
is invocable on its own; the `concierge` agent routes setup requests to it.

**Installation is already done.** This skill is part of the Sertor RAG capability, installed in this
repository by the Kaelen engine: if you are reading it here, the capability (the MCP server, the CLI
and its environment) is installed. Updating or removing it is Kaelen's job, not this skill's (the
`kaelen update` / `kaelen uninstall` commands of the package it came from).

## Hard boundary (orchestrate, never reimplement)

- **No execution of core logic, no library import.** Every access to Sertor goes through a vehicle —
  the deterministic CLI commands (or MCP). Never import the library, never call the `build_*`
  factories.
- **The vehicles you orchestrate**, always from the repository root, through the capability's launcher:
  - `python .sertor/kaelen/rag/launch.py sertor-rag doctor` (and `… doctor --json`) — the
    deterministic health check (the four areas `config`/`provider`/`index`/`mcp` with pass/warn/fail,
    stable JSON schema, exit-code gate).
  - `python .sertor/kaelen/rag/launch.py sertor-rag index .` — builds the index (may trigger the
    one-time GloVe download).
- You **orchestrate** these commands; you do not alter or replace their behaviour.

## How to invoke

The CLI is NOT on `PATH`: it lives in the capability's own environment, which the launcher
`.sertor/kaelen/rag/launch.py` finds. Run it with Python 3.11 or later: try `python`, then `python3`,
then `py -3`. If the launcher answers that the environment is not built on this machine, the
capability has to be installed again here (Kaelen builds the environment per machine) — say so and
stop; do not build anything by hand.

## Consent gate (read-only is free; mutation needs an explicit "yes")

- **Read-only checks run freely, no confirmation:** running `… sertor-rag doctor`, inspecting whether
  `.sertor/.env` exists, reading which keys are present (never their secret values).
- **Every step that mutates the host or downloads runs only after explicit confirmation:** writing a
  setting into `.sertor/.env`, and the first `… sertor-rag index .` (including the GloVe download).
  Propose the step, explain what it will do, and wait for an explicit "yes" before running it.
- If the user does not confirm, do not run the step. Never auto-mutate or auto-download.

## Step 1 — Detect state (read-only)

Run `python .sertor/kaelen/rag/launch.py sertor-rag doctor --json` and read the four areas
(`config`/`provider`/`index`/`mcp`). Also inspect read-only whether `.sertor/.env` exists and which
keys it holds. Determine what is missing.

- **All four areas green** → the RAG is already configured and verified: say so and stop
  (idempotence — re-running on a healthy host verifies, it does not rebuild).
- **Partial** → conduct only the missing steps below.

## Step 2 — Choose provider (minimal heuristic + confirm)

Read three signals via vehicle/file (never the core), then **propose** a provider with a rationale and
let the user decide — never select one automatically:

1. **Cloud credentials present?** — from `doctor --json` (`config`/`provider` areas), or by a
   read-only look at which keys `.sertor/.env` holds (`OPENAI_API_KEY`, `AZURE_OPENAI_*`) — names
   only, never values.
2. **Host airgapped / offline?** — the user states it, or `… sertor-rag doctor --online` reports the
   provider `unreachable`. Do not probe the network yourself.
3. **Is natural-language semantics over the docs needed?** — ask the user.

Recommendation rules (propose with rationale, never impose):

- cloud credentials **absent** OR airgapped → recommend **local**: `glove` if NL semantics is needed
  (the default), `hash` for the deterministic / strict-airgapped floor.
- cloud credentials **present** + NL semantics needed → may propose **cloud** (`openai`, or `azure`)
  with the rationale (semantic quality), or `glove` locally if the user prefers on-machine.

## Step 3 — Configure (on confirm; the user handles secrets)

The settings live in `.sertor/.env`; the Kaelen install wrote the non-secret defaults there and
listed the ones still missing (for example `SERTOR_CORPUS`, the name of this project's corpus).

- **Non-secret settings** (`SERTOR_EMBED_PROVIDER`, `SERTOR_CORPUS`, `SERTOR_STORE_BACKEND`,
  `SERTOR_MEMORY`, `AZURE_OPENAI_ENDPOINT`): propose the exact `KEY=value` line; on explicit
  confirmation, set it in `.sertor/.env` — replace the key's existing line, or add one; touch no other
  line.
- **Secrets** (`OPENAI_API_KEY`, `AZURE_OPENAI_API_KEY`): **never ask the user to paste a secret into
  the conversation, and never write one yourself.** Tell the user which key to add to `.sertor/.env`
  and let them edit the file; then verify with `doctor` that the key is present. If a secret is
  already present, do not ask for it and do not print it.
- `.sertor/.env` is ignored by git (the capability declared it); never stage or commit it.

## Step 4 — Index (on confirm; announce the GloVe download)

If the chosen provider is `glove` and the model is **not** in cache, **announce** the one-time download
(~822 MB) **before** running the index, so the wait is expected and not a silent block. Then, on
confirmation, run `python .sertor/kaelen/rag/launch.py sertor-rag index .`.

## Step 5 — Verify (fail-loud)

Run `python .sertor/kaelen/rag/launch.py sertor-rag doctor` as the obligatory gate before declaring
success:

- `doctor: PASS` (exit 0) → declare the setup **verified**, reporting the supporting outcome.
- **Not green** → expose the failing **area + remedy** taken from the report lines and do **not**
  declare success. Never assume "done": the reported state is the one `doctor` verified.
- After the first index, the MCP server may need a restart (reconnect it in the assistant) to serve
  the new index.
