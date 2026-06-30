---
name: guided-setup
description: "Guides the user from an unconfigured repo to a verified Sertor RAG (a green
  `sertor-rag doctor`). Use it whenever someone wants to get Sertor working. Triggers on
  'set up Sertor', 'install Sertor', 'configure the RAG', 'get the RAG running', 'why is the
  RAG not working', or any first-time setup/onboarding request. Detects current state,
  recommends an embedding provider from context (with confirmation), fills `.env` securely (never
  printing secrets), announces the one-time GloVe download, and verifies fail-loud via `doctor`,
  orchestrating only the deterministic vehicles (`sertor install`, `sertor configure --set`,
  `sertor-rag doctor`/`index`). Read-only checks run freely; every host mutation/download runs only
  after explicit confirmation. It never reimplements a command and never imports the core."
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

- **No execution of core logic, no library import.** This skill does not reimplement any command and
  does not import the core. Every access to Sertor goes through a vehicle — the deterministic CLI
  commands (or MCP). Never import the library, never call the `build_*` factories. Access Sertor
  through a vehicle only.
- **The vehicles you orchestrate** (by command name, host-agnostic):
  - `uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor install rag --assistant <host>`
    — deposits the RAG assets and scaffolds `.sertor/.env` (the installer runs ephemerally via `uvx`).
  - `uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor install wiki --assistant <host>`
    — deposits the wiki tooling/assets (same ephemeral `uvx` installer).
  - `uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor-flow" sertor-flow install --assistant <host>`
    — deposits the governance / SDLC apparatus (a separate package; same ephemeral `uvx` form).
  - `uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor configure --set KEY=VALUE`
    — fills `.sertor/.env` (CI-safe wizard; secrets via a secure prompt).
  - `uv run --project .sertor sertor-rag doctor` (and `… sertor-rag doctor --json`) — the
    deterministic health check (the four areas `config`/`provider`/`index`/`mcp` with pass/warn/fail,
    stable JSON schema, exit-code gate).
  - `uv run --project .sertor sertor-rag index .` — the first index (may trigger the one-time GloVe
    download).
- You **orchestrate** these commands; you do not alter or replace their behaviour. Do not paste inline
  shell/Python that replicates what `install`/`configure`/`doctor`/`index` already do.
- **`--assistant <host>` is required on every install.** `<host>` is the assistant you are running
  as — see "Step 0 — Detect the host" below. Always pass it **explicitly** to `sertor install rag`,
  `sertor install wiki` and `sertor-flow install`; **never** rely on the installer's default (the
  default lays down the wrong host layout when you are not that default host).

## How to invoke

The runtime CLIs you orchestrate (`sertor-rag`, `sertor-wiki-tools`) live in the project's
`.sertor/.venv` and are not on `PATH`, so the steps below route every call through
`uv run --project .sertor`. For the full invocation details — the two levels (runtime via `uv run`,
installer via `uvx`), the venv fallback, and the Windows setup notes — see `sertor-cli-reference.md`
(the reference ships with this capability under `.sertor/`).

## Consent gate (read-only is free; mutation needs an explicit "yes")

- **Read-only checks run freely, no confirmation:** running `uv run --project .sertor sertor-rag
  doctor`, inspecting whether `.sertor/.env` exists, reading which keys are present. These never mutate
  the host.
- **Every step that mutates the host or downloads runs only after explicit confirmation:**
  `sertor install rag`, `sertor configure --set`, and the first
  `uv run --project .sertor sertor-rag index .` (including the GloVe download). Propose the step,
  explain what it will do, and wait for an explicit "yes" before running it.
- If the user does not confirm, do not run the step. Never auto-mutate or auto-download.

## Step 0 — Detect the host (read-only) — pick `--assistant <host>`

Before any install, determine which assistant you are running as: that value is the `<host>` you pass
to **every** install command (`sertor install rag`, `sertor install wiki`, `sertor-flow install`). The
supported values are `claude` and `copilot-cli`.

- **Primary signal:** you ARE the host agent running this skill — pick the value that names the
  assistant you are executing inside. If you run on the GitHub Copilot CLI host, use `copilot-cli`;
  otherwise use `claude`.
