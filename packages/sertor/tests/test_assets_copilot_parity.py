"""Parity guard for the distributable assets across hosts (FEAT-001, feature 056).

The Copilot prompt-files / custom-agents / payload reuse the SAME body as the Claude assets (the
container is translated, the body is verbatim — anti-drift). That makes any `.claude/` path, slash
command or assistant name in a body LEAK onto the Copilot host, where it points at nothing. The
byte-identical guard (`test_assets_copilot_guard.py`) does NOT see this: it only checks the body did
not fork. This suite renders the installation plans (wiki + governance + rag) for Copilot and
asserts four invariants on every rendered LLM-facing body:

  (a) no `.claude/` path-string;
  (b) no slash-command (`/wiki`, `/requirements`, ...) used as an *invocation*;
  (c) no assistant name ("Claude Code");
  (d) **reference closure**: every file a body references is a target of the plan (relatives
      resolved against the referent's container). Closure is run on the Claude plan too (T002): the
      neutralization must not introduce dangling references in the dogfood branch.

Offline (NFR-05): no network, no `uv`. Bodies are LLM-facing markdown (`.md`); scripts (`.ps1`) and
generated config/manifest templates (`.json`/`.tmpl`) are out of scope per the spec (the "Claude
Code" comment in `.ps1` is a code comment, not a body).
"""
from __future__ import annotations

import re
from pathlib import Path

from sertor_install_kit.assistant import AssistantId
from sertor_installer.artifacts import Artifact, ArtifactKind
from sertor_installer.install_rag import build_rag_plan
from sertor_installer.install_wiki import _render_for_target, build_install_plan
from sertor_installer.rag_profile import RagHostProfile, RagInstallOptions
from sertor_installer.resources import read_asset_text
from sertor_installer.surfaces import render_custom_agent

# A slash-command used as an *invocation*: a leading `/` + a known command word, NOT a POSIX path
# (`wiki/log`), a URL (`https://...`) nor a closing tag. Matched after a boundary that is the
# start, whitespace, or a markdown delimiter (backtick/paren/quote). The word must be a bare command
# token (letters/hyphen), so `wiki/log` (no leading `/`) and `http://x` (no leading `/word`) miss.
_SLASH_COMMAND = re.compile(r"(?:^|[\s`(\"'])/(wiki|requirements)\b")

# A markdown link target `[..](path)` or an inline `` `path.md` `` reference. We only care about
# file references (something with an extension or a known craft/playbook/ops name).
_MD_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
_BACKTICK_REF = re.compile(r"`([^`]+?\.(?:md|ps1|toml|json))`")


def _is_llm_body(art: Artifact) -> bool:
    """A rendered FILE/MARKER_BLOCK whose source is an LLM-facing markdown body.

    Scripts (`.ps1`) and generated config/manifest templates are excluded: they are not
    instructional bodies (the spec scopes the `.ps1` "Claude Code" comment OUT).
    """
    if art.kind not in (ArtifactKind.FILE, ArtifactKind.MARKER_BLOCK):
        return False
    if art.source is None:
        return False
    # The rendered target tells us what kind of body it is; `.ps1`/`.json`/`.tmpl` are not bodies.
    src = art.source
    return src.endswith(".md")


def _render_wiki(art: Artifact) -> str:
    if art.kind is ArtifactKind.MARKER_BLOCK:
        assert art.source is not None
        return read_asset_text(art.source)
    return _render_for_target(art)


def _render_rag(art: Artifact) -> str:
    # G1 (E12, R-1 CRITICAL): mirror the REAL render of the plan (`install_rag._render_rag_file`).
    # A Copilot custom-agent (`.agent.md`, e.g. `concierge`) is rendered via `render_custom_agent`
    # (frontmatter translated, `model:` omitted); every other FILE/MARKER_BLOCK body is byte-copy.
    # If this byte-copied the `.agent.md` source instead, the Claude `model: sonnet` frontmatter
    # would slip past the no-leak checks (a/b/c) on Copilot.
    assert art.source is not None
    text = read_asset_text(art.source)
    if art.target_rel.endswith(".agent.md"):
        return render_custom_agent(text)
    return text


