"""Guard: agent-facing assets teach the robust CLI invocation form (FEAT-010, E12).

After `sertor install rag` the runtime CLIs (`sertor-rag`, `sertor-wiki-tools`) live in the
project's `.sertor/.venv` and are **NOT on `PATH`**. An asset that tells the host agent to run a
*bare* `sertor-rag <cmd>` makes `which sertor-rag` come up empty → the agent wrongly concludes "tool
absent" and falls back to manual work (fail-loud broken). The fix: every agent-facing body that
*invokes* a CLI uses the `uv run --project .sertor <cli> …` form and ships the canonical "How to
invoke" guidance.

The form is **`--project`, NOT `--directory`** (FEAT-010 follow-up): `--directory .sertor` changes
the subprocess working directory to `.sertor`, so a relative path like `sertor-rag index .` would
index `.sertor` itself (the footgun). `--project .sertor` uses the `.sertor` venv but keeps the cwd,
so relative paths resolve from the project root. The MCP server template
(`rag/mcp.server.json.tmpl`) keeps `--directory` legitimately (it takes no path argument).

This suite asserts, offline (no network, no `uv`):

  (a) **presence** of the robust form `uv run --project .sertor` in the bodies that drive CLI use
      (the RAG-USAGE block, the `guided-setup` skill, the wiki playbook, the eval skills);
  (b) **scoped absence** of bare *invocations* — a line that runs `sertor-rag`/`sertor-wiki-tools`
      followed by a subcommand, NOT preceded by `uv run --project .sertor` (or `… `, the
      continuation marker). A name-citation ("the `sertor-rag` server") has no subcommand, passes;
  (c) **anti-regression of the footgun**: no agent-facing body reintroduces `uv run --directory
      .sertor` (only the MCP server template may carry `--directory`).

The ban regex is deliberately conservative (it fires only on a CLI + known subcommand reached
without the robust prefix); presence is the primary, robust signal.
"""
from __future__ import annotations

import re

from sertor_installer.resources import read_asset_text

# --- assets that DRIVE CLI invocation (must carry the robust form) ----------------------------

_ROBUST = "uv run --project .sertor"
_FOOTGUN = "uv run --directory .sertor"  # the cwd-changing form — banned in agent-facing bodies

_RAG_USAGE = "rag/claude-md-block-rag-usage.md"
_WIKI_BLOCK = "claude-md-block.md"
_GUIDED_SETUP = "rag/skills/guided-setup/SKILL.md"
_WIKI_PLAYBOOK = "claude/skills/wiki-author/wiki-playbook.md"
_EVAL_SUITE = "rag/skills/eval-suite-author/SKILL.md"
_EVAL_FEEDBACK = "rag/skills/eval-feedback/SKILL.md"
_CONCIERGE = "rag/agents/concierge.md"
# E10-FEAT-021: the single canonical "How to invoke" reference; the blocks/skills point to it.
_CLI_REFERENCE = "rag/sertor-cli-reference.md"

# Every agent-facing body that contains a CLI *invocation* and so must use the robust form.
_INVOKING_ASSETS = (
    _RAG_USAGE,
    _GUIDED_SETUP,
    _WIKI_PLAYBOOK,
    _CLI_REFERENCE,  # E10-FEAT-021: the reference invokes CLIs → must carry the robust form
    _EVAL_SUITE,
    _EVAL_FEEDBACK,
    _CONCIERGE,
    "claude/skills/wiki-author/SKILL.md",
    "claude/commands/wiki.md",
    "claude/agents/wiki-curator.md",
    "claude/skills/wiki-author/ops/record.md",
    "claude/skills/wiki-author/ops/rag-sync.md",
    "claude/skills/wiki-author/ops/lint.md",
    "claude/skills/wiki-author/ops/reorg.md",
    "claude/skills/wiki-author/ops/structure.md",
    "claude/skills/wiki-author/ops/generate.md",
    "claude/skills/wiki-author/ops/distill.md",
)

