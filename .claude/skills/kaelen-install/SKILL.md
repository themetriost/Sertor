---
name: kaelen-install
description: Installs, verifies, updates, rolls back or uninstalls a capability that another node publishes as a Kaelen package, in this repository, for the assistants the person chooses. Use it whenever someone asks to install a Kaelen capability or package from a repository at a commit or tag, to check (verify) one, to update one to a newer version, to remove (uninstall) one, to finish or undo an interrupted install, or to list what Kaelen installed here. Triggers on 'install the <node> capability', 'install this Kaelen package', 'install <capability> from <repository> at <tag>', 'update <capability>', 'uninstall <capability>', 'verify the installed capabilities', 'what did Kaelen install here', 'the install stopped half way'. Runs the package's own engine (with uv or with Python), always dry-runs first, asks consent file by file, and reminds the person to commit. Not for making this repository's own node installable: that is kaelen-authoring.
---

# Kaelen install: put another node's capability into this repository

A **capability** is what a node publishes: skills, agents, commands, hooks, instruction blocks, MCP
servers and support files, for one or more assistants. It travels as a **package** in the producer's git
repository, under `.kaelen/packages/<capability>/`, and the package carries its own copy of the Kaelen
engine. You run that engine to install the capability here, check it, update it or remove it, and you
report what it says.

## What the engine guarantees, and what rests on you

**Guaranteed by the engine** (you could not break it if you tried):

- nothing is written on a dry run;
- an existing file is never replaced or removed without its own `--authorise <path>`: without it the
  command is refused (install) or the file is kept (update, uninstall, `kept-modified`). One
  `--authorise` covers one file: every section and member the capability has in it, together;
- on install and update, an invalid signature and an unmet requirement are always refused; a downgrade,
  an unsigned package, an untrusted signer and broken dependents are refused unless their named flag is
  passed (on uninstall and verify an invalid signature is a finding, and the operation proceeds);
- what it writes is recorded, so verify, uninstall and rollback know exactly what is the capability's.

These hold when the engine runs without a terminal, as in an agent's shell. At a terminal it would ask the
consent questions itself; do not run it that way.

**Resting on you** (the engine cannot see the person):

- asking about **one file at a time** and turning each yes into exactly one `--authorise <path>`;
- passing an overriding flag (`--trust`, `--allow-unsigned`, `--break-dependents`, `--allow-downgrade`,
  `--live`) only on the person's explicit word for that flag;
- reporting refusals and findings as they are.

## Rules you always follow

- **Only the engine acts.** Never copy files into place, never edit or delete anything under `.kaelen/` or
  in a capability's folder `.<node>/kaelen/<capability>/`, never edit a section between Kaelen markers in a
  shared file, and never import the `kaelen` Python package. The engine verifies what it wrote against its
  record: a hand edit becomes a divergence the next operation asks about.
- **Read `--json`, not the text.** Decide from the exit code and the JSON outcome: `verdict`, `errors`,
  `findings`, `conflicts`, `divergences`, `settings`. Name every error and finding by its `rule` and
  `message`; when the outcome carries a top-level `error`, also give its `hint`. The text output is for
  people and may change wording; the JSON names are stable.
- **Dry run first.** Every install, update, uninstall and rollback runs with `--dry-run --json` first; show
  the plan, write only after the person confirms. The plan is the only moment the person can still decide.
  The one exception is completing an interrupted operation, which has no dry run (step 10).
- **Consent is per file**, and why: a replaced file belongs to the capability from then on, so **uninstall
  will remove it**, and Kaelen does not keep its old content (git does). A person who says "yes to all"
  has not seen what each file holds: show the list, say this once, and still ask one by one. Never retry a
  refusal with more consent than was given.
- **Report refusals as refusals.** Do not soften, summarise away or route around them.
- **Pin the source.** A commit or a tag, never a branch: a branch moves, and the same command would
  install something else tomorrow.
- **Secrets are the person's.** Never write, print or ask for the value of a secret setting in a command.

## 1. The source and the engine

You need the producer's **repository address**, a **commit or tag**, and the **capability** name. For a
capability already installed, read them from step 2 (`origin`) and ask the person only to confirm, or to
give them when `origin` is unknown.

**A tag** is resolved to its full commit before anything else:

```
git ls-remote <repository> refs/tags/<tag> "refs/tags/<tag>^{}"
```

