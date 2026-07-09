"""Guard A: the in-scope hooks leave a fail-loud breadcrumb on a degraded path (E10-FEAT-019).

A SessionEnd/Stop hook is non-fatal by design: a failure of the delegated vehicle (or a catastrophic
internal error) is swallowed and the hook still exits 0. Without a trace that silent degradation is
invisible for weeks (the RAG goes stale / the memory is never archived and nobody notices). The
cure, in the portable Python hooks (A-09), is the shared fail-safe runner `_hooklib.run(name,
main)`: it wraps `main()`, catches ANY unexpected exception, persists a single, overwritten
`.sertor/.last-hook-error` breadcrumb (`_hooklib.write_breadcrumb`) and still exits 0. The former
inline `Write-HookBreadcrumb` PowerShell function became this centralized runner + helper.

This suite asserts, offline (no `uv`, no network), over the bundled hook assets in scope:

  - **A1** — every in-scope hook is WRAPPED by the fail-safe runner (`_hooklib.run(...)`, invoked as
    the module entry point) — the single place that guarantees a breadcrumb on any unexpected error.
    A hook that ran `main()` bare would leave its degraded paths mute.
  - **A2** — no *silent-exit* catch: an `except` block that terminates the hook (`sys.exit(...)` /
    `os._exit(...)`) while swallowing a failure WITHOUT leaving a breadcrumb is the regression we
    forbid. The sanctioned exit lives ONLY in `_hooklib.run` (which writes the breadcrumb first);
    the trivial best-effort catches that merely tolerate an operation and let execution continue
    (no exit) are NOT silent-exits and are not flagged.

Includes positive/negative meta-tests so the guard is neither vacuous nor over-eager.
"""
from __future__ import annotations

import re

from sertor_installer.resources import iter_asset_dir

# An exit call that terminates the hook process (bypassing the runner's breadcrumb).
_EXIT_CALL = re.compile(r"\b(?:sys\.exit|os\._exit|exit)\s*\(")

# The four hooks in scope (E10-FEAT-019 §4), now portable Python (A-09). `wiki-pending-check` lives
# under `claude/hooks`, the other three under `rag/hooks`.
_RAG_HOOKS = ("memory-capture.py", "rag-freshness.py", "version-check.py")
_CLAUDE_HOOKS = ("wiki-pending-check.py",)


def _py_code_lines(body: str) -> list[str]:
    """Code only: drop whole-line `#` comments (prose mentioning 'sys.exit' or '_hooklib.run' in a
    comment must not be mistaken for code). Module docstrings never contain an `except …:` header
    nor an exit call, so they are left in place harmlessly."""
    return [ln for ln in body.splitlines() if not ln.strip().startswith("#")]


def _hook_bodies_in_scope() -> list[tuple[str, str]]:
    """(name, code) for the four in-scope hooks — code only, `#` comments stripped."""
    out: list[tuple[str, str]] = []
    rag = {rel: body for rel, body in iter_asset_dir("rag/hooks") if rel.endswith(".py")}
    claude = {rel: body for rel, body in iter_asset_dir("claude/hooks") if rel.endswith(".py")}
    for name in _RAG_HOOKS:
        out.append((name, "\n".join(_py_code_lines(rag[name]))))
    for name in _CLAUDE_HOOKS:
        out.append((name, "\n".join(_py_code_lines(claude[name]))))
    return out


def _except_bodies(code: str) -> list[str]:
    """Bodies of every Python `except …:` block, resolved by indentation (block-scoped).

    Handles both the multi-line form (`except Exception:` + an indented suite) and the inline form
    (`except Exception: stmt`). Blank lines inside a suite are kept; the suite ends at the first
    non-blank line indented at or below the `except` keyword.
    """
    lines = code.splitlines()
    bodies: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        if re.match(r"except\b[^:]*:", stripped):
            indent = len(line) - len(stripped)
            after = stripped.split(":", 1)[1]
            if after.strip():  # inline suite: `except Foo: stmt`
                bodies.append(after.strip())
                i += 1
                continue
            i += 1
            suite: list[str] = []
            while i < len(lines):
                nxt = lines[i]
                if not nxt.strip():
                    suite.append(nxt)
                    i += 1
                    continue
                nindent = len(nxt) - len(nxt.lstrip())
                if nindent <= indent:
                    break
                suite.append(nxt)
                i += 1
            bodies.append("\n".join(suite))
        else:
            i += 1
    return bodies


