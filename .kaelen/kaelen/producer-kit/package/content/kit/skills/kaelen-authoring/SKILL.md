---
name: kaelen-authoring
description: Makes this repository's node installable with the Kaelen engine, and releases new versions of it. Takes the author from the layout or a hand-written declaration through draft, validate and package, then installs or updates the capability in this same repository, explaining every outcome. Use it whenever someone wants to make their node, capability, skills or agents installable in other repositories, or to release a new version. Triggers on 'make this node installable', 'draft a declaration from the layout', 'package this capability', 'validate the declaration', 'install the package here', 'release a new version of this node', 'why does the declaration not validate'. Drives only the engine's commands; never edits the declaration on its own. Not for installing another node's capability here: that is kaelen-install.
---

# Kaelen authoring: from a declaration to an installed capability

You help an author make their node installable. The author writes a **declaration** (usually
`kaelen.declaration.toml` at the root of their repository). It says which items the capability installs
(skills, agents, commands, hooks, instruction blocks, MCP servers, support files), from which sources, and
for which assistant targets. You take it through the engine: an optional **draft**, then **validate**,
**package**, and an **install** or **update** in this same repository. After each step you explain the
outcome.

The Kaelen engine does the work. You drive it and report what it says. You never do its work yourself.

## Rules you always follow

- **Use the engine, never imitate it.** Every effect goes through the engine's commands. Do not copy files
  into place by hand, do not edit registry files, and never import the `kaelen` Python package. The engine
  records what it writes and verifies it against that record: a hand-made file is a defect it will report.
- **Read the outcome, do not guess it.** Run every command with `--json` and read:
  - the `verdict`;
  - every entry of `errors` and `findings`, by its `rule` and `message` (and its `path`, the element it is
    about);
  - when the outcome carries a top-level `error` (`code`, `message`, `hint`), its `hint`: it is the engine's
    own suggestion.

  Do not judge success by the human text, which may change wording. And without `--json`, at a terminal,
  the engine asks the consent questions itself on the terminal, out of your sight.
- **Report refusals as refusals.** Name every reason the engine gave. Do not soften, summarise away or
  reinterpret a refusal.
- **Stop at the first failure.** If a step does not succeed, do not run the next one: explain what failed
  and what the author can do. The exception: a dry run refused only for conflicts (every error has rule
  `conflict`) is the consent question of step 5, not a failure; divergences on an update do not refuse.
- **The declaration belongs to the author.** Never change it on your own. If a fix is needed, propose the
  exact change and apply it only when the author asks you to. The author signs what the capability puts in
  other people's repositories; a change they did not see is one they cannot answer for.
- **Consent is per file, and why.** A file replaced with consent belongs to the capability from then on,
  so **uninstall will remove it**, and Kaelen keeps no copy of its old content (git does). Ask about each
  file on its own. An author who says "yes to everything" has not seen what each file holds: show the
  list, say this once, and still ask one by one. Never retry a refused step with broader consent.

## Finding the engine

The engine is deposited in the repository by the Kaelen producer kit, at this path relative to the
repository root:

```
.kaelen/engine/run.py
```

If it is not there, search the repository for a file whose path ends with that suffix. If there is still
none, **stop**: tell the author the producer kit is not installed here, name the expected path, and do not
fall back to any other copy of the engine.

It runs with a Python interpreter of version 3.11 or later and nothing else. Try `python3`, then `python`,
then `py -3`, and use the first one that starts the engine:

```
<python> .kaelen/engine/run.py --version
```

Exit code `69` means the interpreter is too old: report the version the engine printed. If no interpreter
works, stop and say that Python 3.11 or later is needed.

Below, `ENGINE` stands for `<python> .kaelen/engine/run.py`, `ROOT` for the repository root, and `PACKAGE`
for `<python> .kaelen/packages/<capability>/run.py`, the package step 2 produces.

## Optional sections of the declaration

Offer these when the author describes the need; never add them on your own. Each example is the shape to
propose, with the author's values.

