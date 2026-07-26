"""Start-of-session version-update signal — reads the state and warns if behind. Portable (A-09).

SessionStart hook that reads `.sertor/.version-check.json` (written by `version-check` at the previous
SessionEnd) and, if the verdict is `behind`, emits on **stdout** an update notice the assistant
receives as session-start context (E2-FEAT-013, FR-003).

D<->N boundary: it does NOT apply any update (the user decides). ZERO network (the GET happened at
SessionEnd). Idempotent: absent state or verdict != `behind` → no-op. Always exit 0.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tomllib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hooklib  # noqa: E402

# Fallback when the runtime's own source cannot be read. Deliberately NOT the bare `uvx sertor`:
# that resolves the root package, which does not provide the `sertor` console script — the exact
# command this notice used to publish, and the reason a node following it could not update at all.
_FALLBACK_URL = "https://github.com/themetriost/Sertor.git"


def _runtime_source(sertor_dir) -> tuple[str, str]:
    """The `(url, ref)` this host installed `sertor-core` from, PARSED as TOML — never by hand.

    Read from the runtime's own `pyproject.toml` (`[tool.uv.sources]`) so the notice is correct for
    whichever repository this host installed from — host-agnostic by construction rather than by
    hardcoding ours. `ref` is the `tag`/`rev`/`branch` the host pinned to, or `""` if unpinned.

    **Parsed with `tomllib`, not with string surgery (E2, reported by the Acta node).** The previous
    version did `split("git = ")[1].strip("}").strip('"')`, which happens to work on a ref-less
    source and produces garbage on a pinned one — a host with `{ git = "…", tag = "v0.2.1" }` was
    shown a command containing `…Sertor.git", tag = "v0.2.1#subdirectory=…`, which is not
    executable. The defect **selected for hosts following the discipline**: only a host that pins to
    an immutable ref got the broken command, which is why it never appeared here (our runtime tracks
    HEAD by design, so the pinned branch is unreachable on this node) and reached us from outside.
    `tomllib` is stdlib from 3.11 and this runtime requires ≥3.12: parsing by hand was never needed.
    """
    try:
        with (sertor_dir / "pyproject.toml").open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError, ValueError):
        return _FALLBACK_URL, ""
    source = (data.get("tool") or {}).get("uv", {}).get("sources", {}).get("sertor-core")
    if not isinstance(source, dict):
        return _FALLBACK_URL, ""
    url = source.get("git")
    if not isinstance(url, str) or not url:
        return _FALLBACK_URL, ""
    for key in ("tag", "rev", "branch"):
        ref = source.get(key)
        if isinstance(ref, str) and ref:
            return url, ref
    return url, ""


def _upgrade_command(sertor_dir, installed: str = "", latest: str = "") -> str:
    """The remedy phrased for how THIS host is set up — never a command it cannot act on.

    `sertor` is never a persistent command: it is always fetched on demand by
    `uvx --from "git+…#subdirectory=packages/sertor"`, so that form works on any host with `uv` and
    network. The `#subdirectory` fragment is the load-bearing part — without it `uvx` resolves the
    ROOT package, which does not provide `sertor`, and fails with "An executable named `sertor` is
    not provided". That bare form is the one a node could not run (reported by Kaelen); it is pinned
    against by the guards.

    What the notice must NOT assume is **how the host manages its runtime** (Principle XIV — derive
    where derivable, declare where not):

    - **unpinned** → `sertor upgrade` is the whole remedy;
    - **pinned to a tag naming the installed version** → the new ref is DERIVABLE. The host is told
      to MOVE the pin (carrying the old ref would tell a host that is behind to reinstall the version
      it already has), and warned that `sertor upgrade` — which it still needs, for the assets —
      currently resets the pin. A pin is a deliberate choice; discarding it silently is not a remedy.
    - **pinned to a commit or a branch** → the new ref is NOT derivable from here, so it is not
      invented: the pin is NAMED and the host decides where to move it.
    """
    url, ref = _runtime_source(sertor_dir)
    upgrade = f'uvx --refresh --from "git+{url}#subdirectory=packages/sertor" sertor upgrade'
    if not ref:
        return upgrade

    prefix = "v" if ref.startswith("v") else ""
    known = bool(installed and latest) and ref in (installed, f"v{installed}")
    step = (
        f"set the `sertor-core` pin in .sertor/pyproject.toml to `{prefix}{latest}`" if known
        else f"point the `sertor-core` pin in .sertor/pyproject.toml (now `{ref}`) at the new version"
    )
    return (
        f"your runtime pins `{ref}`, so upgrading is two steps: {step}, then "
        f"`uv sync --project .sertor` for the runtime; and {upgrade} for the installed assets "
        "(that command currently resets the pin, so re-apply it afterwards)"
    )


def main() -> None:
    argparse.ArgumentParser().parse_known_args()  # accept/ignore --assistant (wiring symmetry)
    _hooklib.read_event()  # drain stdin (stdin-guard)

    state_path = _hooklib.sertor_dir() / ".version-check.json"
    if not state_path.is_file():
        return  # no state yet → no-op (INV-1)
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return  # malformed → no-op (non-fatal)
    if not isinstance(state, dict):
        return

    verdict = state.get("verdict")

    if verdict == "behind":
        installed = str(state.get("installed") or "unknown")
        latest = str(state.get("latest") or "unknown")
        dim_text = ""
        dimensions = state.get("dimensions")
        if isinstance(dimensions, dict) and dimensions:
            behind = ", ".join(f"{name} {value}" for name, value in dimensions.items())
            dim_text = f" Installed dimensions: {behind}."
        # Update notice (stdout = SessionStart context). Only WARNS; the user decides (FR-005/CS-4).
        print(
            f"SERTOR UPDATE AVAILABLE: installed {installed}, latest {latest}.{dim_text} "
            f"To update: {_upgrade_command(_hooklib.sertor_dir(), installed, latest)}. "
            "This is only a notice — no update is applied automatically."
        )
        return

    # E2-FEAT-017: honest ONE-TIME cue when the check could not verify (verdict `unknown`: the
    # /VERSION GET failed — offline, or the source repository is private). Without this the updater
    # is silently inert (SessionStart only spoke on `behind`) and the user never learns it cannot
    # verify. No nag: emit ONCE, then persist `unknown_notified` so it does not repeat while unknown.
    if verdict == "unknown" and not state.get("unknown_notified"):
        print(
            "SERTOR UPDATE CHECK UNAVAILABLE: could not verify whether a newer Sertor is available "
            "(the version endpoint was unreachable — offline, or the source repository is private). "
            "Sertor works normally; this notice appears once. To check manually, compare your "
            "installed version with the project's /VERSION, or run `uvx --refresh` on your install."
        )
        try:  # mark notified so it does not repeat every session (best-effort, non-fatal)
            state["unknown_notified"] = True
            state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        except Exception:
            pass
        return

    # up-to-date / ahead / unknown-already-notified / absent → no-op (INV-1)


if __name__ == "__main__":
    _hooklib.run("version-check-start", main)
