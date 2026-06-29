"""Guard A: the in-scope hooks leave a fail-loud breadcrumb on a degraded path (E10-FEAT-019).

A SessionEnd/Stop hook is non-fatal by design: a failure of the delegated vehicle (or a catastrophic
internal error) is swallowed and the hook still exits 0. Without a trace that silent degradation is
invisible for weeks (the RAG goes stale / the memory is never archived and nobody notices). The cure
is the inline `Write-HookBreadcrumb` function (byte-identical across the four hooks): it persists a
single, overwritten `.sertor/.last-hook-error` so a silently swallowed failure leaves an inspectable
trace, while remaining strictly non-fatal (its own write runs inside try/catch).

This suite asserts, offline (no `uv`, no network), over the bundled hook assets in scope:

  - **A1** — every in-scope hook DEFINES `Write-HookBreadcrumb` AND invokes it (a defined-but-unused
    function would mean the degraded paths are still mute).
  - **A2** — no *silent-exit* catch: a `catch { … exit 0 … }` that swallows a failure and terminates
    the hook WITHOUT leaving a breadcrumb is the regression we forbid. The sanctioned best-effort
    sink (the empty `catch { }` inside `Write-HookBreadcrumb` itself, plus the trivial best-effort
    catches that merely tolerate an operation and let execution continue) are NOT silent-exits and
    are not flagged.

Includes positive/negative meta-tests so the guard is neither vacuous nor over-eager.
"""
from __future__ import annotations

import re

from sertor_installer.resources import iter_asset_dir

_BLOCK_COMMENT = re.compile(r"<#.*?#>", re.DOTALL)
_EXIT_ZERO = re.compile(r"\bexit\s+0\b")

# The four hooks in scope (E10-FEAT-019 §4). `wiki-pending-check` lives under `claude/hooks`, the
# other three under `rag/hooks`.
_RAG_HOOKS = ("memory-capture.ps1", "rag-freshness.ps1", "version-check.ps1")
_CLAUDE_HOOKS = ("wiki-pending-check.ps1",)


def _ps1_code_lines(body: str) -> list[str]:
    """Code only: drop `<# … #>` blocks and whole-line `#` comments (prose mentioning 'exit 0' or
    'Write-HookBreadcrumb' must not be mistaken for code)."""
    without_block = _BLOCK_COMMENT.sub("", body)
    return [ln for ln in without_block.splitlines() if not ln.strip().startswith("#")]


def _hook_bodies_in_scope() -> list[tuple[str, str]]:
    """(name, code) for the four in-scope hooks — code only, block/line comments stripped."""
    out: list[tuple[str, str]] = []
    rag = {rel: body for rel, body in iter_asset_dir("rag/hooks") if rel.endswith(".ps1")}
    claude = {rel: body for rel, body in iter_asset_dir("claude/hooks") if rel.endswith(".ps1")}
    for name in _RAG_HOOKS:
        out.append((name, "\n".join(_ps1_code_lines(rag[name]))))
    for name in _CLAUDE_HOOKS:
        out.append((name, "\n".join(_ps1_code_lines(claude[name]))))
    return out


def _catch_bodies(code: str) -> list[str]:
    """Bodies of every PowerShell `catch [Type] { … }` block, via brace matching (nested-safe)."""
    bodies: list[str] = []
    n = len(code)
    i = 0
    while True:
        idx = code.find("catch", i)
        if idx == -1:
            break
        before = code[idx - 1] if idx > 0 else " "
        after = code[idx + 5] if idx + 5 < n else " "
        if before.isalnum() or before in "-_" or after.isalnum() or after in "-_":
            i = idx + 5  # not the bare keyword `catch`
            continue
        j = idx + 5
        while j < n and code[j] in " \t\r\n":
            j += 1
        # optional exception-type filter: catch [System.Exception] { … }
        if j < n and code[j] == "[":
            depth_b = 0
            while j < n:
                if code[j] == "[":
                    depth_b += 1
                elif code[j] == "]":
                    depth_b -= 1
                    if depth_b == 0:
                        j += 1
                        break
                j += 1
            while j < n and code[j] in " \t\r\n":
                j += 1
        if j >= n or code[j] != "{":
            i = idx + 5
            continue
        depth = 0
        k = j
        while k < n:
            if code[k] == "{":
                depth += 1
            elif code[k] == "}":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        bodies.append(code[j + 1 : k])
        i = k + 1
    # Recurse into each body so NESTED catches are captured independently (a silent-exit hiding
    # inside an outer catch is still a silent-exit). Each recursion strips the outer braces, so the
    # string shrinks strictly → termination.
    nested: list[str] = []
    for b in bodies:
        nested.extend(_catch_bodies(b))
    return bodies + nested