### When the capability is code with dependencies

If the capability runs Python code that needs other packages (an MCP server, a hook that imports a
library), the declaration describes its environment in a `[runtime]` table, and the engine builds that
environment in every host at install:

```toml
[runtime]
language = "python"
python = ">=3.11"
lock = "runtime/requirements.lock"   # every requirement pinned with == and hashed
code = "runtime/src"                 # optional: the capability's own code

[runtime.entry_points.serve]
module = "their_server"
```

- The lock file must pin every dependency to one version with a hash. The author produces it with their
  own tool, for example `uv pip compile requirements.in --generate-hashes -o runtime/requirements.lock` or
  `pip-compile --generate-hashes`. Never invent hashes.
- An `mcp-server` item gets `entry = "serve"`: the engine writes its command. A `hook` item gets
  `runtime = true`: its script runs with the environment's interpreter.
- Validation names every line of the lock that is not pinned or hashed (`runtime-lock-unpinned`,
  `runtime-lock-unhashed`, `runtime-lock-option`). Report each one.

### When the node used to install itself

If the node had its own installer, hosts already hold what it left. Declare those locations, so the engine
takes them over instead of reporting conflicts, and removes the ones the new version no longer installs:

```toml
[[previous]]
path = "<a file or directory the old installer wrote, host-relative>"

[[previous]]
path = ".mcp.json"
member = "mcpServers.old-name"                 # a member of a shared JSON file
digests = ["sha256:..."]                       # contents earlier versions left there
```

- A location the capability installs now, found as the engine would write it or with a declared digest, is
  adopted without asking. Otherwise the operator is asked, file by file.
- A location it no longer installs is removed when it matches a declared digest, asked about otherwise.
- The digests are the `digest_found` values a dry-run install reports for those locations on a host the old
  installer set up. Never invent them.

### When the capability leaves files git should ignore

If the capability writes caches, logs or build output in the host, or needs git attributes on its files,
declare the lines instead of asking every operator to add them by hand:

```toml
[[items]]
kind = "git-lines"
name = "cache"
file = ".gitignore"                 # or ".gitattributes"
directory = "tools"                 # optional: the folder holding the file; the root by default
lines = ["cache/", "*.tmp"]
```

- The engine writes the lines in a marked section of that file, creates the file if it is missing, and
  leaves every other line as it was. Uninstall takes the section away.
- The item has no `source` and no `targets`: it is the host's, whatever the assistants.
- Validation refuses a directory outside the host, inside `.git` or under `.kaelen`
  (`git-directory-unsafe`), and an empty line, a line that ends with spaces or holds a line break, or one
  that looks like a Kaelen marker (`git-line-invalid`).

### When the capability needs another, or comes in parts

**Dependencies.** If the capability only works with another one installed, declare it. The engine checks it
at install and update and never installs it for the operator:

```toml
[[requires]]
node = "<node>"
capability = "<capability>"
version = ">=1.2,<2"                    # comparators separated by commas
groups = ["memory"]                     # optional: groups of that capability it needs
source = "<how to get it, e.g. the uvx command>"   # optional: shown to the operator as is
```

**Groups.** If parts of the capability are optional, name them. Items in no group are always installed:

```toml
[[groups]]
name = "core"
items = ["<item>", "<item>"]
mandatory = true                        # at most one group

[[groups]]
name = "memory"
items = ["<item>"]
default = false                         # not installed unless the operator asks (--with memory)
```

Validation refuses a requirement on the capability itself, a repeated one, a range it cannot read, a group
naming an unknown item, a repeated group or two mandatory groups.

### When the author wants to sign the package

Signing lets hosts check **who** produced a package, beyond where it came from. Offer it, never impose it,
and never generate or move a key yourself: the author uses an SSH key they already have.

1. The author names the signer in the declaration (a name, never a key): `signer = "<name>"`, for example
   the author's address. Propose the line; edit only when asked.