# E10-FEAT-021: the full canonical "How to invoke Sertor's commands" guidance (two levels: runtime
# CLIs via `uv run` + installer via `uvx`) lives in EXACTLY ONE asset — the reference. The reduced
# RAG block and the guided-setup skill point to it by name instead of repeating it.
_CANONICAL_GUIDE_ASSETS = (_CLI_REFERENCE,)


# A CLI subcommand we expect to see invoked. The token set is broad enough to catch a regression
# that reintroduces a bare invocation.
_SUBCOMMANDS = (
    "index", "search", "memory", "eval", "graph-eval", "doctor", "observe",  # sertor-rag
    "collect", "scan", "structure", "validate", "lint", "append-log", "migrate",
    "upsert-index", "move", "reconcile",  # sertor-wiki-tools (index/search shared above)
)

# A bare *invocation* (vs a name-citation): a CLI + subcommand FOLLOWED BY a concrete execution
# argument — a path (`.`/`..`/`<path>`), a flag (`--…`), a quoted string, or `init`. A name-citation
# like "the subcommand `sertor-rag eval add-case`" has `add-case` after `eval` (NOT in the arg set),
# so it does not match; an invocation like `sertor-rag index .` or `sertor-rag eval run` does. This
# keeps the ban from firing on prose that merely *names* a command. The `prefix` capture (left
# context) lets us exclude the robust form. Whitespace is normalized first, so a line-wrapped robust
# example `uv run --project .sertor\nsertor-rag …` is seen as robust.
_CLI = r"sertor-rag|sertor-wiki-tools"
_EXEC_ARG = r"(?:\.\.?|--[a-z]|run\b|init\b|\"|<[a-z])"
_BARE_INVOCATION = re.compile(
    r"(?P<prefix>.{0,60}?)`?\b(?P<cli>" + _CLI + r")\s+(?P<sub>"
    + "|".join(_SUBCOMMANDS) + r")\s+" + _EXEC_ARG
)


def _is_robust_context(prefix: str) -> bool:
    """The invocation is robust (not a bare call) if its left context carries the venv-routing
    prefix OR is the cautionary `--directory` footgun explanation.

    The anti-footgun guidance (task 3) cites `sertor-rag index .` inside a sentence like
    "`--directory` changes the working directory, so `sertor-rag index .` would index `.sertor`
    itself" — that is an *illustration of what NOT to do*, not a bare instruction. The phrase
    "working directory" (paired with the `--directory` warning) marks it as cautionary prose.
    """
    return (
        _ROBUST in prefix
        or prefix.rstrip().endswith("…")
        or "working directory" in prefix
    )


# --- (a) presence -----------------------------------------------------------------------------


def test_invoking_assets_carry_robust_form():
    """Every agent-facing body that invokes a CLI ships the `uv run --directory .sertor` form."""
    missing = [a for a in _INVOKING_ASSETS if _ROBUST not in read_asset_text(a)]
    assert not missing, f"robust invocation form `{_ROBUST}` missing from: {missing}"


def test_canonical_guide_present_where_first_invoked():
    """G5 (E10-FEAT-021): the full 'How to invoke' guide lives ONLY in the reference; the reduced
    RAG block and guided-setup skill point to it by name, they do not repeat it."""
    ref_body = read_asset_text(_CLI_REFERENCE)
    assert "How to invoke Sertor's commands" in ref_body, _CLI_REFERENCE
    # the two-level explanation: runtime CLIs via uv run + installer via uvx
    assert _ROBUST in ref_body, _CLI_REFERENCE
    assert "uvx --from" in ref_body, _CLI_REFERENCE
    # the PATH-failure clarification ("not on PATH, NOT not-installed")
    assert "not on `PATH`" in ref_body or "not on PATH" in ref_body, _CLI_REFERENCE
    # The other sedi carry the pointer, NOT the inline section.
    for asset in (_RAG_USAGE, _GUIDED_SETUP):
        body = read_asset_text(asset)
        assert "How to invoke Sertor's commands" not in body, (
            f"{asset}: still contains the inline section (must be a pointer)"
        )
        assert "`sertor-cli-reference.md`" in body, (
            f"{asset}: missing the pointer to sertor-cli-reference.md"
        )