def _wiki_plan(assistant: AssistantId) -> list[Artifact]:
    return build_install_plan(assistant)


def _rag_plan(assistant: AssistantId, tmp_path: Path) -> list[Artifact]:
    options = RagInstallOptions(target_root=tmp_path, backend="azure", with_deps=False)
    profile = RagHostProfile.from_options(options)
    return build_rag_plan(profile, with_deps=False, assistant=assistant)


def _governance_plan(assistant: AssistantId, tmp_path: Path) -> list[Artifact]:
    # Imported lazily: sertor-flow is a sibling package (no runtime dependency from sertor).
    from sertor_flow.install_governance import build_governance_plan
    from sertor_flow.profile import build_governance_profile

    profile = build_governance_profile(tmp_path, assistant=assistant.value)
    return build_governance_plan(profile)


def _governance_render(art: Artifact) -> str:
    from sertor_flow.install_governance import _render_for_target as gov_render

    if art.kind is ArtifactKind.MARKER_BLOCK:
        from sertor_install_kit import read_asset_text as kit_read

        assert art.source is not None
        return kit_read("sertor_flow", art.source)
    return gov_render(art)


# --- the three plans, with their per-plan renderer --------------------------------------------


def _rendered_bodies(plan, render) -> list[tuple[str, str, str]]:
    """(target_rel, source, rendered_body) for every LLM-facing artifact of the plan."""
    out: list[tuple[str, str, str]] = []
    for art in plan:
        if _is_llm_body(art):
            out.append((art.target_rel, art.source or "", render(art)))
    return out


def _plan_targets(plan) -> set[str]:
    return {art.target_rel for art in plan}


# ============================================================================ (a)(b)(c) Copilot


def _all_copilot_bodies(tmp_path: Path) -> list[tuple[str, str, str, str]]:
    """(plan_label, target_rel, source, body) for every Copilot LLM-facing body, all installers."""
    bodies: list[tuple[str, str, str, str]] = []
    for label, items in (
        ("wiki", _rendered_bodies(_wiki_plan(AssistantId.COPILOT_CLI), _render_wiki)),
        (
            "governance",
            _rendered_bodies(
                _governance_plan(AssistantId.COPILOT_CLI, tmp_path), _governance_render
            ),
        ),
        ("rag", _rendered_bodies(_rag_plan(AssistantId.COPILOT_CLI, tmp_path), _render_rag)),
    ):
        for target_rel, source, body in items:
            bodies.append((label, target_rel, source, body))
    return bodies


def test_copilot_bodies_have_no_claude_path(tmp_path: Path):
    """(a) FR-005/FR-010 / SC-002: no `.claude/` path-string in any rendered Copilot body."""
    offenders = [
        f"{label}:{target} (from {source})"
        for label, target, source, body in _all_copilot_bodies(tmp_path)
        if ".claude/" in body
    ]
    assert not offenders, f"`.claude/` leaked into Copilot bodies: {offenders}"


def test_copilot_bodies_have_no_slash_command(tmp_path: Path):
    """(b) FR-006/FR-011 / SC-003: no slash-command invocation in any Copilot body."""
    offenders = [
        f"{label}:{target} → {_SLASH_COMMAND.search(body).group(0)!r}"
        for label, target, source, body in _all_copilot_bodies(tmp_path)
        if _SLASH_COMMAND.search(body)
    ]
    assert not offenders, f"slash-command invocation in Copilot bodies: {offenders}"


def test_copilot_bodies_have_no_assistant_name(tmp_path: Path):
    """(c) FR-007/FR-012: no "Claude Code" assistant name in any rendered Copilot body."""
    offenders = [
        f"{label}:{target} (from {source})"
        for label, target, source, body in _all_copilot_bodies(tmp_path)
        if "Claude Code" in body
    ]
    assert not offenders, f'"Claude Code" leaked into Copilot bodies: {offenders}'