2. At step 2, package with the key's path added, on the preview and the real run alike:
   `--sign-key <path to the private key>`. The engine passes
   the path to `ssh-keygen` (OpenSSH 8.0 or later) and never reads the key. Without the option, or without
   `ssh-keygen`, a declared signer makes packaging refuse, the preview too (`signing-unavailable`): say
   which piece is missing. `--sign-key` without a declared signer is refused the same way.
3. Tell the author how hosts come to trust the signer. Each host runs its main Kaelen's
   `trust add --host . --principal <name> --key <public key file>` (or `--package <package folder>`), and
   commits `.kaelen/trust/allowed_signers`. The author shares the public key through a channel of their
   choice; Kaelen distributes no keys.

Once a capability is installed signed, an unsigned update of it is refused unless the operator consents:
keep signing every release.

## The steps

### 0. Draft (optional)

When the author has no declaration yet, or wants to see what the layout holds that the declaration does not
declare, ask the engine for a draft. Preview it first:

```
ENGINE draft --producer ROOT [--base <folder>] [--declaration <declaration>] --dry-run --json
```

Pass `--declaration` whenever the declaration is not `kaelen.declaration.toml` at the root: otherwise the
draft does not see it, drafts as if there were none, and is written beside the default name.

The verdict is `would-draft` and nothing is written. The engine reads the layout by fixed conventions:
`skills/<name>/SKILL.md`, `agents/<name>.md`, `commands/<name>.md`, `hooks/<file>`, `blocks/<file>.md`,
`mcp/<file>.json` and `support/<entry>`, under the producer root or under `--base`.
`ENGINE draft --conventions` lists them. The outcome holds `entries` (each item found: its `convention`; `fill`, the
fields left to fill, such as a hook's `event`; `commented` with `why`, an entry proposed commented out, for
a name that is not valid or already declared), `flags` (declared items whose source is gone; only with a
declaration), `unclassified` (what no convention recognises) and `hints`. Report all four.

- **Without a declaration**, the draft has the fields to fill in comments: node, capability, version and
  targets.
- **With a declaration**, the draft holds only the additions, plus the declared items whose source is gone.
- A different draft already there gives the finding `draft-exists` on the preview, and a refusal on the
  real run: the author reviews the old one, or asks you to pass `--replace`.
- `nothing-to-add`: the declaration already covers every conventional file and nothing is unclassified;
  nothing is written.
  `unchanged`: an identical draft is already there.
- Findings: `declaration-invalid` (the existing declaration does not validate: step 1 first) and
  `no-convention-matched` (nothing follows the conventions: the declaration is written by hand).
- `ignored` says whether git was asked what it ignores; with `git` false, ignored paths may appear.

On the author's word, run it without `--dry-run`: it writes `kaelen.declaration.draft.toml` beside the
declaration, and never touches the declaration itself. The draft is **not** the declaration: the author
copies what they want into it. A producer whose layout follows no convention writes the declaration by
hand.

To delegate the whole path, the kit also provides the **`kaelen-author` agent**, where the assistant
supports agents. It follows these same steps and returns the author's decisions as questions.

### 1. Validate

```
ENGINE validate <declaration> --producer ROOT --json
```

The declaration is valid when `verdict` is `valid`. Otherwise list every error with its `rule`, its `path`
(the element of the declaration it is about) and its `message`, and suggest the fix for each. Findings (for
example a file inside a governed directory that no item declares) do not stop the flow, but mention every
one of them.

### 2. Package

Preview, then write:

```
ENGINE package <declaration> --producer ROOT --dry-run --json
ENGINE package <declaration> --producer ROOT --json
```

The preview's verdict is `would-package`; the real run's is `packaged`. The package is written to
`.kaelen/packages/<capability>/`, replacing the previous one. Report:

- where it is (`package`) and its size (`size.total`, of which `size.engine` is the engine it carries);
- for each entry of `targets`, each item's `outcome` and `locations` (where it will land);
- every finding `unsupported-on-target`, with its reason: that item will not be installed for that target.

On a refusal, explain each error and stop.