def test_wiki_playbook_ships_runtime_invocation_guide():
    """G5 (E10-FEAT-021): the wiki playbook keeps only the minimal §2 invocation form; the full
    'How to invoke' subsection and the Windows note are removed (single source = the reference)."""
    body = read_asset_text(_WIKI_PLAYBOOK)
    # minimal robust form preserved (§2, wiki-only self-containment) + PATH clarification
    assert _ROBUST in body
    assert "not on `PATH`" in body
    # the dedicated subsection must be REMOVED
    assert "How to invoke the runtime CLIs" not in body, (
        "wiki-playbook still contains the inline subsection: it must be removed"
    )
    # Windows note must be REMOVED (lives only in the reference)
    assert "pywin32_bootstrap" not in body, (
        "wiki-playbook still contains the Windows note: it must be removed"
    )
    # host-agnostic + closure-safe: no installer/URL, no `*.md` reference to the RAG reference
    assert "uvx --from" not in body
    assert "github.com/themetriost/Sertor" not in body
    assert "`sertor-cli-reference.md`" not in body, (
        "wiki-playbook must not cite the reference by filename (dead pointer on wiki-only install)"
    )


def test_no_invoke_section_inline_in_blocks():
    """G1: the always-on claude-md-block*.md do NOT carry the 'How to invoke' inline section."""
    for asset in (_RAG_USAGE, _WIKI_BLOCK):
        body = read_asset_text(asset)
        assert "How to invoke Sertor's commands" not in body, (
            f"{asset}: contains the inline section (must be removed)"
        )
        assert "pywin32_bootstrap" not in body, (
            f"{asset}: contains the Windows note (must be removed)"
        )
        assert "uvx --from" not in body, (
            f"{asset}: contains the installer invocation (must be removed)"
        )


def test_invoke_section_exists_in_exactly_one_asset():
    """G2: 'How to invoke Sertor's commands' + the Windows note exist in EXACTLY one asset."""
    from sertor_installer.resources import iter_asset_dir

    all_md = [rel for rel, _content in iter_asset_dir("") if rel.endswith(".md")]
    heading = "How to invoke Sertor's commands"
    hits_heading = [a for a in all_md if heading in read_asset_text(a)]
    assert hits_heading == [_CLI_REFERENCE], (
        f"the heading '{heading}' must be in exactly one asset ({_CLI_REFERENCE}); "
        f"found in: {hits_heading}"
    )
    note_hits = [a for a in all_md if "pywin32_bootstrap" in read_asset_text(a)]
    assert note_hits == [_CLI_REFERENCE], (
        f"pywin32_bootstrap must be in exactly one asset ({_CLI_REFERENCE}); found in: {note_hits}"
    )


def test_pointers_present_in_reduced_bodies():
    """G3: the reduced bodies carry the expected by-name pointers (REQ-014/015)."""
    assert "`sertor-cli-reference.md`" in read_asset_text(_RAG_USAGE), (
        f"{_RAG_USAGE}: missing the pointer to sertor-cli-reference.md"
    )
    assert "`sertor-cli-reference.md`" in read_asset_text(_GUIDED_SETUP), (
        f"{_GUIDED_SETUP}: missing the pointer to sertor-cli-reference.md"
    )
    assert "`wiki-playbook.md`" in read_asset_text(_WIKI_BLOCK), (
        f"{_WIKI_BLOCK}: missing the by-name reference to wiki-playbook.md"
    )


def test_rag_usage_block_uv_run_replaces_bare_search():
    """The RAG-USAGE block's `search` example is now routed through `uv run --project .sertor`."""
    body = read_asset_text(_RAG_USAGE)
    assert f"{_ROBUST} sertor-rag search" in body


# --- (b) scoped absence of bare invocations ---------------------------------------------------