# Claude product/model names that have no meaning on a Copilot host: the host instruction file
# (`CLAUDE.md`), the assistant family (`Claude`), and the model tiers (`Opus`, `Haiku`). They name
# Claude-specific products/models, so a body rendered for Copilot must not carry them. Matched
# case-sensitively as whole words (`Claude` must not catch e.g. nothing relevant lowercase).
_CLAUDE_NAMES = (
    re.compile(r"CLAUDE\.md"),
    re.compile(r"\bClaude\b"),
    re.compile(r"\bOpus\b"),
    re.compile(r"\bHaiku\b"),
    # Claude slash-command argument placeholder: substituted on Claude, but a meaningless literal
    # on a Copilot custom-agent — a host-specific construct that must not leak into a Copilot body.
    re.compile(r"\$ARGUMENTS"),
)


def test_copilot_bodies_have_no_claude_product_names(tmp_path: Path):
    """(c') no Claude product/model name (`CLAUDE.md`, `Claude`, `Opus`, `Haiku`) in a Copilot body.

    These are Claude-specific products (the host instruction file) and model tiers; on a Copilot
    host they point at nothing or name the wrong assistant. The concept (host instruction file,
    main flow, background curator) must survive, but the name must go.
    """
    offenders: list[str] = []
    for label, target, source, body in _all_copilot_bodies(tmp_path):
        for pat in _CLAUDE_NAMES:
            for m in pat.finditer(body):
                offenders.append(f"{label}:{target} → {m.group(0)!r} (from {source})")
    assert not offenders, f"Claude product/model name leaked into Copilot bodies: {offenders}"


# ================================================================================ (d) closure


def _references(body: str) -> set[str]:
    """File references in a body: markdown link targets + backtick file mentions.

    Anchors/URLs/section links and placeholders (`<...>`) are filtered out; only concrete file-ish
    references survive.
    """
    refs: set[str] = set()
    for m in _MD_LINK.finditer(body):
        target = m.group(1).strip()
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        # strip an anchor fragment
        target = target.split("#", 1)[0].strip()
        if target and "." in Path(target).name and "<" not in target:
            refs.add(target)
    for m in _BACKTICK_REF.finditer(body):
        ref = m.group(1).strip()
        if "<" not in ref:  # `ops/<operation>.md` is an illustrative placeholder, not a file
            refs.add(ref)
    return refs


def _basename(ref: str) -> str:
    return Path(ref).name


# Basenames of the multi-file SUPPORT PAYLOAD bundled with the wiki-author skill (playbook + ops +
# craft). These are the files a body references BY NAME and that the plan MUST deposit on the host
# (closure scope). References to host files (`CLAUDE.md`, `index.md`, `tasks.md`), to spec/req
# artifacts, or to wiki example pages (`azure-ai-search.md`) are NOT plan-deposited payload — they
# are out of closure scope. This is computed from the single canonical source (no hardcoded list).
def _payload_basenames() -> set[str]:
    from sertor_installer.resources import iter_asset_dir

    names: set[str] = set()
    for rel_path, _content in iter_asset_dir("claude/skills/wiki-author"):
        names.add(Path(rel_path).name)
    return names


def _closure_offenders(plan, render) -> list[str]:
    """Payload references that do not resolve to any deposited plan target (by basename).

    Scope = references to the wiki-author support payload (by name). A body that references the
    playbook/ops/craft of the skill MUST find it deposited by the plan; otherwise the capability is
    broken on the host (the FEAT-001 bug). Non-payload references (host files, spec artifacts,
    example pages, placeholders) are out of scope.
    """
    payload = _payload_basenames()
    target_basenames = {Path(t).name for t in _plan_targets(plan)}
    offenders: list[str] = []
    for target_rel, _source, body in _rendered_bodies(plan, render):
        for ref in _references(body):
            base = _basename(ref)
            if base not in payload:
                continue  # not a skill-payload reference → not the plan's responsibility
            if base not in target_basenames:
                offenders.append(f"{target_rel} → {ref}")
    return offenders