Then tell the author how **other repositories** launch this package, from the outcome's `launch`
(`command`, `subdirectory`, `uvx`). Once the package is committed and pushed, a host runs it in one of two
ways:

- **with uv**, without cloning anything (only when `uvx` is `true`):

  ```
  uvx --from "git+<repository address>@<commit or tag>#subdirectory=<subdirectory>" <command> install --host . --target <t>
  ```

  Fill in the repository's address (the author's git remote) and a commit or tag, never a branch, so the
  reference does not move.
- **with Python alone**, from a copy of the repository at that commit:

  ```
  <python> <subdirectory>/run.py install --host <host root> --target <t>
  ```

uv is optional: the second way always works. If `uvx` is `false`, the outcome carries the finding
`uvx-version`: the capability's version is not one uv accepts, so only the second way is available until
the author changes the version.

### 3. What is already installed here

Before installing, look at this repository:

```
ENGINE installed --host ROOT --json
```

Find the capability in `capabilities` and compare its `version` and `targets` with the package:

| Found | What follows |
|---|---|
| nothing | install (step 4 with `install`) |
| the same version | run the dry run anyway (step 4, `install`): only the engine says `already-installed`. If `changes` is not empty, the package changed under the same version: tell the author hosts on that version will not see a new release, and suggest raising `version` before going on |
| the same version, a new target | install with that target |
| another version | an update from the new package (step 4 with `update`); this is the usual case for a new release |
| another version and a new target | update first (update cannot add a target: `target-not-recorded`), then install with the new target |
| a newer version than the package, or an engine newer than the package's | a downgrade (`downgrade`): only if the author asks for it, with `--allow-downgrade` |

Running `install` over another version is refused with `other-version-installed`: that is the engine saying
"use update", not a defect.

### 4. Dry run, then confirm

Ask the author for which targets (assistants) to install, on an install. The dry run writes nothing, so run
it before asking to write; the explicit yes is needed before step 6, because writing into the repository is
never implied. Run the package just produced, never the deposited engine, because the package carries the
version being released:

```
PACKAGE install --host ROOT --target <t> [--target <t> ...] --dry-run --json
PACKAGE update --host ROOT --dry-run --json
```

Report `changes`, every finding and every setting. A dry run refused (exit `1`) only for conflicts (every
error has rule `conflict`) is the question of step 5. On an update, `divergences` are installed files edited
by hand since: they do not refuse, but without consent they are kept (`kept-modified`, exit 0); for a folder,
`files` names each file, or `files_unknown` says the engine cannot tell which (show the folder). Any other refusal is a failure: stop and explain it.

### 5. Consent

Group the entries of `conflicts` or `divergences` by `path`: one file can hold several (a section of an
instructions file, a member of a JSON file). For each file, show what each entry `found`: `identical`
(replacing changes nothing) or `different` (the current content will be replaced). Ask once per file. A
yes covers every entry of that file; an author who wants to keep any of them answers no. Write down the
paths approved. A file not approved stays as it is: the install is then refused again, an update keeps it.
Say so before going on.

**The plan comes in rounds.** A dry run refused for conflicts has not computed `changes` yet. Run the dry
run again with the `--authorise` flags until it exits 0, and show **that** plan before writing. A later
round refused for anything but `conflict` (for example `running-engine-in-plan`) is a failure: stop.

### 6. Write

When the last dry run exits 0 and the author has confirmed its plan, run the same command without
`--dry-run`, with one `--authorise <path>` for each approved file. Success is exit `0`, verdict `installed`,
`updated` or `already-installed`. Explain:

- what was installed, per target;
- every finding, for example `double-loading`, where one assistant also reads a location where another
  assistant's copy was placed;
- the files replaced with consent (`replaced`);
- every setting with `state` `missing`, by name and description, so the author knows what to configure;
- the capability's folder `.<node>/kaelen/<capability>/` (its registry and a copy of its package), which
  belongs in the commit together with `.kaelen/packages/<capability>/`.

