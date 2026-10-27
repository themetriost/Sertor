## Kaelen producer kit

This repository has the **Kaelen producer kit** installed. It lets the repository make its own
capabilities installable in other repositories with the Kaelen install engine.

- **To make a node installable**, use the `kaelen-authoring` skill. It takes a hand-written declaration
  (usually `kaelen.declaration.toml`) through validate, package and install, and explains every
  outcome.
- **To start a declaration from the repository's layout**, ask the engine for a draft:
  `python .kaelen/engine/run.py draft --producer . --json`. It reads the layout by fixed conventions
  (`draft --conventions` lists them), writes `kaelen.declaration.draft.toml` and never touches the
  declaration. The author copies from it.
- **To delegate the authoring path**, use the `kaelen-author` agent where the assistant supports agents.
  Elsewhere the `kaelen-authoring` skill is enough.
- **To install, verify, update or remove a capability another node publishes**, use the
  `kaelen-install` skill. It runs that node's package from its git repository at a commit, dry-runs
  every change first, and asks before replacing any file.
- **The engine** is this repository's main Kaelen, at `.kaelen/engine/run.py`. It runs with any
  Python 3.11 or later and nothing else:
  `python .kaelen/engine/run.py --help`.
- **Reach the engine only through `run.py`.** Do not import the `kaelen` package in your own scripts,
  and do not copy or edit files under `.kaelen/` by hand: the engine records what it writes, and
  verifies it against that record.
- **Installed capabilities** are listed with
  `python .kaelen/engine/run.py installed --host .`. Each one lives in its own folder,
  `.<node>/kaelen/<capability>/`, with its registry and a copy of its package: the folder belongs in
  version control, and the copy can uninstall the capability without its producer.