If a line ends in `^{}` the tag is annotated: its commit is the hash on that line. Otherwise the commit is
the hash of the only line. No line: the tag does not exist, so stop and say so. Use the **40-character
commit** from then on, in the launch and in `--origin`, and tell the person which commit the tag names.
A tag can be moved; the commit cannot.

**A branch**: ask for a commit or a tag, or offer to look up the branch's current commit the same way
(`git ls-remote <repository> refs/heads/<branch>`) and confirm it with the person.

Pick the route, say which one you use, and call it `KAELEN` below:

- **uv** (if `uv --version` succeeds), which needs no clone:
  ```
  uvx --from "git+<repository>@<commit>#subdirectory=.kaelen/packages/<capability>" kaelen
  ```
  uv records where the package came from, so the engine deduces `origin` itself.
- **Python only**: a checkout of the repository at that commit, if the person agrees and git can reach it:
  clone it **outside** this repository (a temporary folder), then `git -C <checkout> checkout <commit>`;
  a clone inside ROOT would land in the person's repository. An interpreter of version 3.11 or later; try
  `python3`, then `python`, then `py -3`:
  ```
  <python> <checkout>/.kaelen/packages/<capability>/run.py
  ```
  Pass `--origin git+<repository>@<commit>#subdirectory=.kaelen/packages/<capability>` on install and
  update, with the full commit (a tag there is recorded as unresolved).

Check the route with `KAELEN --version`: exit 0 and `kaelen <version>`. `ROOT` is the root of this
repository; **always pass `--host ROOT`**, because the engine's default host is the one holding the
package, which under uvx is uv's cache.

## 2. What is already here

```
KAELEN installed --host ROOT --json
```

Without any package, the repository's main Kaelen gives the same list:
`<python> .kaelen/engine/run.py installed --host ROOT --json`.

Each entry of `capabilities` has `version`, `targets`, `origin` (`repository`, `commit`, `subdirectory`,
`how`: `deduced`, `declared` or `unknown`, and `resolved`), `signature`, `requires`, `required_by` and
`groups`. With `resolved` false the recorded commit is not a full commit: it cannot pin anything, and
`verify --provenance` cannot check it; ask the person for the commit. It decides the verb:

| Found for this capability | Verb |
|---|---|
| nothing | install (step 4) |
| the same version, the same targets | nothing to install: the engine answers `already-installed`; offer verify |
| the same version, a new target | install, with the new target (the recorded ones stay) |
| another version | update (step 7) from the package at the new commit |
| `state` `unreadable` | stop: report `reason`; the registry needs a look before any write |

An entry with `layout` `old` sits where engines up to 0.11.0 put it; its next update moves it into its own
folder and says so (`older-engines-blind`). Tell the person.

## 3. Targets