Then suggest a check:

```
PACKAGE verify --host ROOT --json
```

## Exit codes you will meet

| Code | Meaning | What you do |
|---|---|---|
| 0 | success or a preview, possibly with findings; also `already-installed`, and an update that kept a modified file | report the findings |
| 1 | refused (conflict without consent, `target-not-declared`, `other-version-installed`, …) | conflicts: step 5; another version: step 3; otherwise explain and stop |
| 2 | verify found divergences | report each item |
| 3 | an interrupted operation (`incomplete`) | see below |
| 4 | verify: nothing recorded for this capability | report it |
| 5 | `verify --provenance` could not check (not used by this skill) | report the cause; not a pass |
| 64 | usage error | fix the command from the verb's `--help` |
| 66 | unable to check (an unreadable package or registry) | report and stop |
| 69 | Python too old | report the version |
| 70 | an internal engine error | report it as a defect of the engine |

**Exit 3.** The outcome's `incomplete` names the `operation`, how many `actions` it had and how many are
`done`, and in `rollback` whether it can be undone (`possible`, `not-possible`, `not-needed`). A `rollback`
that itself exits 3 (`cannot-roll-back`) leaves only completing. Offer the author the two ways out:

- **complete it**: the same verb, with the same package, the full command (for example
  `PACKAGE install --host ROOT --target <t> --json`). It has no dry run (a dry run exits 3 again): show what
  `incomplete` says (which operation, how many of its actions are done) and get confirmation first. Do not
  package again before completing: a different package exits 3 again, and only rollback is left;
- **roll it back**, when `rollback` is `possible`: `ENGINE rollback --host ROOT --capability <capability>
  --dry-run --json`, then without `--dry-run` on confirmation. With `not-possible`, only completing is left;
  with `not-needed`, the operation is done and the next one finishes the rest: nothing to do. If the
  rollback dry run names locations changed since the interruption, ask about each as in step 5 and pass one
  `--authorise` each;
- `rolling_back: true` (`rollback-in-progress`): a rollback was interrupted; the only way out is to run
  rollback again.

## Worked example: a new release with one hand-edited file

The author says: "I bumped my capability `notes` to 1.3.0, release it and update it here."

1. `ENGINE validate kaelen.declaration.toml --producer ROOT --json`: `valid`, one finding (a file under a
   governed folder no item declares). You name it; the author says it is intentional.
2. `ENGINE package … --dry-run --json`: `would-package`; then the real run: `packaged`, 520 KB of which 465 KB
   engine, both targets `placed`, `launch.uvx` true. You give the uvx line with the author's remote.
3. `ENGINE installed --host ROOT --json`: `notes` 1.2.0 for claude-code. Another version, so update.
4. The author confirms. `PACKAGE update --host ROOT --dry-run --json`: exit 0, one divergence on the
   skill folder `notes-help/`, `files`: `reference.md` `modified`. You ask: "Your `reference.md` was edited
   since 1.2.0. May it be replaced with the 1.3.0 version? If yes, your edit is gone (git keeps it)."
   The author says no.
5. `PACKAGE update --host ROOT --json`: `updated`, finding `kept-modified` for the folder. You report the
   update, that `reference.md` keeps the author's edit, and remind them to commit the capability's folder
   and the new package.

## Failure modes

| Symptom | Cause | What to do |
|---|---|---|
| `python3` opens a store page or prints nothing (Windows) | a placeholder interpreter | try `python`, then `py -3`; report what you used |
| `other-version-installed` on install | a release over an installed version | step 3: update instead |
| `draft-exists` | an older draft is there | the author reviews it, or asks for `--replace` |
| `signing-unavailable` | a declared signer, no `--sign-key` or no `ssh-keygen` | say which piece is missing |
| exit 3 | an interrupted operation | the exit 3 section above |
| `target-not-declared` | a target the declaration does not list | install for the declared targets, or the author adds the target |
| `uvx-version` | a version uv does not accept | only the Python launch until the author changes the version |