def _silent_exit_offenders(code: str) -> list[str]:
    """Catch blocks that `exit 0` (terminate the hook) WITHOUT leaving a breadcrumb — the forbidden
    silent-exit regression. A catch that calls `Write-HookBreadcrumb` is the loud, allowed form;
    a trivial best-effort catch (no `exit 0`, execution continues) is not a silent-exit."""
    return [
        b.strip()
        for b in _catch_bodies(code)
        if _EXIT_ZERO.search(b) and "Write-HookBreadcrumb" not in b
    ]


# --- A1: defined AND invoked ------------------------------------------------------------------


def test_in_scope_hooks_are_discovered():
    """Anti-vacuity: the guard sees exactly the four hooks it must police."""
    names = {name for name, _ in _hook_bodies_in_scope()}
    assert names == {*_RAG_HOOKS, *_CLAUDE_HOOKS}, names


def test_write_hook_breadcrumb_defined_and_invoked_in_scope_hooks():
    """A1: every in-scope hook defines `Write-HookBreadcrumb` and actually invokes it."""
    for name, code in _hook_bodies_in_scope():
        assert "function Write-HookBreadcrumb" in code, f"{name}: function not defined"
        invocations = code.replace("function Write-HookBreadcrumb", "")
        assert "Write-HookBreadcrumb" in invocations, f"{name}: function defined but never invoked"


# --- A2: no silent-exit catch outside the sanctioned breadcrumb sink --------------------------


def test_no_silent_exit_catch_in_scope_hooks():
    """A2: no `catch { … exit 0 … }` swallows a failure without leaving a breadcrumb."""
    offenders = {
        name: o for name, code in _hook_bodies_in_scope() if (o := _silent_exit_offenders(code))
    }
    assert not offenders, f"silent-exit catch without breadcrumb: {offenders}"


# --- meta: the guard is neither vacuous nor over-eager ----------------------------------------


def test_meta_silent_exit_flags_bare_exit_zero_catch():
    """A2 positive: a `catch { exit 0 }` without a breadcrumb IS flagged."""
    body = "try { uv run thing } catch { exit 0 }\nexit 0"
    assert _silent_exit_offenders(body)


def test_meta_silent_exit_allows_breadcrumb_catch():
    """A2 negative: the loud form `catch { Write-HookBreadcrumb …; exit 0 }` is NOT flagged."""
    body = (
        "try { uv run thing } catch {\n"
        "    Write-HookBreadcrumb -Root $root -Hook 'x' -Reason 'failed'\n"
        "    exit 0\n"
        "}\nexit 0"
    )
    assert not _silent_exit_offenders(body)


def test_meta_silent_exit_ignores_trivial_best_effort_catch():
    """A2 negative: a trivial best-effort `catch {}` (no exit, execution continues) is allowed."""
    body = "try { $x = 1 } catch {}\ntry { Pop-Location } catch {}"
    assert not _silent_exit_offenders(body)


def test_meta_a1_detects_missing_breadcrumb_function():
    """A1 scoped meta: a body without `Write-HookBreadcrumb` would fail the A1 assertion."""
    code = "try { uv run thing } catch { exit 0 }"
    assert "function Write-HookBreadcrumb" not in code


def test_meta_catch_bodies_are_nested_safe():
    """The brace matcher returns the full outer body AND the nested catch independently."""
    code = "catch {\n  Write-HookBreadcrumb -Reason 'x'\n  try { Pop-Location } catch {}\n}"
    bodies = _catch_bodies(code)
    assert any("Write-HookBreadcrumb" in b for b in bodies)
    assert any(b.strip() == "" for b in bodies)  # the nested empty catch
