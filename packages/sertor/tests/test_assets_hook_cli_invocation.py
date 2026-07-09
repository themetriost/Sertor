"""Guard: hook scripts invoke the CLI the robust, cwd-independent way (E10-FEAT-017, ISSUE-03).

A SessionEnd/Stop hook can be fired by the host from a working directory that is **not** the project
root. A *bare* `uv run sertor-rag …` then resolves the project/venv from the CWD, so it
either picks the wrong project (a parent/sibling `.sertor`) or fails. Being non-fatal,
the failure is silent (the capture/freshness work never happens). The cure, used by the portable
Python hooks (A-09), is to pin the runtime explicitly with the **list argv** form
`["uv", "run", "--project", str(<root>/.sertor), <cli>, …]` (PATH- and cwd-independent), with a
fallback to the CLI executable inside that venv.

This suite asserts, offline (no `uv`, no network), over the bundled hook assets
(`assets/rag/hooks/*.py`):

  - **presence** — every hook that spawns `uv` uses the project-pinned list form
    `"uv", "run", "--project"` (the two vehicle-invoking hooks, memory-capture and rag-freshness);
  - **scoped absence** of any bare `uv`/`run` invocation — a `["uv", "run", <x>]` argv where `<x>`
    is NOT `"--project"` is the banned, cwd-fragile form;
  - **absence** of the `--directory` footgun (it changes the cwd to `.sertor`).

Includes positive/negative meta-tests so the guard is neither vacuous nor over-eager.
"""
from __future__ import annotations

import re

from sertor_installer.resources import iter_asset_dir

# The project-pinned list argv form: `"uv", "run", "--project"` (whitespace-tolerant).
_PROJECT_PINNED = re.compile(r'"uv"\s*,\s*"run"\s*,\s*"--project"')
# A bare `"uv", "run", <not --project>`: the banned, cwd-fragile list form.
_BARE_UV_RUN = re.compile(r'"uv"\s*,\s*"run"\s*,\s*"(?!--project")')
# The cwd-changing footgun (as a list token or a plain string).
_DIRECTORY_FOOTGUN = re.compile(r'"--directory"|--directory\s+\.sertor')

_HOOK_DIR = "rag/hooks"
# The RAG hooks that actually spawn a vehicle (`uv run … sertor-rag …`). The others (version-check,
# the `-start` inducement hooks, the usage-check) invoke no vehicle by design.
_VEHICLE_HOOKS = ("memory-capture.py", "rag-freshness.py")


def _hook_assets() -> list[tuple[str, str]]:
    """The bundled RAG hook scripts (rel_path, content) — `.py` only."""
    return [(rel, body) for rel, body in iter_asset_dir(_HOOK_DIR) if rel.endswith(".py")]


def _code_lines(body: str) -> list[str]:
    """Code only: drop whole-line `#` comments so prose mentioning 'uv run' is not mistaken for an
    invocation. Module docstrings never carry the list-argv tokens, so they are harmless."""
    return [ln for ln in body.splitlines() if not ln.strip().startswith("#")]


def _code(body: str) -> str:
    return "\n".join(_code_lines(body))


def _bare_uv_run_offenders(body: str) -> list[str]:
    """Code lines carrying a bare `"uv", "run", <x>` where `<x>` is not `"--project"`."""
    return [ln.strip() for ln in _code_lines(body) if _BARE_UV_RUN.search(ln)]


def test_hook_assets_have_no_bare_uv_run():
    """No hook script spawns `uv run` without pinning the runtime via `--project`."""
    found = {rel: o for rel, body in _hook_assets() if (o := _bare_uv_run_offenders(body))}
    assert not found, (
        f'bare `"uv", "run", …` (must be `"uv", "run", "--project", <root>/.sertor, …`): {found}'
    )


def test_vehicle_hooks_carry_project_pinned_form():
    """Presence: every vehicle-invoking hook uses the project-pinned list argv form."""
    bodies = dict(_hook_assets())
    for name in _VEHICLE_HOOKS:
        assert name in bodies, f"{name} missing from the bundled hooks"
        assert _PROJECT_PINNED.search(bodies[name]), (
            f'{name}: missing the project-pinned form `"uv", "run", "--project"`'
        )


def test_hooks_have_no_directory_footgun():
    """Absence: no hook reintroduces the cwd-changing `--directory .sertor` footgun (FEAT-010)."""
    found = {rel for rel, body in _hook_assets() if _DIRECTORY_FOOTGUN.search(_code(body))}
    assert not found, f"`--directory` footgun reintroduced (use `--project`): {found}"


def test_hook_assets_are_discovered():
    """Sanity: the guard sees the hook scripts it is meant to police (anti-vacuity)."""
    rels = {rel for rel, _ in _hook_assets()}
    assert "memory-capture.py" in rels, rels
    assert "rag-freshness.py" in rels, rels


# --- meta: the ban is neither vacuous nor over-eager ------------------------------------------


def test_bare_uv_run_regex_catches_a_bare_call():
    """Positive: a bare `"uv", "run", "sertor-rag", …` is flagged (the guard is not vacuous)."""
    assert _bare_uv_run_offenders('    subprocess.run(["uv", "run", "sertor-rag", "memory"])')


def test_project_pinned_form_and_comments_pass():
    """Negative: the robust form passes; a comment/prose mention of 'uv run' is NOT flagged."""
    assert not _bare_uv_run_offenders(
        '    subprocess.run(["uv", "run", "--project", str(runtime), "sertor-rag", "index", "."])'
    )
    assert not _bare_uv_run_offenders("# never use a bare `uv run` here")
    assert _PROJECT_PINNED.search('["uv", "run", "--project", str(runtime), "sertor-rag"]')