Ask which assistants to install for: `claude-code`, `github-copilot`, `codex`. Help the person choose,
do not choose for them: say which assistants this repository already uses (their instruction files and
folders are there), and which `targets` the installed capabilities have. Only targets the package declares
are accepted (`target-not-declared` otherwise). After the dry run, two findings bear on the choice:
`unsupported-on-target` (an item this assistant cannot hold; the rest still installs) and `double-loading`
(one assistant also reads where another assistant's copy is placed, so it may see an item twice).

## 4. Dry run, then read the plan

```
KAELEN install --host ROOT --target <t> [--target <t> ...] --dry-run --json
```

Report `changes`, every finding and every entry of `settings`. Then go through the plan. Each of these
has a way forward and becomes a question to the person; only what is left stops.

**The plan comes in rounds.** The engine stops at the first gate that refuses (requirements, then
dependents, then signature, then downgrade, then conflicts), and a dry run refused for conflicts has not
computed `changes` yet. So after each answer (a yes, `--trust`, `--with`…), run the dry run again with
the same flags plus the new ones, until it exits 0. Show **that** plan, with its `changes`, `runtime` and
findings, and write only after the person confirms it.

| In the outcome | What it means | The question, or what you do |
|---|---|---|
| `conflicts` (rule `conflict`, exit 1) | existing files the capability would write | step 5, one file at a time |
| `divergences` (update, uninstall) | installed files edited since | step 5; without a yes the file is kept (`kept-modified`, exit 0) |
| `groups` | `chosen`, `included`, `left_out` | which optional groups: `--with <group>`, `--without <group>`; remembered for later updates |
| `requirements` | capabilities this one needs | `requirement-missing`, `requirement-version`, `requirement-groups`: refused with no override; report the entry's `why` and `source`, and the error's `message`, which carries the remedy (install or update that capability, or add its groups), and do that first. `requirement-unreadable`: that capability's registry is broken; verify it |
| `dependent-needs-it` | installed capabilities that need this one | only on explicit word, `--break-dependents`; they stay broken and verify reports them |
| `signer-untrusted` | valid signature, signer not trusted here | show signer and key; `--trust <signer>` for this operation only, on explicit word. For good: `trust add --host ROOT --principal <signer> --package <package folder>` with the main Kaelen (the outcome's `package` names the folder; or `--key <public key file>`), dry run first (`--dry-run --json`), on the person's explicit word, then commit `.kaelen/trust/allowed_signers` |
| `signature-missing` | unsigned where a signature is expected | `--allow-unsigned`, on explicit word only |
| `signature-invalid` | altered, or signed for another package | install and update: stop, no override. Uninstall: a finding; report it, the removal proceeds |
| `keygen-unavailable` | `ssh-keygen` (OpenSSH) is needed | say so |
| `previous` | what an older installer of this node left | `adopted`, `adopted-past-version`, `retired`: nothing to ask. `kept` (changed since): ask per file as in step 5; with a yes it becomes `retired-with-consent` or `adopted-with-consent`; without, a retire stays `kept` and an adopt is `refused`, a conflict that stops the operation |
| `git-line-present`, `git-later-prevails` | lines added to `.gitignore` or `.gitattributes` | notes: the line was already there, or the host's earlier line loses to the section; show them |
| `direct-writer`, `orphan-contribution` | shared files and older engines | notes: the next update of that capability ends it; the leftover goes at the next operation |
| `runtime` | the capability's own environment | `state` (`would-build`, `built`, `kept`) and `tool` (`uv`, or `pip`); `runtime-python` refused: say which Python versions it needs |
| `provenance` | `origin`, `signature`, `signer`, `trusted` | report them; `origin` `unknown` means nothing says where the package came from |
| `other-version-installed` | another version is installed | use update (step 7) |
| `deposited-package` | you ran the copy kept on this host | install and update need the producer's package (step 1) |
| `contribution-unsupported` | this repository's main Kaelen is too old for the shared-file change | `self-update --host ROOT` with this package's engine, dry run first; then again |
| `main-unavailable` | the main Kaelen could not be run | nothing was written; check `.kaelen/engine/run.py` and the Python that runs it |

Any other error: name it with its `message` and `hint`, and stop.

## 5. Consent

Group the entries of `conflicts` or `divergences` by `path`: one file can hold several, one per section or
JSON member (`address`). For each file, show every entry in it with what was `found`:

- `identical`: the bytes already match what Kaelen would write; replacing changes nothing.
- `different`: the person's current content will be replaced.
- For a divergence on a folder (a skill is one), `files` lists each file inside with `modified`, `added` or
  `removed`, so
  the person sees exactly what changed; `files_unknown` means the engine could not list them (its copy of
  what was installed is missing): say so and show the folder.

Ask once per file: "May `<path>` be replaced?", listing what it covers, and write down each yes. A yes
covers every entry of that file; there is no yes to one section and no to another, so a person who wants
to keep any of them answers no. Then say: a file without a yes stays as it is (the install is refused
again, an update or uninstall keeps it), and a replaced file will be removed by uninstall. That is why the
person commits before writing.

## 6. Write and report

When the last dry run exits 0 and the person has confirmed its plan, run the same command without
`--dry-run`, with one `--authorise <path>` per yes and the flags the person agreed to. On exit 0 report:
what was installed per target, every finding, the files replaced, and every setting with `state` `missing`
by name and description, so the person knows what to configure. Then remind
the person to **commit**, including the capability's folder `.<node>/kaelen/<capability>/`, and offer
verify.

## 7. Update

Run the package at the **newer** commit: the repository and subdirectory come from `origin` (step 2); the
new tag or commit comes from the person, resolved as in step 1.

```
KAELEN update --host ROOT --dry-run --json
```

Then as in steps 4 to 6. Divergences do not refuse an update: without a yes the file is kept and reported
as `kept-modified`, with exit 0. A refusal because the package is older than what is installed is a
downgrade: `--allow-downgrade` only if the person asks to go back.

## 8. Verify

```
KAELEN verify --host ROOT --json
```

- Exit `0`: verified. Always say what `not_checked` lists (for example, whether each assistant loads it).
- Exit `2`: something differs. Read each entry of `divergences` by its `state`:
  - `modified` or `absent`: an installed item changed or is gone (with `files` for a folder); offer an
    update with consent, or leave it to the person;
  - `form` or `command`: a defect of the producer (see below), not something an update here fixes;
  - `not-running` (with `--live`): an MCP server did not start;
  - runtime `divergent` or `absent`: offer install again, which rebuilds the environment;
  - `invalid`: the deposited copy's signature does not check;
  - and the findings: `requirement-unsatisfied` (a capability this one needs is missing or at the wrong
    version), provenance `differs` or `mismatch`.
- Exit `4`: not installed here.

Each item also carries `form`: with `state` `fails`, `failed` lists the checks the item fails (for example
`frontmatter: missing description`), so the assistant would ignore it although it is installed. Hook items
carry `command`: with `state` `unresolved`, `missing` lists the interpreter or script not found. Report both
as defects for the producer.

**Every capability at once**, without a package: `<python> .kaelen/engine/run.py verify --host ROOT --json`
(`--capability NAME` for one). Each capability is verified by the engine in its own folder; the document
(`kaelen.host-verify/1`) has one entry per capability and an overall `verdict`; the exit is the worst one.
An entry `not-verifiable` carries `reason` and `remedy`: report both (it makes the exit 66). The verdict
`nothing-installed` means Kaelen installed nothing here.

**Running MCP servers**: `KAELEN verify --host ROOT --live --json` starts them on this machine, so only with
the person's consent. Report each entry of `live`: `running` with `version` and number of `tools`,
`failed` with its `cause`, or `not-checked` with its `cause` (not a pass).

**Provenance**: `KAELEN verify --host ROOT --provenance --json` (or the copy in the capability's folder)
fetches the recorded commit (online, needs git) and compares it with the copy kept in the capability's
folder: `confirmed`; `differs`, naming each file; `mismatch`, when the
commit holds another package; `not-checked` with its `cause` and exit 5, never a pass. Findings
`signer-untrusted` (uninstall stays possible, an update needs a trusted signer) and `provenance-unknown`
(installed by an older engine) are reported as they are.

**An environment** (`runtime`): `matching` is fine; `divergent` lists `differences`, offer install again to
rebuild it; `absent` is normal on a fresh clone (the environment is never committed): offer install, which
builds it and changes nothing else.

## 9. Uninstall

```
KAELEN uninstall --host ROOT [--target <t> ...] --dry-run --json
```

With `--target`, only those assistants' items go; the rest stays installed. Report `changes`; divergences
go to step 5 (without a yes the file is kept). On confirmation run it without
`--dry-run`, then remind the person to commit.

**Without the producer.** The capability's folder holds a copy of its package, so uninstall, verify and
rollback also run from there, with no network:

```
<python> .<node>/kaelen/<capability>/package/run.py uninstall --host ROOT --dry-run --json
```

The copy removes itself last. Install and update always need the producer's package (`deposited-package`).

## 10. An interrupted operation

An outcome `incomplete` (exit 3) says in `incomplete` which operation stopped, how far it got, and in
`rollback` what is left:

- `possible`: offer the two ways out and let the person choose. **Complete it**: usually right for an
  update. It has **no dry run** (a dry run exits 3 again): the plan is `incomplete` itself (`operation`,
  `done` of `actions`). Show it, get confirmation, then run the same verb without `--dry-run`, with the
  exact same package (the same commit; another one exits 3 again). The consents given the first time still
  apply. **Roll it back**: the host goes back to exactly how it was, including files replaced with consent,
  usually right for an install that failed half way:
  ```
  KAELEN rollback --host ROOT --capability <capability> --dry-run --json
  ```
  Report `restored`; a `divergences` entry (`path`, `state`, `digest_found`) is a location changed after the
  interruption: ask per path as in step 5.
- `not-possible` (`cannot-roll-back`): started by an older engine, or its copies are gone. Only completing.
- `not-needed` (error `release-failed`): the operation itself is done; only the main
  Kaelen's last part is left, and the next operation on this host finishes it. Nothing to do but say so.
- `rolling_back: true`: a rollback was interrupted. Run rollback again; nothing else runs on that capability
  until it finishes.

Rollback also runs from the copy in the capability's folder. If the operation was replacing that copy, the
copy refuses (`running-engine-in-plan`) or is missing: run the same rollback with the main Kaelen,
`<python> .kaelen/engine/run.py rollback --host ROOT --capability <capability> --dry-run --json`, then the
same
without `--dry-run` on confirmation.

## Exit codes

| Exit | Meaning | Your action |
|---|---|---|
| 0 | Done, a dry run, or `already-installed`. Update and uninstall also exit 0 when they keep a modified file (`kept-modified`). | Report the findings. |
| 1 | Refused, nothing written. | Read the plan (step 4): conflicts go to consent; refusals with a flag become a question; the rest stops. |
| 2 | Verify: something is modified or absent. | Step 8. |
| 3 | Interrupted, or cannot be rolled back. | Step 10. Act only on confirmation. |
| 4 | Verify: not installed. | Report it. |
| 5 | `verify --provenance` could not check. | Report the cause; it is not a pass. |
| 64 | Wrong arguments. | Fix the command from `--help`; never guess flags. |
| 66 | The package or the registry cannot be trusted or read; in verify of every capability, an entry is `not-verifiable`. | Stop and report `reason` and `remedy` where given. Do not use another copy of the package without telling the person. |
| 69 | Python older than 3.11. | Report the version printed. |
| 70 | An engine defect. | Stop and report the output as a defect of the engine. |

## Worked example: install from a tag, one conflict

The person asks: "install `notes` from `https://example.org/acme/acme-node` at `v1.2.0`, for Claude Code
and Codex."

1. `git ls-remote https://example.org/acme/acme-node refs/tags/v1.2.0 "refs/tags/v1.2.0^{}"` prints two
   lines; the one ending in `^{}` starts with `4f9c…e21a` (40 characters). You say: "v1.2.0 is commit
   4f9c…e21a; I install from that."
2. `uv --version` works: `KAELEN` is
   `uvx --from "git+https://example.org/acme/acme-node@4f9c…e21a#subdirectory=.kaelen/packages/notes" kaelen`.
   `KAELEN --version` prints `kaelen 0.16.2`.
3. `KAELEN installed --host ROOT --json`: no `notes` entry, so install.
4. `KAELEN install --host ROOT --target claude-code --target codex --dry-run --json` exits 1. The only error
   has rule `conflict`; `conflicts` has one entry: the shared instructions file at the root (call it
   `<instructions>`), address `notes`, found `different` (an older hand-made section with the same
   marker). `settings` lists `NOTES_DIR` with `state` `missing`.
5. You ask: "May `<instructions>` be replaced where it holds the `notes` section? Your current text there
   will be replaced, and uninstall will remove the section." The person says yes.
6. The dry run again, with `--authorise <instructions>`, exits 0. Now `changes` lists the skill for both
   assistants and the section; you show that plan and the person confirms.
7. `KAELEN install --host ROOT --target claude-code --target codex --authorise <instructions> --json` exits 0.
   You report the items per target, the replaced section, and that `NOTES_DIR` needs a value; you remind
   the person to commit, including `.acme/kaelen/notes/`, and offer verify.

## Failure modes: when it goes wrong

| Symptom | Cause | What to do |
|---|---|---|
| uvx cannot fetch the repository | network, a private repository, or a wrong address | say which; offer the Python route with a checkout the person can make |
| a write lands in a strange folder, or "not installed" right after install | `--host` omitted under uvx | always `--host ROOT`; on a stray write, check with verify and tell the person |
| `deposited-package` on install or update | you ran the copy in `.<node>/kaelen/<capability>/package/` | run the producer's package (step 1) |
| `python3` opens a store page or prints nothing (Windows) | a placeholder interpreter | try `python`, then `py -3`; report what you used |
| exit 69 | Python older than 3.11 | report the version; uv brings its own Python |
| the commit a tag names changed since last time | the tag was moved | say so; ask which commit the person means before going on |
| `contribution-unsupported` | an old main Kaelen | `self-update` from this package's engine, dry run first |
| exit 70 | engine defect | stop and give the output to the person for the producer |
