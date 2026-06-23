---
name: guided-setup
description: "Guide the user from an unconfigured repo to a verified Sertor RAG (a green
  `sertor-rag doctor`), conversing and orchestrating ONLY the deterministic vehicles
  (`sertor install`, `sertor configure --set`, `sertor-rag doctor`/`index`). Detects current state,
  recommends an embedding provider from context (with confirmation), fills `.env` securely (never
  printing secrets), announces the one-time GloVe download, and verifies fail-loud via `doctor`.
  Read-only checks run freely; every host mutation/download runs only after explicit confirmation.
  It never reimplements a command and never imports the core."
user-invocable: true
disable-model-invocation: false
---

## User Input / When to use

The intent "set up Sertor / configure the RAG on this repo / get the RAG working" triggers this
skill. The text that invoked it IS the goal. If it is empty, ask the user to describe the objective
(configure the RAG on this repository) before proceeding.

This skill carries the *how* of bringing Sertor from "nothing configured" to "RAG verified". It is
invocable on its own; the `concierge` agent routes setup requests to it.

## Hard boundary (orchestrate, never reimplement)

- **No execution of core logic, no library import.** This skill does NOT reimplement any command and
  does NOT import the core. Every access to Sertor goes through a vehicle — the deterministic CLI
  commands (or MCP). Never import the library, never call the `build_*` factories. Access Sertor
  through a vehicle only.
- **The vehicles you orchestrate** (by command name, host-agnostic):
  - `sertor install rag` — deposits the RAG assets and scaffolds `.sertor/.env`.
  - `sertor configure --set KEY=VALUE` — fills `.sertor/.env` (CI-safe wizard; secrets via a secure
    prompt).
  - `sertor-rag doctor` (and `sertor-rag doctor --json`) — the deterministic health check (the four
    areas `config`/`provider`/`index`/`mcp` with pass/warn/fail, stable JSON schema, exit-code gate).
  - `sertor-rag index .` — the first index (may trigger the one-time GloVe download).
- You **orchestrate** these commands; you do not alter or replace their behaviour. Do NOT paste inline
  shell/Python that replicates what `install`/`configure`/`doctor`/`index` already do.

## Consent gate (read-only is free; mutation needs an explicit "yes")

- **Read-only checks run freely, no confirmation:** running `sertor-rag doctor`, inspecting whether
  `.sertor/.env` exists, reading which keys are present. These never mutate the host.
- **Every step that mutates the host or downloads runs ONLY after explicit confirmation:**
  `sertor install rag`, `sertor configure --set`, and the first `sertor-rag index .` (including the
  GloVe download). Propose the step, explain what it will do, and wait for an explicit "yes" before
  running it.
- If the user does not confirm, do NOT run the step. Never auto-mutate or auto-download.

## Step 1 — Detect state (read-only)

Run `sertor-rag doctor --json` and read the four areas (`config`/`provider`/`index`/`mcp`) of the
`doctor` report. Also inspect read-only whether `.sertor/.env` exists and which keys it already holds.
Determine what is missing.

- **All four areas green** → the RAG is already configured and verified: say so, do NOT re-scaffold,
  and stop (idempotence — re-running on a healthy host detects and verifies, it does not rebuild).
- **Partial** → conduct ONLY the missing steps below; do not repeat steps already complete, and do not
  duplicate artifacts already present.

## Step 2 — Choose provider (minimal heuristic + confirm)

Read three signals via vehicle/file (never the core), then **propose** a provider with a rationale and
let the user decide — never select one automatically:

1. **Cloud credentials present?** — from `sertor-rag doctor --json` (`config`/`provider` areas: missing
   `AZURE_OPENAI_*` keys mean no cloud creds), or by a read-only look at `.sertor/.env` / the
   environment for `AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_API_KEY`.
2. **Host airgapped / offline?** — a conversational signal (the user states it), or `sertor-rag doctor
   --online` reporting the provider `unreachable`. Do NOT probe the network yourself.
3. **Is natural-language semantics over the docs needed?** — ask the user (is the corpus rich in
   documentation / NL?).

Recommendation rules (propose with rationale, never impose):

- cloud creds **absent** OR airgapped → recommend **local**: `glove` if NL semantics is needed (the
  core's local default), `hash` for the deterministic / strict-airgapped floor.
- cloud creds **present** + NL semantics needed → may propose **cloud** (Azure) with the rationale
  (semantic quality), or `glove` locally if the user prefers on-machine.
- in EVERY case you propose with a rationale and the **user confirms**; there is no automatic
  selection.

The chosen provider is written to `.sertor/.env` in Step 4 via
`sertor configure --set SERTOR_EMBED_PROVIDER=<glove|hash|azure|ollama>`.

## Step 3 — Install (on confirm)

If the RAG capability is missing (the `mcp`/`config` areas signal it is not installed), propose
`sertor install rag` (optionally `sertor install rag --assistant <host>`). On explicit confirmation,
run it. If the install is already present, skip this step.

## Step 4 — Configure (on confirm; secrets via the secure path)

Fill `.sertor/.env` **only** via `sertor configure --set KEY=VALUE` (or the wizard's secure prompt).

- For **secrets** (e.g. a cloud API key), use the wizard's secure `getpass` prompt and **never print
  the value** — not to the screen, not into the conversation log.
- If a secret is **already present** in `.sertor/.env`, do NOT re-ask for it and do NOT expose it.
- Never hand-edit `.sertor/.env` directly; always go through `sertor configure --set`.

## Step 5 — Index (on confirm; announce the GloVe download)

If the chosen provider is `glove` and the model is **not** in cache, **announce** the one-time download
(~822 MB) **before** running the index, so the wait is expected and not a silent block. Then, on
confirmation, run `sertor-rag index .`.

- If the GloVe model is already in cache, do NOT announce any download.
- When a download progress/ETA becomes available (a future deterministic capability), lean on it;
  until then the textual announcement is enough (honest degradation).

## Step 6 — Verify (fail-loud)

Run `sertor-rag doctor` as the obligatory gate before declaring success:

- `doctor: PASS` (exit 0) → declare the setup **verified**, reporting the supporting outcome.
- **Not green** → expose the failing **area + remedy** taken from the report lines (e.g.
  `provider FAIL provider config incomplete (AZURE_OPENAI_API_KEY)`) and do **NOT** declare success.
  Never assume "done": the reported state is the one `doctor` verified, never a presumed one.

## What NOT to do

- Do NOT print any secret value (screen or conversation log).
- Do NOT hand-fill `.sertor/.env`; always go through `sertor configure --set`.
- Do NOT run any mutating/download step without explicit confirmation.
- Do NOT import the core or call the `build_*` factories; orchestrate the vehicles only.
- Do NOT select a provider automatically; always propose and let the user confirm.
- Do NOT declare the setup "done" without a green `sertor-rag doctor`.
