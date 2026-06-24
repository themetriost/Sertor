# Operation `structure` — structure bootstrap (idempotent)

> **Operation module.** Executor: **curator/CLI** (purely mechanical, no judgment).
> For the **shared substrate** (taxonomy §3) see the playbook `wiki-playbook.md`. Only the procedure is described here.

On a new host (or to repair missing special folders/files): `uv run --project .sertor
sertor-wiki-tools structure init`. Creates the taxonomy folders + index + log with a minimal seed;
**does not overwrite** what already exists
(contract `wiki.structure/1`: `created` / `skipped_existing`). No judgment: purely mechanical.

Append a log entry `structure` **only if** something was created (`created` non-empty); if everything is
`skipped_existing`, **no entry** (idempotent + anti-trivial rule of index §6).