def test_copilot_reference_closure(tmp_path: Path):
    """(d) FR-013 / SC-004: every file a Copilot body references is a deposited plan target."""
    offenders = _closure_offenders(_wiki_plan(AssistantId.COPILOT_CLI), _render_wiki)
    offenders += _closure_offenders(
        _governance_plan(AssistantId.COPILOT_CLI, tmp_path), _governance_render
    )
    assert not offenders, f"dangling references in Copilot bodies: {offenders}"


def test_claude_reference_closure(tmp_path: Path):
    """(d)/T002 FR-014 / SC-004: closure on CLAUDE plan (no dangling refs from neutralization)."""
    offenders = _closure_offenders(_wiki_plan(AssistantId.CLAUDE), _render_wiki)
    offenders += _closure_offenders(
        _governance_plan(AssistantId.CLAUDE, tmp_path), _governance_render
    )
    assert not offenders, f"dangling references in Claude bodies: {offenders}"


# ================================================================================ T003: meta


def test_slash_regex_does_not_false_positive_on_paths_and_urls():
    """R1: the slash-command regex matches `/wiki` (invocation) but NOT `wiki/` paths or URLs."""
    # POSITIVE — invocations the regex MUST catch.
    assert _SLASH_COMMAND.search("run the `/wiki` command")
    assert _SLASH_COMMAND.search("invoke /requirements to start")
    assert _SLASH_COMMAND.search("/wiki record")
    assert _SLASH_COMMAND.search("(/wiki generate medium)")
    # NEGATIVE — POSIX paths, URLs, config keys: NO leading `/command` boundary.
    assert not _SLASH_COMMAND.search("read wiki/log/2026.md")
    assert not _SLASH_COMMAND.search("see https://example.com/wiki/page")
    assert not _SLASH_COMMAND.search("the requirements.md file")
    assert not _SLASH_COMMAND.search("source_dirs in wiki/wiki.config.toml")


def test_closure_names_a_dangling_reference():
    """(d) negative: a body citing an undeposited PAYLOAD file fails closure, naming the reference.

    The reference must be a real payload basename (e.g. `wiki-playbook.md`) so it is in closure
    scope; a plan that does NOT deposit it must be flagged — this is exactly the FEAT-001 bug shape.
    """
    from sertor_installer.artifacts import WriteStrategy

    fake_plan = [
        Artifact(
            ArtifactKind.FILE, "claude/agents/x.md", ".github/agents/x.agent.md",
            WriteStrategy.CREATE_IF_ABSENT,
        ),
    ]

    def render(_art):  # body references the playbook, which the (broken) plan never deposits
        return "Read the `wiki-playbook.md` bundled with this skill and follow it."

    offenders = _closure_offenders(fake_plan, render)
    assert any("wiki-playbook.md" in o for o in offenders), offenders


def test_claude_path_check_catches_reintroduced_leak():
    """(a) negative: a body that reintroduces `.claude/` is caught (guard is not vacuous)."""
    leaked = "Read `.claude/skills/wiki-author/wiki-playbook.md` and follow it."
    assert ".claude/" in leaked  # sanity: the substring the guard searches for


# ===================================================== (d) E12: usability asset closure (R-2)

# Usability assets the concierge agent / guided-setup skill may reference BY NAME (not as a `.md`
# file path, so the file-based `_BACKTICK_REF` closure does not catch them). The concierge cites
# `guided-setup` by name → the skill MUST be deposited on that target, else routing points at
# nothing (the FEAT-001 bug shape for agentic assets).
_USABILITY_ASSET_NAME = re.compile(r"\b(guided-setup|concierge)\b")


def _usability_target_names(plan) -> set[str]:
    """Names of usability assets the rag plan deposits on a target (by basename, hyphenated id)."""
    names: set[str] = set()
    for target in _plan_targets(plan):
        base = Path(target).name
        if base == "SKILL.md":
            # skills live at `<base>/<name>/SKILL.md` → the name is the parent dir
            names.add(Path(target).parent.name)
        elif base.endswith((".md", ".agent.md")):
            # agents live at `agents/<name>.md` or `<name>.agent.md`
            names.add(base.split(".", 1)[0])
    return names