def _silent_exit_offenders(code: str) -> list[str]:
    """`except` blocks that terminate the hook (`sys.exit`/`os._exit`/`exit`) WITHOUT writing a
    breadcrumb — the forbidden silent-exit regression. An `except` that calls `write_breadcrumb`
    before exiting is the loud, allowed form; a trivial best-effort catch (no exit, execution
    continues) is not a silent-exit. The sanctioned exit lives in `_hooklib.run`, not the hooks."""
    return [
        b.strip()
        for b in _except_bodies(code)
        if _EXIT_CALL.search(b) and "write_breadcrumb" not in b
    ]


def _last_code_line(code: str) -> str:
    lines = [ln for ln in code.splitlines() if ln.strip()]
    return lines[-1].strip() if lines else ""


# --- A1: wrapped by the fail-safe runner ------------------------------------------------------


def test_in_scope_hooks_are_discovered():
    """Anti-vacuity: the guard sees exactly the four hooks it must police."""
    names = {name for name, _ in _hook_bodies_in_scope()}
    assert names == {*_RAG_HOOKS, *_CLAUDE_HOOKS}, names


def test_write_hook_breadcrumb_defined_and_invoked_in_scope_hooks():
    """A1: every in-scope hook is wrapped by the fail-safe runner `_hooklib.run(...)` (its module
    entry point), the single place that guarantees a breadcrumb on any unexpected error."""
    for name, code in _hook_bodies_in_scope():
        assert "import _hooklib" in code, f"{name}: does not import the shared _hooklib"
        assert "_hooklib.run(" in code, f"{name}: not wrapped by the fail-safe runner"
        assert _last_code_line(code).startswith("_hooklib.run("), (
            f"{name}: the module entry point must be `_hooklib.run(...)` (found: "
            f"{_last_code_line(code)!r})"
        )


# --- A2: no silent-exit catch outside the sanctioned runner -----------------------------------


def test_no_silent_exit_catch_in_scope_hooks():
    """A2: no `except { … sys.exit(…) … }` swallows a failure without leaving a breadcrumb."""
    offenders = {
        name: o for name, code in _hook_bodies_in_scope() if (o := _silent_exit_offenders(code))
    }
    assert not offenders, f"silent-exit catch without breadcrumb: {offenders}"


# --- meta: the guard is neither vacuous nor over-eager ----------------------------------------


def test_meta_silent_exit_flags_bare_exit_zero_catch():
    """A2 positive: an `except` that `sys.exit(0)` without a breadcrumb IS flagged."""
    body = "try:\n    do_thing()\nexcept Exception:\n    sys.exit(0)\n"
    assert _silent_exit_offenders(body)


def test_meta_silent_exit_allows_breadcrumb_catch():
    """A2 negative: the loud form `except: write_breadcrumb(...); sys.exit(0)` is NOT flagged."""
    body = (
        "try:\n"
        "    do_thing()\n"
        "except Exception:\n"
        "    _hooklib.write_breadcrumb('x', 'failed')\n"
        "    sys.exit(0)\n"
    )
    assert not _silent_exit_offenders(body)


def test_meta_silent_exit_ignores_trivial_best_effort_catch():
    """A2 negative: a trivial best-effort `except: pass` (no exit, continues) is allowed."""
    body = "try:\n    x = 1\nexcept Exception:\n    pass\ntry:\n    pop()\nexcept Exception:\n    y"
    assert not _silent_exit_offenders(body)


def test_meta_a1_detects_missing_runner_wrapper():
    """A1 scoped meta: a body running `main()` bare (no `_hooklib.run`) would fail the A1 check."""
    code = "def main():\n    do_thing()\n\nif __name__ == '__main__':\n    main()\n"
    assert "_hooklib.run(" not in code


def test_meta_except_bodies_are_indentation_scoped():
    """The indentation matcher returns the full suite of an `except` block and stops at dedent."""
    code = (
        "except Exception:\n"
        "    _hooklib.write_breadcrumb('x', 'y')\n"
        "    return\n"
        "next_statement()\n"
    )
    bodies = _except_bodies(code)
    assert len(bodies) == 1
    assert "write_breadcrumb" in bodies[0]
    assert "next_statement" not in bodies[0]  # dedent ends the suite