def _bare_offenders(asset: str) -> list[str]:
    # Normalize whitespace (collapse newlines/indentation) so a line-wrapped robust example
    # `uv run --directory .sertor\n  sertor-rag …` reads as a single robust span.
    body = re.sub(r"\s+", " ", read_asset_text(asset))
    offenders: list[str] = []
    for m in _BARE_INVOCATION.finditer(body):
        if _is_robust_context(m.group("prefix")):
            continue
        offenders.append(f"{m.group('cli')} {m.group('sub')}")
    return offenders


def test_no_bare_invocations_in_invoking_assets():
    """No agent-facing body invokes a CLI bare (CLI + subcommand without the venv-routing prefix).

    Name-citations (no subcommand token) are not matched, so 'the `sertor-rag` MCP server' passes.
    """
    found = {a: o for a in _INVOKING_ASSETS if (o := _bare_offenders(a))}
    assert not found, f"bare CLI invocations (should be `{_ROBUST} …`): {found}"


# --- (c) anti-regression of the `--directory` footgun -----------------------------------------

# Agent-facing assets whose bodies must never reintroduce `uv run --directory .sertor` (it changes
# the cwd to `.sertor`, so `sertor-rag index .` would index `.sertor` itself). The MCP server
# template is intentionally excluded — it takes no path argument and keeps `--directory`.
_FOOTGUN_BANNED_ASSETS = (*_INVOKING_ASSETS, "claude/hooks/wiki-pending-check.py")


def test_no_directory_footgun_in_agent_facing_assets():
    """No agent-facing body uses the cwd-changing `uv run --directory .sertor` form (FEAT-010).

    `--directory` changes the working directory to `.sertor`, so a relative path like
    `sertor-rag index .` would index `.sertor` itself instead of the host project. The cure is
    `--project .sertor` (keeps the cwd). The MCP server template keeps `--directory` legitimately
    (no path argument) and is not in this list.
    """
    offenders = [a for a in _FOOTGUN_BANNED_ASSETS if _FOOTGUN in read_asset_text(a)]
    assert not offenders, (
        f"`{_FOOTGUN}` reintroduced (use `{_ROBUST}` instead): {offenders}"
    )


def test_mcp_server_template_keeps_directory():
    """Sanity: the MCP server template legitimately keeps `--directory` (no path argument)."""
    body = read_asset_text("rag/mcp.server.json.tmpl")
    assert '"--directory"' in body


# --- meta: the ban regex is neither vacuous nor over-eager -------------------------------------


def test_bare_invocation_regex_catches_a_bare_call():
    """Positive: a freshly bare invocation is flagged (the guard is not vacuous)."""
    m = _BARE_INVOCATION.search("run `sertor-rag index .` to build the corpus")
    assert m is not None
    assert not _is_robust_context(m.group("prefix"))


def test_bare_invocation_regex_passes_robust_and_namecitation():
    """Negative: the robust form and a name-citation do NOT count as bare invocations."""
    robust = "run `uv run --project .sertor sertor-rag index .` to build"
    m = _BARE_INVOCATION.search(robust)
    assert m is not None and _is_robust_context(m.group("prefix"))
    # a name-citation has no subcommand token → no match at all
    assert _BARE_INVOCATION.search("the `sertor-rag` MCP server exposes tools") is None
    # a name-citation of a subcommand (no execution arg after it) → no match
    assert _BARE_INVOCATION.search("the subcommand `sertor-rag eval add-case` writes cases") is None
    assert _BARE_INVOCATION.search("declaring success without a green `sertor-rag doctor`") is None


# --- E10-FEAT-022: the eval skills point to the single CLI reference ---------------------------


def test_eval_skills_point_to_reference():
    """G3: the eval skills cite `sertor-cli-reference.md` (FR-010/CS-2).

    The reference closure (the target is deposited by the RAG plan where cited) is already
    guaranteed by `test_cli_reference_closure_in_rag_plan` in `test_assets_copilot_parity.py`.
    """
    for asset in (_EVAL_SUITE, _EVAL_FEEDBACK):
        body = read_asset_text(asset)
        assert "`sertor-cli-reference.md`" in body, (
            f"{asset}: missing the pointer to sertor-cli-reference.md"
        )