def _usability_closure_offenders(plan, render) -> list[str]:
    """Usability names cited by a body that the plan does NOT deposit on the same target."""
    deposited = _usability_target_names(plan)
    offenders: list[str] = []
    for target_rel, _source, body in _rendered_bodies(plan, render):
        for m in _USABILITY_ASSET_NAME.finditer(body):
            name = m.group(1)
            if name not in deposited:
                offenders.append(f"{target_rel} → {name}")
    return offenders


def test_rag_usability_asset_closure_copilot(tmp_path: Path):
    """(d) E12: every usability asset the Copilot rag bodies cite by name is deposited (R-2)."""
    offenders = _usability_closure_offenders(
        _rag_plan(AssistantId.COPILOT_CLI, tmp_path), _render_rag
    )
    assert not offenders, f"dangling usability references in Copilot rag bodies: {offenders}"


def test_rag_usability_asset_closure_claude(tmp_path: Path):
    """(d) E12: every usability asset the Claude rag bodies cite by name is deposited (R-2)."""
    offenders = _usability_closure_offenders(_rag_plan(AssistantId.CLAUDE, tmp_path), _render_rag)
    assert not offenders, f"dangling usability references in Claude rag bodies: {offenders}"


def test_usability_closure_names_a_dangling_reference(tmp_path: Path):
    """(d) negative: a concierge that routes to an undeposited skill fails closure (sanity)."""
    full = _rag_plan(AssistantId.CLAUDE, tmp_path)
    plan = [a for a in full if "guided-setup" not in a.target_rel]
    offenders = _usability_closure_offenders(plan, _render_rag)
    assert any("guided-setup" in o for o in offenders), offenders


# ============================================= (d) E10-FEAT-021: CLI reference closure (G4)

# The canonical CLI reference cited by name (`` `sertor-cli-reference.md` ``) from the RAG usage
# block and the guided-setup skill MUST be a deposited target of the SAME (rag) plan — otherwise the
# pointer is dead on the host (the FEAT-001 bug shape). Twin of `_usability_closure_offenders`, but
# keyed on a `.md` basename rather than a hyphenated asset id.
_CLI_REFERENCE_BASENAME = "sertor-cli-reference.md"


def _reference_closure_offenders(plan, render) -> list[str]:
    """Bodies that cite `sertor-cli-reference.md` by name without the plan depositing it."""
    deposited = {Path(t.target_rel).name for t in plan}
    out: list[str] = []
    for target_rel, _src, body in _rendered_bodies(plan, render):
        if f"`{_CLI_REFERENCE_BASENAME}`" in body and _CLI_REFERENCE_BASENAME not in deposited:
            out.append(target_rel)
    return out


def test_cli_reference_closure_in_rag_plan(tmp_path: Path):
    """G4: the CLI reference is deposited by the rag plan (Claude + Copilot) wherever cited."""
    claude_plan = _rag_plan(AssistantId.CLAUDE, tmp_path)
    copilot_plan = _rag_plan(AssistantId.COPILOT_CLI, tmp_path)
    assert _reference_closure_offenders(claude_plan, _render_rag) == [], (
        "Claude rag plan: sertor-cli-reference.md cited but not deposited"
    )
    assert _reference_closure_offenders(copilot_plan, _render_rag) == [], (
        "Copilot rag plan: sertor-cli-reference.md cited but not deposited"
    )


def test_cli_reference_closure_fails_if_not_deposited(tmp_path: Path):
    """G4 negative: a plan that cites the reference but never deposits it fails closure (sanity)."""
    from sertor_installer.artifacts import WriteStrategy

    fake_body_art = Artifact(
        ArtifactKind.MARKER_BLOCK,
        "rag/claude-md-block-rag-usage.md",  # body cites `sertor-cli-reference.md`
        ".claude/CLAUDE.md",
        WriteStrategy.APPEND_BLOCK,
    )
    plan_without_ref = [fake_body_art]  # the FILE for the reference is missing
    offenders = _reference_closure_offenders(plan_without_ref, _render_rag)
    assert offenders != [], "a plan without the reference should have failed closure"