- **Deterministic fallback (read-only, from the repo's files)** when the primary signal is unclear:
  - a GitHub-Copilot host-instruction file is present (`.github/copilot-instructions.md`) ⇒
    `copilot-cli`;
  - otherwise, a host project-instruction file / per-host config directory is present (the
    capitalized project-instruction markdown at the repo root, or the per-host config folder) ⇒
    `claude`.
- If neither the primary signal nor the fallback resolves the host, **ask the user** which assistant
  this is before installing — do not guess and do not fall back to the installer default.

Carry the resolved `<host>` through the whole flow: substitute it into the `--assistant <host>`
placeholder in Steps 3 and (for wiki/flow) below.

## Step 1 — Detect state (read-only)

Run `uv run --project .sertor sertor-rag doctor --json` and read the four areas
(`config`/`provider`/`index`/`mcp`) of the `doctor` report. Also inspect read-only whether
`.sertor/.env` exists and which keys it already holds. Determine what is missing.

- **All four areas green** → the RAG is already configured and verified: say so, do not re-scaffold,
  and stop (idempotence — re-running on a healthy host detects and verifies, it does not rebuild).
- **Partial** → conduct only the missing steps below; do not repeat steps already complete, and do not
  duplicate artifacts already present.

## Step 2 — Choose provider (minimal heuristic + confirm)

Read three signals via vehicle/file (never the core), then **propose** a provider with a rationale and
let the user decide — never select one automatically:

1. **Cloud credentials present?** — from `uv run --project .sertor sertor-rag doctor --json`
   (`config`/`provider` areas: missing `AZURE_OPENAI_*` keys mean no cloud creds), or by a read-only
   look at `.sertor/.env` / the environment for `AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_API_KEY`.
2. **Host airgapped / offline?** — a conversational signal (the user states it), or
   `uv run --project .sertor sertor-rag doctor --online` reporting the provider `unreachable`. Do not
   probe the network yourself.
3. **Is natural-language semantics over the docs needed?** — ask the user (is the corpus rich in
   documentation / NL?).

Recommendation rules (propose with rationale, never impose):

- cloud creds **absent** OR airgapped → recommend **local**: `glove` if NL semantics is needed (the
  core's local default), `hash` for the deterministic / strict-airgapped floor.
- cloud creds **present** + NL semantics needed → may propose **cloud** (Azure) with the rationale
  (semantic quality), or `glove` locally if the user prefers on-machine.
- in every case you propose with a rationale and the **user confirms**; there is no automatic
  selection.

The chosen provider is written to `.sertor/.env` in Step 4 via
`uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor configure --set SERTOR_EMBED_PROVIDER=<glove|hash|azure|ollama>`.

## Step 3 — Install (on confirm; always with `--assistant <host>`)

Use the `<host>` resolved in Step 0 and pass `--assistant <host>` **explicitly** on every install
command below — never rely on the default.

- **RAG** (the core capability of this flow): if the RAG capability is missing (the `mcp`/`config`
  areas signal it is not installed), propose
  `uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor install rag --assistant <host>`.
  On explicit confirmation, run it. If the install is already present, skip this step.
- **Wiki** (optional, on the user's request): the wiki tooling/assets install via
  `uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor install wiki --assistant <host>`.
  Propose it only if the user wants the wiki; confirm before running; skip if already present.
- **Governance / flow** (optional, on the user's request): the SDLC apparatus ships in a separate
  package and installs via
  `uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor-flow" sertor-flow install --assistant <host>`.
  Propose it only if the user wants the governance/SDLC layer; confirm before running; skip if
  already present.

For all three: install ≠ run (they only deposit assets), and each mutates the host — so each runs
**only after explicit confirmation** (the consent gate above).

## Step 4 — Configure (on confirm; secrets via the secure path)

Fill `.sertor/.env` **only** via
`uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor configure --set KEY=VALUE`
(or the wizard's secure prompt).

- For **secrets** (e.g. a cloud API key), use the wizard's secure `getpass` prompt and **never print
  the value** — not to the screen, not into the conversation log.
- If a secret is **already present** in `.sertor/.env`, do not re-ask for it and do not expose it.
- Never hand-edit `.sertor/.env` directly; always go through `sertor configure --set`.

## Step 5 — Index (on confirm; announce the GloVe download)

If the chosen provider is `glove` and the model is **not** in cache, **announce** the one-time download
(~822 MB) **before** running the index, so the wait is expected and not a silent block. Then, on
confirmation, run `uv run --project .sertor sertor-rag index .`.

- If the GloVe model is already in cache, do not announce any download.
- When a download progress/ETA becomes available (a future deterministic capability), lean on it;
  until then the textual announcement is enough (honest degradation).

## Step 6 — Verify (fail-loud)

Run `uv run --project .sertor sertor-rag doctor` as the obligatory gate before declaring success:

- `doctor: PASS` (exit 0) → declare the setup **verified**, reporting the supporting outcome.
- **Not green** → expose the failing **area + remedy** taken from the report lines (e.g.
  `provider FAIL provider config incomplete (AZURE_OPENAI_API_KEY)`) and do **not** declare success.
  Never assume "done": the reported state is the one `doctor` verified, never a presumed one.
