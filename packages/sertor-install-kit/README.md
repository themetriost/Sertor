# sertor-install-kit

The shared **installation engine** behind Sertor's installers (`sertor` and `sertor-flow`).

Standard-library only, with **no dependency on `sertor-core`**: non-destructive artifact / plan /
executor, additive merges (env, JSON, settings), marker-delimited instruction blocks, per-assistant
targeting, lifecycle primitives, and bundled-resource access.

This is an **internal building block** — you normally install
[`sertor`](https://github.com/themetriost/Sertor/tree/master/packages/sertor) or
[`sertor-flow`](https://github.com/themetriost/Sertor/tree/master/packages/sertor-flow), not this
package directly. MIT licensed.
