"""Plant, in a throwaway smoke host, the state of a host already hit by the MCP SDK major.

Used by BOTH `smoke.ps1` and `smoke.sh` so the planting is described once and the two scripts
cannot drift on it (asset parity). Called before the upgrade step, with the runtime manifest and
the release the host starts from:

    python scripts/smoke_plant_mcp.py <host>/.sertor/pyproject.toml <from_ref>

**What it plants: ONE edit, and not the obvious one** (measured 2026-09-13, E10-FEAT-070).

It **pins `sertor-core` to `<from_ref>`** — and that is enough, because the release a host starts
from has **no `mcp` ceiling**: `uv` then resolves the newest SDK, i.e. the new major, exactly as it
did on the nodes in the field. The frozen major arrives *as a consequence of the pin*, and that is
what makes the fixture faithful — those hosts did not ask for the new major either.

Why the pin is needed at all: the installer writes the runtime source as a BARE git reference, so
the runtime follows the **default branch**, not the release the installer came from (measured: an
install «of v0.4.1» produced a runtime resolving `sertor-core 0.4.1 (de31fe6)`, a commit on the
default branch). With the ceiling that lives there, the condition cannot exist at all.

A first version of this helper ALSO added `mcp>=2` to the runtime dependencies. Dropped, and the
reason is worth keeping: it left in the manifest a constraint no real host has, and it made the
`upgrade` step itself unresolvable — the fixture was breaking the very command under test.

`upgrade` moves the pin back (smoke outcome `pin-moved`), so nothing planted here survives the
upgrade except the frozen SDK major in the lock — which is exactly the condition under test.

Exit code is always 0: whether the planting can be RESOLVED is decided by the `uv sync` that the
calling script runs next, which distinguishes «this release is not affected» from an impediment.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def plant(manifest: Path, from_ref: str) -> list[str]:
    """Edit the runtime manifest in place. Returns the human-readable list of what changed."""
    text = manifest.read_text(encoding="utf-8")
    done: list[str] = []

    def _pin(match: re.Match[str]) -> str:
        return f'sertor-core = {{ git = "{match.group(1)}", tag = "{from_ref}" }}'

    text, count = re.subn(r'sertor-core = \{ git = "([^"]+)"[^}]*\}', _pin, text, count=1)
    if count:
        done.append(f"pinned sertor-core to {from_ref}")

    manifest.write_text(text, encoding="utf-8")
    return done


def main() -> int:
    if len(sys.argv) != 3:
        print(f"usage: {Path(sys.argv[0]).name} <runtime pyproject.toml> <from_ref>",
              file=sys.stderr)
        return 2
    manifest, from_ref = Path(sys.argv[1]), sys.argv[2]
    if not manifest.is_file():
        # Not an error: capabilities other than `rag` create no runtime. The caller guards for this
        # too; saying it out loud keeps a silent no-op from looking like a successful plant.
        print(f"[plant] no runtime manifest at {manifest} — nothing to plant")
        return 0
    changes = plant(manifest, from_ref)
    print("[plant] " + ("; ".join(changes) if changes else "manifest already in the planted state"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
